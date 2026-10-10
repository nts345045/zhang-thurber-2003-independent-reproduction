#!/usr/bin/env python3
"""Independent terminal saved-artifact readback; never calls a field or ray."""
import csv, hashlib, json, math
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def read(p):
    with p.open() as f:return list(csv.DictReader(f))
def load(n):return json.loads((HERE/n).read_text())
def main():
    p,s,e,c=load('prepared.json'),load('summary.json'),load('execution.json'),load('controller_completion.json')
    assert s['status']=='completed_four_configured_evaluations' and e['status']=='completed' and e['return_code']==0
    assert c['status']=='completed' and c['driver_return_code']==0 and c['child_reaped'] and not c['forwarded_signals']
    assert e['summary_sha256']==c['summary_sha256']==sha(HERE/'summary.json')
    assert c['execution_sha256']==sha(HERE/'execution.json') and c['launch_sha256']==sha(HERE/'launch.json')
    assert c['controller_sha256']==sha(HERE/'controller.py')
    assert len(e['commands'])==4 and [q['stage'] for q in e['commands']]==['compile_old','forward_old','compile_D','forward_D']
    assert all(q['return_code']==0 and q['pid']>0 and q['finished_utc'] for q in e['commands'])
    assert s['prepared_sha256']==e['prepared_sha256']==sha(HERE/'prepared.json')
    assert s['prelaunch_review_sha256']==e['prelaunch_review_sha256']==sha(HERE/'prelaunch_review.json')
    pins={}
    for j,base in [(p['original_sha256'],ROOT),(p['runtime_sha256'],Path('/')),(p['output_sha256'],HERE),(p['source_sha256'],HERE),(s['output_sha256'],HERE),(c['log_sha256'],HERE)]:
        for n,h in j.items():
            path=base/n;assert sha(path)==h,str(path);pins[str(path)]=h
    assert s['field_constructions']==1 and s['configured_evaluations']==4 and s['trace_subcalls']==8
    assert e['field_constructions_completed']==1 and e['configured_evaluations_completed']==4 and e['trace_subcalls_completed']==8
    original_status=read(HERE/'inputs/original_status.csv');original_paths=read(HERE/'inputs/original_paths.csv')
    old=read(HERE/'results/old/status.csv');new=read(HERE/'results/D/status.csv')
    assert old==original_status and read(HERE/'results/old/paths.csv')==original_paths
    parity=load('old_parity.json');assert parity['status']=='passed' and parity['status_rows_equal'] and parity['selected_path_rows_equal']
    assert s['old_parity_sha256']==c['old_parity_sha256']==sha(HERE/'old_parity.json')
    for name,h in s['candidate_sha256'].items():assert sha(HERE/'results/old'/name)==sha(HERE/'results/D'/name)==h
    grid=read(HERE/'inputs/trial_grid.csv');bounds={a:(min(float(r[a]) for r in grid),max(float(r[a]) for r in grid)) for a in 'xyz'}
    cells=0;comparisons=[]
    for variant,table in [('old',old),('D',new)]:
        paths=read(HERE/'results'/variant/'paths.csv');starts=read(HERE/'results'/variant/'starts.csv')
        assert len(table)==2 and len(starts)==4 and len(paths)==sum(int(r['ray_path_points']) for r in table)
        for j,(r,original) in enumerate(zip(table,original_status)):
            assert (int(r['event']),int(r['station']))==[(981,160),(987,160)][j]
            assert r['ray_derivatives_evaluated']=='0' and all(r['source_d'+a]=='' for a in 'xyz')
            for key in ('ray_finite','ray_path_in_domain','ray_exact_source_endpoint','ray_exact_receiver_endpoint','ray_initialization_attempted','ray_initialization_succeeded'):assert r[key]=='1'
            for key,value in original.items():
                if key.startswith(('source_','receiver_')):assert r[key]==value
            nodes=[q for q in paths if q['event']==r['event'] and q['station']==r['station']]
            assert [int(q['node']) for q in nodes]==list(range(len(nodes))) and len(nodes)==int(r['ray_path_points'])
            assert [float(nodes[0][a]) for a in 'xyz']==[float(r['source_'+a]) for a in 'xyz']
            assert [float(nodes[-1][a]) for a in 'xyz']==[float(r['receiver_'+a]) for a in 'xyz']
            start=starts[2*j:2*j+2]
            assert [(q['event'],q['station'],q['start']) for q in start]==[(r['event'],r['station'],'straight'),(r['event'],r['station'],'fmm')]
            for q in nodes+start:
                for key,value in original.items():
                    if key.startswith(('source_','receiver_')) and key not in ['source_'+a for a in ('x','y','z','t','dx','dy','dz')]+['receiver_'+a for a in 'xyz']:
                        assert q[key]==value;cells+=1
            for q in nodes:
                assert all(math.isfinite(float(q[a])) and bounds[a][0]<=float(q[a])<=bounds[a][1] for a in 'xyz')
            for q in start:
                assert all(math.isfinite(float(q[k])) for k in ('time','projected_gradient','raw_gradient'))
                assert q['converged'] in ('0','1') and 0<=int(q['iterations'])<=1000
            selected=int(float(start[1]['time'])<float(start[0]['time']))
            assert int(r['ray_selected_fmm_seed'])==selected and r['ray_time']==start[selected]['time']
            for left,right in [('ray_converged','converged'),('ray_iterations','iterations'),('ray_merged_nodes','merged_nodes'),('ray_projected_gradient','projected_gradient'),('ray_raw_gradient','raw_gradient'),('ray_path_points','path_points')]:assert r[left]==start[selected][right]
            assert s['variants'][variant][j]['status']==r and s['variants'][variant][j]['starts']==start
    for a,b,reported in zip(old,new,s['comparisons']):
        computed={'event':int(a['event']),'station':int(a['station']),'D_minus_old_time_s':float(b['ray_time'])-float(a['ray_time']),'old_flag':int(a['ray_converged']),'D_flag':int(b['ray_converged']),'old_selected_fmm':int(a['ray_selected_fmm_seed']),'D_selected_fmm':int(b['ray_selected_fmm_seed']),'old_updates':int(a['ray_iterations']),'D_updates':int(b['ray_iterations']),'old_projected_gradient':float(a['ray_projected_gradient']),'D_projected_gradient':float(b['ray_projected_gradient'])}
        assert all(reported[k]==v for k,v in computed.items());computed['native_context']=reported['native_context'];comparisons.append(computed)
    for path,h in pins.items():assert sha(path)==h,path
    result={'status':'passed','reviewer':'scientific_audit','summary_sha256':sha(HERE/'summary.json'),'execution_sha256':sha(HERE/'execution.json'),'controller_completion_sha256':sha(HERE/'controller_completion.json'),'prepared_sha256':sha(HERE/'prepared.json'),'source_sha256':sha(Path(__file__)),'verified_pin_count':len(pins),'native_metadata_cells':cells,'old_exact_original_status_and_selected_path_parity':True,'candidate_files_byte_identical_old_D':True,'field_constructions':1,'configured_evaluations':4,'trace_subcalls':8,'comparisons':comparisons,'scope':'Saved full native/geometry/selection/termination/pin readback. No field, ray, inverse or reference reevaluation. D flag improvement does not certify global arrival, source accuracy, all181 failed rays, or trial/inversion acceptance.'}
    with (HERE/'review.json').open('x') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
    print(sha(HERE/'review.json'))
if __name__=='__main__':main()
