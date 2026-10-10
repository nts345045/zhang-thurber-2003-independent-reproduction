#!/usr/bin/env python3
"""Freeze initial Loma rays and a stage-0 matrix census; never solve an inversion."""
import argparse
import csv
import json
import math
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import sys
import tarfile

from run_loma_analytic_simulation import atomic_json, inside, sha, utc, verify_hashes
from diagnostics.review_loma_analytic_simulation import terminal_inputs

ROOT = Path(__file__).resolve().parent
COPIED = ('initial_events.csv', 'initial_grid.csv', 'truth_events.csv', 'truth_grid.csv',
          'stations.csv', 'observations.csv', 'ray_samples.csv', 'authoritative_geometry')
PROVENANCE = ('run.cfg', 'preparation_manifest.json', 'analytic_truth_manifest.json',
              'simulation_execution.json', 'simulation_run_manifest.json',
              'simulation_source.tar.gz', 'independent_simulation_review.json')
SETTINGS = dict(iterations=1, matrix_preflight_only=1, ray_initializer=1,
                ray_spacing=.03125, fmm_spacing=.125, ray_iterations=1000,
                raycheck_receiver_batch=4)
THREADS, LIMIT_GIB = 4, 128
PREFIX = 'geometry_initial_ray'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def rows(path):
    with path.open(newline='') as stream:
        reader = csv.DictReader(stream)
        require(reader.fieldnames and len(reader.fieldnames) == len(set(reader.fieldnames)),
                'Missing or duplicate CSV header: ' + str(path))
        for row in reader:
            require(None not in row and None not in row.values(), 'Malformed CSV row: ' + str(path))
            yield row


def finite(value):
    result = float(value)
    require(math.isfinite(result), 'Nonfinite diagnostic value')
    return result


def reviewed_simulation(data):
    """Rehash the terminal files once; do not repeat the 15.9M-row algebra audit."""
    manifest, hashes = terminal_inputs(data)
    review_path = data / 'independent_simulation_review.json'
    review = json.loads(review_path.read_text())
    require(review['status'] == 'passed' and review['input_sha256'] == hashes,
            'Independent simulation review does not bind these exact terminal files')
    for name, key in [('simulation_execution.json', 'simulation_execution_sha256'),
                      ('simulation_run_manifest.json', 'simulation_run_manifest_sha256')]:
        require(review[key] == hashes[name], 'Independent review provenance link changed: ' + name)
    expected = manifest['expected_counts']
    actual = dict(events=review['source_count'], receivers=review['receiver_count'],
                  unique_rays=review['arrival_count'], total_rows=review['total_observations'],
                  absolute_rows=review['observation_counts_by_type'][0],
                  catalog_rows=review['observation_counts_by_type'][1],
                  precise_rows=review['observation_counts_by_type'][2])
    require(all(actual[k] == expected[k] for k in actual), 'Simulation review inventory differs')
    require(review['all_native_fields_match'] and review['truth_status_all_fields_exact'] and
            review['ray_status_fields_blank'], 'Simulation native/truth status audit incomplete')
    hashes['independent_simulation_review.json'] = sha(review_path)
    require(set(COPIED + PROVENANCE) <= set(hashes), 'Required preflight input was not reviewed')
    require((data / 'simulation_truth_mode.txt').read_text().splitlines()[0] ==
            'truth_mode continuous_layered_snell_reference', 'Wrong explicit synthetic truth mode')
    return expected, hashes


def configuration(source):
    values = {}
    for line in source.splitlines():
        words = line.split('#', 1)[0].split()
        if words:
            require(len(words) == 2, 'Malformed inherited configuration')
            finite(words[1]); values[words[0]] = words[1]
    require(float(values.get('authoritative_geometry', 0)) == 1 and
            float(values.get('stage_length', 0)) > 0, 'Require identified geometry and positive stage length')
    # Preserve all inverse weights and other settings; only these declared
    # assessment controls change. Iteration zero is unambiguously stage zero.
    values.update({key: str(value) for key, value in SETTINGS.items()})
    text = '# Initial-ray/matrix census only; no matrix allocation or inverse solve.\n'
    text += '# Original truth-defined sample IDs retained; coordinates use initial_events.csv.\n'
    return text + ''.join('{} {}\n'.format(key, value) for key, value in values.items())


