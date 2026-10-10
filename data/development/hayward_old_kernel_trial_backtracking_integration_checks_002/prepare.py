#!/usr/bin/env python3
"""Preserve attempt001 and prepare only its CMake cache-type parser correction."""
import datetime
import difflib
import hashlib
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OLD = ROOT / 'data/development/hayward_old_kernel_trial_backtracking_integration_checks_001'
CONTROL = ROOT / 'data/development/hayward_old_kernel_trial_backtracking_controls_001'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    assert not (HERE / 'prepared.json').exists() and not (HERE / 'source').exists()
    old = json.loads((OLD / 'prepared.json').read_text())
    for group, base in [('original_sha256', ROOT), ('runtime_sha256', Path('/')), ('output_sha256', OLD)]:
        for name, digest in old[group].items():
            assert sha(base / name) == digest, name
    failed = json.loads((OLD / 'execution.json').read_text())
    assert failed['status'] == 'failed_preserved' and failed['outputs_stable']
    assert [r['stage'] for r in failed['commands']] == ['cmake_configure', 'cmake_build']
    assert all(r['return_code'] == 0 for r in failed['commands'])
    assert not failed['unsettled_process_groups']
    for name, digest in failed['output_sha256'].items():
        assert sha(OLD / name) == digest, name
    for name in old['output_sha256']:
        if name in ('prepare.py', 'run.py', 'README.md'):
            continue
        target = HERE / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(str(OLD / name), str(target))
    source = (OLD / 'run.py').read_text()
    before = """        compiler=next(line.split('=',1)[1] for line in (build/'CMakeCache.txt').read_text().splitlines()
                      if line.startswith('CMAKE_CXX_COMPILER:FILEPATH='))"""
    after = """        compiler_rows=[line for line in (build/'CMakeCache.txt').read_text().splitlines()
                       if line.split(':',1)[0]=='CMAKE_CXX_COMPILER']
        if len(compiler_rows)!=1 or '=' not in compiler_rows[0]:
            raise RuntimeError('Missing or ambiguous CMake compiler cache key')
        compiler=compiler_rows[0].split('=',1)[1]"""
    assert source.count(before) == 1
    revised = source.replace(before, after)
    (HERE / 'run.py').write_text(revised)
    (HERE / 'runner.patch').write_text(''.join(difflib.unified_diff(source.splitlines(True), revised.splitlines(True),
                                                               fromfile='attempt001/run.py', tofile='attempt002/run.py')))
    # Exercise the exact new parser lines, without invoking the runner.
    fragment = '\n'.join(line[8:] for line in after.splitlines()).replace("(build/'CMakeCache.txt').read_text().splitlines()", 'lines')
    controls = []
    for label, lines, succeeds in [
        ('STRING', ['CMAKE_CXX_COMPILER:STRING=/usr/bin/c++'], True),
        ('FILEPATH', ['CMAKE_CXX_COMPILER:FILEPATH=/usr/bin/c++'], True),
        ('missing', ['CMAKE_CXX_COMPILER_AR:FILEPATH=/usr/bin/gcc-ar'], False),
        ('duplicate', ['CMAKE_CXX_COMPILER:STRING=/usr/bin/c++', 'CMAKE_CXX_COMPILER:FILEPATH=/usr/bin/c++'], False),
        ('malformed', ['CMAKE_CXX_COMPILER:STRING'], False)]:
        namespace = {'lines': lines}
        try:
            exec(fragment, namespace)
            assert succeeds and namespace['compiler'] == '/usr/bin/c++'
        except RuntimeError:
            assert not succeeds
        controls.append({'case': label, 'passed': True, 'accepted': succeeds})
    (HERE / 'parser_controls.json').write_text(json.dumps(controls, indent=2) + '\n')
    inputs = dict(old['original_sha256'])
    for path in [OLD / 'prepared.json', OLD / 'execution.json', OLD / 'run.py',
                 OLD / 'build/cmake/CMakeCache.txt', CONTROL / 'review.json',
                 CONTROL / 'summary.json', CONTROL / 'execution.json']:
        inputs[str(path.relative_to(ROOT))] = sha(path)
    assert json.loads((CONTROL / 'review.json').read_text())['status'] == 'passed'
    prepared = dict(old)
    prepared.update(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    controls_review=str((CONTROL / 'review.json').relative_to(ROOT)),
                    original_sha256=inputs,
                    output_sha256={str(path.relative_to(HERE)): sha(path) for path in sorted(HERE.rglob('*')) if path.is_file()},
                    previous_failed_execution_sha256=sha(OLD / 'execution.json'),
                    change='Compiler-cache key parsing accepts unique STRING/FILEPATH records; exact compiler bytes and flags still required. No C++ or test changes.',
                    parser_controls=controls)
    with (HERE / 'prepared.json').open('x') as stream:
        json.dump(prepared, stream, indent=2)
        stream.write('\n')
    print(sha(HERE / 'prepared.json'))

if __name__ == '__main__':
    main()
