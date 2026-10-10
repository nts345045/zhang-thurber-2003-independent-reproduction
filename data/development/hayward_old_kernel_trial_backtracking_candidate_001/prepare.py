#!/usr/bin/env python3
"""Prepare an isolated old-kernel/main-only candidate; no compiler or ray call."""
import difflib
import hashlib
import json
import tarfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OLD = ROOT / 'data/hayward_first_arrival_guarded_001'
PREFLIGHT = ROOT / 'data/hayward_first_arrival_004'
PRIOR = ROOT / 'data/development/hayward_trial_backtracking_candidate_003'

def sha(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()

def read(path):
    return json.loads(path.read_text())

def config(path):
    result = {}
    for line in path.read_text().splitlines():
        fields = line.split('#', 1)[0].split()
        if fields:
            assert len(fields) == 2
            result[fields[0]] = float(fields[1])
    return result

def main():
    assert not (HERE / 'prepared.json').exists()
    assert not (HERE / 'before').exists() and not (HERE / 'after').exists()
    pins = {}
    def pin(path, expected=None):
        value = sha(path)
        if expected is not None:
            assert value == expected, str(path)
        pins[str(path.relative_to(ROOT))] = value
        return value
    pin(OLD / 'dd_inversion_run_manifest.json', '89c013bb0bd5a8987d99e017abf5a6a6f32a88cfb3b75b3f124d8969b6b401e2')
    pin(PREFLIGHT / 'run_manifest.json', '75631991144e76cf16731e0b73e396860ab78db386c556415f990968cb7cc00a')
    pin(PRIOR / 'prepared.json', '1f3f1679c472a136f34709d2f7b0c015861e4c39ec3d3fe69ea768256c9bac9a')
    old, preflight, prior = read(OLD / 'dd_inversion_run_manifest.json'), read(PREFLIGHT / 'run_manifest.json'), read(PRIOR / 'prepared.json')
    pin(OLD / 'guarded_source.tar.gz', old['source_archive_sha256'])
    for rel in ('before/src/main.cpp', 'after/src/main.cpp', 'candidate.patch'):
        pin(PRIOR / rel, prior['output_sha256'][rel])
    bridge = ROOT / 'data/development/hayward_guard_adoption_checks/001/summary.json'
    pin(bridge, '6893f3fd746d21a88878990d5af1bfb0a60107d13ae16be42ae0d049cb59f3ab')
    assert read(bridge)['status'] == 'passed'
    review = ROOT / 'data/development/hayward_trial_backtracking_controls_002/review.json'
    pin(review, '56a4dd3aa36539344a51a97feeaf5c91ab560d1a52b1fafba8974f886f8f0bb3')
    assert read(review)['status'] == 'passed'
    names = sorted(n for n in old['source_sha256'] if n.startswith('src/') or n == 'CMakeLists.txt')
    with tarfile.open(str(OLD / 'guarded_source.tar.gz'), 'r:gz') as archive:
        members = {m.name: m for m in archive.getmembers()}
        assert len(members) == len(archive.getmembers())
        for name in names:
            member = members[name]
            assert member.isfile()
            data = archive.extractfile(member).read()
            assert hashlib.sha256(data).hexdigest() == old['source_sha256'][name]
            for variant in ('before', 'after'):
                dest = HERE / variant / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                with dest.open('xb') as stream:
                    stream.write(data)
    assert (HERE / 'before/src/main.cpp').read_bytes() == (PRIOR / 'before/src/main.cpp').read_bytes()
    (HERE / 'after/src/main.cpp').write_bytes((PRIOR / 'after/src/main.cpp').read_bytes())
    before = (HERE / 'before/src/main.cpp').read_text()
    after = (HERE / 'after/src/main.cpp').read_text()
    patch = ''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                       fromfile='before/src/main.cpp', tofile='after/src/main.cpp'))
    assert patch.encode() == (PRIOR / 'candidate.patch').read_bytes()
    (HERE / 'candidate.patch').write_text(patch)
    changed = [name for name in names if sha(HERE / 'before' / name) != sha(HERE / 'after' / name)]
    assert changed == ['src/main.cpp']
    shared = {}
    for name, value in preflight['source_sha256'].items():
        if name != 'src/main.cpp' and (name.startswith('src/') or name == 'CMakeLists.txt'):
            assert old['source_sha256'][name] == sha(HERE / 'after' / name) == value
            shared[name] = value
    # This whole block contains configuration dispatch, receiver-field
    # preparation and sparse/native-index ray evaluation, including errors.
    start, end = 'double auxiliary_spacing(', 'void initializer_header('
    old_call = before[before.index(start):before.index(end)]
    new_call = after[after.index(start):after.index(end)]
    assert old_call == new_call
    identical_inputs = {}
    for name in ('initial_events.csv', 'initial_grid.csv', 'stations.csv', 'observations.csv'):
        value = pin(OLD / name, old['input_sha256'][name])
        pin(PREFLIGHT / name, value)
        identical_inputs[name] = value
    pin(OLD / 'run.cfg', old['input_sha256']['run.cfg'])
    pin(PREFLIGHT / 'run.cfg')
    settings = config(OLD / 'run.cfg')
    assert settings == config(PREFLIGHT / 'run.cfg')
    runtime = {old['compiler']: old['compiler_sha256']}
    runtime.update(old['runtime_library_sha256'])
    assert all(sha(Path(path)) == value for path, value in runtime.items())
    output = {str(path.relative_to(HERE)): sha(path) for path in sorted(HERE.rglob('*')) if path.is_file()}
    result = {'status': 'prepared_not_executed',
              'scope': 'Separate old7111-kernel, exact candidate003 main-only backtracking candidate; no maintained mutation or numerical execution.',
              'input_sha256': pins, 'runtime_sha256': runtime,
              'original_sha256': {name: old['source_sha256'][name] for name in names},
              'output_sha256': output, 'changed_source_files': changed,
              'bridge': {'preflight_main_sha256': preflight['source_sha256']['src/main.cpp'],
                         'reviewed_guarded_main_sha256': old['source_sha256']['src/main.cpp'],
                         'candidate_main_sha256': sha(HERE / 'after/src/main.cpp'),
                         'prior_guard_bridge_summary_sha256': sha(bridge),
                         'identical_initial_ray_dispatch_block_sha256': hashlib.sha256(old_call.encode()).hexdigest(),
                         'identical_shared_kernel_and_cmake_sha256': shared,
                         'identical_native_numerical_input_sha256': identical_inputs,
                         'identical_effective_config': settings},
              'compiler': old['compiler'], 'flags': old['flags'], 'planned_threads': old['threads'],
              'limitations': ['004 main and guarded main differ; reuse explicitly depends on the prior reviewed guard bridge.',
                             'New binary and bounded controls are pending. No exact binary-identity claim or real inverse authorization follows from source preparation.',
                             'Initial one-dimensional accuracy does not certify later three-dimensional trial models; unchanged current/final guards remain fatal.',
                             'Maintained D adoption and prior candidate003/controls002 remain unchanged and separate.']}
    assert all(sha(ROOT / name) == value for name, value in pins.items())
    with (HERE / 'prepared.json').open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(sha(HERE / 'prepared.json'))

if __name__ == '__main__':
    main()
