import csv,gzip,hashlib,itertools,json,math
from pathlib import Path
from collections import Counter
ROOT=Path.cwd();P=ROOT/'data/development/loma_lom_initial_accuracy_001'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def need(x,m):
 if not x:raise ValueError(m)
def load(p):
 with p.open() as f:return list(csv.DictReader(f))
s=json.loads((P/'summary.json').read_text());e=json.loads((P/'execution.json').read_text())
need(sha(P/'summary.json')=='72ed25dbde4bc14b1e0967f6a1880ff396683735c723b41f633e081a085fe6bb','summary changed')
need(e['status']=='completed' and e['summary_sha256']==sha(P/'summary.json'),'terminal ledger')
for n,h in s['output_sha256'].items():need(sha(P/n)==h,'artifact '+n)
for n,h in s['input_source_sha256'].items():
 need(sha(ROOT/n)==h,'original '+n)
 copied=P/s['frozen_input_mapping'][n]
 if n.endswith('/dd_preflight_ray_status.csv'):
  x=hashlib.sha256()
  with gzip.open(str(copied),'rb') as f:
   for b in iter(lambda:f.read(1048576),b''):x.update(b)
  need(x.hexdigest()==h,'decompressed status hash')
 else:need(sha(copied)==h,'frozen copy '+n)
cap=P/'inputs/preflight/preflight_execution_at_capture.json';ledger=json.loads(cap.read_text())
need(sha(cap)==s['preflight_execution_at_capture_sha256'] and ledger['status']==s['preflight_status_at_capture'],'capture')
commands=[c for c in ledger['completed_commands'] if c['stage']=='initial_matrix_preflight']
need(len(commands)==1 and commands[0]==s['initial_matrix_command'] and commands[0]['return_code']==0,'completed stage')
need(s['overall_preflight_assessed'] is False and s['scientific_pass'] is False,'status distinction')
pre=P/'inputs/preflight';ref=P/'inputs/reference'
ev=load(pre/'initial_events.csv');st=load(pre/'stations.csv');grid=load(pre/'initial_grid.csv')
need(len(ev)==724 and len(st)==52,'geometry counts')
for n in ['initial_events.csv','stations.csv','initial_grid.csv']:need(sha(pre/n)==sha(ref/'inputs'/n),'geometry byte '+n)
box=[(min(float(r[a]) for r in grid),max(float(r[a]) for r in grid)) for a in 'xyz']
counts=Counter();bad=[];source_bad=[];local_bad=[];max_time=max_norm=0.0;seen=0;nonzero_source_t=0
flags=['ray_finite','ray_path_in_domain','ray_exact_source_endpoint','ray_exact_receiver_endpoint','ray_initialization_attempted','ray_initialization_succeeded','ray_converged']
with gzip.open(str(P/'comparison.csv.gz'),'rt',newline='') as cf,gzip.open(str(pre/'dd_preflight_ray_status.csv.gz'),'rt',newline='') as pf,gzip.open(str(ref/'references.csv.gz'),'rt',newline='') as rf,gzip.open(str(ref/'certificates.jsonl.gz'),'rt') as jf:
 for q,(c,r,f,line) in enumerate(itertools.zip_longest(csv.DictReader(cf),csv.DictReader(pf),csv.DictReader(rf),jf)):
  need(None not in (c,r,f,line),'unequal full support');j=json.loads(line);i,k=divmod(q,len(st));need(i<len(ev),'extra ray')
  need((c['comparison_row'],c['event'],c['station'])==(str(q),str(i),str(k)),'comparison order')
  need((r['event'],r['station'],f['pair_index'],f['event'],f['station'])==(str(i),str(k),str(q),str(i),str(k)),'raw/ref order')
  need([j[a] for a in ['pair_index','event','station']]==[q,i,k] and j['source_time_included'] is False,'certificate join/time')
  need(all(c[a]==b for a,b in r.items()),'raw row not lossless')
  for prefix,native in [('source_',ev[i]),('receiver_',st[k])]:
   for a,b in native.items():
    need(f[prefix+a]==b,'reference native '+prefix+a)
    if a not in ('id','x','y','z','t'):need(r[prefix+a]==b,'raw native '+prefix+a)
   for axis,lim in zip('xyz',box):
    x=float(native[axis]);need(float(r[prefix+axis])==float(format(x,'.12g')),'raw rounded coordinates')
    for side,v in zip(['lower','upper'],lim):
     key=prefix+'on_'+axis+'_'+side+'_face';need(int(f[key])==int(x==v) and c['reference_'+key]==f[key],'boundary flag')
  need(float(r['source_t'])==float(format(float(ev[i]['t']),'.12g')),'source t preserve')
  nonzero_source_t+=float(r['source_t'])!=0
  for a,b in c.items():
   if a.startswith('reference_') and a not in ['reference_eligible','reference_complete','reference_valid']:need(f[a[len('reference_'):]]==b,'copied reference field '+a)
  v=j['reference'];first=v['first_arrival'];g=first['source_derivative_s_per_km']
  need(int(f['reference_complete'])==int(v['complete']) and int(f['reference_valid'])==int(v['reference_valid']),'reference validity')
  need(int(f['candidate_count'])==len(v['candidates']) and int(f['near_tie_count'])==len(v['near_ties']),'candidate count')
  need(f['branch']==first['kind'] and float(f['time_s'])==first['time_s'],'reference time/branch')
  need(all(float(f['source_d'+a+'_s_per_km'])==g[n] for n,a in enumerate('xyz')),'reference gradient order')
  eligible=bool(v['complete'] and v['reference_valid'] and len(v['near_ties'])==1 and all(math.isfinite(z) for z in [first['time_s']]+g))
  numeric=[float(r[a]) for a in ['ray_time','source_dx','source_dy','source_dz','ray_projected_gradient','ray_raw_gradient']]
  finite=all(math.isfinite(z) for z in numeric) and numeric[0]>=0
  dt=numeric[0]-first['time_s'];de=[numeric[n+1]-g[n] for n in range(3)];dn=math.sqrt(sum(z*z for z in de))
  need(float(c['time_error_s'])==dt and float(c['source_error_euclidean_norm_s_per_km'])==dn,'error arithmetic')
  need(all(float(c['source_d'+a+'_error_s_per_km'])==de[n] for n,a in enumerate('xyz')),'error vector')
  values=dict(reference_eligible=eligible,modeled_values_finite=finite,numerically_compared=eligible and finite,time_limit_pass=eligible and finite and abs(dt)<=2.5e-5,source_vector_limit_pass=eligible and finite and dn<=3e-6,original_flags_and_path_pass=all(r[a]=='1' for a in flags) and int(r['ray_path_points'])>=2 and finite)
  values['scientific_pass']=values['time_limit_pass'] and values['source_vector_limit_pass'] and values['original_flags_and_path_pass']
  for a,b in values.items():need(int(c[a])==int(b),'derived flag '+a);counts[a]+=b
  counts['saved_local_converged']+=r['ray_converged']=='1';max_time=max(max_time,abs(dt));max_norm=max(max_norm,dn)
  if not values['scientific_pass']:bad.append(q)
  if not values['source_vector_limit_pass']:source_bad.append(dict(row=q,event_resource_id=ev[i]['event_resource_id'],origin_resource_id=ev[i]['origin_resource_id'],source_z=float(ev[i]['z']),branch=f['branch'],z_upper=int(f['source_on_z_upper_face']),error=de))
  if r['ray_converged']!='1':local_bad.append(q)
  seen=q+1
