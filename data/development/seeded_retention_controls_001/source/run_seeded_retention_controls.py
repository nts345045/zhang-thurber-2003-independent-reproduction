#!/usr/bin/env python3
"""Run invented loader/retention controls after independent source approval."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
VARIANTS = ('seed_loaded_B', 'positive_curvature')


def need(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            digest.update(block)
    return digest.hexdigest()


def save(path, value):
    temporary = path.with_name(path.name + '.new')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    temporary.replace(path)


def utc():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def local(text):
    path = (ROOT / text).resolve()
    path.relative_to(ROOT)
    need(path != ROOT, 'A repository subdirectory/file is required')
    return path


def verify(path, expected):
    need(sha(path) == expected, 'Changed pinned file: ' + str(path.relative_to(ROOT)))


def records(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def inventory(directory):
    return {str(p.relative_to(directory)): sha(p) for p in sorted(directory.rglob('*')) if p.is_file()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepared', default='data/development/seeded_retention_prepared_001')
    parser.add_argument('--output', required=True)
    parser.add_argument('--build', required=True, help='Fresh repository-local temporary build directory')
    args = parser.parse_args()
    prepared_dir, out, build = [local(v) for v in (args.prepared, args.output, args.build)]
    need(not out.exists() and not build.exists(), 'Fresh output and build directories required')
    for a, b in ((out, build), (out, prepared_dir), (build, prepared_dir)):
        need(a != b and a not in b.parents and b not in a.parents, 'Disjoint data/build/source directories required')
    prepared_path = prepared_dir / 'prepared.json'
    prepared = json.loads(prepared_path.read_text())
    need(prepared['status'] == 'prepared_for_invented_controls_only', 'Unexpected prepared status')
    pins = dict(prepared['input_sha256'])
    pins[str(prepared_path.relative_to(ROOT))] = sha(prepared_path)
    for name, digest in prepared['output_sha256'].items():
        path = prepared_dir / name
        need(path.resolve().is_file() and prepared_dir in path.resolve().parents, 'Unsafe/missing prepared member')
        pins[str(path.relative_to(ROOT))] = digest
    for name in ('check_seeded_retention.cpp', 'run_seeded_retention_controls.py'):
        pins['diagnostics/' + name] = sha(ROOT / 'diagnostics' / name)
    for name, digest in pins.items():
        verify(local(name), digest)
    compiler = Path(prepared['compiler'])
    need(sha(compiler) == prepared['compiler_sha256'], 'Compiler differs from frozen preparation')
    for variant in VARIANTS:
        actual = inventory(prepared_dir / 'source' / variant)
        need(actual == prepared['variants'][variant]['source_sha256'], 'Changed variant inventory: ' + variant)
    old, new = [prepared_dir / 'source' / variant for variant in VARIANTS]
    need(set(inventory(old)) == set(inventory(new)), 'Variant source file rosters differ')
    changed = {name for name in inventory(old) if sha(old / name) != sha(new / name)}
    need(changed == set(prepared['between_variant_changed_files']) == {
        'src/core.hpp', 'diagnostics/observed_optimizer.hpp', 'diagnostics/extracted_retention.hpp'},
        'Unexpected variant difference')
    for name in ('src/core.hpp', 'diagnostics/observed_optimizer.hpp'):
        before, after = (old / name).read_text(), (new / name).read_text()
        marker = '      if (sy > 1e-14) {'
        need(before.count(marker) == 1 and after == before.replace(marker, '      if (sy > 0) {', 1),
             'Retention change is not the one declared literal: ' + name)
    for variant, expression in zip(VARIANTS, ('sy > 1e-14', 'sy > 0')):
        need((prepared_dir / 'source' / variant / 'diagnostics/extracted_retention.hpp').read_text() ==
             'bool extracted_retention(double sy) { return ' + expression + '; }\n',
             'Extracted predicate differs from actual trace condition')

    out.mkdir(parents=True)
    build.mkdir(parents=True)
    execution = dict(status='preparing', started_utc=utc(), pid=os.getpid(), commands=[],
                     command=[str(Path(__file__).resolve().relative_to(ROOT))] + sys.argv[1:])
    save(out / 'execution.json', execution)
    try:
        shutil.copytree(str(prepared_dir / 'source'), str(out / 'source'))
        for name in ('check_seeded_retention.cpp', 'run_seeded_retention_controls.py'):
            shutil.copyfile(str(ROOT / 'diagnostics' / name), str(out / 'source' / name))
        shutil.copyfile(str(prepared_path), str(out / 'prepared_input.json'))
        (out / 'inputs').mkdir()
        # An invented stale-file control uses the same verifier as real pins.
        before = out / 'inputs/hash_before.txt'
        after = out / 'inputs/hash_after.txt'
        before.write_text('invented original\n')
        after.write_text('invented changed\n')
        verify(before, sha(before))
        rejected = False
        try:
            verify(after, sha(before))
        except ValueError:
            rejected = True
        need(rejected, 'Stale hash was accepted')
        hash_controls = {'matching_hash_passes': True, 'changed_hash_rejected': rejected,
                         'original_sha256': sha(before), 'changed_sha256': sha(after)}
        env = dict(os.environ, OMP_NUM_THREADS='1', PYTHONDONTWRITEBYTECODE='1',
                   TMPDIR=str(build), MPLCONFIGDIR=str(ROOT / 'tmp/matplotlib'))

        def command(argv, label):
            log = out / (label + '.log')
            item = dict(argv=argv, label=label, started_utc=utc())
            execution['commands'].append(item)
            execution['status'] = 'running'
            save(out / 'execution.json', execution)
            with log.open('wb') as stream:
                result = subprocess.run(argv, cwd=str(ROOT), env=env, stdout=stream, stderr=subprocess.STDOUT)
            item.update(return_code=result.returncode, completed_utc=utc(), log_sha256=sha(log))
            save(out / 'execution.json', execution)
            need(result.returncode == 0, 'Command failed; preserved ' + label + '.log')

        variants = {}
        for variant in VARIANTS:
            source = out / 'source' / variant
            binary = build / ('check_' + variant)
            command([str(compiler), '-std=gnu++17', '-O3', '-Wall', '-Wextra', '-Wpedantic', '-fopenmp',
                     '-DAUDIT_PRODUCTION_HYBRID', '-DAUDIT_CONE_METRIC',
                     '-I' + str((source / 'diagnostics').relative_to(ROOT)),
                     str((out / 'source/check_seeded_retention.cpp').relative_to(ROOT)),
                     '-o', str(binary.relative_to(ROOT)), '-lstdc++fs'], 'compile_' + variant)
            target = out / variant
            command([str(binary.relative_to(ROOT)), str(target.relative_to(ROOT)), variant], 'run_' + variant)
            checks = records(target / 'checks.csv')
            need(checks and len({c['check'] for c in checks}) == len(checks) and
                 all(c['passed'] == '1' for c in checks), 'Incomplete or failed invented checks')
            variants[variant] = dict(checks_passed=len(checks), binary_path=str(binary.relative_to(ROOT)),
                                     binary_sha256=sha(binary), trace=records(target / 'trace_summary.csv')[0])
        parity = {}
        for name in ('candidate_bits.txt', 'subnormal_parse_behavior.txt', 'ray_bits.txt', 'history.csv', 'trace_summary.csv'):
            hashes = [sha(out / variant / name) for variant in VARIANTS]
            need(hashes[0] == hashes[1], 'B/C parity failed: ' + name)
            parity[name] = hashes[0]
        # Actual B history proves the one accepted pair exceeds the old cutoff.
        history = records(out / 'seed_loaded_B/history.csv')
        accepted = [r for r in history if r['phase'] == 'accepted']
        need(len(accepted) == 1 and accepted[0]['curvature_pair_accepted'] == '1',
             'The B parity fixture does not satisfy the old-retained-pair premise')
        old_cases, new_cases = [records(out / v / 'retention_cases.csv') for v in VARIANTS]
        need([r['case'] for r in old_cases] == [r['case'] for r in new_cases], 'Retention case roster differs')
        for a, b in zip(old_cases, new_cases):
            need({k: v for k, v in a.items() if k != 'actual_keep'} ==
                 {k: v for k, v in b.items() if k != 'actual_keep'}, 'Retention arithmetic changed')
        cases = {r['case']: r for r in new_cases}
        need(cases['minimum_subnormal']['actual_keep'] == '1' and
             cases['minimum_subnormal']['reciprocal_finite'] == '0' and
             cases['positive_infinity']['actual_keep'] == '1', 'Known unsafe generalization evidence missing')
        for name, digest in pins.items():
            verify(local(name), digest)
        for variant in VARIANTS:
            need(inventory(out / 'source' / variant) == prepared['variants'][variant]['source_sha256'],
                 'Frozen compiled source changed')
        for name in ('check_seeded_retention.cpp', 'run_seeded_retention_controls.py'):
            verify(out / 'source' / name, pins['diagnostics/' + name])
        need(sha(compiler) == prepared['compiler_sha256'], 'Compiler changed during controls')
        execution.update(status='completed', return_code=0, completed_utc=utc())
        save(out / 'execution.json', execution)
        summary = dict(status='passed', prepared_sha256=sha(prepared_path), input_sha256=pins,
            source_sha256={str(p.relative_to(out / 'source')): sha(p)
                           for p in sorted((out / 'source').rglob('*')) if p.is_file()},
            variants=variants, hash_controls=hash_controls, exact_between_variant_parity_sha256=parity,
            threads=1, compiler=str(compiler), compiler_sha256=sha(compiler),
            output_sha256=inventory(out), limitations=[
                'Only invented Candidates and a homogeneous invented seeded trace were executed; no field was constructed.',
                'Raw Candidate round-trip tests cover the stated normal finite binary64 values. Subnormal parsing is reported separately.',
                'The saved post-resampling frame is structurally validated, not returned or recomputed by the loader.',
                'Trace performs its original resampling from the loaded raw seed. Native five-file replay parity remains required.',
                'The one-update trace retains its sole pair under the old cutoff; it does not test subsequent use of newly retained tiny curvature.',
                'Accepting positive curvature alone is unsafe: the minimum subnormal reciprocal overflows, and positive infinity passes both predicates.',
                'Cancellation and underflow can erase exact positive curvature; neither Boolean rule certifies a mathematical curvature sign.',
                'No optimizer correction, native outcome, convergence promotion, inverse calculation, or production authorization is claimed.'])
        save(out / 'summary.json', summary)
        print(str(out / 'summary.json'), flush=True)
    except BaseException as error:
        save(out / 'failure.json', dict(error=repr(error), recorded_utc=utc(), output_sha256=inventory(out)))
        execution.update(status='failed', completed_utc=utc(), failure_sha256=sha(out / 'failure.json'))
        save(out / 'execution.json', execution)
        raise


if __name__ == '__main__':
    main()
