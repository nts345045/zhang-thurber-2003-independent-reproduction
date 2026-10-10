#!/usr/bin/env python3
"""Check a fresh archive restore and published dependency mappings; no solver."""
import sys
sys.dont_write_bytecode = True
import importlib.util
import json
import tarfile
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
spec = importlib.util.spec_from_file_location('failed_run_package', str(HERE/'package.py'))
package = importlib.util.module_from_spec(spec)
spec.loader.exec_module(package)


def main():
    work = ROOT/'tmp/hayward_guarded_failure_restore_check_001'
    work.mkdir()
    (work/'existing').mkdir()
    (work/'linked').symlink_to(work/'existing', target_is_directory=True)
    refusals = {}
    for label, path in (
            ('existing_destination', work/'existing'),
            ('symlinked_ancestor', work/'linked'/'new'),
            ('parent_traversal', work/'..'/'escape'),
            ('outside_project', ROOT.parent/'failed_run_restore_outside_PROJECT')):
        try:
            package.verify(path)
        except ValueError as error:
            refusals[label] = str(error)
        else:
            raise ValueError('Expected restore refusal: '+label)
    result = package.verify(work/'restored')
    restored = work/'restored'
    manifest = json.loads((HERE/'manifest.json').read_text())
    before = json.loads((HERE/'initial_attempt/manifest.json').read_text())
    before['packager_sha256'] = manifest['packager_sha256']
    package.require(before == manifest, 'Unexpected manifest change')
    original = {name: value for name, value in manifest['members'].items()
                if name.startswith('run/')}
    package.require(len(original) == manifest['original_run_file_count'] == 57, 'Original count')
    package.require(set(package.inventory(package.RUN)) == {name[4:] for name in original}, 'Original inventory')
    for name, expected in original.items():
        package.require(package.info(package.RUN/name[4:]) ==
                        {key: expected[key] for key in ('bytes', 'sha256')}, 'Original changed')
    result['original_run_files_rehashed_unchanged'] = len(original)
    result['finished_utc'] = datetime.utcnow().isoformat()+'Z'
    package.write_json(HERE/'archive_verification.json', result)

    # The classification's original paths are resolved by actual restored
    # member hashes, including files nested inside the frozen source tar.
    locations = {v['original_repository_path']:
                 {'member': k, 'sha256': package.info(restored/k)['sha256']}
                 for k, v in manifest['members'].items()}
    run = json.loads((restored/'run/dd_inversion_run_manifest.json').read_text())
    with tarfile.open(str(restored/'run/guarded_source.tar.gz'), 'r:gz') as archive:
        for member in archive:
            package.require(member.isfile() and member.name in run['source_sha256'], 'Frozen source inventory')
            digest = package.digest(archive.extractfile(member))['sha256']
            package.require(digest == run['source_sha256'][member.name], 'Frozen source bytes')
            locations['tmp/hayward_guarded_runs/001/source/'+member.name] = {
                'member': 'run/guarded_source.tar.gz', 'nested_member': member.name,
                'sha256': digest}
    classification = json.loads((HERE/'classification/summary.json').read_text())
    mapped = {}
    for name, digest in classification['input_sha256'].items():
        package.require(name in locations and locations[name]['sha256'] == digest, 'Classification dependency: '+name)
        mapped[name] = locations[name]
    inherited = {}
    for name, entry in manifest['inherited_evidence_resolution'].items():
        path = restored/entry['archive_member'] if 'archive_member' in entry else ROOT/entry['repository_file']
        package.require(package.info(path)['sha256'] == entry['sha256'], 'Inherited pin: '+name)
        inherited[name] = entry
    for name, digest in classification['output_sha256'].items():
        package.require(package.info(HERE/'classification'/name)['sha256'] == digest, 'Classification output')
    package.require(package.info(HERE/'classification/check.py')['sha256'] == classification['source_sha256'], 'Classification source')
    package.require(all(p.stat().st_size < 100000000 for p in HERE.rglob('*') if p.is_file()), 'Published file exceeds100MB')
    pins = {name: package.info(HERE/name)['sha256'] for name in
            ('package.py', 'restore_check.py', 'README.md', 'manifest.json',
             'archive_verification.json', 'initial_attempt/package.py',
             'initial_attempt/manifest.json', 'initial_attempt/archive_verification.json',
             'classification/check.py', 'classification/summary.json',
             'classification/identified_failures.csv')}
    package.write_json(HERE/'restore_check.json', {
        'status': 'passed', 'created_utc': datetime.utcnow().isoformat()+'Z',
        'command': ['python3', str((HERE/'restore_check.py').relative_to(ROOT))],
        'python_version': sys.version, 'input_sha256': pins,
        'restored_directory': str(restored.relative_to(ROOT)),
        'archive_member_count': result['verified_members'],
        'archive_member_bytes': result['verified_member_bytes'],
        'restore_refusals': refusals, 'original_files_unchanged': len(original),
        'classification_input_count': len(mapped), 'classification_input_resolution': mapped,
        'inherited_evidence_count': len(inherited), 'inherited_evidence_resolution': inherited,
        'source_correction': 'Reject parent traversal explicitly; the initial attempt is preserved. Only the packager source hash changed in the manifest; archive bytes and members are identical.',
        'scope': 'Fresh byte-exact extraction and dependency closure; no classification rerun, compiler, archived binary execution, ray or inverse call.'})
    print(json.dumps({'status': 'passed', 'restored_members': result['verified_members'],
                      'classification_inputs': len(mapped), 'inherited_pins': len(inherited),
                      'restore_refusals': len(refusals)}))


if __name__ == '__main__':
    main()