def inventory(data, expected):
    events, stations = [list(rows(data / name)) for name in ('initial_events.csv', 'stations.csv')]
    grid, sample = [list(rows(data / name)) for name in ('initial_grid.csv', 'ray_samples.csv')]
    require(len(events) == expected['events'] and len(stations) == expected['receivers'] and
            len(events) * len(stations) == expected['unique_rays'], 'Initial geometry inventory differs')
    for table in (events, stations):
        require(all(row['id'] == str(i) for i, row in enumerate(table)), 'Changed native geometry indices')
    bounds = {axis: (min(finite(r[axis]) for r in grid), max(finite(r[axis]) for r in grid)) for axis in 'xyz'}
    require(all(finite(r['v']) > 0 for r in grid), 'Nonpositive initial velocity')
    for table in (events, stations):
        for row in table:
            require(all(bounds[a][0] <= finite(row[a]) <= bounds[a][1] for a in 'xyz'),
                    'Initial source or receiver outside the saved grid')
            finite(row['t'])
    selected = [(int(r['event']), int(r['station'])) for r in sample]
    require(len(selected) == expected['diagnostic_sample_rays'] and len(set(selected)) == len(selected) and
            all(0 <= i < len(events) and 0 <= k < len(stations) for i, k in selected),
            'Changed or invalid truth-defined sample inventory')
    components = []
    for n, (i, k) in enumerate(selected[:8]):
        for axis, key in enumerate('xyz'):
            x = finite(events[i][key])
            if bounds[key][0] <= x - .01 and x + .01 <= bounds[key][1]:
                components.append((n, i, k, axis))
    return events, stations, grid, selected, components


def native(row, event, station, with_time=False):
    for prefix, original in [('source_', event), ('receiver_', station)]:
        for key, value in original.items():
            if key not in ('id', 'x', 'y', 'z', 't'):
                require(row[prefix + key] == value, 'Changed native metadata: ' + prefix + key)
        for axis in 'xyz':
            require(finite(row[prefix + axis]) == float(format(float(original[axis]), '.12g')),
                    'Diagnostic coordinates differ from actual initial geometry')
    if with_time:
        require(finite(row['source_t']) == float(format(float(event['t']), '.12g')),
                'Initial source correction changed or confused with travel time')


def identified_failure(events, stations, i, k, **details):
    record = dict(event=i, station=k, event_resource_id=events[i]['event_resource_id'],
                  origin_resource_id=events[i]['origin_resource_id'])
    for key in ('network_code', 'station_code', 'location_code', 'channel_code',
                'channel_seed_id', 'channel_fdsn_source_id', 'metadata_epoch_start', 'metadata_epoch_end'):
        record[key] = stations[k][key]
    record.update(details)
    return record


