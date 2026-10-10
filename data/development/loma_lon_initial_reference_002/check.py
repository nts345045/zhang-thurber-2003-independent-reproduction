#!/usr/bin/env python3
"""Post-completion native/hash and physical consistency review; no ray/reference rerun."""
import collections
import csv
import gzip
import hashlib
import itertools
import json
import math
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]

def require(ok,message):
    if not ok:raise ValueError(message)

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()

def table(path):
    with path.open() as f:return list(csv.DictReader(f))

def velocity(profile,z):
    for (a,va),(b,vb) in zip(profile,profile[1:]):
        if a<=z<=b:return va+(vb-va)*(z-a)/(b-a)
    raise ValueError('Outside finite profile')

def straight_action(profile,source,receiver):
    delta=[b-a for a,b in zip(source,receiver)];length=math.sqrt(sum(q*q for q in delta));cuts=[0.,1.]
    if delta[2]:cuts += [(z-source[2])/delta[2] for z,v in profile if min(source[2],receiver[2])<z<max(source[2],receiver[2])]
    cuts.sort();terms=[]
    for lo,hi in zip(cuts,cuts[1:]):
        va=velocity(profile,source[2]+lo*delta[2]);vb=velocity(profile,source[2]+hi*delta[2]);dv=vb-va
        terms.append(length*(hi-lo)*(math.log1p(dv/va)/dv if dv else 1/va))
    return math.fsum(terms)

