#!/usr/bin/env python3
"""One interval-certified step from the frozen native guide; no solver change."""
import argparse
import csv
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
SUPPORT_SHA='0ed7c9e024366248cbd4f105a10b17dca3e876dfa24605c4ca984faf15622e67'
SQRT_SHA='55f3bd520aa472a3e4d4042808403eaa850c952301ea95d461331af9917ab5f2'


def require(ok,message):
    if not ok:raise ValueError(message)


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    with path.open() as f:return list(csv.DictReader(f))


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,str(path));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def positive_integral(a,b):
    if a>=0 and b>=0:return (a+b)/2
    if a<=0 and b<=0:return Q(0)
    if a>0:return a*a/(2*(a-b))
    return b*b/(2*(b-a))


def display(interval):
    return dict(lower_rational=str(interval[0]),upper_rational=str(interval[1]),
        lower_display=float(interval[0]),upper_display=float(interval[1]))


def action(profile,points,support,sqrt_enclosure):
    """Action only: aligned nonconvex faces remain valid action candidates."""
    total=support.point(0)
    for a,b in zip(points,points[1:]):
        squared=sum((y-x)**2 for x,y in zip(a,b));require(squared>0,'Zero-length trial segment')
        length=sqrt_enclosure(squared,support.SQRT_BITS)[1];dx=b[0]-a[0]
        if dx:
            lo,hi=sorted((a[0],b[0]));cuts=[lo]+[x for x,v in profile if lo<x<hi]+[hi]
            primitive=support.point(0)
            for left,right in zip(cuts,cuts[1:]):
                va,vb=support.speed(profile,left),support.speed(profile,right)
                part=support.point((right-left)/va) if va==vb else support.div(support.logarithm(vb/va)[0],support.point((vb-va)/(right-left)))
                primitive=support.add(primitive,part)
            average=support.div(primitive,support.point(abs(dx)))
        else:average=support.point(1/support.speed(profile,a[0]))
        total=support.add(total,support.rounded(support.mul(length,average)))
    return total


