#!/usr/bin/env python3
"""Independent initial-z references with reviewed rational turning-speed reconstruction.

No ray tracing, observations, inversion, or reuse of x-dependent truth times.
"""
import argparse
import collections
import csv
import gzip
import importlib.util
import itertools
import json
import math
import multiprocessing
import os
from pathlib import Path
import shutil
import signal
import sys
import time

from run_loma_layered_full import sha, utc, atomic_json, table, compressed_text, coordinate_pairs

ROOT = Path(__file__).resolve().parents[1]
REFERENCE_SHA256 = '55f3bd520aa472a3e4d4042808403eaa850c952301ea95d461331af9917ab5f2'
REFERENCE_REVIEW = 'data/development/precise_turn_reference_checks/review_003.json'
REFERENCE_REVIEW_SHA256 = '11b6c57ed050588161e8f30801e644f67b04737188ab235a4df0a677e1d4a192'
REFERENCE_CHECKS = 'data/development/precise_turn_reference_checks/003/summary.json'
REFERENCE_CHECKS_SHA256 = '4bc542d3f4d2edb0a9e6ef82212db07f2d9d6dfd7f0bfbdff6af4d44e2dd24e6'


def require(ok, message):
    if not ok: raise ValueError(message)


def checked_reference_review():
    review_path=ROOT/REFERENCE_REVIEW;checks_path=ROOT/REFERENCE_CHECKS
    require(sha(review_path)==REFERENCE_REVIEW_SHA256 and sha(checks_path)==REFERENCE_CHECKS_SHA256,
        'Reviewed reference evidence changed')
    review=json.loads(review_path.read_text());checks=json.loads(checks_path.read_text())
    require(review['status']=='passed' and checks['status']=='passed' and
        review['summary_sha256']==REFERENCE_CHECKS_SHA256 and review['variant_sha256']==REFERENCE_SHA256 and
        all(review['checks'].values()),'Precise-turn reference has not passed independent review')
    require(sha(ROOT/'diagnostics/first_arrival_1d_precise_turn_reference.py')==REFERENCE_SHA256,
        'Reviewed numerical helper changed')
    return {'numerical_review.json':review_path,'numerical_checks.json':checks_path}


def disjoint_output(data, out):
    require(data!=out and data not in out.parents and out not in data.parents,
        'Reference output must be disjoint from the unchanged simulation directory')


def comparison_ready(result, count):
    counts=result['counts']
    return (counts['reference_complete']==counts['reference_valid']==counts['derivative_defined']==count
        and not result['near_tie_pair_indices'])


def checked_inputs(data, plan_path):
    """Validate review links and only the small inputs used in this calculation."""
    ledger=json.loads((data/'simulation_execution.json').read_text())
    manifest=json.loads((data/'simulation_run_manifest.json').read_text())
    review=json.loads((data/'independent_simulation_review.json').read_text())
    plan=json.loads(plan_path.read_text())
    commands=[c for c in ledger['completed_commands'] if c['stage']=='simulate']
    require(ledger['status']=='completed' and ledger['return_code']==0 and
        ledger['result_status']=='simulation_complete_awaiting_independent_output_review' and
        len(commands)==1 and commands[0]['return_code']==0,'Simulation is not terminal successful')
    require(review['status']=='passed','Independent simulation review has not passed')
    for name,key in [('simulation_execution.json','simulation_execution_sha256'),
                     ('simulation_run_manifest.json','simulation_run_manifest_sha256')]:
        require(sha(data/name)==review[key],'Simulation review link changed: '+name)
    require(sha(data/'simulation_run_manifest.json')==ledger['output_sha256']['simulation_run_manifest.json'],
        'Terminal run manifest hash changed')
    require(sha(data/'analytic_truth_manifest.json')==ledger['analytic_truth_manifest_sha256']==manifest['prepared_manifest_sha256'],
        'Simulation truth provenance link changed')
    names=['initial_events.csv','stations.csv','initial_grid.csv','run.cfg','ray_samples.csv',
        'preparation_manifest.json','analytic_truth_manifest.json','simulation_execution.json',
        'simulation_run_manifest.json','independent_simulation_review.json']
    files={name:data/name for name in names}
    for name,path in files.items():
        if name!='independent_simulation_review.json':
            require(sha(path)==review['input_sha256'][name],'Reviewed initial input changed: '+name)
        if name in plan['input_sha256']:
            require(sha(path)==plan['input_sha256'][name],'Planned initial input changed: '+name)
    require(sha(data/'initial_events.csv')==ledger['output_sha256']['initial_events.csv'],
        'Initial events do not match completed simulation')
    counts=manifest['expected_counts'];expected=(counts['events'],counts['receivers'])
    require(expected==(review['source_count'],review['receiver_count']) and
        counts['unique_rays']==review['arrival_count']==expected[0]*expected[1], 'Full geometry count disagreement')
    files['inverse_plan.json']=plan_path
    return files,expected


