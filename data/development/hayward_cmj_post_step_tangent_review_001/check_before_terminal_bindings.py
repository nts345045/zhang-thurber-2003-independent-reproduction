#!/usr/bin/env python3
"""Saved edge/vector arithmetic only; no project imports or numerical calls."""
from fractions import Fraction as Q
import gzip
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
RUN=ROOT/'data/development/hayward_cmj_post_step_tangent_001'
STEP=ROOT/'data/development/hayward_cmj_tangent_step_001'
START=ROOT/'data/development/hayward_cmj_face_action_001'
PRE=ROOT/'data/development/hayward_cmj_face_action_review_001'
EXPECTED='f67aea4c47dc5014c7e4a6ff07a7417d771da542ecdad6e061a2ee7589a8d9b3'

def require(ok,message):
    if not ok:raise ValueError(message)

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()

def read(p):
    with (gzip.open(str(p),'rt') if p.suffix=='.gz' else p.open()) as f:return json.load(f)

def encoded(x):
    if isinstance(x,Q):return str(x)
    if isinstance(x,dict):return {k:encoded(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)):return [encoded(v) for v in x]
    return x

def bounds(x):
    a,b=map(Q,x);require(a<=b,'Reversed interval');return a,b

def pins(base,values):
    for name,digest in values.items():require(sha(base/name)==digest,'Changed pin: '+name)

def norm(path,vector,axes):
    low=Q(0);high=Q(0);records=[];blocked=[];boundary=0
    for i in range(1,len(path)-1):
        for k,entry in enumerate(vector[i]):
            if entry is None:blocked.append((i,k));continue
            a,b=bounds(entry);x=path[i][k];where='interior';p,q=a,b
            require(axes[k][0]<=x<=axes[k][-1],'Outside box')
            if x==axes[k][0]:p,q=min(a,Q(0)),min(b,Q(0));where='exact_lower'
            elif x==axes[k][-1]:p,q=max(a,Q(0)),max(b,Q(0));where='exact_upper'
            distance=max(p,-q,Q(0));far=max(abs(p),abs(q));s=(distance**2,far**2)
            low+=s[0];high+=s[1];boundary+=int(where!='interior')
            records.append(dict(node=i,axis=k,coordinate_exact=x,component_bounds=(a,b),physical_box_position=where,projected_bounds=(p,q),squared_bounds=s))
    return (low,high),records,blocked,boundary

def compare_norm(saved,result):
    (lo,hi),records,blocked,boundary=result
    require(bounds((saved['lower_squared'],saved['upper_squared']))==(lo,hi),'Squared norm sum')
    require(saved['available_component_count']==len(records) and saved['unavailable_component_count']==len(blocked)
            and saved['exact_physical_boundary_component_count']==boundary and saved['units']=='s^2/km^2','Norm inventory/units')
    for name,scale in [('strict_gradient_scale',Q(1,10**7)),('combined_gradient_scale',Q(1,10**5))]:
        item=saved['threshold_scales'][name];s=scale**2
        require(Q(item['scale_squared'])==s and item['diagnostic_only'] and item['classification']==
                ('strictly_above' if lo>s else 'strictly_below' if hi<s else 'overlapping'),'Diagnostic scale classification')

