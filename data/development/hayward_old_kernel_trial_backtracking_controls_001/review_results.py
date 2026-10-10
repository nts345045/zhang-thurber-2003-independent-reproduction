#!/usr/bin/env python3
"""Independent saved controls readback; no compiler, ray, solve or inverse."""
import csv,hashlib,json,math
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):
 with Path(p).open(newline='') as f:
  reader=csv.DictReader(f);assert len(reader.fieldnames)==len(set(reader.fieldnames)),str(p)
  return list(reader)
def main():
 p=json.loads((HERE/'prepared.json').read_text());s=json.loads((HERE/'summary.json').read_text());e=json.loads((HERE/'execution.json').read_text())
 assert s['status']=='passed' and e['status']=='completed' and e['return_code']==0
 assert s['prepared_sha256']==e['prepared_sha256']==sha(HERE/'prepared.json')
 assert [c['name'] for c in e['commands']]==['compile_before','before','compile_after','after'] and all(c['return_code']==0 for c in e['commands'])
 pins={}
 for m,base in [(p['input_sha256'],ROOT),(p['runtime_sha256'],Path('/')),(p['output_sha256'],HERE),(s['artifact_sha256'],HERE)]:
  for n,h in m.items():
   path=base/n;assert sha(path)==h,str(path);pins[str(path)]=h
 assert s['source_sha256']==p['output_sha256']
 for name,n in [('before',4),('after',1102)]:
  checks=read(HERE/'results'/name/'checks.csv');assert len(checks)==s['controls'][name]==n and all(r['passed']=='1' for r in checks)
 assert len(s['all_valid_byte_parity'])==28
 for item in s['all_valid_byte_parity']:
  assert sha(HERE/'results/before'/item['path'])==sha(HERE/'results/after'/item['path'])==item['sha256']
 base=HERE/'results/after';native_cells=0;cases={}
 for kind,denom,rejects in [('half',2,1),('quarter',4,2)]:
  folder=base/kind;ledger=read(folder/'loc1d_iteration_0_trials.csv')
  assert len(ledger)==rejects+1
  for j,r in enumerate(ledger):
   assert float(r['step_fraction'])==2.**(-j)
   assert r['status']==('local_stopping_rejected' if j<rejects else 'accepted')
   assert r['objective_evaluated']==str(int(j==rejects))
   if j<rejects:assert r['objective_after']==''
  assert float(ledger[-1]['objective_after'])<2e-30 and float(ledger[-1]['objective_after'])<=float(ledger[-1]['objective_before'])
  events=read(folder/'loc1d_events.csv');assert [float(r['t']) for r in events]==[.1,.2]
  initial=read(folder/'initial_events.csv')
  assert all(float(a[k])==float(b[k]) for a,b in zip(events,initial) for k in 'xyz')
  cases[kind]={'quality_rejections':rejects,'accepted_fraction':1/denom,'objective_after':float(ledger[-1]['objective_after'])}
 for kind in ('half','quarter','all','mixed_invalid','state','worse'):
  f=base/kind;mode='dd' if kind in ('mixed_invalid','state') else 'loc1d';prefix=f/(mode+'_iteration_0_solve')
  d=read(str(prefix)+'_delta.csv');w=read(str(prefix)+'_weights.csv');info=read(str(prefix)+'_context.csv')[0]
  initial=read(f/'initial_events.csv');obs=read(f/'observations.csv');g=read(f/'initial_grid.csv')
  assert len(d)==int(info['columns'])==(16 if mode=='dd' else 8) and len(w)==len(obs)==4
  for q,r in enumerate(d):
   assert int(r['parameter_index'])==q
   if q<8:
    event=q//4;assert int(r['event'])==event and r['component']=='xyzt'[q%4]
    for key,value in initial[event].items():
     if key in ('id','x','y','z','t'):continue
     assert r['source_'+key]==value;native_cells+=1
   else:assert int(r['node'])==q-8 and r['source_event_resource_id']=='' and float(r['reference_v'])==5
  for q,(r,o) in enumerate(zip(w,obs)):
   assert int(r['observation_index'])==q
   for key,value in o.items():
    if key in ('i','j','station','type','value'):continue
    assert r['original_'+key]==value;native_cells+=1
   assert int(r['station_j'])==(-1 if int(o['j'])<0 else 1)
  assert float(w[3]['fixed_row_multiplier'])==0
  # Independently use the stored original residuals and closed-form weight rule;
  # no solver weight helper or inverse/forward code is imported.
  cut={}
  for t in range(3):
   a=sorted(abs(float(r['current_residual'])) for r in w if int(r['type'])==t)
   cut[t]=1 if not a else max(.01,6*1.4826*a[len(a)//2])
  sq=0.
  for r,o in zip(w,obs):
   t=int(r['type']);res=float(r['current_residual']);z=res/cut[t]
   weight=(1 if t==0 else .1)*float(o['a_priori_weight'])*max(0.,1-z*z)**2
   if t:
    a,b=initial[int(o['i'])],initial[int(o['j'])]
    distance=math.sqrt(sum((float(a[k])-float(b[k]))**2 for k in 'xyz'))
    weight*=max(0.,1-(distance/20)**2)**2
   if weight<1e-12:weight=0.
   assert abs(weight-float(r['fixed_row_multiplier']))<=1e-15
   sq+=weight*weight*res*res
  assert abs(sq-float(info['objective_before']))<=1e-15
  ledger=read(f/(mode+'_iteration_0_trials.csv'))
  for r in ledger:
   if r['status']!='local_stopping_rejected':continue
   trial=int(r['trial']);pre=f/(mode+'_rejected_trial_it_0_ls_'+str(trial))
   failures=read(str(pre)+'_ray_failures.csv');status=read(str(pre)+'_ray_status.csv')
   assert failures and all(a['reasons']=='local_stopping_failed' for a in failures)
   assert all(a['ray_finite']=='1' and a['ray_path_in_domain']=='1' and a['ray_exact_source_endpoint']=='1' and a['ray_exact_receiver_endpoint']=='1' for a in status)
   trial_events=read(str(pre)+'_events.csv');trial_grid=read(str(pre)+'_grid.csv');accepted=read(str(pre)+'_accepted_events.csv')
   step=float(r['step_fraction']);bounds={k:(min(float(v[k]) for v in g),max(float(v[k]) for v in g)) for k in 'xyz'}
   for i,(a,b,c) in enumerate(zip(initial,trial_events,accepted)):
    for ax,k in enumerate('xyz'):
     expected=min(max(float(a[k])+step*float(d[4*i+ax]['increment']),bounds[k][0]),bounds[k][1]);assert float(b[k])==expected
     assert float(c[k])==float(a[k])
    assert float(b['t'])==float(a['t'])+step*float(d[4*i+3]['increment']) and float(c['t'])==float(a['t'])
   for node,(a,b) in enumerate(zip(g,trial_grid)):
    expected=float(a['v'])*(math.exp(-step*float(d[8+node]['increment'])) if mode=='dd' else 1)
    assert float(b['v'])==expected
  if kind in ('all','mixed_invalid','state'):
   assert len(ledger)==12 and all(r['objective_evaluated']=='0' for r in ledger)
   assert 'No objective-evaluable trial' in (f/'caught.txt').read_text()
   assert not (f/(mode+'_events.csv')).exists() and not (f/(mode+'_grid.csv')).exists()
  if kind=='mixed_invalid':assert ledger[0]['status']=='invalid_trial_model' and sum(r['status']=='local_stopping_rejected' for r in ledger)==11
  if kind=='worse':assert ledger[0]['status']=='local_stopping_rejected' and all(r['status']=='objective_rejected' for r in ledger[1:]) and float(read(f/'loc1d_history.csv')[0]['step_fraction'])==0
 for kind in ('current','final','mixed','unexpected'):
  f=base/kind;assert (f/'caught.txt').read_text() and not (f/'loc1d_events.csv').exists()
  if kind in ('mixed','unexpected'):assert not (f/'loc1d_rejected_trial_it_0_ls_1_context.csv').exists()
 for f in sorted(base.glob('io_*')):
  assert 'Cannot finish' in (f/'caught.txt').read_text() and not (f/'loc1d_events.csv').exists()
 for kind in ('prior_trial','prior_solve','dangling','prior_ledger'):
  assert 'Refusing prior' in (base/kind/'caught.txt').read_text()
 for path,h in pins.items():assert sha(path)==h,path
 result={'status':'passed','reviewer':'scientific_audit','summary_sha256':sha(HERE/'summary.json'),'execution_sha256':sha(HERE/'execution.json'),'source_sha256':sha(Path(__file__)),'verified_pin_count':len(pins),'executed_artifact_pins':len(s['artifact_sha256']),'checks':s['controls'],'all_valid_identical_files':28,'native_metadata_cells':native_cells,'independent_known_targets':cases,'scope':'Saved-only rehash/readback plus complete frozen source/seam review. Actual pure-local failure rosters, all-row native weights, unscaled increments and clamped/exponential trial states independently reconstructed. No compiler/forward/solve/inverse rerun.','limitations':['1102 records include repeated fieldwise assertions across small invented cases, not1102 independent scientific experiments.','Prescribed test deltas are explicitly separated from actual solved vectors/status; this suite does not establish real-data convergence or global3D first arrivals.','The core/input/existing guard integration checks and production adoption remain separate.','Retained compile warning concerns fixture indentation only; no warning suppression or source rewrite followed execution.']}
 with (HERE/'review.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
 print(sha(HERE/'review.json'))
if __name__=='__main__':main()