def geometry(events, stations, grid, expected):
    require((len(events),len(stations))==tuple(expected) and all(n>0 for n in expected),'Incomplete initial geometry')
    for rows in (events,stations):
        require(all(row['id']==str(n) for n,row in enumerate(rows)),'Native indices not consecutive')
        require(all(math.isfinite(float(row[k])) for row in rows for k in 'xyzt'),'Nonfinite native geometry/time correction')
    require(all(row['event_resource_id'] and row['origin_resource_id'] for row in events),'Missing source identity')
    for row in stations:
        require(all(row[k] for k in ('network_code','station_code','channel_code','channel_seed_id',
            'channel_fdsn_source_id','metadata_epoch_start')),'Missing receiver identity')
        require(row['channel_seed_id']=='.'.join(row[k] for k in ('network_code','station_code','location_code','channel_code')),
            'Receiver SEED fields disagree')
    nodes=[tuple(float(row[k]) for k in ('x','y','z','v')) for row in grid]
    require(all(all(math.isfinite(v) for v in node) and node[3]>0 for node in nodes),'Invalid velocity grid')
    axes=[sorted(set(node[d] for node in nodes)) for d in range(3)]
    require(all(len(axis)>=2 for axis in axes) and len(nodes)==len(set(node[:3] for node in nodes)) and
        set(node[:3] for node in nodes)==set(itertools.product(*axes)),'Grid is not a complete unique Cartesian product')
    levels=sorted(set((node[2],node[3]) for node in nodes))
    require(len(levels)==len(axes[2]),'Initial velocity is not z-only')
    require(all(a[1]<=b[1] for a,b in zip(levels,levels[1:])),'Initial depth profile is not nondecreasing')
    box=[[axis[0],axis[-1]] for axis in axes]
    require(all(box[d][0]<=float(row[k])<=box[d][1] for rows in (events,stations) for row in rows
        for d,k in enumerate('xyz')),'Initial endpoint outside finite original grid')
    return levels,box


def load_reference(path):
    spec=importlib.util.spec_from_file_location('initial_z_reference_frozen',str(path))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.enumerate_arrivals


def reference_for(pair, levels, enumerate_arrivals):
    # Only xyz enter the reference; arbitrary saved source/receiver t is metadata.
    try:
        depths,speeds=map(list,zip(*levels))
        result=enumerate_arrivals(depths,speeds,pair[0],pair[1])
        json.dumps(result,allow_nan=False)
        return result
    except (ArithmeticError,ValueError,RuntimeError) as error:
        return dict(complete=False,reference_valid=False,candidates=[],first_arrival=None,
            unresolved=[dict(reason='Reference arithmetic exception',exception_type=type(error).__name__,exception=str(error))])


def worker_init(path, levels):
    global WORKER_REFERENCE, WORKER_LEVELS
    WORKER_REFERENCE=load_reference(Path(path));WORKER_LEVELS=levels


def worker_reference(pair):
    return reference_for(pair,WORKER_LEVELS,WORKER_REFERENCE)


