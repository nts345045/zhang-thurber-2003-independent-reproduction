#!/usr/bin/env python3
"""Freeze, then test the separately prepared old-kernel backtracking loop."""
import argparse
import csv
import difflib
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
CANDIDATE = ROOT / 'data/development/hayward_old_kernel_trial_backtracking_candidate_001'
PREPARED_SHA = '5bb45c57b3f594485abbaf144da3b540f2c7f8d42dc783837976fbe33b5d96dd'
HELPERS = ['diagnostics/check_trial_backtracking.cpp', 'diagnostics/run_old_kernel_trial_backtracking_checks.py']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('Fixture seam must match exactly once: ' + old)
    return text.replace(old, new, 1)


def instrument(text):
    declarations = '''// Test-only seams: actual invert body and arithmetic are retained.
std::string fixture_output(const std::string &);
Vec fixture_solve(Matrix, double, LSQRInfo *);
void fixture_gate(const std::string &, const Grid &, const std::vector<Event> &,
                  const std::vector<Event> &, const std::vector<Ray> &,
                  const std::vector<int> &, bool, bool);
'''
    text = replace_once(text, 'std::ofstream output(std::string p) {',
                        declarations + 'std::ofstream output(std::string p) {')
    text = replace_once(text, '  std::ofstream f(p);', '  std::ofstream f(fixture_output(p));')
    text = replace_once(text,
                        '      inversion_ray_gate(prefix, model, sources, stations, result, used,',
                        '      fixture_gate(prefix, model, sources, stations, result, used,')
    return replace_once(text, '    Vec delta = solve(std::move(A), c.get("damping"), &linear_info);',
                        '    Vec delta = fixture_solve(std::move(A), c.get("damping"), &linear_info);')


def prepare(out):
    if sha(CANDIDATE / 'prepared.json') != PREPARED_SHA:
        raise ValueError('Candidate preparation changed')
    original = json.loads((CANDIDATE / 'prepared.json').read_text())
    for name, digest in original['output_sha256'].items():
        if sha(CANDIDATE / name) != digest:
            raise ValueError('Candidate output changed: ' + name)
    out.mkdir(parents=True)
    inputs = {str((CANDIDATE / 'prepared.json').relative_to(ROOT)): PREPARED_SHA}
    for name, digest in original['output_sha256'].items():
        inputs[str((CANDIDATE / name).relative_to(ROOT))] = digest
    for variant in ('before', 'after'):
        shutil.copytree(str(CANDIDATE / variant), str(out / 'source' / variant))
        main = out / 'source' / variant / 'src/main.cpp'
        modified = instrument(main.read_text())
        target = main.parent / 'fixture_main.cpp'
        target.write_text(modified)
        patch = ''.join(difflib.unified_diff(main.read_text().splitlines(True), modified.splitlines(True),
                                            fromfile=variant + '/src/main.cpp', tofile=variant + '/src/fixture_main.cpp'))
        (out / (variant + '_fixture.patch')).write_text(patch)
    for name in HELPERS:
        target = out / 'source' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(str(ROOT / name), str(target))
        inputs[name] = sha(ROOT / name)
    compiler = Path(original['compiler']).resolve()
    runtime = dict(original['runtime_sha256'])
    runtime.update({str(compiler): sha(compiler), str(Path(sys.executable).resolve()): sha(Path(sys.executable).resolve())})
    if any(sha(Path(name)) != digest for name, digest in runtime.items()):
        raise ValueError('Original compiler/runtime changed')
    (out / 'README.md').write_text('''# Invented trial-backtracking controls

This package tests the separately frozen old7111-kernel candidate with the exact candidate003 main-only delta. Maintained D adoption and the earlier D-based controls remain separate. It is not an adopted solver or an observed earthquake. Every event, origin, pick, arrival and XX.MOCK..HHZ epoch is invented. Native-format fields exercise the actual loader and retain empty locations, quoted/newline metadata, a zero-weight observation and both differential receiver epochs.

Preparation does not compile or run the fixtures. Execution is a separate phase after source review. The copied `invert` loop is unchanged except for three explicit fixture seams shown in the saved diffs: the actual returned Rays pass through a wrapper into the actual gate; the actual LSQR solve runs before an optional prescribed test increment is returned; selected output streams can be redirected to `/dev/full` after freshness checks. No quality exception is fabricated. Pure/mixed failures alter actual returned Ray records. All-valid cases leave every seam inert and require byte-identical before/after output and status tables.

The independent half/quarter-step targets are homogeneous source-time offsets. Original fixed weights are reconstructed with sorted medians and the declared row-multiplier formula. Snapshot checks cover all source/model increments, LSQR status, original metadata and zero rows. Rejected states are checked against the original accepted source coordinates, source clamping and exponential model update at every fraction. No objective is assigned to rejected trials. Current/final/mixed/unexpected failures, no evaluable trial, valid-but-worse objectives, prior artifacts, incomplete snapshots and deferred stream errors remain distinct. Tiny homogeneous 5→6→5 field-cache checks compare actual cached and fresh results while preserving native receiver indices.

The I/O fixture uses the Linux full device to produce failure after a successful open. These checks exercise flush/close error propagation, not power-loss durability or all filesystem failure modes. A prescribed increment is explicitly a fixture input and is not presented as the actual LSQR solution; the actual solve result/status remain captured for inspection. Numerical comparison bounds here are roundoff/serialization controls, not changed scientific ray thresholds. No observational request, native ray, real inverse, production edit or acceptance-flag promotion is performed.

After review, from the integration checkout:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/run_old_kernel_trial_backtracking_checks.py --phase run --variant 001
```

The runner requires unchanged prepared inputs and helpers, fresh build/results/execution paths, records commands before launch, preserves every failed output, and checks original inputs again after execution. It does not commit anything.
'''.replace('--variant 001', '--variant ' + out.name.rsplit('_', 1)[1]))
    outputs = {str(p.relative_to(out)): sha(p) for p in sorted(out.rglob('*')) if p.is_file()}
    save(out / 'prepared.json', dict(status='prepared_not_executed', candidate_prepared_sha256=PREPARED_SHA,
                                    input_sha256=inputs, runtime_sha256=runtime, output_sha256=outputs,
                                    compiler_path=str(compiler),
                                    compile_flags=['-std=gnu++17', '-O3', '-Wall', '-Wextra', '-Wpedantic', '-fopenmp'],
                                    python_version=sys.version, scope='invented controls only'))


