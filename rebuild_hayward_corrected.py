#!/usr/bin/env python3
"""Replay the identified Hayward preparation and one guarded catalog-plus-CC attempt."""
import argparse
import csv
import datetime
import hashlib
import importlib.util
import io
import json
import math
import os
from pathlib import Path
import re
import resource
import shutil
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
SOURCES = ROOT / 'data/development/hayward_corrected_rebuild_sources_001'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def write_json(path, value):
    temporary = path.with_name(path.name + '.new')
    with temporary.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
    os.replace(str(temporary), str(path))


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def verify(base, pins):
    for name, digest in pins.items():
        path = base / name
        require(not path.is_symlink() and path.is_file(), 'Missing regular input: ' + name)
        path.resolve().relative_to(base.resolve())
        require(sha(path) == digest, 'Input/source hash differs: ' + name)


def fresh_path(value, parent):
    path = Path(os.path.abspath(str(value)))
    require(path.parent == parent and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', path.name),
            'Use a fresh named immediate child of ' + str(parent))
    require(not path.exists() and not path.is_symlink(), 'Refusing existing destination: ' + str(path))
    for part in (path,) + tuple(path.parents):
        require(not part.is_symlink(), 'Destination traverses a symbolic link: ' + str(part))
    require(path.resolve() == path, 'Destination is not canonical')
    return path


def executable(value):
    found = shutil.which(str(value))
    require(found is not None, 'Executable unavailable: ' + str(value))
    # Invocation names select TeX formats and Python virtual environments.
    return os.path.abspath(found)


def group_members(pgid):
    """Linux process groups: zombies are reported but cannot write scientific files."""
    result = []
    for path in Path('/proc').glob('[0-9]*/stat'):
        try:
            fields = path.read_text().rsplit(')', 1)[1].split()
        except FileNotFoundError:
            continue
        if int(fields[2]) == pgid:
            result.append({'pid': int(path.parent.name), 'state': fields[0]})
    return result


def cleanup(child, record):
    # Only the new session created for this exact child is ever signalled.
    for sig in (signal.SIGTERM, signal.SIGKILL):
        members = group_members(child.pid)
        if not any(p['state'] != 'Z' for p in members):
            break
        try:
            os.killpg(child.pid, sig)
        except ProcessLookupError:
            pass
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if child.poll() is not None and not any(p['state'] != 'Z' for p in group_members(child.pid)):
                break
            time.sleep(0.1)
    record['return_code'] = child.wait(timeout=5)
    record['child_reaped'] = True
    record['remaining_group_members'] = group_members(child.pid)
    record['outputs_stable'] = not any(p['state'] != 'Z' for p in record['remaining_group_members'])


def run_stage(command, stage, build, env, outcome, native=False, cwd=ROOT):
    command = [str(value) for value in command]
    record = dict(stage=stage, command=command, started_utc=utc(), return_code=None,
                  child_reaped=False, outputs_stable=False)
    outcome['commands'].append(record)
    child = None
    oldmask = None
    try:
        with (build / 'logs' / (stage + '.stdout')).open('xb') as stdout, \
                (build / 'logs' / (stage + '.stderr')).open('xb') as stderr:
            oldmask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGINT, signal.SIGTERM})

            def child_setup():
                signal.pthread_sigmask(signal.SIG_SETMASK, oldmask)
                if native:
                    _, hard = resource.getrlimit(resource.RLIMIT_AS)
                    limit = 128 * 1024 ** 3
                    if hard != resource.RLIM_INFINITY:
                        limit = min(limit, hard)
                    resource.setrlimit(resource.RLIMIT_AS, (limit, limit))

            child = subprocess.Popen(command, cwd=str(cwd), env=env, stdout=stdout, stderr=stderr,
                                     start_new_session=True, preexec_fn=child_setup)
            record.update(pid=child.pid, pgid=child.pid)
            write_json(build / 'execution.json', outcome)
            signal.pthread_sigmask(signal.SIG_SETMASK, oldmask)
            oldmask = None
            record['return_code'] = child.wait()
            record['child_reaped'] = True
            record['remaining_group_members'] = group_members(child.pid)
            record['outputs_stable'] = not any(p['state'] != 'Z' for p in record['remaining_group_members'])
            require(record['outputs_stable'], stage + ' left a live process-group member')
            if record['return_code'] != 0:
                raise RuntimeError(stage + ' exited ' + str(record['return_code']))
    except BaseException:
        if child is not None:
            handlers = {sig: signal.signal(sig, signal.SIG_IGN) for sig in (signal.SIGINT, signal.SIGTERM)}
            try:
                cleanup(child, record)
            except BaseException as error:
                record['cleanup_error'] = repr(error)
                record['outputs_stable'] = False
            finally:
                for sig, handler in handlers.items():
                    signal.signal(sig, handler)
        else:
            record['launch_failed'] = True
            record['outputs_stable'] = True
        raise
    finally:
        if oldmask is not None:
            signal.pthread_sigmask(signal.SIG_SETMASK, oldmask)
        record['finished_utc'] = utc()
        write_json(build / 'execution.json', outcome)


