#!/usr/bin/env python3
"""Losslessly package, verify, or restore an independently reviewed simulation."""
import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import tarfile

ROOT = Path(__file__).resolve().parents[1]
BLOCK = 1024 * 1024
MAX_PART = 50 * BLOCK


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(stream, target=None):
    value, size = hashlib.sha256(), 0
    for chunk in iter(lambda: stream.read(BLOCK), b''):
        value.update(chunk); size += len(chunk)
        if target is not None:
            target.write(chunk)
    return dict(sha256=value.hexdigest(), bytes=size)


def info(path):
    with path.open('rb') as stream:
        return digest(stream)


def json_write(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False); stream.write('\n')


def safe_name(name):
    path = PurePosixPath(name)
    require(name and path.parts and not path.is_absolute() and '..' not in path.parts and
            str(path) == name and '\\' not in name, 'Unsafe member path: ' + name)
    return name


def files(directory):
    paths = sorted(directory.rglob('*'))
    require(not any(p.is_symlink() for p in paths), 'Symbolic links are not simulation artifacts')
    require(all(p.is_file() or p.is_dir() for p in paths), 'Nonregular simulation artifact')
    return {safe_name(p.relative_to(directory).as_posix()): p for p in paths if p.is_file()}


class SplitWriter:
    """Write a single compressed stream directly into bounded regular files."""
    def __init__(self, directory, limit):
        self.directory, self.limit = directory, limit
        self.stream = None; self.parts = []; self.size = 0
        self.total = 0; self.hash = hashlib.sha256(); self.part_hash = None

    def finish_part(self):
        if self.stream is not None:
            self.stream.close()
            self.parts.append(dict(file=self.name, bytes=self.size, sha256=self.part_hash.hexdigest()))
            self.stream = None

    def write(self, data):
        count = len(data); view = memoryview(data)
        while view:
            if self.stream is None:
                self.name = 'simulation.tar.gz.part{:04d}'.format(len(self.parts))
                self.stream = (self.directory/self.name).open('xb')
                self.size = 0; self.part_hash = hashlib.sha256()
            take = min(len(view), self.limit-self.size); chunk = view[:take]
            self.stream.write(chunk); self.part_hash.update(chunk); self.hash.update(chunk)
            self.size += take; self.total += take; view = view[take:]
            if self.size == self.limit:
                self.finish_part()
        return count

    def flush(self):
        if self.stream is not None:
            self.stream.flush()


class PartsReader:
    """Read and hash ordered parts without concatenating them on disk or in RAM."""
    def __init__(self, directory, parts):
        self.directory, self.parts = directory, parts
        self.index = 0; self.stream = None; self.size = 0; self.total = 0
        self.hash = hashlib.sha256(); self.part_hash = None

    def read(self, size):
        require(size >= 0, 'Unbounded archive read requested')
        result = []
        while size and self.index < len(self.parts):
            part = self.parts[self.index]
            if self.stream is None:
                self.stream = (self.directory/safe_name(part['file'])).open('rb')
                self.size = 0; self.part_hash = hashlib.sha256()
            chunk = self.stream.read(size)
            if chunk:
                result.append(chunk); size -= len(chunk)
                self.part_hash.update(chunk); self.hash.update(chunk)
                self.size += len(chunk); self.total += len(chunk)
            else:
                self.stream.close(); self.stream = None
                require(self.size == part['bytes'] and self.part_hash.hexdigest() == part['sha256'],
                        'Archive part hash/size mismatch: ' + part['file'])
                self.index += 1
        return b''.join(result)


def gate(data, review_path, inventory):
    review = json.loads(review_path.read_text())
    ledger = json.loads((data/'simulation_execution.json').read_text())
    require(ledger['status'] == 'completed' and ledger['return_code'] == 0 and
            ledger['result_status'] == 'simulation_complete_awaiting_independent_output_review',
            'Simulation must be terminal and successful')
    require(review['status'] == 'passed' and review['all_native_fields_match'] is True and
            review['truth_status_all_fields_exact'] is True and review['ray_status_fields_blank'] is True,
            'Independent numerical/native output review must pass')
    require(review['simulation_execution_sha256'] == inventory['simulation_execution.json']['sha256'] and
            review['simulation_run_manifest_sha256'] == inventory['simulation_run_manifest.json']['sha256'],
            'Independent review does not identify this terminal simulation')
    required = {'observations.csv', 'arrivals.csv', 'initial_events.csv', 'truth_events.csv', 'stations.csv',
                'simulation_truth_status.csv', 'simulation_truth_mode.txt', 'analytic_truth/references.csv',
                'analytic_truth_manifest.json', 'simulation_execution.json', 'simulation_run_manifest.json',
                'simulation_source.tar.gz'}
    require(required <= set(review['input_sha256']), 'Incomplete reviewed simulation inventory')
    for name, expected in review['input_sha256'].items():
        safe_name(name)
        require(name in inventory and inventory[name]['sha256'] == expected, 'Reviewed artifact changed: ' + name)
    for name, expected in ledger['output_sha256'].items():
        require(review['input_sha256'].get(name) == expected, 'Unreviewed terminal output: ' + name)
    run = json.loads((data/'simulation_run_manifest.json').read_text())
    expected = run['expected_counts']
    require(review['arrival_count'] == expected['unique_rays'] and review['total_observations'] == expected['total_rows'] and
            review['observation_counts_by_type'] == [expected[k] for k in ('absolute_rows','catalog_rows','precise_rows')],
            'Independent review does not cover full declared observation support')
    return review, expected


