#!/usr/bin/env python3
"""Restore historical sentinel bytes only into a newly created scratch tree."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys

sys.dont_write_bytecode = True
PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parents[2]
RUNS = ['loma_failed_search_3426_001', 'loma_outer_accumulation_native_001',
        'loma_curvature_capture_native_001', 'loma_seed_loaded_b_native_001',
        'loma_positive_curvature_native_001', 'loma_usable_curvature_native_001']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def need(ok, message):
    if not ok:
        raise ValueError(message)


def local(root, name):
    rel = PurePosixPath(name)
    need(not rel.is_absolute() and '..' not in rel.parts and str(rel)==name,
         'Unsafe/noncanonical archive member: '+name)
    path = root.joinpath(*rel.parts)
    need(not any(p.is_symlink() for p in [path]+list(path.parents) if p!=root.parent),
         'Symlinked evidence path: '+name)
    return path


def validate(root, archive, require_locks=False):
    expected = ['data/development/'+run+'/execution.lock' for run in RUNS]
    need([r['path'] for r in archive['records']]==expected, 'Unexpected/duplicate record roster')
    for name, digest in archive['terminal_evidence_sha256'].items():
        need(sha(local(root,name))==digest, 'Changed terminal evidence: '+name)
    lock_pins = {}
    for record in archive['records']:
        name = record['path']
        raw = record['archived_text'].encode('ascii')
        need(re.fullmatch(b'[1-9][0-9]*\n',raw) is not None, 'Unexpected historical sentinel format')
        need(len(raw)==record['size_bytes'] and hashlib.sha256(raw).hexdigest()==record['sha256'],
             'Archived bytes/hash differ: '+name)
        lock_pins[name] = record['sha256']
        directory = local(root,str(PurePosixPath(name).parent))
        summary = json.loads((directory/'summary.json').read_text())
        execution = json.loads((directory/'execution.json').read_text())
        need(execution['status']=='completed' and execution['return_code']==0 and
             execution['summary_sha256']==sha(directory/'summary.json'), 'Nonterminal/unbound ledger')
        need(summary['status'].startswith('completed') and not summary.get('partial_hashes_withheld_live_descendants',False),
             'Incomplete terminal summary')
        need(raw==(str(execution['pid'])+'\n').encode('ascii') and
             summary.get('driver_pid',execution['pid'])==execution['pid'], 'Historical PID join differs')
        need(summary['output_sha256']['execution.lock']==record['sha256'], 'Summary sentinel pin differs')
        need(summary['prepared_sha256']==sha(directory/'prepared.json'), 'Prepared/summary join differs')
        need(summary['finished_utc'] and execution['finished_utc'], 'Missing terminal times')
        if (directory/'controller_completion.json').exists():
            controller = json.loads((directory/'controller_completion.json').read_text())
            need(controller['status']=='completed' and controller['driver_pid']==execution['pid'],
                 'Controller terminal/driver join differs')
            need(controller.get('summary_sha256',controller.get('native_summary_sha256'))==sha(directory/'summary.json') and
                 controller.get('execution_sha256',controller.get('native_execution_sha256'))==sha(directory/'execution.json'),
                 'Controller ledger hash differs')
            if directory.name=='loma_outer_accumulation_native_001':
                need(controller['detached_driver_return_code'] is None and
                     'did not reap' in controller['driver_terminal_evidence'], 'Original unreaped-driver caveat changed')
            else:
                need(controller['driver_return_code']==0 and controller['child_reaped'] is True,
                     'Reaped-controller status differs')
        with (directory/'identified_ray.csv').open(newline='') as handle:
            native = list(csv.DictReader(handle))
        need(len(native)==1 and all(native[0][k]==v for k,v in record['native_identifiers'].items()),
             'Native identity link differs')
        if require_locks:
            need(local(root,name).read_bytes()==raw, 'Restored historical bytes differ: '+name)
    for dependency in archive['lock_lookups']:
        document = json.loads(local(root,dependency['document']).read_text())
        recorded = document[dependency['map']][dependency['key']]
        need(recorded==dependency['sha256']==lock_pins[dependency['lock_path']], 'Lock dependency changed')
    return dict(records=len(lock_pins), lock_bytes=sum(r['size_bytes'] for r in archive['records']),
                lock_lookups=len(archive['lock_lookups']), terminal_evidence_files=len(archive['terminal_evidence_sha256']))


def restore(source, destination, archive, archive_sha):
    counts = validate(source,archive)
    raw_path = Path(destination).absolute()
    need('..' not in raw_path.parts, 'Scratch path must not contain ..')
    need(not any(p.is_symlink() for p in [raw_path]+list(raw_path.parents)), 'Scratch path has a symlink')
    need(raw_path.parent.is_dir(), 'Scratch parent must already exist')
    # No existing directory, checkout, lock or runtime state can be modified.
    raw_path.mkdir(exist_ok=False)
    receipt = dict(status='restoring_historical_evidence', archive_sha256=archive_sha,
                   scope='Fresh scratch only; numeric PID text is historical evidence, never process authority',
                   counts=counts, restored_sha256={})
    try:
        for record in archive['records']:
            path = local(raw_path,record['path'])
            path.parent.mkdir(parents=True,exist_ok=True)
            descriptor = os.open(str(path),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o444)
            with os.fdopen(descriptor,'wb') as handle:
                handle.write(record['archived_text'].encode('ascii'))
            need(sha(path)==record['sha256'],'Restored hash differs')
            receipt['restored_sha256'][record['path']]=sha(path)
        validate(source,archive)
        receipt['status']='restored_historical_evidence'
    except BaseException as error:
        receipt.update(status='failed_partial_restoration_retained',error=repr(error))
        raise
    finally:
        with (raw_path/'historical_lock_restoration.json').open('x') as handle:
            json.dump(receipt,handle,indent=2);handle.write('\n')
    return receipt


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--scratch',help='Nonexistent destination; creates only inert historical paths and receipt')
    group.add_argument('--verify',help='Read-only verification after populating the fresh checkout snapshot')
    args=parser.parse_args()
    archive_path=PACKAGE/'archive.json'
    archive=json.loads(archive_path.read_text())
    if args.scratch:
        result=restore(ROOT,args.scratch,archive,sha(archive_path))
    else:
        target=Path(args.verify).absolute()
        receipt=json.loads((target/'historical_lock_restoration.json').read_text())
        need(receipt['status']=='restored_historical_evidence' and receipt['archive_sha256']==sha(archive_path),
             'Not this archive\'s completed fresh restoration')
        result=dict(status='verified',**validate(target,archive,require_locks=True))
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