def support_bound(profile,points,support,sqrt_enclosure):
    g=[[support.point(0) for k in range(3)] for p in points];aligned=[]
    for n,(a,b) in enumerate(zip(points,points[1:])):
        r=support.segment(profile,a,b,sqrt_enclosure)
        for k in range(3):
            g[n][k]=support.add(g[n][k],r['ga'][k]);g[n+1][k]=support.add(g[n+1][k],r['gb'][k])
        if r['aligned']:aligned.append(dict(edge=n,**r['aligned']))
    middle=[sum(v)/2 for row in g[1:-1] for v in row]
    radii=[(v[1]-v[0])/2 for row in g[1:-1] for v in row]
    norm=sqrt_enclosure(sum(v*v for v in middle),support.SQRT_BITS)[1]
    error=sqrt_enclosure(sum(v*v for v in radii),support.SQRT_BITS)[1]
    return g,dict(norm_midpoint=display(norm),norm_error=display(error),
        support_norm_upper_rational=str(norm[1]+error[1]),support_norm_upper_display=float(norm[1]+error[1]),
        aligned_edges=aligned,stationarity_labeled=False,source_or_model_derivative_selected=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True);args=parser.parse_args()
    out=(ROOT/args.output).resolve();out.relative_to(ROOT);out.mkdir(parents=True);start=time.monotonic()
    base=ROOT/'data/development/native_interface_support/001'
    native_base=base/'source/data/development/interface_directional/001/inputs'
    support_path=ROOT/'diagnostics/check_native_interface_support.py';sqrt_path=ROOT/'diagnostics/first_arrival_1d_precise_turn_reference.py'
    inputs=[Path(__file__).resolve(),support_path,sqrt_path,ROOT/'src/core.hpp',base/'summary.json',base/'support_vector.csv']+[native_base/n for n in ('truth_grid.csv','native_path.csv','native_case.csv')]
    hashes={str(p.relative_to(ROOT)):sha(p) for p in inputs};frozen=out/'source';frozen.mkdir()
    def copied(p):return frozen/p.relative_to(ROOT)
    for p in inputs:
        target=copied(p);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(str(p),str(target))
        require(sha(target)==hashes[str(p.relative_to(ROOT))],'Source changed during freeze')
    require(sha(copied(support_path))==SUPPORT_SHA and sha(copied(sqrt_path))==SQRT_SHA,'Reviewed arithmetic dependency changed')
    core=copied(ROOT/'src/core.hpp').read_text()
    require('for (int ls = 0; ls < 24; ls++, step *= 0.5)' in core and 'newT <= T + 1e-4 * step * slope' in core,'Existing Armijo constants changed')
    support=module('frozen_native_support',copied(support_path));sqrt_enclosure=module('frozen_exact_sqrt',copied(sqrt_path)).candidate_sqrt_enclosure
    original=json.loads(copied(base/'summary.json').read_text());rows=load(copied(base/'support_vector.csv'))
    require(sha(copied(base/'summary.json'))=='4ab53a668bda8332b16259af18dd667ac3fff88382c6d38bf0ef61c02c43dbd1','Reviewed original support summary changed')
    require(sha(copied(base/'support_vector.csv'))==original['artifact_sha256']['support_vector.csv'],'Reviewed support table changed')
    native=load(copied(native_base/'native_case.csv'));require(len(native)==1,'Native case not unique');native=native[0]
    old_rows=load(copied(native_base/'native_path.csv'));grid=load(copied(native_base/'truth_grid.csv'))
    require(native==original['native_case'] and len(rows)==len(old_rows)==original['path_nodes'],'Native source mapping differs')
    profile=sorted(set((Q(float(r['x'])),Q(float(r['v']))) for r in grid))
    axes=[sorted(set(Q(float(r[k])) for r in grid)) for k in 'xyz']
    require(len(profile)==len(axes[0]) and all(v>0 for x,v in profile),'Model is not positive and x-only')
    ids=['event','station','source_event_resource_id','source_origin_resource_id','receiver_channel_seed_id',
        'receiver_channel_fdsn_source_id','receiver_metadata_epoch_start','receiver_metadata_epoch_end']
    points=[tuple(Q(float(r[k])) for k in 'xyz') for r in rows]
    g=[];middle=[];face_nodes=set()
    for n,(r,old) in enumerate(zip(rows,old_rows)):
        require(all(r[k]==v for k,v in old.items()) and int(r['node'])==n and all(r[k]==native[k] for k in ids),'Native path/support row differs')
        endpoint=n in (0,len(rows)-1);require(int(r['endpoint_fixed'])==endpoint,'Fixed endpoint mapping differs')
        values=[]
        for k in 'xyz':
            lo,hi=r['g'+k+'_lower_rational'],r['g'+k+'_upper_rational']
            if endpoint:require(lo==hi=='','Endpoint derivative should be absent');values.append(support.point(0))
            else:values.append((Q(lo),Q(hi)));require(values[-1][0]<=values[-1][1],'Reversed support interval')
        g.append(values);middle.append(tuple(sum(v)/2 for v in values))
        if int(r['incident_convex_face_x']):face_nodes.add(n)
    require(all(axes[k][0]<p[k]<axes[k][-1] for p in points[1:-1] for k in range(3)),'Original movable knots must be interior')
    for n,prefix in [(0,'source_'),(-1,'receiver_')]:require(all(points[n][k]==Q(float(native[prefix+axis])) for k,axis in enumerate('xyz')),'Native endpoint changed')
    checks=[]
    def check(name,ok):checks.append(dict(name=name,passed=bool(ok)));require(ok,name)
    for a,b,expected in [(Q(1),Q(-1),Q(1,4)),(Q(-1),Q(1),Q(1,4)),(Q(2),Q(4),Q(3)),(Q(-2),Q(-4),Q(0)),(Q(0),Q(2),Q(1)),(Q(-2),Q(0),Q(0))]:
        check('positive_integral_'+str(a)+'_'+str(b),positive_integral(a,b)==expected)
    c=Q(1,5);bad_support_dot=-2*c*c;actual=bad_support_dot+positive_integral(-c,c)+positive_integral(c,-c)
    check('negative_support_dot_is_insufficient',bad_support_dot<0 and actual==Q(1,50)>0)
    old_action=tuple(Q(x) for x in original['total_action_interval_rational'])
    check('action_only_reproduces_original_interval',action(profile,points,support,sqrt_enclosure)==old_action)
    attempts=[];results=[];direction_rows=[];armijo=Q(1,10000)
    attempt_path=out/'attempts.jsonl';attempt_path.touch(exist_ok=False)
    def record_attempt(record):
        attempts.append(record)
        with attempt_path.open('a') as f:f.write(json.dumps(record,allow_nan=False)+'\n')
    for name,tangent in [('negative_support_midpoint',False),('tangent_projection',True)]:
        m=[tuple(Q(0) if tangent and n in face_nodes and k==0 else value for k,value in enumerate(row)) for n,row in enumerate(middle)]
        norm=sqrt_enclosure(sum(v*v for row in m for v in row),support.SQRT_BITS)[1]
        require(norm[1]>0,'Zero direction does not establish a new certificate')
        d=[tuple(-v/norm[1] for v in row) for row in m]
        dot=support.point(0)
        for gradient,direction in zip(g,d):
            for component,value in zip(gradient,direction):dot=support.add(dot,support.mul(component,support.point(value)))
        correction=support.point(0)
        for edge in original['aligned_segments']:
            n=edge['edge'];require(points[n][0]==points[n+1][0]==Q(edge['x']),'Aligned edge mapping differs')
            minus,plus,on_face=support.normal_slopes(profile,points[n][0])
            require(minus==0 and plus==Q(1,18) and on_face,'Expected actual zero/one-eighteenth slopes')
            length=sqrt_enclosure(sum((b-a)**2 for a,b in zip(points[n],points[n+1])),support.SQRT_BITS)[1]
            correction=support.add(correction,support.mul(length,support.point((plus-minus)*positive_integral(d[n][0],d[n+1][0]))))
        derivative=support.add(dot,correction)
        if tangent:check('tangent_direction_cusp_correction_exactly_zero',correction==support.point(0))
        for n,row in enumerate(rows):
            saved={k:row[k] for k in ['node','x','y','z']+ids};saved['direction']=name
            for k,axis in enumerate('xyz'):saved['d'+axis+'_rational']=str(d[n][k])
            direction_rows.append(saved)
        result=dict(direction=name,normalization=display(norm),support_dot=display(dot),cusp_correction=display(correction),
            actual_directional_derivative=display(derivative),directional_descent_certified=derivative[1]<0,accepted=False,
            original_local_flag=native['original_converged'],stationarity_labeled=False,source_or_model_derivative_selected=False)
        if derivative[1]>=0:
            result['status']='direction_not_certified_no_trials';results.append(result);continue
        for backtrack in range(24):
            step=Q(1,1<<backtrack);trial=[tuple(x+step*v for x,v in zip(p,direction)) for p,direction in zip(points,d)]
            record=dict({k:native[k] for k in ids},direction=name,backtrack=backtrack,step_rational=str(step),accepted=False)
            require(trial[0]==points[0] and trial[-1]==points[-1],'Fixed endpoint moved')
            if not all(axes[k][0]<=p[k]<=axes[k][-1] for p in trial for k in range(3)):
                record['status']='outside_original_box';record_attempt(record);continue
            if any(a==b for a,b in zip(trial,trial[1:])):
                record['status']='zero_length_trial_segment';record_attempt(record);continue
            try:value=action(profile,trial,support,sqrt_enclosure)
            except (ArithmeticError,ValueError) as error:
                record.update(status='action_interval_unresolved',error=str(error));record_attempt(record)
                result.update(status='action_interval_unresolved',error=str(error));break
            rhs=old_action[0]+armijo*step*derivative[0]
            accepted=value[1]<=rhs;record.update(status='accepted' if accepted else 'armijo_not_certified',
                action=display(value),action_change=display(support.sub(value,old_action)),armijo_rhs_lower_rational=str(rhs),accepted=accepted)
            record_attempt(record)
            print(name,'backtrack',backtrack,'accepted',accepted,'change',float(value[1]-old_action[0]),flush=True)
            if not accepted:continue
            check(name+'_strict_action_decrease',value[1]<old_action[0])
            try:
                bound_g,bound=support_bound(profile,trial,support,sqrt_enclosure);bound['status']='computed_for_new_polygon'
            except (ArithmeticError,ValueError) as error:
                bound_g=None;bound=dict(status='support_bound_unresolved_for_new_polygon',error=str(error),stationarity_labeled=False)
            saved_rows=[]
            for n,(p,row) in enumerate(zip(trial,rows)):
                saved={k:row[k] for k in ['node']+ids};saved['coordinate_basis']='exact rational diagnostic polygon; decimal xyz are approximate displays'
                saved['endpoint_fixed']=int(n in (0,len(rows)-1));saved['original_local_flag']=native['original_converged']
                for k,axis in enumerate('xyz'):
                    saved[axis]=format(float(p[k]),'.17g');saved[axis+'_rational']=str(p[k])
                    saved['g'+axis+'_lower_rational']='' if saved['endpoint_fixed'] or bound_g is None else str(bound_g[n][k][0])
                    saved['g'+axis+'_upper_rational']='' if saved['endpoint_fixed'] or bound_g is None else str(bound_g[n][k][1])
                saved_rows.append(saved)
            filename=name+'_path.csv'
            with (out/filename).open('x',newline='') as f:
                writer=csv.DictWriter(f,fieldnames=list(saved_rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(saved_rows)
            result.update(status='one_step_accepted',accepted=True,backtrack=backtrack,step_rational=str(step),
                new_action=display(value),new_support_bound=bound,new_polygon_file=filename)
            break
        if not result['accepted'] and 'status' not in result:result['status']='halving_budget_exhausted_without_accepted_step'
        results.append(result)
    with (out/'directions.csv').open('x',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(direction_rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(direction_rows)
    for name,h in hashes.items():require(sha(ROOT/name)==h and sha(frozen/name)==h,'Pinned file changed during diagnostic')
    summary=dict(status='completed_one_step_diagnostic',checks=checks,native_case=native,input_source_sha256=hashes,
        original_action=display(old_action),results=results,armijo_coefficient_rational=str(armijo),halving_budget=24,
        elapsed_seconds=time.monotonic()-start,original_local_flag=native['original_converged'],production_or_convergence_flags_changed=False,
        limitations=['Two independent single steps from the same original polygon; no outer optimization or QP.',
            'Full convex-cusp correction is included before any step; a negative supporting dot alone never enables trials.',
            'The tangent projection is a feasible search direction, not an all-direction certificate.',
            'Exact rational coordinates define each new polygon; decimal xyz fields are approximate displays.',
            'New support bounds apply only to their saved diagnostic polygons and retained-node variations.',
            'No source/model derivative, inserted-knot, continuous stationary-curve or global first-arrival claim.',
            'Exact rational interval endpoints are authoritative; decimal interval displays may round inward.'])
    summary['artifact_sha256']={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()}
    with (out/'summary.json').open('x') as f:json.dump(summary,f,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps(dict(status=summary['status'],checks=len(checks),results=[{k:r[k] for k in ('direction','status','accepted')} for r in results])))


if __name__=='__main__':
    try:main()
    except Exception as error:
        if '--output' in sys.argv:
            failed=(ROOT/sys.argv[sys.argv.index('--output')+1]).resolve()
            if failed.is_dir() and ROOT in failed.parents and not (failed/'summary.json').exists():
                path=failed/'failure.json'
                if not path.exists():
                    with path.open('x') as f:json.dump(dict(status='failed_component_preserved',error_type=type(error).__name__,error=str(error)),f,indent=2);f.write('\n')
        raise
