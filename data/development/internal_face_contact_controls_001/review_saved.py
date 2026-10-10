import json, hashlib, math
from datetime import datetime
from fractions import Fraction as Q
from pathlib import Path
R=Path.cwd(); P=R/'data/development/internal_face_contact_controls_001'
def read(p): return json.loads(p.read_text())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
checks=[]; pins={}; maps={}
def check(label,ok):
 assert ok,label
 checks.append(label)
def pin(p,h):
 p=Path(p); check('hash '+str(p),sha(p)==h); pins[str(p.relative_to(R)) if str(p).startswith(str(R)+'/') else str(p)]=h
pre=read(P/'prepared.json'); s=read(P/'results/summary.json'); ex=read(P/'execution.json'); outer=read(P/'outer_reaping.json'); launch=read(P/'prelaunch_review.json')
for name,base,m in [('input',R,pre['input_sha256']),('prepared',P,pre['output_sha256']),('runtime',Path('/'),pre['runtime_sha256']),('sources',R,s['source_sha256']),('results',P/'results',s['output_sha256']),('execution_outputs',P,ex['output_sha256'])]:
 maps[name]=len(m)
 for path,h in m.items(): pin(base/path,h)
pin(Path(pre['python']['executable']),pre['python']['sha256'])
for rec in (ex,outer,launch): pin(P/'prepared.json',rec['prepared_sha256'])
for rec in (ex,outer):
 pin(P/'prelaunch_review.json',rec['prelaunch_review_sha256']);pin(P/'results/summary.json',rec['summary_sha256'])
pin(P/'execution.json',outer['execution_sha256']);pin(P/'build/observe',s['binary_sha256']);check('binary execution join',s['binary_sha256']==ex['binary_sha256'])
check('terminal and reaped',ex['status']=='completed' and ex['return_code']==0 and ex['outputs_stable'] and not ex['unsettled_groups'] and outer['status']=='completed_and_reaped' and outer['tool_exit_code']==0 and outer['wrapper_pid']==ex['controller_pid'])
check('compile/driver ownership',len(ex['commands'])==2 and all(v['return_code']==0 and v['child_reaped'] for v in ex['commands']))
check('compile command pin',ex['commands'][0]['command']==pre['compile_command'])
check('controls result pass',s['status']=='passed' and len(s['checks'])==30 and all(v['passed'] for v in s['checks']) and not s['unresolved_children'])
check('invented scope',s['invented_only'] and s['no_stationarity_or_first_arrival_claim'] and s['candidate_convergence_status'] is None and all(s[k]==0 for k in ('native_calls','trace_calls','field_calls')))
check('result inventory closure',set(s['output_sha256'])=={str(v.relative_to(P/'results')) for v in (P/'results').rglob('*') if v.is_file() and v.name!='summary.json'})
for v in (P/'logs').glob('*.log'):
 if 'stderr' in v.name or 'compile.stdout' in v.name: check('empty log '+v.name,v.read_bytes()==b'')
check('driver stdout',read(P/'logs/controls.stdout.log')==dict(status='passed',checks=30,summary_sha256=sha(P/'results/summary.json')))
B=lambda x:tuple(Q(v) for v in x)
add=lambda a,b:(a[0]+b[0],a[1]+b[1])
sub=lambda a,b:(a[0]-b[1],a[1]-b[0])
square=lambda a:(Q(0) if a[0]<=0<=a[1] else min(v*v for v in a),max(v*v for v in a))
summ=lambda vs:tuple(sum((v[k] for v in vs),Q(0)) for k in (0,1))
def decimal_hex(rec,key):
 a=rec[key]; b=rec[key+'_hex'];check('decimal/hex count',len(a)==len(b))
 for x,y in zip(a,b): check('decimal/hex exact',math.isfinite(float(x)) and float(x).hex()==float.fromhex(y).hex())
 return [Q(float.fromhex(v)) for v in b]
