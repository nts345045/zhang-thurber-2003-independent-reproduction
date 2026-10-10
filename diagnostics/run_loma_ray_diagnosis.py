#!/usr/bin/env python3
"""Observe one identified failed Loma ray without changing the live diagnostic."""
import argparse
import csv
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import shutil
import subprocess
import time
from types import SimpleNamespace

if not __debug__:
    raise RuntimeError('Integrity checks require Python without optimization')
ROOT=Path(__file__).resolve().parents[1]
os.chdir(str(ROOT))
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--variant',required=True)
args=parser.parse_args()
if not re.fullmatch(r'[A-Za-z0-9_-]+',args.variant):parser.error('Invalid variant')
origin=Path('data/development/loma_geometry_preflight/001')
inputs=Path('data/loma_lom_001')
out=Path('data/development/loma_geometry_preflight')/('row005_'+args.variant)
out.mkdir(parents=True,exist_ok=False)
build=Path('tmp/loma_ray_diagnosis')/args.variant
build.mkdir(parents=True,exist_ok=False)
summary={'status':'preparing','scope':'One identified diagnostic ray; no new observational retrieval, cohort changes, simulation, or inversion',
         'diagnostic_row':5,'event':473,'native_receiver':2,'commands':[],'source_sha256':{},'input_sha256':{},
         'budgets':[1000,4000],'field_and_path_spacing_pairs_km':[[.5,.5],[.25,.25]],
         'OMP_NUM_THREADS':4,'address_space_limit_bytes':128*1024**3}

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):
    with p.open(newline='') as f:return list(csv.DictReader(f))
def save():
    temporary=out/'summary.json.new'
    temporary.write_text(json.dumps(summary,indent=2)+'\n');temporary.replace(out/'summary.json')
def limit():resource.setrlimit(resource.RLIMIT_AS,(128*1024**3,128*1024**3))
def command(name,argv):
    record={'name':name,'argv':list(map(str,argv)),'status':'running'}
    summary['commands'].append(record);summary['status']=name;save();print(name,flush=True)
    start=time.time()
    with (out/(name+'_stdout.log')).open('w') as stdout,(out/(name+'_stderr.log')).open('w') as stderr:
        code=subprocess.call(record['argv'],stdout=stdout,stderr=stderr,preexec_fn=limit,
                             env=dict(os.environ,TMPDIR=str(ROOT/'tmp'),OMP_NUM_THREADS='4'))
    record.update(status='completed',exit_code=code,seconds=time.time()-start);save()
    if code:raise RuntimeError(name+' failed with exit '+str(code))

