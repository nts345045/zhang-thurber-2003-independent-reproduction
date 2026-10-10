#!/usr/bin/env python3
"""Capture completed historical sentinel bytes as inert JSON; never modify them."""
import csv
import hashlib
import json
from pathlib import Path
import sys

sys.dont_write_bytecode=True
from restore import ROOT,PACKAGE,RUNS,sha,validate


def main():
    records,pins,lookups=[],{},[]
    id_fields=['observation_index','source_event_resource_id','source_origin_resource_id',
               'receiver_channel_seed_id','receiver_channel_fdsn_source_id',
               'receiver_metadata_epoch_start','receiver_metadata_epoch_end']
    for run in RUNS:
        directory=ROOT/'data/development'/run
        lock=directory/'execution.lock'
        raw=lock.read_bytes()
        with (directory/'identified_ray.csv').open(newline='') as handle:
            rows=list(csv.DictReader(handle))
        if len(rows)!=1:
            raise ValueError('Unexpected native roster')
        records.append(dict(path=str(lock.relative_to(ROOT)),archived_text=raw.decode('ascii'),
                            size_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),
                            native_identifiers={k:rows[0][k] for k in id_fields},
                            meaning='Completed historical one-use sentinel bytes; not live lock ownership'))
        for name in ['summary.json','execution.json','prepared.json','identified_ray.csv',
                     'controller_completion.json','publication_manifest.json','packaging_receipt.json']:
            path=directory/name
            if not path.exists():
                continue
            rel=str(path.relative_to(ROOT));pins[rel]=sha(path)
            if path.suffix!='.json':
                continue
            document=json.loads(path.read_text())
            for field in ['input_sha256','output_sha256','members_sha256']:
                for key,digest in document.get(field,{}).items():
                    if key.endswith('/execution.lock') or key=='execution.lock':
                        full=str((directory/key).relative_to(ROOT)) if key=='execution.lock' else key
                        lookups.append(dict(document=rel,map=field,key=key,lock_path=full,sha256=digest))
    old_receipt=ROOT/'data/development/loma_curvature_capture_review_001/packaging_receipt.json'
    pins[str(old_receipt.relative_to(ROOT))]=sha(old_receipt)
    archive=dict(format='completed-historical-sentinel-evidence-v1',records=records,
                 terminal_evidence_sha256=pins,lock_lookups=lookups,
                 authored_source_sha256={str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__).resolve(),PACKAGE/'restore.py']},
                 limitations=['Archive contains inert JSON text, not active lock files; no process is queried, signalled or resumed.',
                              'Outer accumulation original launcher did not reap its detached driver; its existing terminal-ledger caveat is unchanged.',
                              'This closes the six sentinel dependencies only, not every other source/data/runtime dependency in the scientific packages.'])
    counts=validate(ROOT,archive,require_locks=True)
    with (PACKAGE/'archive.json').open('x') as handle:
        json.dump(archive,handle,indent=2);handle.write('\n')
    print(json.dumps(dict(status='captured',archive_sha256=sha(PACKAGE/'archive.json'),**counts),indent=2))


if __name__=='__main__':
    main()
