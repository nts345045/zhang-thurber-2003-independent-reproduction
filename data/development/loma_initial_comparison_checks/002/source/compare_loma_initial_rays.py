#!/usr/bin/env python3
"""Compare saved full initial rays to continuous references; never retrace rays."""
import argparse
import collections
import csv
import gzip
import hashlib
import itertools
import json
import math
from pathlib import Path
import shutil
import signal
import sys

from run_loma_layered_full import sha, utc, atomic_json, table, compressed_text

ROOT=Path(__file__).resolve().parents[1]
TIME_LIMIT=2.5e-5
SOURCE_LIMIT=3e-6


def require(ok,message):
    if not ok:raise ValueError(message)


def relative(path):
    return str(path.resolve().relative_to(ROOT))


def disjoint(out,*inputs):
    require(out!=ROOT,'Output cannot be the repository root')
    for path in inputs:
        require(out!=path and out not in path.parents and path not in out.parents,'Output must be disjoint from input evidence')


def safe_member(base,name):
    path=(base/name).resolve();path.relative_to(base.resolve());return path


def checked_reference(reference):
    summary=json.loads((reference/'summary.json').read_text());ledger=json.loads((reference/'execution.json').read_text())
    require(ledger['status']=='completed' and ledger['summary_sha256']==sha(reference/'summary.json'),'Reference is not terminal with matching summary')
    require(summary['status'] in ('complete','completed_with_unresolved_references') and summary['source_time_included'] is False,
        'Reference completion/time definition differs')
    for name in ('review.json','independent_review.json'):
        review=json.loads((reference/name).read_text())
        require(review['status']=='passed' and review['summary_sha256']==sha(reference/'summary.json') and
            review['execution_sha256']==sha(reference/'execution.json'),'Missing/stale independent reference review: '+name)
    files={name:safe_member(reference,name) for name in summary['output_sha256']}
    for name,path in files.items():require(sha(path)==summary['output_sha256'][name],'Reference artifact changed: '+name)
    required={'references.csv.gz','certificates.jsonl.gz','inputs/initial_events.csv','inputs/stations.csv',
        'inputs/initial_grid.csv','inputs/run.cfg','inputs/simulation_execution.json','inputs/simulation_run_manifest.json',
        'inputs/independent_simulation_review.json','inputs/analytic_truth_manifest.json'}
    require(required<=set(files),'Incomplete frozen reference inventory')
    for name in ('summary.json','execution.json','review.json','independent_review.json'):files[name]=reference/name
    return summary,files