try:
    live=json.loads((origin/'summary.json').read_text());commit=live['commit'];summary['commit']=commit
    for name,expected in live['input_sha256'].items():assert sha(inputs/name)==expected,name
    for name,expected in live['source_sha256'].items():
        source=origin/'source'/name;assert sha(source)==expected,name
        target=out/'source'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(str(source),str(target))
    selected=read(inputs/'ray_samples.csv')[5]
    assert (int(selected['event']),int(selected['station']))==(473,2)
    events,stations=read(inputs/'truth_events.csv'),read(inputs/'stations.csv')
    for prefix,row in [('source_',events[473]),('receiver_',stations[2])]:
        assert all(selected[prefix+k]==v for k,v in row.items())
    selected=dict(selected,diagnostic_row='5',source_z_km=events[473]['z'],receiver_z_km=stations[2]['z'])
    for prefix,row in [('source_',events[473]),('receiver_',stations[2])]:
        assert all(float(selected[prefix+axis+'_km'])==float(row[axis]) for axis in 'xyz')
    with (out/'identified_ray.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(selected),lineterminator='\n');writer.writeheader();writer.writerow(selected)
    shutil.copyfile(str(inputs/'truth_grid.csv'),str(out/'truth_grid.csv'))
    summary['input_sha256']={str(inputs/name):expected for name,expected in live['input_sha256'].items()}
    summary['identified_ray_sha256']=sha(out/'identified_ray.csv')
    for name in ['diagnostics/check_ray_stopping.cpp','diagnostics/run_ray_stopping.py','diagnostics/first_arrival_fmm.hpp']:
        target=out/'source'/name;target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(subprocess.check_output(['git','show',commit+':'+name]))
    for name in ['diagnostics/loma_path_checks.hpp','diagnostics/run_loma_ray_diagnosis.py']:
        target=out/'source'/name;shutil.copyfile(name,str(target))
    # Reuse exactly the retained observation-only hook generator, without its
    # hardcoded Hayward launcher or any direction/stopping changes.
    recipe=(out/'source/diagnostics/run_ray_stopping.py').read_text()
    first,last=recipe.index('def instrument(source):'),recipe.index('\nobserved_trace = ')
    context={'args':SimpleNamespace(production_hybrid=True,cone_hybrid=False,cone_metric=False,reduced_metric=False),
             'pure_metric':False}
    exec(recipe[first:last],context)
    core=(out/'source/src/core.hpp').read_text()
    first=core.index('Ray trace(const Grid &g,');last=core.index('\nstruct Entry {',first)
    original=core[first:last];observed=context['instrument'](original)
    (out/'source/diagnostics/observed_optimizer.hpp').write_text(observed)
    (out/'instrumentation.diff').write_text(''.join(difflib.unified_diff(original.splitlines(True),observed.splitlines(True),fromfile='trace.cpp',tofile='observed_trace.cpp')))
    original_driver=(out/'source/diagnostics/check_ray_stopping.cpp').read_text()
    driver=original_driver.replace('observation_index','diagnostic_row').replace('dd_source_','source_')
    def replace(old,new):
        global driver
        if driver.count(old)!=1:raise ValueError('Driver insertion changed: '+old)
        driver=driver.replace(old,new,1)
    replace('if(argc!=6)', 'if(argc!=7)')
    replace('OUT BUDGETS SPACINGS','OUT BUDGETS SPACINGS AUX_SPACING')
    replace('first_arrival::Field field(g,b,.5,2,true);','first_arrival::Field field(g,b,std::stod(argv[6]),2,true);')
    replace('Vec values(const std::string &text) {','#include "loma_path_checks.hpp"\n\nVec values(const std::string &text) {')
    replace('  first_arrival::Field field(g,b,std::stod(argv[6]),2,true);',
            '  std::ofstream integration(out+"/integration_checks.csv");\n'
            '  integration<<std::setprecision(21);\n'
            '  integration<<"run_id,diagnostic_row,node,axis,step_km,analytic_gradient,node_x,nearest_velocity_kink_x,node_distance_to_kink_km,previous_node_x,next_node_x,strict_segment_kink_crossings,exact_interface_aligned_segments,near_interface_aligned_segments_1e_minus8_km,quadrature_time_s,exact_x_time_s,quadrature_action_error_s,quadrature_forward,quadrature_backward,quadrature_central,exact_forward,exact_backward,exact_central\\n";\n'
            '  first_arrival::Field field(g,b,std::stod(argv[6]),2,true);')
    replace('    std::cout<<audit_run', '    loma_path_checks(integration,g,ray,gradient,audit_run,audit_observation);\n    std::cout<<audit_run')
    (out/'source/diagnostics/check_ray_stopping.cpp').write_text(driver)
    (out/'driver_adaptation.diff').write_text(''.join(difflib.unified_diff(original_driver.splitlines(True),driver.splitlines(True),fromfile='check_ray_stopping.cpp',tofile='loma_check_ray_stopping.cpp')))
    summary['source_sha256']={str(p.relative_to(out/'source')):sha(p) for p in (out/'source').rglob('*') if p.is_file()}
    binary=build/'check'
    command('compile',['g++','-std=c++17','-O2','-fopenmp','-DAUDIT_PRODUCTION_HYBRID','-DAUDIT_CONE_METRIC',
                       out/'source/diagnostics/check_ray_stopping.cpp','-lstdc++fs','-o',binary])
    summary['binary_sha256']=sha(binary)
    all_results=[]
    for label,spacing in [('spacing050',.5),('spacing025',.25)]:
        target=out/label;target.mkdir()
        command(label,[binary,out/'truth_grid.csv',out/'identified_ray.csv',target,'1000,4000',str(spacing),str(spacing)])
        result=read(target/'results.csv');assert len(result)==4
        assert all(r['logged_matches_unobserved_variant']=='1' for r in result)
        for row in result:row['field_spacing_km']=spacing
        all_results.extend(result)
    partial=json.loads((origin/'partial_findings.json').read_text())
    baseline=partial['rows_with_full_native_identity'][5]['diagnostic']
    matched=[]
    for spacing,prefix in [(.5,'production'),(.25,'refined')]:
        candidates=[r for r in all_results if r['field_spacing_km']==spacing and int(r['max_updates'])==1000]
        direct=next(r for r in candidates if r['initialization']=='straight')
        fmm=next(r for r in candidates if r['initialization']=='fmm')
        selected=fmm if float(fmm['time_s'])<float(direct['time_s']) else direct
        for actual,expected in [('time_s','time'),('projected_gradient','gradient')]:
            assert float(format(float(selected[actual]),'.12g'))==float(baseline[prefix+'_'+expected])
        matched.append({'spacing_km':spacing,'selected_initializer':selected['initialization'],'matches_live_1000_iteration_diagnostic':True})
    for name,expected in live['input_sha256'].items():assert sha(inputs/name)==expected,name
    summary.update(status='completed_with_original_flags_preserved',results=all_results,baseline_matches=matched,
                   limitations=['No global branch enumeration or first-arrival certificate.',
                                'Increasing the diagnostic iteration budget changes neither live settings nor stopping rules.',
                                'Exact and near interface alignment are reported separately; near alignment alone is not exact nonsmoothness.',
                                'Paths, histories and component rows join to identified_ray.csv through diagnostic_row=5; no observational pick identity is invented.'])
    summary['output_sha256']={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file() and p!=out/'summary.json'}
except BaseException as error:
    summary.update(status='failed',failure=str(error));save();raise
save();print(str(out/'summary.json'),flush=True)
