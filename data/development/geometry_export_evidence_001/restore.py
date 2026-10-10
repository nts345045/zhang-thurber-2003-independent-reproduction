#!/usr/bin/env python3
"""Restore the lossless bounded-check archive without overwriting any file."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def safe_path(base, name):
    parts = PurePosixPath(name)
    require(not parts.is_absolute() and name == str(parts) and
            all(p not in ('', '.', '..') for p in parts.parts), 'Unsafe member: ' + name)
    path = base.joinpath(*parts.parts)
    for parent in path.parents:
        if parent == base:
            break
        require(not parent.is_symlink(), 'Symlink parent: ' + str(parent))
    return path


def matches(path, entry):
    if entry['type'] == 'symlink':
        return path.is_symlink() and os.readlink(str(path)) == entry['target']
    return (path.is_file() and not path.is_symlink() and
            path.stat().st_mode & 0o777 == entry['mode'] and sha(path) == entry['sha256'])


def restore(destination):
    # Both a separate inspection directory and the repository itself are valid.
    requested = Path(destination).absolute()
    require(not requested.is_symlink(), 'Destination is a symlink')
    target = requested.resolve()
    require(target == ROOT or ROOT in target.parents, 'Keep restored evidence within this project')
    record = json.loads((HERE/'packaging.json').read_text())
    require(record['status'] == 'verified_lossless', 'Archive has not passed readback')
    require(sha(HERE/'members.json') == record['members_sha256'], 'Member manifest changed')
    archive = HERE/record['archive']
    require(sha(archive) == record['archive_sha256'], 'Archive changed')
    with gzip.open(str(archive), 'rb') as stream:
        while stream.read(1048576):
            pass  # Verify the gzip trailer before creating any output.
    expected = json.loads((HERE/'members.json').read_text())['members']
    restored = existing = 0
    with tarfile.open(str(archive), 'r:gz') as stream:
        members = stream.getmembers()
        require(len(members) == len(expected) and
                {m.name for m in members} == set(expected), 'Duplicate or missing archive member')
        # Check every member and existing target before creating anything.
        for member in members:
            item = expected[member.name]
            path = safe_path(target, member.name)
            require(member.mode == item['mode'] and member.mode & ~0o777 == 0,
                    'Unexpected member permissions')
            if item['type'] == 'symlink':
                require(member.issym() and member.linkname == item['target'] and
                        PurePosixPath(item['target']).name == item['target'] and
                        item['target'] not in ('', '.', '..'), 'Unexpected symbolic link')
            else:
                require(item['type'] == 'file' and member.isfile() and member.size == item['bytes'],
                        'Unexpected member type/size')
                require(hashlib.sha256(stream.extractfile(member).read()).hexdigest() == item['sha256'],
                        'Member bytes differ: ' + member.name)
            if path.exists() or path.is_symlink():
                require(matches(path, item), 'Refusing to overwrite different evidence: ' + member.name)
        for member in members:
            item = expected[member.name]
            path = safe_path(target, member.name)
            if path.exists() or path.is_symlink():
                existing += 1
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            if item['type'] == 'symlink':
                os.symlink(item['target'], str(path))
            else:
                with path.open('xb') as output:
                    output.write(stream.extractfile(member).read())
                path.chmod(item['mode'])
            require(matches(path, item), 'Restored bytes differ: ' + member.name)
            restored += 1
    print(json.dumps(dict(status='verified_lossless', restored=restored,
                         already_identical=existing, members=len(expected)), sort_keys=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', required=True)
    restore(parser.parse_args().destination)
