#!/usr/bin/env python3
"""Isolate near-critical direct-root arithmetic; do not edit the reference module."""
import argparse
import csv
from decimal import Decimal as D, localcontext
from fractions import Fraction as Q
import gzip
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import shutil
import sys

import numpy as np
from scipy.optimize import brentq

ROOT=Path(__file__).resolve().parents[1]


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def decimal(q):
    return D(q.numerator)/D(q.denominator)


def high_precision(profile,a,b,distance,base):
    """Independent 80-digit reciprocal-affine integrals and monotone bisection."""
    pieces=[]
    for (x,vx),(y,vy) in zip(profile,profile[1:]):
        lo,hi=max(a,x),min(b,y)
        if hi<=lo:continue
        g=(vy-vx)/(y-x)
        pieces.append(tuple(decimal(q) for q in (hi-lo,vx+g*(lo-x),vx+g*(hi-x),g)))
    target=decimal(Q(distance));vmax=decimal(base)
    def integral(delta,with_time=False):
        u=vmax+delta;xx=D(0);tt=D(0)
        for h,va,vb,g in pieces:
            qa=((u-va)*(u+va)).sqrt();qb=((u-vb)*(u+vb)).sqrt()
            if g:
                xx+=h*(va+vb)/(qa+qb)
                if with_time:tt+=(((u+qa)/va).ln()-((u+qb)/vb).ln())/g
            else:
                xx+=h*va/qa
                if with_time:tt+=h*u/(va*qa)
        return xx,tt
    lo,hi=D(0),vmax
    while integral(hi)[0]>target:hi*=2
    iterations=0
    for iterations in range(400):
        mid=(lo+hi)/2
        if mid==lo or mid==hi:break
        if integral(mid)[0]>target:lo=mid
        else:hi=mid
    delta=(lo+hi)/2;xx,tt=integral(delta,True)
    return dict(delta=delta,u=vmax+delta,time=tt,distance_residual=xx-target,
        bracket_width=hi-lo,bisections=iterations+1)


