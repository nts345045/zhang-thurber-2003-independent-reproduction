#!/usr/bin/env python3
"""Terminal saved-record algebra only; no project numerical imports or calls."""
import csv
from fractions import Fraction as Q
import gzip
import hashlib
import json
import math
from pathlib import Path
import struct

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
RUN=ROOT/'data/development/hayward_cmj_tangent_step_002'
FIRST=ROOT/'data/development/hayward_cmj_tangent_step_001'
FIRST_REVIEW=ROOT/'data/development/hayward_cmj_tangent_step_review_001'
POST=ROOT/'data/development/hayward_cmj_post_step_tangent_001'
POST_REVIEW=ROOT/'data/development/hayward_cmj_post_step_tangent_review_001'
START=ROOT/'data/development/hayward_cmj_face_action_001'
CONTROL=ROOT/'data/development/cmj_tangent_step_source_002'
CHECKS={}


def check(name,condition):
    CHECKS[name]=CHECKS.get(name,0)+1
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


def encoded(value):
    if isinstance(value,Q):return str(value)
    if isinstance(value,dict):return {str(k):encoded(v) for k,v in value.items()}
    if isinstance(value,(tuple,list)):return [encoded(v) for v in value]
    return value


def pins(base,values):
    for name,digest in values.items():check('sha256',sha(base/name)==digest)


def bounds(value):
    a,b=map(Q,value);check('interval_order',a<=b);return a,b


def add(a,b):return a[0]+b[0],a[1]+b[1]
def sub(a,b):return a[0]-b[1],a[1]-b[0]
def point(value):return Q(value),Q(value)
def xyz(row):return tuple(Q(float(row[k])) for k in 'xyz')
def squared(v):return sum((x*x for x in v),Q(0))


def emitted(values,hex_values):
    check('binary64_inventory',len(values)==len(hex_values))
    result=[]
    for a,h in zip(values,hex_values):
        a=float(a);b=float.fromhex(h)
        check('finite_decimal_hex_agreement',math.isfinite(a) and a.hex()==b.hex())
        result.append(Q(a))
    return result


def contract(components,direction):
    result=point(0)
    check('complete_slope_nodes',len(components)==len(direction))
    check('fixed_endpoint_direction',direction[0]==direction[-1]==(Q(0),)*3)
    for row,d in zip(components[1:-1],direction[1:-1]):
        check('complete_slope_axes',len(row)==len(d)==3)
        for interval,value in zip(row,d):
            if interval is None:check('unavailable_normal_zero',value==0)
            else:
                a,b=interval[0]*value,interval[1]*value
                result=add(result,(min(a,b),max(a,b)))
    return result


def geometry(path,axes):
    check('positive_edges',all(a!=b for a,b in zip(path,path[1:])))
    check('physical_box',all(axes[k][0]<=p[k]<=axes[k][-1] for p in path for k in range(3)))


def action_record(record,a,b,axes):
    """Check saved geometry and declared budget, without evaluating velocity."""
    cuts={Q(0),Q(1)};aligned=[]
    for k,axis in enumerate(axes):
        if a[k]==b[k]:
            if a[k] in axis[1:-1]:aligned.append([k,axis.index(a[k])])
        else:
            for x in axis[1:-1]:
                u=(x-a[k])/(b[k]-a[k])
                if 0<u<1:cuts.add(u)
    ordered=sorted(cuts);pieces=record['pieces'];length=bounds(record['length'])
    check('saved_length_squares',0<length[0] and length[0]**2<=squared(tuple(y-x for x,y in zip(a,b)))<=length[1]**2)
    check('saved_exact_cell_cuts',[(Q(p['u'][0]),Q(p['u'][1])) for p in pieces]==list(zip(ordered,ordered[1:])))
    check('saved_alignment',record['aligned']==aligned)
    for p in pieces:
        lo,hi=bounds(p['velocity_bounds']);rho=Q(p['rho'])
        check('saved_positive_velocity_and_series',0<lo<=hi and rho==(hi-lo)/(hi+lo) and 0<=rho<1 and p['series_degree']==(0 if rho==0 else 8))
    value=bounds(record['action']);check('positive_action_bound',value[0]>0);return value