def check_full(data, expected, geometry):
    events, stations, grid, selected, components = geometry
    require(not list(rows(data / 'dd_history.csv')), 'Preflight unexpectedly performed an inverse iteration')
    for name in ('dd_events.csv', 'dd_grid.csv', 'dd_residuals.csv', 'dd_slices.csv'):
        require(not (data / name).exists(), 'Preflight unexpectedly wrote inverse output: ' + name)
    matrix = list(rows(data / 'dd_matrix_preflight.csv'))
    require(len(matrix) == 1 and matrix[0]['iteration'] == '0', 'Require one stage-0 matrix census')
    m = {key: finite(value) for key, value in matrix[0].items()}
    require(all(v >= 0 and v.is_integer() for v in m.values()), 'Invalid matrix count')
    require(m['observation_rows'] == expected['total_rows'] and
            m['columns'] == 4 * len(events) + len(grid) and
            m['damped_rows'] == m['active_data_rows'] + m['smoothing_rows'] + m['columns'],
            'Matrix census geometry/observation inventory differs')
    failures, count = [], 0
    max_projected, max_raw = 0., 0.
    for n, row in enumerate(rows(data / 'dd_preflight_ray_status.csv')):
        i, k = divmod(n, len(stations))
        require(i < len(events) and (row['event'], row['station']) == (str(i), str(k)),
                'Full initial ray support/order differs')
        native(row, events[i], stations[k], True)
        require(all(row[key] == '1' for key in ('ray_finite', 'ray_path_in_domain',
                    'ray_exact_source_endpoint', 'ray_exact_receiver_endpoint',
                    'ray_initialization_attempted', 'ray_initialization_succeeded')),
                'Hard ray validity/initializer failure at event {}, station {}'.format(i, k))
        require(finite(row['ray_time']) >= 0 and int(row['ray_path_points']) >= 2,
                'Invalid pure travel time or path inventory')
        for key in ('source_dx', 'source_dy', 'source_dz', 'ray_projected_gradient', 'ray_raw_gradient'):
            finite(row[key])
        require(row['ray_converged'] in ('0', '1'), 'Invalid local stopping flag')
        if row['ray_converged'] != '1':
            failures.append(identified_failure(events, stations, i, k, row=n,
                reason='unchanged local stopping criterion failed'))
        max_projected = max(max_projected, float(row['ray_projected_gradient']))
        max_raw = max(max_raw, float(row['ray_raw_gradient']))
        count += 1
    require(count == expected['unique_rays'], 'Incomplete full initial ray support')
    return dict(full_rays=count, local_converged=count - len(failures), local_failures=failures,
                maximum_projected_gradient=max_projected, maximum_raw_gradient=max_raw,
                matrix_census=matrix[0], matrix_stage=0)


def check_sample(data, geometry):
    events, stations, grid, selected, components = geometry
    sample = list(rows(data / (PREFIX + '_convergence.csv')))
    ids = list(rows(data / (PREFIX + '_identifiers.csv')))
    derivatives = list(rows(data / (PREFIX + '_derivatives.csv')))
    require(len(sample) == len(ids) == len(selected), 'Sample support incomplete')
    failures = []
    for n, (row, identity, pair) in enumerate(zip(sample, ids, selected)):
        i, k = pair
        for record in (row, identity):
            require(tuple(record[key] for key in ('diagnostic_row', 'event', 'station')) ==
                    tuple(map(str, (n, i, k))), 'Truth-defined sample order/native indices changed')
        native(identity, events[i], stations[k])
        for key in ('production_time', 'refined_time', 'difference', 'production_gradient',
                    'refined_gradient', 'production_raw_gradient', 'refined_raw_gradient'):
            finite(row[key])
        for key, value in [('production_path_spacing', SETTINGS['ray_spacing']),
                           ('refined_path_spacing', SETTINGS['ray_spacing'] / 2),
                           ('production_requested_fmm_spacing', SETTINGS['fmm_spacing']),
                           ('refined_requested_fmm_spacing', SETTINGS['fmm_spacing'] / 2)]:
            require(finite(row[key]) == value, 'Sample spacing/refinement changed')
        for prefix in ('production_', 'refined_'):
            require(all(row[prefix + key] == '1' for key in ('initialization_attempted', 'initialization_succeeded')),
                    'Sample initializer failed at diagnostic row ' + str(n))
            require(row[prefix + 'converged'] in ('0', '1'), 'Invalid sample stopping flag')
            if row[prefix + 'converged'] != '1':
                failures.append(identified_failure(events, stations, i, k, diagnostic_row=n, side=prefix,
                                     reason='unchanged local stopping criterion failed'))
    actual = [tuple(int(r[key]) for key in ('diagnostic_row', 'event', 'station', 'axis')) for r in derivatives]
    require(actual == components, 'Valid central-difference component inventory/order changed')
    for row in derivatives:
        for key in ('production_derivative', 'refined_derivative', 'finite_difference', 'production_error', 'refined_error'):
            finite(row[key])
        for prefix in ('plus_', 'minus_'):
            require(all(row[prefix + key] == '1' for key in ('initialization_attempted', 'initialization_succeeded')),
                    'Derivative perturbation initializer failed')
            require(row[prefix + 'converged'] in ('0', '1'), 'Invalid perturbation stopping flag')
            if row[prefix + 'converged'] != '1':
                failures.append(identified_failure(events, stations, int(row['event']), int(row['station']),
                    diagnostic_row=int(row['diagnostic_row']), axis=int(row['axis']),
                    side=prefix, reason='perturbed local stopping criterion failed'))
    return dict(sample_rays=len(sample), derivative_components=len(derivatives), local_failures=failures,
                maximum_absolute_time_refinement_s=max(abs(float(r['difference'])) for r in sample),
                maximum_production_fd_error_s_per_km=max([abs(float(r['production_error'])) for r in derivatives] or [0.]),
                maximum_refined_fd_error_s_per_km=max([abs(float(r['refined_error'])) for r in derivatives] or [0.]),
                numerical_magnitudes_status='Retained for scientific review; no new sampled accuracy threshold imposed')


