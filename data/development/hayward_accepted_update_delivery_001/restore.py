#!/usr/bin/env python3
"""Verify the closed archive and restore into a NEW directory; never overwrite."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path, PurePosixPath
import tarfile

HERE = Path(__file__).resolve().parent


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1048576), b''):
            h.update(chunk)
    return h.hexdigest()


def safe_path(base, name):
    rel = PurePosixPath(name)
    require(not rel.is_absolute() and name == str(rel) and rel.parts and
            all(p not in ('', '.', '..') for p in rel.parts), 'Unsafe member path: ' + name)
    return base.joinpath(*rel.parts)


def restore(destination):
    target = Path(destination).absolute()
    require(target.resolve() == target and not target.exists() and not target.is_symlink(), 'Destination must be new and have no symlink ancestors')
    require(target.parent.is_dir(), 'Destination parent must already exist')
    record = json.loads((HERE / 'packaging.json').read_text())
    require(record['status'] == 'verified_lossless', 'Package did not pass')
    require(sha(HERE / 'members.json') == record['members_sha256'], 'Manifest changed')
    archive_path = HERE / record['archive']
    require(archive_path.parent == HERE and sha(archive_path) == record['archive_sha256'], 'Archive changed')
    expected = json.loads((HERE / 'members.json').read_text())['members']
    with gzip.open(str(archive_path), 'rb') as f:
        while f.read(1048576):
            pass  # Verify the gzip trailer before creating any output.
    with tarfile.open(str(archive_path), 'r:gz') as archive:
        members = archive.getmembers()
        require(len(members) == record['member_count'] == len(expected) and
                {m.name for m in members} == set(expected), 'Duplicate/missing member')
        # No extractall: validate every regular-file name, mode and byte hash first.
        for member in members:
            safe_path(target, member.name)
            item = expected[member.name]
            require(item['type'] == 'file' and member.isfile() and member.size == item['bytes'] and
                    member.mode == item['mode'] and member.mode & ~0o777 == 0 and
                    member.mtime == member.uid == member.gid == 0 and member.uname == member.gname == '', 'Unexpected member metadata')
            require(hashlib.sha256(archive.extractfile(member).read()).hexdigest() == item['sha256'], 'Member bytes changed: ' + member.name)
        target.mkdir()
        for member in members:
            path = safe_path(target, member.name)
            path.parent.mkdir(parents=True, exist_ok=True)
            require(path.parent.resolve() == path.parent and not path.is_symlink(), 'Unexpected alias during restore')
            with path.open('xb') as f:
                f.write(archive.extractfile(member).read())
            path.chmod(expected[member.name]['mode'])
            require(sha(path) == expected[member.name]['sha256'], 'Restored bytes changed: ' + member.name)
    require(sha(archive_path) == record['archive_sha256'], 'Archive changed during restore')
    result = {'status': 'verified_lossless_restore', 'members': len(expected),
              'archive_sha256': record['archive_sha256'], 'members_sha256': record['members_sha256'],
              'destination': str(target), 'overwrite_count': 0, 'solver_calls': 0, 'integration_calls': 0}
    with (target / 'restore_receipt.json').open('x') as f:
        json.dump(result, f, indent=2, sort_keys=True)
        f.write('\n')
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', required=True)
    restore(parser.parse_args().destination)