def starting_evidence(saved,first,post,full,axes):
    """Independently resolve saved first-trial references, without integration."""
    before=[tuple(map(Q,p['candidate_exact_rational'])) for p in saved['coordinate_provenance']]
    prior=first['result'];path=[tuple(map(Q,p)) for p in prior['trial']];geometry(path,axes)
    check('eligible_second_start',len(path)==len(before) and path[0]==before[0] and path[-1]==before[-1]
          and all(axes[k][0]<p[k]<axes[k][-1] for p in path[1:-1] for k in range(3)))
    check('first_trial_reviewed_outcome',prior['status']=='diagnostic_trial_accepted' and prior['new_convergence_status'] is None
          and not prior['original_status_changed'] and post['status']=='completed_available_tangent_bounds' and post['ineligibility']==[])
    folder=FIRST/('event_'+str(first['event']));rounded=read(folder/'round/stdout.json')
    with (folder/'round/stdout.json').open() as stream:tokens=json.load(stream,parse_float=str,parse_int=str)
    check('first_round_output_join',rounded==prior['rounded_record'])
    flat=emitted(rounded['trial'],rounded['trial_hex'])
    check('first_round_exact_coordinates',flat==[x for p in path for x in p])
    coordinates=post['coordinate_provenance']
    check('second_start_coordinate_inventory',len(coordinates)==len(path) and full['coordinate_provenance']==coordinates
          and full['prior_starting_coordinate_provenance']==first['coordinate_provenance']==saved['coordinate_provenance'])
    for i,(p,row) in enumerate(zip(path,coordinates)):
        check('post_coordinate_identity',row['node']==i and tuple(map(Q,row['exact_rational']))==p
              and row['decimal_tokens']==tokens['trial'][3*i:3*i+3] and row['binary64_hex']==rounded['trial_hex'][3*i:3*i+3])
    # Resolve each recorded first-trial reference directly. Do not evaluate an
    # action or import the native loader/cache implementation.
    original={v['cache_id']:v for v in saved['unique_action_edge_records']};ids=saved['candidate_edge_record_ids']
    old=[];last={}
    for i,identity in enumerate(ids):
        record=original[identity];key=(before[i],before[i+1])
        check('original_action_geometry',tuple(map(Q,record['a_exact']))==key[0] and tuple(map(Q,record['b_exact']))==key[1])
        value=bounds(record['record']['action']);old.append(value)
        if key in last:check('original_duplicate_action',old[last[key]]==value)
        last[key]=i
    action=prior['action'];new=action['new_edge_records'];new_keys=[]
    for i,row in enumerate(new):
        key=(tuple(map(Q,row['a'])),tuple(map(Q,row['b'])))
        check('first_new_record_inventory',row['record_id']==i and key not in last)
        new_keys.append(key)
    check('first_unique_new_geometries',len(set(new_keys))==len(new_keys))
    total=point(0);old_total=point(0);paired=point(0);edges=[];sources=[];used=set()
    check('complete_first_edge_references',len(action['edge_joins'])==len(path)-1==len(old))
    for i,join in enumerate(action['edge_joins']):
        ref=join['trial_record'];key=(path[i],path[i+1]);source=ref['source']
        if source=='saved_start':
            index=ref['edge'];check('first_saved_start_last_index',key in last and index==last[key]);value=old[index]
        else:
            check('known_first_record_source',source=='new_trial');index=ref['record_id'];used.add(index)
            check('first_new_record_geometry',0<=index<len(new) and new_keys[index]==key)
            value=action_record(new[index]['record'],key[0],key[1],axes)
        check('first_reference_action',bounds(ref['action'])==value)
        change=point(0) if key==(before[i],before[i+1]) else sub(value,old[i])
        check('first_exact_ordered_cancellation',join['edge']==i and join['identical']==(key==(before[i],before[i+1]))
              and bounds(join['difference'])==change)
        total=add(total,value);old_total=add(old_total,old[i]);paired=add(paired,change);edges.append(value)
        sources.append({k:v for k,v in ref.items() if k!='action'})
    check('complete_first_action_sums',used==set(range(len(new))) and len(new)==action['action_edge_evaluations']==prior['action_edge_evaluations']
          and old_total==bounds(action['starting_action'])==bounds(saved['candidate_action']['exact_rational_bounds'])
          and total==bounds(action['trial_action'])==bounds(post['saved_trial_action'])
          and paired==bounds(action['paired_difference']) and sub(total,old_total)==bounds(action['full_difference']))
    check('complete_second_starting_action',full['starting_edge_record_ids']==sources and full['starting_action_record_joins']==action['edge_joins']
          and bounds(full['starting_candidate_action']['exact_rational_bounds'])==total)
    edge_components=post['tangent_edge_records'];nodes=post['free_node_components'];blocked=set();aligned=[]
    check('post_full_component_inventory',[v['edge'] for v in edge_components]==list(range(len(path)-1))
          and [v['node'] for v in nodes]==list(range(1,len(path)-1)))
    for i,(a,b,row) in enumerate(zip(path,path[1:],edge_components)):
        faces=[[k,axis.index(a[k])] for k,axis in enumerate(axes) if a[k]==b[k] and a[k] in axis[1:-1]]
        check('post_actual_single_face_mask',len(faces)<=1 and row['endpoint_nodes']==[i,i+1] and row['blocked_axes']==[k for k,index in faces])
        aligned.append(dict(edge=i,aligned_internal_faces=faces))
        for k,index in faces:blocked.update((node,k) for node in (i,i+1) if 0<node<len(path)-1)
    check('post_geometry_inventory',aligned==post['aligned_edge_inventory'] and sorted(blocked)==[tuple(v) for v in post['geometric_blocked_slots']]
          and full['unavailable_slots']==post['geometric_blocked_slots'])
    components=[None]+[[None if v is None else bounds(v) for v in p['components']] for p in nodes]+[None]
    check('post_fixed_endpoint_omission',edge_components[0]['components'][0] is None and edge_components[-1]['components'][1] is None)
    for i,row in enumerate(components[1:-1],1):
        check('post_raw_physical_axes',len(row)==3)
        for k,value in enumerate(row):check('post_geometric_slot_availability',(value is None)==((i,k) in blocked))
    return path,components,edge_components,edges,total