def solve_delta(reference,profile,a,b,distance,base):
    def value(delta):return reference.leg(profile,a,b,base+Q(delta))[0]-distance
    upper=float(base)
    if value(0.)<0:raise ValueError('Requested direct branch is not admissible')
    while value(upper)>0:
        upper*=2
        if not math.isfinite(upper):raise ArithmeticError('Direct offset bracket overflow')
    delta=brentq(value,0.,upper,xtol=float(np.nextafter(0.,1.)),rtol=4*np.finfo(float).eps)
    u=base+Q(delta)  # Never round base + delta before the rational square difference.
    x,t=reference.leg(profile,a,b,u)
    return delta,u,x,t


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True)
    args=parser.parse_args();out=(ROOT/args.output).resolve();out.relative_to(ROOT);out.mkdir(parents=True)
    baseline=ROOT/'data/development/loma_layered_full_001'
    summary=json.loads((baseline/'summary.json').read_text())
    ledger=json.loads((baseline/'execution.json').read_text())
    if ledger['status']!='completed' or ledger['summary_sha256']!=sha(baseline/'summary.json'):
        raise ValueError('Require the preserved terminal full batch')
    for name,expected in summary['output_sha256'].items():
        if sha(baseline/name)!=expected:raise ValueError('Baseline changed: '+name)
    source=out/'source';source.mkdir()
    for path in [Path(__file__).resolve()]+list((baseline/'source').glob('first_arrival*reference.py')):
        shutil.copyfile(str(path),str(source/path.name))
    sys.path.insert(0,str(source))
    spec=importlib.util.spec_from_file_location('frozen_layered',str(source/'first_arrival_layered_reference.py'))
    reference=importlib.util.module_from_spec(spec);spec.loader.exec_module(reference)
    cases=[]
    with gzip.open(str(baseline/'references.csv.gz'),'rt',newline='') as f:
        native={int(row['pair_index']):row for row in csv.DictReader(f) if row['reference_valid']=='0'}
    with gzip.open(str(baseline/'certificates.jsonl.gz'),'rt') as f:
        for line in f:
            item=json.loads(line)
            if item['pair_index'] not in native:continue
            row=native[item['pair_index']]
            if len(item['reference']['candidates'])!=1 or item['reference']['candidates'][0]['kind']!='direct':
                raise ValueError('Conditioning diagnostic expects the preserved sole direct candidate')
            s=[float(row['source_'+a]) for a in 'xyz'];r=[float(row['receiver_'+a]) for a in 'xyz']
            cases.append(dict(name='native_pair_'+str(item['pair_index']),kind='identified failed closure',
                native_metadata=row,profile=summary['profile_x_velocity_km_km_s'],source=s,receiver=r,
                saved_candidate=item['reference']['candidates'][0]))
    if len(cases)!=11:raise ValueError('Preserved failed support changed')
    for epsilon in (1.,1e-2,1e-5,1e-8,1e-12):
        for distance in (5.,50.):
            cases.append(dict(name='invented_epsilon_{}_distance_{}'.format(epsilon,distance),kind='invented near-critical plateau',
                profile=[[-2.,6.],[0.,6.],[1.,4.],[2.,4.]],source=[-epsilon,0.,0.],receiver=[1.,distance,0.]))
    results=[]
    with localcontext() as context:
        context.prec=80
        for case in cases:
            profile=[(Q(float(x)),Q(float(v))) for x,v in case['profile']]
            s,r=case['source'],case['receiver'];a,b=sorted((Q(s[0]),Q(r[0])))
            distance=math.hypot(r[1]-s[1],r[2]-s[2]);base=reference.maximum(profile,a,b)
            delta,u,x,time=solve_delta(reference,profile,a,b,distance,base)
            exact=high_precision(profile,a,b,distance,base)
            nearest=float(decimal(base)/exact['u']);neighbors=[]
            for label,k in [('below',float(np.nextafter(nearest,0.))),('nearest',nearest),('above',float(np.nextafter(nearest,1.)))]:
                if not 0<k<1:
                    neighbors.append(dict(label=label,k=k,admissible_finite_parameter=False));continue
                xx,tt=reference.leg(profile,a,b,base/Q(k))
                neighbors.append(dict(label=label,k=k,admissible_finite_parameter=True,distance_residual_km=xx-distance,time_s=tt))
            rounded_x,rounded_time=reference.leg(profile,a,b,Q(float(u)))
            from_p=Q(1/(1/float(u)));sample_x,sample_time=reference.leg(profile,a,b,from_p)
            vs=reference.velocity(profile,Q(s[0]));sign=(r[0]>s[0])-(r[0]<s[0]);p=1/float(u)
            gradient=[-sign*math.sqrt(float(u*u-vs*vs))/float(u*vs),-p*(r[1]-s[1])/distance,-p*(r[2]-s[2])/distance]
            dv=decimal(vs);eu=exact['u'];ep=1/eu
            exact_gradient=[-D(sign)*((eu-dv)*(eu+dv)).sqrt()/(eu*dv),
                -ep*D.from_float(r[1]-s[1])/D.from_float(distance),-ep*D.from_float(r[2]-s[2])/D.from_float(distance)]
            result=dict(case=case,base_velocity_km_s=float(base),offset_velocity_km_s=delta,
                exact_rational_u=[str(u.numerator),str(u.denominator)],stable_distance_residual_km=x-distance,
                stable_time_s=time,stable_time_minus_80digit_s=float(D.from_float(time)-exact['time']),
                stable_source_derivative_original_axes=gradient,
                stable_source_error_norm_s_per_km=math.sqrt(sum((g-float(e))**2 for g,e in zip(gradient,exact_gradient))),
                high_precision={k:str(v) for k,v in exact.items()},neighboring_binary64_k=neighbors,
                rounded_u_distance_residual_km=rounded_x-distance if math.isfinite(rounded_x) else None,
                reconstructed_u_from_p_distance_residual_km=sample_x-distance if math.isfinite(sample_x) else None,
                unchanged_distance_closure_pass=abs(x-distance)<=1e-8)
            results.append(result)
    report=dict(scope='Isolated direct-root conditioning comparison; maintained reference and failed full batch unchanged',
        cases=results,case_count=len(results),identified_failed_pairs=11,invented_controls=10,decimal_precision=80,
        unchanged_distance_closure_tolerance_km=1e-8,closure_passes=sum(r['unchanged_distance_closure_pass'] for r in results),
        maximum_stable_distance_residual_km=max(abs(r['stable_distance_residual_km']) for r in results),
        maximum_absolute_time_difference_from_80digit_s=max(abs(r['stable_time_minus_80digit_s']) for r in results),
        maximum_source_vector_difference_from_80digit_s_per_km=max(r['stable_source_error_norm_s_per_km'] for r in results),
        baseline_summary_sha256=sha(baseline/'summary.json'),source_sha256={p.name:sha(p) for p in source.iterdir()},
        proposal='Replace only the direct k-root by delta=u-vmax>=0 with u=Q(vmax)+Q(delta), retain all branch/closure gates, and preserve exact rational u for any future path sampling.',
        limitations=['Decimal arithmetic is an independent high-precision check, not outward interval arithmetic.',
            'No direct-root change has been applied to the maintained reference; no production path or input was changed.',
            'Reconstructing u from rounded p or float(u) can lose the resolved near-critical offset.',
            'General candidate enumeration, turning roots and branch selection are outside this isolated change.'])
    (out/'results.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('cases','source_sha256')},indent=2))


if __name__=='__main__':main()