def checked_preflight(data,reference,reference_summary):
    # Atomic replacement by the live controller makes this one opened file a
    # consistent snapshot. Its later mutation is expected and is not rechecked.
    captured=(data/'preflight_execution.json').read_bytes();ledger=json.loads(captured.decode('utf-8'))
    manifest=json.loads((data/'preflight_run_manifest.json').read_text())
    full=json.loads((data/'full_initial_checks.json').read_text())
    commands=[r for r in ledger['completed_commands'] if r['stage']=='initial_matrix_preflight']
    require(len(commands)==1 and commands[0]['return_code']==0,'Full initial matrix stage has not completed successfully')
    binary=(ROOT/manifest['binary']).resolve();binary.relative_to(ROOT)
    command=commands[0]['command']
    require(len(command)==5 and Path(command[0]).resolve()==binary and command[1]=='invert' and
        Path(command[2]).resolve()==data/'run.cfg' and Path(command[3]).resolve()==data and command[4]=='dd',
        'Completed command is not this frozen initial matrix preflight')
    require(ledger['threads']==manifest['threads'] and manifest['matrix_preflight_only'] is True and
        manifest['matrix_mode']=='dd' and manifest['matrix_iteration']==manifest['matrix_stage']==0,'Matrix stage/source setting mismatch')
    require(sha(binary)==manifest['binary_sha256'],'Frozen preflight binary changed')
    cfg={}
    for line in (data/'run.cfg').read_text().splitlines():
        words=line.split('#',1)[0].split()
        if words:
            require(len(words)==2,'Malformed assessment configuration');cfg[words[0]]=float(words[1])
    require(cfg['iterations']==cfg['matrix_preflight_only']==1 and cfg['stage_length']>0,'Not a stage-0 census-only configuration')
    for name in ('initial_events.csv','stations.csv','initial_grid.csv'):
        require(sha(data/name)==manifest['input_sha256'][name]==sha(reference/'inputs'/name),'Initial geometry/grid byte mismatch: '+name)
    require(sha(data/'run.cfg')==manifest['input_sha256']['run.cfg'],'Assessment configuration changed')
    names=['initial_events.csv','stations.csv','initial_grid.csv','run.cfg','dd_preflight_ray_status.csv',
        'dd_matrix_preflight.csv','full_initial_checks.json','preflight_run_manifest.json','preflight_source.tar.gz']
    require(sha(data/'preflight_source.tar.gz')==manifest['source_archive_sha256'],'Frozen preflight source archive changed')
    for name in ('simulation_execution.json','simulation_run_manifest.json','independent_simulation_review.json','analytic_truth_manifest.json'):
        path='simulation_provenance/'+name
        require(sha(data/path)==manifest['input_sha256'][path]==sha(reference/'inputs'/name),'Simulation provenance differs: '+name)
        names.append(path)
    require(manifest['simulation_review_sha256']==sha(reference/'inputs/independent_simulation_review.json'),'Different simulation review')
    count=reference_summary['expected_pairs'];expected=manifest['expected_counts']
    require(expected['events']==reference_summary['source_count'] and expected['receivers']==reference_summary['receiver_count'] and
        expected['unique_rays']==full['full_rays']==count and full['matrix_stage']==0,'Incomplete/mismatched full native support')
    _,matrix=table(data/'dd_matrix_preflight.csv')
    require(len(matrix)==1 and matrix[0]==full['matrix_census'] and matrix[0]['iteration']=='0','Stage-0 census/check mismatch')
    require(int(matrix[0]['observation_rows'])==expected['total_rows'],'Matrix observation inventory differs')
    files={name:data/name for name in names}
    return manifest,full,files,captured,ledger


def native_join(row,reference_row,event,station):
    for prefix,native in [('source_',event),('receiver_',station)]:
        for key,value in native.items():
            require(reference_row[prefix+key]==value,'Reference native metadata mismatch')
            if key not in ('id','x','y','z','t'):
                require(row[prefix+key]==value,'Ray native metadata mismatch: '+prefix+key)
        for axis in 'xyz':
            require(float(row[prefix+axis])==float(format(float(native[axis]),'.12g')),'Ray coordinates differ from saved initial geometry')
    require(float(row['source_t'])==float(format(float(event['t']),'.12g')),'Saved source_t changed')


