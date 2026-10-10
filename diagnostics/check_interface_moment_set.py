#!/usr/bin/env python3
"""Exact moment-set controls and saved native residual bounds; no optimizer."""
import argparse
import csv
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]
SQRT_SHA='55f3bd520aa472a3e4d4042808403eaa850c952301ea95d461331af9917ab5f2'


def require(ok,message):
    if not ok:raise ValueError(message)


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def feasible(c,a,b):return c>=0 and (a==b==0 if c==0 else (a+b)**2<=2*c*a and (a+b)**2<=2*c*b)


def realize(c,a,b):
    require(feasible(c,a,b),'Infeasible endpoint moments')
    mass=a+b
    if mass==0:return []
    if mass==c:return [(Q(0),Q(1),c)]
    t=mass/c;lo=mass*mass/(2*c);hi=mass-lo;theta=(b-lo)/(hi-lo)
    return [(Q(0),t,c*(1-theta)),(1-t,Q(1),c*theta)]


def moments(pieces):
    a=b=Q(0)
    for lo,hi,value in pieces:
        b+=value*(hi*hi-lo*lo)/2;a+=value*(hi-lo-(hi*hi-lo*lo)/2)
    return a,b


def bounded_density(pieces,c):
    cuts=sorted(set([Q(0),Q(1)]+[u for lo,hi,v in pieces for u in (lo,hi)]))
    if not all(0<=lo<=hi<=1 and v>=0 for lo,hi,v in pieces):return False
    return all(0<=sum(v for lo,hi,v in pieces if lo<(left+right)/2<hi)<=c for left,right in zip(cuts,cuts[1:]))


def optimum_density(c,a,b):
    if a>=0 and b>=0:return [(Q(0),Q(1),c)]
    if a<=0 and b<=0:return []
    zero=-a/(b-a)
    return [(zero,Q(1),c)] if b>a else [(Q(0),zero,c)]


def positive_integral(a,b):
    if a>=0 and b>=0:return (a+b)/2
    if a<=0 and b<=0:return Q(0)
    return a*a/(2*(a-b)) if a>0 else b*b/(2*(b-a))


def read(path):
    with path.open() as f:return list(csv.DictReader(f))


