#!/usr/bin/env python3
"""Continuous alpha=0 support-vector bounds for one frozen x-only native path."""
import argparse
import csv
from decimal import Decimal, localcontext
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]
SQRT_SHA='55f3bd520aa472a3e4d4042808403eaa850c952301ea95d461331af9917ab5f2'
LOG_BITS=160
COMPONENT_BITS=128
SQRT_BITS=128


def require(ok,message):
    if not ok:raise ValueError(message)


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def point(x):return (Q(x),Q(x))


def add(a,b):return (a[0]+b[0],a[1]+b[1])


def neg(a):return (-a[1],-a[0])


def sub(a,b):return add(a,neg(b))


def mul(a,b):
    p=[x*y for x in a for y in b];return (min(p),max(p))


def div(a,b):
    require(not b[0]<=0<=b[1],'Interval divisor contains zero')
    return mul(a,(1/b[1],1/b[0]))


def rounded(a,bits=COMPONENT_BITS):
    """Outward absolute dyadic rounding only after exact segment operations."""
    scale=1<<bits
    lower=(a[0]*scale).numerator//(a[0]*scale).denominator
    upper=-((-a[1]*scale).numerator//(-a[1]*scale).denominator)
    result=(Q(lower,scale),Q(upper,scale))
    require(result[0]<=a[0]<=a[1]<=result[1],'Incorrect outward rounding')
    return result


def logarithm(r):
    """Exact rational atanh series and an absolute remainder enclosure."""
    require(r>0,'Nonpositive logarithm argument')
    z=(r-1)/(r+1);square=z*z;power=z;total=Q(0)
    for n in range(10000):
        total+=power/(2*n+1);power*=square
        tail=2*abs(power)/((2*n+3)*(1-square))
        if tail<=Q(1,1<<LOG_BITS):return (2*total-tail,2*total+tail),n+1,tail
    raise ArithmeticError('Logarithm series budget exhausted; bound unresolved')


def speed(profile,x):
    for (a,va),(b,vb) in zip(profile,profile[1:]):
        if a<=x<=b:return va+(vb-va)*(x-a)/(b-a)
    raise ValueError('Point outside finite x profile')


def normal_slopes(profile,x):
    for n,(a,va) in enumerate(profile):
        if x==a:
            require(0<n<len(profile)-1,'Aligned outer x-boundary is outside this native control')
            lo=(va-profile[n-1][1])/(a-profile[n-1][0]);hi=(profile[n+1][1]-va)/(profile[n+1][0]-a)
            return -lo/(va*va),-hi/(va*va),True
    for (a,va),(b,vb) in zip(profile,profile[1:]):
        if a<x<b:
            g=-(vb-va)/(b-a)/speed(profile,x)**2;return g,g,False
    raise ValueError('Aligned point outside finite profile')


def segment(profile,a,b,sqrt_enclosure):
    delta=[y-x for x,y in zip(a,b)];squared=sum(x*x for x in delta)
    require(squared>0,'Zero-length native segment')
    length=sqrt_enclosure(squared,SQRT_BITS)[1]
    require(length[0]>0 and length[0]**2<=squared<=length[1]**2,'Length enclosure failed')
    dx=delta[0];terms=0;tail=Q(0);aligned=None
    if dx:
        lo,hi=sorted((a[0],b[0]));cuts=[lo]+[x for x,v in profile if lo<x<hi]+[hi]
        primitive=point(0)
        for left,right in zip(cuts,cuts[1:]):
            va,vb=speed(profile,left),speed(profile,right)
            if va==vb:part=point((right-left)/va)
            else:
                logarithmic,n,error=logarithm(vb/va);terms=max(terms,n);tail=max(tail,error)
                part=div(logarithmic,point((vb-va)/(right-left)))
            primitive=add(primitive,part)
        if dx<0:primitive=neg(primitive)
        average=div(primitive,point(dx))
        ja=div(sub(average,point(1/speed(profile,a[0]))),point(dx))
        jb=div(sub(point(1/speed(profile,b[0])),average),point(dx))
    else:
        minus,plus,on_face=normal_slopes(profile,a[0])
        require(plus>=minus,'Nonconvex aligned jump cannot use this supporting construction')
        average=point(1/speed(profile,a[0]));ja=jb=point(minus/2)
        aligned=dict(x=str(a[0]),minus=str(minus),plus=str(plus),on_grid_face=on_face,alpha='0')
    factor=div(average,length)
    ga=[mul(point(-d),factor) for d in delta];gb=[neg(v) for v in ga]
    ga[0]=add(ga[0],mul(length,ja));gb[0]=add(gb[0],mul(length,jb))
    return dict(ga=[rounded(v) for v in ga],gb=[rounded(v) for v in gb],action=rounded(mul(length,average)),
        aligned=aligned,max_log_terms=terms,max_log_tail=tail,length=length)


def decimal_value(q):return Decimal(q.numerator)/Decimal(q.denominator)


def decimal_action(profile,a,b):
    """Independent high-precision action for invented derivative controls only."""
    a=list(map(decimal_value,a));b=list(map(decimal_value,b));p=[tuple(map(decimal_value,r)) for r in profile]
    def v(x):
        for (lo,va),(hi,vb) in zip(p,p[1:]):
            if lo<=x<=hi:return va+(vb-va)*(x-lo)/(hi-lo)
        raise ValueError('Outside invented profile')
    length=sum((y-x)**2 for x,y in zip(a,b)).sqrt();dx=b[0]-a[0]
    if not dx:return length/v(a[0])
    lo,hi=sorted((a[0],b[0]));cuts=[lo]+[x for x,s in p if lo<x<hi]+[hi];total=Decimal(0)
    for left,right in zip(cuts,cuts[1:]):
        va,vb=v(left),v(right)
        total+=(right-left)/va if va==vb else (vb/va).ln()*(right-left)/(vb-va)
    return length*total/abs(dx)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True);args=parser.parse_args()
    out=(ROOT/args.output).resolve();out.relative_to(ROOT);out.mkdir(parents=True)
    base=ROOT/'data/development/interface_directional/001'
    inputs=[Path(__file__).resolve(),ROOT/'diagnostics/first_arrival_1d_precise_turn_reference.py',
        base/'inputs/truth_grid.csv',base/'inputs/native_path.csv',base/'inputs/native_case.csv',base/'directions.csv',base/'directional.csv',base/'review/summary.json']
    hashes={str(p.relative_to(ROOT)):sha(p) for p in inputs};snapshot=out/'source';snapshot.mkdir()
    for p in inputs:
        target=snapshot/p.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(str(p),str(target))
        require(sha(target)==hashes[str(p.relative_to(ROOT))],'Changed input during freeze')
    numerical=snapshot/'diagnostics/first_arrival_1d_precise_turn_reference.py';require(sha(numerical)==SQRT_SHA,'Reviewed square-root helper changed')
    spec=importlib.util.spec_from_file_location('frozen_sqrt',str(numerical));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    square_root=module.candidate_sqrt_enclosure
    checks=[]
    def check(name,ok):checks.append(dict(name=name,passed=bool(ok)));require(ok,name)
    with localcontext() as ctx:
        ctx.prec=100
        for ratio in (Q(1),Q(2),Q(1,2),Q(3,2),Q(99,100),Q(1001,1000)):
            interval,n,tail=logarithm(ratio);exact=decimal_value(ratio).ln()
            check('decimal_log_control_'+str(ratio),decimal_value(interval[0])<=exact<=decimal_value(interval[1]))
            inverse=logarithm(1/ratio)[0];check('exact_log_reciprocity_'+str(ratio),interval==neg(inverse))
        profiles=[[(Q(-2),Q(6)),(Q(3),Q(6))],[(Q(-2),Q(4)),(Q(0),Q(5)),(Q(3),Q(8))]]
        a=[Q(-1),Q(1,3),Q(1,2)];b=[Q(2),Q(-1,4),Q(3,2)]
        h=Q(1,10**24)
        for case,profile in enumerate(profiles):
            result=segment(profile,a,b,square_root)
            check('invented_action_enclosure_'+str(case),decimal_value(result['action'][0])<=decimal_action(profile,a,b)<=decimal_value(result['action'][1]))
            for axis in range(3):
                lo=a[:];hi=a[:];lo[axis]-=h;hi[axis]+=h
                derivative=(decimal_action(profile,hi,b)-decimal_action(profile,lo,b))/(2*decimal_value(h))
                check('invented_source_fd_enclosure_{}_{}'.format(case,axis),decimal_value(result['ga'][axis][0])<=derivative<=decimal_value(result['ga'][axis][1]))
    def read(path):
        with path.open() as f:return list(csv.DictReader(f))
    grid=read(base/'inputs/truth_grid.csv');path=read(base/'inputs/native_path.csv');native=read(base/'inputs/native_case.csv')
    require(len(native)==1,'Native case not unique');native=native[0]
    axes=[sorted(set(Q(float(r[k])) for r in grid)) for k in 'xyz'];profile=sorted(set((Q(float(r['x'])),Q(float(r['v']))) for r in grid))
    require(len(profile)==len(axes[0]),'Actual grid is not x-only')
    require(len(grid)==len(axes[0])*len(axes[1])*len(axes[2]) and len(set(tuple(r[k] for k in 'xyz') for r in grid))==len(grid),'Incomplete native Cartesian grid')
    require(all(v>0 for x,v in profile),'Nonpositive native velocity')
    minus,plus,face=normal_slopes(profile,Q(0));check('actual_constant_zero_face_slopes',face and minus==0 and plus==Q(1,18))
    ids=[k for k in path[0] if k.startswith(('source_','receiver_'))]+['event','station']
    require(all(all(r[k]==native[k] for k in ids) for r in path),'Native identities differ')
    points=[tuple(Q(float(r[k])) for k in 'xyz') for r in path]
    require(all(int(r['node'])==n for n,r in enumerate(path)),'Native nodes reordered')
    require(all(axes[k][0]<=p[k]<=axes[k][-1] for p in points for k in range(3)),'Path outside finite box')
    require(all(axes[k][0]<p[k]<axes[k][-1] for p in points[1:-1] for k in range(3)),'This native bound assumes all movable nodes are interior')
    g=[[point(0) for k in range(3)] for p in points];action=point(0);face_nodes=set();aligned=[];max_terms=0;max_tail=Q(0)
    for n in range(1,len(points)):
        r=segment(profile,points[n-1],points[n],square_root)
        for k in range(3):g[n-1][k]=add(g[n-1][k],r['ga'][k]);g[n][k]=add(g[n][k],r['gb'][k])
        action=add(action,r['action']);max_terms=max(max_terms,r['max_log_terms']);max_tail=max(max_tail,r['max_log_tail'])
        if r['aligned']:
            aligned.append(dict(edge=n-1,**r['aligned']))
            if r['aligned']['minus']!=r['aligned']['plus']:face_nodes.update((n-1,n))
    check('native_exact_guide_inventory',len(aligned)==1874 and all(r['x']=='0' for r in aligned))
    directions=[r for r in read(base/'directions.csv') if r['case']=='native_row5_retained_h0.03125' and r['direction']=='in_plane_negative_gradient']
    require(len(directions)==len(path),'Saved tangent direction incomplete')
    d=[]
    for n,r in enumerate(directions):
        require(int(r['node'])==n and all(r[k]==path[n][k] for k in ids) and all(Q(float(r[k]))==points[n][kidx] for kidx,k in enumerate('xyz')),'Saved tangent native join differs')
        d.append(tuple(Q(float(r[k])) for k in ('dx','dy','dz')))
    require(all(v==0 for endpoint in (d[0],d[-1]) for v in endpoint),'Direction moves fixed endpoint')
    require(all(d[n][0]==0 for n in face_nodes),'Saved tangent direction changes aligned-face normal')
    middle=[];radius=[];dot=point(0);tangent_max_lower=Q(0);rows=[]
    for n,(native_row,gradient) in enumerate(zip(path,g)):
        row=dict(native_row);row['endpoint_fixed']=int(n in (0,len(path)-1));row['incident_convex_face_x']=int(n in face_nodes)
        for k,axis in enumerate('xyz'):
            interval=gradient[k];row['g'+axis+'_lower_rational']=str(interval[0]) if not row['endpoint_fixed'] else ''
            row['g'+axis+'_upper_rational']=str(interval[1]) if not row['endpoint_fixed'] else ''
            if not row['endpoint_fixed']:
                mid=sum(interval)/2;rad=(interval[1]-interval[0])/2;middle.append(mid);radius.append(rad)
                dot=add(dot,mul(interval,point(d[n][k])))
                if not(k==0 and n in face_nodes):tangent_max_lower=max(tangent_max_lower,min(map(abs,interval)) if interval[0]*interval[1]>0 else Q(0))
        rows.append(row)
    with (out/'support_vector.csv').open('x',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(rows)
    norm_mid=square_root(sum(v*v for v in middle),SQRT_BITS)[1];norm_error=square_root(sum(v*v for v in radius),SQRT_BITS)[1]
    residual_upper=norm_mid[1]+norm_error[1];infinity_upper=max(abs(v)+r for v,r in zip(middle,radius))
    check('native_continuous_tangent_slope_strictly_negative',dot[1]<0)
    for name,h in hashes.items():require(sha(ROOT/name)==h,'Input changed during diagnostic')
    result=dict(status='completed_bound_computation',checks=checks,native_case=native,input_source_sha256=hashes,
        path_nodes=len(path),exact_aligned_segments=len(aligned),aligned_segments=aligned,alpha='0',normal_slopes_s_per_km2=[str(minus),str(plus)],
        arithmetic=dict(sqrt_relative_bits=SQRT_BITS,log_absolute_tail_bits=LOG_BITS,segment_component_outward_absolute_bits=COMPONENT_BITS,
            max_log_terms=max_terms,max_log_tail_rational=str(max_tail),norm_of_component_enclosure_radii_upper_s_per_km=float(norm_error[1])),
        support_norm_midpoint_interval_rational=list(map(str,norm_mid)),support_norm_error_interval_rational=list(map(str,norm_error)),
        supporting_vector_norm_upper_s_per_km=float(residual_upper),supporting_vector_norm_upper_rational=str(residual_upper),
        supporting_vector_max_component_upper_s_per_km=float(infinity_upper),supporting_vector_max_component_upper_rational=str(infinity_upper),
        unaffected_tangent_max_component_lower_s_per_km=float(tangent_max_lower),
        continuous_saved_tangent_slope_interval_rational=list(map(str,dot)),continuous_saved_tangent_slope_interval_s_per_km=list(map(float,dot)),
        total_action_interval_rational=list(map(str,action)),total_action_interval_s=list(map(float,action)),
        original_local_flag=native['original_converged'],original_updates=native['original_updates'],stationarity_labeled=False,source_derivative_selected=False,
        interpretation='One feasible continuous supporting vector is enclosed. Its upper norm is a sufficient lower bound on all retained-node first variations; a large upper bound is not itself a nonstationarity proof. The independent saved tangent direction has a separately negative continuous interval slope.',
        limitations=['Only this finite, nonzero-segment, x-only saved path and alpha=0 are covered.','No QP, path optimization, source/model derivative selection, global first-arrival claim or production stopping change.','The bound covers existing knot directions, not inserted knots or arbitrary new curves.','Displayed decimal bounds are approximate; exact rational endpoint strings are the authoritative enclosures.','100-digit Decimal action/finite-difference controls are consistency tests; rigorous inclusion comes from the exact series remainder and rational square-root checks.'])
    result['artifact_sha256']={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()}
    with (out/'summary.json').open('x') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps(dict(status=result['status'],checks=len(checks),support_upper=result['supporting_vector_norm_upper_s_per_km'],tangent_lower=result['unaffected_tangent_max_component_lower_s_per_km'],integration_error=result['arithmetic']['norm_of_component_enclosure_radii_upper_s_per_km'],slope=result['continuous_saved_tangent_slope_interval_s_per_km'])))

if __name__=='__main__':main()
