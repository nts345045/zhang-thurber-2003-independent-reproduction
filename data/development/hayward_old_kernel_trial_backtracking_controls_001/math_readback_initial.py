#!/usr/bin/env python3
"""Independent saved-only scope, parity and scalar objective readback."""
import csv,difflib,hashlib,json,tarfile
from pathlib import Path
from fractions import Fraction as Q
P=Path(__file__).resolve().parent;R=P.parents[2]
pins={}
def sha(p):
 p=p.resolve();h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 value=h.hexdigest();pins[str(p)]=value;return value

def checked(p,digest):assert sha(p)==digest,str(p)
def load(p):return json.loads(p.read_text())
def rows(p):
 with p.open(newline='') as f:return list(csv.DictReader(f))
s=load(P/'summary.json');p=load(P/'prepared.json');e=load(P/'execution.json');prior=load(P/'review.json')
assert s['status']=='passed' and e['status']=='completed' and e['return_code']==0
assert sha(P/'summary.json')==prior['summary_sha256']=='deb1c4379029456366b388e22c01ac3a3c4c879c11d17507c7f5d5bda836fb1c'
assert sha(P/'execution.json')==prior['execution_sha256']
assert sha(P/'prepared.json')==s['prepared_sha256']==e['prepared_sha256']
for n,h in p['input_sha256'].items():checked(R/n,h)
for n,h in p['runtime_sha256'].items():checked(Path(n),h)
for n,h in p['output_sha256'].items():checked(P/n,h)
for n,h in s['source_sha256'].items():checked(P/n,h)
for n,h in s['artifact_sha256'].items():checked(P/n,h)
assert len(e['commands'])==4 and all(c['return_code']==0 for c in e['commands'])
for c in e['commands']:
 if c['name'].startswith('compile'):assert '-O3' in c['argv'] and '-fopenmp' in c['argv'] and not any('NDEBUG' in a for a in c['argv'])
C=R/'data/development/hayward_old_kernel_trial_backtracking_candidate_001';candidate=load(C/'prepared.json')
for n,h in candidate['input_sha256'].items():checked(R/n,h)
for n,h in candidate['output_sha256'].items():checked(C/n,h)
archive=R/'data/hayward_first_arrival_guarded_001/guarded_source.tar.gz'
with tarfile.open(str(archive)) as tar:
 for name,h in candidate['original_sha256'].items():
  checked(C/'before'/name,h)
  assert hashlib.sha256(tar.extractfile(name).read()).hexdigest()==h
  for variant in ('before','after'):assert (P/'source'/variant/name).read_bytes()==(C/variant/name).read_bytes()
changed=[n for n in candidate['original_sha256'] if (C/'before'/n).read_bytes()!=(C/'after'/n).read_bytes()]
assert changed==['src/main.cpp']
assert sha(C/'before/src/core.hpp')=='7111f67c896b7b93d344372423259e288533210807392e7da2eec72f0c55caed'
assert not (P/'source/after/src/usable_ray_curvature.hpp').exists()
assert (C/'candidate.patch').read_bytes()==(R/'data/development/hayward_trial_backtracking_candidate_003/candidate.patch').read_bytes()
# Only the three declared fixture seams differ from each frozen main.cpp.
declarations='''// Test-only seams: actual invert body and arithmetic are retained.
std::string fixture_output(const std::string &);
Vec fixture_solve(Matrix, double, LSQRInfo *);
void fixture_gate(const std::string &, const Grid &, const std::vector<Event> &,
                  const std::vector<Event> &, const std::vector<Ray> &,
                  const std::vector<int> &, bool, bool);
'''
for variant in ('before','after'):
 text=(P/'source'/variant/'src/main.cpp').read_text()
 for a,b in [('std::ofstream output(std::string p) {',declarations+'std::ofstream output(std::string p) {'),
             ('std::ofstream f(p);','std::ofstream f(fixture_output(p));'),
             ('inversion_ray_gate(prefix, model, sources, stations, result, used,','fixture_gate(prefix, model, sources, stations, result, used,'),
             ('Vec delta = solve(std::move(A), c.get("damping"), &linear_info);','Vec delta = fixture_solve(std::move(A), c.get("damping"), &linear_info);')]:
  assert text.count(a)==1;text=text.replace(a,b)
 assert text==(P/'source'/variant/'src/fixture_main.cpp').read_text()
 parity=sorted(str(f.relative_to(P/'results/before')) for root in ('valid_loc1d','valid_dd') for f in (P/'results/before'/root).rglob('*') if f.is_file())
