#!/usr/bin/env python3
"""Freeze invented ordered-ray/identity parity and refined-cache size checks."""
import argparse
import csv
import difflib
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--build', required=True)
    args = parser.parse_args()
    out, build = [(ROOT / p).resolve() for p in (args.output, args.build)]
    for p in (out, build):
        p.relative_to(ROOT); p.mkdir(parents=True)
    summary = dict(status='preparing', commands=[], checks=[],
                   scope='Invented diagnostic cache/output controls; no real preflight or inverse calculation')

    def save():
        (out / 'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n')

    def check(name, value):
        summary['checks'].append(dict(name=name, passed=bool(value)))
        if not value:
            raise ValueError(name)

    def run(label, command, success=True, threads=4):
        command = [str(p.relative_to(ROOT)) if isinstance(p, Path) else str(p) for p in command]
        entry = dict(label=label, command=command, threads=threads)
        summary['commands'].append(entry); save()
        start = time.time()
        with (out / (label + '_stdout.log')).open('w') as stdout, (out / (label + '_stderr.log')).open('w') as stderr:
            result = subprocess.run(['/usr/bin/time', '-v', '-o', str(out / (label + '_resources.txt'))] + command,
                cwd=str(ROOT), stdout=stdout, stderr=stderr,
                env=dict(os.environ, OMP_NUM_THREADS=str(threads), OPENBLAS_NUM_THREADS='1',
                         PYTHONDONTWRITEBYTECODE='1', TMPDIR=str(ROOT / 'tmp')))
        entry.update(return_code=result.returncode, elapsed_seconds=time.time()-start)
        resource = (out / (label + '_resources.txt')).read_text()
        entry['maximum_resident_set_KiB'] = int(next(line.split(':')[-1] for line in resource.splitlines()
            if 'Maximum resident set size' in line))
        save()
        check(label + '_exit', (result.returncode == 0) == success)
        print(label, result.returncode, round(entry['elapsed_seconds'], 3), flush=True)

    try:
        commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=str(ROOT), universal_newlines=True).strip()
        summary['baseline_commit'] = commit
        sources = ['src/' + p.name for p in sorted((ROOT / 'src').iterdir()) if p.is_file()]
        sources += ['diagnostics/check_raycheck_batching.cpp', 'diagnostics/run_raycheck_batching.py']
        summary['maintained_source_sha256'] = {name: sha(ROOT / name) for name in sources}
        needle = '    Ray b = configured_trace(g, e[i].p, stations[k].p, refined, refined_fields);'
        instrumentation = needle + '\n    std::cerr << "diagnostic_refined_cache " << n << \' \' << refined_fields.fields.size() << \'\\n\';'
        for mode in ('baseline', 'current'):
            snapshot, compiled = out / 'source' / mode, build / mode
            for name in sources:
                target = snapshot / name; target.parent.mkdir(parents=True, exist_ok=True)
                content = (ROOT / name).read_bytes()
                if mode == 'baseline' and name.startswith('src/'):
                    content = subprocess.check_output(['git', 'show', commit + ':' + name], cwd=str(ROOT))
                target.write_bytes(content)
            shutil.copytree(str(snapshot), str(compiled))
            path = compiled / 'src/main.cpp'; original = path.read_text()
            check(mode + '_unique_diagnostic_insertion', original.count(needle) == 1)
            changed = original.replace(needle, instrumentation)
            path.write_text(changed)
            (out / (mode + '_diagnostic_access.diff')).write_text(''.join(difflib.unified_diff(
                original.splitlines(True), changed.splitlines(True), fromfile='frozen/src/main.cpp',
                tofile='diagnostic/src/main.cpp')))
            flags = ['-DBASELINE'] if mode == 'baseline' else []
            run('compile_' + mode, ['g++', '-std=c++17', '-O3', '-Wall', '-Wextra', '-Wpedantic', '-fopenmp'] +
                flags + [compiled / 'diagnostics/check_raycheck_batching.cpp', '-lstdc++fs', '-o', build / (mode + '_check')])
            summary[mode + '_compiled_source_sha256'] = {str(p.relative_to(compiled)):sha(p) for p in compiled.rglob('*') if p.is_file()}
            summary[mode + '_binary_sha256'] = sha(build / (mode + '_check'))
        parity_names = ['initial_ray_convergence.csv', 'initial_ray_derivatives.csv',
                        'initial_ray_identifiers.csv', 'identified_failure.txt']
        groups = {}
        for mode, batches in [('baseline', [-1]), ('current', [-1, 0, 1, 2, 4])]:
            for threads in (1, 4):
                for batch in batches:
                    label = '{}_b{}_t{}'.format(mode, batch, threads)
                    target = out / label; target.mkdir()
                    run(label, [build / (mode + '_check'), target, batch, threads], threads=threads)
                    with (target / 'checks.csv').open() as stream:
                        checks = list(csv.DictReader(stream))
                    check(label + '_component_checks', checks and all(r['passed'] == '1' for r in checks))
                    groups[label] = {name: sha(target / name) for name in parity_names}
                    cache = [list(map(int, line.split()[1:])) for line in (out / (label + '_stderr.log')).read_text().splitlines()
                             if line.startswith('diagnostic_refined_cache ')]
                    check(label + '_ordered_cache_census', [r[0] for r in cache] == list(range(16)))
                    count = [r[1] for r in cache]
                    check(label + '_cache_limit', all(n == 5 for n in count) if batch <= 0 else
                          max(count) == min(batch, 5) and all(1 <= n <= batch for n in count))
                    if batch == 4:
                        check(label + '_noncontiguous_repeat_batch', count == [4]*12 + [3]*4)
        control = groups['baseline_b-1_t1']
        check('all_frozen_default_and_B0_B1_B2_B4_outputs_bitwise_equal', all(r == control for r in groups.values()))
        summary['parity_groups'] = groups
        invalid = ['-1', '0.5', 'nan', 'inf', '-inf', '1e999', '2147483648', '2x', '', '2 extra',
                   'nan\nraycheck_receiver_batch 2']
        base = out / 'current_b0_t4'
        for i, token in enumerate(invalid):
            config = out / ('invalid_' + str(i) + '.cfg')
            config.write_text('raycheck_receiver_batch ' + token + '\n')
            label = 'invalid_token_' + str(i)
            run(label, [build / 'current_check', '--solver', 'raycheck', config, out / 'missing_inputs', 'initial'], False)
            check(label + '_rejects_before_input_access', 'raycheck_receiver_batch' in (out / (label + '_stderr.log')).read_text())
        valid = out / 'valid_comment_duplicate.cfg'
        valid.write_text((base / 'fixture.cfg').read_text() + 'raycheck_receiver_batch 1\nraycheck_receiver_batch 2.0 # exact integer\n')
        copied = out / 'valid_cli'; shutil.copytree(str(base), str(copied))
        run('valid_cli', [build / 'current_check', '--solver', 'raycheck', valid, copied, 'initial'])
        check('valid_comments_duplicates_preserve_outputs', all(sha(copied/n) == control[n] for n in parity_names[:3]))
        for mode in ('baseline', 'current'):
            target = out / ('geometry_' + mode); shutil.copytree(str(base), str(target))
            run('geometry_' + mode, [build / (mode + '_check'), '--solver', 'geometrycheck', valid, target, 'initial'])
        check('geometry_only_identifiers_and_FDs_bitwise_equal', all(sha(out / 'geometry_baseline' / ('geometry_' + n)) ==
            sha(out / 'geometry_current' / ('geometry_' + n)) for n in parity_names[:3]))
        check('maintained_sources_unchanged', all(sha(ROOT/name) == digest for name,digest in summary['maintained_source_sha256'].items()))
        summary.update(status='passed', limitations=[
            'Only copied diagnostic main.cpp files add a cache-count stderr statement after the unchanged refined trace; no arithmetic is changed.',
            'Measured RSS is from small invented fixtures and is not a Loma peak or a 128 GiB guarantee.',
            'Batching preserves mathematical inputs and ordered output; it does not validate global first-arrival accuracy or nonlinear inversion.'])
    except BaseException as error:
        summary.update(status='failed', failure=str(error)); save(); raise
    summary['output_sha256'] = {str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file() and p.name != 'summary.json'}
    save(); print(out / 'summary.json', flush=True)


if __name__ == '__main__':
    main()
