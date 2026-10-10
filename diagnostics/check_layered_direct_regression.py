#!/usr/bin/env python3
"""Verify maintained delta-root integration against the frozen 80-digit control."""
import argparse
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True)
    args=parser.parse_args();out=(ROOT/args.output).resolve();out.relative_to(ROOT);out.mkdir(parents=True)
    source=out/'source';source.mkdir()
    for p in [Path(__file__).resolve(),ROOT/'diagnostics/first_arrival_layered_reference.py',ROOT/'diagnostics/first_arrival_1d_reference.py']:
        shutil.copyfile(str(p),str(source/p.name))
    control=ROOT/'data/development/loma_layered_direct_conditioning_001/results.json'
    shutil.copyfile(str(control),str(out/'conditioning_control.json'))
    prior=json.loads(control.read_text());sys.path.insert(0,str(source))
    spec=importlib.util.spec_from_file_location('layered_delta',str(source/'first_arrival_layered_reference.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    checks=[];cases=[]
    def check(name,value):checks.append(dict(name=name,passed=bool(value)))
    for case in prior['cases']:
        definition=case['case'];profile=definition['profile'];s,r=definition['source'],definition['receiver']
        ref=module.enumerate_arrivals([x for x,v in profile],[v for x,v in profile],
            [s[1],s[2],s[0]],[r[1],r[2],r[0]])
        first=ref['first_arrival'];name=definition['name']
        check(name+'_valid_direct',ref['reference_valid'] and first['kind']=='direct')
        if first:
            check(name+'_matches_80digit_checked_control',first['time_s']==case['stable_time_s'] and
                first['distance_residual_km']==case['stable_distance_residual_km'] and
                [first['source_derivative_s_per_km'][d] for d in (2,0,1)]==case['stable_source_derivative_original_axes'])
            u=Q(*map(int,first['phase_velocity_exact_ratio']))
            a,b=sorted((Q(s[0]),Q(r[0])))
            xx,tt=module.leg([(Q(float(z)),Q(float(v))) for z,v in profile],a,b,u)
            check(name+'_rational_parameter_roundtrip',tt==first['time_s'] and
                xx-math.hypot(r[1]-s[1],r[2]-s[2])==first['distance_residual_km'])
        cases.append(dict(case=definition,reference=ref))
    # Positive finite inputs with a transverse offset too small for finite
    # binary64 u^2 evaluation must be unresolved rather than silently accepted.
    overflow=module.enumerate_arrivals([0.,1.],[5.,6.],[0.,0.,0.],[1e-300,0.,1.])
    check('direct_arithmetic_overflow_fails_closed',not overflow['complete'] and not overflow['reference_valid'] and
        overflow['first_arrival'] is None and any(r['reason']=='Direct-root arithmetic unresolved' for r in overflow['unresolved']))
    original_brentq=module.brentq
    def exhausted(*args,**kwargs):raise RuntimeError('Invented brentq iteration exhaustion')
    module.brentq=exhausted
    try:
        exhausted_result=module.enumerate_arrivals([0.,1.],[5.,6.],[0.,0.,0.],[1.,0.,1.])
    finally:
        module.brentq=original_brentq
    check('direct_root_iteration_failure_fails_closed',not exhausted_result['complete'] and
        exhausted_result['first_arrival'] is None and any(r.get('exception')=='Invented brentq iteration exhaustion'
            for r in exhausted_result['unresolved']))
    result=dict(scope='Maintained direct-root integration against frozen identified/invented arithmetic controls; no solver runs',
        checks=checks,passed=all(c['passed'] for c in checks),count=len(checks),cases=cases,overflow_control=overflow,
        iteration_failure_control=exhausted_result,
        control_sha256=sha(control),source_sha256={p.name:sha(p) for p in source.iterdir()},
        command='PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python3 diagnostics/check_layered_direct_regression.py --output '+str(out.relative_to(ROOT)))
    (out/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(checks=len(checks),passed=result['passed'],failures=[c for c in checks if not c['passed']]),indent=2))
    raise SystemExit(0 if result['passed'] else 1)


if __name__=='__main__':main()
