#!/usr/bin/env python3
"""Compare all declared Loma geometry samples with the isolated layered reference."""
import argparse
import collections
import csv
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import shutil
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def table(path):
    with path.open() as stream:
        reader = csv.DictReader(stream); names, rows = reader.fieldnames, list(reader)
    if not names or len(set(names)) != len(names) or any(None in r for r in rows):
        raise ValueError('Invalid CSV: ' + str(path.relative_to(ROOT)))
    return names, rows


def write(path, rows):
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader(); writer.writerows(rows)


def stats(values):
    return None if not values else dict(count=len(values), minimum=min(values), maximum=max(values),
        median=statistics.median(values), rms=math.sqrt(sum(v*v for v in values)/len(values)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    out = (ROOT/args.output).resolve(); out.relative_to(ROOT)
    data = ROOT/'data/loma_lom_001'
    terminal = ROOT/'data/development/loma_geometry_preflight/001/summary.json'
    manifest = json.loads(terminal.read_text())
    completed = [c for c in manifest['commands'] if c['name']=='geometrycheck']
    if manifest['status'] != 'completed' or len(completed)!=1 or completed[0]['exit_code']!=0:
        raise ValueError('Require the completed geometry command, without inferring scientific acceptance')
    files = {name:data/name for group in ('input_sha256','outputs_sha256') for name in manifest[group]}
    for group in ('input_sha256','outputs_sha256'):
        for name, expected in manifest[group].items():
            if sha(files[name])!=expected:
                raise ValueError('Frozen input/output changed: '+name)
    sources = [Path(__file__).resolve(), ROOT/'diagnostics/first_arrival_layered_reference.py',
               ROOT/'diagnostics/first_arrival_1d_reference.py']
    hashes = {str(p.relative_to(ROOT)):sha(p) for p in list(files.values())+sources+[terminal]}
    out.mkdir(parents=True); saved=out/'inputs'; saved.mkdir(); snapshot=out/'source'; snapshot.mkdir()
    for name,p in files.items():
        shutil.copyfile(str(p),str(saved/name))
        if sha(saved/name)!=hashes[str(p.relative_to(ROOT))]:raise ValueError('Changed while copying: '+name)
    shutil.copyfile(str(terminal),str(saved/'terminal_geometry_summary.json'))
    for p in sources:shutil.copyfile(str(p),str(snapshot/p.name))
    sys.path.insert(0,str(snapshot))
    spec=importlib.util.spec_from_file_location('layered',str(snapshot/'first_arrival_layered_reference.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    _,events=table(saved/'truth_events.csv');_,stations=table(saved/'stations.csv')
    _,grid=table(saved/'truth_grid.csv');_,samples=table(saved/'ray_samples.csv')
    _,convergence=table(saved/'geometry_truth_ray_convergence.csv')
    _,identifiers=table(saved/'geometry_truth_ray_identifiers.csv')
    _,derivatives=table(saved/'geometry_truth_ray_derivatives.csv')
    if (len(events),len(stations),len(samples),len(convergence),len(identifiers))!=(724,52,104,104,104):
        raise ValueError('Full prepared geometry or declared diagnostic support changed')
    if any(r['id']!=str(n) for rows in (events,stations) for n,r in enumerate(rows)):
        raise ValueError('Nonconsecutive native geometry indices')
    levels=sorted(set((float(r['x']),float(r['v'])) for r in grid))
    if len(levels)!=len(set(x for x,v in levels)) or any(not math.isfinite(x) or not math.isfinite(v) or v<=0 for x,v in levels):
        raise ValueError('Expected finite positive x-only velocity model')
    normal,speeds=map(list,zip(*levels))
    box=[[min(float(r[k]) for r in grid),max(float(r[k]) for r in grid)] for k in 'xyz']
    permuted_box=[box[1],box[2],box[0]]
    records, references=[],[]
    counts=collections.Counter()
    for index,(sample,ray,identity) in enumerate(zip(samples,convergence,identifiers)):
        if ray['diagnostic_row']!=str(index) or identity['diagnostic_row']!=str(index):
            raise ValueError('Incomplete or unordered diagnostic rows')
        if any(row[key]!=sample[key] for row in (ray,identity) for key in ('event','station')):
            raise ValueError('Changed native sample pair')
        source,receiver=events[int(sample['event'])],stations[int(sample['station'])]
        for prefix,native in (('source_',source),('receiver_',receiver)):
            if any(sample[prefix+k]!=v for k,v in native.items()):
                raise ValueError('Geometry sample metadata differs from native table')
        for key,value in identity.items():
            if key in ('diagnostic_row','event','station'):continue
            expected=sample[key]
            if key in ('source_x','source_y','source_z','receiver_x','receiver_y','receiver_z'):
                if float(value)!=float(format(float(expected),'.12g')):
                    raise ValueError('Saved diagnostic coordinate changed')
            elif value!=expected:
                raise ValueError('Saved diagnostic metadata changed: '+key)
        for key,value in ray.items():
            if not key.endswith('_message') and not math.isfinite(float(value)):
                raise ValueError('Nonfinite saved diagnostic value: '+key)
        s=[float(source[k]) for k in 'xyz'];r=[float(receiver[k]) for k in 'xyz']
        if any(not box[d][0]<=p[d]<=box[d][1] for p in (s,r) for d in range(3)):
            raise ValueError('Native endpoint outside original finite box')
        try:
            reference=module.enumerate_arrivals(normal,speeds,[s[1],s[2],s[0]],
                [r[1],r[2],r[0]],bounds=permuted_box)
            json.dumps(reference,allow_nan=False)
        except (ArithmeticError,ValueError) as error:
            reference=dict(complete=False,reference_valid=False,candidates=[],first_arrival=None,
                           unresolved=[dict(reason='Reference arithmetic exception',exception=str(error))])
        references.append(dict(diagnostic_row=index,event=sample['event'],station=sample['station'],
                               native_metadata=sample,reference=reference))
        first=reference.get('first_arrival')
        item=dict(ray)
        item.update({'saved_'+k:v for k,v in identity.items()})
        item.update({'geometry_'+k:v for k,v in sample.items()})
        item.update(reference_complete=int(reference['complete']),reference_valid=int(reference['reference_valid']),
            reference_candidate_count=len(reference['candidates']),reference_near_tie_count=len(reference.get('near_ties',[])),
            reference_time_s=first['time_s'] if first else '',reference_branch=first['kind'] if first else '',
            reference_turning_x_km=first['turning_depth_km'] if first and first['turning_depth_km'] is not None else '')
        gradient=first.get('source_derivative_s_per_km') if first else None
        for d,k in enumerate('xyz'):
            item['reference_source_d'+k]=gradient[(2,0,1)[d]] if gradient is not None else ''
        for mode in ('production','refined'):
            item[mode+'_minus_reference_s']=float(ray[mode+'_time'])-first['time_s'] if first else ''
            counts[mode+'_saved_converged']+=int(ray[mode+'_converged'])
        counts['reference_complete']+=reference['complete'];counts['reference_valid']+=reference['reference_valid']
        counts['near_ties']+=len(reference.get('near_ties',[]))>1
        if first:counts['branch_'+first['kind']]+=1
        records.append(item)
        if (index+1)%10==0:print('Compared {}/104 identified Loma geometry rays'.format(index+1),flush=True)
    write(out/'comparison.csv',records)
    with (out/'references.jsonl').open('w') as stream:
        for r in references:stream.write(json.dumps(r,allow_nan=False)+'\n')
    derivative_records=[]
    seen=set()
    for row in derivatives:
        q,d=int(row['diagnostic_row']),int(row['axis'])
        if not 0<=q<104 or not 0<=d<3 or (q,d) in seen:
            raise ValueError('Invalid or repeated derivative diagnostic')
        seen.add((q,d));native=records[q]
        if any(row[k]!=native[k] for k in ('event','station')):
            raise ValueError('Derivative pair differs from native sample')
        item=dict(row);item.update({'saved_'+k:v for k,v in identifiers[q].items()})
        exact=native['reference_source_d'+'xyz'[d]];item['reference_derivative']=exact
        for mode in ('production','refined'):
            value=float(row[mode+'_derivative'])
            if not math.isfinite(value):raise ValueError('Nonfinite saved source derivative')
            item[mode+'_minus_reference_s_per_km']=value-exact if exact!='' else ''
        derivative_records.append(item)
    if seen!={(q,d) for q in range(8) for d in range(3)}:
        raise ValueError('Saved derivative support changed')
    write(out/'derivative_comparison.csv',derivative_records)
    for name,expected in hashes.items():
        if sha(ROOT/name)!=expected:raise ValueError('Source/input changed during reference comparison: '+name)
    summary=dict(status='complete' if counts['reference_valid']==104 else 'unresolved_cases_preserved',
        command='PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python3 diagnostics/compare_loma_layered_reference.py --output '+str(out.relative_to(ROOT)),
        scope='All104 declared identified geometry samples; no truth generation, inversion, gate change or production solver substitution',
        reference_counts=dict(counts),profile_x_velocity_km_km_s=levels,original_box_km=box,
        coordinate_permutation='Reference (x,y,z) = original (y,z,x); derivatives are mapped back in comparison tables',
        input_source_sha256=hashes,
        comparison={mode:stats([r[mode+'_minus_reference_s'] for r in records if r[mode+'_minus_reference_s']!=''])
                    for mode in ('production','refined')},
        derivative_comparison={mode:stats([r[mode+'_minus_reference_s_per_km'] for r in derivative_records
                                          if r[mode+'_minus_reference_s_per_km']!='']) for mode in ('production','refined')},
        original_metadata_preserved=True,all104_rows_preserved=True,saved_derivative_components=len(derivative_records),
        limitations=['Candidate families suffice for minimum time only when enumeration is complete; equal maxima can admit a continuum of paths.',
                     'Time ordering is floating point, not an interval minimum-time certificate.',
                     'Tied first arrivals retain branch derivatives and may not have one ordinary source gradient.',
                     'Only24 source derivative components are saved by the original geometry diagnostic; none are invented for other rays.',
                     'Saved production/refined numbers retain their12-significant-digit serialization and original local flags.',
                     'The reported native source coordinates are catalog-defined simulation geometry, not inferred ground truth.'])
    summary['output_sha256']={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()}
    (out/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:summary[k] for k in ('status','reference_counts','comparison','derivative_comparison')},indent=2))


if __name__=='__main__':main()
