#!/usr/bin/env python3
"""Freeze and enumerate the full prepared Loma geometry with the layered reference.

This writes independent reference evidence only, never observations or solver input.
"""
import argparse
import collections
import contextlib
import csv
import datetime
import gzip
import hashlib
import importlib.util
import io
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

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1048576), b''):
            value.update(chunk)
    return value.hexdigest()


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def atomic_json(path, value):
    temporary = path.with_name(path.name+'.temporary')
    with temporary.open('w') as stream:
        json.dump(value, stream, indent=2, allow_nan=False); stream.write('\n')
        stream.flush(); os.fsync(stream.fileno())
    os.replace(str(temporary), str(path))


def table(path):
    with path.open() as stream:
        reader = csv.DictReader(stream); names, rows = reader.fieldnames, list(reader)
    if not names or len(set(names)) != len(names) or any(
            None in row or None in row.values() for row in rows):
        raise ValueError('Malformed CSV: '+path.name)
    return names, rows


def geometry(events, stations, grid, expected_counts):
    """Validate all native rows and the complete Cartesian x-only model grid."""
    if (len(events), len(stations)) != expected_counts:
        raise ValueError('Full prepared geometry counts changed')
    for rows in (events, stations):
        if any(row['id'] != str(n) for n, row in enumerate(rows)):
            raise ValueError('Native indices must be consecutive and unique')
        if any(not math.isfinite(float(row[k])) for row in rows for k in ('x','y','z','t')):
            raise ValueError('Nonfinite native geometry')
        if any(float(row['t']) != 0 for row in rows):
            raise ValueError('Reference geometry requires declared zero origin/receiver corrections')
    for row in events:
        if not row['event_resource_id'] or not row['origin_resource_id']:
            raise ValueError('Missing native source identity')
    for row in stations:
        if any(not row[k] for k in ('network_code','station_code','channel_code',
                'channel_seed_id','channel_fdsn_source_id','metadata_epoch_start')):
            raise ValueError('Missing native receiver identity')
        if row['channel_seed_id'] != '.'.join(row[k] for k in (
                'network_code','station_code','location_code','channel_code')):
            raise ValueError('Native receiver SEED fields disagree')
    nodes = [(float(row['x']),float(row['y']),float(row['z']),float(row['v'])) for row in grid]
    if any(not all(math.isfinite(q) for q in node) or node[3] <= 0 for node in nodes):
        raise ValueError('Nonfinite or nonpositive velocity grid')
    axes = [sorted(set(node[d] for node in nodes)) for d in range(3)]
    if any(len(axis)<2 for axis in axes) or len(nodes)!=len(set(node[:3] for node in nodes)) or (
            set(node[:3] for node in nodes) != set(itertools.product(*axes))):
        raise ValueError('Model grid is not a complete, unique Cartesian product')
    levels = sorted(set((node[0],node[3]) for node in nodes))
    if len(levels) != len(axes[0]):
        raise ValueError('Velocity depends on coordinates other than x')
    box = [[axis[0],axis[-1]] for axis in axes]
    if any(not box[d][0] <= float(row[k]) <= box[d][1]
           for rows in (events,stations) for row in rows for d,k in enumerate('xyz')):
        raise ValueError('Native endpoint outside the original finite box')
    return levels, box


@contextlib.contextmanager
def compressed_text(path):
    # Empty filename and mtime=0 keep gzip headers independent of paths and clocks.
    with path.open('xb') as raw:
        with gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0) as zipped:
            with io.TextIOWrapper(zipped, encoding='utf-8', newline='') as stream:
                yield stream


def reference_for(source, receiver, depths, speeds, permuted_box, enumerate_arrivals):
    try:
        result=enumerate_arrivals(depths,speeds,[source[1],source[2],source[0]],
            [receiver[1],receiver[2],receiver[0]],bounds=permuted_box)
        json.dumps(result,allow_nan=False)
        return result
    except (ArithmeticError,ValueError) as error:
        return dict(complete=False,reference_valid=False,candidates=[],first_arrival=None,
            unresolved=[dict(reason='Reference arithmetic exception',exception=str(error))])


def load_reference(path):
    sys.path.insert(0,str(path.parent))
    spec=importlib.util.spec_from_file_location('layered_frozen',str(path))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.enumerate_arrivals