need(seen==724*52==s['rows'],'complete count');need(dict(counts)==s['counts'],'counts');need(max_time==s['maximum_absolute_time_error_s'] and max_norm==s['maximum_source_error_euclidean_norm_s_per_km'],'maxima')
need(bad==[v['comparison_row'] for v in s['failures']],'failure inventory')
for fail in s['failures']:
 i,k=divmod(fail['comparison_row'],52)
 need(fail['event']==i and fail['station']==k and fail['event_resource_id']==ev[i]['event_resource_id'] and fail['origin_resource_id']==ev[i]['origin_resource_id'],'failure event join')
 for a in ['network_code','station_code','location_code','channel_code','channel_seed_id','channel_fdsn_source_id','metadata_epoch_start','metadata_epoch_end']:need(fail[a]==st[k][a],'failure receiver join')
for n,h in s['output_sha256'].items():need(sha(P/n)==h,'post artifact '+n)
for n,h in s['input_source_sha256'].items():need(sha(ROOT/n)==h,'post original '+n)
review=dict(status='passed',scope='Independent saved-table/native/error/hash readback only; no reference enumeration, ray tracing, inversion or sampled-stage assessment',summary_sha256=sha(P/'summary.json'),execution_sha256=sha(P/'execution.json'),comparison_sha256=sha(P/'comparison.csv.gz'),comparer_source_sha256=sha(P/'source/compare_loma_initial_rays.py'),review_helper_sha256=sha(ROOT/'tmp/review_loma_accuracy_saved.py'),verified_output_hashes=len(s['output_sha256']),verified_original_and_frozen_input_hashes=len(s['input_source_sha256']),decompressed_full_ray_hash_matches=True,verified_pairs=seen,all_raw_status_fields_preserved=True,all_native_source_receiver_fields_match=True,ordered_indices_complete=True,reference_flags_candidate_counts_and_xyz_gradients_match_certificates=True,boundary_flags_match_exact_saved_geometry=True,pure_time_and_euclidean_source_error_arithmetic_matches=True,source_time_offsets_preserved_and_excluded=True,nonzero_source_time_rows=nonzero_source_t,counts=dict(counts),maximum_absolute_time_error_s=max_time,maximum_source_error_norm_s_per_km=max_norm,scientific_pass=False,all_failed_rows_preserved=True,source_failures=dict(count=len(source_bad),all_source_z_16=all(x['source_z']==16 for x in source_bad),all_bottom_boundary=all(x['branch']=='bottom_boundary' and x['z_upper']==1 for x in source_bad),unique_source_events=len(set(x['event_resource_id'] for x in source_bad)),max_absolute_error_xyz=[max(abs(x['error'][n]) for x in source_bad) for n in range(3)],minimum_z_error=min(x['error'][2] for x in source_bad),maximum_z_error=max(x['error'][2] for x in source_bad)),local_failure_comparison_rows=local_bad,failure_join='summary.json failures and comparison.csv.gz retain event/origin/channel/epoch identifiers for every failure',material_issue_found=False,limitations=['Review success validates preserved evidence, not numerical acceptance;49 rows still fail a check.','The boundary-only error pattern is descriptive and does not establish causality.','The captured overall preflight was still running; only its completed full matrix stage is assessed.','No high-precision action or reference arithmetic was rerun.'])
with (P/'review.json').open('x') as f:json.dump(review,f,indent=2);f.write('\n')
print(json.dumps(review,indent=2))
