#!/usr/bin/env python3
"""Freeze the reviewed D inputs and a single diagnostic stopping intervention."""
import ast
import difflib
import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = ROOT / 'data/development/loma_lon_straight_curvature_replay_001'

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()

def main():
    if (HERE / 'prepared.json').exists() or (HERE / 'inputs').exists():
        raise RuntimeError('Exclusive preparation; preserve prior attempts')
    review = json.loads((BASE / 'review.json').read_text())
    summary = json.loads((BASE / 'summary.json').read_text())
    execution = json.loads((BASE / 'execution.json').read_text())
    oldprep = json.loads((BASE / 'prepared_v3.json').read_text())
    if review['status'] != 'passed' or execution['status'] != 'completed' or execution['return_code'] != 0:
        raise RuntimeError('Baseline is not independently reviewed terminal success')
    if sha(BASE / 'review.json') != '3e9d14d95c435d242ac8a241f452d712e8ea1beda066b1d645fa0b0f30c725a9':
        raise RuntimeError('Unexpected baseline review')
    if sha(BASE / 'summary.json') != 'ee14057bc05c7747f30eda6df9670b0f89e26a777390668d9d78f20b03523bde':
        raise RuntimeError('Unexpected baseline summary')
    if execution['summary_sha256'] != sha(BASE / 'summary.json'):
        raise RuntimeError('Baseline execution pin mismatch')
    for name, expected in summary['output_sha256'].items():
        if sha(BASE / name) != expected:
            raise RuntimeError('Baseline output changed: ' + name)
    for name, expected in oldprep['output_sha256'].items():
        if sha(BASE / name) != expected:
            raise RuntimeError('Baseline prepared file changed: ' + name)
    for name, expected in oldprep['runtime_sha256'].items():
        if sha(Path(name)) != expected:
            raise RuntimeError('Compiler/runtime changed: ' + name)
    originals = {}
    def copy(old, new):
        originals[str(old.relative_to(ROOT))] = sha(old)
        new.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(str(old), str(new))
    inputs = HERE / 'inputs'
    for name in ('initial_grid.csv', 'initial_events.csv', 'stations.csv', 'run.cfg', 'native_context.json',
                 'selected_reference.csv', 'selected_status.csv', 'selected_comparison.csv', 'old_flags.make', 'compiler_version.txt'):
        copy(BASE / 'inputs' / name, inputs / name)
    for name in ('summary.json', 'execution.json', 'review.json', 'controller_completion.json', 'prepared_v3.json', 'old_parity.json'):
        copy(BASE / name, inputs / ('baseline_' + name))
    for old in sorted((BASE / 'results/D').glob('*.csv')):
        copy(old, inputs / 'baseline_D' / old.name)
    source = HERE / 'source/strict'
    for old in sorted((BASE / 'source/D').rglob('*')):
        if old.is_file():
            copy(old, source / old.relative_to(BASE / 'source/D'))
    path = source / 'src/core.hpp'
    baseline_core = path.read_text()
    before = 'if (change < 1e-11 && projected_ray_gradient(g, p, grad) < 1e-5) {'
    after = 'if (false && change < 1e-11 && projected_ray_gradient(g, p, grad) < 1e-5) {'
    if baseline_core.count(before) != 1:
        raise RuntimeError('Unexpected combined-stop source')
    strict_core = baseline_core.replace(before, after)
    path.write_text(strict_core)
    (HERE / 'core.hpp.diff').write_text(''.join(difflib.unified_diff(
        baseline_core.splitlines(True), strict_core.splitlines(True), fromfile='reviewed_D/src/core.hpp', tofile='strict/src/core.hpp')))
    driver = (BASE / 'driver.cpp').read_text()
    originals[str((BASE / 'driver.cpp').relative_to(ROOT))] = sha(BASE / 'driver.cpp')
    old_comment = '// Four calls total are authorized: this executable evaluates two fixed pairs.'
    new_comment = '// Two calls total are authorized: this executable evaluates two fixed pairs.'
    if driver.count(old_comment) != 1:
        raise RuntimeError('Unexpected driver comment')
    (HERE / 'driver.cpp').write_text(driver.replace(old_comment, new_comment))
    (HERE / 'driver.cpp.diff').write_text(''.join(difflib.unified_diff(driver.splitlines(True),
        (HERE/'driver.cpp').read_text().splitlines(True), fromfile='baseline_driver.cpp', tofile='strict_driver.cpp')))
    (HERE / 'runner.diff').write_text(''.join(difflib.unified_diff((BASE/'run_v3.py').read_text().splitlines(True),
        (HERE/'run.py').read_text().splitlines(True), fromfile='reviewed_runner_v3.py', tofile='strict_runner.py')))
    originals[str((BASE/'run_v3.py').relative_to(ROOT))] = sha(BASE/'run_v3.py')
    ast.parse((HERE / 'run.py').read_text())
    for name, expected in originals.items():
        if sha(ROOT / name) != expected:
            raise RuntimeError('Input changed during preparation')
    pins = {str(p.relative_to(HERE)): sha(p) for p in sorted(HERE.rglob('*')) if p.is_file()}
    prepared = {'status': 'prepared_not_executed', 'native_pairs': [8670, 8674], 'native_calls': 2,
        'source_intervention': 'Only false&& disables the combined early-stop condition; driver comment updated from four to two calls, no driver arithmetic change',
        'baseline_review_sha256': sha(BASE/'review.json'), 'baseline_summary_sha256': sha(BASE/'summary.json'),
        'original_sha256': originals, 'runtime_sha256': oldprep['runtime_sha256'],
        'compiler': oldprep['compiler'], 'flags': oldprep['flags'], 'output_sha256': pins,
        'source_sha256': {str(p.relative_to(HERE)): sha(p) for p in sorted(source.rglob('*')) if p.is_file()},
        'settings': {'ray_spacing_km': .03125, 'maximum_updates': 1000, 'strict_projected_gradient': 1e-7,
                     'armijo_trials': 24, 'seed': None, 'time_limit_s': 2.5e-5, 'source_norm_limit_s_per_km': 3e-6},
        'loop_termination_basis': 'Derived from inspected exits: updates==1000 is loop-budget exhaustion (post-return strict flag separate); otherwise flagtrue is strict top check, flagfalse is failed24-trial search; exceptions are failed execution. No history instrumentation.'}
    with (HERE / 'prepared.json').open('x') as f:
        json.dump(prepared, f, indent=2, allow_nan=False)
        f.write('\n')
    print(sha(HERE/'prepared.json'))

if __name__ == '__main__':
    main()
