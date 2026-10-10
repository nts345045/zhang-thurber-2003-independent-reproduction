#!/usr/bin/env python3
"""Archive/verify/restore a terminal failed run; never execute its binary."""
import sys
sys.dont_write_bytecode = True
import argparse
import csv
import gzip
import hashlib
import json
import shutil
import subprocess
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path, PurePosixPath

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RUN = ROOT/'data/hayward_first_arrival_guarded_001'
BLOCK = 1024*1024


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(stream, output=None):
    h, count = hashlib.sha256(), 0
    for chunk in iter(lambda: stream.read(BLOCK), b''):
        h.update(chunk)
        count += len(chunk)
        if output is not None:
            output.write(chunk)
    return {'sha256': h.hexdigest(), 'bytes': count}


def info(path):
    with path.open('rb') as stream:
        return digest(stream)


def write_json(path, data):
    with path.open('x') as stream:
        json.dump(data, stream, indent=2, sort_keys=True)
        stream.write('\n')


def safe(name):
    p = PurePosixPath(name)
    require(name and not p.is_absolute() and '..' not in p.parts and
            str(p) == name and '\\' not in name, 'Unsafe member: '+name)
    return name


def inventory(directory):
    result = {}
    for p in sorted(directory.rglob('*')):
        require(not p.is_symlink() and (p.is_file() or p.is_dir()), 'Nonregular input')
        if p.is_file():
            result[safe(p.relative_to(directory).as_posix())] = p
    return result


def verify(restore=None):
    manifest_path = HERE/'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    require(manifest['format'] == 'gzip-tar-member-sha256-v1', 'Unknown format')
    require(info(HERE/'package.py')['sha256'] == manifest['packager_sha256'], 'Packager source changed')
    for name, expected in manifest['readable_files'].items():
        require(info(HERE/safe(name)) == expected, 'Readable file changed: '+name)
    for name, expected in manifest['external_repository_files'].items():
        require(info(ROOT/safe(name)) == expected, 'External evidence changed: '+name)
    if restore is not None:
        require('..' not in restore.parts, 'Parent traversal in restore path')
        target = restore.absolute()
        target.relative_to(ROOT)
        require(not target.exists() and not target.is_symlink(), 'Restore destination exists')
        require(not any(p.is_symlink() for p in [target]+list(target.parents)), 'Symlinked restore path')
        target.mkdir(parents=True)
        restore = target
    seen = set()
    # A bounded temporary compressed copy keeps the ordinary one-file case
    # and optional split case identical without a custom stream framework.
    with tempfile.TemporaryFile(dir=str(ROOT/'tmp')) as compressed:
        overall = hashlib.sha256()
        total = 0
        for part in manifest['archive_files']:
            p = HERE/safe(part['file'])
            with p.open('rb') as stream:
                actual = digest(stream)
            require(actual == {k: part[k] for k in ('bytes', 'sha256')}, 'Archive file changed')
            require(actual['bytes'] < 100*BLOCK, 'Published archive file reaches100MiB')
            with p.open('rb') as stream:
                for chunk in iter(lambda: stream.read(BLOCK), b''):
                    compressed.write(chunk); overall.update(chunk); total += len(chunk)
        require(total == manifest['compressed_bytes'] and overall.hexdigest() == manifest['compressed_sha256'], 'Compressed stream mismatch')
        compressed.seek(0)
        with gzip.GzipFile(fileobj=compressed, mode='rb') as zipped:
            with tarfile.open(fileobj=zipped, mode='r|') as archive:
                for member in archive:
                    name = safe(member.name)
                    require(member.isfile() and name not in seen and name in manifest['members'], 'Unexpected archive member')
                    expected = manifest['members'][name]
                    require(member.size == expected['bytes'], 'Member header size mismatch')
                    stream = archive.extractfile(member)
                    if restore is None:
                        actual = digest(stream)
                    else:
                        path = restore/name
                        path.parent.mkdir(parents=True, exist_ok=True)
                        with path.open('xb') as output:
                            actual = digest(stream, output)
                        path.chmod(member.mode & 0o777)
                    require(actual == {k: expected[k] for k in ('bytes', 'sha256')}, 'Member bytes differ: '+name)
                    seen.add(name)
            # Consume the gzip footer/CRC, not merely the tar end marker.
            while zipped.read(BLOCK):
                pass
        require(compressed.tell() == total, 'Compressed stream was not fully consumed')
    require(seen == set(manifest['members']), 'Missing archive members')
    return {'status': 'passed', 'manifest_sha256': info(manifest_path)['sha256'],
            'verified_members': len(seen), 'verified_member_bytes': sum(v['bytes'] for v in manifest['members'].values()),
            'compressed_bytes': total, 'compressed_sha256': overall.hexdigest(),
            'external_repository_pins_verified': len(manifest['external_repository_files']),
            'readable_files_verified': len(manifest['readable_files']),
            'restore': str(restore.relative_to(ROOT)) if restore else None,
            'scope': 'Complete raw-byte inventory/hash/gzip readback only; scientific classification is separate.'}


