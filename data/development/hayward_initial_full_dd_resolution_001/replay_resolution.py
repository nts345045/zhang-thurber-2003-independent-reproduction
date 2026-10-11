#!/usr/bin/env python3
"""Restore verified scientific inputs to a fresh directory, then exec one replay."""
import argparse
import hashlib
import json
import os
import shutil
import sys
import tarfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SOURCE_SHA256 = '64315e341200cbac98be78e45a03de81eb040e96d265ab1adb15c9d08b907d43'
EXPECTED = {'initial_events.csv', 'initial_grid.csv', 'observations.csv', 'stations.csv',
            'run.cfg', 'authoritative_ids_required'} | {
    'initial_full_linearization_' + name + '.csv' for name in
    ('rows', 'matrix', 'columns', 'suppressed', 'smoothing_rows', 'smoothing_matrix', 'rays', 'info')}


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True,
                        help='Fresh repository-relative directory beneath tmp/')
    args = parser.parse_args()
    parts = args.output.parts
    if args.output.is_absolute() or len(parts) < 2 or parts[0] != 'tmp' or '..' in parts:
        raise ValueError('Output must be a fresh relative child of repository tmp/')
    output = ROOT / args.output
    for parent in (output,) + tuple(output.parents):
        if parent == ROOT:
            break
        if parent.is_symlink():
            raise ValueError('Do not traverse a symlink: ' + str(parent))
    if output.exists():
        raise ValueError('Preserve existing replay destination: ' + str(output))
    manifest = json.loads((HERE / 'scientific_manifest.json').read_text())
    assert manifest['status'] == 'passed' and manifest['record_type'] == 'closed scientific output inventory'
    source = ROOT / 'resolution_full_hayward.py'
    assert manifest['resolution_source']['sha256'] == sha(source) == SOURCE_SHA256
    assert manifest['input_archive']['file'] == 'replay_inputs.tar.gz'
    assert manifest['input_archive']['index_file'] == 'replay_inputs.json'
    archive, index_path = HERE / 'replay_inputs.tar.gz', HERE / 'replay_inputs.json'
    assert sha(index_path) == manifest['input_archive']['index_sha256']
    index = json.loads(index_path.read_text())
    assert index['archive'] == archive.name and index['member_count'] == 14
    assert set(index['members']) == EXPECTED and index['status'] == 'passed'
    assert sha(archive) == index['archive_sha256'] == manifest['input_archive']['sha256']
    identity_names = ('data/initial_full_dd_identifiers.json.gz',
                      'data/initial_full_dd_identifiers_manifest.json')
    for name in identity_names:
        assert sha(HERE / name) == manifest['output_sha256'][name], name
    identity = json.loads((HERE / identity_names[1]).read_text())
    assert identity['identity_sha256'] == manifest['output_sha256'][identity_names[0]]
    assert identity['counts'] == {'events': 1092, 'receiver_epochs': 372, 'model_nodes': 462,
                                  'observations': 58980, 'primitive_picks': 14262}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir()
    data = output / 'data'
    data.mkdir()
    seen = set()
    with tarfile.open(archive, 'r:gz') as tar:
        for member in tar:
            if not member.isfile() or member.name not in EXPECTED or member.name in seen:
                raise ValueError('Unexpected, duplicate or nonregular archive member: ' + member.name)
            item = index['members'][member.name]
            assert member.size == item['bytes'] and member.mode == item['mode']
            target = data / member.name
            with tar.extractfile(member) as saved, target.open('xb') as restored:
                shutil.copyfileobj(saved, restored)
            assert sha(target) == item['sha256'], member.name
            target.chmod(member.mode)
            seen.add(member.name)
    assert seen == EXPECTED
    for name in identity_names:
        target = data / Path(name).name
        with (HERE / name).open('rb') as saved, target.open('xb') as restored:
            shutil.copyfileobj(saved, restored)
        assert sha(target) == manifest['output_sha256'][name]
    environment = dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
                       PYTHONDONTWRITEBYTECODE='1')
    for key, name in (('TMPDIR', 'tmp'), ('MPLCONFIGDIR', 'matplotlib'), ('XDG_CACHE_HOME', 'cache')):
        (output / name).mkdir()
        environment[key] = str(output / name)
    command = [sys.executable, '-B', str(source), '--data-dir', str(data), '--mode', 'initial']
    record = {'status': 'inputs_restored_before_numerical_replay',
              'archive_sha256': sha(archive), 'member_count': len(seen),
              'input_sha256': {name: item['sha256'] for name, item in index['members'].items()},
              'identity_sha256': {Path(name).name: manifest['output_sha256'][name] for name in identity_names},
              'resolution_source_sha256': SOURCE_SHA256,
              'scope': 'One unchanged INITIAL stage0 catalog-only matrix calculation; no ray or reference evaluation.'}
    with (output / 'replay_preparation.json').open('x') as stream:
        json.dump(record, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print('Verified 14 scientific input files and both complete identifier companions; starting one resolution replay.', flush=True)
    os.execve(sys.executable, command, environment)


if __name__ == '__main__':
    if not __debug__:
        raise ValueError('Run with Python assertions enabled')
    main()
