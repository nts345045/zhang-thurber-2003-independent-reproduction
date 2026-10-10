#!/usr/bin/env python3
"""Preserve a reviewed simulation using exact base members and small replacements."""
import argparse
import json
from pathlib import Path
import shutil

import package_loma_simulation as archive

ROOT = Path(__file__).resolve().parents[1]
PHYSICAL = ('truth_events.csv', 'initial_events.csv', 'arrivals.csv', 'observations.csv',
            'simulation_truth_status.csv', 'simulation_truth_mode.txt')


def snapshot(directory):
    return {name: archive.info(path) for name, path in archive.files(directory).items()}


def disjoint(a, b):
    archive.require(a != b and a not in b.parents and b not in a.parents,
                    'Publication, base, original run and restore paths must be disjoint')


def base_package(base, expected=None):
    actual = snapshot(base)
    if expected is not None:
        archive.require(actual == expected, 'Base file inventory or bytes changed')
    manifest = json.loads((base / 'manifest.json').read_text())
    execution = json.loads((base / 'execution.json').read_text())
    verification = json.loads((base / 'verification.json').read_text())
    digest = actual['manifest.json']['sha256']
    archive.require(manifest['format'] == 'split-gzip-tar-v1' and manifest['status'] == 'verified' and
                    execution['status'] == 'completed' and execution['manifest_sha256'] == digest and
                    verification['status'] == 'passed' and verification['manifest_sha256'] == digest,
                    'Base package is not a completed verified archive')
    parts = manifest['parts']
    archive.require([p['file'] for p in parts] == ['simulation.tar.gz.part{:04d}'.format(i) for i in range(len(parts))],
                    'Base parts are not consecutive')
    for part in parts:
        archive.require(0 < part['bytes'] <= archive.MAX_PART and actual[archive.safe_name(part['file'])] ==
                        {k: part[k] for k in ('sha256', 'bytes')}, 'Base part changed')
    for name, value in manifest['readable_files'].items():
        archive.require(actual[archive.safe_name(name)] == value, 'Base readable evidence changed')
    return manifest, actual


def verify(package, base):
    actual = snapshot(package)
    manifest = json.loads((package / 'manifest.json').read_text())
    execution = json.loads((package / 'execution.json').read_text())
    archive.require(manifest['format'] == 'simulation-overlay-v1' and execution['status'] == 'completed' and
                    execution['manifest_sha256'] == actual['manifest.json']['sha256'], 'Overlay manifest or execution changed')
    members, stored, reused = manifest['members'], manifest['stored_files'], manifest['reused_members']
    for name in set(members) | set(stored) | set(reused) | set(manifest['supporting_files']):
        archive.safe_name(name)
    archive.require(len(reused) == len(set(reused)) and not (set(stored) & set(reused)) and
                    set(stored) | set(reused) == set(members), 'Overlay member mapping is incomplete or duplicated')
    expected_paths = {'manifest.json', 'execution.json'} | set(manifest['supporting_files']) | {'files/' + n for n in stored}
    archive.require(set(actual) == expected_paths, 'Overlay contains missing or extra files')
    for name, value in manifest['supporting_files'].items():
        archive.require(actual[name] == value, 'Overlay supporting evidence changed: ' + name)
    for name, value in stored.items():
        archive.require(value == members[name] and actual['files/' + name] == value,
                        'Overlay replacement changed: ' + name)
    bm, base_files = base_package(base, manifest['base_inventory'])
    archive.require(base_files['manifest.json']['sha256'] == manifest['base_manifest_sha256'], 'Stale base manifest')
    for name in reused:
        archive.require(bm['members'].get(name) == members[name], 'Reused member differs from base: ' + name)
    archive.require(all(bm['members'].get(n) == members.get(n) for n in PHYSICAL), 'Physical simulation output changed')
    archive.require(members['independent_simulation_review.json']['sha256'] == manifest['independent_review_sha256'],
                    'LON independent review identity differs')
    for table in bm['identity_mapping']['native_tables']:
        name = table['archived_member']
        archive.require(members.get(name) == bm['members'][name], 'Native table differs from its base identity mapping')
    return manifest, bm