raws={}; paths={}
for i,cmd in enumerate(s['commands']):
 check('helper ledger',cmd['index']==i and cmd['return_code']==0 and cmd['child_reaped'] and cmd['invented_only'])
 f=P/'results/calls'/('{:03d}_{}'.format(i,cmd['mode']));pin(f.with_suffix('.input'),cmd['input_sha256']);pin(f.with_suffix('.stdout.json'),cmd['stdout_sha256']);pin(f.with_suffix('.stderr.log'),cmd['stderr_sha256'])
 check('helper stderr empty',f.with_suffix('.stderr.log').read_bytes()==b'')
 raw=read(f.with_suffix('.stdout.json'));raws[i]=raw
 check('helper scope',raw['invented_only'] and raw['trace_calls']==raw['field_calls']==0 and raw['mode']==cmd['mode'])
 tokens=f.with_suffix('.input').read_text().split();nx,ny,nz,n=map(int,tokens[:4]);check('grid dimensions',(nx,ny,nz)==(3,2,2))
 vals=[Q(float.fromhex(x)) for x in tokens[4:4+7+12+3*n]]
 check('axes',vals[:7]==list(map(Q,[-1,0,1,-1,4,-1,1])))
 outer_v=vals[7];check('nodal model',outer_v in (5,7) and vals[7:19]==[Q(6) if j%3==1 else outer_v for j in range(12)])
 path=[tuple(vals[19+3*j:22+3*j]) for j in range(n)];paths[i]=path
 check('input/raw path',decimal_hex(raw,'path')==[v for row in path for v in row])
 for key in ('action','endpoint_gradient' if n==2 else 'gradient'):decimal_hex(raw,key)
 if cmd['mode']=='solve':decimal_hex(raw['metric'],'direction')
 if cmd['mode']=='edge':decimal_hex(raw,'reconstructed_core_cuts')
assessments={}
def walk(v):
 if isinstance(v,dict):
  if 'affine_reference' in v:
   i=v['observed']['command'];check('duplicate assessment identity',i not in assessments or assessments[i]==v);assessments[i]=v
  for x in v.values():walk(x)
 elif isinstance(v,list):
  for x in v:walk(x)
walk(s['families']);check('one assessment per call',set(assessments)==set(range(10)))
for i,a in sorted(assessments.items()):
 path=[tuple(map(Q,p)) for p in a['path']];check('assessment raw/geometry',path==paths[i] and a['observed']['record']==raws[i])
 E=a['edge_records'];o=a['affine_reference'];OE=[o] if len(path)==2 else o['edge_records'];check('edge count',len(E)==len(OE)==len(path)-1)
 check('action sum',B(a['action'])==summ([B(v['action']) for v in E]))
 check('affine action sum',len(path)==2 or B(o['action'])==summ([B(v['action']) for v in OE]))
 cs=[[(Q(0),Q(0)) for k in range(3)] for p in path];blocked=set()
 for j,(e,oe) in enumerate(zip(E,OE)):
  check('edge index',e['edge']==j)
  check('affine endpoints',tuple(map(Q,oe['a_exact']))==path[j] and tuple(map(Q,oe['b_exact']))==path[j+1])
  length=B(oe['length']);sq=sum(((y-x)**2 for x,y in zip(path[j],path[j+1])),Q(0));check('length squared enclosure',0<length[0] and length[0]**2<=sq<=length[1]**2)
  aligned=path[j][0]==path[j+1][0]==0;check('blocked edge normal',e['blocked_axes']==oe['blocked_axes']==([0] if aligned else []))
  for side in (0,1):
   for k,v in enumerate(e['components'][side]):
    check('normal None semantics',(v is None)==(aligned and k==0))
    if v is None:blocked.add((j+side,k))
    else:cs[j+side][k]=add(cs[j+side][k],B(v))
 for j,k in blocked:cs[j][k]=None
 check('assembled components',cs[1:-1]==[[None if v is None else B(v) for v in row] for row in a['available_components']])
 check('blocked roster',a['blocked_slots']==[list(v) for v in sorted(blocked) if 0<v[0]<len(path)-1])
 check('available norm sum',B(a['available_squared_norm'])==summ([square(v) for row in cs[1:-1] for v in row if v is not None]))
 ref=[v for row in (o['components'] if len(path)==2 else o['internal_components']) for v in row];actual=decimal_hex(raws[i],'endpoint_gradient' if len(path)==2 else 'gradient');errors=[]
 for k,(x,v,c) in enumerate(zip(actual,ref,a['ordinary_gradient_error']['components'])):
  check('error index',c['component']==k)
  if v is None:check('unavailable error',c['unavailable'] and Q(c['observed'])==x)
  else:
   error=sub((x,x),B(v));check('component error arithmetic',B(c['error'])==error);errors.append(square(error))
 check('error norm arithmetic',B(a['ordinary_gradient_error']['squared_norm'])==summ(errors))
 action=decimal_hex(raws[i],'action')[0];check('action error arithmetic',B(a['action_error'])==sub((action,action),B(o['action'])))
 check('oracle action overlap',max(Q(a['action'][0]),Q(o['action'][0]))<=min(Q(a['action'][1]),Q(o['action'][1])))