def catalog_compatibility(output, expected):
    actual = {name: sha(output / name) for name in expected['expected_catalog_sha256']}
    different = {name: {'expected': digest, 'actual': actual[name]}
                 for name, digest in expected['expected_catalog_sha256'].items() if actual[name] != digest}
    manifest = json.loads((output / 'selection_manifest.json').read_text())
    reference = json.loads((SOURCES / 'expected_selection_manifest.json').read_text())
    require(manifest.pop('script_sha256') == sha(SOURCES / 'prepare_hayward.py'),
            'Preparation source identity differs')
    reference.pop('script_sha256')
    compatible = not different and manifest == reference
    write_json(output / 'catalog_compatibility.json', dict(
        status='passed' if compatible else 'failed_preserved', differing_files=different,
        selection_manifest_scientific_fields_equal=manifest == reference,
        adapted_script_sha256=sha(SOURCES / 'prepare_hayward.py'),
        rule='Exact bytes for eight scientific tables; all selection-manifest fields equal except its declared script hash.',
        limitation='A runtime rounding difference is a compatibility failure, not a metadata or physical exclusion.'))
    require(compatible, 'Regenerated catalog differs; see catalog_compatibility.json. '
            'Use a compatible --preparation-python; no rounding substitution is applied.')


def assemble_cc(output, expected):
    # Import only the frozen data assembler; its historical run()/CLI is never called.
    spec = importlib.util.spec_from_file_location('frozen_hayward_cc', str(SOURCES / 'prepare_hayward_cc.py'))
    cc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cc)
    exported = ROOT / 'data/development/native_dt_cc_001'
    fields, catalog = cc.table(output / 'observations.csv')
    _, events = cc.table(output / 'initial_events.csv')
    _, stations = cc.table(output / 'stations.csv')
    _, sidecar = cc.table(exported / 'dt.cc.identifiers.csv.gz')
    _, event_map = cc.table(exported / 'event_id_map.csv')
    _, epochs = cc.table(exported / 'receiver_epochs.csv.gz')
    columns, combined = cc.assemble(fields, catalog, events, stations, sidecar, event_map, epochs,
                                    (exported / 'dt.cc').read_text())
    require(len(catalog) == 58980 and len(combined) == 59078, 'Changed catalog/CC inventory')
    require(not (set(cc.PINS) & set(columns)), 'CC provenance column collision')
    columns += list(cc.PINS)
    for index, row in enumerate(combined):
        row.update(expected['cc_provenance'] if index >= len(catalog) else {name: '' for name in cc.PINS})
    pairs = lambda rows: {(int(r[side]), int(r['station' if side == 'i' else 'station_j']))
                          for r in rows for side in ('i', 'j') if int(r[side]) >= 0}
    require(pairs(catalog) == pairs(combined) and len(pairs(combined)) == 14262,
            'CC rows changed native ray support')
    require(all({key: row[key] for key in fields} == old for row, old in zip(combined, catalog)),
            'A raw catalog field or row order changed')
    (output / 'catalog_provenance').mkdir()
    shutil.copyfile(str(output / 'observations.csv'), str(output / 'catalog_provenance/observations.csv'))
    temporary = output / 'observations.csv.new'
    with temporary.open('x', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, lineterminator='\n')
        writer.writeheader()
        writer.writerows(combined)
    require(sha(temporary) == expected['expected_combined_observations_sha256'],
            'Combined observations differ from the identified saved weighting experiment')
    os.replace(str(temporary), str(output / 'observations.csv'))
    (output / 'cc_inputs').mkdir()
    for name in ('dt.cc', 'dt.cc.identifiers.csv.gz', 'event_id_map.csv', 'receiver_epochs.csv.gz'):
        shutil.copyfile(str(exported / name), str(output / 'cc_inputs' / name))
    write_json(output / 'preparation_manifest.json', dict(
        status='prepared_identified_catalog_plus_cc_inputs', counts=expected['counts'],
        catalog_fields_and_order_unchanged=True, native_ray_support_unchanged=True,
        original_catalog_sha256=sha(output / 'catalog_provenance/observations.csv'),
        combined_observations_sha256=sha(output / 'observations.csv'),
        cc_provenance=expected['cc_provenance'],
        cc_weight='Saved CC squared is the empirical residual/Jacobian row multiplier; squared objective has CC to the fourth power.',
        cc_uncertainty='Blank and unestimated; no CC sigma, covariance or new waveform measurement.',
        selection='Saved provider selection tables, not a reparse or reacquisition of raw provider XML.'))