def create(data, review, comparison_path, base, output):
    for a, b in ((data, output), (base, output), (data, base)):
        disjoint(a, b)
    archive.require(not output.exists(), 'Preserve the prior overlay; use a fresh directory')
    archive.require(review == data / 'independent_simulation_review.json', 'Preserve the native review inside the run inventory')
    comparison_info = archive.info(comparison_path)
    comparison = json.loads(comparison_path.read_text())
    archive.require(comparison['status'] == 'passed' and comparison['all_physical_simulation_outputs_byte_identical'] is True and
                    comparison['all_original_hashes_and_inventories_reverified_at_end'] is True,
                    'A completed exact-byte comparison is required')
    members = snapshot(data)
    independent, counts = archive.gate(data, review, members)
    bm, base_files = base_package(base)
    archive.require(base_files['manifest.json']['sha256'] == comparison['base_package_manifest_sha256'], 'Comparison uses another base')
    left = {n: row['lom'] for n, row in comparison['members'].items() if row['lom'] is not None}
    right = {n: row['lon'] for n, row in comparison['members'].items() if row['lon'] is not None}
    archive.require(left == bm['members'] and right == members, 'Compared source inventories changed')
    archive.require(all(bm['members'].get(n) == members.get(n) for n in PHYSICAL), 'Physical outputs cannot be replaced')
    reused = sorted(n for n, value in members.items() if bm['members'].get(n) == value)
    stored = {n: value for n, value in members.items() if n not in reused}
    archive.require(all(v['bytes'] <= archive.MAX_PART for v in stored.values()), 'A replacement exceeds 50 MiB; use a full archive')
    output.mkdir(parents=True)
    archive.json_write(output / 'execution.json', dict(status='preparing'))
    try:
        for name, expected in stored.items():
            target = output / 'files' / archive.safe_name(name)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(str(data / name), str(target))
            archive.require(archive.info(target) == expected, 'Replacement changed during copy: ' + name)
        shutil.copyfile(str(comparison_path), str(output / 'comparison.json'))
        archive.require(archive.info(output / 'comparison.json') == comparison_info, 'Comparison changed during copy')
        (output / 'README.md').write_text('''# LON simulation publication

This package retains all LON-specific files under `files/`. The remaining
members are byte-identical to the verified LOM archive. `manifest.json` records
the complete LON inventory, every resource-bearing native table, the exact base
package files, and each replacement hash. `comparison.json` records the actual
model, configuration, source and payload differences. All observations are
synthetic; provider IDs identify the authoritative simulation geometry.

Keep the complete LOM package with this package. Restore only into a fresh path:

```sh
python3 diagnostics/package_loma_variant.py verify --package LON_PACKAGE --base LOM_PACKAGE
python3 diagnostics/package_loma_variant.py restore --package LON_PACKAGE --base LOM_PACKAGE --output FRESH_DIRECTORY
```

Paths are relative to the repository. The helper rejects changed base or overlay
files, unsafe paths and existing restore directories. It verifies the base tar
stream, applies the declared replacements, and hashes every restored LON file.
A failed restore retains its partial directory for inspection. Original local
simulations remain unchanged. This publication establishes lossless storage,
not inverse accuracy or equivalence of the distinct starting velocity models.
''')
        manifest = dict(format='simulation-overlay-v1', original_data=str(data.relative_to(ROOT)),
            scope='Exact reviewed LON bytes restored from identical LOM base members and explicit LON replacements',
            members=members, stored_files=stored, reused_members=reused, counts=counts,
            base_manifest_sha256=base_files['manifest.json']['sha256'], base_inventory=base_files,
            identity_mapping=dict(basis='Native table links refer to the pinned base package; archived member paths refer to the restored LON directory',
                                  base_package_mapping=bm['identity_mapping']),
            independent_review_sha256=archive.info(review)['sha256'],
            supporting_files={n: archive.info(output / n) for n in ('README.md', 'comparison.json')},
            helper_sha256=archive.info(Path(__file__))['sha256'], archive_helper_sha256=archive.info(Path(archive.__file__))['sha256'])
        archive.json_write(output / 'manifest.json', manifest)
        (output / 'execution.json').write_text(json.dumps(dict(status='completed',
            manifest_sha256=archive.info(output / 'manifest.json')['sha256']), indent=2) + '\n')
        verify(output, base)
        archive.require(snapshot(data) == members, 'Original run changed during overlay creation')
        archive.require(archive.info(comparison_path) == comparison_info, 'Comparison changed during overlay creation')
        return dict(status='passed', members=len(members), reused_members=len(reused), stored_members=len(stored),
                    stored_bytes=sum(v['bytes'] for v in stored.values()), originals_unchanged=True)
    except BaseException as error:
        (output / 'execution.json').write_text(json.dumps(dict(status='failed', error_type=type(error).__name__, error=str(error)), indent=2) + '\n')
        raise


def restore(package, base, output):
    disjoint(package, output); disjoint(base, output)
    archive.require(not output.exists(), 'Restore target must be fresh')
    manifest, bm = verify(package, base)
    archive.verify(base, bm, restore=output)
    for name in set(bm['members']) - set(manifest['members']):
        (output / name).unlink()
    for name, expected in manifest['stored_files'].items():
        target = output / name
        if target.exists():
            archive.require(archive.info(target) == bm['members'][name], 'Unexpected pre-replacement file')
            target.unlink()
        target.parent.mkdir(parents=True, exist_ok=True)
        with (package / 'files' / name).open('rb') as source, target.open('xb') as destination:
            archive.require(archive.digest(source, destination) == expected, 'Replacement changed while restoring')
    archive.require(snapshot(output) == manifest['members'], 'Restored LON inventory or bytes differ')
    verify(package, base)
    return dict(status='passed', restored_members=len(manifest['members']),
                restored_bytes=sum(v['bytes'] for v in manifest['members'].values()), full_inventory_and_hashes_match=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command')
    create_parser = sub.add_parser('create')
    for name in ('data', 'review', 'comparison', 'base', 'output'):
        create_parser.add_argument('--' + name, required=True)
    for action in ('verify', 'restore'):
        command = sub.add_parser(action)
        command.add_argument('--package', required=True); command.add_argument('--base', required=True)
        if action == 'restore': command.add_argument('--output', required=True)
    args = parser.parse_args()
    archive.require(args.command is not None, 'Choose create, verify or restore')
    def local(name):
        path = (ROOT / name).resolve(); path.relative_to(ROOT); return path
    if args.command == 'create':
        result = create(*(local(getattr(args, n)) for n in ('data', 'review', 'comparison', 'base', 'output')))
    elif args.command == 'restore':
        result = restore(local(args.package), local(args.base), local(args.output))
    else:
        manifest, unused = verify(local(args.package), local(args.base))
        result = dict(status='passed', members=len(manifest['members']), scope='Exact pinned base and replacement bytes')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