fast,slow,cuts=s['families'];searches=fast['searches']+[slow['search']];c=Q(float('1e-4'));trial_results=[]
def directional(v):
 check('directional edge sum',B(v['derivative'])==summ([B(e['derivative']) for e in v['edges']]))
 return B(v['derivative'])
for index,z in enumerate(searches):
 start=z['start'] if index<2 else slow['start'];path=[tuple(map(Q,p)) for p in start['path']]
 d=[tuple(map(Q,p)) for p in z['direction']] if index<2 else [(Q(0),)*3,(Q(1),Q(0),Q(0)),(Q(1),Q(0),Q(0)),(Q(0),)*3]
 nom=directional(z['nominal_directional']);check('nominal negative',nom[1]<0);check('one accepted trial',len(z['trials'])==1)
 tr=z['trials'][0];step=Q(tr['step']);trial=[tuple(map(Q,p)) for p in tr['trial']]
 exact=[tuple(p[k]+step*d0[k] for k in range(3)) for p,d0 in zip(path,d)];check('exact construction',[list(map(str,p)) for p in exact]==tr['unrounded'])
 check('single binary64 rounding',trial==[tuple(Q(float(x)) for x in p) for p in exact]);check('rounded hex',tr['trial_hex']==[[float(x).hex() for x in p] for p in trial]);check('fixed endpoints',trial[0]==path[0] and trial[-1]==path[-1])
 actual=directional(tr['actual_displacement_directional']);check('actual displacement negative',actual[1]<0)
 changes=[dict(edge=j,difference=[str(v) for v in sub(B(tr['assessment']['edge_records'][j]['action']),B(start['edge_records'][j]['action']))]) for j in range(3) if path[j:j+2]!=trial[j:j+2]]
 check('changed edge cancellation',changes==tr['changed_edges']);change=summ([B(v['difference']) for v in changes]);check('paired action arithmetic',change==B(tr['difference']))
 rhs=c*step*nom[0];check('conservative Armijo',Q(tr['conservative_armijo_rhs'])==rhs and change[1]<=rhs)
 slope=float(start['observed']['record']['metric']['slope_binary64']) if index<2 else float(-Q(1,18));core_rhs=float(start['observed']['record']['action'][0])+float(c)*float(step)*slope
 check('recorded binary64 Armijo',core_rhs==tr['recorded_core_rhs'] and float(tr['assessment']['observed']['record']['action'][0])<=core_rhs and tr['recorded_core_acceptance'])
 check('accepted status',tr['accepted'] and tr['status']=='accepted' and tr['halving']==0)
 if index<2:
  moving=[j for j in (1,2) if not z['search_fixed'][3*(j-1)]];events=sorted((-path[j][0]/d[j][0],j) for j in moving)
  check('event ratios',[[str(a),b] for a,b in events]==z['exact_events'] and step==events[0][0] and [j for tau,j in events if tau==step]==tr['hits']==[index+1])
  check('no fast crossing',all(p[0]>=0 for p in trial))
 trial_results.append(dict(name=z['name'],step=str(step),difference=[str(v) for v in change],approximate_change_s=float((change[0]+change[1])/2),contacts=tr['hits']))
check('final fast contact',fast['current']['path'][1][0]==fast['current']['path'][2][0]=='0' and fast['current']['assessment']['blocked_slots']==[[1,0],[2,0]] and fast['temporary_contact'] is None)
check('isolated ordinary descent',fast['searches'][0]['trials'][0]['assessment']['blocked_slots']==[] and directional(fast['isolated_release_directional'])[1]<0)
for sign in ('plus','minus'):
 d=directional(slow[sign]);check('slow exact true-D',d[0]<=-Q(1,18)<=d[1]<0)