def verify(package, manifest, restore=None):
    require(manifest['format'] == 'split-gzip-tar-v1', 'Unknown archive format')
    parts = manifest['parts']
    require(parts and all(0 < p['bytes'] <= MAX_PART for p in parts), 'Invalid part size')
    require([p['file'] for p in parts] == ['simulation.tar.gz.part{:04d}'.format(i) for i in range(len(parts))],
            'Parts must be unique and in sequence')
    for name, expected in manifest['readable_files'].items():
        require(info(package/safe_name(name)) == expected, 'Readable evidence changed: ' + name)
    members = manifest['members']; seen = set()
    for name in members:
        safe_name(name)
    if restore is not None:
        restore.mkdir(parents=True)  # Exclusive: never overwrite a prior run or restore.
    reader = PartsReader(package, parts)
    with gzip.GzipFile(fileobj=reader, mode='rb') as zipped:
        with tarfile.open(fileobj=zipped, mode='r|') as archive:
            for member in archive:
                name = safe_name(member.name)
                require(member.isfile() and name in members and name not in seen, 'Unexpected/duplicate/nonregular member: ' + name)
                require(member.size == members[name]['bytes'], 'Tar member size differs: ' + name)
                source = archive.extractfile(member)
                if restore is None:
                    actual = digest(source)
                else:
                    target = restore/name; target.parent.mkdir(parents=True, exist_ok=True)
                    with target.open('xb') as stream:
                        actual = digest(source, stream)
                    target.chmod(member.mode & 0o777)
                require(actual == members[name], 'Tar member bytes differ: ' + name)
                seen.add(name)
        # Read through gzip trailer/CRC and all parts; tar EOF alone is insufficient.
        while zipped.read(BLOCK):
            pass
    require(seen == set(members), 'Missing archive members')
    require(reader.index == len(parts) and reader.total == manifest['compressed_bytes'] and
            reader.hash.hexdigest() == manifest['compressed_sha256'], 'Incomplete compressed stream')
    return dict(status='passed', members_verified=len(seen), parts_verified=len(parts),
                uncompressed_bytes=sum(x['bytes'] for x in members.values()),
                all_member_hashes_and_sizes_match=True, compressed_stream_hash_and_gzip_crc_match=True)


