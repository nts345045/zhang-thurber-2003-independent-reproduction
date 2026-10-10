#!/usr/bin/env python3
"""Check saved native coordinates and interval acceptance; do not rerun action."""
import csv
from fractions import Fraction as Q
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def read(p):
    with p.open() as f:return list(csv.DictReader(f))


def interval(value):return tuple(Q(value[k]) for k in ('lower_rational','upper_rational'))


def main():
    summary=json.loads((HERE/'summary.json').read_text());receipt=json.loads((HERE/'execution_receipt.json').read_text())
    assert receipt['return_code']==0 and receipt['summary_sha256']==sha(HERE/'summary.json') and receipt['run_log_sha256']==sha(HERE/'run.log')
    for name,digest in summary['artifact_sha256'].items():assert sha(HERE/name)==digest,name
    for name,digest in summary['input_source_sha256'].items():assert sha(ROOT/name)==sha(HERE/'source'/name)==digest,name
    native=summary['native_case'];ids=['event','station','source_event_resource_id','source_origin_resource_id',
        'receiver_channel_seed_id','receiver_channel_fdsn_source_id','receiver_metadata_epoch_start','receiver_metadata_epoch_end']
    dirs=read(HERE/'directions.csv');names=[r['direction'] for r in summary['results']]
    assert len(names)==len(set(names))==2 and len(dirs)==5410
    original=read(HERE/'source/data/development/native_interface_support/001/support_vector.csv')
    assert len(original)==2705
    points=[tuple(Q(float(r[k])) for k in 'xyz') for r in original]
    grid=read(HERE/'source/data/development/native_interface_support/001/source/data/development/interface_directional/001/inputs/truth_grid.csv')
    bounds=[(min(Q(float(r[k])) for r in grid),max(Q(float(r[k])) for r in grid)) for k in 'xyz']
    trials=[json.loads(line) for line in (HERE/'attempts.jsonl').read_text().splitlines()]
    assert len(trials)==40
    old=interval(summary['original_action']);c=Q(summary['armijo_coefficient_rational']);verified=[]
    for result in summary['results']:
        name=result['direction'];direction=[r for r in dirs if r['direction']==name]
        assert len(direction)==2705
        d=[];normalizer=interval(result['normalization'])[1]
        for n,(r,initial) in enumerate(zip(direction,original)):
            assert int(r['node'])==n and all(r[k]==native[k] for k in ids)
            assert all(Q(float(r[k]))==points[n][axis] for axis,k in enumerate('xyz'))
            expected=[]
            for axis in 'xyz':
                value=Q(0) if int(initial['endpoint_fixed']) else -(Q(initial['g'+axis+'_lower_rational'])+Q(initial['g'+axis+'_upper_rational']))/(2*normalizer)
                if name=='tangent_projection' and axis=='x' and int(initial['incident_convex_face_x']):value=Q(0)
                expected.append(value)
            values=tuple(Q(r['d'+axis+'_rational']) for axis in 'xyz');assert values==tuple(expected);d.append(values)
        selected=[r for r in trials if r['direction']==name];assert len(selected)==20
        derivative=interval(result['actual_directional_derivative']);assert derivative[1]<0
        dot=interval(result['support_dot']);correction=interval(result['cusp_correction'])
        assert derivative==(dot[0]+correction[0],dot[1]+correction[1])
        for n,trial in enumerate(selected):
            assert trial['backtrack']==n and Q(trial['step_rational'])==Q(1,1<<n)
            assert all(trial[k]==native[k] for k in ids)
            value=interval(trial['action']);rhs=old[0]+c*Q(trial['step_rational'])*derivative[0]
            assert rhs==Q(trial['armijo_rhs_lower_rational'])
            assert trial['accepted']==(value[1]<=rhs)==(n==19)
            assert interval(trial['action_change'])==(value[0]-old[1],value[1]-old[0])
        assert result['accepted'] and result['backtrack']==19 and interval(result['new_action'])==interval(selected[-1]['action'])
        rows=read(HERE/result['new_polygon_file']);assert len(rows)==2705
        step=Q(result['step_rational']);new_points=[];squared_mid=Q(0);squared_error=Q(0)
        for n,row in enumerate(rows):
            assert int(row['node'])==n and all(row[k]==native[k] for k in ids)
            assert row['original_local_flag']==summary['original_local_flag']==native['original_converged']=='0'
            q=tuple(Q(row[k+'_rational']) for k in 'xyz');new_points.append(q)
            assert q==tuple(p+step*v for p,v in zip(points[n],d[n]))
            assert all(bounds[k][0]<=x<=bounds[k][1] and float(row['xyz'[k]])==float(x) for k,x in enumerate(q))
            for k in 'xyz':
                lo,hi=row['g'+k+'_lower_rational'],row['g'+k+'_upper_rational']
                if n in (0,len(rows)-1):assert lo==hi==''
                else:
                    lo,hi=Q(lo),Q(hi);assert lo<=hi
                    squared_mid+=((lo+hi)/2)**2;squared_error+=((hi-lo)/2)**2
        assert new_points[0]==points[0] and new_points[-1]==points[-1]
        assert all(a!=b for a,b in zip(new_points,new_points[1:]))
        bound=result['new_support_bound'];norm=interval(bound['norm_midpoint']);error=interval(bound['norm_error'])
        assert norm[0]**2<=squared_mid<=norm[1]**2 and error[0]**2<=squared_error<=error[1]**2
        assert Q(bound['support_norm_upper_rational'])==norm[1]+error[1]
        assert len(bound['aligned_edges'])==sum(a[0]==b[0] for a,b in zip(new_points,new_points[1:]))
        verified.append(dict(direction=name,verified_native_rows=len(rows),verified_trials=len(selected),exact_step_reconstruction=True,
            exact_endpoints=True,domain_and_nonzero_segments=True,blank_endpoint_derivatives=True,interval_norm_bounds=True))
    output=dict(status='passed_saved_evidence_readback',scope='Native/hash/rational-coordinate/interval-inequality checks only; no action or optimizer rerun.',
        summary_sha256=sha(HERE/'summary.json'),execution_receipt_sha256=sha(HERE/'execution_receipt.json'),readback_source_sha256=sha(Path(__file__)),
        pinned_hashes=len(summary['artifact_sha256'])+len(summary['input_source_sha256']),verified=verified,
        original_flag_preserved=True,new_stationarity_or_first_arrival_claim=False)
    with (HERE/'readback.json').open('x') as f:json.dump(output,f,indent=2);f.write('\n')
    print(json.dumps(output))


if __name__=='__main__':main()
