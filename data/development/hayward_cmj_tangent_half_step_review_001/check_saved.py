#!/usr/bin/env python3
"""Saved half-step algebra only; reuse reviewed stdlib checker functions."""
import hashlib
import importlib.util
import json
from pathlib import Path
from fractions import Fraction as Q
import sys

sys.dont_write_bytecode=True

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
RUN=ROOT/'data/development/hayward_cmj_tangent_half_step_001'
PRIOR=ROOT/'data/development/hayward_cmj_tangent_step_002'
SHARED=ROOT/'data/development/hayward_cmj_tangent_step_review_002'
POST=ROOT/'data/development/hayward_cmj_post_step_tangent_001'
START=ROOT/'data/development/hayward_cmj_face_action_001'
FIRST=ROOT/'data/development/hayward_cmj_tangent_step_001'
CONTROL=ROOT/'data/development/cmj_tangent_step_source_002'


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''):h.update(block)
    return h.hexdigest()


def read(path):
    with path.open() as stream:return json.load(stream)


def main():
    assert not (HERE/'review.json').exists(),'Preserve existing review'
    approval=read(HERE/'source_review.json');prepared=read(RUN/'prepared.json')
    assert approval['status']=='passed' and approval['checker_sha256']==sha(Path(__file__))
    shared=SHARED/'check_saved.py'
    assert sha(shared)==prepared['input_sha256'][str(shared.relative_to(ROOT))]
    spec=importlib.util.spec_from_file_location('saved_step002_checker',str(shared))
    c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
    check=c.check;read_saved=c.read;bounds=c.bounds;add=c.add;sub=c.sub;point=c.point
    summary=read(RUN/'summary.json');execution=read(RUN/'execution.json');outer=read(RUN/'outer_reaping.json')
    check('approval_terminal_hashes',approval['native_summary_sha256']==sha(RUN/'summary.json')
          and approval['native_execution_sha256']==sha(RUN/'execution.json') and approval['outer_reaping_sha256']==sha(RUN/'outer_reaping.json'))
    check('terminal_half_step',summary['status']==execution['status']=='completed_bounded_half_step_diagnostic' and execution['return_code']==0
          and execution['outputs_stable'] and execution['unsettled_groups']==[] and summary['error'] is None)
    check('root_outer_reaped',outer['status']=='completed_and_reaped' and outer['tool_exit_code']==0 and outer['wrapper_process_absent']
          and outer['wrapper_pid']==execution['pid'] and outer['prepared_sha256']==sha(RUN/'prepared.json')
          and outer['prelaunch_review_sha256']==sha(RUN/'prelaunch_review.json')
          and outer['execution_sha256']==sha(RUN/'execution.json') and outer['summary_sha256']==sha(RUN/'summary.json'))
    check('prelaunch_review',read(RUN/'prelaunch_review.json')['status']=='passed'
          and read(RUN/'prelaunch_review.json')['prepared_sha256']==sha(RUN/'prepared.json'))
    for record in (summary,execution):
        check('terminal_preparation',record['prepared_sha256']==sha(RUN/'prepared.json')
              and record['prelaunch_review_sha256']==sha(RUN/'prelaunch_review.json'))
    check('stable_output_inventory',summary['output_sha256']==execution['output_sha256'])
    c.pins(ROOT,prepared['input_sha256']);c.pins(RUN,prepared['output_sha256']);c.pins(Path('/'),prepared['runtime_sha256']);c.pins(RUN,summary['output_sha256'])
    check('environment_and_budget',execution['environment']==prepared['environment'] and summary['settings']==prepared['settings']==dict(terms=8,subdivisions=1,bits=128)
          and summary['budget']==dict(metric_solves_maximum=0,rounded_trials_maximum=2,new_action_edges_maximum=2058))
    check('no_extra_calls',all(summary[k]==0 for k in ('native_trace_calls','field_calls','tangent_integrals','optimizer_iterations')))
    previous_review=read(SHARED/'review.json');receipt=read(SHARED/'execution.json')
    check('passed_previous_review',previous_review['status']=='passed' and receipt['status']=='passed' and receipt['return_code']==0 and receipt['child_reaped']
          and receipt['output_sha256']['review.json']==sha(SHARED/'review.json') and receipt['checker_sha256']==previous_review['checker_sha256']==sha(shared))
    for field,name in (('native_prepared_sha256','prepared.json'),('native_summary_sha256','summary.json'),
                       ('native_execution_sha256','execution.json'),('outer_reaping_sha256','outer_reaping.json')):
        check('reviewed_full_step_chain',previous_review[field]==sha(PRIOR/name))
    identities=read(RUN/'native_contexts.json')
    check('full_native_roster',identities==read(PRIOR/'native_contexts.json')==summary['native_contexts']==execution['native_contexts']==outer['native_contexts']
          and [v['event'] for v in identities]==[981,987] and [v['event'] for v in summary['cases']]==[981,987])
    check('previous_review_full_context',[dict(event=v['event'],station=v['station'],native_context=v['native_context'],catalog_uses=v['catalog_uses'])
          for v in previous_review['cases']]==identities)
    axes=tuple(tuple(map(Q,a)) for a in read(START/'model_provenance.json')['axes_exact_rational'])
    reports=[];total_new=0;commands=execution['commands'];expected_commands=[]
    for identity,short in zip(identities,summary['cases']):
        event=identity['event'];folder=RUN/('event_'+str(event));full=read_saved(folder/'result.json.gz');value=full['result']
        prior_path=PRIOR/('event_'+str(event))/'result.json.gz';prior=read_saved(prior_path);old=prior['result']
        first=read_saved(FIRST/('event_'+str(event))/'result.json.gz');post=read_saved(POST/('event_'+str(event)+'.json.gz'))
        saved=read_saved(START/('event_'+str(event)+'.json.gz'))
        path,components,edge_components,starting_edges,starting_total=c.starting_evidence(saved,first,post,prior,axes)
        for i,row in enumerate(components[1:-1],1):
            for k,value_bound in enumerate(row):
                left=edge_components[i-1]['components'][1][k];right=edge_components[i]['components'][0][k]
                check('complete_raw_incident_sum',value_bound==(None if left is None or right is None else add(bounds(left),bounds(right))))
        check('half_start_is_retained_path',full['coordinate_provenance']==prior['coordinate_provenance']
              and full['starting_candidate_action']==prior['starting_candidate_action']
              and full['starting_edge_record_ids']==prior['starting_edge_record_ids'] and full['starting_action_record_joins']==prior['starting_action_record_joins'])
        check('native_and_catalog_identity',full['event']==short['event']==event and full['station']==short['station']==160
              and full['native_context']==short['native_context']==prior['native_context']==identity['native_context']
              and full['catalog_uses']==short['catalog_uses']==prior['catalog_uses']==identity['catalog_uses'] and len(full['catalog_uses'])==9)
        status=identity['native_context']['original_status']
        check('unchanged_flags',full['original_status']==status and status['ray_converged']==status['ray_derivatives_evaluated']=='0'
              and all(status['source_d'+k]=='' for k in 'xyz') and full['candidate_convergence_status'] is None
              and value['new_convergence_status'] is None and not value['original_status_changed']
              and short['original_convergence_flag']=='0' and short['candidate_convergence_status'] is None)
        metric_path=prior_path.parent/'metric/stdout.json';metric=read_saved(metric_path)
        flat=c.emitted(metric['direction'],metric['direction_hex']);direction=[(Q(0),)*3]+[tuple(flat[i:i+3]) for i in range(0,len(flat),3)]+[(Q(0),)*3]
        check('same_saved_direction',metric==old['metric'] and len(flat)==3*(len(path)-2)
              and direction==[tuple(map(Q,p)) for p in old['direction']]==[tuple(map(Q,p)) for p in value['direction']])
        slope=c.contract(components,direction)
        check('same_complete_nominal_slope',slope==bounds(old['nominal_slope'])==bounds(value['nominal_slope']) and slope[1]<0)
        alpha=Q(1,2);limit=Q(old['geometric_bound'])
        check('fixed_half_step',summary['alpha']==prepared['alpha']==value['alpha']==0.5 and summary['alpha_hex']==prepared['alpha_hex']==value['alpha_hex']==float(.5).hex()
              and 0<alpha<=limit and Q(value['geometric_bound'])==limit)
        rejected=full['rejected_full_step']
        check('positive_full_step_preserved',old['status']==rejected['status']=='diagnostic_trial_not_accepted' and old['alpha']==rejected['alpha']==1.0
              and bounds(old['action']['paired_difference'])==bounds(rejected['paired_difference']) and bounds(rejected['paired_difference'])[0]>0
              and rejected['result_file']==str(prior_path.relative_to(ROOT)) and rejected['result_sha256']==sha(prior_path))
        chain=dict(prior['chain_provenance'],rejected_full_step_result_sha256=sha(prior_path),saved_direction_output_sha256=sha(metric_path),
                   full_step_review_sha256=sha(SHARED/'review.json'))
        check('complete_half_step_chain',full['chain_provenance']==chain and full['unavailable_slots']==prior['unavailable_slots']
              and full['post_step_comparison']==prior['post_step_comparison'])
        rounded=read_saved(folder/'round/stdout.json');check('raw_round_output',rounded==value['rounded_record'])
        coordinates=c.emitted(rounded['trial'],rounded['trial_hex']);trial=[tuple(coordinates[i:i+3]) for i in range(0,len(coordinates),3)]
        check('rounded_inventory_endpoints',len(trial)==len(path) and trial[0]==path[0] and trial[-1]==path[-1]);c.geometry(trial,axes)
        displacement=[]
        for i,(p,q,d) in enumerate(zip(path,trial,direction)):
            for k in range(3):
                product=float(alpha)*float(d[k]);expected=float(p[k])+product
                check('same_two_operation_rounding',q[k]==Q(expected))
                if i not in (0,len(path)-1):check('fixed_unavailable_coordinate',components[i][k] is not None or q[k]==p[k])
            displacement.append(tuple(y-x for x,y in zip(p,q)))
        check('saved_trial_and_displacement',trial==[tuple(map(Q,p)) for p in value['trial']] and displacement==[tuple(map(Q,p)) for p in value['actual_displacement']])
        actual=c.contract(components,displacement);check('complete_actual_slope',actual==bounds(value['actual_displacement_slope']))
        tokens=[str(len(path)),float(alpha).hex()]+[float(x).hex() for p in path for x in p]+[float(x).hex() for p in direction for x in p]
        check('exact_round_input',(folder/'round/input.txt').read_text().split()==tokens)
        action=None;new_count=0
        if actual[1]>=0:
            check('unresolved_displacement_no_action',value['status']=='actual_displacement_slope_unresolved' and value['action_edge_evaluations']==0)
        else:
            record=value['action'];cache={};start=point(0);total=point(0);paired=point(0);same=0
            for i,b in enumerate(starting_edges):
                key=(path[i],path[i+1])
                if key in cache:check('identical_start_bounds',cache[key][0]==b)
                cache[key]=(b,'saved_start',i);start=add(start,b)
            new=record['new_edge_records'];check('complete_half_edge_joins',len(record['edge_joins'])==len(path)-1)
            for i,(a,b,x,y) in enumerate(zip(path,path[1:],trial,trial[1:])):
                key=(x,y)
                if key not in cache:
                    row=new[new_count];check('half_new_edge_geometry',row['record_id']==new_count and tuple(map(Q,row['a']))==x and tuple(map(Q,row['b']))==y)
                    cache[key]=(c.action_record(row['record'],x,y,axes),'new_trial',new_count);new_count+=1
                after,source,index=cache[key];change=point(0) if (a,b)==key else sub(after,starting_edges[i]);join=record['edge_joins'][i];ref=join['trial_record']
                check('half_exact_cache_and_cancellation',join['edge']==i and join['identical']==((a,b)==key) and bounds(join['difference'])==change
                      and bounds(ref['action'])==after and ref['source']==source and ref['edge' if source=='saved_start' else 'record_id']==index)
                total=add(total,after);paired=add(paired,change);same+=int((a,b)==key)
            check('complete_half_action_sums',start==starting_total==bounds(record['starting_action']) and total==bounds(record['trial_action'])
                  and paired==bounds(record['paired_difference']) and sub(total,start)==bounds(record['full_difference']))
            full_difference=sub(total,start)
            check('full_paired_overlap',max(paired[0],full_difference[0])<=min(paired[1],full_difference[1]))
            rhs=Q(float('1e-4'))*alpha*slope[0]
            check('unchanged_conservative_armijo',Q(record['nominal_armijo_rhs_lower'])==rhs and record['conservative_nominal_armijo']==(paired[1]<=rhs)
                  and value['status']==('diagnostic_trial_accepted' if paired[1]<=rhs else 'diagnostic_trial_not_accepted'))
            check('half_action_classifications',record['strict_decrease']==(paired[1]<0) and record['strict_increase']==(paired[0]>0))
            check('half_new_edge_inventory',new_count==len(new)==record['action_edge_evaluations']==value['action_edge_evaluations']<=len(path)-1)
            action=dict(starting=start,trial=total,paired_difference=paired,nominal_armijo_rhs_lower=rhs,
                        conservative_nominal_armijo=paired[1]<=rhs,new_edges=new_count,identical_ordered_edges=same)
        total_new+=new_count
        check('case_summary',short['status']==value['status'] and short['metric_solves']==value['metric_solves']==0
              and short['rounded_trials']==value['rounded_trials']==1 and short['action_edge_evaluations']==new_count
              and short['result_file']==str((folder/'result.json.gz').relative_to(RUN)) and short['result_sha256']==sha(folder/'result.json.gz'))
        item=next(v for v in commands if v['event']==event);expected_commands.append((event,'round'))
        check('no_new_metric_files',not (folder/'metric').exists())
        check('owned_round_only',item['station']==160 and item['mode']=='round' and item['return_code']==0 and item['child_reaped'] and not item.get('cleanup')
              and item['command']==[str(CONTROL/'build/metric_step'),'round',str(folder/'round/input.txt')])
        c.pins(folder/'round',item['output_sha256'])
        for file in (folder/'result.json.gz',folder/'round/input.txt',folder/'round/stdout.json',folder/'round/stderr.log'):
            attached=read_saved(Path(str(file)+'.identifiers.json'))
            check('complete_numeric_sidecar',attached['native_context']==identity['native_context'] and attached['catalog_uses']==identity['catalog_uses']
                  and attached['chain_provenance']==chain and attached['unavailable_slots']==full['unavailable_slots']
                  and attached['evidence_sha256']==prepared['input_sha256'] and attached['prepared_sha256']==sha(RUN/'prepared.json')
                  and attached['expected_file']==str(file.relative_to(ROOT)) and attached['candidate_convergence_status'] is None)
            if file.parent.name=='round':
                check('declared_input_sidecar',attached['input_file']==str((folder/'round/input.txt').relative_to(ROOT))
                      and attached['input_file_sha256']==sha(folder/'round/input.txt') and attached['file_sha256']==(sha(file) if file.name=='input.txt' else None))
            else:check('declared_result_sidecar',attached['file_sha256'] is None)
        reports.append(dict(identity,status=value['status'],original_convergence_flag='0',candidate_convergence_status=None,
                            alpha=alpha,nominal_slope=slope,actual_displacement_slope=actual,action=action,
                            metric_solves=0,rounded_trials=1,chain_provenance=chain,units=dict(action='s',nominal_slope='s per dimensionless step',actual_displacement_slope='s')))
    check('fixed_command_and_action_inventory',[(v['event'],v['mode']) for v in commands]==expected_commands and len(commands)==outer['helper_calls_reaped']==2 and total_new<=2058)
    files={str(p.relative_to(RUN)) for e in (981,987) for p in (RUN/('event_'+str(e))).rglob('*') if p.is_file()}
    check('no_unlisted_native_outputs',files==set(summary['output_sha256']))
    c.pins(ROOT,prepared['input_sha256']);c.pins(RUN,prepared['output_sha256']);c.pins(RUN,summary['output_sha256'])
    result=dict(status='passed',reviewer='ray_math_review',checker_sha256=sha(Path(__file__)),shared_checker_sha256=sha(shared),
                source_review_sha256=sha(HERE/'source_review.json'),native_prepared_sha256=sha(RUN/'prepared.json'),
                native_summary_sha256=sha(RUN/'summary.json'),native_execution_sha256=sha(RUN/'execution.json'),outer_reaping_sha256=sha(RUN/'outer_reaping.json'),
                previous_step_review_sha256=sha(SHARED/'review.json'),check_counts=c.CHECKS,cases=reports,total_new_action_edges=total_new,
                limitations=['Saved identities, binary64/rational algebra and terminal receipts only; no native numerical helper or integration.',
                             'The saved metric direction is bound to step002 review; no second full metric audit or new solve.',
                             'No post-half-step gradient, normal stationarity, minimum, first-arrival or source/model derivative conclusion.'])
    with (HERE/'review.json').open('x') as stream:json.dump(c.encoded(result),stream,indent=2,sort_keys=True,allow_nan=False);stream.write('\n')


if __name__=='__main__':main()
