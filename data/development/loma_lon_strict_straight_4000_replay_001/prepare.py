#!/usr/bin/env python3
"""Freeze a two-call cap comparison from the reviewed strict-1000 package."""
import ast
import difflib
import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = ROOT / 'data/development/loma_lon_strict_straight_replay_001'


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def diff(before, after, first, second):
    return ''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                      fromfile=first, tofile=second))


def main():
    if (HERE / 'prepared.json').exists() or (HERE / 'inputs').exists():
        raise RuntimeError('Exclusive preparation; preserve prior attempts')
    review = json.loads((BASE / 'review.json').read_text())
    summary = json.loads((BASE / 'summary.json').read_text())
    execution = json.loads((BASE / 'execution.json').read_text())
    oldprep = json.loads((BASE / 'prepared.json').read_text())
    if sha(BASE / 'review.json') != '981487f2a95910d63790f7415ccb64da25f796c11093cf0d303e8858f1e71af0':
        raise RuntimeError('Unexpected strict-1000 review')
    if sha(BASE / 'summary.json') != '363886801314b87e7e3cf5d1869180c7f25f2124594c16a92f3276fdf9678da2':
        raise RuntimeError('Unexpected strict-1000 summary')
    if review['status'] != 'passed' or execution['status'] != 'completed' or execution['return_code'] != 0:
        raise RuntimeError('Strict-1000 package is not independently reviewed terminal success')
    for name in ('summary', 'execution', 'controller_completion', 'prelaunch_review'):
        if review[name + '_sha256'] != sha(BASE / (name + '.json')):
            raise RuntimeError('Strict-1000 review binding changed: ' + name)
    if execution['summary_sha256'] != sha(BASE / 'summary.json') or execution['native_calls_completed'] != 2:
        raise RuntimeError('Strict-1000 execution mismatch')
    for inventory in (summary['output_sha256'], oldprep['output_sha256']):
        for name, expected in inventory.items():
            if sha(BASE / name) != expected:
                raise RuntimeError('Strict-1000 artifact changed: ' + name)
    for name, expected in oldprep['original_sha256'].items():
        if sha(ROOT / name) != expected:
            raise RuntimeError('Strict-1000 original pin changed: ' + name)
    for name, expected in oldprep['runtime_sha256'].items():
        if sha(Path(name)) != expected:
            raise RuntimeError('Compiler/runtime changed: ' + name)
    originals = {}

    def copy(old, new):
        originals[str(old.relative_to(ROOT))] = sha(old)
        new.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(str(old), str(new))

    for old in sorted((BASE / 'inputs').rglob('*')):
        if old.is_file():
            copy(old, HERE / 'inputs' / old.relative_to(BASE / 'inputs'))
    for name in ('summary.json', 'execution.json', 'review.json', 'controller_completion.json', 'prepared.json'):
        copy(BASE / name, HERE / 'inputs' / ('strict_1000_' + name))
    for old in sorted((BASE / 'results/strict').glob('*.csv')):
        copy(old, HERE / 'inputs/strict_1000' / old.name)
    source = HERE / 'source/strict'
    for old in sorted((BASE / 'source/strict').rglob('*')):
        if old.is_file():
            copy(old, source / old.relative_to(BASE / 'source/strict'))
    for old in sorted((BASE / 'source/strict').rglob('*')):
        if old.is_file() and sha(old) != sha(source / old.relative_to(BASE / 'source/strict')):
            raise RuntimeError('Strict numerical source copy differs')

    config = HERE / 'inputs/run.cfg'
    before = config.read_text()
    if before.splitlines().count('ray_iterations 1000') != 1:
        raise RuntimeError('Unexpected original cap setting')
    after = before.replace('ray_iterations 1000\n', 'ray_iterations 4000\n')
    if before == after or after.replace('ray_iterations 4000\n', 'ray_iterations 1000\n') != before:
        raise RuntimeError('Unexpected config mutation')
    config.write_text(after)
    (HERE / 'run.cfg.diff').write_text(diff(before, after, 'strict_1000/run.cfg', 'strict_4000/run.cfg'))

    driver = (BASE / 'driver.cpp').read_text()
    originals[str((BASE / 'driver.cpp').relative_to(ROOT))] = sha(BASE / 'driver.cpp')
    old_guard = 'config.get("ray_iterations") != 1000'
    if driver.count(old_guard) != 1:
        raise RuntimeError('Unexpected driver validation guard')
    new_driver = driver.replace(old_guard, 'config.get("ray_iterations") != 4000')
    (HERE / 'driver.cpp').write_text(new_driver)
    (HERE / 'driver.cpp.diff').write_text(diff(driver, new_driver, 'strict_1000/driver.cpp', 'strict_4000/driver.cpp'))
    old_runner = (BASE / 'run.py').read_text()
    new_runner = (HERE / 'run.py').read_text()
    originals[str((BASE / 'run.py').relative_to(ROOT))] = sha(BASE / 'run.py')
    (HERE / 'runner.diff').write_text(diff(old_runner, new_runner, 'strict_1000/run.py', 'strict_4000/run.py'))
    first, second = ast.parse(old_runner), ast.parse(new_runner)
    unchanged = ('verify', 'group_members', 'signal_group', 'terminate_and_reap', 'interrupted', 'command')
    for name in unchanged:
        a = [n for n in ast.walk(first) if isinstance(n, ast.FunctionDef) and n.name == name]
        b = [n for n in ast.walk(second) if isinstance(n, ast.FunctionDef) and n.name == name]
        if len(a) != 1 or len(b) != 1 or ast.dump(a[0]) != ast.dump(b[0]):
            raise RuntimeError('Reviewed lifecycle/check function changed: ' + name)
    for name, expected in originals.items():
        if sha(ROOT / name) != expected:
            raise RuntimeError('Input changed during preparation')
    prepared = {
        'status': 'prepared_not_executed', 'native_pairs': [8670, 8674], 'native_calls': 2,
        'source_intervention': 'Strict-1000 numerical source is byte-identical; only run.cfg cap 1000 to 4000 and matching driver validation guard change. Runner classification and truthful two-call prose follow that cap.',
        'strict_1000_review_sha256': sha(BASE / 'review.json'),
        'strict_1000_summary_sha256': sha(BASE / 'summary.json'),
        'original_sha256': originals, 'runtime_sha256': oldprep['runtime_sha256'],
        'compiler': oldprep['compiler'], 'flags': oldprep['flags'],
        'output_sha256': {str(p.relative_to(HERE)): sha(p) for p in sorted(HERE.rglob('*')) if p.is_file()},
        'source_sha256': {str(p.relative_to(HERE)): sha(p) for p in sorted(source.rglob('*')) if p.is_file()},
        'unchanged_lifecycle_functions_ast': list(unchanged),
        'settings': {'ray_spacing_km': .03125, 'maximum_updates': 4000, 'strict_projected_gradient': 1e-7,
                     'armijo_trials': 24, 'seed': None, 'time_limit_s': 2.5e-5, 'source_norm_limit_s_per_km': 3e-6},
        'loop_termination_basis': 'Derived from inspected exits: updates==4000 is loop-budget exhaustion, with post-return strict flag separate; otherwise a true flag is the strict top check and a false flag is exhausted 24-trial search. Exceptions remain failed execution; no history instrumentation.',
        'scope_limit': 'Exactly two calls; no adaptive cap escalation, FMM construction, full-cohort run or production change.',
    }
    with (HERE / 'prepared.json').open('x') as f:
        json.dump(prepared, f, indent=2, allow_nan=False)
        f.write('\n')
    print(sha(HERE / 'prepared.json'))


if __name__ == '__main__':
    main()
