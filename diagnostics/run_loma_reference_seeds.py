#!/usr/bin/env python3
"""Isolate branch seeding, polygon error and seed resampling for four native rays."""
import argparse
import csv
import datetime
import difflib
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def rows(path):
    with path.open() as stream:return list(csv.DictReader(stream))

def write(path, records):
    with path.open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(records[0]),lineterminator='\n')
        writer.writeheader();writer.writerows(records)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--variant',required=True)
    args=parser.parse_args()
    if not re.fullmatch('[A-Za-z0-9_-]+',args.variant):parser.error('Plain variant required')
    os.chdir(str(ROOT))
    out=ROOT/'data/development/loma_geometry_preflight'/('reference_seeds_'+args.variant)
    out.mkdir(parents=True,exist_ok=False)
    build=ROOT/'tmp/loma_reference_seeds'/args.variant;build.mkdir(parents=True,exist_ok=False)
    original=ROOT/'data/development/loma_geometry_preflight/001'
    reference=ROOT/'data/development/loma_geometry_preflight/layered_reference_001'
    manifest=json.loads((original/'summary.json').read_text())
    reference_manifest=json.loads((reference/'summary.json').read_text())
    summary=dict(status='preparing',started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        scope='Four identified exact critical-guide seeds; no production changes, observational queries, truth generation or inversion',
        selected_diagnostic_rows=[5,49,57,88],spacings_km=[.5,.25,.125,.0625,.03125],max_updates=1000,
        commands=[],input_sha256={},source_sha256={},
        limitations=['Supplied first-arrival seeds use known x-only references and are not a general 3D initialization method.',
                    'Reference time ordering is floating point; complete candidate enumeration is distinct from interval-certified time ranking.',
                    'No-resampling copy changes only initialization; every interior node remains free during optimization.',
                    'Fixed-polygon source derivatives are not optimized-travel-time derivatives unless path stationarity and branch differentiability hold.',
                    'Raw sampled-polygon stages have no solver convergence claim; numerical flags remain unchanged elsewhere.'])
    def save():
        temporary=out/'summary.json.new';temporary.write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n');temporary.replace(out/'summary.json')
    def copy(source,target,expected=None):
        actual=sha(source)
        if expected is not None and actual!=expected:raise ValueError('Changed source/input: '+str(source))
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(str(source),str(target))
        if sha(target)!=actual:raise ValueError('Copy mismatch')
        return actual
    def command(name,argv):
        record=dict(stage=name,command=[str(p.relative_to(ROOT)) if isinstance(p,Path) else p for p in argv],status='running')
        summary['commands'].append(record);summary['status']=name;save();start=time.time()
        with (out/(name+'_stdout.log')).open('w') as stdout,(out/(name+'_stderr.log')).open('w') as stderr:
            process=subprocess.Popen(record['command'],stdout=stdout,stderr=stderr,env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1'))
            record['pid']=process.pid;save();code=process.wait()
        record.update(return_code=code,seconds=time.time()-start,status='completed');save()
        if code:raise RuntimeError(name+' exited '+str(code))
    try:
        if manifest['status']!='completed' or reference_manifest['status']!='complete':raise ValueError('Require terminal geometry and reference')
        for name,expected in reference_manifest['output_sha256'].items():
            if sha(reference/name)!=expected:raise ValueError('Reference artifact changed: '+name)
        for name,expected in manifest['source_sha256'].items():
            summary['source_sha256'][name]=copy(original/'source'/name,out/'source'/name,expected)
        for name in ['truth_grid.csv','truth_events.csv','stations.csv','ray_samples.csv']:
            summary['input_sha256'][name]=copy(ROOT/'data/loma_lom_001'/name,out/'inputs'/name,manifest['input_sha256'][name])
        for name in ['summary.json','references.jsonl','comparison.csv']:
            summary['input_sha256']['reference_'+name]=copy(reference/name,out/'inputs'/('reference_'+name))
        for name in ['check_loma_reference_seeds.cpp','run_loma_reference_seeds.py','loma_path_checks.hpp']:
            summary['source_sha256']['diagnostics/'+name]=copy(ROOT/'diagnostics'/name,out/'source/diagnostics'/name)
        copy(reference/'source/first_arrival_1d_reference.py',out/'source/diagnostics/first_arrival_1d_reference.py')
        sampler_file=out/'source/diagnostics/first_arrival_1d_reference.py'
        spec=importlib.util.spec_from_file_location('frozen_sampler',str(sampler_file))
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        core=(out/'source/src/core.hpp').read_text()
        start=core.index('Ray trace(const Grid &g,');stop=core.index('\nstruct Entry {',start)
        unmodified=core[start:stop]
        modified=unmodified.replace('Ray trace(', 'Ray trace_preserve_seed(',1)
        start=modified.index('    int n = std::max(2, int(std::ceil(arc.back() / spacing)));')
        stop=modified.index('\n  } else {',start)
        modified=modified[:start]+'    p = *seed;'+modified[stop:]
        if modified[modified.index('\n  } else {'): ]!=unmodified[unmodified.index('\n  } else {'): ]:
            raise ValueError('Unexpected optimizer or unseeded change')
        (out/'source/diagnostics/preserve_seed_trace.hpp').write_text(modified+'\n')
        (out/'initialization_only.diff').write_text(''.join(difflib.unified_diff(unmodified.splitlines(True),modified.splitlines(True),fromfile='frozen_trace',tofile='diagnostic_preserve_seed_trace')))
        refs={r['diagnostic_row']:r for r in map(json.loads,(out/'inputs/reference_references.jsonl').read_text().splitlines())}
        events,stations,samples=[rows(out/'inputs'/name) for name in ['truth_events.csv','stations.csv','ray_samples.csv']]
        profile=reference_manifest['profile_x_velocity_km_km_s']
        depths=[-p[0] for p in reversed(profile)];speeds=[p[1] for p in reversed(profile)]
        cases,seeds,selected=[],[],[]
        for index in summary['selected_diagnostic_rows']:
            ref=refs[index];sample=samples[index]
            if ref['native_metadata']!=sample or ref['event']!=sample['event'] or ref['station']!=sample['station']:raise ValueError('Native reference join mismatch')
            result=ref['reference'];candidate=result['first_arrival']
            if not result['complete'] or not result['reference_valid'] or len(result['near_ties'])!=1:raise ValueError('Reference incomplete, invalid or tied')
            if candidate['kind']!='critical_maximum_or_plateau' or candidate['turning_depth_km']!=0 or candidate['p_s_per_km']!=1/6:raise ValueError('Unsupported selected branch')
            a=events[int(sample['event'])];b=stations[int(sample['station'])]
            for prefix,native in [('source_',a),('receiver_',b)]:
                if any(sample[prefix+k]!=value for k,value in native.items()):raise ValueError('Native input join mismatch')
            endpoints=[[float(row[k]) for k in 'xyz'] for row in [a,b]]
            transformed=[[p[1],p[2],-p[0]] for p in endpoints]
            if any(p[2]>0 for p in transformed):raise ValueError('Mirror does not orient both guide legs outward')
            oriented=dict(candidate,turning_depth_km=-candidate['turning_depth_km'])
            source=candidate['source_derivative_s_per_km'];source=[source[2],source[0],source[1]]
            selected.append(ref)
            for spacing in summary['spacings_km']:
                points=module.sample_path(depths,speeds,transformed[0],transformed[1],oriented,spacing)
                points=[[-p[2],p[0],p[1]] for p in points]
                if points[0]!=endpoints[0] or points[-1]!=endpoints[1]:raise ValueError('Sampler endpoint mismatch')
                if any(not all(math.isfinite(v) and lo<=v<=hi for v,(lo,hi) in zip(p,reference_manifest['original_box_km'])) for p in points):raise ValueError('Sampler outside finite box')
                case_id='row{}_h{}'.format(index,format(spacing,'.8g'))
                case=dict(case_id=case_id,diagnostic_row=index,spacing_km=spacing,reference_time_s=candidate['time_s'],
                    reference_source_dx=source[0],reference_source_dy=source[1],reference_source_dz=source[2])
                case.update(sample);cases.append(case)
                seeds.extend(dict(case_id=case_id,node=n,x=p[0],y=p[1],z=p[2]) for n,p in enumerate(points))
        write(out/'cases.csv',cases);write(out/'seeds.csv',seeds)
        (out/'selected_references.jsonl').write_text(''.join(json.dumps(r,allow_nan=False)+'\n' for r in selected))
        summary['source_sha256']={str(p.relative_to(out/'source')):sha(p) for p in (out/'source').rglob('*') if p.is_file()}
        summary['coordinate_mapping']='Sampler(y,z,-x), reversed x profile, guide normal0; returned points(-normal,transverse0,transverse1). Reference source derivative permutes(original dx,dy,dz)=(reference dz,dx,dy).'
        save()
        binary=build/'check'
        command('compile',['g++','-std=c++17','-O2','-fopenmp',out/'source/diagnostics/check_loma_reference_seeds.cpp','-lstdc++fs','-o',binary])
        summary['binary_sha256']=sha(binary)
        command('diagnostic',[binary,out/'inputs/truth_grid.csv',out/'cases.csv',out/'seeds.csv',out])
        output_rows=rows(out/'results.csv');checks=rows(out/'checks.csv')
        if len(output_rows)!=len(cases)*5 or any(r['passed']!='1' for r in checks):raise ValueError('Incomplete diagnostic or failed control')
        summary.update(status='completed_with_original_flags_preserved',result_rows=len(output_rows),checks_passed=len(checks),
            optimized_convergence_counts={stage:sum(r['converged']=='1' for r in output_rows if r['stage']==stage) for stage in ['uniform_resampled_optimized','retained_seed_optimized']})
        summary['output_sha256']={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file() and p.name not in ['summary.json','summary.json.new']}
    except BaseException as error:
        summary.update(status='failed',error_type=type(error).__name__,error=str(error));save();raise
    save();print(str(out.relative_to(ROOT)),flush=True)

if __name__=='__main__':main()
