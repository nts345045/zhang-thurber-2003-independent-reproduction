#!/usr/bin/env python3
"""Saved-byte restoration checks only; never execute the archived fixtures."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(destination):
    if not __debug__:
        raise RuntimeError('Do not disable assertions')
    target = Path(destination).absolute()
    assert ROOT/'tmp' in target.parents
    assert not target.exists() and not target.is_symlink()
    assert not (HERE/'restore_check.json').exists()
    package = json.loads((HERE/'packaging.json').read_text())
    members = json.loads((HERE/'members.json').read_text())['members']
    assert sha(HERE/'restore.py') == package['restore_script_sha256']
    assert sha(HERE/'members.json') == package['members_sha256']
    command = [sys.executable, str(HERE/'restore.py'), '--destination', str(target)]
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    attempts = []

    def call(label, success):
        result = subprocess.run(command, env=environment, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        record = dict(label=label, return_code=result.returncode,
                      stdout=result.stdout.decode(), stderr=result.stderr.decode())
        attempts.append(record)
        assert (result.returncode == 0) == success, record
        return json.loads(record['stdout']) if success else record

    first = call('fresh_restore', True)
    assert first['restored'] == len(members) and first['already_identical'] == 0

    def verify(base):
        for name, item in members.items():
            path = base/name
            assert item['type'] == 'file' and path.is_file() and not path.is_symlink()
            assert path.stat().st_size == item['bytes']
            assert path.stat().st_mode & 0o777 == item['mode']
            assert sha(path) == item['sha256'], name

    verify(target)
    actual = {str(p.relative_to(target)) for p in target.rglob('*')
              if p.is_file() or p.is_symlink()}
    assert actual == set(members)
    repeated = call('idempotent_restore', True)
    assert repeated['restored'] == 0 and repeated['already_identical'] == len(members)
    # Modify only one restored scratch file; the originals and archive stay intact.
    name = sorted(members)[0]
    item, scratch = members[name], target/name
    original = scratch.read_bytes()
    scratch.chmod(item['mode'] ^ 0o100)
    try:
        failure = call('different_mode_refused', False)
        assert 'Refusing to overwrite different evidence' in failure['stderr']
        assert scratch.stat().st_mode & 0o777 == item['mode'] ^ 0o100
    finally:
        scratch.chmod(item['mode'])
    scratch.write_bytes(original + b'\nintentional scratch-only mismatch\n')
    try:
        failure = call('different_bytes_refused', False)
        assert 'Refusing to overwrite different evidence' in failure['stderr']
        assert scratch.read_bytes() == original + b'\nintentional scratch-only mismatch\n'
    finally:
        scratch.write_bytes(original)
    verify(target)
    verify(ROOT)
    dependencies = json.loads((HERE/'dependencies.json').read_text())
    for name, item in dependencies['original_inputs'].items():
        assert sha(ROOT/name) == item['sha256']
    result = dict(status='passed', scope='Archive/restore only; no fixture or numerical execution.',
                  archive_sha256=sha(HERE/'evidence.tar.gz'),
                  packaging_sha256=sha(HERE/'packaging.json'),
                  members_sha256=sha(HERE/'members.json'),
                  dependencies_sha256=sha(HERE/'dependencies.json'),
                  checker_sha256=sha(Path(__file__)), restore_sha256=sha(HERE/'restore.py'),
                  command=command, destination=str(target.relative_to(ROOT)),
                  verified_members=len(members), verified_bytes=package['regular_file_bytes'],
                  verified_original_dependencies=len(dependencies['original_inputs']),
                  original_bytes_and_modes_unchanged=True, exact_restored_roster=True,
                  compiled_binaries_preserved_but_not_executed=package['compiled_binaries'],
                  symbolic_links=package['symbolic_links'], attempts=attempts)
    with (HERE/'restore_check.json').open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps(dict(status='passed', verified_members=len(members),
                         restore_check_sha256=sha(HERE/'restore_check.json')), sort_keys=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', required=True)
    main(parser.parse_args().destination)