def boundary_fields(source, receiver, box):
    return {prefix+'on_'+axis+'_'+side+'_face':int(float(row[axis])==box[d][n])
        for prefix,row in [('source_',source),('receiver_',receiver)]
        for d,axis in enumerate('xyz') for n,side in enumerate(('lower','upper'))}


def write_references(out, events, stations, levels, box, references, progress):
    counts=collections.Counter();invalid=[];ties=[];minimum=math.inf;maximum=-math.inf
    with compressed_text(out/'references.csv.gz') as csv_stream, compressed_text(out/'certificates.jsonl.gz') as json_stream:
        writer=None
        for index,(source,receiver) in enumerate(itertools.product(events,stations)):
            i,k=divmod(index,len(stations));ref=next(references);first=ref.get('first_arrival')
            require(not first or (ref['complete'] and ref['reference_valid']),'Invalid reference exposes first arrival')
            for candidate in ref['candidates']:
                turn=candidate.get('turning_depth_km')
                require(turn is None or box[2][0]<=turn<=box[2][1],'Candidate outside finite depth domain')
            row=dict(pair_index=index,event=i,station=k,reference_complete=int(ref['complete']),reference_valid=int(ref['reference_valid']),
                candidate_count=len(ref['candidates']),near_tie_count=len(ref.get('near_ties',[])),
                time_s=first['time_s'] if first else '',branch=first['kind'] if first else '',
                turning_depth_km=first['turning_depth_km'] if first and first['turning_depth_km'] is not None else '')
            gradient=first.get('source_derivative_s_per_km') if first else None
            for d,axis in enumerate('xyz'): row['source_d'+axis+'_s_per_km']=gradient[d] if gradient is not None else ''
            row.update(boundary_fields(source,receiver,box))
            row.update({'source_'+name:value for name,value in source.items()})
            row.update({'receiver_'+name:value for name,value in receiver.items()})
            if writer is None:
                writer=csv.DictWriter(csv_stream,fieldnames=list(row),lineterminator='\n');writer.writeheader()
            writer.writerow(row)
            json_stream.write(json.dumps(dict(pair_index=index,event=i,station=k,
                native_metadata_mapping='references.csv.gz: pair_index; inputs/initial_events.csv: id=event; inputs/stations.csv: id=station',
                source_time_included=False,reference=ref),allow_nan=False,separators=(',',':'))+'\n')
            counts['pairs']+=1;counts['reference_complete']+=ref['complete'];counts['reference_valid']+=ref['reference_valid']
            counts['candidate_total']+=len(ref['candidates']);counts['derivative_defined']+=gradient is not None
            if first:
                counts['branch_'+first['kind']]+=1;minimum=min(minimum,first['time_s']);maximum=max(maximum,first['time_s'])
            else: invalid.append(index)
            if len(ref.get('near_ties',[]))>1: ties.append(index)
            if k==len(stations)-1:
                csv_stream.flush();json_stream.flush();progress(dict(counts))
        require(next(references,None) is None,'Extra calculated references')
    return dict(counts=dict(counts),invalid_reference_pair_indices=invalid,near_tie_pair_indices=ties,
        time_range_s=[minimum,maximum] if minimum<math.inf else None)