def compare_row(row,refrow,reference,box):
    """Retain flags separately from reference eligibility and numerical errors."""
    result=dict(row);first=reference.get('first_arrival');g=first.get('source_derivative_s_per_km') if first else None
    unique=len(reference.get('near_ties',[]))==1
    eligible=bool(reference['complete'] and reference['reference_valid'] and first and unique and g is not None and
        len(g)==3 and math.isfinite(first['time_s']) and all(math.isfinite(x) for x in g))
    require(int(refrow['reference_complete'])==int(reference['complete']) and int(refrow['reference_valid'])==int(reference['reference_valid']),
        'Reference flags/certificate mismatch')
    require(int(refrow['near_tie_count'])==len(reference.get('near_ties',[])) and int(refrow['candidate_count'])==len(reference['candidates']),
        'Reference candidate/tie count mismatch')
    require(refrow['branch']==(first['kind'] if first else ''),'Reference branch mismatch')
    for key,value in [('time_s',first['time_s'] if first else None)]+[('source_d'+a+'_s_per_km',g[d] if g is not None else None) for d,a in enumerate('xyz')]:
        require((value is None and refrow[key]=='') or (value is not None and float(refrow[key])==value),'Reference numeric/certificate mismatch')
    keep=['pair_index','reference_complete','reference_valid','candidate_count','near_tie_count','time_s','branch','turning_depth_km']
    keep += ['source_d'+a+'_s_per_km' for a in 'xyz']
    keep += [prefix+a for prefix in ('source_','receiver_') for a in 'xyzt']
    keep += [prefix+'on_'+a+'_'+side+'_face' for prefix in ('source_','receiver_') for a in 'xyz' for side in ('lower','upper')]
    for key in keep:
        value=refrow[key];result[key if key in ('reference_complete','reference_valid') else 'reference_'+key]=value
    for prefix in ('source_','receiver_'):
        for d,a in enumerate('xyz'):
            x=float(refrow[prefix+a]);require(box[d][0]<=x<=box[d][1],'Reference endpoint outside finite box')
            for side,n in [('lower',0),('upper',1)]:
                require(int(refrow[prefix+'on_'+a+'_'+side+'_face'])==int(x==box[d][n]),'Reference boundary flag mismatch')
    flag_names=['ray_finite','ray_path_in_domain','ray_exact_source_endpoint','ray_exact_receiver_endpoint',
        'ray_initialization_attempted','ray_initialization_succeeded','ray_converged']
    for name in flag_names:require(row[name] in ('0','1'),'Malformed ray flag: '+name)
    values=[float(row[key]) for key in ('ray_time','source_dx','source_dy','source_dz','ray_projected_gradient','ray_raw_gradient')]
    modeled_finite=all(math.isfinite(v) for v in values) and values[0]>=0
    path_valid=int(row['ray_path_points'])>=2
    comparable=eligible and modeled_finite
    dt=values[0]-first['time_s'] if comparable else None
    errors=[values[d+1]-g[d] for d in range(3)] if comparable else None
    norm=math.sqrt(sum(x*x for x in errors)) if comparable else None
    time_pass=comparable and abs(dt)<=TIME_LIMIT;source_pass=comparable and norm<=SOURCE_LIMIT
    flags_pass=all(row[key]=='1' for key in flag_names) and path_valid and modeled_finite
    result.update(reference_eligible=int(eligible),modeled_values_finite=int(modeled_finite),numerically_compared=int(comparable),
        time_error_s=dt if comparable else '',source_error_euclidean_norm_s_per_km=norm if comparable else '',
        time_limit_pass=int(time_pass),source_vector_limit_pass=int(source_pass),
        original_flags_and_path_pass=int(flags_pass),scientific_pass=int(flags_pass and time_pass and source_pass))
    for d,a in enumerate('xyz'):result['source_d'+a+'_error_s_per_km']=errors[d] if comparable else ''
    reasons=[]
    if not eligible:reasons.append('reference_not_unique_valid_with_defined_gradient')
    if not modeled_finite:reasons.append('modeled_values_nonfinite_or_negative_time')
    if not path_valid:reasons.append('ray_path_has_fewer_than_two_points')
    reasons += [key+'_false' for key in flag_names if row[key]!='1']
    if comparable and not time_pass:reasons.append('absolute_time_error_exceeds_25_microseconds')
    if comparable and not source_pass:reasons.append('source_vector_norm_exceeds_3e-6_s_per_km')
    return result,reasons