def verify(out, prepared):
    for name, digest in prepared['input_sha256'].items():
        if sha(ROOT / name) != digest:
            raise ValueError('Original source changed: ' + name)
    for name, digest in prepared['output_sha256'].items():
        if sha(out / name) != digest:
            raise ValueError('Prepared file changed: ' + name)
    for name, digest in prepared['runtime_sha256'].items():
        if sha(Path(name)) != digest:
            raise ValueError('Runtime changed: ' + name)


def run(out, variant):
    prepared = json.loads((out / 'prepared.json').read_text())
    verify(out, prepared)
    build = ROOT / 'tmp/old_kernel_trial_backtracking_checks' / variant
    for path in (build, out / 'results', out / 'execution.json', out / 'summary.json'):
        if path.exists() or path.is_symlink():
            raise ValueError('Use fresh execution: ' + str(path))
    build.mkdir(parents=True)
    (out / 'results').mkdir()
    execution = dict(status='running', prepared_sha256=sha(out / 'prepared.json'), commands=[])
    environment = dict(os.environ, TMPDIR=str(ROOT / 'tmp'), OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
                       PYTHONDONTWRITEBYTECODE='1', LC_ALL='C')

    def command(name, argv):
        argv = [str(x) for x in argv]
        record = dict(name=name, argv=argv, status='running')
        execution['commands'].append(record)
        save(out / 'execution.json', execution)
        start = time.monotonic()
        with (out / (name + '_stdout.log')).open('w') as stdout, (out / (name + '_stderr.log')).open('w') as stderr:
            code = subprocess.call(argv, cwd=str(ROOT), env=environment, stdout=stdout, stderr=stderr)
        record.update(return_code=code, seconds=time.monotonic()-start, status='completed' if code == 0 else 'failed')
        save(out / 'execution.json', execution)
        if code:
            raise RuntimeError(name + ' failed; original outputs retained')

    summary = dict(status='running', prepared_sha256=sha(out / 'prepared.json'), source_sha256=prepared['output_sha256'])
    try:
        flags = [prepared['compiler_path']] + prepared['compile_flags']
        for name in ('before', 'after'):
            command('compile_' + name, flags + (['-DCANDIDATE'] if name == 'after' else []) +
                    ['-I', out / 'source' / name / 'src', out / 'source/diagnostics/check_trial_backtracking.cpp',
                     '-lstdc++fs', '-o', build / name])
            command(name, [build / name, out / 'results' / name])
        parity = []
        for mode in ('loc1d', 'dd'):
            before = out / 'results/before' / ('valid_' + mode)
            after = out / 'results/after' / ('valid_' + mode)
            for path in sorted(before.iterdir()):
                if not path.is_file():
                    raise ValueError('Unexpected valid fixture directory')
                if path.read_bytes() != (after / path.name).read_bytes():
                    raise ValueError('Before/after mismatch: ' + mode + '/' + path.name)
                parity.append(dict(path='valid_' + mode + '/' + path.name, sha256=sha(path)))
            extras = {p.name for p in after.iterdir()} - {p.name for p in before.iterdir()}
            if any(not name.startswith(mode + '_iteration_') or not name.endswith('_trials.csv') for name in extras):
                raise ValueError('Unexpected extra all-valid output')
        totals = {}
        for name in ('before', 'after'):
            with (out / 'results' / name / 'checks.csv').open(newline='') as stream:
                rows = list(csv.DictReader(stream))
            if not rows or any(row['passed'] != '1' for row in rows):
                raise ValueError('Failed recorded control')
            totals[name] = len(rows)
        verify(out, prepared)
        summary.update(status='passed', controls=totals, all_valid_byte_parity=parity,
                       binary_sha256={name: sha(build / name) for name in ('before', 'after')},
                       scope='invented controls and injected failures; no native/production run')
        execution.update(status='completed', return_code=0)
    except BaseException as error:
        execution.update(status='failed', error_type=type(error).__name__, error=str(error))
        summary.update(status='failed', error_type=type(error).__name__, error=str(error))
        raise
    finally:
        save(out / 'execution.json', execution)
        summary['artifact_sha256'] = {str(p.relative_to(out)): sha(p) for p in sorted(out.rglob('*'))
                                      if p.is_file() and p != out / 'summary.json'}
        save(out / 'summary.json', summary)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase', choices=('prepare', 'run'), required=True)
    parser.add_argument('--variant', required=True)
    args = parser.parse_args()
    if not args.variant.isdigit():
        raise ValueError('Use a numeric variant')
    out = ROOT / ('data/development/hayward_old_kernel_trial_backtracking_controls_' + args.variant)
    if args.phase == 'prepare':
        prepare(out)
    else:
        run(out, args.variant)
    print(str(out))


if __name__ == '__main__':
    main()