assert sorted(x['path'] for x in s['all_valid_byte_parity'])==parity and len(parity)==28
for item in s['all_valid_byte_parity']:
 a=P/'results/before'/item['path'];b=P/'results/after'/item['path']
 assert a.read_bytes()==b.read_bytes();checked(a,item['sha256']);checked(b,item['sha256'])
for variant,count in [('before',4),('after',1102)]:
 checks=rows(P/'results'/variant/'checks.csv');assert len(checks)==count and all(x['passed']=='1' for x in checks)
# Reconstruct objectives from saved ray times: homogeneous geometry/grid do not
# change; the declared test increments affect source origin times only.
math=[]
for case,accepted_step in [('half',.5),('quarter',.25),('worse',None)]:
 q=P/'results/after'/case;weights=rows(q/'loc1d_iteration_0_solve_weights.csv');delta=rows(q/'loc1d_iteration_0_solve_delta.csv')
 initial=rows(q/'loc1d_iteration_0_solve_accepted_events.csv');final=rows(q/'loc1d_events.csv')
 assert len(delta)==8 and all(float(x['increment'])==0 for x in delta if x['component']!='t')
 dt={int(x['event']):float(x['increment']) for x in delta if x['component']=='t'}
 rays=rows(q/'loc1d_rejected_trial_it_0_ls_0_ray_status.csv')
 times={(int(x['event']),int(x['station'])):float(x['ray_time']) for x in rays}
 assert sorted(times)==[(0,0),(0,1),(1,1)]
 for r in rays:
  i=int(r['event']);assert all(float(r['source_'+a])==float(initial[i][a]) for a in 'xyz')
  assert r['source_event_resource_id']=='smi:invented/event'+str(i) and r['receiver_channel_seed_id']=='XX.MOCK..HHZ' and r['receiver_location_code']==''
 assert all(float(z['v'])==5 for z in rows(q/'initial_grid.csv'))
 for w in weights:
  assert w['original_event_i_resource_id']=='smi:invented/event'+w['i']
  assert w['original_channel_seed_id']=='XX.MOCK..HHZ'
 assert weights[2]['original_metadata_epoch_start']=='1980-01-01T00:00:00Z' and weights[2]['original_metadata_epoch_j_start']=='1990-01-01T00:00:00Z'
 assert weights[2]['original_metadata_epoch_j_end']=='' and float(weights[3]['fixed_row_multiplier'])==0
 ledger=rows(q/'loc1d_iteration_0_trials.csv');trial=next(t for t in ledger if t['objective_evaluated']=='1');step=float(trial['step_fraction'])
 residuals=[];value=0
 for w in weights:
  i,j,k,kj=(int(w[a]) for a in ('i','j','station','station_j'))
  predicted=float(initial[i]['t'])+step*dt[i]+times[i,k]
  if j>=0:predicted-=float(initial[j]['t'])+step*dt[j]+times[j,kj]
  residual=float(w['value'])-predicted;weight=float(w['fixed_row_multiplier'])
  value+=weight*weight*residual*residual;residuals.append(residual)
 assert value==float(trial['objective_after'])
 for i in range(2):assert all(final[i][a]==initial[i][a] for a in ('x','y','z'))
 if accepted_step is not None:
  assert step==accepted_step and trial['status']=='accepted' and len(ledger)==(2 if case=='half' else 3)
  assert [float(z['t']) for z in final]==[.1,.2] and max(map(abs,residuals))==2.**-53
 else:
  assert trial['status']=='objective_rejected' and value>float(trial['objective_before'])>0 and len(ledger)==12
  assert all(x['status']=='objective_rejected' for x in ledger[1:])
  assert all(float(z['t'])==0 for z in final)
 math.append({'case':case,'trial':int(trial['trial']),'step':step,'saved_and_reconstructed_objective':value,'saved_before':float(trial['objective_before']),
              'reconstructed_binary64_residuals':residuals,'exact_arithmetic_on_saved_rounded_residuals':str(sum((Q(float(w['fixed_row_multiplier']))**2*Q(res)**2 for w,res in zip(weights,residuals)),Q(0)))})
