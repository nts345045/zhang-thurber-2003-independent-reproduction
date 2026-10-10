#!/usr/bin/env python3
"""Compare saved complete LON reference attempts; never rerun reference arithmetic."""
import argparse
import collections
import csv
from fractions import Fraction as Q
import gzip
import hashlib
import itertools
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def require(ok,message):
    if not ok:raise ValueError(message)


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''):h.update(block)
    return h.hexdigest()


def records(path):
    with gzip.open(str(path),'rt') as f:
        for line in f:yield json.loads(line)


def table(path):
    with path.open() as f:return list(csv.DictReader(f))


def checked(path):
    summary=json.loads((path/'summary.json').read_text());execution=json.loads((path/'execution.json').read_text())
    require(execution['status']=='completed' and execution['summary_sha256']==sha(path/'summary.json'),'Attempt is not terminal/hash-bound')
    for name,digest in summary['output_sha256'].items():require(sha(path/name)==digest,'Changed artifact: '+name)
    for name,digest in summary['input_source_sha256'].items():require(sha(ROOT/name)==digest,'Changed original source/input: '+name)
    return summary


def velocity(profile,z):
    for (a,va),(b,vb) in zip(profile,profile[1:]):
        if a<=z<=b:return va+(vb-va)*(z-a)/(b-a)
    raise ValueError('Outside finite profile')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--old',default='data/development/loma_lon_initial_reference_001')
    parser.add_argument('--new',default='data/development/loma_lon_initial_reference_002')
    args=parser.parse_args();old=(ROOT/args.old).resolve();new=(ROOT/args.new).resolve()
    for p in (old,new):p.relative_to(ROOT)
    a=checked(old);b=checked(new)
    names=['initial_events.csv','stations.csv','initial_grid.csv','run.cfg','ray_samples.csv',
        'preparation_manifest.json','analytic_truth_manifest.json','simulation_execution.json',
        'simulation_run_manifest.json','independent_simulation_review.json']
    require(all(sha(old/'inputs'/name)==sha(new/'inputs'/name) for name in names),'Native inputs changed between attempts')
    require(a['profile_depth_velocity_km_km_s']==b['profile_depth_velocity_km_km_s'] and a['original_box_km']==b['original_box_km'],'Profile or box changed')
    require(a['expected_pairs']==b['expected_pairs'],'Support changed')
    events=table(new/'inputs/initial_events.csv');stations=table(new/'inputs/stations.csv')
    profile=[tuple(Q(float(v)) for v in row) for row in b['profile_depth_velocity_km_km_s']]
    counts=collections.Counter();changes=[];largest_time=None;largest_gradient=None;closures=[0.,0.]
    target=new/'attempt_comparison.csv.gz'
    with target.open('xb') as raw,gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as zipped:
        import io
        with io.TextIOWrapper(zipped,encoding='utf-8',newline='') as stream:
            writer=None
            for n,(left,right) in enumerate(itertools.zip_longest(records(old/'certificates.jsonl.gz'),records(new/'certificates.jsonl.gz'))):
                require(left is not None and right is not None,'Unequal certificate support')
                i,k=divmod(n,len(stations))
                for record in (left,right):require((record['pair_index'],record['event'],record['station'])==(n,i,k),'Reordered native support')
                x=left['reference'];y=right['reference']
                for name in ('root_tolerance','distance_tolerance_km','max_isolation_boxes_per_layer','near_tie_time_tolerance_s','isolation_boxes','unresolved'):
                    require(x[name]==y[name],'Root gates/isolation changed at pair '+str(n))
                require(len(x['candidates'])==len(y['candidates']),'Candidate count changed at pair '+str(n))
                row=dict(pair_index=n,event=i,station=k,old_reference_valid=int(x['reference_valid']),new_reference_valid=int(y['reference_valid']),
                    old_reference_complete=int(x['complete']),new_reference_complete=int(y['complete']),candidate_count=len(y['candidates']))
                row.update({'source_'+key:value for key,value in events[i].items()})
                row.update({'receiver_'+key:value for key,value in stations[k].items()})
                dt=[];dg=[];changed=0
                for index,(c,d) in enumerate(zip(x['candidates'],y['candidates'])):
                    for key in ('kind','layer','root_interval','certificate'):
                        require(c.get(key)==d.get(key),'Candidate identity or isolated root changed at pair '+str(n))
                    if c['kind']!='turning':require(c==d,'Nonturning candidate changed at pair '+str(n))
                    else:
                        lo,hi=map(Q,d['turning_u_enclosure_rational']);u=Q(d['u_rational']);w=Q(d['turning_u_squared_rational'])
                        bits=d['turning_u_enclosure_relative_bits'];turn=Q(d['turning_depth_rational'])
                        require(bits==128 and lo<=u<=hi and lo*lo<=w<=hi*hi and (hi-lo)**2<=w*Q(2)**(2*(1-bits)),'Invalid exact square-root enclosure')
                        require(u==(lo+hi)/2,'Candidate does not retain the rational midpoint')
                        (za,va),(zb,vb)=profile[d['layer']:d['layer']+2]
                        u0=max(va,velocity(profile,Q(float(events[i]['z']))),velocity(profile,Q(float(stations[k]['z']))))
                        middle=sum(d['root_interval'])/2
                        require(w==u0*u0+Q(middle)**2,'Stored squared speed differs from original isolated root midpoint')
                        require(turn==za+(u-va)*(zb-za)/(vb-va) and float(turn)==d['turning_depth_km'],'Stored rational turn inconsistent')
                        counts['turning_enclosures_verified']+=1
                    delta=d['time_s']-c['time_s'];dt.append(delta);changed+=delta!=0
                    ga=c.get('source_derivative_s_per_km');gb=d.get('source_derivative_s_per_km')
                    norm=math.sqrt(math.fsum((p-q)**2 for p,q in zip(ga,gb))) if ga is not None and gb is not None else 0.
                    require((ga is None)==(gb is None),'Derivative definedness changed')
                    dg.append(norm);closures[0]=max(closures[0],abs(c['distance_residual_km']));closures[1]=max(closures[1],abs(d['distance_residual_km']))
                    context=dict(pair_index=n,candidate_index=index,event=i,station=k,native_metadata=row.copy(),old_candidate=c,new_candidate=d)
                    if largest_time is None or abs(delta)>abs(largest_time['time_change_s']):largest_time=dict(time_change_s=delta,**context)
                    if largest_gradient is None or norm>largest_gradient['source_gradient_change_norm_s_per_km']:largest_gradient=dict(source_gradient_change_norm_s_per_km=norm,**context)
                    counts['candidates']+=1
                first=[ref.get('first_arrival') for ref in (x,y)]
                for label,f in zip(('old','new'),first):
                    row[label+'_selected_branch']=f['kind'] if f else ''
                    row[label+'_time_s']=f['time_s'] if f else ''
                selected_change=bool(first[0] and first[1] and (first[0]['kind'],first[0].get('layer'),first[0].get('root_interval'))!=(first[1]['kind'],first[1].get('layer'),first[1].get('root_interval')))
                row.update(selected_branch_changed=int(selected_change),candidate_times_changed=changed,
                    maximum_absolute_candidate_time_change_s=max(map(abs,dt)) if dt else 0.,maximum_candidate_source_gradient_change_norm_s_per_km=max(dg) if dg else 0.,
                    old_near_tie_count=len(x.get('near_ties',[])),new_near_tie_count=len(y.get('near_ties',[])))
                if x['reference_valid']!=y['reference_valid'] or x['complete']!=y['complete'] or selected_change or x.get('near_ties')!=y.get('near_ties'):
                    changes.append(row.copy())
                counts['pairs']+=1;counts['candidate_times_changed']+=changed;counts['selected_branch_changes']+=selected_change
                counts['old_valid']+=x['reference_valid'];counts['new_valid']+=y['reference_valid']
                if writer is None:writer=csv.DictWriter(stream,fieldnames=list(row),lineterminator='\n');writer.writeheader()
                writer.writerow(row)
    require(counts['pairs']==a['expected_pairs']==len(events)*len(stations),'Incomplete support')
    checked(old);checked(new)
    result=dict(status='passed',scope='Every saved candidate/root/native pair compared; no reference enumeration or ray rerun',counts=dict(counts),
        unchanged_native_inputs=names,old_new_maximum_candidate_closure_km=closures,identified_status_or_selected_branch_changes=changes,
        largest_absolute_candidate_time_change=largest_time,largest_candidate_source_gradient_change=largest_gradient,
        original_failed_attempt_preserved=True,old_reference_comparison_ready=a['reference_comparison_ready'],new_reference_comparison_ready=b['reference_comparison_ready'],
        hashes={str(p.relative_to(ROOT)):sha(p) for p in [old/'summary.json',old/'execution.json',new/'summary.json',new/'execution.json',target,Path(__file__).resolve()]},
        limitations=['Changes in ordinary floating-point candidate times are reported, not interval-certified rankings.',
            'Original attempt001 validity remains unchanged; the new computation has separate provenance.',
            'This validates saved reference evidence, not a numerical forward operator or inversion.'])
    with (new/'attempt_comparison.json').open('x') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps(dict(status='passed',counts=dict(counts),new_reference_comparison_ready=b['reference_comparison_ready']),indent=2))

if __name__=='__main__':main()