def worker_init(path, levels, box):
    global WORKER_REFERENCE, WORKER_DEPTHS, WORKER_SPEEDS, WORKER_BOX
    WORKER_REFERENCE=load_reference(Path(path));WORKER_DEPTHS,WORKER_SPEEDS=map(list,zip(*levels))
    WORKER_BOX=[box[1],box[2],box[0]]


def worker_reference(pair):
    return reference_for(pair[0],pair[1],WORKER_DEPTHS,WORKER_SPEEDS,WORKER_BOX,WORKER_REFERENCE)


def coordinate_pairs(events,stations):
    for source in events:
        for receiver in stations:
            yield ([float(source[k]) for k in 'xyz'],[float(receiver[k]) for k in 'xyz'])


def stream_references(out, events, stations, levels, box, enumerate_arrivals, progress, ordered_references=None):
    depths, speeds = map(list, zip(*levels)); permuted_box = [box[1],box[2],box[0]]
    counts = collections.Counter(); times=[]; unresolved=[]; ties=[]
    with compressed_text(out/'references.csv.gz') as csv_stream, compressed_text(out/'certificates.jsonl.gz') as json_stream:
        writer = None
        for i, source in enumerate(events):
            s = [float(source[k]) for k in 'xyz']
            for k, receiver in enumerate(stations):
                index = i*len(stations)+k; r = [float(receiver[a]) for a in 'xyz']
                reference = (next(ordered_references) if ordered_references is not None else
                    reference_for(s,r,depths,speeds,permuted_box,enumerate_arrivals))
                first = reference.get('first_arrival')
                if first and (not reference['complete'] or not reference['reference_valid']):
                    raise ValueError('Invalid reference exposes a first-arrival value')
                for candidate in reference['candidates']:
                    normal = candidate.get('turning_depth_km')
                    if normal is not None and not box[0][0] <= normal <= box[0][1]:
                        raise ValueError('Reference candidate leaves the finite normal domain')
                row = dict(pair_index=index,event=i,station=k,reference_complete=int(reference['complete']),
                    reference_valid=int(reference['reference_valid']),candidate_count=len(reference['candidates']),
                    near_tie_count=len(reference.get('near_ties',[])),time_s=first['time_s'] if first else '',
                    branch=first['kind'] if first else '',
                    turning_x_km=first['turning_depth_km'] if first and first['turning_depth_km'] is not None else '')
                gradient = first.get('source_derivative_s_per_km') if first else None
                for d,axis in enumerate('xyz'):
                    row['source_d'+axis+'_s_per_km'] = gradient[(2,0,1)[d]] if gradient is not None else ''
                row.update({'source_'+name:value for name,value in source.items()})
                row.update({'receiver_'+name:value for name,value in receiver.items()})
                if writer is None:
                    writer=csv.DictWriter(csv_stream,fieldnames=list(row),lineterminator='\n');writer.writeheader()
                writer.writerow(row)
                record=dict(pair_index=index,event=i,station=k,
                    native_metadata_mapping='references.csv.gz: pair_index; inputs/truth_events.csv: id=event; inputs/stations.csv: id=station',
                    reference=reference)
                json_stream.write(json.dumps(record,allow_nan=False,separators=(',',':'))+'\n')
                counts['pairs']+=1;counts['reference_complete']+=reference['complete']
                counts['reference_valid']+=reference['reference_valid']
                counts['candidate_total']+=len(reference['candidates'])
                if first:
                    counts['branch_'+first['kind']]+=1;times.append(first['time_s'])
                else:unresolved.append(index)
                if len(reference.get('near_ties',[]))>1:ties.append(index)
            csv_stream.flush();json_stream.flush()
            progress(dict(counts))
    return dict(counts=dict(counts),unresolved_pair_indices=unresolved,near_tie_pair_indices=ties,
        time_range_s=[min(times),max(times)] if times else None)