def package(data, review_path, output, part_bytes):
    require(0 < part_bytes <= MAX_PART, 'Part bound must be at most 50 MiB')
    require(not output.exists(), 'Preserve prior publication output; use a fresh directory')
    require(data != output and data not in output.parents and output not in data.parents, 'Archive output must be separate from original data')
    # Check terminal status before hashing a potentially growing large CSV.
    ledger = json.loads((data/'simulation_execution.json').read_text())
    require(ledger['status'] == 'completed' and ledger['return_code'] == 0, 'Do not archive a live or failed simulation')
    require(json.loads(review_path.read_text())['status'] == 'passed', 'Independent review has not passed')
    originals = files(data); inventory = {name:info(path) for name,path in originals.items()}
    review, counts = gate(data, review_path, inventory)
    review_info = info(review_path)
    output.mkdir(parents=True)  # Fresh publication directory only.
    json_write(output/'execution.json', dict(status='packaging', original_data=str(data.relative_to(ROOT))))
    writer = SplitWriter(output, part_bytes)
    try:
        native_names = {'truth_events.csv','initial_events.csv','stations.csv',
                        'analytic_truth/inputs/truth_events.csv','analytic_truth/inputs/stations.csv'}
        readable = {}
        for name,path in originals.items():
            if path.suffix.lower() in ('.json','.md','.cfg','.txt','.log') or name in native_names or name == 'authoritative_geometry':
                require(inventory[name]['bytes'] <= MAX_PART, 'Readable evidence exceeds 50 MiB: ' + name)
                target = output/'readable'/name; target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(str(path),str(target)); readable['readable/'+name] = info(target)
                require(readable['readable/'+name] == inventory[name], 'Readable copy changed')
        shutil.copyfile(str(review_path),str(output/'independent_output_review.json'))
        readable['independent_output_review.json'] = info(output/'independent_output_review.json')
        require(readable['independent_output_review.json'] == review_info, 'Review changed during copy')
        identity_tables = []
        for name in sorted(native_names-{'initial_events.csv'}):
            columns = (['event_resource_id','origin_resource_id'] if name.endswith('truth_events.csv') else
                       ['network_code','station_code','location_code','channel_code','channel_seed_id',
                        'channel_fdsn_source_id','metadata_epoch_start','metadata_epoch_end'])
            with (data/name).open() as stream:
                reader = csv.DictReader(stream); rows = list(reader)
            require(set(columns) <= set(reader.fieldnames), 'Native identity columns missing: ' + name)
            require(len(rows) == counts['events' if name.endswith('truth_events.csv') else 'receivers'],
                    'Native identity-table support differs: ' + name)
            require(all(r[k] for r in rows for k in columns if k not in ('location_code','metadata_epoch_end')),
                    'Native identity missing: ' + name)
            identity_tables.append(dict(archived_member=name,readable_file='readable/'+name,
                rows=len(rows),identifier_columns=columns,sha256=inventory[name]['sha256']))
        with gzip.GzipFile(filename='',fileobj=writer,mode='wb',compresslevel=1,mtime=0) as zipped:
            with tarfile.open(fileobj=zipped,mode='w|',format=tarfile.PAX_FORMAT) as archive:
                for name,path in originals.items():
                    member = tarfile.TarInfo(name); member.size = inventory[name]['bytes']
                    member.mode = path.stat().st_mode & 0o777
                    with path.open('rb') as stream:
                        archive.addfile(member,stream)
        writer.finish_part()
        manifest = dict(format='split-gzip-tar-v1',status='pending_readback',
            scope='Lossless publication of synthetic observations and their authoritative native geometry/identities; not an inversion or observed waveform dataset',
            original_data=str(data.relative_to(ROOT)), originals_retained=True, counts=counts,
            independent_review_sha256=review_info['sha256'], simulation_execution_sha256=review['simulation_execution_sha256'],
            simulation_run_manifest_sha256=review['simulation_run_manifest_sha256'],
            identity_mapping=dict(native_tables=identity_tables,
                observation_table='observations.csv',
                observation_identity_basis='Every original observation byte is retained, including both native event/origin identifiers and channel/epoch fields. Derived synthetic records are not provider picks.'),
            members=inventory, readable_files=readable, parts=writer.parts, part_size_limit_bytes=part_bytes,
            compression='gzip level 1; deterministic header; one tar stream across all parts',
            compressed_bytes=writer.total,compressed_sha256=writer.hash.hexdigest(),
            helper_sha256=info(Path(__file__))['sha256'])
        result = verify(output,manifest)
        require(files(data) == originals, 'Original run file inventory changed during packaging')
        for name,path in originals.items():
            require(info(path) == inventory[name], 'Original artifact changed during packaging: ' + name)
        require(info(review_path) == review_info, 'Independent review changed during packaging')
        manifest['status'] = 'verified'; json_write(output/'manifest.json',manifest)
        result['manifest_sha256'] = info(output/'manifest.json')['sha256']; json_write(output/'verification.json',result)
        (output/'README.md').write_text('''# Lossless simulation publication

The original local run is retained unchanged. `manifest.json` records each tar
member and each part's SHA-256 and byte count, reviewed completion hashes,
synthetic observation counts, and native identity-table mappings. `readable/`
keeps manifests, configuration, logs, and native event/channel tables accessible.
`independent_output_review.json` is the accepted numerical/native review.
All observations are synthetic; authoritative resource IDs identify geometry,
not new provider picks. This package does not establish inversion accuracy.

Parts are consecutive bytes of one gzip-compressed tar stream, each at most
50 MiB. Keep every part in order. Verification and restore use bounded memory:

```sh
python3 diagnostics/package_loma_simulation.py verify --package PACKAGE
python3 diagnostics/package_loma_simulation.py restore --package PACKAGE --output FRESH_DIRECTORY
```

Replace PACKAGE with this directory. The restore directory must not exist.
Restore verifies member paths, sizes, hashes, part hashes, and gzip integrity;
a failed restore leaves its partial directory for inspection. No record IDs,
CSV formatting, or numerical precision are changed by compression. Publish
this directory and the helper, not the multi-gigabyte original CSV files.
''')
        (output/'execution.json').write_text(json.dumps(dict(status='completed',manifest_sha256=result['manifest_sha256']),indent=2)+'\n')
        return result
    except BaseException as error:
        writer.finish_part()
        json_write(output/'failure.json',dict(status='failed',error_type=type(error).__name__,error=str(error)))
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command')
    create = sub.add_parser('package'); create.add_argument('--data',required=True)
    create.add_argument('--review',required=True); create.add_argument('--output',required=True)
    create.add_argument('--part-bytes',type=int,default=MAX_PART)
    for name in ('verify','restore'):
        command = sub.add_parser(name); command.add_argument('--package',required=True)
        if name == 'restore': command.add_argument('--output',required=True)
    args = parser.parse_args()
    require(args.command is not None,'Choose package, verify, or restore')
    def local(name):
        path = (ROOT/name).resolve(); path.relative_to(ROOT); return path
    if args.command == 'package':
        result = package(local(args.data),local(args.review),local(args.output),args.part_bytes)
    else:
        directory = local(args.package); manifest = json.loads((directory/'manifest.json').read_text())
        require(manifest['status'] == 'verified','Package has not passed readback')
        result = verify(directory,manifest,local(args.output) if args.command == 'restore' else None)
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    main()
