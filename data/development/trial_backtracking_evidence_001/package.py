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
    'hayward_trial_backtracking_candidate_001',
    'hayward_trial_backtracking_candidate_002',
    'hayward_trial_backtracking_candidate_003',
    'hayward_trial_backtracking_controls_001',
    'hayward_trial_backtracking_controls_002',
    'hayward_trial_backtracking_integration_checks_001',
    'hayward_old_kernel_trial_backtracking_candidate_001',
    'hayward_old_kernel_trial_backtracking_controls_001',
    'hayward_old_kernel_trial_backtracking_integration_checks_001',
    'hayward_old_kernel_trial_backtracking_integration_checks_002',
    'hayward_trial_completion_candidate_001',
    'hayward_trial_completion_candidate_002',
    'hayward_trial_completion_checks_001',
    'hayward_trial_completion_checks_002',
    'hayward_trial_completion_review_002',
    'hayward_old_kernel_backtracking_launcher_001',
    'hayward_old_kernel_backtracking_launcher_checks_001',
    'hayward_old_kernel_backtracking_launcher_checks_002',
    'internal_ridge_stationarity_controls_001',
]
SOURCES = [
    'diagnostics/check_trial_backtracking.cpp',
    'diagnostics/run_trial_backtracking_checks.py',
    'diagnostics/run_old_kernel_trial_backtracking_checks.py',
    'diagnostics/review_old_kernel_trial_completion.py',
    'diagnostics/check_old_kernel_backtracking_launcher.py',
    'run_hayward_old_kernel_backtracking.py',
]
REVIEWS = {
    'hayward_trial_backtracking_controls_002': ('review.json', '56a4dd3aa36539344a51a97feeaf5c91ab560d1a52b1fafba8974f886f8f0bb3'),
    'hayward_old_kernel_trial_backtracking_controls_001': ('review.json', 'fc750af56ea2d2333c7c1c2856a629181ca96a233fec2fd831ee5fd82b5bad5f'),
    'hayward_old_kernel_trial_backtracking_integration_checks_002': ('review.json', '7faa22a6bb009a3c8c5470ffb4e7cff6dddf02987dfb3c18db032f7e362fdda6'),
    'hayward_trial_completion_checks_002': ('review.json', 'e975435edc021696f0e8766e6e7bcb15a45c8bfa2d09e09388ad4e35e2e7374c'),
    'internal_ridge_stationarity_controls_001': ('root_review.json', 'e50ad3b89cb9908fc9aed91509b2fc85f326e007a38545c271da84a3bbacd6a7'),
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
    assert not any((HERE/n).exists() for n in ('evidence.tar.gz', 'members.json', 'packaging.json'))
    # Numerical failures and source-only drafts belong in the record. Require
    # the completed suites and launcher review before closing this package.
    for name, (review_name, digest) in REVIEWS.items():
        p = ROOT/'data/development'/name
        assert sha(p/review_name) == digest
        review = json.loads((p/review_name).read_text())
        summary = json.loads((p/'summary.json').read_text())
        execution = json.loads((p/'execution.json').read_text())
        assert review['status'] == summary['status'] == 'passed'
        assert execution['status'] == 'completed' and execution['return_code'] == 0
        assert review.get('summary_sha256', review.get('controls_summary_sha256')) == sha(p/'summary.json')
        assert review['execution_sha256'] == sha(p/'execution.json')
        assert execution['prepared_sha256'] == summary['prepared_sha256'] == sha(p/'prepared.json')
        for key in ('artifact_sha256', 'output_sha256', 'source_sha256'):
            for rel, expected in summary.get(key, {}).items():
                assert sha(p/rel) == expected, rel
        for rel, target in summary.get('intentional_symlinks', {}).items():
            assert (p/rel).is_symlink() and os.readlink(str(p/rel)) == target
    launcher = ROOT/'data/development/hayward_old_kernel_backtracking_launcher_001'
    assert sha(launcher/'prepared.json') == '39593013076b06ce0ab5fac64d9ac4ec7d23f272762dbbdb6931fc002df8cf3d'
    assert sha(launcher/'root_source_review.json') == '658551b39b919cb85f332e212f366cada88d330ed80f24796a2b6ec41a48075f'
    prepared = json.loads((launcher/'prepared.json').read_text())
    for key in ('input_sha256', 'original004_required_sha256'):
        for rel, expected in prepared[key].items():
            assert sha(ROOT/rel) == expected, rel
    for rel, expected in prepared['source_sha256'].items():
        assert sha(ROOT/prepared['source_mapping'][rel]) == expected, rel
    checks = ROOT/'data/development/hayward_old_kernel_backtracking_launcher_checks_002'
    assert sha(checks/'review.json') == '8ee63a3c7e825d5ce75d5d70de023b3f67d13fceea8ae5855583752d14848b22'
    review = json.loads((checks/'review.json').read_text())
    summary = json.loads((checks/'summary.json').read_text())
    execution = json.loads((checks/'execution.json').read_text())
    assert review['status'] == summary['status'] == 'passed'
    assert execution['status'] == 'completed' and execution['return_code'] == 0 and execution['child_reaped']
    assert review['summary_sha256'] == execution['summary_sha256'] == sha(checks/'summary.json')
    assert review['execution_sha256'] == sha(checks/'execution.json')
    assert review['prepared_sha256'] == execution['prepared_sha256'] == sha(checks/'prepared.json')
    assert review['launcher_prepared_sha256'] == summary['prepared_sha256'] == sha(launcher/'prepared.json')
    assert review['root_source_review_sha256'] == sha(launcher/'root_source_review.json')
    for rel, expected in summary['artifact_sha256'].items():
        assert sha(checks/rel) == expected, rel
    for rel, expected in summary['source_sha256'].items():
        assert sha(ROOT/rel) == expected, rel
    for rel, expected in execution['log_sha256'].items():
        assert sha(checks/rel) == expected, rel
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
                  scope='Exact saved evidence including failed controls and source-only drafts; packaging adds no numerical acceptance.')
    save(HERE/'packaging.json', result)
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