check('slow exact affine tangent zero',all(v is None or B(v)==(0,0) for row in slow['start']['affine_reference']['internal_components'] for v in row))
near=[]
for row in cuts['cases']:
 a=row['assessment'];p=[tuple(map(Q,v)) for v in a['path']];exact=-p[0][0]/(p[1][0]-p[0][0]);check('exact near cut',Q(row['exact_cut'])==exact)
 delta=float(p[1][0])-float(p[0][0]);u=(0.0-float(p[0][0]))/delta;insert=abs(delta)>1e-12 and u>1e-10 and u<1-1e-10
 expected=[Q(0),Q(u),Q(1)] if insert else [Q(0),Q(1)];check('frozen core cut classification',list(map(Q,row['reconstructed_core_cuts']))==expected and row['omitted_internal_cut']==row['expected_omission']==(not insert))
 err=B(a['ordinary_gradient_error']['squared_norm']);maximum=max(abs(Q(x)) for v in a['ordinary_gradient_error']['components'] for x in v['error'])
 near.append(dict(name=row['name'],exact_cut=str(exact),omitted=not insert,gradient_squared_error=[str(v) for v in err],approximate_six_component_error_norm_s_per_km=math.sqrt(float(err[1])),approximate_max_component_error_s_per_km=float(maximum),action_error=a['action_error']))
check('actual counts',s['counts']==dict(helper_calls=10,combined_edge_calls=22,affine_edge_references=22,directional_edge_calls=24,fast_searches=2,slow_searches=1))
check('all families completed',all(v['status']=='completed' for v in s['families']))
check('all scope flags unchanged',fast['candidate_convergence_status'] is None and slow['candidate_convergence_status'] is None)
for path,h in pins.items():check('final stable hash',sha(R/path)==h)
review=dict(status='passed',reviewer='earthscope_discovery',reviewed_utc=datetime.utcnow().isoformat()+'Z',prepared_sha256=sha(P/'prepared.json'),summary_sha256=sha(P/'results/summary.json'),execution_sha256=sha(P/'execution.json'),outer_reaping_sha256=sha(P/'outer_reaping.json'),prelaunch_review_sha256=sha(P/'prelaunch_review.json'),source_sha256=s['source_sha256'],pin_map_counts=maps,unique_hashes_verified=len(pins),saved_checks_verified=len(checks),recorded_control_checks=30,actual_counts=s['counts'],trials=trial_results,near_cut_errors=near,method='Read-only stdlib JSON/hash/Fraction readback of closed records and previously reviewed source. No project imports, evaluator calls, quadrature, fit, compile, ray/field/inverse calls or new general checker framework.',findings=['All input/source/runtime and closed output pins match; compiler, control driver and ten helpers report code0/reaped; all stderr and compiler stdout are empty. Root outer receipt binds the same summary/execution and outer reaping.','All ten numeric inputs, decimal/hex outputs and embedded observer records match; exact saved edge/component sums, unavailable normals, squared error norms and action errors reconstruct.','Three accepted trials reconstruct from rational p+alpha*d followed by one binary64 rounding; exact contact ratios, actual-direction signs, unchanged-edge cancellation, conservative interval Armijo and recorded binary64 comparison match.','Both slow release intervals contain -1/18. Aligned normal None is distinct from exact affine tangent zero. Final fast contact is not claimed stationary.','Four near-cut classifications and all six-component gradient-error norms reconstruct; the omitted central crossing preserves a large ordinary-gradient error despite a tiny action error.'],limits=['Source/record integrity and saved arithmetic review, not a repeated independent integral or numerical execution.','The fast contact mask is a temporary proposal subspace, not a physical constraint; no full supporting-vector or convergence certificate at its formed face.','Slow branch-hull zero is not a valid supporting-vector bound for the true directional derivative.','Near-cut errors are observations of the frozen evaluator, not a production correction or tolerance change; all fixtures are invented.'],input_sha256=pins)
with (P/'review.json').open('x') as out:json.dump(review,out,indent=2,sort_keys=True,allow_nan=False);out.write('\n')
print(json.dumps(dict(status=review['status'],checks=len(checks),unique_pins=len(pins),pin_map_counts=maps,review_sha256=sha(P/'review.json'),trials=trial_results,near=[{k:v for k,v in r.items() if k not in ('gradient_squared_error','action_error')} for r in near]),indent=2))