def iv(value):return tuple(Q(value[k]) for k in ('lower_rational','upper_rational'))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True);args=parser.parse_args()
    out=(ROOT/args.output).resolve();out.relative_to(ROOT);out.mkdir(parents=True);frozen=out/'source';frozen.mkdir()
    old=ROOT/'data/development/native_interface_support/001';step=ROOT/'data/development/native_interface_step/001'
    sqrt_path=ROOT/'diagnostics/first_arrival_1d_precise_turn_reference.py';proof=ROOT/'data/development/interface_moment_set/proof.md'
    inputs=[Path(__file__).resolve(),proof,sqrt_path,old/'summary.json',old/'support_vector.csv',step/'summary.json',step/'attempts.jsonl']+[step/(name+'_path.csv') for name in ('negative_support_midpoint','tangent_projection')]
    hashes={str(p.relative_to(ROOT)):sha(p) for p in inputs}
    def copied(p):return frozen/p.relative_to(ROOT)
    for p in inputs:
        target=copied(p);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(str(p),str(target));require(sha(target)==hashes[str(p.relative_to(ROOT))],'Changed frozen input')
    require(sha(copied(sqrt_path))==SQRT_SHA,'Reviewed square-root enclosure source changed')
    spec=importlib.util.spec_from_file_location('frozen_sqrt',str(copied(sqrt_path)));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    def sqrt_bounds(value):
        result=m.candidate_sqrt_enclosure(value,128)[1];require(0<=result[0] and result[0]**2<=value<=result[1]**2,'Invalid square-root enclosure');return result
    checks=[]
    def check(name,ok):checks.append(dict(name=name,passed=bool(ok)));require(ok,name)
    check('zero_jump_unique_zero_moments',feasible(Q(0),Q(0),Q(0)) and realize(Q(0),Q(0),Q(0))==[])
    for a,b in [(Q(1),Q(0)),(Q(0),Q(1)),(Q(-1),Q(1))]:check('zero_jump_rejects_'+str(a)+'_'+str(b),not feasible(Q(0),a,b))
    check('reversed_jump_ineligible',not feasible(Q(-1),Q(0),Q(0)))
    directions=[(a,b) for a in (Q(-2),Q(-1,3),Q(0),Q(1,2),Q(3)) for b in (Q(-2),Q(-1,3),Q(0),Q(1,2),Q(3))]
    for c in (Q(0),Q(1,3),Q(2)):
        for a,b in directions:
            pieces=optimum_density(c,a,b);a_m,b_m=moments(pieces)
            check('exact_support_{}_{}_{}'.format(c,a,b),bounded_density(pieces,c) and feasible(c,a_m,b_m) and a*a_m+b*b_m==c*positive_integral(a,b))
    examples=[]
    for c in (Q(1,3),Q(2)):
        for t in (Q(0),Q(1,4),Q(1,2),Q(3,4),Q(1)):
            mass=c*t;lo=mass*mass/(2*c);hi=mass-lo
            for theta in (Q(0),Q(1,3),Q(1)):
                b=lo+theta*(hi-lo);a=mass-b;pieces=realize(c,a,b)
                label='{}_{}_{}'.format(c,t,theta)
                check('realizability_'+label,feasible(c,a,b) and moments(pieces)==(a,b) and bounded_density(pieces,c))
                check('all_direction_support_'+label,all(x*a+y*b<=c*positive_integral(x,y) for x,y in directions))
                examples.append(dict(c=str(c),a=str(a),b=str(b),pieces=[[str(x) for x in row] for row in pieces]))
            if 0<t<1:
                epsilon=c/Q(1024)
                check('below_exact_moment_boundary_{}_{}'.format(c,t),not feasible(c,mass-(lo-epsilon),lo-epsilon))
                check('above_exact_moment_boundary_{}_{}'.format(c,t),not feasible(c,mass-(hi+epsilon),hi+epsilon))
    original=json.loads(copied(old/'summary.json').read_text());steps=json.loads(copied(step/'summary.json').read_text())
    require(sha(copied(old/'summary.json'))=='4ab53a668bda8332b16259af18dd667ac3fff88382c6d38bf0ef61c02c43dbd1' and sha(copied(step/'summary.json'))=='167bfd760019f461bdfcf373ce699575739bcc0704874c3ffde94044eedc23eb','Reviewed native evidence changed')
    native=original['native_case'];require(native==steps['native_case'],'Native cases differ')
    ids=['event','station','source_event_resource_id','source_origin_resource_id','receiver_channel_seed_id','receiver_channel_fdsn_source_id','receiver_metadata_epoch_start','receiver_metadata_epoch_end']
    cases=[('original',old/'support_vector.csv',original['aligned_segments'],Q(original['supporting_vector_norm_upper_rational']))]
    for result in steps['results']:
        bound=result['new_support_bound'];cases.append((result['direction'],step/result['new_polygon_file'],bound['aligned_edges'],Q(bound['support_norm_upper_rational'])))
    bounds=[]
    for name,path,aligned,incumbent in cases:
        rows=read(copied(path));face_nodes=set(n for edge in aligned if Q(edge['plus'])>Q(edge['minus']) for n in (edge['edge'],edge['edge']+1))
        squared_mid=squared_error=Q(0);fixed_components=0
        for n,row in enumerate(rows):
            require(int(row['node'])==n and all(row[k]==native[k] for k in ids),'Native row changed')
            if int(row['endpoint_fixed']):continue
            for axis,k in enumerate('xyz'):
                if axis==0 and n in face_nodes:continue
                lo,hi=Q(row['g'+k+'_lower_rational']),Q(row['g'+k+'_upper_rational']);require(lo<=hi,'Reversed native interval')
                squared_mid+=((lo+hi)/2)**2;squared_error+=((hi-lo)/2)**2;fixed_components+=1
        length=sqrt_bounds(squared_mid);error=sqrt_bounds(squared_error);lower=max(Q(0),length[0]-error[1]);upper=length[1]+error[1]
        check('native_fixed_projection_bound_'+name,0<lower<=upper<=incumbent)
        record=dict({k:native[k] for k in ids},polygon=name,polygon_sha256=sha(copied(path)),movable_knots=len(rows)-2,
            fixed_components=fixed_components,guide_incident_knots=len(face_nodes),original_local_flag=native['original_converged'],
            fixed_projection_norm_lower_rational=str(lower),fixed_projection_norm_upper_rational=str(upper),
            fixed_projection_norm_lower_display=float(lower),fixed_projection_norm_upper_display=float(upper),
            incumbent_support_norm_upper_rational=str(incumbent),incumbent_support_norm_upper_display=float(incumbent),
            maximum_possible_norm_reduction_upper_rational=str(incumbent-lower),
            maximum_possible_relative_norm_reduction_upper_display=float(1-lower/incumbent),stationarity_labeled=False)
        bounds.append(record)
    tangent=next(r for r in steps['results'] if r['direction']=='tangent_projection');derivative=iv(tangent['actual_directional_derivative']);old_action=iv(steps['original_action'])
    curvature=[]
    for line in copied(step/'attempts.jsonl').read_text().splitlines():
        row=json.loads(line)
        if row['direction']!='tangent_projection':continue
        require(all(row[k]==native[k] for k in ids),'Trial native identity changed')
        h=Q(row['step_rational']);value=iv(row['action'])
        lo=(value[0]-old_action[1]-h*derivative[1])/(h*h);hi=(value[1]-old_action[0]-h*derivative[0])/(h*h)
        require(lo<=hi,'Reversed curvature interval')
        curvature.append(dict({k:native[k] for k in ids},backtrack=row['backtrack'],step_rational=str(h),accepted=row['accepted'],
            secant_coefficient_lower_rational=str(lo),secant_coefficient_upper_rational=str(hi),
            secant_coefficient_lower_display=float(lo),secant_coefficient_upper_display=float(hi)))
    check('all_twenty_saved_tangent_trials_retained',len(curvature)==20)
    for name,rows in [('native_fixed_projection.csv',bounds),('native_tangent_curvature.csv',curvature)]:
        with (out/name).open('x',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(rows)
    for name,digest in hashes.items():require(sha(ROOT/name)==sha(frozen/name)==digest,'Input/source changed during component')
    result=dict(status='completed_exact_moment_controls',checks=checks,realizability_examples=examples,native_case=native,
        input_source_sha256=hashes,native_fixed_projection_bounds=bounds,last_three_tangent_secants=curvature[-3:],
        limitations=['Exact moment-set/support equivalence applies only to constant nonnegative jump coefficient c.','No dual norm minimization, QP, outer optimization, production or convergence-flag change.','Native projection lower bounds concern supporting-vector norms for each saved polygon, not a global or inserted-knot certificate.','The saved directional secants do not identify a Hessian spectrum or establish mesh stiffness as the cause of slow convergence.','No source/model derivative is selected; original native flags remain unchanged.','Rational endpoints are authoritative; float displays are approximate.'])
    result['artifact_sha256']={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()}
    with (out/'summary.json').open('x') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps(dict(status=result['status'],checks=len(checks),native_relative_reduction_bounds=[b['maximum_possible_relative_norm_reduction_upper_display'] for b in bounds])))


if __name__=='__main__':main()
