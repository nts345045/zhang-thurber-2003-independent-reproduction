#!/usr/bin/env python3
"""Exercise the historical-lock overlay in a disposable metadata-only checkout."""
import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys

sys.dont_write_bytecode=True
from restore import ROOT,PACKAGE,sha,validate,restore


def main():
    archive_path=PACKAGE/'archive.json'; archive=json.loads(archive_path.read_text())
    digest=sha(archive_path)
    work=ROOT/'tmp/terminal_lock_archive_checks_001'
    work.mkdir(exist_ok=False)
    pins=dict(archive['terminal_evidence_sha256'])
    pins.update({r['path']:r['sha256'] for r in archive['records']})
    for name,h in pins.items():
        assert sha(ROOT/name)==h
    checks=[]
    target=work/'scratch'
    receipt=restore(ROOT,target,archive,digest)
    checks.append(dict(name='fresh_restore_six_exact_records',passed=len(receipt['restored_sha256'])==6))
    # Equivalent to populating the remaining checkout snapshot: copy only the
    # immutable metadata needed by the real lock consumers, without runtime state.
    for name in archive['terminal_evidence_sha256']:
        path=target/name;path.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/name,path)
    counts=validate(target,archive,require_locks=True)
    checks.append(dict(name='actual_prepared_summary_and_publication_lookups',passed=counts['lock_lookups']==29))
    checks.append(dict(name='terminal_native_and_packaging_pins',passed=counts['terminal_evidence_files']==32))
    command=[sys.executable,str(PACKAGE/'restore.py'),'--verify',str(target)]
    run=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    result=json.loads(run.stdout.decode('utf8'))
    checks.append(dict(name='public_verify_cli',passed=run.returncode==0 and result['status']=='verified'))
    checks.append(dict(name='restored_files_read_only',passed=all((target/r['path']).stat().st_mode&0o222==0 for r in archive['records'])))
    def rejected(name,source,destination,changed):
        existed=destination.exists() or destination.is_symlink()
        before={str(p.relative_to(destination)):sha(p) for p in destination.rglob('*') if p.is_file()} if destination.is_dir() else {}
        try:
            restore(source,destination,changed,digest)
        except (ValueError,FileExistsError,FileNotFoundError) as error:
            passed=(existed or not destination.exists())
            after={str(p.relative_to(destination)):sha(p) for p in destination.rglob('*') if p.is_file()} if destination.is_dir() else {}
            passed=passed and before==after
            checks.append(dict(name=name,passed=passed,rejection_type=type(error).__name__,reason=str(error).replace(str(ROOT),'<checkout>')))
        else:
            checks.append(dict(name=name,passed=False))
    rejected('existing_populated_destination',ROOT,target,archive)
    empty=work/'empty';empty.mkdir()
    rejected('existing_empty_destination',ROOT,empty,archive)
    alias=work/'alias';alias.symlink_to(target,target_is_directory=True)
    rejected('symlink_destination',ROOT,alias,archive)
    rejected('symlink_parent',ROOT,alias/'never_created',archive)
    bad=copy.deepcopy(archive);bad['records'][0]['archived_text']='1\n'
    rejected('corrupted_archived_bytes',ROOT,work/'corrupted_bytes',bad)
    bad=copy.deepcopy(archive);bad['records'][0]['path']='../execution.lock'
    rejected('unsafe_path',ROOT,work/'unsafe',bad)
    bad=copy.deepcopy(archive);bad['records'].append(copy.deepcopy(bad['records'][0]))
    rejected('duplicate_record',ROOT,work/'duplicate',bad)
    stale=work/'stale_checkout';stale.mkdir()
    for name in archive['terminal_evidence_sha256']:
        path=stale/name;path.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,path)
    ledger='data/development/loma_usable_curvature_native_001/execution.json'
    path=stale/ledger;data=json.loads(path.read_text());data['status']='running';path.write_text(json.dumps(data)+'\n')
    rejected('stale_terminal_hash',stale,work/'stale_output',archive)
    bad=copy.deepcopy(archive);bad['terminal_evidence_sha256'][ledger]=sha(path)
    rejected('hash_consistent_but_nonterminal_ledger',stale,work/'running_output',bad)
    for name,h in pins.items():
        assert sha(ROOT/name)==h
    checks.append(dict(name='all_38_original_lock_and_terminal_files_unchanged',passed=True))
    output=dict(status='passed' if all(c['passed'] for c in checks) else 'failed',checks=checks,
                archive_sha256=digest,source_sha256={p.name:sha(p) for p in [Path(__file__).resolve(),PACKAGE/'restore.py',PACKAGE/'capture.py']},
                scratch_directory=str(work.relative_to(ROOT)),source_inputs_unchanged_sha256=pins,
                actual_lock_lookup_count=counts['lock_lookups'],terminal_evidence_files=counts['terminal_evidence_files'],
                verified_restored_lock_count=counts['records'],restored_bytes=counts['lock_bytes'],
                verify_cli_command=['python3',str((PACKAGE/'restore.py').relative_to(ROOT)),'--verify',str(target.relative_to(ROOT))],
                verify_cli_result=result,
                scope='Fresh metadata-only checkout fixture for lock closure; no solver, process signaling, native data acquisition, or Git mutation.')
    with (PACKAGE/'check_results.json').open('x') as handle:
        json.dump(output,handle,indent=2);handle.write('\n')
    print(json.dumps(dict(status=output['status'],checks=len(checks),result_sha256=sha(PACKAGE/'check_results.json')),indent=2))
    if output['status']!='passed':
        raise SystemExit(1)


if __name__=='__main__':
    main()
