#!/usr/bin/env python3
"""Freeze and run approved invented C/D curvature controls; never native rays."""
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
PREPARED_SHA = 'eff5bffcb2f37e38e6bc646bc5aa425201b30b93de542ec8430ec2e1b341f524'


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


def local(name):
    path = (ROOT / name).resolve()
    path.relative_to(ROOT)
    need(path != ROOT, 'Repository subpath required')
    return path


def verify(path, digest):
    need(sha(path) == digest, 'Changed pin: ' + str(path.relative_to(ROOT)))


def inventory(directory):
    return {str(p.relative_to(directory)): sha(p) for p in sorted(directory.rglob('*')) if p.is_file()}


def records(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def extracted_caller(core):
    begin = core.index('    Vec q;\n    const bool usable_memory = usable_lbfgs_ray_direction(')
    end = core.index('    double step = 1, newT = T;', begin)
    direction = core[begin:end]
    need('q = cone_ray_direction(g, p, grad);' in direction and
         'S.clear();' in direction and '!(slope < 0)' in direction,
         'Expected existing fallback and final strict-descent block')
    begin = core.index('      double sy = dot(s, y);')
    end = core.index('    }\n    p = std::move(trial);', begin)
    admission = core[begin:end]
    need(admission.count('usable_ray_curvature(') == 1 and
         admission.count('rho.push_back(reciprocal);') == 1,
         'Expected actual admission block')
    return ('// Byte-extracted D caller blocks; no Ray or convergence claim.\n'
            'Vec fixture_actual_direction(const Grid &g,const std::vector<P> &p,const Vec &grad,\n'
            '    std::vector<Vec> &S,std::vector<Vec> &Y,Vec &rho) {\n' + direction +
            '  return q;\n}\n'
            'void fixture_actual_admission(const Vec &s,const Vec &y,\n'
            '    std::vector<Vec> &S,std::vector<Vec> &Y,Vec &rho) {\n' + admission + '}\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepared', default='data/development/usable_ray_curvature_prepared_001')
    parser.add_argument('--output', required=True)
    parser.add_argument('--build', required=True)
    args = parser.parse_args()
    prepared_dir, out, build = [local(v) for v in (args.prepared, args.output, args.build)]
    need(not out.exists() and not build.exists(), 'Fresh output/build required')
    for a, b in ((out, build), (out, prepared_dir), (build, prepared_dir)):
        need(a != b and a not in b.parents and b not in a.parents, 'Disjoint output/build/source required')
    prepared_path = prepared_dir / 'prepared.json'
    verify(prepared_path, PREPARED_SHA)
    prepared = json.loads(prepared_path.read_text())
    need(prepared['status'] == 'prepared_invented_controls_only', 'Unexpected prepared state')
    pins = {str(prepared_path.relative_to(ROOT)): PREPARED_SHA}
    for name, digest in prepared['source_sha256'].items():
        path = (prepared_dir / name).resolve()
        need(prepared_dir in path.parents, 'Unsafe prepared member')
        pins[str(path.relative_to(ROOT))] = digest
    baseline = ROOT / 'data/development/loma_positive_curvature_native_001'
    for name, digest in prepared['baseline_source_sha256'].items():
        pins[str((baseline / name).relative_to(ROOT))] = digest
    pins[str((baseline / 'summary.json').relative_to(ROOT))] = prepared['baseline_summary_sha256']
    pins[str((baseline / 'review.json').relative_to(ROOT))] = prepared['baseline_review_sha256']
    for name in ('usable_ray_curvature.hpp', 'prepare_usable_ray_curvature.py',
                 'check_usable_ray_curvature.cpp', 'run_usable_ray_curvature_checks.py'):
        pins['diagnostics/' + name] = sha(ROOT / 'diagnostics' / name)
    need(pins['diagnostics/usable_ray_curvature.hpp'] == prepared['helper_sha256'] and
         pins['diagnostics/prepare_usable_ray_curvature.py'] == prepared['preparer_sha256'],
         'Maintained helper/preparer drifted')
    for name, digest in pins.items():
        verify(local(name), digest)
    old, new = [prepared_dir / name for name in ('C', 'D')]
    old_files, new_files = inventory(old), inventory(new)
    need(set(new_files) - set(old_files) == {'diagnostics/usable_ray_curvature.hpp'} and
         not set(old_files) - set(new_files), 'Unexpected source roster difference')
    need({name for name in old_files if old_files[name] != new_files[name]} ==
         {'src/core.hpp', 'diagnostics/observed_optimizer.hpp'}, 'Unexpected C/D change')
    for name, digest in prepared['baseline_source_sha256'].items():
        need(old_files[name[len('source/'):]] == digest, 'C is not the frozen positive-only baseline')
    compiler_text = shutil.which('g++')
    need(compiler_text is not None, 'g++ required')
    compiler = Path(compiler_text).resolve()
    compiler_sha = sha(compiler)
    out.mkdir(parents=True)
    build.mkdir(parents=True)
    execution = dict(status='preparing', started_utc=utc(), pid=os.getpid(), commands=[],
                     command=[str(Path(__file__).resolve().relative_to(ROOT))] + sys.argv[1:])
    save(out / 'execution.json', execution)
    try:
        for name in ('C', 'D'):
            shutil.copytree(str(prepared_dir / name), str(out / 'source' / name))
        fixture = out / 'source' / 'fixture'
        fixture.mkdir()
        for name in ('usable_ray_curvature.hpp', 'check_usable_ray_curvature.cpp', 'run_usable_ray_curvature_checks.py'):
            shutil.copyfile(str(ROOT / 'diagnostics' / name), str(fixture / name))
        generated = extracted_caller((new / 'src/core.hpp').read_text())
        (fixture / 'extracted_usable_caller.hpp').write_text(generated)
        shutil.copyfile(str(prepared_path), str(out / 'prepared_input.json'))
        source_pins = {str(p.relative_to(ROOT)): sha(p) for p in sorted((out / 'source').rglob('*')) if p.is_file()}
        env = dict(os.environ, OMP_NUM_THREADS='1', PYTHONDONTWRITEBYTECODE='1', TMPDIR=str(build))

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

        command([str(compiler), '--version'], 'compiler_version')
        variants = {}
        for variant in ('C', 'D'):
            binary = build / ('check_' + variant)
            argv = [str(compiler), '-std=gnu++17', '-O3', '-Wall', '-Wextra', '-Wpedantic', '-fopenmp',
                    '-DAUDIT_PRODUCTION_HYBRID', '-DAUDIT_CONE_METRIC']
            if variant == 'D':
                argv.append('-DUSABLE_VARIANT_D')
            argv += ['-I' + str((out / 'source' / variant / 'diagnostics').relative_to(ROOT)),
                     '-I' + str(fixture.relative_to(ROOT)),
                     str((fixture / 'check_usable_ray_curvature.cpp').relative_to(ROOT)),
                     '-o', str(binary.relative_to(ROOT)), '-lstdc++fs']
            command(argv, 'compile_' + variant)
            command([str(binary.relative_to(ROOT)), str((out / variant).relative_to(ROOT))], 'run_' + variant)
            checks = records(out / variant / 'checks.csv')
            need(checks and len({r['check'] for r in checks}) == len(checks) and
                 all(r['passed'] == '1' for r in checks), 'Failed/incomplete invented checks')
            variants[variant] = dict(checks_passed=len(checks), binary=str(binary.relative_to(ROOT)),
                                     binary_sha256=sha(binary), rays=records(out / variant / 'rays.csv'))
        # Both component builds use the identical D helper/caller. C production
        # trace remains unmodified and does not call that helper.
        parity = {}
        names = ['pair_cases.csv', 'checks.csv', 'rays.csv']
        for case in ('homogeneous_seeded', 'homogeneous_direct', 'affine_seeded', 'affine_direct'):
            names += [case + '_ray_bits.txt', case + '_history.csv']
        for name in names:
            hashes = [sha(out / variant / name) for variant in ('C', 'D')]
            need(hashes[0] == hashes[1], 'C/D exact parity failed: ' + name)
            parity[name] = hashes[0]
        pair_cases = {r['case']: r for r in records(out / 'D/pair_cases.csv')}
        need(pair_cases['exact_negative_computed_positive']['usable'] == '1',
             'Required exact-sign limitation missing')
        for name, digest in pins.items():
            verify(local(name), digest)
        for name, digest in source_pins.items():
            verify(local(name), digest)
        need(inventory(out / 'source/C') == old_files and inventory(out / 'source/D') == new_files,
             'Compiled variant snapshot changed')
        need((fixture / 'extracted_usable_caller.hpp').read_text() == extracted_caller((new / 'src/core.hpp').read_text()),
             'Extracted caller changed')
        need(sha(compiler) == compiler_sha, 'Compiler changed')
        execution.update(status='completed', return_code=0, completed_utc=utc())
        save(out / 'execution.json', execution)
        summary = dict(status='passed', prepared_sha256=PREPARED_SHA, input_sha256=pins,
            source_sha256=source_pins, variants=variants, exact_parity_sha256=parity,
            compiler=str(compiler), compiler_sha256=compiler_sha, threads=1,
            output_sha256=inventory(out), limitations=[
                'Invented arithmetic and four invented seeded/direct rays only; no native input, FMM field, or inverse calculation.',
                'All component helper/caller controls use the frozen D logic; actual C trace remains unchanged.',
                'Usability checks certify representability of checked computed quantities, not the exact sign or information in curvature.',
                'An exact negative dot with a positive computed sum is deliberately retained; cancellation and underflow are not repaired.',
                'Zero finite slope may be arithmetically usable but the unchanged caller still rejects it as a search direction.',
                'The deliberately inconsistent finite reciprocal fixture tests defensive use-time rejection, not a reachable admitted memory.',
                'Bitwise full-Ray and CSV history parity is bounded to the stated invented geometries; native C/D parity remains untested.',
                'No existing ray flags, action, source derivatives, Armijo checks, stopping criteria, or production files are changed.'])
        save(out / 'summary.json', summary)
        print(str(out.relative_to(ROOT) / 'summary.json'), flush=True)
    except BaseException as error:
        save(out / 'failure.json', dict(error=repr(error), recorded_utc=utc(), output_sha256=inventory(out)))
        execution.update(status='failed', completed_utc=utc(), failure_sha256=sha(out / 'failure.json'))
        save(out / 'execution.json', execution)
        raise


if __name__ == '__main__':
    main()