def disjoint(*paths):
    for i, a in enumerate(paths):
        require(a != ROOT, 'Repository root is not a run directory')
        for b in paths[i + 1:]:
            require(a != b and a not in b.parents and b not in a.parents, 'Run directories must be disjoint')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--simulation', required=True, help='Unchanged completed and independently audited simulation')
    parser.add_argument('--output', required=True, help='Fresh copied initial-preflight directory')
    parser.add_argument('--build', required=True, help='Fresh source/build directory')
    args = parser.parse_args()
    data, out, build = [inside(ROOT, ROOT / p) for p in (args.simulation, args.output, args.build)]
    disjoint(data, out, build)
    require(not out.exists() and not build.exists(), 'Preserve previous runs; require fresh output and build directories')
    expected, original_hashes = reviewed_simulation(data)
    out.mkdir(parents=True)  # Exclusive directory creation guards the whole run.
    ledger_path = out / 'preflight_execution.json'
    ledger = dict(status='preparing', started_utc=utc(), driver_pid=os.getpid(), command=sys.argv,
                  threads=THREADS, completed_commands=[], scope=__doc__,
                  simulation_directory=str(data.relative_to(ROOT)),
                  simulation_review_sha256=original_hashes['independent_simulation_review.json'])
    atomic_json(ledger_path, ledger)
    active = None
    env = dict(os.environ, TMPDIR=str(ROOT / 'tmp'), PYTHONDONTWRITEBYTECODE='1',
               OMP_NUM_THREADS=str(THREADS), OPENBLAS_NUM_THREADS='1', LC_ALL='C')

    def run(command, stage, limited=False):
        nonlocal active
        command = [str(x) for x in command]
        measured = ['/usr/bin/time', '-v', '-o', str(out / (stage + '_resources.txt'))] + command
        ledger.update(status='running', current_stage=stage, current_command=command,
                      current_command_started_utc=utc(), current_child_pid=None,
                      child_pid_semantics='GNU time process-group leader; it waits for the stated executable')
        atomic_json(ledger_path, ledger)
        def limit():
            resource.setrlimit(resource.RLIMIT_AS, (LIMIT_GIB * 1024**3, LIMIT_GIB * 1024**3))
        with (out / (stage + '_stdout.log')).open('x') as stdout, (out / (stage + '_stderr.log')).open('x') as stderr:
            active = subprocess.Popen(measured, cwd=str(ROOT), env=env, stdout=stdout, stderr=stderr,
                                      start_new_session=True, preexec_fn=limit if limited else None)
            ledger['current_child_pid'] = active.pid
            atomic_json(ledger_path, ledger)
            code = active.wait()
        record = dict(stage=stage, command=command, supervisor_command=measured, pid=active.pid,
                      return_code=code, finished_utc=utc())
        resource_text = (out / (stage + '_resources.txt')).read_text()
        for line in resource_text.splitlines():
            if 'Maximum resident set size (kbytes):' in line:
                record['maximum_resident_set_kbytes'] = int(line.rsplit(':', 1)[1])
        ledger['completed_commands'].append(record)
        active = None
        atomic_json(ledger_path, ledger)
        if code:
            raise subprocess.CalledProcessError(code, command)

    def interrupted(signum, unused):
        raise SystemExit(128 + signum)
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    try:
        copied = {}
        for name in COPIED + PROVENANCE:
            relative = name if name in COPIED else 'simulation_provenance/' + name
            target = out / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(str(data / name), str(target))
            copied[relative] = original_hashes[name]
        verify_hashes(out, copied)
        (out / 'run.cfg').write_text(configuration((data / 'run.cfg').read_text()))
        copied['run.cfg'] = sha(out / 'run.cfg')
        geometry = inventory(out, expected)
        source = build / 'source'; source.mkdir(parents=True)
        names = [Path('CMakeLists.txt'), Path(__file__).resolve().relative_to(ROOT),
                 Path('run_loma_analytic_simulation.py'), Path('diagnostics/review_loma_analytic_simulation.py')]
        names += [p.relative_to(ROOT) for p in sorted((ROOT / 'src').iterdir()) if p.is_file()]
        source_hashes = {str(p): sha(ROOT / p) for p in names}
        for name in names:
            target = source / name; target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(str(ROOT / name), str(target))
        verify_hashes(ROOT, source_hashes); verify_hashes(source, source_hashes)
        def normalize(info):
            info.uid = info.gid = info.mtime = 0
            info.uname = info.gname = ''; info.pax_headers = {}
            return info
        archive = out / 'preflight_source.tar.gz'
        with tarfile.open(str(archive), 'x:gz') as stream:
            for name in names:
                stream.add(str(source / name), arcname=str(name), filter=normalize)
        ledger.update(input_sha256=copied, source_sha256=source_hashes, source_archive_sha256=sha(archive))
        atomic_json(ledger_path, ledger)
        run(['cmake', '--version'], 'cmake_version')
        run(['cmake', '-S', source, '-B', build / 'compiled'], 'configure')
        cache = (build / 'compiled/CMakeCache.txt').read_text().splitlines()
        compiler = next(line.split('=', 1)[1] for line in cache if line.startswith('CMAKE_CXX_COMPILER:FILEPATH='))
        run([compiler, '--version'], 'compiler_version')
        run(['cmake', '--build', build / 'compiled', '-j', '2'], 'compile')
        binary = build / 'compiled/dd'
        run(['ldd', binary], 'runtime_libraries')
        libraries = {}
        for line in (out / 'runtime_libraries_stdout.log').read_text().splitlines():
            for name in line.split():
                if name.startswith('/'):
                    libraries[name] = sha(Path(name))
        manifest = dict(base_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=str(ROOT), universal_newlines=True).strip(),
            simulation_directory=str(data.relative_to(ROOT)), simulation_review_sha256=original_hashes['independent_simulation_review.json'],
            original_simulation_sha256=original_hashes, input_sha256=copied, expected_counts=expected,
            source_directory=str(source.relative_to(ROOT)), source_sha256=source_hashes, source_archive_sha256=sha(archive),
            binary=str(binary.relative_to(ROOT)), binary_sha256=sha(binary), compiler=compiler,
            compiler_sha256=sha(Path(compiler)), runtime_library_sha256=libraries,
            settings=SETTINGS, matrix_mode='dd', matrix_iteration=0, matrix_stage=0,
            matrix_preflight_only=True, expected_valid_fd_components=len(geometry[4]),
            sample_selection_basis='Unchanged truth-geometry selected IDs; diagnostics use actual perturbed initial coordinates',
            truth_mode='continuous_layered_snell_reference', threads=THREADS, address_space_limit_GiB=LIMIT_GIB,
            environment={key: env[key] for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'TMPDIR', 'PYTHONDONTWRITEBYTECODE', 'LC_ALL')},
            limitations=['No inverse solve or accepted inversion is performed.',
                'Full continuous initial-z references and their independent accuracy review remain separate prerequisites.',
                'Initial 1D accuracy does not certify arbitrary updated 3D models or nonlinear convergence.',
                'Sample differences and central differences are retained for review; FD truncation is separate from ray accuracy.',
                'Receiver batching bounds field count; the declared address-space limit is not a measured-memory guarantee.'])
        atomic_json(out / 'preflight_run_manifest.json', manifest)

        def frozen():
            verify_hashes(out, copied); verify_hashes(source, source_hashes)
            require(sha(binary) == manifest['binary_sha256'] and sha(archive) == manifest['source_archive_sha256'],
                    'Frozen executable/source changed')
            require(sha(Path(compiler)) == manifest['compiler_sha256'], 'Compiler changed')
            for name, digest in libraries.items():
                require(sha(Path(name)) == digest, 'Runtime library changed: ' + name)
        frozen()
        # This is the sole use of the invert CLI; the pinned configuration
        # returns after the stage-0 census and cannot allocate/solve the matrix.
        run([binary, 'invert', out / 'run.cfg', out, 'dd'], 'initial_matrix_preflight', True)
        full = check_full(out, expected, geometry)
        atomic_json(out / 'full_initial_checks.json', full)
        frozen()
        # Preserve diagnostic evidence even when a full-support local flag is false.
        run([binary, 'geometrycheck', out / 'run.cfg', out, 'initial'], 'initial_geometrycheck', True)
        sample = check_sample(out, geometry)
        frozen(); verify_hashes(data, original_hashes)
        result = dict(full=full, sample=sample, independent_reference_status='awaiting separate full initial-z comparison',
                      inversion_accepted=False,
                      status='failed_scientific_checks_preserved' if full['local_failures'] or sample['local_failures'] else 'ready_for_accuracy_review')
        atomic_json(out / 'preflight_checks.json', result)
        outputs = {p.name: sha(p) for p in sorted(out.iterdir()) if p.is_file() and
                   p.name not in set(copied) | {'preflight_execution.json'}}
        ledger.update(status='completed', finished_utc=utc(), return_code=0, result_status=result['status'],
                      output_sha256=outputs, immutable_inputs_verified=True, original_simulation_verified=True)
        atomic_json(ledger_path, ledger)
        print(json.dumps({key: result[key] for key in ('status', 'independent_reference_status', 'inversion_accepted')}, indent=2))
    except BaseException as error:
        if active is not None:
            if active.poll() is None:
                try: os.killpg(active.pid, signal.SIGTERM)
                except ProcessLookupError: pass
                try: active.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    try: os.killpg(active.pid, signal.SIGKILL)
                    except ProcessLookupError: pass
                    active.wait()
            ledger['exception_child'] = dict(pid=active.pid, return_code=active.returncode)
        ledger.update(status='interrupted' if isinstance(error, (SystemExit, KeyboardInterrupt)) else 'failed',
                      finished_utc=utc(), error=str(error),
                      return_code=getattr(error, 'returncode', getattr(error, 'code', None)))
        ledger['partial_output_sha256'] = {p.name: sha(p) for p in sorted(out.iterdir()) if p.is_file() and
                                          p.name not in set(COPIED) | {'run.cfg', 'preflight_execution.json'}}
        atomic_json(ledger_path, ledger)
        raise


if __name__ == '__main__':
    main()
