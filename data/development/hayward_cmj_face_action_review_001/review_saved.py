#!/usr/bin/env python3
"""Terminal-only saved-record review; no action integration or numeric-module import."""
from bisect import bisect_right
import csv
from fractions import Fraction as Q
import gzip
import hashlib
from itertools import product
import json
import math
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
RUN=ROOT/'data/development/hayward_cmj_face_action_001'
COUNTS={}


def check(name,condition):
    COUNTS[name]=COUNTS.get(name,0)+1
    if not condition:raise AssertionError(name)


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''):h.update(block)
    return h.hexdigest()


def read(path):
    with (gzip.open(str(path),'rt') if path.suffix=='.gz' else path.open()) as stream:return json.load(stream)


def rows(path):
    with path.open(newline='') as stream:return list(csv.DictReader(stream))


def encode(value):
    if isinstance(value,Q):return str(value)
    if isinstance(value,dict):return {str(k):encode(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [encode(v) for v in value]
    return value


def save(path,value):
    with path.open('x') as stream:json.dump(encode(value),stream,indent=2,sort_keys=True,allow_nan=False);stream.write('\n')


def pins(base,mapping):
    for name,digest in mapping.items():check('file_sha256',sha(base/name)==digest)


def interval(values):
    a,b=map(Q,values);check('interval_order',a<=b);return a,b


def add(a,b):return a[0]+b[0],a[1]+b[1]
def sub(a,b):return a[0]-b[1],a[1]-b[0]
def exact(text):return Q(float(text))
def point(row):return tuple(exact(row[a]) for a in 'xyz')
def dot(a,b):return sum((x*y for x,y in zip(a,b)),Q(0))


def polynomial(coefficients,u):
    result=Q(0)
    for c in reversed(coefficients):result=result*u+Q(c)
    return result


def extrema(coefficients):
    a=list(map(Q,coefficients));check('quadratic_degree',1<=len(a)<=3)
    samples=[polynomial(a,Q(0)),polynomial(a,Q(1))]
    if len(a)==3 and a[2]:
        u=-a[1]/(2*a[2])
        if 0<u<1:samples.append(polynomial(a,u))
    return min(samples),max(samples)


def cuts_and_alignment(a,b,axes):
    cuts={Q(0),Q(1)};aligned=[]
    for k,axis in enumerate(axes):
        if a[k]==b[k]:
            if a[k] in axis[1:-1]:aligned.append((k,axis.index(a[k])))
        else:
            for x in axis[1:-1]:
                u=(x-a[k])/(b[k]-a[k])
                if 0<u<1:cuts.add(u)
    return sorted(cuts),aligned


def verify_pieces(record,a,b,axes):
    cuts,aligned=cuts_and_alignment(a,b,axes)
    check('action_alignment',record['aligned']==[list(v) for v in aligned])
    pieces=record['pieces']
    check('exact_piece_partition',[(Q(p['u'][0]),Q(p['u'][1])) for p in pieces]==list(zip(cuts,cuts[1:])))
    for p in pieces:
        lo,hi=interval(p['velocity_bounds']);rho=Q(p['rho']);n=p['series_degree'];c=(lo+hi)/2
        check('positive_velocity_bound',0<lo<=hi and rho==(hi-lo)/(hi+lo) and 0<=rho<1)
        check('declared_series_degree',n==(0 if rho==0 else 8))
        check('reciprocal_tail_formula',Q(p['reciprocal_tail'])==rho**(n+1)/(c*(1-rho)))
        check('cubic_velocity_degree',1<=len(p['velocity_polynomial'])<=4)
        left,right=map(Q,p['u'])
        for u in (left,right):
            position=tuple(x+u*(y-x) for x,y in zip(a,b))
            check('piece_in_closed_cell',all(axes[k][p['cell'][k]]<=position[k]<=axes[k][p['cell'][k]+1] for k in range(3)))
    length=interval(record['length']);square=dot(tuple(y-x for x,y in zip(a,b)),tuple(y-x for x,y in zip(a,b)))
    check('exact_length_enclosure',0<length[0] and length[0]**2<=square<=length[1]**2)


def grid_normal_slope(position,cell,axis,axes,velocity):
    # Algebraic bilinear slope, only for auditing saved jump polynomials.
    result=Q(0);width=axes[axis][cell[axis]+1]-axes[axis][cell[axis]]
    for corner in product((0,1),repeat=3):
        weight=Q(1 if corner[axis] else -1)/width
        for k in range(3):
            if k==axis:continue
            f=(position[k]-axes[k][cell[k]])/(axes[k][cell[k]+1]-axes[k][cell[k]])
            weight*=f if corner[k] else 1-f
        result+=weight*velocity[tuple(axes[k][cell[k]+corner[k]] for k in range(3))]
    return result


def jump_check(edge,a,b,axes,velocity):
    cuts,aligned=cuts_and_alignment(a,b,axes)
    check('single_face_jump_inventory',len(aligned)==1 and len(edge['whole_piece_jumps'])==len(cuts)-1)
    axis,index=aligned[0];all_convex=True;minimum=None
    for saved,(left,right) in zip(edge['whole_piece_jumps'],zip(cuts,cuts[1:])):
        check('jump_piece_join',list(map(Q,saved['u']))==[left,right] and saved['normal_axis']==axis)
        mid=(left+right)/2;position=tuple(x+mid*(y-x) for x,y in zip(a,b))
        cell=[min(len(v)-2,max(0,bisect_right(v,position[k])-1)) for k,v in enumerate(axes)]
        minus=list(cell);minus[axis]=index-1;plus=list(cell);plus[axis]=index
        values=[]
        for s in (Q(0),Q(1,2),Q(1)):
            u=left+(right-left)*s;position=tuple(x+u*(y-x) for x,y in zip(a,b))
            values.append(grid_normal_slope(position,minus,axis,axes,velocity)-grid_normal_slope(position,plus,axis,axes,velocity))
        c2=2*(values[2]-2*values[1]+values[0]);coefficients=[values[0],values[2]-values[0]-c2,c2]
        while len(coefficients)>1 and coefficients[-1]==0:coefficients.pop()
        check('independent_jump_coefficients',list(map(Q,saved['jump_numerator']))==coefficients)
        bounds=extrema(coefficients)
        check('whole_piece_jump_extrema',interval(saved['jump_numerator_bounds'])==bounds and saved['convex_normal_jump']==(bounds[0]>=0))
        all_convex=all_convex and bounds[0]>=0;minimum=bounds[0] if minimum is None else min(minimum,bounds[0])
    return all_convex,minimum


def projected_tangent_norm(components,candidate,axes,selected):
    total=(Q(0),Q(0));entries=[];missing=0;boundary_count=0
    for row in components:
        node=row['node']
        for k,saved in enumerate(row['components']):
            if saved is None:missing+=1;continue
            lo,hi=interval(saved);where='interior';projected=(lo,hi)
            if candidate[node][k]==axes[k][0]:where='exact_lower';projected=(min(lo,Q(0)),min(hi,Q(0)))
            elif candidate[node][k]==axes[k][-1]:where='exact_upper';projected=(max(lo,Q(0)),max(hi,Q(0)))
            if where!='interior':boundary_count+=1
            a,b=projected;squared=(Q(0) if a<=0<=b else min(a*a,b*b),max(a*a,b*b))
            total=add(total,squared)
            entries.append(dict(node=node,axis='xyz'[k],coordinate_exact=candidate[node][k],
                selected_near_face_node=node in selected,physical_box_position=where,
                component_bounds=(lo,hi),projected_bounds=projected,squared_bounds=squared))
    scales={}
    for name,scale in [('strict_gradient_scale',Q(1,10**7)),('combined_gradient_scale',Q(1,10**5))]:
        square=scale*scale
        scales[name]=dict(scale_squared=square,classification='strictly_above' if total[0]>square else
                         ('strictly_below' if total[1]<square else 'overlapping'),diagnostic_only=True)
    summary=dict(lower_squared=total[0],upper_squared=total[1],units='s^2/km^2',
        informational_binary64_sqrt=[math.sqrt(float(v)) for v in total],sqrt_units='s/km',
        available_component_count=len(entries),unavailable_face_normal_count=missing,
        exact_physical_boundary_component_count=boundary_count,threshold_scales=scales,
        interpretation='Lower bound for any coupled support residual sharing these fixed tangent components; existence and eligibility remain separate. No stopping decision.',
        activity_rule='Exact physical boundary only; no 1e-10 activity band.')
    return summary,entries


def main():
    check('fresh_review',not (HERE/'review.json').exists() and not (RUN/'review.json').exists())
    execution=read(RUN/'execution.json')
    check('terminal_owned_execution',execution['status']=='completed' and execution['return_code']==0 and execution['child_reaped'])
    summary=read(RUN/'summary.json');prepared=read(RUN/'prepared.json');prelaunch=read(RUN/'prelaunch_review.json')
    check('terminal_calculation',summary['status']=='completed_bounded_calculation' and summary['error'] is None)
    check('prelaunch_binding',prelaunch['status']=='passed' and prelaunch['prepared_sha256']==sha(RUN/'prepared.json'))
    for record in (execution,summary):
        check('execution_prepared_binding',record['prepared_sha256']==sha(RUN/'prepared.json'))
        check('execution_prelaunch_binding',record['prelaunch_review_sha256']==sha(RUN/'prelaunch_review.json'))
    check('controller_source_binding',execution['controller_sha256']==sha(RUN/'controller.py'))
    check('python_runtime_binding',execution['python_sha256']==prepared['python']['executable_sha256']==sha(Path(prepared['python']['executable'])))
    check('exact_executed_command',execution['command']==[prepared['python']['executable']]+prepared['planned_command'][1:])
    check('declared_environment',execution['environment']==prepared['environment'])
    pins(ROOT,prepared['input_sha256']);pins(RUN,prepared['output_sha256'])
    pins(RUN,execution['output_sha256']);pins(RUN,summary['output_sha256'])
    check('fixed_budget',summary['settings']==prepared['settings']==dict(terms=8,subdivisions=1,bits=128))
    check('no_solver_or_step',all(summary[k]==0 for k in ('native_trace_calls','field_calls','optimizer_calls','descent_steps')))
    native_contexts=read(RUN/'inputs/native_context.json')
    statuses=rows(RUN/'inputs/original_status.csv');raw_paths=rows(RUN/'inputs/original_paths.csv')
    selection=rows(RUN/'inputs/near_face_nodes.csv');raw_grid=rows(RUN/'inputs/trial_grid.csv')
    axes=tuple(tuple(sorted({exact(r[k]) for r in raw_grid})) for k in 'xyz')
    velocity={point(r):exact(r['v']) for r in raw_grid}
    check('positive_complete_grid',len(velocity)==len(raw_grid)==462 and all(v>0 for v in velocity.values()))
    model=read(RUN/'model_provenance.json')
    check('model_native_context',model['native_contexts']==native_contexts)
    check('model_raw_file',model['recorded_grid_sha256']==sha(RUN/'inputs/trial_grid.csv'))
    check('model_axes',[list(map(Q,v)) for v in model['axes_exact_rational']]==[list(v) for v in axes])
    check('model_node_inventory',len(model['nodes'])==len(raw_grid)==462)
    for saved,raw in zip(model['nodes'],raw_grid):
        for key in ('x','y','z','v'):
            entry=saved['values'][key]
            check('model_binary64_provenance',entry['raw_text']==raw[key] and entry['binary64_hex']==float(raw[key]).hex() and Q(entry['exact_rational'])==exact(raw[key]))
    reports=[];norm_records=[]
    check('two_case_inventories',len(statuses)==len(native_contexts)==len(prepared['cases'])==len(summary['results'])==2)
    for status,context,plan,saved_summary in zip(statuses,native_contexts,prepared['cases'],summary['results']):
        event=int(status['event']);result=read(RUN/('event_'+str(event)+'.json.gz'))
        check('native_roster',event==plan['event']==result['event']==saved_summary['event'] and result['station']==160)
        check('full_native_context',result['native_context']==context and context['original_status']==status and result['original_status']==status)
        check('flags_unmodified',status['ray_converged']==result['original_convergence_flag_preserved']=='0' and result['candidate_convergence_status'] is None)
        native=[r for r in raw_paths if int(r['event'])==event];selected=plan['selected_original_nodes']
        selected_rows=[r for r in selection if int(r['event'])==event]
        check('selected_node_inventory',result['selected_nodes']==selected==[int(r['node']) for r in selected_rows])
        metadata=[k for k in native[0] if k.startswith(('source_','receiver_'))]
        check('full_metadata',result['full_metadata']=={k:status[k] for k in metadata})
        for row in native:check('path_native_join',all(row[k]==status[k] for k in metadata))
        for row in selected_rows:check('selected_raw_join',all(row[k]==v for k,v in native[int(row['node'])].items()))
        original=list(map(point,native));candidate=[(Q(0),p[1],p[2]) if i in selected else p for i,p in enumerate(original)]
        check('path_point_count',len(original)==plan['original_path_nodes']==len(result['coordinate_provenance']))
        for i,(saved,raw) in enumerate(zip(result['coordinate_provenance'],native)):
            check('candidate_node_join',saved['node']==i and saved['x_replaced_with_exact_zero']==(i in selected) and tuple(map(Q,saved['candidate_exact_rational']))==candidate[i])
            for key in 'xyz':
                entry=saved['original'][key]
                check('path_binary64_provenance',entry['raw_text']==raw[key] and entry['binary64_hex']==float(raw[key]).hex() and Q(entry['exact_rational'])==exact(raw[key]))
        check('fixed_exact_endpoints',candidate[0]==original[0] and candidate[-1]==original[-1])
        check('original_positive_contained_geometry',all(a!=b for a,b in zip(original,original[1:])) and
              all(axes[k][0]<=p[k]<=axes[k][-1] for p in original for k in range(3)))
        outside=[i for i,p in enumerate(candidate) if any(not axes[k][0]<=p[k]<=axes[k][-1] for k in range(3))]
        collapsed=[i for i,(a,b) in enumerate(zip(candidate,candidate[1:])) if a==b]
        ineligible=[]
        if outside:ineligible.append(dict(reason='candidate_outside_physical_box',nodes=outside))
        if collapsed:ineligible.append(dict(reason='candidate_zero_length_edges_no_merging',edges=collapsed))
        check('candidate_eligibility_preserved',result['candidate_ineligibility']==ineligible)
        if ineligible:
            check('ineligible_case_unevaluated',result['action_classification']=='ineligible_candidate' and
                  all(result[k] is None for k in ('original_action','candidate_action','candidate_minus_original')) and
                  all(v==0 for v in result['counts'].values()))
            for key,value in saved_summary.items():check('summary_full_result_join',result[key]==value)
            reports.append(dict(event=event,station=160,native_context=context,original_flag='0',candidate_flag=None,
                action_classification='ineligible_candidate',candidate_ineligibility=ineligible))
            continue
        edge_records=result['unique_action_edge_records'];old_ids=result['original_edge_record_ids'];new_ids=result['candidate_edge_record_ids']
        check('edge_record_inventory',[r['cache_id'] for r in edge_records]==list(range(len(edge_records))) and len(old_ids)==len(new_ids)==len(original)-1)
        keys=[]
        for record in edge_records:
            a,b=tuple(map(Q,record['a_exact'])),tuple(map(Q,record['b_exact']));keys.append((a,b))
            verify_pieces(record['record'],a,b,axes)
        check('cache_unique_geometry',len(set(keys))==len(keys))
        before=after=delta=(Q(0),Q(0));changed=[]
        for i,(old,new) in enumerate(zip(old_ids,new_ids)):
            check('edge_geometry_mapping',keys[old]==(original[i],original[i+1]) and keys[new]==(candidate[i],candidate[i+1]))
            left=interval(edge_records[old]['record']['action']);right=interval(edge_records[new]['record']['action'])
            before=add(before,left);after=add(after,right)
            if old==new:continue
            difference=sub(right,left);delta=add(delta,difference)
            changed.append(dict(edge=i,original_record=old,candidate_record=new,difference=list(map(str,difference))))
        for name,bounds in [('original_action',before),('candidate_action',after),('candidate_minus_original',delta)]:
            check('exact_action_sums',interval(result[name]['exact_rational_bounds'])==bounds)
        check('exact_changed_edge_cancellation',result['changed_edges']==changed and result['unchanged_edge_count']==len(old_ids)-len(changed))
        check('action_sign_classification',result['action_classification']==('decreased' if delta[1]<0 else ('increased' if delta[0]>0 else 'unresolved')))
        aligned=[cuts_and_alignment(a,b,axes)[1] for a,b in zip(candidate,candidate[1:])]
        singles=[i for i,v in enumerate(aligned) if len(v)==1];multiple=[i for i,v in enumerate(aligned) if len(v)>1]
        check('complete_single_face_jump_inventory',[r['edge'] for r in result['face_jump_records']]==singles)
        jump_checks=[jump_check(r,candidate[r['edge']],candidate[r['edge']+1],axes,velocity) for r in result['face_jump_records']]
        witness=result['tangent_witness']
        if multiple:
            check('multi_face_unsupported',witness['status']=='unsupported_multiple_aligned_faces' and result['candidate_free_node_tangent_components'] is None)
            norm=None
        else:
            assembled=[[(Q(0),Q(0)) for k in range(3)] for p in candidate];blocked=set()
            check('tangent_edge_inventory',[r['edge'] for r in result['candidate_edge_tangent_records']]==list(range(len(candidate)-1)))
            for row in result['candidate_edge_tangent_records']:
                i=row['edge'];expected_axes=[k for k,unused in aligned[i]]
                check('edge_blocked_normal_axes',row['blocked_axes']==expected_axes)
                for side in (0,1):
                    if i+side in (0,len(candidate)-1):check('fixed_components_omitted',row['components'][side] is None);continue
                    for k,saved in enumerate(row['components'][side]):
                        check('normal_slot_availability',(saved is None)==(k in expected_axes))
                        if saved is None:blocked.add((i+side,k))
                        else:assembled[i+side][k]=add(assembled[i+side][k],interval(saved))
            for i,k in blocked:assembled[i][k]=None
            components=result['candidate_free_node_tangent_components']
            check('free_node_inventory',[row['node'] for row in components]==list(range(1,len(candidate)-1)))
            for row in components:
                check('full_adjacent_edge_component_sum',[None if v is None else interval(v) for v in row['components']]==assembled[row['node']])
            norm,entries=projected_tangent_norm(components,candidate,axes,selected)
            norm_records.append(dict(event=event,station=160,native_context=context,summary=norm,components=entries))
            first=None
            for i in range(1,len(candidate)-1):
                for k,bounds in enumerate(assembled[i]):
                    if bounds is None or bounds[0]<=0<=bounds[1]:continue
                    sign=-1 if bounds[0]>0 else 1
                    if (sign<0 and candidate[i][k]==axes[k][0]) or (sign>0 and candidate[i][k]==axes[k][-1]):continue
                    first=(i,k,sign);break
                if first is not None:break
            if first is None:check('no_resolved_witness',witness['status']=='no_sign_resolved_feasible_tangent_component')
            else:
                i,k,sign=first
                check('deterministic_witness_selection',(witness['node'],'xyz'.index(witness['axis']),witness['sign'])==first)
                check('witness_spatial_context',witness['selected_near_face_node']==(i in selected) and
                      witness['incident_to_exact_face_edge']==any(j==i for j,unused in blocked) and
                      witness['distance_in_node_indices_to_selected_set']==min(abs(i-j) for j in selected))
                d=tuple(map(Q,witness['nonzero_direction']));check('unit_coordinate_direction',d==tuple(Q(sign if j==k else 0) for j in range(3)) and dot(d,d)==Q(witness['direction_euclidean_norm_exact'])==1)
                terms=witness['nonzero_edge_terms'];check('two_nonzero_edges',[r['edge'] for r in terms]==[i-1,i] and witness['exactly_zero_other_edge_count']==len(candidate)-3)
                derivative=(Q(0),Q(0))
                for term in terms:derivative=add(derivative,interval(term['record']['derivative']))
                check('complete_witness_edge_sum',interval(witness['full_directional']['exact_rational_bounds'])==derivative)
                check('witness_sign_preserved',witness['status']==('negative_tangent_witness' if derivative[1]<0 else 'directional_interval_unresolved'))
                if derivative[1]<0:check('witness_magnitude',tuple(map(Q,witness['descent_magnitude_bounds']))==(-derivative[1],-derivative[0]))
                h=Q(witness['feasible_positive_step_bound']);check('positive_geometric_step_bound',h>0)
                check('witness_true_box_feasibility',all(axes[j][0]<=candidate[i][j]+h*d[j]<=axes[j][-1] for j in range(3)))
                for edge in (i-1,i):
                    e=tuple(b-a for a,b in zip(candidate[edge],candidate[edge+1]))
                    check('witness_positive_edge_length_guarantee',h*h*dot(d,d)<=dot(e,e)/4)
        check('reported_counts',result['counts']['action_edge_evaluations']==len(edge_records) and
              result['counts']['tangent_edge_evaluations']==len(result['candidate_edge_tangent_records']) and
              result['counts']['witness_nonzero_edge_evaluations']==len(witness.get('nonzero_edge_terms',[])))
        for key,value in saved_summary.items():check('summary_full_result_join',result[key]==value)
        reports.append(dict(event=event,station=160,native_context=context,original_flag='0',candidate_flag=None,
            action_bounds=dict(original=before,candidate=after,candidate_minus_original=delta),action_classification=result['action_classification'],
            changed_edges=len(changed),unchanged_edges=result['unchanged_edge_count'],
            single_face_edges=len(singles),multiple_face_edges=len(multiple),
            all_single_face_patches_convex=all(v[0] for v in jump_checks),
            minimum_jump_numerator=min((v[1] for v in jump_checks),default=None),
            tangent_witness=witness,tangent_projected_norm=norm))
    pins(ROOT,prepared['input_sha256']);pins(RUN,prepared['output_sha256']);pins(RUN,execution['output_sha256'])
    check('complete_two_case_readback',[r['event'] for r in reports]==[981,987])
    save(HERE/'tangent_norms.json',dict(native_contexts=native_contexts,cases=norm_records,
         arithmetic='Exact rational interval projection and squared sums of saved tangent enclosures; no reintegration.'))
    result=dict(status='passed',reviewer='ray_math_review',summary_sha256=sha(RUN/'summary.json'),
        execution_sha256=sha(RUN/'execution.json'),prepared_sha256=sha(RUN/'prepared.json'),
        prelaunch_review_sha256=sha(RUN/'prelaunch_review.json'),controller_sha256=sha(RUN/'controller.py'),
        checker_sha256=sha(Path(__file__)),tangent_norms_sha256=sha(HERE/'tangent_norms.json'),
        check_counts=COUNTS,cases=reports,
        limits=['Saved interval arithmetic and provenance review only; no reciprocal action or directional integral recomputed.',
                'Jump coefficients checked by independent exact trilinear slope algebra at three points per quadratic piece.',
                'Projected tangent norm uses the true physical box and excludes unavailable internal-face normals.',
                'Norm comparisons are diagnostic scales, not a stopping rule or status promotion.'])
    save(HERE/'review.json',result);save(RUN/'review.json',result)


if __name__=='__main__':main()