def verify_outputs(out, events, stations):
    """Read both streams back and verify complete Cartesian support and all metadata."""
    count=0
    with gzip.open(str(out/'references.csv.gz'),'rt',newline='') as csv_stream, gzip.open(str(out/'certificates.jsonl.gz'),'rt') as json_stream:
        for row,line in itertools.zip_longest(csv.DictReader(csv_stream),json_stream):
            if row is None or line is None:
                raise ValueError('Reference table/certificate lengths disagree')
            if count >= len(events)*len(stations):raise ValueError('Extra reference pair')
            i,k=divmod(count,len(stations));record=json.loads(line)
            if any(int(row[name])!=value or record[name]!=value for name,value in (
                    ('pair_index',count),('event',i),('station',k))):
                raise ValueError('Missing, repeated, or reordered reference pair')
            for prefix,native in (('source_',events[i]),('receiver_',stations[k])):
                if any(row[prefix+name]!=value for name,value in native.items()):
                    raise ValueError('Native metadata changed in output')
            first=record['reference'].get('first_arrival')
            if (first is None)!=(row['time_s']=='') or (first and float(row['time_s'])!=first['time_s']):
                raise ValueError('Reference time/certificate mismatch')
            for name,key in (('reference_complete','complete'),('reference_valid','reference_valid')):
                if int(row[name])!=int(record['reference'][key]):
                    raise ValueError('Reference flags/certificate mismatch')
            reference=record['reference']
            if int(row['candidate_count'])!=len(reference['candidates']) or int(row['near_tie_count'])!=len(reference.get('near_ties',[])):
                raise ValueError('Reference candidate count/certificate mismatch')
            if row['branch']!=(first['kind'] if first else ''):
                raise ValueError('Reference branch/certificate mismatch')
            turn=first.get('turning_depth_km') if first else None
            if (turn is None)!=(row['turning_x_km']=='') or (turn is not None and float(row['turning_x_km'])!=turn):
                raise ValueError('Reference turning coordinate/certificate mismatch')
            gradient=first.get('source_derivative_s_per_km') if first else None
            for d,axis in enumerate('xyz'):
                value=row['source_d'+axis+'_s_per_km']
                if (gradient is None)!=(value=='') or (gradient is not None and float(value)!=gradient[(2,0,1)[d]]):
                    raise ValueError('Reference source gradient/certificate mismatch')
            count+=1
    if count!=len(events)*len(stations):raise ValueError('Incomplete reference support')
    return count


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True)
    parser.add_argument('--workers',type=int,default=4)
    args=parser.parse_args();out=(ROOT/args.output).resolve();out.relative_to(ROOT)
    if args.workers<1:parser.error('workers must be positive')
    # Exclusive creation precedes all work; failed/incomplete directories are never reused.
    out.mkdir(parents=True)
    ledger=dict(status='preparing',started_utc=utc(),pid=os.getpid(),workers=args.workers,completed_pairs=0,
        command='PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python3 diagnostics/run_loma_layered_full.py --output '+str(out.relative_to(ROOT))+' --workers '+str(args.workers))
    atomic_json(out/'execution.json',ledger);started=time.monotonic()
    def terminate(signum,unused):
        raise SystemExit(128+signum)
    signal.signal(signal.SIGTERM,terminate)
    try:
        data=ROOT/'data/loma_lom_001';terminal=ROOT/'data/development/loma_geometry_preflight/001/summary.json'
        manifest=json.loads(terminal.read_text())
        commands=[c for c in manifest['commands'] if c['name']=='geometrycheck']
        if manifest['status']!='completed' or len(commands)!=1 or commands[0]['exit_code']!=0:
            raise ValueError('Require completed original geometry evidence, without inferring scientific acceptance')
        files={name:data/name for name in manifest['input_sha256']}
        if not {'truth_events.csv','stations.csv','truth_grid.csv','authoritative_geometry'}<=set(files):
            raise ValueError('Missing full geometry input hashes')
        for name,expected in manifest['input_sha256'].items():
            if sha(files[name])!=expected:raise ValueError('Input changed: '+name)
        sources=[Path(__file__).resolve(),ROOT/'diagnostics/first_arrival_layered_reference.py',ROOT/'diagnostics/first_arrival_1d_reference.py']
        hashes={str(p.relative_to(ROOT)):sha(p) for p in list(files.values())+sources+[terminal]}
        saved=out/'inputs';saved.mkdir();snapshot=out/'source';snapshot.mkdir()
        for name,path in files.items():shutil.copyfile(str(path),str(saved/name))
        shutil.copyfile(str(terminal),str(saved/'terminal_geometry_summary.json'))
        for path in sources:shutil.copyfile(str(path),str(snapshot/path.name))
        copies={str(path.relative_to(ROOT)):saved/name for name,path in files.items()}
        copies.update({str(path.relative_to(ROOT)):snapshot/path.name for path in sources})
        copies[str(terminal.relative_to(ROOT))]=saved/'terminal_geometry_summary.json'
        for name,path in copies.items():
            if sha(path)!=hashes[name]:raise ValueError('Changed while freezing: '+name)
        _,events=table(saved/'truth_events.csv');_,stations=table(saved/'stations.csv');_,grid=table(saved/'truth_grid.csv')
        levels,box=geometry(events,stations,grid,(724,52))
        reference_path=snapshot/'first_arrival_layered_reference.py'
        enumerate_arrivals=load_reference(reference_path)
        import numpy
        import scipy
        ledger.update(status='running',expected_pairs=len(events)*len(stations),input_source_sha256=hashes,
            python_version=sys.version.split()[0],numpy_version=numpy.__version__,scipy_version=scipy.__version__)
        atomic_json(out/'execution.json',ledger)
        def progress(counts):
            ledger.update(completed_pairs=counts['pairs'],counts=counts,seconds=time.monotonic()-started,updated_utc=utc())
            atomic_json(out/'execution.json',ledger)
            if counts['pairs']%(52*20)==0:print('Enumerated {}/37648 native geometry pairs'.format(counts['pairs']),flush=True)
        if args.workers==1:
            result=stream_references(out,events,stations,levels,box,enumerate_arrivals,progress)
        else:
            with multiprocessing.Pool(args.workers,initializer=worker_init,initargs=(str(reference_path),levels,box)) as pool:
                ordered=pool.imap(worker_reference,coordinate_pairs(events,stations),chunksize=8)
                result=stream_references(out,events,stations,levels,box,None,progress,ordered)
        ledger.update(status='validating');atomic_json(out/'execution.json',ledger)
        verified=verify_outputs(out,events,stations)
        for name,expected in hashes.items():
            if sha(ROOT/name)!=expected or sha(copies[name])!=expected:
                raise ValueError('Source/input changed during reference batch: '+name)
        summary=dict(status='complete' if result['counts']['reference_valid']==verified else 'completed_with_unresolved_references',
            scope='Independent fixed-truth geometry reference for every native source/receiver pair; no observations, simulation or inversion',
            source_count=len(events),receiver_count=len(stations),expected_pairs=37648,verified_pairs=verified,
            input_source_sha256=hashes,profile_x_velocity_km_km_s=levels,original_box_km=box,
            coordinate_permutation='Reference (x,y,z)=original (y,z,x); output source derivatives return to original axes',
            finite_box_basis='Every candidate stays in the finite normal profile domain and has monotone transverse coordinates between its native endpoints',
            native_metadata_mapping='All source_/receiver_ columns in references.csv.gz preserve native strings; complete input tables retained under inputs/',
            command=ledger['command'],workers=args.workers,seconds=time.monotonic()-started,
            limitations=['Catalog-defined simulation geometry is not inferred earthquake ground truth.',
                'Complete enumeration means candidate families suffice for minimum time; equal maxima can admit a continuum of paths.',
                'Time ordering uses ordinary floating point, not interval-certified minimum-time ranking.',
                'Near ties retain all branch certificates and branch-specific derivatives; no unique gradient is asserted.',
                'Unresolved or invalid references retain certificates and blank first-arrival values, without a successful reference flag.',
                'This reference batch does not change or certify the production ray solver or generate noisy observations.'],**result)
        summary['output_sha256']={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file() and p.name!='execution.json'}
        atomic_json(out/'summary.json',summary)
        ledger.update(status='completed',result_status=summary['status'],finished_utc=utc(),seconds=time.monotonic()-started,
            summary_sha256=sha(out/'summary.json'))
        atomic_json(out/'execution.json',ledger)
        print(json.dumps({k:summary[k] for k in ('status','verified_pairs','counts','time_range_s')},indent=2),flush=True)
    except BaseException as error:
        ledger.update(status='interrupted' if isinstance(error,(KeyboardInterrupt,SystemExit)) else 'failed',
            finished_utc=utc(),seconds=time.monotonic()-started,error_type=type(error).__name__,error=str(error))
        atomic_json(out/'execution.json',ledger)
        raise


if __name__=='__main__':main()
