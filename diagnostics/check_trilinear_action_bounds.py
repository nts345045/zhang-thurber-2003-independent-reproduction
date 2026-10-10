#!/usr/bin/env python3
"""Six invented families for fixed-polygon trilinear action and variation bounds."""
import argparse
from fractions import Fraction as Q
import hashlib
from itertools import product
import json
from pathlib import Path
import signal
import sys
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def encoded(value):
    if isinstance(value,Q): return str(value)
    if isinstance(value,dict): return {str(k):encoded(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)): return [encoded(v) for v in value]
    return value


def save(path, value):
    with path.open('x') as stream:
        json.dump(encoded(value),stream,indent=2,sort_keys=True,allow_nan=False);stream.write('\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True);args=parser.parse_args()
    out=(ROOT/args.output).resolve();out.relative_to(ROOT)
    if any((out/name).exists() for name in ('summary.json','results.json','checks.json')):
        raise ValueError('Preserve prior controls, including incomplete output')
    prepared=json.loads((out/'prepared.json').read_text())
    review=json.loads((out/'prelaunch_review.json').read_text())
    if review.get('status')!='passed' or review.get('prepared_sha256')!=sha(out/'prepared.json'):
        raise ValueError('Require the independent review of this exact preparation')
    for name,digest in prepared['input_sha256'].items():
        if sha(ROOT/name)!=digest: raise ValueError('Changed original source/design: '+name)
    for name,digest in prepared['output_sha256'].items():
        if sha(out/name)!=digest: raise ValueError('Changed frozen source/document: '+name)
    sys.path.insert(0,str(out/'source'))
    from diagnostics import trilinear_action_bounds as t
    from diagnostics.check_native_interface_support import logarithm
    settings=t.options(**prepared['control_settings'])
    checks=[];results={};started=time.time();status='running';error=None
    def check(name,ok):
        checks.append(dict(name=name,passed=bool(ok)))
        if not ok: raise AssertionError(name)
    def rejected(name,call):
        try: call()
        except ValueError as e: checks.append(dict(name=name,passed=True,rejection=str(e)))
        else: raise AssertionError('Accepted invalid fixture: '+name)
    def contains(bounds,expected): return bounds[0]<=expected<=bounds[1]
    def encloses(bounds,oracle): return bounds[0]<=oracle[0]<=oracle[1]<=bounds[1]
    def overlap(a,b): return max(a[0],b[0])<=min(a[1],b[1])
    def grid(axes,fn):
        axes=tuple(tuple(Q(x) for x in a) for a in axes)
        return t.model(axes,{index:fn(*(axes[k][index[k]] for k in range(3)))
                             for index in product(*(range(len(a)) for a in axes))})
    def interrupted(signum,unused): raise SystemExit(128+signum)
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    try:
        # 1. Constant medium: exact rational geometry, irrational length, and the
        # complete two-edge middle-node gradient with fixed endpoints.
        g=grid(((-2,1000),(-2,6),(-1,1)),lambda x,y,z:Q(6))
        a=(0,0,0);b=(3,4,0)
        action=t.edge_action(g,a,b,settings)
        check('constant_3_4_5_action',contains(action['action'],Q(5,6)))
        check('constant_rho_zero_all_pieces',all(p['rho']==0 and p['reciprocal_tail']==0 for p in action['pieces']))
        derivative=t.edge_directional(g,a,b,(0,0,0),(1,0,0),settings)
        reverse=t.edge_directional(g,b,a,(1,0,0),(0,0,0),settings)
        check('constant_geometric_directional',contains(derivative['derivative'],Q(1,10)))
        check('constant_reversed_directional',overlap(derivative['derivative'],reverse['derivative']))
        irrational=t.edge_action(g,a,(1,1,0),settings)
        check('irrational_length_exact_square_bounds',(6*irrational['action'][0])**2<=2<=(6*irrational['action'][1])**2)
        avg,weighted,details=t.reciprocal_integrals((Q(6),),[(Q(-2),),(Q(-1),Q(2))],(Q(6),Q(6)),0)
        check('constant_inverse_square_signed_moments',avg==(Q(1,6),Q(1,6)) and weighted==[(Q(-1,18),Q(-1,18)),(Q(0),Q(0))])
        path=[(-1,0,0),(0,1,0),(1,0,0)]
        witness=t.tangent_witness(g,path,settings)
        check('constant_full_adjacent_edge_witness',witness['status']=='negative_tangent_witness' and witness['node']==1 and witness['axis']==1)
        check('constant_witness_fixed_endpoints',witness['direction'][0]==witness['direction'][-1]==(0,0,0))
        check('constant_witness_positive_feasibility',witness['evaluation']['feasible_step_bound']>0)
        results['constant']=dict(action=action,derivative=derivative,irrational=irrational,witness=witness,exact_signed_moments=weighted)

        # 2. Reciprocal-affine action: a bounded logarithm is an independent
        # primitive; endpoint directions are inward at the finite-box ends.
        affine=[]
        for slope in (1,-1):
            va=Q(5 if slope==1 else 6);vb=va+slope
            g=grid(((0,1),(-1,1),(-1,1)),lambda x,y,z:va+slope*x)
            action=t.edge_action(g,(0,0,0),(1,0,0),settings)
            log=logarithm(vb/va)[0];oracle=t.div(log,t.point(slope))
            check('affine_log_action_'+str(slope),encloses(action['action'],oracle))
            source=t.edge_directional(g,(0,0,0),(1,0,0),(1,0,0),(0,0,0),settings)
            receiver=t.edge_directional(g,(0,0,0),(1,0,0),(0,0,0),(-1,0,0),settings)
            check('affine_source_partial_'+str(slope),contains(source['derivative'],-1/va))
            check('affine_receiver_inward_partial_'+str(slope),contains(receiver['derivative'],-1/vb))
            low=t.edge_directional(g,(0,0,0),(1,0,0),(1,0,0),(0,0,0),t.options(0,1,128))
            check('affine_N0_tail_retains_true_derivative_'+str(slope),contains(low['derivative'],-1/va))
            check('affine_later_bound_narrows_'+str(slope),source['derivative'][1]-source['derivative'][0]<low['derivative'][1]-low['derivative'][0])
            affine.append(dict(slope=slope,action=action,log_oracle=oracle,source=source,receiver=receiver,N0=low))
        results['reciprocal_affine']=affine

        # 3. Genuine cubic restriction with a partial-fraction logarithm oracle.
        function=lambda x,y,z:(2+x)*(3+y)*(4+z)
        g=grid(((0,1),(0,1),(0,1)),function)
        a=(0,0,0);b=(1,1,1)
        action=t.edge_action(g,a,b,settings)
        primitive=t.add(t.sub(t.mul(t.point(Q(1,2)),logarithm(Q(3,2))[0]),logarithm(Q(4,3))[0]),
                        t.mul(t.point(Q(1,2)),logarithm(Q(5,4))[0]))
        oracle=t.mul(t.length_interval((Q(1),Q(1),Q(1)),192),primitive)
        check('cubic_partial_fraction_log_oracle',encloses(action['action'],oracle))
        inward=t.edge_directional(g,a,b,(0,0,0),(-1,-1,-1),settings)
        inward_oracle=t.mul(t.point(Q(-1,60)),t.length_interval((Q(1),Q(1),Q(1)),192))
        check('cubic_inward_endpoint_directional_oracle',encloses(inward['derivative'],inward_oracle))
        v,gradient,unused=t.cell_polynomials(g,(Q(0),)*3,(Q(1),)*3,Q(0),Q(1),(0,0,0))
        check('cubic_polynomial_coefficients',v==tuple(map(Q,(24,26,9,1))))
        check('cubic_spatial_gradient_polynomials',gradient==[tuple(map(Q,(12,7,1))),tuple(map(Q,(8,6,1))),tuple(map(Q,(6,5,1)))])
        crossed=grid(((0,Q(1,2),1),(0,1),(0,1)),function)
        crossed_action=t.edge_action(crossed,a,b,settings)
        crossed_inward=t.edge_directional(crossed,a,b,(0,0,0),(-1,-1,-1),settings)
        split=t.path_action(g,[a,(Q(1,2),)*3,b],settings)
        check('cubic_exact_cell_crossing',any(p['u'][1]==Q(1,2) for p in crossed_action['pieces']))
        check('cubic_crossing_directional_oracle',encloses(crossed_inward['derivative'],inward_oracle))
        check('same_curve_split_unsplit_action',overlap(action['action'],split['action']) and overlap(action['action'],crossed_action['action']))
        narrow=grid(((0,1,2),(-1,1),(-1,1)),lambda x,y,z:5+x)
        left=float.fromhex('0x1.fffffffffffffp-1');right=float.fromhex('0x1.0000000000001p+0')
        tiny=t.edge_action(narrow,(left,0,0),(right,0,0),settings)
        check('nextafter_binary64_values_preserved',t.exact(left)==1-Q(1,2**53) and t.exact(right)==1+Q(1,2**52))
        check('nextafter_plane_cut_not_dropped',any(p['u'][1]==Q(1,3) for p in tiny['pieces']))
        tangent=t.edge_action(narrow,(1,Q(-1,2),0),(1,Q(1,2),0),settings)
        check('tangent_plane_action',contains(tangent['action'],Q(1,6)))
        results['cubic_and_partition']=dict(action=action,oracle=oracle,inward=inward,inward_oracle=inward_oracle,
                                            crossed=crossed_action,crossed_inward=crossed_inward,
                                            split=split,nextafter=tiny,tangent=tangent)

        # 4. Fast ridge and reversed cusp. Ordinary directional signs are kept
        # distinct from a convexified Clarke zero and independent endpoint boxes.
        ridges=[]
        for label,base,slope in [('fast',6,-1),('slow',5,1)]:
            g=grid(((-1,0,1),(-1,1),(-1,1)),lambda x,y,z:Q(base)+slope*abs(x))
            path=[(0,Q(-1,2),0),(0,0,0),(0,Q(1,2),0)]
            jumps=t.face_jumps(g,path[0],path[1]);variations=[]
            for sign in (-1,1):
                d=[(0,0,0),(sign,0,0),(0,0,0)]
                variation=t.path_directional(g,path,d,settings);variations.append(variation)
                exact_derivative=Q(-slope,2*base*base)
                check(label+'_normal_direction_'+str(sign),contains(variation['derivative'],exact_derivative))
            check(label+'_whole_interval_jump_class',all(r['convex_normal_jump']==(label=='fast') for r in jumps))
            crossing=t.edge_directional(g,path[0],path[-1],(1,0,0),(-1,0,0),settings)
            check(label+'_rational_normal_sign_split',any(r['u'][1]==Q(1,2) for r in crossing['pieces']) and
                  {r['cell'][0] for r in crossing['pieces']}=={0,1})
            check(label+'_correlated_sign_change_integral',contains(crossing['derivative'],Q(-slope,2*base*base)))
            ridges.append(dict(label=label,jumps=jumps,variations=variations,crossing=crossing))
        def absolute_linear(a,b):
            return (abs(a)+abs(b))/2 if a*b>=0 else (a*a+b*b)/(2*(abs(a)+abs(b)))
        def coupled(a,b):return -Q(3,8)*a+Q(3,8)*b+absolute_linear(Q(a),Q(b))
        check('coupled_coordinate_probes_positive',all(coupled(a,b)>0 for a,b in [(1,0),(-1,0),(0,1),(0,-1)]))
        check('coupled_combination_descends',coupled(1,-1)==Q(-1,4))
        results['ridge']=dict(cases=ridges,abstract_component_only=dict(coordinate_values=[coupled(a,b) for a,b in [(1,0),(-1,0),(0,1),(0,-1)]],coupled_value=coupled(1,-1)))

        # 5. Variable face coefficients and two adjacent-edge tangent terms.
        def face_velocity(x,y,z):
            shared=(2+y)*(3+z)
            return shared+x*(1+y)/4 if x<=0 else shared-x*(2+z)/4
        g=grid(((-1,0,1),(0,1),(0,1)),face_velocity)
        a=(0,0,0);b=(0,1,1)
        jumps=t.face_jumps(g,a,b)
        check('variable_face_exact_linear_jump_bound',len(jumps)==1 and jumps[0]['jump_numerator']==(Q(3,4),Q(1,2)) and jumps[0]['jump_numerator_bounds']==(Q(3,4),Q(5,4)))
        variation=t.edge_directional(g,a,b,(1,0,0),(-1,0,0),settings)
        length=t.length_interval((Q(0),Q(1),Q(1)),128)
        broad=(length[0]/1152,length[1]/96)
        check('variable_face_normal_integral_positive_bound',broad[0]<=variation['derivative'][0]<=variation['derivative'][1]<=broad[1])
        path=[(0,Q(1,10),Q(1,2)),(0,Q(2,5),Q(1,2)),(0,Q(4,5),Q(1,2))]
        first=t.edge_tangent_components(g,path[0],path[1],settings)
        second=t.edge_tangent_components(g,path[1],path[2],settings)
        witness=t.tangent_witness(g,path,settings)
        check('face_normal_component_not_ordinary',witness['components'][1][0] is None)
        check('collinear_middle_redistribution_zero',contains(witness['components'][1][1],Q(0)))
        check('both_adjacent_tangent_terms_nonzero',first['components'][1][2][1]<0 and second['components'][0][2][1]<0)
        check('full_adjacent_tangent_assembly',witness['components'][1][2]==t.add(first['components'][1][2],second['components'][0][2]))
        check('variable_face_fixed_endpoint_witness',witness['status']=='negative_tangent_witness' and witness['axis']==2 and witness['evaluation']['derivative'][1]<0 and witness['evaluation']['feasible_step_bound']>0)
        blocked=[(p[0],p[1],Q(1)) for p in path]
        blocked_witness=t.tangent_witness(g,blocked,settings)
        check('physical_boundary_blocks_outward_witness',blocked_witness['status']=='no_negative_tangent_witness_resolved')
        # A true quadratic jump is negative inside despite positive endpoints.
        def changing_jump_velocity(x,y,z):
            return (2+y)*(3+z)+(x*(y*z-(y+z)/2+Q(3,16)) if x<=0 else 0)
        changing=grid(((-1,0,1),(0,1),(0,1)),changing_jump_velocity)
        changing_jumps=t.face_jumps(changing,a,b)
        check('quadratic_jump_positive_endpoints_negative_vertex',len(changing_jumps)==1 and
              changing_jumps[0]['jump_numerator']==(Q(3,16),Q(-1),Q(1)) and
              changing_jumps[0]['jump_numerator_bounds']==(Q(-1,16),Q(3,16)) and
              not changing_jumps[0]['convex_normal_jump'])
        # An independent bounded-log primitive for variable normal coefficients.
        factored=grid(((-1,0,1),(0,1),(0,1)),lambda x,y,z:(2-abs(x))*(3+y)*(4+z))
        factored_action=t.edge_action(factored,a,b,settings)
        factored_variation=t.edge_directional(factored,a,b,(1,0,0),(-1,0,0),settings)
        root_two=t.length_interval((Q(0),Q(1),Q(1)),192)
        action_oracle=t.mul(t.mul(root_two,t.point(Q(1,2))),
                           t.sub(logarithm(Q(4,3))[0],logarithm(Q(5,4))[0]))
        def primitive_at(u):
            return t.sub(t.mul(t.point(7),logarithm(u+3)[0]),t.mul(t.point(9),logarithm(u+4)[0]))
        signed_integral=t.sub(t.sub(t.mul(t.point(2),primitive_at(Q(1,2))),primitive_at(Q(0))),primitive_at(Q(1)))
        normal_oracle=t.mul(t.mul(root_two,t.point(Q(1,4))),signed_integral)
        check('variable_face_action_log_oracle',encloses(factored_action['action'],action_oracle))
        check('variable_face_sign_changing_normal_log_oracle',encloses(factored_variation['derivative'],normal_oracle))
        results['variable_face']=dict(jumps=jumps,normal_variation=variation,broad_positive_bound=broad,
            first=first,second=second,witness=witness,boundary=blocked_witness,changing_jumps=changing_jumps,
            factored_action=factored_action,action_oracle=action_oracle,
            factored_variation=factored_variation,normal_oracle=normal_oracle)

        # 6. Failure/precision/cancellation controls, with all unresolved states retained.
        rejected('zero_length_rejected',lambda:t.edge_action(g,a,a,settings))
        rejected('outside_box_rejected',lambda:t.edge_action(g,(-2,0,0),b,settings))
        rejected('nonpositive_velocity_rejected',lambda:grid(((0,1),(0,1),(0,1)),lambda x,y,z:Q(0)))
        rejected('nonfinite_binary64_rejected',lambda:t.exact(float('nan')))
        rejected('outward_direction_rejected',lambda:t.path_directional(g,blocked,[(0,0,0),(0,0,1),(0,0,0)],settings))
        rejected('direct_edge_outward_direction_rejected',lambda:t.edge_directional(g,a,b,(0,-1,0),(0,0,0),settings))
        crossed_faces=grid(((-1,0,1),(-1,0,1),(-1,1)),lambda x,y,z:Q(6))
        rejected('multiple_aligned_faces_variation_rejected',lambda:t.edge_directional(crossed_faces,(0,0,Q(-1,2)),(0,0,Q(1,2)),(0,0,0),(0,0,0),settings))
        check('multiple_aligned_faces_action_still_defined',contains(t.edge_action(crossed_faces,(0,0,Q(-1,2)),(0,0,Q(1,2)),settings)['action'],Q(1,6)))
        g=grid(((0,1),(-1,1),(-1,1)),lambda x,y,z:Q(1,1000)+Q(9999,1000)*x)
        original=[(0,0,0),(Q(1,2),Q(1,3),0),(1,0,0)]
        candidate=[original[0],(Q(1,2),Q(1,2),0),original[-1]]
        unresolved=t.action_difference(g,original,candidate,t.options(0,1,128))
        check('finite_low_series_budget_sign_unresolved',contains(unresolved['difference'],Q(0)))
        unresolved['interpretation']='Bounded interval contains zero; no action sign or accuracy pass.'
        same=t.action_difference(g,original,original,settings)
        check('identical_edges_cancel_exactly',same['difference']==(0,0) and same['changed_edges']==[])
        g=grid(((0,1000),(-2,2),(-1,1)),lambda x,y,z:Q(6))
        original=[(0,0,0),(1,1,0),(2,0,0),(1000,0,0)]
        candidate=[original[0],(1,float.fromhex('0x1.0000000000001p+0'),0),original[2],original[3]]
        before=t.path_action(g,original,settings);after=t.path_action(g,candidate,settings)
        difference=t.action_difference(g,original,candidate,settings)
        check('sub_total_ulp_action_sign_bounded',difference['difference'][0]>0 and len(difference['changed_edges'])==2)
        check('rounded_total_actions_do_not_resolve_change',float(sum(before['action'])/2)==float(sum(after['action'])/2))
        rejected('candidate_endpoint_change_rejected',lambda:t.action_difference(g,original,[(0,1,0)]+candidate[1:],settings))
        results['failure_and_cancellation']=dict(unresolved=unresolved,identical=same,before=before,after=after,difference=difference)
        for name,digest in prepared['input_sha256'].items(): check('unchanged_input_'+name,sha(ROOT/name)==digest)
        for name,digest in prepared['output_sha256'].items(): check('unchanged_frozen_'+name,sha(out/name)==digest)
        status='passed'
    except BaseException as e:
        status='failed';error=dict(type=type(e).__name__,message=str(e));raise
    finally:
        save(out/'results.json',results);save(out/'checks.json',checks)
        save(out/'summary.json',dict(status=status,error=error,prepared_sha256=sha(out/'prepared.json'),
            prelaunch_review_sha256=sha(out/'prelaunch_review.json'),
            elapsed_seconds=time.time()-started,control_settings=settings,controls_total=len(checks),
            controls_passed=sum(r['passed'] for r in checks),declared_families=6,
            numerical_scope='Invented fixed-polygon rational integrals and directional witnesses only.',
            native_evaluations=0,ray_calls=0,optimizer_calls=0,
            limitations=['Finite integration budgets leave intervals unresolved when necessary.',
                         'No all-direction stationarity, first-arrival, source/model derivative, or native status claim.'],
            output_sha256={n:sha(out/n) for n in ('results.json','checks.json')},input_sha256=prepared['input_sha256']))


if __name__=='__main__':main()
