#!/usr/bin/env python3
"""Regenerate only the three bundled final-polygon bounds, without optimization."""
import argparse
from fractions import Fraction as Q
import gzip
import importlib.util
import json
import os
from pathlib import Path
import signal
import sys

sys.dont_write_bytecode = True
from summarize import (HERE, encode, final_files, fresh_output, numeric, read,
                       reference_for, require, save, sha, verify_package)

SETTINGS = dict(terms=8, subdivisions=1, bits=128)
SELECTED = ['lom_24104_mesh16_bottom', 'lom_24104_mesh8_inward_10m', 'lom_24104_mesh16_inward_2p5m']


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, str(path))
    result = importlib.util.module_from_spec(spec); spec.loader.exec_module(result)
    return result


def packed(path, value):
    data = (json.dumps(encode(value), sort_keys=True, indent=2, allow_nan=False)+'\n').encode('utf8')
    with Path(path).open('xb') as stream:
        with gzip.GzipFile(fileobj=stream, mode='wb', mtime=0) as zipped:
            zipped.write(data)


def comparison(assembly, case, reference):
    def subtract(value, target):
        lo, hi = map(Q,value); a,b = Q(target['lower_exact']),Q(target['upper_exact'])
        require(lo<=hi and a<=b, 'Ordered bounds'); return lo-b,hi-a
    time_error = subtract(assembly['action']['final_action'],reference['time_s'])
    partials = assembly['fixed_polygon_endpoint_partials']['source']
    require(len(partials)==3 and all(v is not None for v in partials), 'Complete ordinary fixed-source intervals')
    errors=[]; squared=[Q(0),Q(0)]
    for value,target in zip(partials,reference['source_gradient_s_per_km']):
        a,b=subtract(value,target);errors.append((a,b))
        squared[0]+=Q(0) if a<=0<=b else min(a*a,b*b);squared[1]+=max(a*a,b*b)
    def classify(pair,limit):
        return 'within' if pair[1]<=limit else 'outside' if pair[0]>limit else 'overlapping'
    lower=Q(0) if time_error[0]<=0<=time_error[1] else min(map(abs,time_error))
    return dict(time_error_s=time_error,source_error_xyz_s_per_km=errors,source_error_squared_norm=squared,
        time_limit_s=2.5e-5,time_limit_classification=classify((lower,max(map(abs,time_error))),Q(float('2.5e-5'))),
        source_vector_norm_limit_s_per_km=3e-6,source_limit_classification=classify(squared,Q(float('3e-6'))**2),
        reference_file='references/references.json',reference_sha256=sha(HERE/'references/references.json'),
        reference_record_index=case['reference_record_index'],optimized_ray_source_derivative_certified=False,
        first_arrival_certified=False,endpoint_scope='Fixed-polygon endpoint family only; physical boundary directions are one-sided.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',help='absent directory under repository tmp/')
    args=parser.parse_args()
    if hasattr(sys,'set_int_max_str_digits'): sys.set_int_max_str_digits(20000)
    manifest=verify_package();output=fresh_output(args.output)
    os.environ.update(LC_ALL='C',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
    source=HERE/'interval_source'
    adapter=module(source/'audit_adapter.py','portable_final_adapter')
    helper=module(source/'aligned_face_support.py','portable_full_support')
    norms=module(source/'physical_box_norm.py','portable_physical_box')
    cases=read(HERE/'cases.json')['cases'];loaded=[]
    require(len(cases)==6,'Complete six-case disposition roster')
    for case in cases:
        grid,start,initial,model_sha=numeric(case);final,summary,pins=final_files(case)
        normalized=adapter.normalize(summary,initial,final,grid['axes'],model_sha,case,{},SETTINGS)
        require(normalized['start']==start,'Exact generated initial geometry')
        reference=reference_for(case,grid,normalized['final'])
        loaded.append((case,grid,normalized,reference))
    selected=[case['case_id'] for case,grid,n,ref in loaded if n['decision']['selected']]
    require(selected==SELECTED,'Only the frozen three final geometries')
    require(sum(len(n['final'])-1 for c,g,n,r in loaded if n['decision']['selected'])==9949,
            'Exact final-only 9949-edge budget')
    require(all(not n['aligned_edges'] and not n['ordered_patches'] and not n['theta_exact']
                for c,g,n,r in loaded if n['decision']['selected']), 'No aligned moments or fit')
    output.mkdir();(output/'tmp').mkdir();os.environ['TMPDIR']=str(output/'tmp')
    for case,grid,n,ref in loaded:
        if n['decision']['selected']:
            save(output/(case['case_id']+'.json.gz.identifiers.json'),dict(identity=case,settings=SETTINGS,
                geometry_sha256=sha(HERE/'final'/(case['case_id']+'_final.csv')),scope='Frozen final geometry only.'))
    sys.path.insert(0,str(source/'source'))
    from diagnostics import trilinear_action_bounds as primitive
    for name in ('trilinear_action_bounds','check_native_interface_support','first_arrival_1d_precise_turn_reference'):
        require(Path(sys.modules['diagnostics.'+name].__file__).resolve()==source/'source/diagnostics'/(name+'.py'),
                'Bundled unchanged interval module')
    attempted=completed=0;reports=[];active=None;destination=None
    record=dict(status='running',settings=SETTINGS,native_cases=cases,selected_case_ids=selected,
        package_manifest_sha256=manifest,starting_action_edges=0,normal_patches=0,
        optimizer_calls=0,reference_solves=0,coefficient_fits=0,
        scope='Three frozen final polygons only. Starting action/net decrease not assessed; no optimized-source or first-arrival certification.')
    def interrupted(sig,unused): raise SystemExit(128+sig)
    previous={sig:signal.signal(sig,interrupted) for sig in (signal.SIGINT,signal.SIGTERM)}
    try:
        for case,grid,n,reference in loaded:
            if not n['decision']['selected']:
                reports.append(dict(identity=case,status='unresolved_not_selected',decision=n['decision']));continue
            active=dict(identity=case,normalized=n,settings=SETTINGS,edge_records=[],patch_moment_records=[],
                        starting_bundle=None,status='evaluating_final_polygon',candidate_convergence_status=None)
            destination=output/(case['case_id']+'.json.gz')
            for edge,(a,b) in enumerate(zip(n['final'],n['final'][1:])):
                require(attempted<9949,'Final edge budget');attempted+=1
                value=primitive.edge_tangent_components(grid,a,b,SETTINGS)
                active['edge_records'].append(dict(value,edge=edge,a_exact=a,b_exact=b,model_sha256=n['model_sha256'],settings=SETTINGS))
                completed+=1
                if completed%64==0: print(json.dumps(dict(completed_final_edges=completed)),flush=True)
            assembly=adapter.assemble(n,active['edge_records'],[],helper,norms.projected_norm)
            active.update(assembly=assembly,analytic_comparison=comparison(assembly,case,reference),status='completed_final_polygon_assessment')
            packed(destination,active)
            reports.append(dict(identity=case,status=active['status'],result_file=destination.name,result_sha256=sha(destination),
                full_support_status=assembly['status'],full_support_norm=assembly['full_support']['norm'],
                full_witness_below_strict_scale=assembly['full_witness_below_strict_scale'],
                starting_action=None,paired_net_change=None,final_action=assembly['action']['final_action'],
                analytic_comparison=active['analytic_comparison']))
            active=None;destination=None
        require(attempted==completed==9949 and verify_package()==manifest,'Complete unchanged final-only scope')
        record['status']='completed_bounded_final_only_audit'
    except BaseException as error:
        record.update(status='failed_preserved',error=type(error).__name__+': '+str(error))
        if active is not None and destination is not None and not destination.exists():
            active.update(status='failed_preserved',error=record['error']);packed(destination,active)
        raise
    finally:
        for sig,handler in previous.items(): signal.signal(sig,handler)
        record.update(attempted_final_edges=attempted,completed_final_edges=completed,cases=reports)
        save(output/'summary.json',record)


if __name__=='__main__':
    main()