def compare(saved,out,refsummary,full):
    _,events=table(saved/'preflight/initial_events.csv');_,stations=table(saved/'preflight/stations.csv')
    count=0;counts=collections.Counter();failures=[];max_time=0.;max_source=0.;max_projected=0.;max_raw=0.
    with gzip.open(str(saved/'preflight/dd_preflight_ray_status.csv.gz'),'rt',newline='') as pf, \
         gzip.open(str(saved/'reference/references.csv.gz'),'rt',newline='') as rf, \
         gzip.open(str(saved/'reference/certificates.jsonl.gz'),'rt') as jf, compressed_text(out/'comparison.csv.gz') as output:
        writer=None
        for row,refrow,line in itertools.zip_longest(csv.DictReader(pf),csv.DictReader(rf),jf):
            require(row is not None and refrow is not None and line is not None,'Native ray/reference support lengths differ')
            i,k=divmod(count,len(stations));require(i<len(events),'Extra native ray')
            record=json.loads(line)
            require((row['event'],row['station'])==(str(i),str(k)) and
                all(int(refrow[key])==value and record[key]==value for key,value in [('pair_index',count),('event',i),('station',k)]),
                'Missing/reordered native ray/reference pair')
            require(record['source_time_included'] is False,'Reference includes source time')
            native_join(row,refrow,events[i],stations[k])
            result,reasons=compare_row(row,refrow,record['reference'],refsummary['original_box_km'])
            result['comparison_row']=count
            if writer is None:
                writer=csv.DictWriter(output,fieldnames=list(result),lineterminator='\n');writer.writeheader()
            writer.writerow(result)
            for key in ('reference_eligible','modeled_values_finite','numerically_compared','time_limit_pass','source_vector_limit_pass','original_flags_and_path_pass','scientific_pass'):
                counts[key]+=result[key]
            counts['saved_local_converged']+=row['ray_converged']=='1'
            if result['numerically_compared']:
                max_time=max(max_time,abs(result['time_error_s']));max_source=max(max_source,result['source_error_euclidean_norm_s_per_km'])
            if math.isfinite(float(row['ray_projected_gradient'])):max_projected=max(max_projected,float(row['ray_projected_gradient']))
            if math.isfinite(float(row['ray_raw_gradient'])):max_raw=max(max_raw,float(row['ray_raw_gradient']))
            if reasons:
                failure=dict(comparison_row=count,event=i,station=k,reasons=reasons,
                    event_resource_id=events[i]['event_resource_id'],origin_resource_id=events[i]['origin_resource_id'])
                failure.update({key:stations[k][key] for key in ('network_code','station_code','location_code','channel_code',
                    'channel_seed_id','channel_fdsn_source_id','metadata_epoch_start','metadata_epoch_end')})
                failures.append(failure)
            count+=1
    require(count==refsummary['verified_pairs']==refsummary['expected_pairs']==full['full_rays'],'Incomplete full native support')
    require(counts['saved_local_converged']==full['local_converged'] and max_projected==full['maximum_projected_gradient'] and
        max_raw==full['maximum_raw_gradient'],'Saved full-stage checks disagree with ray table')
    return dict(rows=count,counts=dict(counts),failures=failures,scientific_pass=counts['scientific_pass']==count,
        maximum_absolute_time_error_s=max_time if counts['numerically_compared'] else None,
        maximum_source_error_euclidean_norm_s_per_km=max_source if counts['numerically_compared'] else None)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--data',required=True)
    parser.add_argument('--reference',default='data/development/loma_initial_reference_001');parser.add_argument('--output',required=True)
    args=parser.parse_args();data=(ROOT/args.data).resolve();reference=(ROOT/args.reference).resolve();out=(ROOT/args.output).resolve()
    for path in (data,reference,out):path.relative_to(ROOT)
    disjoint(out,data,reference);out.mkdir(parents=True)
    ledger=dict(status='preparing',started_utc=utc(),command='python3 diagnostics/compare_loma_initial_rays.py --data '+relative(data)+' --reference '+relative(reference)+' --output '+relative(out))
    atomic_json(out/'execution.json',ledger)
    def interrupted(signum,unused):raise SystemExit(128+signum)
    signal.signal(signal.SIGTERM,interrupted)
    try:
        refsummary,ref_files=checked_reference(reference)
        manifest,full,pre_files,captured,pre_ledger=checked_preflight(data,reference,refsummary)
        hashes={relative(path):sha(path) for path in list(ref_files.values())+list(pre_files.values())}
        saved=out/'inputs';copies={}
        for group,files in [('reference',ref_files),('preflight',pre_files)]:
            for name,path in files.items():
                target=saved/group/name;target.parent.mkdir(parents=True,exist_ok=True)
                if group=='preflight' and name=='dd_preflight_ray_status.csv':
                    target=target.with_suffix('.csv.gz')
                    with path.open('rb') as src,target.open('xb') as raw:
                        with gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as dst:shutil.copyfileobj(src,dst)
                    h=hashlib.sha256()
                    with gzip.open(str(target),'rb') as stream:
                        for b in iter(lambda:stream.read(1048576),b''):h.update(b)
                    require(h.hexdigest()==hashes[relative(path)],'Status table changed during compressed snapshot')
                else:
                    shutil.copyfile(str(path),str(target));require(sha(target)==hashes[relative(path)],'Input changed during snapshot')
                copies[relative(path)]=str(target.relative_to(out))
        (saved/'preflight/preflight_execution_at_capture.json').write_bytes(captured)
        sources=[Path(__file__).resolve(),ROOT/'diagnostics/run_loma_layered_full.py']
        (out/'source').mkdir()
        for path in sources:
            hashes[relative(path)]=sha(path);target=out/'source'/path.name;shutil.copyfile(str(path),str(target));copies[relative(path)]=str(target.relative_to(out))
        ledger.update(status='comparing',input_source_sha256=hashes);atomic_json(out/'execution.json',ledger)
        result=compare(saved,out,refsummary,full)
        for name,digest in hashes.items():require(sha(ROOT/name)==digest,'Completed input/source changed during comparison: '+name)
        summary=dict(status='comparison_complete',scientific_status='all_existing_limits_and_flags_pass' if result['scientific_pass'] else 'failed_or_ineligible_rows_preserved',
            scope='Saved full initial rays versus frozen continuous initial-z references; no reference recomputation, ray trace or inversion',
            readiness_basis='completed_initial_matrix_preflight_command_with_frozen_full_status_and_checks',
            overall_preflight_assessed=False,preflight_status_at_capture=pre_ledger['status'],
            preflight_execution_at_capture_sha256=hashlib.sha256(captured).hexdigest(),
            initial_matrix_command=[c for c in pre_ledger['completed_commands'] if c['stage']=='initial_matrix_preflight'][0],
            time_limit_s=TIME_LIMIT,source_euclidean_norm_limit_s_per_km=SOURCE_LIMIT,
            time_basis='Pure ray_time minus reference propagation time; source_t retained separately and excluded',
            coordinate_mapping='Raw source_dx/dy/dz versus original xyz reference derivatives; no permutation',
            configuration_basis='Initial events/stations/grid and simulation provenance are byte identical; run.cfg intentionally differs for declared assessment settings',
            input_source_sha256=hashes,frozen_input_mapping=copies,command=ledger['command'],
            failure_join='Every failure carries native IDs and comparison_row in comparison.csv.gz; every native pair remains in that table',
            limitations=['This assesses the saved initial depth-only model, not later three-dimensional updates or nonlinear convergence.',
                'Existing local flags are retained independently of accuracy; no ray is removed from the comparison.',
                'Boundary and tied-branch derivatives retain their reference limitations; an ineligible reference cannot pass.',
                'The independent sampled refinement/finite-difference stage may still be running; it is not assessed here.',
                'CSV ray values have 12-significant-digit serialization; existing numerical limits are unchanged.'],**result)
        summary['output_sha256']={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file() and p!=out/'execution.json'}
        atomic_json(out/'summary.json',summary)
        ledger.update(status='completed',finished_utc=utc(),result_status=summary['scientific_status'],summary_sha256=sha(out/'summary.json'))
        atomic_json(out/'execution.json',ledger);print(json.dumps({k:summary[k] for k in ('status','scientific_status','rows','counts')},indent=2))
    except BaseException as error:
        ledger.update(status='interrupted' if isinstance(error,(KeyboardInterrupt,SystemExit)) else 'failed',finished_utc=utc(),
            error_type=type(error).__name__,error=str(error));atomic_json(out/'execution.json',ledger);raise

if __name__=='__main__':main()
