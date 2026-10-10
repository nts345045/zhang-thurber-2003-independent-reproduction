#!/usr/bin/env python3
"""Read saved identified probes and interval arithmetic; no action evaluation."""
import csv
from fractions import Fraction as Q
import hashlib
import json
import math
from pathlib import Path

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
CONTROL='data/development/loma_node_action_controls_003'
OBSERVER='data/development/loma_initial_failure_3426_001'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text())


def rows(path):
    with path.open(newline='') as f:
        return list(csv.DictReader(f))


def need(ok,message):
    if not ok:
        raise ValueError(message)


def bounds(record):
    a,b=Q(record['lower_rational']),Q(record['upper_rational'])
    need(a<=b,'Reversed interval')
    need(float(a)==record['lower_display'] and float(b)==record['upper_display'],'Display differs')
    return a,b


def main():
    s=load(OUT/'summary.json');receipt=load(OUT/'execution_receipt.json')
    summary_hash=sha(OUT/'summary.json')
    need(s['status']=='completed_native_two_segment_diagnostic','Nonterminal result')
    need(receipt['summary_sha256']==summary_hash and receipt['return_code']==0 and receipt['probes']==40,'Receipt mismatch')
    before={'summary.json':summary_hash,'execution_receipt.json':sha(OUT/'execution_receipt.json')}
    before.update(s['artifact_sha256'])
    for n,h in before.items():need(sha(OUT/n)==h,'Changed frozen artifact '+n)
    revision_path=ROOT/CONTROL/'review_revision.json';revision=load(revision_path)
    need(receipt['review_revision_record_sha256']==sha(revision_path) and revision['native_summary_sha256']==summary_hash,'Revision receipt mismatch')
    frozen_review=OUT/'source'/CONTROL/'review.json'
    old=load(frozen_review);current=load(ROOT/CONTROL/'review.json')
    need(sha(frozen_review)==sha(ROOT/CONTROL/'review_at_native_launch.json')==revision['consumed_review_sha256']==receipt['consumed_controls_review_sha256'],'Consumed review not preserved')
    need(sha(ROOT/CONTROL/'review.json')==revision['later_review_sha256'],'Later review mismatch')
    changed={k for k in old if old[k]!=current[k]}
    need(changed==set(revision['changed_fields'])=={'source_math_findings','native_input_review','limitations'},'Non-prose review mutation')
    changed_indices={'source_math_findings':1,'native_input_review':2,'limitations':0}
    for k,index in changed_indices.items():
        need(revision['changed_fields'][k]['at_launch']==old[k] and revision['changed_fields'][k]['later_wording']==current[k],'Revision does not describe bytes')
        need(len(old[k])==len(current[k]) and all(x==y for j,(x,y) in enumerate(zip(old[k],current[k])) if j!=index),'Additional review edits')
    need(old['status']==current['status']=='passed' and old['controls_summary_sha256']==sha(OUT/'source'/CONTROL/'summary.json'),'Review control gate mismatch')
    for n,h in s['input_source_sha256'].items():
        need(sha(OUT/'source'/n)==h,'Frozen input mismatch')
        if n!=CONTROL+'/review.json':need(sha(ROOT/n)==h,'Current nonreview input changed')
    base=OUT/'source'/OBSERVER
    native=rows(base/'identified_ray.csv')
    need(len(native)==1 and s['native_context']==native[0],'Native context mismatch')
    source=load(base/'summary.json');sidecar=load(base/'paths.csv.identifiers.json')
    need(source['native_context']==native[0] and sidecar['native_context']==native[0] and sidecar['file_sha256']==sha(base/'paths.csv'),'Native path detached')
    run='fmm_0.031250_1000'
    path=[r for r in rows(base/'paths.csv') if r['run_id']==run]
    need([int(r['node']) for r in path]==list(range(1134)),'Incomplete native path')
    need(s['adjacent_original_nodes']==path[483:486] and s['focus_node']==484,'Wrong local nodes')
    points=[[Q(float(r[k])) for k in 'xyz'] for r in path[483:486]]
    need(s['exact_saved_points_xyz_rational']==[[str(v) for v in p] for p in points],'Binary coordinate reconstruction')
    grid=rows(base/'inputs/initial_grid.csv')
    profile=sorted(set((Q(float(r['z'])),Q(float(r['v']))) for r in grid))
    need(s['depth_profile_rational']==[[str(v) for v in p] for p in profile],'Depth profile mismatch')
    need(s['axis_permutation']=='(physical z, physical x, physical y)','Wrong frame declaration')
    result=next(r for r in rows(base/'results.csv') if r['run_id']==run)
    need(result==s['original_result'] and result['converged']=='0','Original result or flag changed')
    failed=[r for r in rows(base/'history.csv') if r['run_id']==run and r['phase']=='line_search_failed']
    need(failed==[s['original_failed_search']],'Failed search mismatch')
    selected=[r for r in rows(base/'path_gradient_checks.csv') if r['run_id']==run and r['node']=='484' and r['axis']=='2' and Q(float(r['step_km']))==Q(float(1e-6))]
    need(selected==[s['original_focus_node_fd']],'Focus difference mismatch')
    original_action=bounds(s['adjacent_action'])
    saved=[Q(float(path[484]['gradient_'+k])) for k in 'xyz']
    need(s['saved_node_gradient_xyz_rational']==list(map(str,saved)),'Saved gradient mismatch')
    for exact,old_value,error in zip(s['exact_node_gradient_xyz'],saved,s['exact_minus_saved_gradient_xyz']):
        lo,hi=bounds(exact)
        need(bounds(error)==(lo-old_value,hi-old_value),'Gradient interval subtraction mismatch')
    ulp=Q(2)**(math.frexp(float(result['time_s']))[1]-53);slope=Q(float(failed[0]['directional_slope']))
    need(Q(s['original_full_action_ulp_s_rational'])==ulp and Q(s['original_slope_s_rational'])==slope,'ULP or slope mismatch')
    need(s['original_full_step_linear_decrease_in_ulps']==float(-slope/ulp) and s['original_full_step_armijo_decrease_in_ulps']==float(-Q(float(1e-4))*slope/ulp),'ULP ratios mismatch')
    z=points[1][2];gap=z-7
    expect=[('within_current_depth_piece',p,gap/(1<<p)) for p in (1,2,4,8,12,16,20,24,28)]
    expect.append(('original_break_crossing_central_difference',None,Q(float(1e-6))))
    probes=s['probes'];need(len(probes)==40,'Incomplete probes')
    ids=['source_event_resource_id','source_origin_resource_id','receiver_channel_seed_id','receiver_channel_fdsn_source_id','receiver_metadata_epoch_start','receiver_metadata_epoch_end']
    groups={}
    for label,power,h in expect:
        for mode in ('exact_rational_perturbation','binary64_rounded_perturbation'):
            group=[r for r in probes if r['label']==label and r['halving_power']==power and r['coordinate_mode']==mode]
            need([r['sign'] for r in group]==[-1,1],'Probe ordering/support')
            for r in group:
                need(all(r[k]==native[0][k] for k in ids) and r['observation_index']==3426 and r['run_id']==run and r['focus_node']==484 and r['original_local_flag']=='0','Probe native/flag mapping')
                intended=z+r['sign']*h;actual=intended if mode=='exact_rational_perturbation' else Q(float(intended))
                need(Q(r['h_rational'])==h and Q(r['intended_z_rational'])==intended and Q(r['actual_z_rational'])==actual and Q(r['actual_delta_z_rational'])==actual-z,'Probe coordinate reconstruction')
                need(profile[0][0]<actual<profile[-1][0],'Probe outside finite depth interval')
                need(r['crosses_depth_break']==(not (7<actual<11)) and r['coordinate_changed']==(actual!=z),'Probe classification')
                action=bounds(r['adjacent_action']);change=bounds(r['exact_action_change'])
                need(change==(action[0]-original_action[1],action[1]-original_action[0]),'Action interval difference')
                sign='strict_decrease' if change[1]<0 else 'strict_increase' if change[0]>0 else 'inconclusive'
                need(r['action_change_sign']==sign,'Action sign label')
            span=Q(group[1]['actual_z_rational'])-Q(group[0]['actual_z_rational'])
            left,right=bounds(group[0]['adjacent_action']),bounds(group[1]['adjacent_action'])
            for r in group:
                need(Q(r['actual_central_span_rational'])==span,'Central span mismatch')
                if span:need(bounds(r['actual_central_difference'])==((right[0]-left[1])/span,(right[1]-left[0])/span),'Central interval difference')
                else:need(r['actual_central_difference'] is None and not r['coordinate_changed'],'Collapsed probe misclassified')
            groups[(label,power,mode)]=group
    for n,h in before.items():need(sha(OUT/n)==h,'Artifact changed during readback')
    need(sha(revision_path)==receipt['review_revision_record_sha256'],'Revision changed during readback')
    minus=groups[('within_current_depth_piece',1,'binary64_rounded_perturbation')][0]
    crossing=groups[('original_break_crossing_central_difference',None,'binary64_rounded_perturbation')]
    review=dict(status='passed_saved_result_review',material_issue_found=False,
        scope='Independent native/hash and exact saved-interval arithmetic readback; no new action evaluation, ray trace or optimization.',
        summary_sha256=summary_hash,execution_receipt_sha256=before['execution_receipt.json'],
        review_revision_sha256=sha(revision_path),checker_sha256=sha(Path(__file__)),
        frozen_input_hashes_verified=len(s['input_source_sha256']),current_nonreview_input_hashes_verified=len(s['input_source_sha256'])-1,
        artifact_hashes_verified=len(s['artifact_sha256']),consumed_controls_review_sha256=sha(frozen_review),
        documented_later_review_sha256=sha(ROOT/CONTROL/'review.json'),
        probe_count=40,native_identity_fields_all_match=True,original_flag_unchanged=True,
        coordinate_and_axis_mapping_verified=True,action_and_gradient_interval_subtractions_verified=True,
        central_spans_and_interval_quotients_verified=True,collapsed_binary_probe_count=sum(not r['coordinate_changed'] for r in probes),
        native_identifiers={k:native[0][k] for k in ids},
        exact_node_z_gradient=s['exact_node_gradient_xyz'][2],exact_minus_saved_z_gradient=s['exact_minus_saved_gradient_xyz'][2],
        minus_half_gap_binary_action_change=minus['exact_action_change'],
        original_crossing_probe_action_signs=[r['action_change_sign'] for r in crossing],
        limitations=['These are fixed-polygon coordinate probes, not the original saved L-BFGS search direction or trial paths.',
                     'A cross-break central quotient need not equal the local derivative at the original node.',
                     'The frozen consumed review is authoritative for this run; its later three prose revisions do not alter source, status or control pins.',
                     'No source derivative, convergence flag, production method or inverse acceptance changes.'])
    with (OUT/'review.json').open('x') as f:json.dump(review,f,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps(dict(status=review['status'],review_sha256=sha(OUT/'review.json'),probes=40,frozen_inputs=len(s['input_source_sha256']),artifacts=len(s['artifact_sha256'])),indent=2))


if __name__=='__main__':
    main()
