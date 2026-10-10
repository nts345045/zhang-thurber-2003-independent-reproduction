#!/usr/bin/env python3
"""Invented-only controls for one metric direction and one rounded trial.

Requires separately reviewed preparation and a separately compiled binary.
Does not load native geometry or launch a trace, field, or iterative search.
"""
import argparse
from fractions import Fraction as Q
import hashlib
from itertools import product
import json
import math
import os
from pathlib import Path
import signal
import struct
import subprocess
import sys
import time

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def encoded(value):
    if isinstance(value,Q):return str(value)
    if isinstance(value,dict):return {str(k):encoded(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [encoded(v) for v in value]
    return value


def save(path, value):
    with path.open('x') as stream:
        json.dump(encoded(value),stream,sort_keys=True,indent=2,allow_nan=False);stream.write('\n')


def verify(root, pins):
    for name,digest in pins.items():
        path=(root/name).resolve();path.relative_to(root)
        if sha(path)!=digest:raise ValueError('Changed pinned file: '+name)


def fresh_output(root, output):
    out=(root/output).resolve();out.relative_to(root)
    if any((out/n).exists() for n in ('summary.json','results.json','checks.json','cases')):
        raise ValueError('Preserve prior output, including incomplete cases')
    return out


def exact_dense(weights, gradient, fixed):
    """Independent small dense rational elimination, not a Thomas reimplementation."""
    n=len(weights)-1;result=[Q(0)]*(3*n)
    for axis in range(3):
        slots=[i for i in range(n) if not fixed[3*i+axis]]
        matrix=[]
        for i in slots:
            matrix.append([weights[i]+weights[i+1] if i==j else
                           (-weights[max(i,j)] if abs(i-j)==1 else Q(0)) for j in slots]
                          +[-Q(gradient[3*i+axis])])
        for i in range(len(slots)):
            pivot=matrix[i][i]
            if pivot<=0:raise ValueError('Invented positive system lost a pivot')
            matrix[i]=[x/pivot for x in matrix[i]]
            for j in range(len(slots)):
                if j!=i:
                    factor=matrix[j][i]
                    matrix[j]=[a-factor*b for a,b in zip(matrix[j],matrix[i])]
        for i,node in enumerate(slots):result[3*node+axis]=matrix[i][-1]
    return result


def oracle_sqrt(value):
    """Independent absolute dyadic enclosure for the small invented radicals."""
    value=Q(value)
    if value<=0:raise ValueError('Positive invented radical required')
    scale=1<<192;integer=value.numerator*scale*scale//value.denominator
    root=1<<((integer.bit_length()+1)//2)
    while True:
        next_root=(root+integer//root)//2
        if next_root>=root:break
        root=next_root
    if not root*root<=integer<(root+1)*(root+1):raise AssertionError('Integer square-root oracle failed')
    lower=Q(root,scale);upper=lower if lower*lower==value else Q(root+1,scale)
    if not lower*lower<=value<=upper*upper:raise AssertionError('Invented radical enclosure failed')
    return lower,upper


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',required=True);p.add_argument('--binary',required=True)
    p.add_argument('--binary-sha256',required=True);args=p.parse_args()
    out=fresh_output(ROOT,args.output);binary=(ROOT/args.binary).resolve();binary.relative_to(out)
    prepared=json.loads((out/'prepared.json').read_text())
    review=json.loads((out/'prelaunch_review.json').read_text())
    if review.get('status')!='passed' or review.get('prepared_sha256')!=sha(out/'prepared.json'):
        raise ValueError('Require independent source/preparation approval')
    if sha(binary)!=args.binary_sha256:raise ValueError('Changed reviewed build binary')
    verify(ROOT,prepared['input_sha256']);verify(out,prepared['output_sha256'])
    sys.path.insert(0,str(out/'source'))
    from diagnostics import trilinear_action_bounds as t
    from diagnostics import tangent_metric_step as m
    checks=[];results={};commands=[];active=None;started=time.time();status='failed';error=None
    (out/'cases').mkdir()
    settings=t.options(8,1,128)
    def check(name,ok):
        checks.append(dict(name=name,passed=bool(ok)))
        if not ok:raise AssertionError(name)
    def reject(name,call):
        try:call()
        except (ValueError,OverflowError) as exc:checks.append(dict(name=name,passed=True,reason=str(exc)))
        else:raise AssertionError('Invalid fixture accepted: '+name)
    def call(name,mode,content,success=True):
        nonlocal active
        folder=out/'cases'/name;folder.mkdir()
        inp=folder/'input.txt';inp.write_text(content)
        command=[str(binary),mode,str(inp)];record=dict(name=name,command=command)
        commands.append(record)
        with (folder/'stdout.json').open('x') as stdout,(folder/'stderr.log').open('x') as stderr:
            previous_mask=signal.pthread_sigmask(signal.SIG_BLOCK,{signal.SIGINT,signal.SIGTERM})
            try:
                active=subprocess.Popen(command,stdout=stdout,stderr=stderr,start_new_session=True)
            except BaseException:
                signal.pthread_sigmask(signal.SIG_SETMASK,previous_mask);raise
            try:
                signal.pthread_sigmask(signal.SIG_SETMASK,previous_mask)
                record['pid']=active.pid;record['return_code']=active.wait()
            finally:
                cleanup_mask=signal.pthread_sigmask(signal.SIG_BLOCK,{signal.SIGINT,signal.SIGTERM})
                try:
                    if active.poll() is None:
                        try:os.killpg(active.pid,signal.SIGTERM)
                        except ProcessLookupError:pass
                        active.wait()
                    record['child_reaped']=True;active=None
                finally:signal.pthread_sigmask(signal.SIG_SETMASK,cleanup_mask)
        check(name+'_return_code',record['return_code']==0 if success else record['return_code']!=0)
        return json.loads((folder/'stdout.json').read_text()) if success else None
    def weights_text(weights,gradient,fixed):
        return '\n'.join([str(len(weights))]+[str(x) for x in weights]+[str(x) for x in gradient]+[str(int(x)) for x in fixed])+'\n'
    def grid(axes,fn):
        axes=tuple(tuple(Q(x) for x in a) for a in axes)
        return t.model(axes,{index:fn(*(axes[k][index[k]] for k in range(3)))
                             for index in product(*(range(len(a)) for a in axes))})
    def interrupted(sig,unused):raise SystemExit(128+sig)
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    try:
        # A dense rational solve distinguishes principal restriction from
        # deleting edges incident on the fixed coordinate.
        weights=list(map(Q,(1,1,2,2,2)));gradient=[0,4,0,0,-7,0,0,123,0,0,4,0]
        fixed=[True,False,True,True,False,True,True,True,True,True,False,True]
        record=call('principal','weights',weights_text(weights,gradient,fixed))
        oracle=exact_dense(weights,gradient,fixed)
        actual=[Q(x) for x in record['direction']]
        check('principal_dense_rational_agreement',actual==oracle)
        check('fixed_slots_exact_zero',all(not flag or value==0 for flag,value in zip(fixed,actual)))
        check('incident_edges_remain_in_principal_diagonal',oracle[1::3]==[-1,2,0,-1])
        check('exact_free_principal_pivots',[record['pivots'][k] for k in (1,4,10)]==[2,2.5,4])
        check('exact_energy_and_slope_not_factor_two',record['quadratic_binary64']==22 and record['slope_binary64']==-22 and
              sum(Q(g)*d for g,d in zip(gradient,oracle))==-22)
        results['principal']=dict(record=record,exact_dense_solution=oracle,
                                  oracle='Free y matrix [[2,-1,0],[-1,3,0],[0,0,4]]; d=(-1,2,-1), Q=22.')

        invalid=[('zero_weight',[0,1],[1,0,0]),('negative_weight',[-1,2],[1,0,0]),
                 ('nonfinite_weight',['nan',1],[1,0,0]),('nonfinite_rhs',[1,1],['inf',0,0]),
                 ('diagonal_overflow',['1e308','1e308'],[1,0,0]),
                 ('cancelled_pivot',['1e-300','1e300','1e-300'],[1,0,0,1,0,0]),
                 ('eliminated_rhs_overflow',[1,1,1],['-1.7e308',0,0,'-1.7e308',0,0]),
                 ('solution_overflow',['1e-308','1e-308'],['1e308',0,0])]
        for name,w,g in invalid:call(name,'weights',weights_text(w,g,[False]*len(g)),False)

        # A homogeneous two-link polygon has known length and gradient. The
        # internal z plane intentionally makes the unavailable normal explicit.
        # Both available components include complete adjacent-edge derivatives.
        g=grid(((-1,2),(-1,1),(-1,0,1)),lambda x,y,z:Q(4))
        path=[(Q(0),)*3,(Q(1,2),Q(1,4),Q(0)),(Q(1),Q(0),Q(0))]
        length=oracle_sqrt(Q(5,16))
        gy=t.div(t.point(Q(1,8)),length)
        components=[None,[(Q(0),Q(0)),gy,None],None]
        old=[dict(action=t.mul(t.point(Q(1,4)),length)) for unused in range(2)]
        experiment=m.single_trial(t,g,path,components,old,settings,
            lambda text:call('homogeneous_bent','solve',text),lambda text:call('homogeneous_trial','round',text))
        results['homogeneous_trial']=dict(start=path,components=components,experiment=experiment)
        zero_values=experiment['metric']['direction'];zero_hex=experiment['metric']['direction_hex']
        check('homogeneous_signed_zero_decimal_hex_roundtrip',
              all(type(zero_values[k]) is float and zero_values[k]==0 and
                  zero_values[k].hex()==float.fromhex(zero_hex[k]).hex() for k in (0,2)) and
              math.copysign(1,zero_values[0])==-1 and math.copysign(1,zero_values[2])==1)
        check('single_direction_single_trial_acceptance',experiment['status']=='diagnostic_trial_accepted' and
              experiment['metric_solves']==experiment['rounded_trials']==1)
        direction=experiment['direction'];slope=experiment['nominal_slope']
        bound=experiment['geometric_bound'];alpha=experiment['alpha']
        trial=experiment['trial'];actual_slope=experiment['actual_displacement_slope'];action=experiment['action']
        check('homogeneous_full_slope_radical_formula',slope==t.mul(gy,t.point(direction[1][1])))
        check('homogeneous_metric_slope_negative',slope[1]<0 and direction[1][0]==direction[1][2]==0)
        check('single_full_step_within_exact_geometric_bound',alpha==1 and bound>1)
        check('rounded_displacement_full_slope_negative',actual_slope[1]<0)
        check('endpoint_and_normal_coordinates_unchanged',trial[0]==path[0] and trial[-1]==path[-1] and trial[1][2]==0)
        start_bounds=action['starting_action'];trial_bounds=action['trial_action']
        check('homogeneous_start_action_exact_squaring',0<start_bounds[0] and start_bounds[0]**2<=Q(5,64)<=start_bounds[1]**2)
        trial_square=(1+4*trial[1][1]**2)/16
        check('homogeneous_rounded_trial_action_exact_squaring',0<trial_bounds[0] and trial_bounds[0]**2<=trial_square<=trial_bounds[1]**2)
        exact_length=oracle_sqrt(Q(1,4)+trial[1][1]**2)
        oracle_delta=((exact_length[0]-length[1])/2,(exact_length[1]-length[0])/2)
        check('homogeneous_full_length_action_oracle',action['paired_difference'][0]<=oracle_delta[0]<=oracle_delta[1]<=action['paired_difference'][1])
        check('homogeneous_conservative_armijo',action['conservative_nominal_armijo'] and action['strict_decrease'])
        check('armijo_rhs_exact_saved_arithmetic',action['nominal_armijo_rhs_lower']==Q(float('1e-4'))*Q(alpha)*slope[0])
        check('changed_action_budget_two_edges',action['action_edge_evaluations']==2)
        results['homogeneous_trial'].update(oracle_delta=oracle_delta,
            ideal_radical_oracle=dict(start_action='sqrt(5)/8',gradient_y='1/(2*sqrt(5))',weight='1/sqrt(5)',
                direction_y='-1/4',metric_energy='1/(8*sqrt(5))',full_step_action='1/4',
                full_step_difference='(2-sqrt(5))/8',
                interpretation='Ideal exact solve; actual binary64 direction and rounded trial are tested separately.'))

        flat_grid=grid(((-2,2),(-2,2),(-2,2)),lambda x,y,z:Q(1))
        flat=[(Q(-1),Q(0),Q(0)),(Q(0),)*3,(Q(1),Q(0),Q(0))]
        zeros=[None,[(Q(0),Q(0))]*3,None]
        def no_round(unused):raise AssertionError('A stationary fixture must not generate a trial')
        stationary=m.single_trial(t,flat_grid,flat,zeros,[dict(action=(Q(1),Q(1)))]*2,settings,
                                  lambda text:call('stationary','solve',text),no_round)
        results['stationary']=stationary
        zero_values=stationary['metric']['direction'];zero_hex=stationary['metric']['direction_hex']
        check('stationary_signed_zero_decimal_hex_roundtrip',
              all(type(v) is float and v==0 and v.hex()==float.fromhex(h).hex()
                  for v,h in zip(zero_values,zero_hex)) and any(math.copysign(1,v)==-1 for v in zero_values))
        check('stationary_no_descent_or_trial',stationary['status']=='nominal_slope_unresolved' and
              stationary['nominal_slope']==(0,0) and stationary['rounded_trials']==stationary['action_edge_evaluations']==0)
        wide=[None,[(Q(0),Q(0)),(Q(-1),Q(2)),None],None]
        uncertain=m.contraction(wide,direction)
        check('unresolved_interval_not_declared_descent',uncertain[0]<0<uncertain[1])
        reject('unavailable_normal_must_be_exact_zero',lambda:m.contraction(components,[(0,0,0),(0,0,1),(0,0,0)]))
        reject('no_reversed_derivative_intervals',lambda:m.contraction([None,[(1,0),(0,0),(0,0)],None],[(0,0,0)]*3))
        def trial_record(points):
            values=[float(x) for p in points for x in p]
            return dict(trial=values,trial_hex=[x.hex() for x in values])
        wrong_endpoint=[(Q(1,4),Q(0),Q(0)),path[1],path[2]]
        reject('trial_fixed_endpoint_rejected',lambda:m.trial_geometry(t,g,path,direction,components,1,
                                                                      trial_record(wrong_endpoint)))
        reject('trial_unavailable_normal_rejected',lambda:m.trial_geometry(t,g,path,[(0,0,0),(0,0,1),(0,0,0)],components,1,
                                                                          trial_record([path[0],(Q(1,2),Q(1,4),1),path[2]])))
        reject('trial_box_violation_rejected',lambda:m.trial_geometry(t,g,path,[(0,0,0),(0,2,0),(0,0,0)],components,1,
                                                                    trial_record([path[0],(Q(1,2),Q(9,4),0),path[2]])))
        reject('trial_collapsed_edge_rejected',lambda:m.trial_geometry(t,g,path,[(0,0,0),(Q(-1,2),Q(-1,4),0),(0,0,0)],components,1,
                                                                     trial_record([path[0],path[0],path[2]])))
        reject('changed_component_mask_rejected',lambda:m.start_inputs(t,g,path,[None,[(0,0),gy,(0,0)],None]))

        # A real binary64 tie can erase the nominal displacement. Its exact
        # full slope then equals zero even though the nominal bound is negative.
        rounding_grid=grid(((-1,3),(-1,2),(-1,1)),lambda x,y,z:Q(1))
        rounding_path=[(Q(0),)*3,(Q(1),Q(1),Q(0)),(Q(2),Q(0),Q(0))]
        rounding_components=[None,[(Q(0),Q(0)),(Q(1),Q(2)),(Q(0),Q(0))],None]
        tiny=[(Q(0),)*3,(Q(0),-Q(2)**-54,Q(0)),(Q(0),)*3]
        raw=call('rounded_zero_displacement','round',m.trial_input(rounding_path,tiny,1.0))
        q,delta,rounded_slope=m.trial_geometry(t,rounding_grid,rounding_path,tiny,rounding_components,1.0,raw)
        check('nominal_negative_but_rounded_zero_is_not_accepted',m.contraction(rounding_components,tiny)[1]<0 and rounded_slope==(0,0) and q==rounding_path)
        results['rounding']=dict(nominal=tiny,nominal_slope=m.contraction(rounding_components,tiny),trial=q,actual=delta,actual_slope=rounded_slope)
        reject('positive_step_underflow_remains_unresolved',lambda:m.downward_step(Q(2)**-1100))
        bound=Q(1,3);step=m.downward_step(bound)
        next_bits=struct.unpack('>Q',struct.pack('>d',step))[0]+1
        successor=struct.unpack('>d',struct.pack('>Q',next_bits))[0]
        check('downward_step_is_largest_admissible_binary64',Q(step)<=bound<Q(successor))
        reject('active_physical_boundary_not_silently_fixed',lambda:m.start_inputs(t,flat_grid,[(Q(-1),0,0),(Q(2),0,0),(Q(1),0,0)],zeros))
        both=grid(((-1,0,1),(-1,0,1),(-1,1)),lambda x,y,z:Q(1))
        reject('multiple_aligned_faces_explicitly_unsupported',lambda:m.start_inputs(t,both,[(0,0,Q(-1,2)),(0,0,0),(0,0,Q(1,2))],zeros))
        unchanged=m.trial_actions(t,g,path,path,old,settings,1,slope)
        check('unchanged_edges_cancel_without_action_evaluation',unchanged['paired_difference']==(0,0) and unchanged['action_edge_evaluations']==0)
        # Invented identity/hash gates: no authoritative inputs are modified.
        pin=out/'cases'/'invented_pin.txt';pin.write_text('invented\n');digest=sha(pin)
        verify(out,{'cases/invented_pin.txt':digest});pin.write_text('mutated invented fixture\n')
        reject('changed_input_pin_rejected',lambda:verify(out,{'cases/invented_pin.txt':digest}))
        reject('prior_output_refused',lambda:fresh_output(ROOT,args.output))
        verify(ROOT,prepared['input_sha256']);verify(out,prepared['output_sha256'])
        check('all_prepared_source_and_input_pins_unchanged',True)
        status='passed'
    except BaseException as exc:
        error=dict(type=type(exc).__name__,message=str(exc));raise
    finally:
        save(out/'results.json',results);save(out/'checks.json',checks)
        outputs={str(p.relative_to(out)):sha(p) for p in sorted((out/'cases').rglob('*')) if p.is_file()}
        outputs.update({name:sha(out/name) for name in ('results.json','checks.json')})
        save(out/'summary.json',dict(status=status,error=error,checks=len(checks),passed=sum(c['passed'] for c in checks),
            elapsed_seconds=time.time()-started,prepared_sha256=sha(out/'prepared.json'),
            prelaunch_review_sha256=sha(out/'prelaunch_review.json'),source_sha256=prepared['input_sha256'],
            binary_sha256=sha(binary),commands=commands,output_sha256=outputs,
            native_evaluations=0,ray_calls=0,field_calls=0,optimizer_calls=0,
            scope='Invented metric/interval/rounding/action controls only; no native direction or trial.'))


if __name__=='__main__':main()
