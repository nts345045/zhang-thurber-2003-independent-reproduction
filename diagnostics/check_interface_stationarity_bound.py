#!/usr/bin/env python3
"""Exact two-endpoint convex-interface controls; no optimizer or production edit."""
import argparse
import csv
from fractions import Fraction as Q
import hashlib
import itertools
import json
import math
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(ok,message):
    if not ok:raise ValueError(message)


def positive_integral(a,b):
    """Exact integral from0 to1 of max((1-u)*a+u*b,0)."""
    if min(a,b)>=0:return (a+b)/2
    if max(a,b)<=0:return Q(0)
    if a>0:return a*a/(2*(a-b))
    return b*b/(2*(b-a))


def direct_integral(a,b,minus,plus):
    """Independent split polynomial antiderivative, including its exact zero."""
    cuts=[Q(0),Q(1)]
    if a!=b:
        zero=-a/(b-a)
        if 0<zero<1:cuts.append(zero)
    cuts.sort();total=Q(0)
    for lo,hi in zip(cuts,cuts[1:]):
        slope=plus if a+(b-a)*(lo+hi)/2>=0 else minus
        total+=slope*(a*(hi-lo)+(b-a)*(hi*hi-lo*lo)/2)
    return total


def variation(d,minus,plus,smooth=(Q(0),Q(0))):
    a,b=d
    return smooth[0]*a+smooth[1]*b+minus*(a+b)/2+(plus-minus)*positive_integral(a,b)


