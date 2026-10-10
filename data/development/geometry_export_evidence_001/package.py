#!/usr/bin/env python3
"""Package the explicit completed/draft evidence roster without changing inputs."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PACKAGES = [
    'hayward_full_dd_geometry_export_candidate_001',
    'hayward_full_dd_geometry_export_controls_001',
    'hayward_full_dd_geometry_export_controls_002',
]
SOURCES = []
# Exact final reviews and their frozen prerequisites; no new scientific gate.
PINS = {
    PACKAGES[0] + '/prepared.json': '082426a6b05f6006deecff368cb22ea347cffa70a49b8a3ef7257ca566e50263',
    PACKAGES[0] + '/root_source_review.json': '9497a06dbda165bf3b498ebd7bc3e3defdd23d88f2372260a94da9593b0aadab',
    PACKAGES[1] + '/prepared.json': '0f5207d5ad5ae08c5a91ae1761152764cdfef47f7ca87464296bfd6ffb222bc7',
    PACKAGES[2] + '/prepared.json': '833201e5c9b6156d34940208972508a94c36b21c6b56b5a3d3f6d0febe4243bb',
    PACKAGES[2] + '/prelaunch_review.json': '2b127dcf79caf6aa39fb4e0af729bafcc2d5bd464e245b2a743c7c3853f17d57',
    PACKAGES[2] + '/summary.json': 'f090766ef2bafd6aeaeb049506800d566386fffaac2e2feacd6762f94a1428a2',
    PACKAGES[2] + '/execution.json': '34255a4ca3fa9a3551b922ea9aed94fbbbe07b5dcb91c5f394793d447b2ebaeb',
    PACKAGES[2] + '/review.json': '87e8e5599fe7d087c49042f043d3b2e8db007cf5ae401d4405bb91a0838d891b',
    PACKAGES[2] + '/review_saved.py': '0e50e976f5ca586c06fb87c119b22ce467d1f1c8970df8bde57bab6b6b583598',
    PACKAGES[2] + '/RESULTS.md': '0235279020bd7e1efa3d5ff147af27b541440c93e0f177b1aaabe6dc676f21ae',
    PACKAGES[2] + '/controller_provenance/completion.json': 'f7f496ef5ea38db6495545cc8b59a8b4bdce9781c2d7fee3ad8fbb309080fa0f',
}


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def save(path, data):
    with path.open('x') as stream:
        json.dump(data, stream, indent=2, sort_keys=True)
        stream.write('\n')


def main():
    if not __debug__:
        raise RuntimeError('Do not disable integrity assertions')
    assert not any((HERE/n).exists() for n in ('evidence.tar.gz', 'members.json', 'packaging.json', 'dependencies.json'))
    base = ROOT/'data/development'
    for name, digest in PINS.items():
        assert sha(base/name) == digest, name
    dependencies = {}
    runtime = {}
    pin_counts = {}
    for name in PACKAGES:
        directory = base/name
        prepared = json.loads((directory/'prepared.json').read_text())
        counts = {}
        for key in ('input_sha256', 'original_sha256', 'output_sha256', 'runtime_sha256'):
            entries = prepared.get(key, {})
            counts[key] = len(entries)
            for rel, digest in entries.items():
                path = directory/rel if key == 'output_sha256' else ROOT/rel
                assert sha(path) == digest, str(path)
                if key == 'runtime_sha256':
                    assert Path(rel).is_absolute()
                    assert rel not in runtime or runtime[rel] == digest
                    runtime[rel] = digest
                elif key != 'output_sha256':
                    assert not Path(rel).is_absolute() and '..' not in Path(rel).parts
                    assert rel not in dependencies or dependencies[rel] == digest
                    dependencies[rel] = digest
        pin_counts[name] = counts
    draft = base/PACKAGES[1]
    assert not any((draft/n).exists() for n in ('execution.json', 'summary.json', 'build', 'results', 'logs'))
    candidate = base/PACKAGES[0]
    source_review = json.loads((candidate/'root_source_review.json').read_text())
    assert source_review['status'] == 'passed_source_review'
    assert source_review['prepared_sha256'] == sha(candidate/'prepared.json')
    assert source_review['after_header_sha256'] == sha(candidate/'after/src/full_linearization.hpp')
    assert source_review['candidate_patch_sha256'] == sha(candidate/'candidate.patch')
    terminal = base/PACKAGES[2]
    review = json.loads((terminal/'review.json').read_text())
    summary = json.loads((terminal/'summary.json').read_text())
    execution = json.loads((terminal/'execution.json').read_text())
    prelaunch = json.loads((terminal/'prelaunch_review.json').read_text())
    assert review['status'] == summary['status'] == prelaunch['status'] == 'passed'
    assert summary['passed'] == summary['total'] == review['control_records'] == 82
    assert execution['status'] == 'completed' and execution['return_code'] == 0
    assert execution['all_direct_children_reaped'] and len(execution['commands']) == 34
    assert all(c['reaped'] and c['return_code'] == c['expected_return_code'] for c in execution['commands'])
    assert execution['summary_sha256'] == sha(terminal/'summary.json')
    assert execution['prepared_sha256'] == summary['prepared_sha256'] == prelaunch['prepared_sha256'] == sha(terminal/'prepared.json')
    assert execution['prelaunch_review_sha256'] == sha(terminal/'prelaunch_review.json')
    assert review['checker_sha256'] == sha(terminal/'review_saved.py')
    for key in ('input_sha256',):
        for rel, digest in review[key].items():
            assert sha(terminal/rel) == digest
    for rel, digest in prelaunch['source_sha256'].items():
        assert sha(terminal/rel) == digest
    for rel, digest in summary['artifact_sha256'].items():
        assert sha(terminal/rel) == digest
    completion_dir = terminal/'controller_provenance'
    completion = json.loads((completion_dir/'completion.json').read_text())
    assert completion['status'] == 'completed' and completion['child_reaped'] and completion['child_return_code'] == 0
    assert completion['execution_sha256'] == sha(terminal/'execution.json')
    assert completion['summary_sha256'] == sha(terminal/'summary.json')
    for name in ('controller.py', 'stdout.log', 'stderr.log'):
        key = 'controller_sha256' if name == 'controller.py' else name.split('.')[0] + '_sha256'
        assert completion[key] == sha(completion_dir/name)
    files = [ROOT/name for name in SOURCES]
    for name in PACKAGES:
        directory = ROOT/'data/development'/name
        assert directory.is_dir() and not directory.is_symlink(), name
        files.extend(p for p in directory.rglob('*') if p.is_file() or p.is_symlink())
    files = sorted(files, key=lambda p: str(p.relative_to(ROOT)))
    members = {}
    for path in files:
        rel = str(path.relative_to(ROOT))
        assert rel not in members and '__pycache__' not in path.parts and path.suffix != '.pyc'
        assert path.name != 'execution.lock', 'Live runtime state is outside the evidence package'
        item = dict(mode=path.lstat().st_mode & 0o777)
        if path.is_symlink():
            target = os.readlink(str(path))
            assert Path(target).name == target and target not in ('', '.', '..')
            item.update(type='symlink', target=target)
        else:
            item.update(type='file', bytes=path.stat().st_size, sha256=sha(path))
        members[rel] = item
    # Complete source closure is retained; historical prerequisites and system
    # runtimes remain explicit rather than silently copying installed binaries.
    dependencies = {name: dict(sha256=digest, archived_at_original_path=name in members,
                              byte_identical_archived_files=[n for n, m in members.items()
                                  if m['type'] == 'file' and m['sha256'] == digest])
                    for name, digest in sorted(dependencies.items())}
    save(HERE/'dependencies.json', dict(original_inputs=dependencies, runtime_sha256=runtime,
                                        verified_prepared_pin_counts=pin_counts,
                                        runtime_policy='Recorded hashes only; system runtimes are not archived.'))
    compiled = {}
    for name, item in members.items():
        if item['type'] == 'file':
            with (ROOT/name).open('rb') as stream:
                if stream.read(4) == b'\x7fELF':
                    compiled[name] = item
    expected_elf = {'data/development/' + PACKAGES[2] + '/build/' + name
                    for name in ('before', 'after', 'after_io')}
    assert set(compiled) == expected_elf
    assert not any(item['type'] == 'symlink' for item in members.values())
    save(HERE/'members.json', dict(packages=PACKAGES, sources=SOURCES, members=members))
    archive = HERE/'evidence.tar.gz'
    with archive.open('xb') as raw:
        with gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode='w', format=tarfile.PAX_FORMAT) as stream:
                for name, item in sorted(members.items()):
                    info = tarfile.TarInfo(name)
                    info.mode = item['mode']; info.mtime = 0
                    if item['type'] == 'symlink':
                        info.type = tarfile.SYMTYPE; info.linkname = item['target']
                        stream.addfile(info)
                    else:
                        info.size = item['bytes']
                        with (ROOT/name).open('rb') as source:
                            stream.addfile(info, source)
    # Read back all archive members and recheck the untouched original files.
    with tarfile.open(str(archive), 'r:gz') as stream:
        records = stream.getmembers()
        assert len(records) == len(members) and {m.name for m in records} == set(members)
        for record in records:
            item = members[record.name]; path = ROOT/record.name
            assert record.mode == item['mode'] == path.lstat().st_mode & 0o777
            if item['type'] == 'symlink':
                assert record.issym() and record.linkname == item['target'] == os.readlink(str(path))
            else:
                assert record.isfile() and record.size == item['bytes']
                assert hashlib.sha256(stream.extractfile(record).read()).hexdigest() == item['sha256'] == sha(path)
    with gzip.open(str(archive), 'rb') as stream:
        while stream.read(1048576):
            pass  # Consume the trailer and verify the gzip CRC.
    result = dict(status='verified_lossless', archive=archive.name,
                  archive_sha256=sha(archive), archive_bytes=archive.stat().st_size,
                  members_sha256=sha(HERE/'members.json'), member_count=len(members),
                  regular_file_bytes=sum(m.get('bytes', 0) for m in members.values()),
                  symbolic_links=sum(m['type'] == 'symlink' for m in members.values()),
                  package_script_sha256=sha(Path(__file__)), restore_script_sha256=sha(HERE/'restore.py'),
                  dependencies_sha256=sha(HERE/'dependencies.json'), compiled_binaries=compiled,
                  review_gate_sha256=PINS,
                  scope='Exact three-package geometry evidence: source-only candidate, unexecuted001, terminal reviewed002; no field calculation or scientific acceptance added.')
    save(HERE/'packaging.json', result)
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
