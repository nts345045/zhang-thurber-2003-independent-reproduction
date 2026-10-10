#!/usr/bin/env python3
"""One fixed half-step per saved direction; no new metric or tangent work."""
import datetime
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
PREVIOUS=ROOT/'data/development/hayward_cmj_tangent_step_002'
PREVIOUS_REVIEW=ROOT/'data/development/hayward_cmj_tangent_step_review_002'
C=ROOT/'data/development/cmj_tangent_step_source_002'
SETTINGS=dict(terms=8,subdivisions=1,bits=128)
ALPHA=0.5


def require(ok,message):
    if not ok:raise ValueError(message)


def now():return datetime.datetime.utcnow().isoformat()+'Z'


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''):h.update(block)
    return h.hexdigest()


def read(path):
    with path.open() as stream:return json.load(stream)


def main():
    prepared=read(HERE/'prepared.json');approval=read(HERE/'prelaunch_review.json')
    require(approval.get('status')=='passed' and approval.get('prepared_sha256')==sha(HERE/'prepared.json'),'Independent prelaunch review required')
    def verify():
        for base,pins in ((ROOT,prepared['input_sha256']),(HERE,prepared['output_sha256'])):
            for name,digest in pins.items():require(sha(base/name)==digest,'Changed pinned file: '+name)
        for name,digest in prepared['runtime_sha256'].items():require(sha(name)==digest,'Changed runtime: '+name)
    verify()
    require(prepared['settings']==SETTINGS and prepared['alpha']==ALPHA and prepared['alpha_hex']==ALPHA.hex(),'Fixed half-step settings')
    controls=read(C/'summary.json');control_review=read(C/'review.json')
    require(controls['status']==control_review['status']=='passed' and control_review['summary_sha256']==sha(C/'summary.json')
            and control_review['binary_sha256']==sha(C/'build/metric_step'),'Unchanged reviewed round binary and controls')
    review=read(PREVIOUS_REVIEW/'review.json');receipt=read(PREVIOUS_REVIEW/'execution.json')
    require(review['status']=='passed','Independent full-step readback')
    for field,name in (('native_prepared_sha256','prepared.json'),('native_summary_sha256','summary.json'),
                       ('native_execution_sha256','execution.json'),('outer_reaping_sha256','outer_reaping.json')):
        require(review[field]==sha(PREVIOUS/name),'Reviewed full-step terminal pin: '+name)
    require(receipt['status']=='passed' and receipt['return_code']==0 and receipt['child_reaped']
            and receipt['output_sha256']['review.json']==sha(PREVIOUS_REVIEW/'review.json')
            and receipt['checker_sha256']==review['checker_sha256']==sha(PREVIOUS_REVIEW/'check_saved.py'),'Reaped full-step review')
    summary=read(PREVIOUS/'summary.json');execution=read(PREVIOUS/'execution.json');outer=read(PREVIOUS/'outer_reaping.json')
    require(summary['status']==execution['status']=='completed_bounded_diagnostic' and execution['return_code']==0
            and execution['outputs_stable'] and not execution['unsettled_groups'] and summary['error'] is None,'Terminal full-step wrapper')
    require(outer['status']=='completed_and_reaped' and outer['tool_exit_code']==0 and outer['wrapper_process_absent']
            and outer['summary_sha256']==sha(PREVIOUS/'summary.json') and outer['execution_sha256']==sha(PREVIOUS/'execution.json'),'Reaped full-step wrapper')
    require(summary['output_sha256']==execution['output_sha256'],'Full-step output inventory')
    for name,digest in summary['output_sha256'].items():require(sha(PREVIOUS/name)==digest,'Changed full-step output: '+name)
    identifiers=read(HERE/'native_contexts.json')
    require(identifiers==read(PREVIOUS/'native_contexts.json')==summary['native_contexts']==outer['native_contexts']
            and [v['event'] for v in identifiers]==[981,987],'Exact two-case native roster')
    require([dict(event=v['event'],station=v['station'],native_context=v['native_context'],catalog_uses=v['catalog_uses'])
             for v in review['cases']]==identifiers,'Full-step review native/catalog joins')
    for name in ('execution.json','summary.json','event_981','event_987'):require(not (HERE/name).exists(),'Preserve prior output: '+name)
    os.environ.update(prepared['environment'])
    # This frozen module imports only stdlib at load time. Its load_inputs()
    # performs saved-data joins, not a metric, gradient or integration call.
    spec=importlib.util.spec_from_file_location('saved_step002_loader',str(PREVIOUS/'run.py'))
    base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
    require(Path(base.__file__).resolve()==PREVIOUS/'run.py','Frozen saved-data loader')
    save=base.save;load=base.read;interval=base.interval
    group_members=base.group_members;stop_group=base.stop_group
    ledger=dict(status='running',pid=os.getpid(),started_utc=now(),commands=[],native_contexts=identifiers,
                prepared_sha256=sha(HERE/'prepared.json'),prelaunch_review_sha256=sha(HERE/'prelaunch_review.json'),
                input_sha256=prepared['input_sha256'],runtime_sha256=prepared['runtime_sha256'],
                environment={k:os.environ[k] for k in prepared['environment']})
    def update():
        tmp=HERE/'execution.json.new';tmp.write_text(json.dumps(ledger,indent=2,sort_keys=True,allow_nan=False)+'\n');tmp.replace(HERE/'execution.json')
    def interrupted(sig,unused):raise SystemExit(128+sig)
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    update();unsettled=[];completed=[];current=None;answer=None;code=1
    try:
        grid,cases=base.load_inputs();verify()
        require([dict(event=v['event'],station=v['station'],native_context=v['native_context'],catalog_uses=v['catalog_uses']) for v in cases]==identifiers,
                'Same retained accepted first-step paths and complete native context')
        sys.path.insert(0,str(C/'source'))
        from diagnostics import tangent_metric_step as m
        from diagnostics import trilinear_action_bounds as t
        for name in ('tangent_metric_step','trilinear_action_bounds','check_native_interface_support','first_arrival_1d_precise_turn_reference'):
            require(Path(sys.modules['diagnostics.'+name].__file__).resolve()==C/'source/diagnostics'/(name+'.py'),'Frozen numerical import')
        for case in cases:
            event=case['event'];prior_path=PREVIOUS/('event_'+str(event))/'result.json.gz';prior=load(prior_path);old=prior['result']
            require(prior['event']==event and prior['station']==160 and prior['native_context']==case['native_context']
                    and prior['catalog_uses']==case['catalog_uses'] and prior['original_status']==case['original_status'],'Full-step case identity')
            require(prior['coordinate_provenance']==case['coordinate_provenance'] and prior['starting_candidate_action']==base.encoded(case['candidate_action'])
                    and prior['starting_edge_record_ids']==case['candidate_edge_record_ids']
                    and prior['starting_action_record_joins']==case['starting_action_record_joins'],'Identical retained starting path/action cache')
            require(prior['candidate_convergence_status'] is None and old['new_convergence_status'] is None and not old['original_status_changed']
                    and old['status']=='diagnostic_trial_not_accepted' and old['alpha']==1.0 and old['alpha_hex']==float(1).hex()
                    and interval(old['action']['paired_difference'])[0]>0 and old['action']['strict_increase'],'Preserved resolved positive-action alpha-one rejection')
            metric_path=prior_path.parent/'metric/stdout.json';metric=load(metric_path)
            require(metric==old['metric'],'Saved direction output binding')
            flat=m.emitted(metric['direction'],metric['direction_hex'])
            require(len(flat)==3*(len(case['path'])-2),'Complete saved direction')
            direction=[(Q(0),)*3]+[tuple(flat[i:i+3]) for i in range(0,len(flat),3)]+[(Q(0),)*3]
            require(direction==[tuple(map(Q,p)) for p in old['direction']],'Exact same binary64 direction; no solve')
            slope=m.contraction(case['components'],direction);bound=Q(old['geometric_bound'])
            require(slope==interval(old['nominal_slope']) and slope[1]<0 and 0<Q(ALPHA)<=bound,'Same complete negative nominal slope and feasible half-step')
            current=HERE/('event_'+str(event));current.mkdir()
            chain=dict(case['chain_provenance'],rejected_full_step_result_sha256=sha(prior_path),
                       saved_direction_output_sha256=sha(metric_path),full_step_review_sha256=sha(PREVIOUS_REVIEW/'review.json'))
            identity=dict(event=event,station=160,native_context=case['native_context'],catalog_uses=case['catalog_uses'],
                          original_status=case['original_status'],candidate_convergence_status=None,chain_provenance=chain,
                          coordinate_basis='Retained accepted first-step path; never the rejected alpha-one trial',
                          node_count=len(case['path']),node_order='Source 0 through fixed receiver n-1; physical xyz',
                          interior_slot_order='node 1..n-2, then x,y,z; unavailable slots fixed',edge_order='edge e joins nodes e,e+1',
                          unavailable_slots=case['unavailable_slots'],selected_near_face_nodes=case['selected_near_face_nodes'],
                          selected_near_face_role='Historical original selection; current availability comes from exact starting geometry',
                          evidence_sha256=prepared['input_sha256'],prepared_sha256=sha(HERE/'prepared.json'))
            result_path=current/'result.json.gz'
            save(current/'result.json.gz.identifiers.json',dict(identity,expected_file=str(result_path.relative_to(ROOT)),file_sha256=None,
                 role='One separately bounded half-step or preserved failure; final byte hashes follow reap'))
            value=dict(status='unusable_rounded_trial',metric_solves=0,rounded_trials=0,action_edge_evaluations=0,
                       alpha=ALPHA,alpha_hex=ALPHA.hex(),geometric_bound=bound,direction=direction,nominal_slope=slope,
                       new_convergence_status=None,original_status_changed=False)
            answer=dict(identity,coordinate_provenance=case['coordinate_provenance'],starting_candidate_action=case['candidate_action'],
                        starting_edge_record_ids=case['candidate_edge_record_ids'],starting_action_record_joins=case['starting_action_record_joins'],
                        post_step_comparison=case['post_step_comparison'],settings=SETTINGS,
                        rejected_full_step=dict(result_file=str(prior_path.relative_to(ROOT)),result_sha256=sha(prior_path),status=old['status'],
                                                alpha=old['alpha'],paired_difference=old['action']['paired_difference']),result=value)
            calls=[]
            def helper(text):
                require(not calls,'Exactly one rounded half-step per case');calls.append('round')
                folder=current/'round';folder.mkdir();input_path=folder/'input.txt';input_bytes=text.encode('utf8')
                input_digest=hashlib.sha256(input_bytes).hexdigest()
                for name,role in (('input.txt','Hexadecimal binary64 half-step input'),('stdout.json','Declared rounded trial'),('stderr.log','Declared diagnostics')):
                    save(folder/(name+'.identifiers.json'),dict(identity,expected_file=str((folder/name).relative_to(ROOT)),
                         role=role,mode='round',input_file=str(input_path.relative_to(ROOT)),input_file_sha256=input_digest,
                         file_sha256=input_digest if name=='input.txt' else None))
                with input_path.open('xb') as stream:stream.write(input_bytes)
                command=[str(C/'build/metric_step'),'round',str(input_path)]
                item=dict(event=event,station=160,mode='round',command=command,started_utc=now(),
                          native_context=case['native_context'],catalog_uses=case['catalog_uses'])
                ledger['commands'].append(item);update()
                with (folder/'stdout.json').open('x') as stdout,(folder/'stderr.log').open('x') as stderr:
                    old_mask=signal.pthread_sigmask(signal.SIG_BLOCK,{signal.SIGINT,signal.SIGTERM})
                    try:child=subprocess.Popen(command,cwd=str(ROOT),env=dict(os.environ,**prepared['environment']),stdout=stdout,stderr=stderr,start_new_session=True)
                    except BaseException:
                        signal.pthread_sigmask(signal.SIG_SETMASK,old_mask);raise
                    try:
                        item['pid']=child.pid
                        signal.pthread_sigmask(signal.SIG_SETMASK,old_mask);update()
                        returned=child.wait()
                        if returned!=0 or group_members(child.pid):raise RuntimeError('Helper failed or left live writers')
                    except BaseException:
                        state=stop_group(child);item['cleanup']=state
                        if state['live_members'] or not state['child_reaped']:unsettled.append(state)
                        raise
                    finally:
                        item.update(return_code=child.returncode,child_reaped=child.poll() is not None,finished_utc=now());update()
                item['output_sha256']={name:sha(folder/name) for name in ('input.txt','stdout.json','stderr.log')};update()
                return load(folder/'stdout.json')
            value['rounded_trials']=1
            raw=helper(m.trial_input(case['path'],direction,ALPHA));value['rounded_record']=raw
            trial,displacement,actual=m.trial_geometry(t,grid,case['path'],direction,case['components'],ALPHA,raw)
            value.update(trial=trial,actual_displacement=displacement,actual_displacement_slope=actual,status='actual_displacement_slope_unresolved')
            if actual[1]<0:
                value.update(status='action_evaluation_failed',action_edge_evaluations=None)
                action=m.trial_actions(t,grid,case['path'],trial,case['starting_edges'],SETTINGS,ALPHA,slope)
                value.update(action=action,action_edge_evaluations=action['action_edge_evaluations'],
                             status='diagnostic_trial_accepted' if action['conservative_nominal_armijo'] else 'diagnostic_trial_not_accepted')
            count=value['action_edge_evaluations'];require(count is None or 0<=count<=len(case['path'])-1,'Per-case action budget')
            verify();save(result_path,answer)
            completed.append(dict(event=event,station=160,native_context=case['native_context'],catalog_uses=case['catalog_uses'],
                result_file=str(result_path.relative_to(HERE)),result_sha256=sha(result_path),status=value['status'],
                metric_solves=0,rounded_trials=1,action_edge_evaluations=count,original_convergence_flag='0',candidate_convergence_status=None))
            current=None;answer=None
        require(len(ledger['commands'])==2 and sum(v['action_edge_evaluations'] for v in completed)<=2058,'Two rounding calls and fixed total action budget')
        ledger['status']='completed_bounded_half_step_diagnostic';code=0
    except BaseException as exc:
        if isinstance(exc,SystemExit) and isinstance(exc.code,int):code=exc.code
        ledger.update(status='failed_preserved',error=dict(type=type(exc).__name__,message=str(exc)))
        if current is not None and answer is not None and not (current/'result.json.gz').exists():
            answer['wrapper_failure']=ledger['error'];save(current/'result.json.gz',answer)
    finally:
        stable=not unsettled and all(v.get('child_reaped') for v in ledger['commands'])
        outputs={} if not stable else {str(p.relative_to(HERE)):sha(p) for p in sorted(HERE.glob('event_*/*')) if p.is_file()}
        if stable:
            for p in sorted(HERE.glob('event_*/*/*')):
                if p.is_file():outputs[str(p.relative_to(HERE))]=sha(p)
        summary=dict(status=ledger['status'],error=ledger.get('error'),cases=completed,native_contexts=identifiers,settings=SETTINGS,
                     alpha=ALPHA,alpha_hex=ALPHA.hex(),budget=dict(metric_solves_maximum=0,rounded_trials_maximum=2,new_action_edges_maximum=2058),
                     native_trace_calls=0,field_calls=0,tangent_integrals=0,optimizer_iterations=0,
                     interpretation='One fixed half-step on each exact saved direction, from the retained accepted first-step paths; no stopping or convergence decision.',
                     prepared_sha256=sha(HERE/'prepared.json'),prelaunch_review_sha256=sha(HERE/'prelaunch_review.json'),output_sha256=outputs)
        save(HERE/'summary.json',summary)
        ledger.update(return_code=code,finished_utc=now(),outputs_stable=stable,unsettled_groups=unsettled,
                      summary_sha256=sha(HERE/'summary.json'),output_sha256=outputs)
        update()
    return code


if __name__=='__main__':sys.exit(main())