def main():
    require(not (HERE/'review.json').exists(),'Fresh review required')
    prepared=read(RUN/'prepared.json');execution=read(RUN/'execution.json');summary=read(RUN/'summary.json');outer=read(RUN/'outer_reaping.json')
    require(sha(RUN/'prepared.json')==EXPECTED,'Prepared source changed')
    require(execution['status']==summary['status']=='completed_bounded_tangent_diagnostic' and execution['return_code']==0 and summary['error'] is None,'Terminal calculation required')
    require(outer['status']=='completed_and_reaped' and outer['tool_exit_code']==0 and outer['wrapper_pid']==execution['pid'] and outer['wrapper_process_absent'],'Owned terminal receipt required')
    for key,file in [('execution_sha256','execution.json'),('summary_sha256','summary.json'),('prepared_sha256','prepared.json'),('prelaunch_review_sha256','prelaunch_review.json')]:
        require(outer[key]==sha(RUN/file),'Outer receipt binding')
    approval=read(RUN/'prelaunch_review.json');require(approval['status']=='passed' and approval['prepared_sha256']==EXPECTED,'Native prelaunch gate')
    identities=read(RUN/'native_contexts.json')
    require(identities==execution['native_contexts']==summary['native_contexts']==outer['native_contexts']==read(STEP/'native_contexts.json'),'Full native contexts')
    require([v['event'] for v in identities]==[981,987] and [v['event'] for v in summary['cases']]==[981,987],'Two-ray roster')
    require(summary['output_sha256']==execution['output_sha256'] and execution['summary_sha256']==sha(RUN/'summary.json'),'Terminal output map')
    for base,key in [(ROOT,'input_sha256'),(RUN,'output_sha256'),(Path('/'),'runtime_sha256')]:pins(base,prepared[key])
    pins(RUN,summary['output_sha256'])
    require(summary['settings']==dict(terms=8,subdivisions=1,bits=128) and summary['tangent_edge_budget']==2058,'Fixed primitive budget')
    require(all(summary[k]==0 for k in ['action_integrations','metric_solves','rounded_trials','trace_calls','field_calls','optimizer_iterations']) and execution['subprocess_calls']==0,'No extra numerical work')
    axes=[tuple(map(Q,a)) for a in read(START/'model_provenance.json')['axes_exact_rational']]
    old={v['event']:v for v in read(PRE/'tangent_norms.json')['cases']};reports=[];edge_count=0
    for identity,brief in zip(identities,summary['cases']):
        event=identity['event'];p=RUN/brief['result_file'];full=read(p);prior=read(STEP/('event_'+str(event))/'result.json.gz')
        require(sha(p)==brief['result_sha256'] and full['status']==brief['status']=='completed_available_tangent_bounds','Complete identified result')
        for record in [full,brief]:
            require(all(record[k]==identity[k] for k in ['event','station','native_context','catalog_uses']) and len(record['catalog_uses'])==9,'Native/catalog record joins')
            require(record['original_convergence_flag']=='0' and record['candidate_convergence_status'] is None,'Preserved flags')
        status=identity['native_context']['original_status']
        require(status['ray_converged']==status['ray_derivatives_evaluated']=='0' and all(status['source_d'+k]=='' for k in 'xyz'),'Original unevaluated source partials')
        attached=read(Path(str(p)+'.identifiers.json'))
        require(all(attached[k]==identity[k] for k in ['event','station','native_context','catalog_uses']) and attached['file_sha256'] is None and attached['expected_file']==str(p.relative_to(ROOT)),'Predeclared identified sidecar')
        require(attached['prepared_sha256']==EXPECTED and attached['evidence_sha256']==prepared['input_sha256'],'Sidecar evidence closure')
        path=[tuple(map(Q,v)) for v in prior['result']['trial']];before=[tuple(map(Q,v['candidate_exact_rational'])) for v in prior['coordinate_provenance']]
        require([tuple(map(Q,v['exact_rational'])) for v in full['coordinate_provenance']]==path and path[0]==before[0] and path[-1]==before[-1],'Exact saved trial/endpoints')
        require(full['prior_result_sha256']==sha(STEP/('event_'+str(event))/'result.json.gz') and full['saved_trial_action']==prior['result']['action']['trial_action'],'Prior trial binding')
        n=len(path);records=full['tangent_edge_records'];require(len(records)==n-1 and full['ineligibility']==[],'Complete edge inventory')
        vector=[[(Q(0),Q(0)) for k in range(3)] for i in path];vector[0]=vector[-1]=None;blocked=set();alignment=[]
        for e,(a,b,record) in enumerate(zip(path,path[1:],records)):
            require(a!=b and all(axes[k][0]<=a[k]<=axes[k][-1] and axes[k][0]<=b[k]<=axes[k][-1] for k in range(3)),'Feasible positive edge')
            faces=[(k,axis.index(a[k])) for k,axis in enumerate(axes) if a[k]==b[k] and a[k] in axis[1:-1]]
            require(len(faces)<=1 and record['edge']==e and record['endpoint_nodes']==[e,e+1] and record['blocked_axes']==[k for k,index in faces],'Actual geometry mask')
            alignment.append(dict(edge=e,aligned_internal_faces=faces))
            for side in (0,1):
                i=e+side
                if i in (0,n-1):require(record['components'][side] is None,'Fixed endpoint omission');continue
                require(len(record['components'][side])==3,'All incident axes')
                for k,value in enumerate(record['components'][side]):
                    require((value is None)==(k in record['blocked_axes']),'Edge availability')
                    if value is None:blocked.add((i,k))
                    else:
                        a0,b0=bounds(value);v,w=vector[i][k];vector[i][k]=(v+a0,w+b0)
        for i,k in blocked:vector[i][k]=None
        require(encoded(alignment)==full['aligned_edge_inventory'] and encoded(sorted(blocked))==full['geometric_blocked_slots'],'Derived alignment inventory')
        require(encoded([dict(node=i,components=vector[i]) for i in range(1,n-1)])==full['free_node_components'],'Adjacent derivative sums')
        after_norm=norm(path,vector,axes);compare_norm(full['post_step_norm'],after_norm)
        require(encoded(after_norm[1])==full['available_projected_components'],'Complete projected vector')
        pre_vector=[[None]*3 for i in before];pre_vector[0]=pre_vector[-1]=None
        for row in old[event]['components']:
            i=row['node'];k='xyz'.index(row['axis']);require(Q(row['coordinate_exact'])==before[i][k],'Pre-step coordinate');pre_vector[i][k]=bounds(row['component_bounds'])
        before_norm=norm(before,pre_vector,axes);compare_norm(full['pre_step_norm'],before_norm)
        require(before_norm[0]==bounds((old[event]['summary']['lower_squared'],old[event]['summary']['upper_squared'])),'Prior independent squared norm')
        comparison=full['comparison'];pre_mask=set(before_norm[2]);same=pre_mask==blocked
        require(comparison==brief['comparison'] and comparison['pre']==full['pre_step_norm'] and comparison['post']==full['post_step_norm'] and comparison['same_available_mask']==same and comparison['diagnostic_only'],'Comparison identity')
        require(comparison['newly_unavailable_slots']==encoded(sorted(blocked-pre_mask)) and comparison['newly_available_slots']==encoded(sorted(pre_mask-blocked)),'Availability changes')
        if same and before_norm[0][0]>0:require(bounds(comparison['squared_norm_ratio_bounds'])==(after_norm[0][0]/before_norm[0][1],after_norm[0][1]/before_norm[0][0]),'Exact ratio enclosure')
        require(full['attempted_tangent_edges']==full['completed_tangent_edges']==brief['tangent_edge_evaluations']==n-1,'Per-ray integration count');edge_count+=n-1
        reports.append(dict(identity,pre_squared_bounds=before_norm[0],post_squared_bounds=after_norm[0],same_available_mask=same,available_components=len(after_norm[1]),blocked_components=len(blocked),physical_boundary_components=after_norm[3],original_convergence_flag='0',candidate_convergence_status=None))
    require(edge_count==summary['attempted_tangent_edges']==summary['completed_tangent_edges']==execution['attempted_tangent_edges']==execution['completed_tangent_edges']==2058,'Total bounded integration count')
    require({p.name for p in RUN.glob('event_*') if p.is_file()}==set(summary['output_sha256']),'Complete terminal file inventory')
    for base,key in [(ROOT,'input_sha256'),(RUN,'output_sha256'),(Path('/'),'runtime_sha256')]:pins(base,prepared[key])
    pins(RUN,summary['output_sha256'])
    result=dict(status='passed',reviewer='scientific_audit',checker_sha256=sha(Path(__file__)),native_prepared_sha256=EXPECTED,native_summary_sha256=sha(RUN/'summary.json'),native_execution_sha256=sha(RUN/'execution.json'),outer_reaping_sha256=sha(RUN/'outer_reaping.json'),cases=reports,review_numerical_calls=0,limitations=['Saved-array/native/hash arithmetic only; no reintegration or numerical helper calls.','The reviewed source/control evidence supports primitive derivative inclusion; this readback independently verifies assembly and norm algebra.','Available tangent norms are not all-direction stationarity, source accuracy, first-arrival or convergence certificates.'])
    with (HERE/'review.json').open('x') as f:json.dump(encoded(result),f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
    print(json.dumps({'status':'passed','review_sha256':sha(HERE/'review.json'),'edge_records':edge_count}))
if __name__=='__main__':main()
