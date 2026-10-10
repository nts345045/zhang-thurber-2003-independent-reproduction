#!/usr/bin/env python3
"""Read saved tables only: no reference arithmetic or ray/inversion run."""
import collections
import csv
import hashlib
import itertools
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]

def require(ok, message):
    if not ok: raise ValueError(message)

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''): h.update(b)
    return h.hexdigest()

def rows(path):
    with path.open() as f: return list(csv.DictReader(f))

def main():
    summary=json.loads((HERE/'summary.json').read_text())
    maps=['input_sha256','output_sha256','original_reverified_sha256','reused_reference_sha256']
    checked={}
    for name in maps:
        for path,digest in summary[name].items():
            require(sha(ROOT/path)==digest,'Hash mismatch: '+path);checked[path]=digest
    require(summary['overall_preflight_assessed'] is False,'Unexpected overall preflight claim')
    inp=HERE/'inputs';events=rows(inp/'initial_events.csv');stations=rows(inp/'stations.csv')
    obs=rows(inp/'observations.csv');native=rows(inp/'initial_linearization_rows.csv')
    comparison=rows(HERE/'comparison.csv');columns=rows(inp/'initial_linearization_columns.csv')
    require(len(native)==len(comparison)==summary['rays'],'Row count')
    for n,column in enumerate(columns):
        require(int(column['column'])==n,'Column ordering')
        if n<4*len(events):
            i,d=divmod(n,4);event=events[i]
            require(column['parameter']=='xyzt'[d] and int(column['event'])==i and column['node']=='-1','Source column mapping')
            for key,value in event.items():
                if key not in ('id','x','y','z','t'):
                    require(column['source_'+key]==value,'Source column metadata')
    gradients=[[0.0]*4 for _ in native];source_entries=set();matrix_entries=0
    with (inp/'initial_linearization_matrix.csv').open() as f:
        for entry in csv.DictReader(f):
            r,c=int(entry['row']),int(entry['column']);v=float(entry['value'])
            require(0<=r<len(native) and 0<=c<len(columns) and math.isfinite(v),'Triplet bounds/finite')
            if c<4*len(events):
                i,d=divmod(c,4)
                require(i==int(native[r]['i']) and (r,c) not in source_entries,'Foreign/duplicate source triplet')
                source_entries.add((r,c));gradients[r][d]=v
            matrix_entries+=1
    errors=[];times=[];pairs=set();branches=collections.Counter();passed=0
    with (HERE/'references.jsonl').open() as f:
        references=[json.loads(line) for line in f]
    require(len(references)==len(native),'Reference count')
    absolute_indices=[n for n,o in enumerate(obs) if o['type']=='0']
    require([int(r['observation_row']) for r in native]==absolute_indices,'Complete original absolute support')
    for n,(original,row,record,g) in enumerate(zip(native,comparison,references,gradients)):
        require(all(row[k]==v for k,v in original.items()),'Original exported column changed')
        i,k=int(row['i']),int(row['station']);oi=int(row['observation_row']);o=obs[oi]
        require(int(row['row'])==n and record['row']==str(n) and record['event']==str(i) and record['station']==str(k) and record['observation_row']==str(oi),'Reference/native join')
        require((i,k) not in pairs,'Duplicate native pair');pairs.add((i,k))
        require(o['j']=='-1' and o['type']=='0' and o['i']==str(i) and o['station']==str(k),'Absolute observation join')
        for key,value in o.items():
            if key not in ('j','type','value'): require(row[key]==value,'Observation metadata changed')
        require(float(row['observed'])==float(format(float(o['value']),'.12g')),'Observed value serialization')
        require(row['event_i_resource_id']==events[i]['event_resource_id'] and row['origin_i_resource_id']==events[i]['origin_resource_id'],'Native source identity')
        for key in ('network_code','station_code','location_code','channel_code','channel_seed_id','channel_fdsn_source_id','metadata_epoch_start','metadata_epoch_end'):
            require(row[key]==stations[k][key],'Native channel/epoch join')
        require(row['channel_source_sha256']==stations[k]['source_sha256'],'Native receiver provenance')
        ref=record['reference'];first=ref['first_arrival']
        require(ref['complete'] and ref['reference_valid'] and first is not None,'Unresolved reference')
        require(row['reference_complete']==row['reference_valid']=='1' and row['reference_branch']==first['kind'],'Reference status')
        require(int(row['reference_candidate_count'])==len(ref['candidates']) and int(row['reference_near_tie_count'])==len(ref['near_ties']),'Reference candidates/ties')
        require(len(ref['near_ties'])==1,'Reference near tie')
        require(g[3]==1.0,'Missing/nonunit origin derivative')
        delta=[]
        for d,axis in enumerate('xyz'):
            require(float(row['source_'+axis+'_km'])==float(events[i][axis]) and float(row['receiver_'+axis+'_km'])==float(stations[k][axis]),'Native coordinate join')
            target=first['source_derivative_s_per_km'][d]
            require(float(row['production_source_d'+axis])==g[d] and float(row['reference_source_d'+axis])==target,'Source derivative reconstruction')
            difference=g[d]-target;delta.append(difference)
            require(float(row['production_source_d'+axis+'_minus_reference'])==difference,'Derivative difference')
        dt=float(row['ray_time'])-first['time_s'];norm=math.sqrt(sum(v*v for v in delta))
        require(float(row['reference_time_s'])==first['time_s'] and float(row['production_minus_reference_s'])==dt,'Time difference')
        require(row['ray_converged']==row['ray_initialization_succeeded']=='1','Saved ray flag')
        times.append(abs(dt));errors.append(norm);branches[first['kind']]+=1
        passed+=abs(dt)<=2.5e-5 and norm<=3e-6
    require(passed==len(native),'Unchanged accuracy limit failure')
    reported=summary['accuracy']['all']
    require(max(times)==reported['absolute_time_error_s']['maximum'] and max(errors)==reported['source_error_euclidean_norm_s_per_km']['maximum'],'Reported maxima')
    require(all(sha(ROOT/path)==digest for path,digest in checked.items()),'Input changed during review')
    result=dict(status='passed',material_issue_found=False,scope='Independent saved-table/native-metadata and sparse-source reconstruction review; no reference, solver, or inversion rerun; sampled and overall preflight not assessed.',verified_pairs=len(native),source_components=3*len(native),matrix_entries_checked=matrix_entries,native_metadata_fields_all_match=True,source_column_metadata_all_match=True,complete_original_absolute_support=True,reference_cache_hash_matches=True,source_derivatives_reconstructed_from_sparse_triplets=True,branch_counts=dict(branches),saved_local_convergence_pass=len(native),saved_initialization_pass=len(native),time_limit_s=2.5e-5,source_euclidean_norm_limit_s_per_km=3e-6,both_limits_pass=passed,maximum_absolute_time_error_s=max(times),maximum_source_error_euclidean_norm_s_per_km=max(errors),summary_sha256=sha(HERE/'summary.json'),packaging_sha256=sha(HERE/'packaging.json'),review_source_sha256=sha(Path(__file__)),verified_sha256=checked,limitations=summary['limitations'])
    (HERE/'independent_review.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:result[k] for k in ('status','verified_pairs','both_limits_pass','maximum_absolute_time_error_s','maximum_source_error_euclidean_norm_s_per_km')}))

if __name__=='__main__': main()
