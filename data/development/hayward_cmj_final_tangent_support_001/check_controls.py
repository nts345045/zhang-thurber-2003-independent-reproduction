#!/usr/bin/env python3
"""Three compact invented control families; execution requires prior review."""
from fractions import Fraction as Q
import hashlib
import importlib.util
from itertools import product
import json
from pathlib import Path
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def encoded(value):
    if isinstance(value,Q): return str(value)
    if isinstance(value,dict): return {str(k):encoded(v) for k,v in value.items()}
    if isinstance(value,(tuple,list)): return [encoded(v) for v in value]
    return value


def main():
    output=HERE/'controls'; output.mkdir(exist_ok=True)
    if (output/'summary.json').exists(): raise ValueError('Preserve existing controls')
    sys.path.insert(0,str(HERE/'source')); sys.path.insert(0,str(HERE))
    from diagnostics import trilinear_action_bounds as t
    from diagnostics.check_native_interface_support import logarithm
    import aligned_face_support as support
    zero_path=ROOT/'data/development/hayward_cmj_post_step_zero_support_001/run.py'
    if sha(zero_path)!='8223688462bf10d4c619fc6adaffd1a0066de5dd80454d902b2364459b92d067': raise ValueError('Changed projected-norm source')
    spec=importlib.util.spec_from_file_location('reviewed_physical_box_norm',str(zero_path))
    zero=importlib.util.module_from_spec(spec); spec.loader.exec_module(zero)
    checks=[]; results=[]; error=None
    def check(name,ok):
        checks.append(dict(name=name,passed=bool(ok)))
        if not ok: raise AssertionError(name)
    def rejected(name,function):
        try: function()
        except ValueError: check(name,True)
        else: check(name,False)
    def grid(axes,function):
        return t.model(axes,{k:function(*(axes[j][k[j]] for j in range(3))) for k in product(*(range(len(a)) for a in axes))})
    def encloses(a,b): return a[0]<=b[0]<=b[1]<=a[1]
    point=lambda x:(Q(x),Q(x))
    settings=t.options(8,1,128)
    try:
        # 1. Exact constant moments, a coupled algebra fixture, and scalar fitting guards.
        axes=((-Q(1,4),Q(0),Q(1,4)),(Q(0),Q(1)),(-Q(1),Q(1)))
        g=grid(axes,lambda x,y,z:1-2*abs(x)); a=(Q(0),Q(0),Q(0)); b=(Q(0),Q(1),Q(0))
        moments=support.aligned_patch_moments(g,a,b,settings,t)
        item=dict(family='constant_moments_and_coupling',moments=moments); results.append(item)
        check('constant_four_exact_moments',moments['status']=='bounded_convex_patch_moments'
              and moments['patches'][0]['minus']==[point(-1),point(-1)] and moments['patches'][0]['plus']==[point(1),point(1)])
        path=[(-Q(1,4),Q(0),Q(0)),a,b,(Q(1,4),Q(1),Q(0))]
        z=[point(0),point(0),point(0)]
        # These three records are an algebra fixture, not a claimed evaluation of g.
        # Ordinary incident normals are b=(1/3,-1/3); the middle face moments are exact.
        records=[dict(edge=0,blocked_axes=[],components=[z,[point(Q(1,3)),point(0),point(0)]]),
                 dict(edge=1,blocked_axes=[0],components=[[None,point(0),point(0)],[None,point(0),point(0)]]),
                 dict(edge=2,blocked_axes=[],components=[[point(-Q(1,3)),point(0),point(0)],z])]
        base=support.ordinary_base(path,records); patches=[dict(moments['patches'][0],edge=1)]
        omitted=[dict(r,components=list(r['components'])) for r in records]
        omitted[0]['components'][0]=None; omitted[-1]['components'][1]=None
        check('fixed_endpoint_arrays_may_be_omitted',support.ordinary_base(path,omitted)==base)
        proposal=support.propose_theta(path,base,patches)
        witness=support.assemble_support(path,base,patches,proposal['theta_exact'],axes,zero.projected_norm)
        item.update(base=base,proposal=proposal,witness=witness)
        check('shared_constant_fit',proposal['theta']==[0.5] and proposal['termination']=='coefficients_unchanged')
        check('ordinary_entry_exit_normals_retained',len(base['ordinary_contributions_in_blocked_slots'])==2
              and witness['vector'][0]['components'][0]==point(Q(1,3)) and witness['vector'][1]['components'][0]==point(-Q(1,3)))
        check('restricted_family_residual_not_general_minimum',Q(witness['norm']['lower_squared'])==Q(2,9)==Q(witness['norm']['upper_squared']))
        # theta(u)=u gives (-1/3,+1/3), exactly canceling this same b. A constant theta cannot.
        density=tuple(sum(Q(c,k+1) for k,c in enumerate(p)) for p in ((-2,6,-4),(0,-2,4)))
        check('nonconstant_density_cancels',density[0]+Q(1,3)==density[1]-Q(1,3)==0)
        clipped=dict(base,components=[None,[point(-3),point(0),point(0)],[point(-3),point(0),point(0)],None])
        clipped_fit=support.propose_theta(path,clipped,patches); item['clipped_proposal']=clipped_fit
        check('bounded_coordinate_clip',clipped_fit['theta']==[1.0] and clipped_fit['termination']=='coefficients_unchanged')
        homogeneous=grid(axes,lambda x,y,z:Q(1)); hm=support.aligned_patch_moments(homogeneous,a,b,settings,t)
        hz=support.propose_theta(path,base,[dict(hm['patches'][0],edge=1)]); item.update(homogeneous=hm,zero_column_proposal=hz)
        check('true_zero_midpoint_column',hz['exact_zero_midpoint_columns']==[0] and hz['theta']==[0.5])
        combined=t.edge_tangent_components(homogeneous,a,b,settings); item['combined_constant']=combined
        check('combined_action_closed_form',combined['action']==point(1)
              and combined['components']==[[None,point(-1),point(0)],[None,point(1),point(0)]])
        tiny=dict(patches[0],minus=[point(0),point(0)],plus=[point(Q(1,2**600)),point(Q(1,2**600))])
        unusable=support.propose_theta(path,base,[tiny]); item['underflowed_norm_proposal']=unusable
        check('nonzero_float_column_norm_underflow_is_not_zero',unusable['status']=='proposal_unusable'
              and unusable['termination']=='unusable_midpoint_arithmetic' and unusable['exact_zero_midpoint_columns']==[])

        # 2. Independent log integrals for a genuinely variable quadratic face.
        axes2=((-Q(1),Q(0),Q(1)),(Q(0),Q(1)),(Q(0),Q(1)))
        variable=grid(axes2,lambda x,y,z:(2-abs(x))*(3+y)*(4+z)); a2=(Q(0),Q(0),Q(0)); b2=(Q(0),Q(1),Q(1))
        vm=support.aligned_patch_moments(variable,a2,b2,settings,t)
        item=dict(family='variable_face_log_oracle',moments=vm); results.append(item)
        l43=logarithm(Q(4,3))[0]; l54=logarithm(Q(5,4))[0]
        integrals=[t.sub(t.mul(point(4),l43),t.mul(point(5),l54)),t.add(t.mul(point(-3),l43),t.mul(point(4),l54))]
        length=t.length_interval((Q(0),Q(1),Q(1)),192)
        check('oracle_radical_squared',length[0]**2<=2<=length[1]**2)
        negative=[t.mul(t.mul(point(-Q(1,4)),length),v) for v in integrals]
        positive=[t.mul(point(-1),v) for v in negative]; item.update(minus_log_oracle=negative,plus_log_oracle=positive)
        check('four_variable_face_log_moments',all(encloses(actual,expected) for side,values in (('minus',negative),('plus',positive)) for actual,expected in zip(vm['patches'][0][side],values)))
        reverse=support.aligned_patch_moments(variable,b2,a2,settings,t); item['reversed']=reverse
        check('reversed_endpoint_weights',all(encloses(actual,expected) for side,values in (('minus',negative[::-1]),('plus',positive[::-1])) for actual,expected in zip(reverse['patches'][0][side],values)))
        split=support.aligned_patch_moments(variable,a2,b2,t.options(8,2,128),t); item['subdivided']=split
        sums={side:[(sum(p[side][j][0] for p in split['patches']),sum(p[side][j][1] for p in split['patches'])) for j in (0,1)] for side in ('minus','plus')}
        check('split_global_shape_functions',all(encloses(actual,expected) for side,values in (('minus',negative),('plus',positive)) for actual,expected in zip(sums[side],values)))

        # 3. Whole-patch sign eligibility, full-vector assembly and true-box projection.
        bad=grid(axes2,lambda x,y,z:(2+y)*(3+z)+(x*(y*z-(y+z)/2+Q(3,16)) if x<0 else 0))
        bad_moments=support.aligned_patch_moments(bad,a2,b2,settings,t)
        item=dict(family='eligibility_and_box',nonconvex=bad_moments); results.append(item)
        check('positive_endpoints_do_not_prove_convex_jump',bad_moments['status']=='ineligible_nonconvex_normal_jump'
              and bad_moments['patches'][0]['exact_jump_range']==(-Q(1,16),Q(3,16)) and bad_moments['normal_patch_integrations']==0)
        rejected('out_of_range_theta',lambda:support.assemble_support(path,base,patches,[-Q(1,10)],axes,zero.projected_norm))
        rejected('zero_length_edge',lambda:support.aligned_patch_moments(variable,a2,a2,settings,t))
        axes3=((-Q(1),Q(0),Q(1)),(-Q(1),Q(0),Q(1)),(-Q(1),Q(1)))
        multi=support.aligned_patch_moments(grid(axes3,lambda x,y,z:Q(1)),(0,0,0),(0,0,1),settings,t); item['multiple_face']=multi
        check('multiple_aligned_faces_explicitly_ineligible',multi['status']=='ineligible_single_aligned_face_required' and len(multi['aligned'])==2)
        box_path=[(0,0,0),(-Q(1),0,0),(Q(1),0,0),(-Q(1)+Q(1,10**12),0,0),(0,0,0)]
        components=[None,[point(2),point(0),point(0)],[point(-2),point(0),point(0)],[point(2),point(0),point(0)],None]
        norm,projected,blocked=zero.projected_norm(box_path,components,((-Q(1),Q(1)),)*3)
        item.update(box_norm=norm,box_components=projected)
        check('true_box_not_old_activity_band',not blocked and Q(norm['lower_squared'])==Q(norm['upper_squared'])==4
              and projected[0]['projected_bounds']==point(0) and projected[3]['projected_bounds']==point(0)
              and projected[6]['physical_box_position']=='interior' and projected[6]['projected_bounds']==point(2))
        # Two adjacent face edges: interval contributions must add at their shared node.
        # These perturbed intervals enclose the constant exact moments -1/+1.
        shared_path=[(-Q(1,4),0,0),(0,0,0),(0,1,0),(0,2,0),(Q(1,4),2,0)]
        shared_records=[dict(edge=0,blocked_axes=[],components=[None,[point(Q(1,6)),point(0),point(0)]]),
                        dict(edge=1,blocked_axes=[0],components=[[None,point(0),point(0)],[None,point(0),point(0)]]),
                        dict(edge=2,blocked_axes=[0],components=[[None,point(0),point(0)],[None,point(0),point(0)]]),
                        dict(edge=3,blocked_axes=[],components=[[point(-Q(1,6)),point(0),point(0)],None])]
        around=lambda c,r:(Q(c)-r,Q(c)+r)
        shared_patches=[dict(patches[0],edge=1,a_exact=shared_path[1],b_exact=shared_path[2],
                             minus=[around(-1,Q(1,10)),around(-1,Q(1,5))],plus=[around(1,Q(1,20)),around(1,Q(1,4))]),
                        dict(patches[0],edge=2,a_exact=shared_path[2],b_exact=shared_path[3],
                             minus=[around(-1,Q(1,8)),around(-1,Q(1,16))],plus=[around(1,Q(1,6)),around(1,Q(1,12))])]
        tf,sf=float(Q(1,3)),float(Q(2,3)); tq,sq=Q(tf),Q(sf)
        c1=Q(1,6)+2*tq-1; c2=2*tq+2*sq-2; c3=-Q(1,6)+2*sq-1
        r1=(1-tq)/10+tq/20; r2=(1-tq)/5+tq/4+(1-sq)/8+sq/6; r3=(1-sq)/16+sq/12
        expected=[dict(node=i,components=[around(c,r),point(0),point(0)]) for i,c,r in ((1,c1,r1),(2,c2,r2),(3,c3,r3))]
        expected_squared=((c1+r1)**2+(c3-r3)**2,(c1-r1)**2+max((c2-r2)**2,(c2+r2)**2)+(c3+r3)**2)
        shared=support.assemble_support(shared_path,support.ordinary_base(shared_path,shared_records),shared_patches,[tf,sf],
                                        ((-Q(1,4),Q(1,4)),(-Q(1),Q(3)),(-Q(1),Q(1))),zero.projected_norm)
        item['shared_node_interval_fixture']=dict(theta_hex=[tf.hex(),sf.hex()],theta_exact=[tq,sq],
             expected_vector=expected,expected_squared=expected_squared,witness=shared)
        check('shared_node_binary64_interval_sum',tq!=Q(1,3) and sq!=Q(2,3) and c1+r1<0 and c2-r2<0<c2+r2 and c3-r3>0
              and shared['theta_exact']==[tq,sq] and shared['vector']==expected
              and (Q(shared['norm']['lower_squared']),Q(shared['norm']['upper_squared']))==expected_squared
              and len(shared['ordinary_contributions_in_blocked_slots'])==2)
    except Exception as exc:
        error=dict(type=type(exc).__name__,message=str(exc))
    payload=dict(status='failed' if error else 'passed',error=error,invented_only=True,families=results,checks=checks,
        helper_sha256=sha(HERE/'aligned_face_support.py'),primitive_sha256=sha(HERE/'source/diagnostics/trilinear_action_bounds.py'),
        source_sha256={str(p.relative_to(ROOT)):sha(p) for p in (Path(__file__).resolve(),HERE/'aligned_face_support.py',HERE/'source/diagnostics/trilinear_action_bounds.py',
            HERE/'source/diagnostics/check_native_interface_support.py',HERE/'source/diagnostics/first_arrival_1d_precise_turn_reference.py',zero_path)},
        native_calls=0,ray_calls=0,interpretation='Invented moment, coupling and proposal/box controls. No native action, fit, support or stationarity result.')
    with (output/'summary.json').open('x') as stream: json.dump(encoded(payload),stream,indent=2,sort_keys=True,allow_nan=False); stream.write('\n')
    print(json.dumps(dict(status=payload['status'],checks=len(checks),summary_sha256=sha(output/'summary.json'))))
    return 1 if error else 0


if __name__=='__main__': sys.exit(main())
