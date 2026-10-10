#!/usr/bin/env python3
"""Observe a frozen Loma initial failure without changing its numerical method."""
import argparse
import csv
import difflib
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def records(path):
    opener = gzip.open if path.suffix == '.gz' else open
    with opener(str(path), 'rt', newline='') as stream:
        return list(csv.DictReader(stream))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--comparison', required=True)
    parser.add_argument('--pair', type=int, required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--build', required=True)
    args = parser.parse_args()
    os.chdir(str(ROOT))
    comparison, out, build = [(ROOT / value).resolve() for value in
                              (args.comparison, args.output, args.build)]
    for path in (comparison, out, build):
        path.relative_to(ROOT)
        require(path != ROOT, 'Cannot use repository root')
    for a, b in ((out, comparison), (build, comparison), (out, build)):
        require(a != b and a not in b.parents and b not in a.parents,
                'Diagnostic, build and frozen evidence must be disjoint')
    require(not out.exists() and not build.exists(), 'Fresh output/build required')
    summary = dict(status='preparing', started_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                   scope='Observation-only frozen initial ray; no solver change or inversion',
                   pair_index=args.pair, commands=[], input_sha256={})
    out.mkdir(parents=True)
    build.mkdir(parents=True)

    def save():
        temp = out / 'summary.json.new'
        temp.write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n')
        temp.replace(out / 'summary.json')

    def copy(path, target, expected=None):
        digest = sha(path)
        require(expected is None or digest == expected, 'Changed input: ' + str(path))
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(str(path), str(target))
        require(sha(target) == digest, 'Copy mismatch')
        summary['input_sha256'][str(path.relative_to(ROOT))] = digest

    def command(name, argv):
        record = dict(stage=name, command=[str(p.relative_to(ROOT)) if isinstance(p, Path) else p
                                          for p in argv], status='running')
        summary['commands'].append(record)
        started = time.time()
        with (out / (name + '_stdout.log')).open('w') as stdout, \
             (out / (name + '_stderr.log')).open('w') as stderr:
            child = subprocess.Popen(record['command'], stdout=stdout, stderr=stderr,
                                     env=dict(os.environ, OMP_NUM_THREADS='1', TMPDIR=str(ROOT / 'tmp')))
            record['pid'] = child.pid
            save()
            code = child.wait()
        record.update(status='completed', return_code=code, seconds=time.time() - started)
        save()
        require(code == 0, name + ' failed')

    try:
        assessment = json.loads((comparison / 'summary.json').read_text())
        ledger = json.loads((comparison / 'execution.json').read_text())
        require(ledger['status'] == 'completed' and ledger['summary_sha256'] == sha(comparison / 'summary.json'),
                'Require completed hash-bound saved comparison')
        require(assessment['status'] == 'comparison_complete', 'Comparison incomplete')
        require(any(f['comparison_row'] == args.pair for f in assessment['failures']), 'Select a recorded failed ray')
        for name, digest in assessment['output_sha256'].items():
            path = (comparison / name).resolve()
            path.relative_to(comparison)
            require(sha(path) == digest, 'Changed comparison artifact: ' + name)
        frozen = comparison / 'inputs/preflight'
        manifest = json.loads((frozen / 'preflight_run_manifest.json').read_text())
        require(sha(ROOT / manifest['binary']) == manifest['binary_sha256'], 'Frozen binary changed')
        require(sha(Path(manifest['compiler'])) == manifest['compiler_sha256'], 'Compiler changed')
        for name in ('initial_events.csv', 'stations.csv', 'initial_grid.csv', 'run.cfg', 'preflight_run_manifest.json'):
            copy(frozen / name, out / 'inputs' / name, manifest['input_sha256'].get(name))
        for name in ('summary.json', 'execution.json'):
            copy(comparison / name, out / 'inputs' / ('comparison_' + name))
        events = records(frozen / 'initial_events.csv')
        stations = records(frozen / 'stations.csv')
        require(0 <= args.pair < len(events) * len(stations), 'Pair outside native roster')
        i, k = divmod(args.pair, len(stations))
        selected = records(frozen / 'dd_preflight_ray_status.csv.gz')[args.pair]
        require((selected['event'], selected['station']) == (str(i), str(k)),
                'Not the selected native failed comparison row')
        original = dict(selected)
        for prefix, native in [('source_', events[i]), ('receiver_', stations[k])]:
            for key, value in native.items():
                if key not in ('id', 'x', 'y', 'z', 't'):
                    require(selected[prefix + key] == value, 'Native metadata mismatch: ' + prefix + key)
                selected['native_' + prefix + key] = value
            for axis in 'xyz':
                require(float(selected[prefix + axis]) == float(format(float(native[axis]), '.12g')),
                        'Rounded coordinate mismatch')
                selected[prefix + axis + '_km'] = native[axis]
        selected['observation_index'] = str(args.pair)
        selected['observation_index_basis'] = 'local original event-times-receiver pair index, not a provider observation ID'
        identified = out / 'identified_ray.csv'
        with identified.open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(selected), lineterminator='\n')
            writer.writeheader()
            writer.writerow(selected)
        cfg = {}
        for line in (frozen / 'run.cfg').read_text().splitlines():
            words = line.split('#', 1)[0].split()
            if words:
                require(len(words) == 2, 'Malformed frozen config')
                cfg[words[0]] = float(words[1])
        require(cfg['ray_initializer'] == 1 and cfg['ray_iterations'].is_integer(), 'Unexpected frozen forward settings')
        source_root = ROOT / manifest['source_directory']
        for name, digest in manifest['source_sha256'].items():
            if name.startswith('src/'):
                copy(source_root / name, out / 'source' / name, digest)
        for name in ('check_ray_stopping.cpp', 'run_ray_stopping.py', 'first_arrival_fmm.hpp', 'observe_loma_initial_failure.py'):
            copy(ROOT / 'diagnostics' / name, out / 'source/diagnostics' / name)
        recipe = (out / 'source/diagnostics/run_ray_stopping.py').read_text()
        context = dict(args=SimpleNamespace(production_hybrid=True, cone_hybrid=False,
                                           cone_metric=False, reduced_metric=False), pure_metric=False)
        exec(recipe[recipe.index('def instrument(source):'):recipe.index('\nobserved_trace = ')], context)
        core = (out / 'source/src/core.hpp').read_text()
        start = core.index('Ray trace(const Grid &g,')
        trace = core[start:core.index('\nstruct Entry {', start)]
        observed = context['instrument'](trace)
        (out / 'source/diagnostics/observed_optimizer.hpp').write_text(observed)
        (out / 'instrumentation.diff').write_text(''.join(difflib.unified_diff(
            trace.splitlines(True), observed.splitlines(True), fromfile='frozen_trace', tofile='observed_trace')))
        driver_path = out / 'source/diagnostics/check_ray_stopping.cpp'
        driver_original = driver_path.read_text()
        driver = driver_original
        replacements = [('if(argc!=6)', 'if(argc!=7)'), ('OUT BUDGETS SPACINGS', 'OUT BUDGETS SPACINGS FIELD_SPACING'),
                        ('pos("dd_source_")', 'pos("source_")'),
                        ('first_arrival::Field field(g,b,.5,2,true);', 'first_arrival::Field field(g,b,std::stod(argv[6]),2,true);')]
        for old, new in replacements:
            require(driver.count(old) == 1, 'Observer driver adaptation point changed')
            driver = driver.replace(old, new, 1)
        driver_path.write_text(driver)
        (out / 'driver_adaptation.diff').write_text(''.join(difflib.unified_diff(
            driver_original.splitlines(True), driver.splitlines(True), fromfile='original_driver', tofile='loma_driver')))
        summary.update(source_sha256={str(p.relative_to(out / 'source')): sha(p) for p in (out / 'source').rglob('*') if p.is_file()},
                       frozen_binary_sha256=manifest['binary_sha256'], compiler=manifest['compiler'],
                       compiler_sha256=manifest['compiler_sha256'], path_spacing_km=cfg['ray_spacing'],
                       field_spacing_km=cfg['fmm_spacing'], maximum_updates=int(cfg['ray_iterations']),
                       native_context=selected, status='observing')
        binary = build / 'observe'
        command('compile', [manifest['compiler'], '-std=gnu++17', '-O3', '-Wall', '-Wextra', '-Wpedantic', '-fopenmp',
                            '-DAUDIT_PRODUCTION_HYBRID', '-DAUDIT_CONE_METRIC', driver_path, '-lstdc++fs', '-o', binary])
        summary['binary_sha256'] = sha(binary)
        command('observe', [binary, out / 'inputs/initial_grid.csv', identified, out,
                            str(int(cfg['ray_iterations'])), str(cfg['ray_spacing']), str(cfg['fmm_spacing'])])
        values = records(out / 'results.csv')
        require(len(values) == 2 and all(r['logged_matches_unobserved_variant'] == '1' for r in values),
                'Observation changed the unmodified numerical result')
        best = min(values, key=lambda r: float(r['time_s']))
        for key, original_key in [('time_s', 'ray_time'), ('projected_gradient', 'ray_projected_gradient'),
                                  ('raw_gradient', 'ray_raw_gradient'), ('source_dx', 'source_dx'),
                                  ('source_dy', 'source_dy'), ('source_dz', 'source_dz')]:
            require(float(format(float(best[key]), '.12g')) == float(original[original_key]),
                    'Selected result differs from frozen full preflight: ' + key)
        for key, original_key in [('updates', 'ray_iterations'), ('converged', 'ray_converged'),
                                  ('merged_nodes', 'ray_merged_nodes'), ('path_nodes', 'ray_path_points')]:
            require(best[key] == original[original_key], 'Selected ray status differs: ' + key)
        require((best['initialization'] == 'fmm') == (original['ray_selected_fmm_seed'] == '1'), 'Different selected seed')
        for name in ('results.csv', 'history.csv', 'paths.csv', 'path_gradient_checks.csv', 'cone_metric.csv'):
            sidecar = dict(file=name, file_sha256=sha(out / name), join_key='observation_index',
                           join_value=str(args.pair), native_context=selected,
                           context_csv='identified_ray.csv', context_sha256=sha(identified),
                           basis='Synthetic initial coordinates retain provider catalog/receiver identities; no provider pick is invented')
            (out / (name + '.identifiers.json')).write_text(json.dumps(sidecar, indent=2) + '\n')
        for name, digest in summary['input_sha256'].items():
            require(sha(ROOT / name) == digest, 'Input changed during observation: ' + name)
        summary.update(status='completed_with_original_flags_preserved', results=values,
                       selected_full_preflight_result_matches=True, observed_paths_and_arrays_match_unobserved=True,
                       limitations=['One original failed ray at unchanged spacing and update budget; no refinement or correction.',
                                    'The hooks record existing iterations; finite-difference checks hold polygon nodes fixed.',
                                    'Original flags are retained regardless of continuous-reference time or derivative accuracy.'])
        summary['output_sha256'] = {str(p.relative_to(out)): sha(p) for p in out.rglob('*')
                                   if p.is_file() and p.name not in ('summary.json', 'summary.json.new')}
    except BaseException as error:
        summary.update(status='failed', failure=repr(error), finished_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
        save()
        raise
    summary['finished_utc'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    save()
    print(str(out / 'summary.json'), flush=True)


if __name__ == '__main__':
    main()
