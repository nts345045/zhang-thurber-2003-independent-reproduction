#!/usr/bin/env python3
"""Saved-table sign certificate only; no ray/action/optimizer evaluation."""
import csv
from fractions import Fraction as Q
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    summary=json.loads((HERE/'summary.json').read_text())
    for name,digest in summary['artifact_sha256'].items():assert sha(HERE/name)==digest,name
    for name,digest in summary['input_source_sha256'].items():assert sha(ROOT/name)==sha(HERE/'source'/name)==digest,name
    old=HERE/'source/data/development/native_interface_support/001'
    step=HERE/'source/data/development/native_interface_step/001'
    original=json.loads((old/'summary.json').read_text());steps=json.loads((step/'summary.json').read_text())
    native=summary['native_case'];assert native==original['native_case']==steps['native_case']
    ids=['event','station','source_event_resource_id','source_origin_resource_id','receiver_channel_seed_id',
        'receiver_channel_fdsn_source_id','receiver_metadata_epoch_start','receiver_metadata_epoch_end']
    cases=[('original',old/'support_vector.csv',original['aligned_segments'])]
    for result in steps['results']:cases.append((result['direction'],step/result['new_polygon_file'],result['new_support_bound']['aligned_edges']))
    output=[]
    for name,path,edges in cases:
        with path.open() as f:rows=list(csv.DictReader(f))
        nodes=set()
        for edge in edges:
            assert Q(edge['x'])==0 and Q(edge['minus'])==0 and Q(edge['plus'])==Q(1,18)
            nodes.update((edge['edge'],edge['edge']+1))
        selected=[];nonzero=[]
        for n in sorted(nodes):
            row=rows[n];assert int(row['node'])==n and all(row[k]==native[k] for k in ids)
            if int(row['endpoint_fixed']):continue
            lo,hi=Q(row['gx_lower_rational']),Q(row['gx_upper_rational']);assert lo<=hi
            selected.append((lo,hi))
            if lo!=0 or hi!=0:nonzero.append(dict(node=n,lower_rational=str(lo),upper_rational=str(hi)))
        certified=all(lo>=0 for lo,hi in selected)
        output.append(dict({k:native[k] for k in ids},polygon=name,polygon_sha256=sha(path),affected_internal_knots=len(selected),
            exact_zero_components=sum(lo==hi==0 for lo,hi in selected),strictly_positive_lower_bounds=sum(lo>0 for lo,hi in selected),
            strictly_negative_upper_bounds=sum(hi<0 for lo,hi in selected),nonzero_components=nonzero,
            alpha_zero_minimum_norm_certified=certified,
            certificate_status='certified_by_nonnegative_components' if certified else 'sign_criterion_inconclusive',
            original_local_flag=native['original_converged'],stationarity_labeled=False))
    record=dict(status='completed_saved_sign_certificate',source_sha256=sha(Path(__file__)),
        corollary_sha256=sha(HERE.parent/'nonnegative_corollary.md'),summary_sha256=sha(HERE/'summary.json'),
        verified_pins=len(summary['artifact_sha256'])+len(summary['input_source_sha256']),results=output,
        scope='Exact saved interval signs and full convex moment sets; no numerical optimizer, action rerun or flag change.')
    with (HERE/'normal_sign_certificate.json').open('x') as f:json.dump(record,f,indent=2);f.write('\n')
    print(json.dumps([(r['polygon'],r['certificate_status']) for r in output]))


if __name__=='__main__':main()