def main():
    summary=json.loads((HERE/'summary.json').read_text());ledger=json.loads((HERE/'execution.json').read_text())
    require(ledger['status']=='completed' and ledger['summary_sha256']==sha(HERE/'summary.json'),'Not terminal/matching')
    for name,digest in summary['output_sha256'].items():require(sha(HERE/name)==digest,'Artifact hash changed: '+name)
    for name,digest in summary['input_source_sha256'].items():require(sha(ROOT/name)==digest,'Original input/source changed: '+name)
    events=table(HERE/'inputs/initial_events.csv');stations=table(HERE/'inputs/stations.csv')
    profile=summary['profile_depth_velocity_km_km_s'];box=summary['original_box_km'];vmax=max(v for z,v in profile)
    count=0;counts=collections.Counter(derivative_defined=0);lower=[];upper=[];eikonal=[];closures=[];invalid=[];ties=[]
    with gzip.open(str(HERE/'references.csv.gz'),'rt',newline='') as cf, gzip.open(str(HERE/'certificates.jsonl.gz'),'rt') as jf:
        for row,line in itertools.zip_longest(csv.DictReader(cf),jf):
            require(row is not None and line is not None,'Table/certificate count mismatch')
            i,k=divmod(count,len(stations));require(i<len(events),'Extra pair');record=json.loads(line);ref=record['reference']
            require(all(int(row[name])==value and record[name]==value for name,value in [('pair_index',count),('event',i),('station',k)]),'Pair ordering')
            for prefix,native in [('source_',events[i]),('receiver_',stations[k])]:
                require(all(row[prefix+name]==value for name,value in native.items()),'Native metadata mismatch')
            require(record['source_time_included'] is False and summary['source_time_included'] is False,'Propagation time includes source correction')
            s=[float(row['source_'+a]) for a in 'xyz'];r=[float(row['receiver_'+a]) for a in 'xyz']
            for prefix,point in [('source_',s),('receiver_',r)]:
                for d,a in enumerate('xyz'):
                    require(box[d][0]<=point[d]<=box[d][1],'Endpoint outside box')
                    for side,n in [('lower',0),('upper',1)]:
                        require(int(row[prefix+'on_'+a+'_'+side+'_face'])==int(point[d]==box[d][n]),'Boundary flag mismatch')
            if 'root_tolerance' in ref:
                require(ref['root_tolerance']==1e-12 and ref['distance_tolerance_km']==1e-8,'Original reference gate changed')
            else:
                require(not ref['complete'] and not ref['reference_valid'] and not ref['candidates'] and ref.get('first_arrival') is None and ref['unresolved'], 'Missing gates without explicit arithmetic failure')
            candidates=ref['candidates'];first=ref.get('first_arrival')
            for c in candidates:
                closures.append(abs(c['distance_residual_km']))
                turn=c.get('turning_depth_km');require(turn is None or box[2][0]<=turn<=box[2][1],'Candidate outside finite depth box')
            expected_valid=ref['complete'] and bool(candidates) and all(math.isfinite(c['time_s']) and abs(c['distance_residual_km'])<=1e-8 for c in candidates)
            require(ref['reference_valid']==expected_valid,'Reference validity/closure mismatch')
            counts['pairs']+=1;counts['reference_complete']+=ref['complete'];counts['reference_valid']+=ref['reference_valid'];counts['candidate_total']+=len(candidates)
            require(int(row['reference_complete'])==int(ref['complete']) and int(row['reference_valid'])==int(ref['reference_valid']),'Saved flags mismatch')
            require(int(row['candidate_count'])==len(candidates) and int(row['near_tie_count'])==len(ref.get('near_ties',[])),'Candidate/tie count mismatch')
            if len(ref.get('near_ties',[]))>1:ties.append(count)
            if first:
                require(ref['reference_valid'] and first['time_s']==min(c['time_s'] for c in candidates),'Selected first time mismatch')
                require(float(row['time_s'])==first['time_s'] and row['branch']==first['kind'],'Table first time/branch mismatch')
                g=first.get('source_derivative_s_per_km');counts['derivative_defined']+=g is not None
                if g is not None:
                    require(len(g)==3 and all(math.isfinite(x) for x in g),'Invalid source gradient')
                    require(all(float(row['source_d'+a+'_s_per_km'])==g[d] for d,a in enumerate('xyz')),'Derivative axes/values mismatch')
                    eikonal.append(math.sqrt(sum(x*x for x in g))-1/velocity(profile,s[2]))
                counts['branch_'+first['kind']]+=1
                distance=math.sqrt(sum((a-b)**2 for a,b in zip(s,r)));lower.append(first['time_s']-distance/vmax)
                upper.append(first['time_s']-straight_action(profile,s,r))
            else:
                invalid.append(count);require(row['time_s']=='' and all(row['source_d'+a+'_s_per_km']=='' for a in 'xyz'),'Invalid reference exposes numerical value')
            count+=1
    require(count==len(events)*len(stations)==summary['verified_pairs'],'Full support incomplete')
    require(dict(counts)==summary['counts'] and invalid==summary['invalid_reference_pair_indices'] and ties==summary['near_tie_pair_indices'],'Summary count/status mismatch')
    usable=counts['reference_complete']==counts['reference_valid']==counts['derivative_defined']==count and not ties
    require(summary['reference_comparison_ready']==usable,'Summary usability mismatch')
    result=dict(status='passed',scope='Saved-table/native/hash and independent straight-action physical checks; no reference enumeration or ray/inversion rerun',
        verified_pairs=count,counts=dict(counts),invalid_reference_count=len(invalid),near_tie_count=len(ties),reference_comparison_ready=usable,
        native_metadata_fields_all_match=True,ordered_indices_complete=True,original_xyz_source_derivatives_match=True,
        source_time_preserved_as_metadata_only=True,exact_boundary_flags_match=True,
        maximum_candidate_distance_closure_km=max(closures) if closures else None,
        physical_bounds=dict(minimum_time_minus_euclidean_over_global_vmax_s=min(lower) if lower else None,
            maximum_time_minus_independent_straight_action_s=max(upper) if upper else None,
            maximum_absolute_endpoint_eikonal_norm_residual_s_per_km=max(map(abs,eikonal)) if eikonal else None),
        interpretation='Physical-bound residuals are reported without imposing an additional scientific threshold; roundoff-sized signed differences can occur.',
        limitations=['The consistency bounds do not independently prove branch completeness or certify interval time ranking.',
            'Boundary/tied derivatives are branch derivatives, not an assertion of a unique unconstrained centered derivative.',
            'No numerical forward-operator or inversion acceptance follows from this reference-table review.'],
        summary_sha256=sha(HERE/'summary.json'),execution_sha256=sha(HERE/'execution.json'),review_source_sha256=sha(Path(__file__)))
    for name,digest in summary['output_sha256'].items():require(sha(HERE/name)==digest,'Artifact changed during review: '+name)
    (HERE/'review.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':main()