def table(path):
    with path.open(newline='') as stream:
        reader = csv.DictReader(stream)
        rows = list(reader)
        require(reader.fieldnames and all(None not in r and all(v is not None for v in r.values()) for r in rows),
                'Malformed saved table: ' + path.name)
        return rows


def accepted_states(output):
    """Only snapshot pairs joined to completed history AND accepted trial rows are reportable."""
    path = output / 'dd_history.csv'
    if not path.exists():
        return [], []
    data = path.read_bytes()
    complete = data[:data.rfind(b'\n') + 1].decode('utf-8')
    history = list(csv.DictReader(io.StringIO(complete)))
    original, grid = [table(output / name) for name in ('initial_events.csv', 'initial_grid.csv')]
    bounds = {k: (min(float(r[k]) for r in grid), max(float(r[k]) for r in grid)) for k in 'xyz'}
    states, notes, seen = [], [], set()
    if len(complete.encode('utf-8')) != len(data):
        notes.append('Incomplete final history line retained but excluded from accepted-state joins.')
    for row in history:
        require(None not in row and all(v is not None for v in row.values()), 'Malformed complete history row')
        iteration = int(row['iteration'])
        require(iteration not in seen and 0 <= iteration < 18, 'Invalid/duplicate history iteration')
        seen.add(iteration)
        step = float(row['step_fraction'])
        require(math.isfinite(step) and 0 <= step <= 1, 'Invalid history step')
        if step == 0:
            continue
        trials = table(output / ('dd_iteration_%d_trials.csv' % iteration))
        accepted = [r for r in trials if r['status'] == 'accepted']
        require(len(accepted) == 1 and accepted[0] == trials[-1], 'Accepted history lacks one terminal accepted trial')
        trial = accepted[0]
        require(trial['objective_evaluated'] == '1' and float(trial['step_fraction']) == step,
                'Accepted history/trial step differs')
        require(float(trial['objective_after']) <= float(trial['objective_before']), 'Accepted objective increased')
        for key in ('objective_before', 'objective_after'):
            require(float(row[key]) == float(format(float(trial[key]), '.12g')), 'History/trial objective differs')
        names = {kind: 'dd_accepted_it_%d_%s.csv' % (iteration, kind) for kind in ('events', 'grid')}
        events, model = [table(output / names[kind]) for kind in ('events', 'grid')]
        require(len(events) == len(original) and len(model) == len(grid), 'Snapshot inventory differs')
        for old, new in zip(original, events):
            require(all(new[k] == v for k, v in old.items() if k not in ('x', 'y', 'z', 't', 'coordinate_basis')),
                    'Accepted event native metadata differs')
            require(new['coordinate_basis'] == 'independent accepted inversion state after iteration %d; run incomplete' % iteration,
                    'Accepted snapshot scope differs')
            require(all(math.isfinite(float(new[k])) for k in 'xyzt') and
                    all(bounds[k][0] <= float(new[k]) <= bounds[k][1] for k in 'xyz'), 'Invalid accepted source')
        for old, new in zip(grid, model):
            require(all(float(old[k]) == float(new[k]) for k in 'xyz') and
                    math.isfinite(float(new['v'])) and float(new['v']) > 0, 'Invalid accepted model')
        states.append(dict(iteration=iteration, events_file=names['events'], grid_file=names['grid'],
                           sha256s={name: sha(output / name) for name in names.values()}))
    linked = {name for state in states for name in state['sha256s']}
    unlinked = sorted(p.name for p in output.glob('dd_accepted_it_*') if p.name not in linked)
    if unlinked:
        notes.append('Unjoined snapshot files are preserved and not presented as accepted: ' + ', '.join(unlinked))
    return states, notes