# Fatal and no-update outcomes are distinct and contain no fabricated objective.
outcomes={}
for case in ('all','mixed_invalid','state','current','final','mixed','unexpected'):
 q=P/'results/after'/case;mode='dd' if case in ('state','mixed_invalid') else 'loc1d'
 error=(q/'caught.txt').read_text();assert error
 assert not (q/(mode+'_events.csv')).exists() and not (q/(mode+'_grid.csv')).exists()
 ledger_path=q/(mode+'_iteration_0_trials.csv');ledger=rows(ledger_path) if ledger_path.exists() else []
 if case in ('all','mixed_invalid','state'):
  assert len(ledger)==12 and 'No objective-evaluable trial' in error
  assert all(float(t['step_fraction'])==2.**(-i) and t['objective_evaluated']=='0' and t['objective_after']=='' for i,t in enumerate(ledger))
  assert ledger[0]['status']==('invalid_trial_model' if case=='mixed_invalid' else 'local_stopping_rejected')
  assert all(t['status']=='local_stopping_rejected' for t in ledger[1:])
  phase='no_objective_evaluable_trial'
 elif case in ('current','final'):
  ctx=rows(q/(mode+'_failed_forward_context.csv'))[0];phase=ctx['phase']
  assert phase==case+'_model' and ctx['derivatives_requested']=='1'
  assert len(ledger)==(0 if case=='current' else 1)
  if case=='final':assert ledger[0]['status']=='accepted'
 else:
  assert not ledger and 'No objective-evaluable' not in error
  ctx=rows(q/(mode+'_rejected_trial_it_0_ls_0_context.csv'))[0]
  assert ctx['phase']=='line_search_trial' and ctx['derivatives_requested']=='0'
  phase='fatal_'+case+'_trial'
 outcomes[case]={'phase':phase,'trial_rows':len(ledger)}
# Detect mutations across this readback, including source and all original outputs.
for name,h in list(pins.items()):checked(Path(name),h)
review={'status':'passed','reviewer':'ray_math_review','scope':'Independent saved-only source bridge, 28-file parity, selected objective arithmetic and fatal-outcome review; no compiler, action, ray or inverse reevaluation.',
 'summary_sha256':sha(P/'summary.json'),'execution_sha256':sha(P/'execution.json'),'prior_review_sha256':sha(P/'review.json'),
 'candidate_prepared_sha256':sha(C/'prepared.json'),'checker_sha256':sha(Path(__file__)),
 'source_bridge':{'changed_production_files':changed,'old_kernel_sha256':sha(C/'before/src/core.hpp'),'candidate003_patch_identical':True,'frozen_archive_source_members_verified':len(candidate['original_sha256']),'fixture_seams':'Exact declarations and three output/gate/solve call substitutions only.'},
 'verified_unique_pins':len(pins),'executed_artifact_pins':len(s['artifact_sha256']),'all_valid_byte_identical_files':len(parity),
 'saved_assertion_counts':s['controls'],'independent_objective_reconstructions':math,'failure_outcomes':outcomes,
 'findings':['Both sides retain the unchanged old7111 kernel; only the candidate main.cpp policy changes outside the declared test seams.',
             'Half and quarter recovery use the prescribed fixture increments, not a claim that the actual LSQR solve produced those increments; both are separately saved.',
             'Saved ray times, fixed original weights and source-time increments reproduce the selected nonzero and near-zero objectives exactly in binary64 arithmetic.',
             'Pure local trial rejection has no objective; current/final/mixed/unexpected failures remain fatal and distinct from no-evaluable-trial exhaustion.'],
 'limitations':['The 1102 after assertions include repeated fieldwise checks, not independent scientific cases.','This review reconstructs three objective rows; the separate existing nonzero-objective review covers all 11 worse rows.','No native recovery, production adoption, source/model derivative accuracy or global first-arrival assertion follows.']}
with (P/'math_review.json').open('x') as f:json.dump(review,f,indent=2,allow_nan=False);f.write('\n')
print(sha(P/'math_review.json'))
