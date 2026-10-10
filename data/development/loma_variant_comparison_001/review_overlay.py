#!/usr/bin/env python3
"""Independent check of compact publication and completed restore evidence."""
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
BASE = ROOT / 'data/published/loma_lom_analytic_001'
PACKAGE = ROOT / 'data/published/loma_lon_analytic_001'
RESTORED = ROOT / 'tmp/loma_lon_overlay_restore_001'


def sha(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


def read(path):
    return json.loads(path.read_text())


def inventory(directory):
    return {str(p.relative_to(directory)): p for p in directory.rglob('*') if p.is_file()}


def check_files(directory, expected):
    files = inventory(directory)
    assert set(files) == set(expected)
    for name, value in expected.items():
        assert files[name].stat().st_size == value['bytes']
        assert sha(files[name]) == value['sha256']


def main():
    manifest = read(PACKAGE / 'manifest.json')
    base = read(BASE / 'manifest.json')
    check_files(BASE, manifest['base_inventory'])
    assert sha(BASE / 'manifest.json') == manifest['base_manifest_sha256']
    expected = dict(manifest['supporting_files'])
    expected.update({'files/' + k: v for k, v in manifest['stored_files'].items()})
    actual = inventory(PACKAGE)
    assert set(actual) == set(expected) | {'manifest.json', 'execution.json'}
    for name, value in expected.items():
        assert actual[name].stat().st_size == value['bytes'] and sha(actual[name]) == value['sha256']
    assert read(PACKAGE / 'execution.json') == dict(status='completed', manifest_sha256=sha(PACKAGE / 'manifest.json'))
    members, reused, stored = manifest['members'], manifest['reused_members'], manifest['stored_files']
    assert len(reused) == len(set(reused)) and not set(reused) & set(stored)
    assert set(members) == set(reused) | set(stored)
    assert all(members[n] == base['members'][n] for n in reused)
    assert all(members[n] == stored[n] for n in stored)
    assert read(PACKAGE / 'files/independent_simulation_review.json')['status'] == 'passed'
    assert sha(PACKAGE / 'files/independent_simulation_review.json') == manifest['independent_review_sha256']
    assert read(ROOT / 'data/development/loma_variant_packaging_checks_001/summary.json')['status'] == 'passed'
    for action in ('create', 'restore'):
        execution = read(HERE / ('overlay_' + action + '_execution.json'))
        assert execution['status'] == 'completed' and execution['returncode'] == 0
        for name, digest in execution['output_sha256'].items():
            assert sha(HERE / name) == digest
        for name, digest in execution['source_sha256'].items():
            assert sha(ROOT / name) == digest
    restore = read(HERE / 'overlay_restore_stdout.json')
    assert restore == dict(status='passed', restored_members=len(members),
                          restored_bytes=sum(v['bytes'] for v in members.values()),
                          full_inventory_and_hashes_match=True)
    restored = inventory(RESTORED)
    assert set(restored) == set(members)
    for name, value in members.items():
        assert restored[name].stat().st_size == value['bytes']
        if name != 'observations.csv':
            assert sha(restored[name]) == value['sha256']
    native_counts = {}
    for table in base['identity_mapping']['native_tables']:
        name = table['archived_member']
        assert name in reused and members[name]['sha256'] == table['sha256']
        with restored[name].open(newline='') as stream:
            rows = list(csv.DictReader(stream))
        assert len(rows) == table['rows']
        assert all(set(table['identifier_columns']) <= set(row) for row in rows)
        for row in rows:
            if 'channel_seed_id' in row:
                assert row['channel_seed_id'] == '.'.join(row[k] for k in ('network_code', 'station_code', 'location_code', 'channel_code'))
                assert row['channel_fdsn_source_id'] and row['metadata_epoch_start']
            else:
                assert row['event_resource_id'] and row['origin_resource_id']
        native_counts[name] = len(rows)
    evidence = [PACKAGE / 'manifest.json', HERE / 'comparison.json', HERE / 'overlay_restore_execution.json',
                HERE / 'overlay_restore_stdout.json', Path(__file__).resolve()]
    result = dict(status='passed', reviewer='root', created_utc=datetime.now(timezone.utc).isoformat(),
                  scope='Independent publication inventory, exact member mapping, provenance and completed-restore evidence review',
                  base_files_rehashed=len(inventory(BASE)), package_files=len(actual),
                  reused_members=len(reused), stored_members=len(stored), restored_members=len(members),
                  restored_nonobservation_members_rehashed=len(members)-1, native_table_rows=native_counts,
                  evidence_sha256={str(p.relative_to(ROOT)): sha(p) for p in evidence},
                  limits=['The 6.8 GB observation payload was fully hashed by the completed fresh-restore command; this review verifies its pinned terminal evidence and file size without repeating that full read.',
                          'Publication validates lossless storage and identity preservation, not inverse accuracy.'])
    (HERE / 'overlay_review.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