def make_report(output, build, env, python, mapping):
    """Report a closed attempt without rewriting its numerical outcome or changing its return code."""
    logs = build / 'report'
    (logs / 'logs').mkdir(parents=True)
    result = dict(status='running', commands=[], return_code=None, failed_stage=None,
                  numerical_outcome_sha256=sha(output / 'rebuild_outcome.json'),
                  source_sha256=mapping['renderer_sha256'], outputs_stable=False,
                  scientific_success=False, output_sha256={})
    stage = 'saved_output_render'
    try:
        require(sha(ROOT / 'plot_hayward_corrected.py') == mapping['renderer_sha256'], 'Report source changed')
        report_python = executable(python)
        result['report_python'] = dict(path=report_python, sha256=sha(Path(report_python)))
        run_stage([report_python, ROOT / 'plot_hayward_corrected.py', '--data', output, '--output', output / 'report'],
                  stage, logs, env, result)
        stage = 'report_tex_pass_1'
        latex = executable('pdflatex')
        result['pdflatex'] = dict(path=latex, sha256=sha(Path(latex)))
        for number in (1, 2):
            stage = 'report_tex_pass_%d' % number
            run_stage([latex, '-no-shell-escape', '-interaction=nonstopmode', '-halt-on-error', 'report.tex'],
                      stage, logs, env, result, cwd=output / 'report')
        result.update(status='completed_saved_output_report', return_code=0)
    except BaseException as error:
        last = result['commands'][-1] if result['commands'] else {}
        code = last.get('return_code') if last.get('stage') == stage else None
        result.update(status='failed_preserved', failed_stage=stage, error=repr(error),
                      return_code=code if code not in (None, 0) else (130 if isinstance(error, KeyboardInterrupt) else 1))
    finally:
        result['finished_utc'] = utc()
        result['outputs_stable'] = all(r['outputs_stable'] for r in result['commands'])
        if result['outputs_stable']:
            result['output_sha256'] = {str(p.relative_to(output)): sha(p)
                                      for p in (output / 'report').rglob('*') if p.is_file()}
        require(sha(output / 'rebuild_outcome.json') == result['numerical_outcome_sha256'],
                'Report must not modify the numerical outcome')
        write_json(logs / 'execution.json', result)
        write_json(output / 'report_execution.json', result)
    return result['return_code']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path, help='Fresh immediate child of repository data/')
    parser.add_argument('--build', required=True, type=Path, help='Fresh immediate child of repository tmp/')
    parser.add_argument('--preparation-python', default=sys.executable, help='Interpreter with NumPy/Requests and compatible saved-weight arithmetic')
    parser.add_argument('--report-python', default=sys.executable, help='Interpreter with Matplotlib for the closed saved-output report')
    parser.add_argument('--cxx', default='c++', help='C++17 compiler with OpenMP')
    args = parser.parse_args()
    require(sys.platform.startswith('linux'), 'This owned process-group runner requires Linux /proc')
    output = fresh_path(args.output, ROOT / 'data')
    build = fresh_path(args.build, ROOT / 'tmp')
    preparation_python, cxx, cmake = [executable(value) for value in (args.preparation_python, args.cxx, 'cmake')]
    expected = json.loads((SOURCES / 'scientific_inputs.json').read_text())
    mapping = json.loads((SOURCES / 'source_mapping.json').read_text())
    verify(SOURCES, mapping['package_sha256'])
    require(sha(Path(__file__)) == mapping['entrypoint_sha256'], 'Entrypoint differs from selected source')
    pins = dict(expected['input_sha256'], **expected['provider_source_sha256'])
    verify(ROOT, pins)
    build.mkdir(parents=True)
    for name in ('logs', 'tmp', 'cache', 'cache/matplotlib', 'cache/texmf', 'cache/texmf-var', 'cache/texmf-config'):
        (build / name).mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    for name in ('PYTHONOPTIMIZE', 'PYTHONPATH', 'CFLAGS', 'CXXFLAGS', 'CPPFLAGS', 'LDFLAGS', 'CMAKE_PREFIX_PATH'):
        env.pop(name, None)
    env.update(PYTHONPATH=str(ROOT), PYTHONDONTWRITEBYTECODE='1', OMP_NUM_THREADS='4',
               OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1', LC_ALL='C', CXX=cxx,
               TMPDIR=str(build / 'tmp'), XDG_CACHE_HOME=str(build / 'cache'),
               MPLCONFIGDIR=str(build / 'cache/matplotlib'), TEXMFHOME=str(build / 'cache/texmf'),
               TEXMFVAR=str(build / 'cache/texmf-var'), TEXMFCONFIG=str(build / 'cache/texmf-config'))
    outcome = dict(status='running', started_utc=utc(), return_code=None, failed_stage=None,
                   commands=[], scientific_success=False, counts=None, accepted_states=[],
                   history_metrics_scope='pre-update', source_mapping_sha256=sha(SOURCES / 'source_mapping.json'),
                   input_sha256=pins, output_sha256={}, outputs_stable=False,
                   runtime={name: {'path': path, 'sha256': sha(Path(path))} for name, path in
                            (('entrypoint_python', sys.executable), ('preparation_python', preparation_python), ('cxx', cxx), ('cmake', cmake))},
                   limitations=['One independent authoritative subset and empirical CC weighting experiment.',
                                'No final accuracy, convergence, manuscript recovery or first-arrival claim follows from command completion.',
                                'No covariance calculation, new waveform measurement, network request or automatic retry.'])
    stage = 'preparation_runtime'
    previous = {}
    def interrupted(signum, frame):
        raise KeyboardInterrupt('Received signal %d; closing only owned child group' % signum)
    for sig in (signal.SIGINT, signal.SIGTERM):
        previous[sig] = signal.signal(sig, interrupted)
    try:
        write_json(build / 'execution.json', outcome)
        run_stage([preparation_python, '-c',
                   'import json,sys,numpy,requests; print(json.dumps(dict(python=sys.version, '
                   'numpy=numpy.__version__, requests=requests.__version__)))'], stage, build, env, outcome)
        outcome['preparation_runtime'] = json.loads((build / 'logs/preparation_runtime.stdout').read_text())
        stage = 'catalog_preparation'
        run_stage([preparation_python, SOURCES / 'prepare_hayward.py', '--selection', 'reproduction', '--output', output],
                  stage, build, env, outcome)
        stage = 'catalog_compatibility'
        catalog_compatibility(output, expected)
        stage = 'catalog_cc_assembly'
        assemble_cc(output, expected)
        shutil.copyfile(str(SOURCES / 'run.cfg'), str(output / 'run.cfg'))
        outcome['counts'] = expected['counts']
        outcome['prepared_input_sha256'] = {str(p.relative_to(output)): sha(p) for p in output.rglob('*') if p.is_file()}
        shutil.copytree(str(SOURCES / 'source'), str(build / 'source'))
        stage = 'cmake_configure'
        run_stage([cmake, '-S', build / 'source', '-B', build / 'build', '-DCMAKE_CXX_COMPILER=' + cxx,
                   '-DCMAKE_BUILD_TYPE=', '-DCMAKE_CXX_FLAGS=', '-DCMAKE_EXE_LINKER_FLAGS='], stage, build, env, outcome)
        stage = 'cmake_build'
        run_stage([cmake, '--build', build / 'build', '--parallel', '2'], stage, build, env, outcome)
        binary = build / 'build/dd'
        outcome['binary_sha256'] = sha(binary)
        outcome['built_source_sha256'] = {str(p.relative_to(build / 'source')): sha(p)
                                         for p in (build / 'source').rglob('*') if p.is_file()}
        require(outcome['built_source_sha256'] == mapping['numerical_source_sha256'],
                'Compiled source copy differs from the selected snapshot')
        outcome['build_record_sha256'] = {str(p.relative_to(build)): sha(p)
                                         for p in (build / 'build/CMakeCache.txt', build / 'build/CMakeFiles/dd.dir/flags.make',
                                                   build / 'build/CMakeFiles/dd.dir/link.txt') if p.is_file()}
        stage = 'runtime_libraries'
        run_stage([executable('ldd'), binary], stage, build, env, outcome)
        linked = (build / 'logs/runtime_libraries.stdout').read_text()
        require('not found' not in linked, 'Unresolved compiled runtime library')
        libraries = sorted(set(re.findall(r'(?:=>\s*)?(/[^\s(]+)', linked)))
        require(libraries, 'No compiled runtime libraries recorded')
        outcome['runtime_library_sha256'] = {name: sha(Path(name)) for name in libraries}
        verify(ROOT, pins)
        verify(SOURCES, mapping['package_sha256'])
        verify(output, outcome['prepared_input_sha256'])
        stage = 'dd_invert'
        run_stage([binary, 'invert', output / 'run.cfg', output, 'dd'], stage, build, env, outcome, native=True)
        outcome.update(status='completed_dd_attempt_pending_scientific_review', return_code=0)
    except BaseException as error:
        failed = outcome['commands'][-1] if outcome['commands'] else {}
        code = failed.get('return_code') if failed.get('stage') == stage else None
        outcome.update(status='failed_preserved', failed_stage=stage, error=repr(error),
                       return_code=code if code not in (None, 0) else (130 if isinstance(error, KeyboardInterrupt) else 1))
    finally:
        outcome['finished_utc'] = utc()
        outcome['outputs_stable'] = all(r['outputs_stable'] for r in outcome['commands'])
        if outcome['outputs_stable']:
            output.mkdir(exist_ok=True)
            try:
                outcome['accepted_states'], outcome['accepted_state_notes'] = accepted_states(output)
            except Exception as error:
                outcome['accepted_state_readback_error'] = repr(error)
                outcome['accepted_states'] = []
            outcome['output_sha256'] = {str(p.relative_to(output)): sha(p) for p in output.rglob('*') if p.is_file()}
            write_json(output / 'rebuild_outcome.json', outcome)
        write_json(build / 'execution.json', outcome)
        try:
            report_code = make_report(output, build, env, args.report_python, mapping) if outcome['outputs_stable'] else 1
        except BaseException as error:
            report_code = 130 if isinstance(error, KeyboardInterrupt) else 1
            write_json(build / 'report_failure.json', dict(status='failed_preserved', error=repr(error),
                       return_code=report_code, numerical_return_code=outcome['return_code']))
        finally:
            for sig, handler in previous.items():
                signal.signal(sig, handler)
    print(json.dumps({key: outcome[key] for key in ('status', 'return_code', 'failed_stage', 'outputs_stable')}, sort_keys=True))
    code = outcome['return_code'] if outcome['return_code'] != 0 else report_code
    return code if code >= 0 else 128 - code


if __name__ == '__main__':
    sys.exit(main())