def support(minus,plus,partitions,smooth=(Q(0),Q(0))):
    require(plus>=minus,'Nonconvex interface jump is ineligible')
    gradient=list(smooth);previous=Q(0)
    for lo,hi,alpha in partitions:
        require(lo==previous and lo<hi<=1 and 0<=alpha<=1,'Invalid supporting partition/coefficient')
        slope=minus+alpha*(plus-minus)
        gradient[0]+=slope*((hi-lo)-(hi*hi-lo*lo)/2)
        gradient[1]+=slope*(hi*hi-lo*lo)/2;previous=hi
    require(previous==1,'Supporting partition is incomplete')
    return tuple(gradient)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True);args=parser.parse_args()
    out=(ROOT/args.output).resolve();out.relative_to(ROOT);out.mkdir(parents=True)
    inputs=[Path(__file__).resolve(),ROOT/'data/development/interface_directional/stationarity_proposal.md',
        ROOT/'diagnostics/interface_directional.hpp',ROOT/'diagnostics/check_interface_directional.cpp',
        ROOT/'data/development/interface_directional/001/directional.csv',
        ROOT/'data/development/interface_directional/001/directions.csv',
        ROOT/'data/development/interface_directional/001/review/summary.json']
    hashes={str(p.relative_to(ROOT)):sha(p) for p in inputs}
    snapshot=out/'source';snapshot.mkdir()
    for p in inputs:
        target=snapshot/p.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(str(p),str(target))
        require(sha(target)==hashes[str(p.relative_to(ROOT))],'Changed input during freeze')
    checks=[]
    def check(name,ok,**detail):
        checks.append(dict(name=name,passed=bool(ok),**detail));require(ok,name)
    values=list(map(Q,[-2,-1,0,1,2]));directions=list(itertools.product(values,repeat=2))
    # Includes a symmetric minimum, a one-sided plateau, and convex jumps
    # whose two slopes share a sign: convexity, not slope sign, is required.
    jumps=[(Q(-1),Q(1)),(Q(0),Q(1)),(Q(1),Q(3)),(Q(-3),Q(-1))]
    integral_cases=0;bound_cases=0;normal_cone_cases=0
    for minus,plus in jumps:
        for d in directions:
            check('exact_split_integral_'+str(integral_cases),variation(d,minus,plus)==direct_integral(*d,minus,plus));integral_cases+=1
        for alpha in (Q(0),Q(1,4),Q(1)):
            g=support(minus,plus,[(Q(0),Q(1),alpha)],(Q(1,3),Q(-1,5)))
            for d in directions:
                actual=variation(d,minus,plus,(Q(1,3),Q(-1,5)));linear=sum(x*y for x,y in zip(g,d))
                radius=max(map(abs,g));lower=-radius*sum(map(abs,d))
                check('arbitrary_feasible_support_'+str(bound_cases),actual>=linear>=lower);bound_cases+=1
    A=Q(1);c=Q(3,8);smooth=(c,-c)
    probes=[variation(d,-A,A,smooth) for d in [(Q(1),Q(0)),(Q(-1),Q(0)),(Q(0),Q(1)),(Q(0),Q(-1))]]
    check('all_single_coordinate_sign_probes_positive',min(probes)==Q(1,8))
    coupled=variation((Q(-1),Q(1)),-A,A,smooth)
    check('coupled_direction_is_descent_despite_coordinate_probes',coupled==Q(-1,4))
    c=Q(1,5);smooth=(c,-c)
    constant=support(-A,A,[(Q(0),Q(1),Q(1,2))],smooth)
    check('constant_support_best_is_nonzero',constant==(c,-c))
    # ||(c+t,-c+t)||²=2c²+2t² proves t=0 is the global constant-support optimum.
    check('constant_support_exact_minimum_squared_norm',sum(v*v for v in constant)==2*c*c)
    direction=tuple(-v for v in constant);slope=variation(direction,-A,A,smooth)
    check('negative_best_restricted_support_is_ascent',slope==A*c/2-2*c*c==Q(1,50))
    halves=[(Q(0),Q(1,2),(1-4*c/A)/2),(Q(1,2),Q(1),(1+4*c/A)/2)]
    certificate=support(-A,A,halves,smooth)
    check('two_half_support_exact_zero_certificate',certificate==(0,0))
    for n,d in enumerate(directions):check('stationary_function_nonnegative_'+str(n),variation(d,-A,A,smooth)>=0)
    # A valid nonoptimal coefficient also gives a valid (weaker) bound.
    bad_but_feasible=support(-A,A,[(Q(0),Q(1),Q(1))],smooth)
    check('nonoptimal_support_bound_does_not_require_qp_success',bad_but_feasible!=(0,0) and all(
        variation(d,-A,A,smooth)>=sum(g*x for g,x in zip(bad_but_feasible,d)) for d in directions))
    try:support(A,-A,[(Q(0),Q(1),Q(1,2))])
    except ValueError:rejected=True
    else:rejected=False
    check('reversed_cusp_ineligible',rejected)
    check('zero_clarke_choice_not_stationary_certificate',variation((Q(1),Q(1)),A,-A)==-A)
    g=support(Q(0),Q(2),[(Q(0),Q(1),Q(0))],(Q(3),Q(-2)));normal=(Q(-3),Q(2))
    check('domain_polar_cancels_gradient',tuple(a+b for a,b in zip(g,normal))==(0,0))
    for d in directions:
        if d[0]>=0 and d[1]<=0:
            check('domain_polar_bound_'+str(normal_cone_cases),sum(n*x for n,x in zip(normal,d))<=0 and variation(d,0,2,(Q(3),Q(-2)))>=0)
            normal_cone_cases+=1
    # Read the already frozen native evidence; no action/gradient is recomputed.
    prefix=ROOT/'data/development/interface_directional/001'
    with (prefix/'directional.csv').open() as f:
        rows=[r for r in csv.DictReader(f) if r['case']=='native_row5_retained_h0.03125' and r['direction']=='in_plane_negative_gradient']
    require(len(rows)==1,'Native aggregate not unique');native=rows[0]
    with (prefix/'directions.csv').open() as f:
        reader=csv.DictReader(f);fields=reader.fieldnames
        nodes=[r for r in reader if r['case']==native['case'] and r['direction']==native['direction']]
    require(len(nodes)==int(native['path_nodes']),'Native direction support incomplete')
    keys=[k for k in fields if k.startswith(('source_','receiver_'))]+['event','station']
    require(all(all(r[k]==native[k] for k in keys) for r in nodes),'Native identity mismatch')
    with (out/'native_direction.csv').open('x',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');writer.writeheader();writer.writerows(nodes)
    d=[float(r[k]) for r in nodes for k in ('dx','dy','dz')];norm=math.sqrt(math.fsum(x*x for x in d))
    dot=float(native['chosen_gradient_dot_direction']);scale=-dot/(norm*norm)
    native_result=dict(identity={k:native[k] for k in keys},path_nodes=len(nodes),saved_original_local_flag=native['original_converged'],
        tangent_gradient_norm_s_per_km=-dot/norm,tangent_gradient_max_abs_component_s_per_km=scale*max(map(abs,d)),
        saved_directional_slope_s_per_km=native['directional_32point'],saved_direction_norm=norm,
        basis='The saved source hook zeros interface-normal gradient coordinates before normalizing the negative direction. Reconstruction uses only that saved direction and dot product.',
        classification='Retained numerical evidence of nonstationarity; supporting normal slopes cannot cancel the untouched smooth/tangent residual.')
    prior=json.loads((prefix/'review/summary.json').read_text());confirmed=[r for r in prior['high_precision_controls'] if r['direction']==native['direction']]
    require(len(confirmed)==1 and confirmed[0]['confirmed_numerical_descent'],'Native prior descent evidence missing')
    native_result['existing_high_precision_descent']=confirmed[0]
    check('native_original_failure_retained',native['original_converged']=='0')
    check('native_smooth_tangent_residual_exceeds_existing_strict_gradient_limit',native_result['tangent_gradient_max_abs_component_s_per_km']>1e-7)
    check('native_existing_directional_descent_retained',float(native['directional_32point'])<0 and float(confirmed[0]['exact_action_change_100digits_s'])<0)
    result=dict(status='passed',scope=__doc__,checks=len(checks),failed=0,results=checks,
        exact_rational_control_counts=dict(split_integrals=integral_cases,arbitrary_feasible_support_bounds=bound_cases,domain_polar_directions=normal_cone_cases),
        coupled_control=dict(A=str(A),c='3/8',smallest_coordinate_slope='1/8',coupled_slope=str(coupled)),
        conservative_control=dict(A=str(A),c='1/5',constant_support=list(map(str,constant)),negative_support_slope=str(slope),two_half_support=list(map(str,certificate))),
        native_evidence=native_result,input_source_sha256=hashes,
        command='PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/check_interface_stationarity_bound.py --output '+str(out.relative_to(ROOT)),
        limitations=['The exact component controls cover constant face coefficients and retained-node directions, not inserted knots or a global first arrival.',
            'The native residual is reconstructed from saved floating-point outputs; no new continuous stationarity or rigorous interval certificate is asserted.',
            'No auxiliary optimizer is used. Any feasible support gives its bound; auxiliary optimality affects only tightness.',
            'Internal stationarity does not alone validate source or model derivatives.',
            'No production source, stopping flag, threshold, or native path is modified.'])
    for name,h in hashes.items():require(sha(ROOT/name)==h,'Input/source changed during controls')
    result['artifact_sha256']={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()}
    with (out/'summary.json').open('x') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps(dict(status='passed',checks=len(checks),failed=0,native_tangent_max=native_result['tangent_gradient_max_abs_component_s_per_km'])))

if __name__=='__main__':main()