def verify_outputs(out, events, stations, box):
    count=0
    with gzip.open(str(out/'references.csv.gz'),'rt',newline='') as c, gzip.open(str(out/'certificates.jsonl.gz'),'rt') as j:
        for row,line in itertools.zip_longest(csv.DictReader(c),j):
            require(row is not None and line is not None and count<len(events)*len(stations),'Table/certificate length mismatch')
            i,k=divmod(count,len(stations));record=json.loads(line);ref=record['reference'];first=ref.get('first_arrival')
            require(all(int(row[key])==value and record[key]==value for key,value in [('pair_index',count),('event',i),('station',k)]),'Reordered native support')
            require(record['source_time_included'] is False,'Source time included in pure travel time')
            for prefix,native in [('source_',events[i]),('receiver_',stations[k])]:
                require(all(row[prefix+key]==value for key,value in native.items()),'Native metadata changed')
            require(all(int(row[key])==value for key,value in boundary_fields(events[i],stations[k],box).items()),'Boundary flags changed')
            for key,value in [('reference_complete',int(ref['complete'])),('reference_valid',int(ref['reference_valid'])),
                    ('candidate_count',len(ref['candidates'])),('near_tie_count',len(ref.get('near_ties',[])))]:
                require(int(row[key])==value,'Reference status/count mismatch')
            require(row['branch']==(first['kind'] if first else ''),'Reference branch mismatch')
            gradient=first.get('source_derivative_s_per_km') if first else None
            values=[('time_s',first['time_s'] if first else None),('turning_depth_km',first.get('turning_depth_km') if first else None)]
            values += [('source_d'+axis+'_s_per_km',gradient[d] if gradient is not None else None) for d,axis in enumerate('xyz')]
            for key,value in values:
                require((value is None and row[key]=='') or (value is not None and math.isfinite(float(row[key])) and float(row[key])==value),'Reference numeric/certificate mismatch')
            count+=1
    require(count==len(events)*len(stations),'Incomplete native support')
    return count


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data',default='data/loma_lon_analytic_001');parser.add_argument('--output',required=True)
    parser.add_argument('--plan',default='data/development/loma_lon_initial_reference_plan_002/plan.json')
    parser.add_argument('--workers',type=int,default=4);args=parser.parse_args()
    data=(ROOT/args.data).resolve();out=(ROOT/args.output).resolve();plan=(ROOT/args.plan).resolve()
    for p in (data,out,plan):p.relative_to(ROOT)
    require(args.workers>0,'workers must be positive');disjoint_output(data,out);out.mkdir(parents=True)
    started=time.monotonic();ledger=dict(status='preparing',started_utc=utc(),pid=os.getpid(),workers=args.workers,completed_pairs=0,
        command='PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python3 diagnostics/run_loma_initial_precise_turn_reference.py --data '+str(data.relative_to(ROOT))+' --output '+str(out.relative_to(ROOT))+' --plan '+str(plan.relative_to(ROOT))+' --workers '+str(args.workers))
    atomic_json(out/'execution.json',ledger)
    def terminate(signum,unused):raise SystemExit(128+signum)
    signal.signal(signal.SIGTERM,terminate)
    try:
        files,expected=checked_inputs(data,plan)
        files.update(checked_reference_review())
        sources=[Path(__file__).resolve(),ROOT/'diagnostics/run_loma_layered_full.py',ROOT/'diagnostics/first_arrival_1d_precise_turn_reference.py']
        require(sha(sources[-1])==REFERENCE_SHA256,'Reviewed numerical helper changed')
        hashes={str(p.relative_to(ROOT)):sha(p) for p in list(files.values())+sources}
        saved=out/'inputs';saved.mkdir();snapshot=out/'source';snapshot.mkdir();copies={}
        for name,path in files.items():
            shutil.copyfile(str(path),str(saved/name));copies[str(path.relative_to(ROOT))]=saved/name
        for path in sources:
            shutil.copyfile(str(path),str(snapshot/path.name));copies[str(path.relative_to(ROOT))]=snapshot/path.name
        for name,path in copies.items():require(sha(path)==hashes[name],'Changed during freeze: '+name)
        for path,digest in [(snapshot/'first_arrival_1d_precise_turn_reference.py',REFERENCE_SHA256),
                (saved/'numerical_review.json',REFERENCE_REVIEW_SHA256),(saved/'numerical_checks.json',REFERENCE_CHECKS_SHA256)]:
            require(sha(path)==digest,'Frozen numerical source/review differs from reviewed selection')
        _,events=table(saved/'initial_events.csv');_,stations=table(saved/'stations.csv');_,grid=table(saved/'initial_grid.csv')
        levels,box=geometry(events,stations,grid,expected);reference_path=snapshot/'first_arrival_1d_precise_turn_reference.py'
        reference=load_reference(reference_path)
        import numpy
        import scipy
        ledger.update(status='running',expected_pairs=len(events)*len(stations),input_source_sha256=hashes,
            python_version=sys.version.split()[0],numpy_version=numpy.__version__,scipy_version=scipy.__version__)
        atomic_json(out/'execution.json',ledger)
        def progress(counts):
            ledger.update(completed_pairs=counts['pairs'],counts=counts,seconds=time.monotonic()-started,updated_utc=utc())
            atomic_json(out/'execution.json',ledger)
            if counts['pairs']%(20*len(stations))==0:print('Enumerated {}/{} initial native pairs'.format(counts['pairs'],len(events)*len(stations)),flush=True)
        if args.workers==1:
            refs=(reference_for(pair,levels,reference) for pair in coordinate_pairs(events,stations))
            result=write_references(out,events,stations,levels,box,refs,progress)
        else:
            with multiprocessing.Pool(args.workers,initializer=worker_init,initargs=(str(reference_path),levels)) as pool:
                refs=pool.imap(worker_reference,coordinate_pairs(events,stations),chunksize=8)
                result=write_references(out,events,stations,levels,box,refs,progress)
        ledger.update(status='validating');atomic_json(out/'execution.json',ledger)
        verified=verify_outputs(out,events,stations,box)
        for name,expected_hash in hashes.items():
            require(sha(ROOT/name)==sha(copies[name])==expected_hash,'Source/input changed during reference run: '+name)
        summary=dict(status='complete' if result['counts']['reference_valid']==verified else 'completed_with_unresolved_references',
            scope='Independent continuous reference for complete saved perturbed initial geometry and depth-only initial grid; no observations, rays or inversion computed',
            source_count=len(events),receiver_count=len(stations),expected_pairs=len(events)*len(stations),verified_pairs=verified,
            reference_comparison_ready=comparison_ready(result,verified),
            reference_quality_basis='Every reference complete and valid, no near-tied branches, and finite defined source derivatives for every pair; separate from execution completion',
            input_source_sha256=hashes,profile_depth_velocity_km_km_s=levels,original_box_km=box,
            coordinate_mapping='Reference and saved source derivatives use original x,y,z axes; no permutation',
            source_time_included=False,source_time_basis='Saved source_t is preserved native metadata, excluded from pure propagation travel time',
            finite_box_basis='Every candidate remains within the finite depth profile; horizontal coordinates move monotonically between endpoints in the original convex rectangle',
            native_metadata_mapping='Every source_/receiver_ field is preserved verbatim in references.csv.gz; exact input tables are frozen',
            command=ledger['command'],workers=args.workers,seconds=time.monotonic()-started,
            limitations=['Only the saved horizontally uniform nondecreasing initial model is covered.',
                'Rational turning-speed reconstruction changes only candidate evaluation; isolated roots, physical formulas and acceptance gates are unchanged.',
                'Time ordering uses ordinary floating point, not interval-certified minimum-time ranking.',
                'Near ties retain branch-specific derivatives; no unique derivative is asserted at a tie.',
                'Endpoint box flags are explicit; derivatives at boundary sources are branch derivatives and must not imply an out-of-domain centered perturbation.',
                'Invalid/unresolved references keep all certificates and blank first-arrival values; no scientific gate is relaxed.',
                'This does not certify the numerical forward operator or any inversion.'],**result)
        summary['output_sha256']={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file() and p.name!='execution.json'}
        atomic_json(out/'summary.json',summary)
        ledger.update(status='completed',result_status=summary['status'],finished_utc=utc(),seconds=time.monotonic()-started,
            summary_sha256=sha(out/'summary.json'));atomic_json(out/'execution.json',ledger)
        print(json.dumps({k:summary[k] for k in ('status','verified_pairs','counts','time_range_s')},indent=2),flush=True)
    except BaseException as error:
        ledger.update(status='interrupted' if isinstance(error,(KeyboardInterrupt,SystemExit)) else 'failed',
            finished_utc=utc(),seconds=time.monotonic()-started,error_type=type(error).__name__,error=str(error))
        atomic_json(out/'execution.json',ledger);raise

if __name__=='__main__':main()