def create():
    require(not (HERE/'manifest.json').exists() and not (HERE/'archive').exists(), 'Archive already exists')
    files = inventory(RUN)
    raw_info = {name: info(path) for name, path in files.items()}
    ledger = json.loads(files['dd_inversion_execution.json'].read_text())
    run = json.loads(files['dd_inversion_run_manifest.json'].read_text())
    completion = json.loads(files['controller_provenance/completion.json'].read_text())
    require(ledger['status'] == completion['status'] == 'failed' and
            ledger['return_code'] == completion['driver_return_code'] == 1 and
            completion['child_reaped'] is True and ledger['scientific_success'] is False,
            'Expected reaped terminal failed run')
    for name in ('dd_inversion_execution.json', 'dd_inversion_run_manifest.json'):
        require(completion[name+'_sha256'] == raw_info[name]['sha256'], 'Controller terminal linkage')
    for group in ('input_sha256', 'copied_provenance_sha256', 'build_provenance_sha256'):
        for name, expected in run[group].items():
            require(raw_info[name]['sha256'] == expected, 'Run pin changed: '+name)
    for name, expected in ledger['partial_output_sha256'].items():
        require(raw_info[name]['sha256'] == expected, 'Terminal output changed: '+name)
    require(raw_info['guarded_source.tar.gz']['sha256'] == run['source_archive_sha256'], 'Source archive changed')
    with tarfile.open(str(files['guarded_source.tar.gz']), 'r:gz') as source:
        members = source.getmembers()
        require(len(members) == len(run['source_sha256']), 'Frozen source inventory count')
        for member in members:
            require(member.isfile() and member.name in run['source_sha256'], 'Unexpected frozen source')
            require(digest(source.extractfile(member))['sha256'] == run['source_sha256'][member.name], 'Frozen source member changed')
    with files['dd_history.csv'].open() as stream:
        require(not list(csv.DictReader(stream)), 'Expected no accepted history rows')
    require(not any(name in files for name in ('dd_events.csv', 'dd_grid.csv', 'dd_residuals.csv', 'dd_output_contract.json')), 'Unexpected accepted final result')
    binary = ROOT/run['binary']
    require(info(binary)['sha256'] == run['binary_sha256'], 'Executed binary changed')
    members = {'run/'+name: path for name, path in files.items()}
    members['execution_provenance/dd'] = binary
    tracked = set(subprocess.check_output(['git', 'ls-files', '-z'], cwd=str(ROOT)).decode().strip('\0').split('\0'))
    external, dependencies = {}, {}
    for name, expected in run['inherited_evidence_sha256'].items():
        p = ROOT/name
        actual = info(p)
        require(actual['sha256'] == expected, 'Inherited evidence changed: '+name)
        matches = [key for key, value in raw_info.items() if value == actual]
        if matches:
            dependencies[name] = {'sha256': expected, 'archive_member': 'run/'+sorted(matches)[0]}
        elif name in tracked:
            external[name] = actual
            dependencies[name] = {'sha256': expected, 'repository_file': name}
        else:
            key = 'inherited_samples/'+p.name
            require(key not in members, 'Duplicate supplementary basename')
            members[key] = p
            dependencies[name] = {'sha256': expected, 'archive_member': key}
    member_info = {name: dict(info(p), original_repository_path=str(p.relative_to(ROOT))) for name, p in sorted(members.items())}
    readable_names = ['dd_failed_forward_context.csv', 'dd_failed_forward_ray_failures.csv',
                      'dd_history.csv', 'dd_matrix_preflight.csv', 'dd_inversion_execution.json',
                      'dd_inversion_run_manifest.json', 'controller_provenance/completion.json',
                      'dd_invert_stderr.log', 'initial_events.csv', 'stations.csv', 'initial_grid.csv',
                      'run.cfg', 'authoritative_ids_required']
    readable = {}
    for name in readable_names:
        target = HERE/'readable'/name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write(files[name].read_bytes())
        readable['readable/'+name] = info(target)
        require(readable['readable/'+name] == raw_info[name], 'Readable copy mismatch')
    work = ROOT/'tmp/hayward_guarded_failure_archive_001'
    work.mkdir()
    temporary = work/'failed_run.tar.gz'
    with temporary.open('xb') as stream:
        with gzip.GzipFile(fileobj=stream, mode='wb', filename='', mtime=0, compresslevel=6) as zipped:
            with tarfile.open(fileobj=zipped, mode='w|', format=tarfile.PAX_FORMAT) as archive:
                for name, path in sorted(members.items()):
                    meta = tarfile.TarInfo(name)
                    meta.size = member_info[name]['bytes']
                    meta.mode = path.stat().st_mode & 0o777
                    meta.mtime = 0; meta.uid = meta.gid = 0
                    with path.open('rb') as source:
                        archive.addfile(meta, source)
    compressed_info = info(temporary)
    (HERE/'archive').mkdir()
    parts = []
    if compressed_info['bytes'] < 100*BLOCK:
        target = HERE/'archive/failed_run.tar.gz'
        shutil.copyfile(str(temporary), str(target))
        parts.append(dict(info(target), file='archive/failed_run.tar.gz'))
    else:
        with temporary.open('rb') as stream:
            number = 0
            while True:
                chunk = stream.read(50*BLOCK)
                if not chunk:
                    break
                target = HERE/('archive/failed_run.tar.gz.part%04d' % number)
                with target.open('xb') as output:
                    output.write(chunk)
                parts.append(dict(info(target), file=target.relative_to(HERE).as_posix()))
                number += 1
    require(all(info(path) == raw_info[name] for name, path in files.items()), 'Original run changed while packaging')
    require(set(inventory(RUN)) == set(files), 'Original run inventory changed')
    require(all(info(path) == {k: member_info[name][k] for k in ('sha256', 'bytes')} for name, path in members.items()), 'Consumed member changed')
    write_json(HERE/'manifest.json', {
        'format': 'gzip-tar-member-sha256-v1', 'created_utc': datetime.utcnow().isoformat()+'Z',
        'packager_sha256': info(Path(__file__).resolve())['sha256'],
        'original_run': str(RUN.relative_to(ROOT)), 'original_run_file_count': len(files),
        'original_run_unchanged': True, 'all_original_run_files_archived': True,
        'archive_files': parts, 'compressed_bytes': compressed_info['bytes'], 'compressed_sha256': compressed_info['sha256'],
        'members': member_info, 'readable_files': readable,
        'external_repository_files': external, 'inherited_evidence_resolution': dependencies,
        'frozen_source_members_verified': len(run['source_sha256']),
        'executed_binary_sha256': run['binary_sha256'], 'executed_binary_member': 'execution_provenance/dd',
        'native_identity_mapping': {
            'events': 'run/initial_events.csv', 'receivers_with_native_epochs': 'run/stations.csv',
            'original_catalog_observations': 'run/observations.csv',
            'failed_trial_events': 'run/dd_failed_forward_events.csv',
            'all_ray_status_and_native_metadata': 'run/dd_failed_forward_ray_status.csv',
            'failed_paths_with_native_metadata': 'run/dd_failed_forward_ray_paths.csv',
            'failed_ray_roster': 'run/dd_failed_forward_ray_failures.csv'},
        'outcome': {'terminal_status': 'failed', 'exit_code': 1, 'accepted_updates': 0,
                    'final_accepted_solution_written': False,
                    'last_accepted_tables_are_starting_state_not_an_inferred_solution': True},
        'limitations': ['Byte preservation does not validate ray accuracy or an inverse result.',
                        'Full scientific/native/state classification is published separately under classification/.',
                        'Absolute project paths in original ledgers/logs are preserved as historical evidence, not portable execution commands.',
                        'The archived binary is environment-specific; compiler, flags and runtime hashes remain in the original manifest.',
                        'Only the executed binary and existing small build provenance are included; the generated CMake tree is not archived.']})
    result = verify()
    result['original_run_files_rehashed_unchanged'] = len(files)
    result['finished_utc'] = datetime.utcnow().isoformat()+'Z'
    write_json(HERE/'archive_verification.json', result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('create', 'verify'))
    parser.add_argument('--restore', type=Path)
    args = parser.parse_args()
    if args.action == 'create':
        require(args.restore is None, 'Restore belongs to verify')
        result = create()
    else:
        result = verify(args.restore)
    print(json.dumps(result, indent=2, sort_keys=True))