def main():
    check('fresh_review',not (HERE/'review.json').exists())
    approval=read(HERE/'source_review.json')
    check('independent_source_review',approval['status']=='passed' and approval['checker_sha256']==sha(Path(__file__)))
    prepared=read(RUN/'prepared.json');execution=read(RUN/'execution.json');summary=read(RUN/'summary.json')
    outer=read(RUN/'outer_reaping.json')
    check('review_terminal_pins',approval['native_summary_sha256']==sha(RUN/'summary.json') and approval['native_execution_sha256']==sha(RUN/'execution.json'))
    check('review_outer_pin',approval['outer_reaping_sha256']==sha(RUN/'outer_reaping.json'))
    check('owned_outer_reaping_receipt',outer['status']=='completed_and_reaped' and outer['tool_exit_code']==0 and outer['wrapper_process_absent']
          and outer['wrapper_pid']==execution['pid'] and outer['execution_sha256']==sha(RUN/'execution.json')
          and outer['summary_sha256']==sha(RUN/'summary.json') and outer['prepared_sha256']==sha(RUN/'prepared.json')
          and outer['prelaunch_review_sha256']==sha(RUN/'prelaunch_review.json'))
    check('terminal_wrapper',execution['status']==summary['status']=='completed_bounded_diagnostic' and execution['return_code']==0
          and execution['outputs_stable'] and execution['unsettled_groups']==[] and summary['error'] is None)
    prelaunch=read(RUN/'prelaunch_review.json')
    check('native_prelaunch',prelaunch['status']=='passed' and prelaunch['prepared_sha256']==sha(RUN/'prepared.json'))
    for record in (summary,execution):
        check('terminal_preparation',record['prepared_sha256']==sha(RUN/'prepared.json') and record['prelaunch_review_sha256']==sha(RUN/'prelaunch_review.json'))
    check('actual_parent_environment',execution['environment']==prepared['environment'])
    check('same_terminal_output_inventory',summary['output_sha256']==execution['output_sha256'])
    pins(ROOT,prepared['input_sha256']);pins(RUN,prepared['output_sha256']);pins(Path('/'),prepared['runtime_sha256'])
    pins(RUN,summary['output_sha256'])
    check('no_extra_work',all(summary[k]==0 for k in ('native_trace_calls','field_calls','tangent_integrals','optimizer_iterations')))
    check('fixed_settings',summary['settings']==prepared['settings']==dict(terms=8,subdivisions=1,bits=128))
    identities=read(RUN/'native_contexts.json')
    check('complete_terminal_contexts',summary['native_contexts']==execution['native_contexts']==outer['native_contexts']==identities)
    first_review=read(FIRST_REVIEW/'review.json');post_review=read(POST_REVIEW/'review.json')
    for base,review in ((FIRST,first_review),(POST,post_review)):
        check('passed_inherited_review',review['status']=='passed')
        for field,name in (('native_prepared_sha256','prepared.json'),('native_summary_sha256','summary.json'),
                           ('native_execution_sha256','execution.json'),('outer_reaping_sha256','outer_reaping.json')):
            check('inherited_review_terminal_hash',review[field]==sha(base/name))
        check('inherited_review_contexts',[dict(event=v['event'],station=v['station'],native_context=v['native_context'],catalog_uses=v['catalog_uses'])
              for v in review['cases']]==identities)
    receipt=read(POST_REVIEW/'execution_receipt.json')
    check('inherited_review_reaped',receipt['status']=='completed_and_reaped' and receipt['tool_exit_code']==0
          and receipt['review_sha256']==sha(POST_REVIEW/'review.json')
          and receipt['checker_sha256']==post_review['checker_sha256']==sha(POST_REVIEW/'check.py'))
    original_context={x['event']:x for x in read(START/'inputs/native_context.json')}
    catalog=rows(ROOT/'data/hayward/observations.csv');stations=rows(START/'inputs/stations.csv');events=rows(START/'inputs/trial_events.csv')
    model=read(START/'model_provenance.json');axes=tuple(tuple(map(Q,v)) for v in model['axes_exact_rational'])
    grid=rows(START/'inputs/trial_grid.csv');grid_by_xyz={xyz(v):Q(float(v['v'])) for v in grid}
    check('model_pin',model['recorded_grid_sha256']==sha(START/'inputs/trial_grid.csv'))
    commands=execution['commands'];reports=[];expected_commands=[];new_total=0
    check('two_case_roster',[v['event'] for v in identities]==[981,987] and [v['event'] for v in summary['cases']]==[981,987])
    for identity,short in zip(identities,summary['cases']):
        event=identity['event'];folder=RUN/('event_'+str(event));saved=read(START/('event_'+str(event)+'.json.gz'))
        full=read(folder/'result.json.gz');value=full['result'];context=identity['native_context']
        first_path=FIRST/('event_'+str(event))/'result.json.gz';first=read(first_path)
        post_path=POST/('event_'+str(event)+'.json.gz');post=read(post_path)
        chain=dict(first_trial_result_sha256=sha(first_path),first_trial_round_stdout_sha256=sha(first_path.parent/'round/stdout.json'),
                   post_step_result_sha256=sha(post_path),first_trial_summary_sha256=sha(FIRST/'summary.json'),
                   post_step_summary_sha256=sha(POST/'summary.json'),post_step_review_sha256=sha(POST_REVIEW/'review.json'),
                   post_step_review_receipt_sha256=sha(POST_REVIEW/'execution_receipt.json'))
        check('second_step_exact_chain',full['chain_provenance']==chain and post['prior_result_sha256']==sha(first_path))
        check('inherited_case_identity',first['event']==post['event']==event and first['station']==post['station']==160
              and first['native_context']==post['native_context']==context
              and first['catalog_uses']==post['catalog_uses']==identity['catalog_uses'])
        check('inherited_post_flags',post['original_convergence_flag']=='0' and post['candidate_convergence_status'] is None)
        check('post_comparison_preserved',full['post_step_comparison']==post['comparison'])
        audit=next(v for v in post_review['cases'] if v['event']==event)
        check('reviewed_post_norm_bounds',bounds(audit['post_squared_bounds'])==(Q(post['post_step_norm']['lower_squared']),Q(post['post_step_norm']['upper_squared']))
              and bounds(audit['pre_squared_bounds'])==(Q(post['pre_step_norm']['lower_squared']),Q(post['pre_step_norm']['upper_squared'])))
        check('full_original_native_context',context==original_context[event]==saved['native_context']==full['native_context']==short['native_context'])
        check('full_catalog_context',identity['catalog_uses']==full['catalog_uses']==short['catalog_uses'] and len(identity['catalog_uses'])==9)
        for use in identity['catalog_uses']:
            row=catalog[use['zero_based_observation_row']];check('original_catalog_row',row==use['original_row'])
            for side,epoch in use['epoch_joins'].items():
                k=int(row['station'] if side=='i' else row['station_j']);e=int(row[side])
                check('both_native_epoch_indices',epoch['station_index']==k and epoch['event_index']==e and epoch['receiver_native']==stations[k])
                prefix='metadata_epoch_' if side=='i' else 'metadata_epoch_j_'
                check('both_epoch_boundaries',all(row[prefix+end]==stations[k]['metadata_epoch_'+end] for end in ('start','end')))
                check('both_event_origin_ids',row['event_'+side+'_resource_id']==events[e]['event_resource_id'] and row['origin_'+side+'_resource_id']==events[e]['origin_resource_id'])
            check('catalog_use_pair',int(row[use['side']])==event and int(row['station'] if use['side']=='i' else row['station_j'])==160)
        check('preserved_flags',full['original_status']==context['original_status'] and context['original_status']['ray_converged']=='0'
              and context['original_status']['ray_derivatives_evaluated']=='0' and all(context['original_status']['source_d'+k]=='' for k in 'xyz')
              and full['candidate_convergence_status'] is None and short['candidate_convergence_status'] is None
              and value['new_convergence_status'] is None and not value['original_status_changed'])
        path,components,edge_components,starting_edges,starting_total=starting_evidence(saved,first,post,full,axes)
        check('fixed_current_state_endpoints',path[0]==xyz(context['source_native']) and path[-1]==xyz(context['receiver_native']))
        rhs=[];fixed=[]
        check('full_midpoint_inventory',len(value['midpoint_mapping'])==3*(len(path)-2))
        for i in range(1,len(path)-1):
            for k,v in enumerate(components[i]):
                left=edge_components[i-1]['components'][1][k];right=edge_components[i]['components'][0][k]
                check('complete_adjacent_tangent_sum',v==(None if left is None or right is None else add(bounds(left),bounds(right))))
                item=value['midpoint_mapping'][3*(i-1)+k]
                check('midpoint_slot_identity',item['node']==i and item['axis']==k and item['available']==(v is not None))
                converted=0.0 if v is None else float((v[0]+v[1])/2);rhs.append(converted);fixed.append(v is None)
                check('midpoint_binary64_rhs',float(item['metric_rhs']).hex()==converted.hex())
                if v is not None:
                    check('midpoint_exact_bounds',bounds(item['bounds'])==v and Q(item['midpoint'])==(v[0]+v[1])/2 and Q(item['exact_converted'])==Q(converted) and item['binary64_hex']==converted.hex())
        metric=read(folder/'metric/stdout.json');check('saved_metric_output',metric==value['metric'])
        flat=emitted(metric['direction'],metric['direction_hex'])
        check('direction_inventory',len(flat)==len(rhs) and all(not f or x==0 for f,x in zip(fixed,flat)))
        direction=[(Q(0),)*3]+[tuple(flat[i:i+3]) for i in range(0,len(flat),3)]+[(Q(0),)*3]
        check('full_recorded_direction',direction==[tuple(map(Q,p)) for p in value['direction']])
        weights=[Q(float(v)) for v in metric['weights']]
        check('positive_weight_and_pivot_inventory',len(weights)==len(path)-1 and all(w>0 for w in weights)
              and len(metric['pivots'])==len(flat) and all(math.isfinite(float(v)) and float(v)>0 for v in metric['pivots']))
        account=value['metric_exact_account'];energy=sum(w*squared(tuple(y-x for x,y in zip(a,b))) for w,a,b in zip(weights,direction,direction[1:]))
        check('exact_emitted_metric_energy',Q(account['exact_recorded_metric_energy'])==energy)
        check('exact_emitted_midpoint_slope',Q(account['exact_recorded_midpoint_slope'])==sum(Q(g)*d for g,d in zip(rhs,flat)))
        check('complete_residual_inventory',len(account['exact_recorded_residuals'])==len(flat))
        for i in range(1,len(path)-1):
            for k in range(3):
                slot=3*(i-1)+k;item=account['exact_recorded_residuals'][slot]
                residual=(weights[i-1]+weights[i])*direction[i][k]-weights[i-1]*direction[i-1][k]-weights[i]*direction[i+1][k]+Q(rhs[slot])
                check('principal_block_recorded_residual',item['node']==i and item['axis']==k and item['fixed']==fixed[slot] and Q(item['exact_recorded_equation_residual'])==residual)
        slope=contract(components,direction);check('complete_nominal_slope',bounds(value['nominal_slope'])==slope)
        tokens=[str(len(a)) for a in axes]+[str(len(path))]
        for axis in axes:tokens.extend(float(x).hex() for x in axis)
        tokens.extend(float(grid_by_xyz[x,y,z]).hex() for z in axes[2] for y in axes[1] for x in axes[0])
        tokens.extend(float(x).hex() for p in path for x in p);tokens.extend(x.hex() for x in rhs);tokens.extend(str(int(v)) for v in fixed)
        check('complete_metric_input_mapping',(folder/'metric/input.txt').read_text().split()==tokens)
        modes=['solve'];action=None;actual=None
        if slope[1]>=0:
            check('unresolved_nominal_no_trial',value['status']=='nominal_slope_unresolved' and value['rounded_trials']==0 and value['action_edge_evaluations']==0)
        else:
            modes.append('round');alpha=Q(float(value['alpha']));limit=Q(value['geometric_bound'])
            check('positive_nominal_bound',0<alpha<=1 and alpha<=limit and float(value['alpha']).hex()==value['alpha_hex'])
            for i,p in enumerate(path):check('bound_box_feasibility',all(axes[k][0]<=p[k]+limit*direction[i][k]<=axes[k][-1] for k in range(3)))
            for a,b,da,db in zip(path,path[1:],direction,direction[1:]):
                check('bound_half_edge_feasibility',4*limit*limit*squared(tuple(y-x for x,y in zip(da,db)))<=squared(tuple(y-x for x,y in zip(a,b))))
            if alpha<1:
                bits=struct.unpack('>Q',struct.pack('>d',float(alpha)))[0]
                next_value=struct.unpack('>d',struct.pack('>Q',bits+1))[0]
                check('largest_admissible_binary64_step',Q(next_value)>min(Q(1),limit))
            rounded=read(folder/'round/stdout.json');check('saved_round_output',rounded==value['rounded_record'])
            coordinates=emitted(rounded['trial'],rounded['trial_hex'])
            trial=[tuple(coordinates[i:i+3]) for i in range(0,len(coordinates),3)]
            check('rounded_node_inventory',len(trial)==len(path) and trial[0]==path[0] and trial[-1]==path[-1])
            geometry(trial,axes);displacement=[]
            for i,(p,q,d) in enumerate(zip(path,trial,direction)):
                if i not in (0,len(path)-1):
                    for k in range(3):
                        product=float(alpha)*float(d[k]);expected=float(p[k])+product
                        check('separate_binary64_multiply_add',q[k]==Q(expected))
                        check('fixed_unavailable_coordinate',components[i][k] is not None or q[k]==p[k])
                displacement.append(tuple(y-x for x,y in zip(p,q)))
            check('recorded_rounded_geometry',trial==[tuple(map(Q,p)) for p in value['trial']] and displacement==[tuple(map(Q,p)) for p in value['actual_displacement']])
            actual=contract(components,displacement);check('complete_actual_displacement_slope',actual==bounds(value['actual_displacement_slope']))
            tokens=[str(len(path)),float(alpha).hex()]+[float(x).hex() for p in path for x in p]+[float(x).hex() for d in direction for x in d]
            check('complete_round_input_mapping',(folder/'round/input.txt').read_text().split()==tokens)
            if actual[1]>=0:
                check('unresolved_actual_no_action',value['status']=='actual_displacement_slope_unresolved' and value['action_edge_evaluations']==0)
            else:
                action=value['action'];cache={};starting=point(0)
                for e,a in enumerate(starting_edges):
                    key=(path[e],path[e+1])
                    if key in cache:check('identical_starting_bounds',cache[key][0]==a)
                    cache[key]=(a,'saved_start',e);starting=add(starting,a)
                check('starting_full_sum',starting==starting_total==bounds(action['starting_action']))
                new=action['new_edge_records'];used=0;total=point(0);paired=point(0);same=0
                check('complete_trial_edge_joins',len(action['edge_joins'])==len(path)-1)
                for e,(a,b,c,d) in enumerate(zip(path,path[1:],trial,trial[1:])):
                    key=(c,d)
                    if key not in cache:
                        row=new[used];check('new_edge_ordered_geometry',row['record_id']==used and tuple(map(Q,row['a']))==c and tuple(map(Q,row['b']))==d)
                        value_bound=action_record(row['record'],c,d,axes);cache[key]=(value_bound,'new_trial',used);used+=1
                    after,source,index=cache[key];before=starting_edges[e]
                    change=point(0) if (a,b)==key else sub(after,before);paired=add(paired,change);total=add(total,after)
                    join=action['edge_joins'][e];record=join['trial_record'];same+=int((a,b)==key)
                    check('exact_ordered_edge_cancellation',join['edge']==e and join['identical']==((a,b)==key) and bounds(join['difference'])==change)
                    check('reused_or_new_record_join',bounds(record['action'])==after and record['source']==source and record['edge' if source=='saved_start' else 'record_id']==index)
                check('unique_new_edge_count',used==len(new)==action['action_edge_evaluations']==value['action_edge_evaluations']<=len(path)-1)
                full_difference=sub(total,starting);rhs=Q(float('1e-4'))*alpha*slope[0]
                check('trial_full_and_paired_sums',total==bounds(action['trial_action']) and paired==bounds(action['paired_difference']) and full_difference==bounds(action['full_difference']))
                check('paired_full_consistency',max(paired[0],full_difference[0])<=min(paired[1],full_difference[1]))
                check('conservative_armijo_arithmetic',Q(action['nominal_armijo_rhs_lower'])==rhs and action['conservative_nominal_armijo']==(paired[1]<=rhs))
                check('action_classifications',action['strict_decrease']==(paired[1]<0) and action['strict_increase']==(paired[0]>0)
                      and value['status']==('diagnostic_trial_accepted' if paired[1]<=rhs else 'diagnostic_trial_not_accepted'))
                new_total+=used
                action=dict(starting=starting,trial=total,paired_difference=paired,full_difference=full_difference,nominal_armijo_rhs_lower=rhs,
                            conservative_nominal_armijo=paired[1]<=rhs,new_edges=used,identical_ordered_edges=same)
        check('case_summary_join',short['status']==value['status'] and short['metric_solves']==value['metric_solves']==1
              and short['rounded_trials']==value['rounded_trials']==len(modes)-1 and short['action_edge_evaluations']==value['action_edge_evaluations'])
        check('case_result_hash',short['result_file']==str((folder/'result.json.gz').relative_to(RUN)) and short['result_sha256']==sha(folder/'result.json.gz'))
        for mode in modes:
            d=folder/('metric' if mode=='solve' else 'round');expected_commands.append((event,mode))
            item=next(v for v in commands if v['event']==event and v['mode']==mode)
            check('reaped_helper',item['return_code']==0 and item['child_reaped'] and item['pid']>0 and not item.get('cleanup'))
            check('exact_helper_command',item['command']==[str(CONTROL/'build/metric_step'),mode,str(d/'input.txt')])
            pins(d,item['output_sha256'])
            for name in ('input.txt','stdout.json','stderr.log'):
                attached=read(d/(name+'.identifiers.json'))
                check('helper_identifiers',attached['native_context']==context and attached['catalog_uses']==identity['catalog_uses'] and attached['candidate_convergence_status'] is None)
                check('helper_evidence_binding',attached['evidence_sha256']==prepared['input_sha256'] and attached['prepared_sha256']==sha(RUN/'prepared.json')
                      and attached['chain_provenance']==chain and attached['unavailable_slots']==full['unavailable_slots'])
                check('declared_file_binding',attached['expected_file']==str((d/name).relative_to(ROOT)) and attached['input_file']==str((d/'input.txt').relative_to(ROOT))
                      and attached['input_file_sha256']==sha(d/'input.txt') and attached['file_sha256']==(sha(d/'input.txt') if name=='input.txt' else None))
        attached=read(folder/'result.json.gz.identifiers.json')
        check('result_identifiers',attached['native_context']==context and attached['catalog_uses']==identity['catalog_uses'] and attached['evidence_sha256']==prepared['input_sha256']
              and attached['file_sha256'] is None and attached['expected_file']==str((folder/'result.json.gz').relative_to(ROOT))
              and attached['chain_provenance']==chain and attached['unavailable_slots']==full['unavailable_slots'])
        reports.append(dict(event=event,station=160,native_context=context,catalog_uses=identity['catalog_uses'],status=value['status'],
                            original_convergence_flag='0',candidate_convergence_status=None,nominal_slope=slope,actual_displacement_slope=actual,
                            alpha=value.get('alpha'),alpha_hex=value.get('alpha_hex'),exact_emitted_metric_energy=energy,
                            units=dict(nominal_slope='s per dimensionless step',actual_displacement_slope='s',metric_energy='s',action='s'),
                            action=action,metric_solves=1,rounded_trials=len(modes)-1,chain_provenance=chain,
                            starting_post_step_comparison=post['comparison']))
    check('exact_command_inventory',[(v['event'],v['mode']) for v in commands]==expected_commands and len(commands)<=4)
    check('outer_helper_count',outer['helper_calls_reaped']==len(commands))
    check('bounded_action_inventory',new_total<=2058)
    actual_files={str(p.relative_to(RUN)) for name in ('event_981','event_987') for p in (RUN/name).rglob('*') if p.is_file()}
    check('no_uninventoried_case_files',actual_files==set(summary['output_sha256']))
    pins(ROOT,prepared['input_sha256']);pins(RUN,prepared['output_sha256']);pins(RUN,summary['output_sha256'])
    review=dict(status='passed',reviewer='ray_math_review',checker_sha256=sha(Path(__file__)),source_review_sha256=sha(HERE/'source_review.json'),
                native_prepared_sha256=sha(RUN/'prepared.json'),native_summary_sha256=sha(RUN/'summary.json'),native_execution_sha256=sha(RUN/'execution.json'),
                outer_reaping_sha256=sha(RUN/'outer_reaping.json'),first_step_review_sha256=sha(FIRST_REVIEW/'review.json'),
                post_step_review_sha256=sha(POST_REVIEW/'review.json'),
                check_counts=CHECKS,cases=reports,total_new_action_edges=new_total,
                limitations=['Saved-output exact rational/binary64 algebra only; no action, tangent or metric recalculation.',
                             'Before-launch sidecar ordering is established by the frozen reviewed source; saved files alone do not establish creation times.',
                             'Original false flags and null candidate convergence are preserved. No first-arrival, endpoint/source/model derivative or optimization convergence conclusion.'])
    with (HERE/'review.json').open('x') as stream:json.dump(encoded(review),stream,indent=2,sort_keys=True,allow_nan=False);stream.write('\n')


if __name__=='__main__':main()
