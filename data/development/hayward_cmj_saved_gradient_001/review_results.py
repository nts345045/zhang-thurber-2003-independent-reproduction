#!/usr/bin/env python3
"""Saved CSV/native/rational readback only; no path_eval, field, or ray calls."""
import csv,hashlib,json,math
from fractions import Fraction as Q
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def read(p):
 with p.open() as f:return list(csv.DictReader(f))
def main():
 p=json.loads((HERE/'prepared.json').read_text());s=json.loads((HERE/'summary.json').read_text());e=json.loads((HERE/'execution.json').read_text())
 assert e['status']=='completed' and e['return_code']==0 and e['summary_sha256']==sha(HERE/'summary.json')
 assert [x['stage'] for x in e['commands']]==['compile_old','evaluate_old','compile_D','evaluate_D'] and all(x['return_code']==0 for x in e['commands'])
 assert s['fixed_path_evaluations']==e['fixed_path_evaluations_completed']==4 and s['trace_calls']==s['field_constructions']==0
 assert e['prepared_sha256']==s['prepared_sha256']==sha(HERE/'prepared.json')
 assert e['prelaunch_review_sha256']==sha(HERE/'prelaunch_review.json')
 pins={}
 for mapping,base in [(p['original_sha256'],ROOT),(p['runtime_sha256'],Path('/')),(p['output_sha256'],HERE),(s['output_sha256'],HERE)]:
  for n,h in mapping.items():
   path=base/n;assert sha(path)==h,str(path);pins[str(path)]=h
 replay=ROOT/p['replay_package'];native_cells=0;findings=[]
 for variant in ('old','D'):
  original_paths=read(replay/'results'/variant/'paths.csv');original_status=read(replay/'results'/variant/'status.csv')
  nodes=read(HERE/'results'/variant/'node_gradients.csv');norms=read(HERE/'results'/variant/'norms.csv');tops=read(HERE/'results'/variant/'top_components.csv')
  assert len(nodes)==len(original_paths) and len(norms)==2 and len(tops)==80
  for row,old in zip(nodes,original_paths):
   for k,v in old.items():assert row[k]==v;native_cells+=1
   assert row['variant']==variant
  for j,original in enumerate(original_status):
   saved=norms[j]
   for k,v in original.items():assert saved[k]==v;native_cells+=1
   assert saved['ray_converged']=='0' and saved['ray_derivatives_evaluated']=='0' and all(saved['source_d'+a]=='' for a in 'xyz')
   assert saved['diagnostic_raw_norm']==saved['ray_raw_gradient'] and saved['diagnostic_projected_norm']==saved['ray_projected_gradient']
   selected=[r for r in nodes if r['event']==saved['event'] and r['station']==saved['station']]
   case=s['cases'][(0 if variant=='old' else 2)+j];assert case['saved_status_and_diagnostic_norms']==saved
   assert [int(r['node']) for r in selected]==list(range(len(selected)))
   assert case['free_node_count']==len(selected)-2 and int(saved['free_components'])==3*(len(selected)-2)
   near=[];totals={b:[Q(0)]*3 for b in ('raw','projected')};near_totals={b:[Q(0)]*3 for b in totals};components=[]
   for index,r in enumerate(selected):
    free=0<index<len(selected)-1;assert int(r['is_free'])==free
    if not free:
     assert all(r[b+'_g'+a]=='' for b in totals for a in 'xyz');continue
    within=abs(Q(float(r['x'])))<Q(1,1000000)
    if within:near.append(index)
    for ax,a in enumerate('xyz'):
     item={'row':r,'axis':a}
     for b in totals:
      value=float(r[b+'_g'+a]);assert math.isfinite(value);square=Q(value)**2;totals[b][ax]+=square
      if within:near_totals[b][ax]+=square
      item[b]=square
     components.append(item)
   assert near==case['near_face_free_nodes'] and len(near)==case['near_face_free_node_count']
   fractions={}
   for b in totals:
    total=sum(totals[b],Q(0));report=case['squared_component_decomposition'][b]
    expected={'total_squared_norm':total,'near_face_x_fraction_of_total':near_totals[b][0]/total,'near_face_all_axes_fraction_of_total':sum(near_totals[b],Q(0))/total}
    for k,v in expected.items():assert report[k]['exact_rational']==str(v) and report[k]['float_display']==float(v)
    for k,values in [('axis_squared_norm',totals[b]),('near_face_axis_squared_norm',near_totals[b])]:
     for a,v in zip('xyz',values):assert report[k][a]['exact_rational']==str(v) and report[k][a]['float_display']==float(v)
    # Positive squared summation plus rounded norm: a conservative binary64
    # operation-count bound, not a scientific ray/stationarity threshold.
    n=int(saved['free_components']);eps=Q(1,2**52);bound=(n+4)*eps/(1-(n+4)*eps)
    assert abs(Q(float(saved['diagnostic_'+b+'_norm']))**2-total)/total <= bound
    expected_top=sorted(components,key=lambda c:(-c[b],int(c['row']['node']),c['axis']))[:20]
    actual_top=[r for r in tops if r['event']==saved['event'] and r['station']==saved['station'] and r['rank_basis']==b]
    assert len(actual_top)==20
    for rank,(a,x) in enumerate(zip(actual_top,expected_top),1):
     assert int(a['rank'])==rank and a['axis']==x['axis'] and a['exact_component_square']==str(x[b])
     for k,v in x['row'].items():assert a[k]==v;native_cells+=1
     assert a['component_s_per_km']==x['row'][b+'_g'+x['axis']] and float(a['squared_fraction_of_total'])==float(x[b]/total)
    fractions[b]=float(expected['near_face_x_fraction_of_total'])
   assert case['diagnostic_action_minus_recorded_action_s']==float(saved['diagnostic_path_action'])-float(saved['ray_time'])
   findings.append({'variant':variant,'event':int(saved['event']),'station':int(saved['station']),'native_status':original,'near_face_free_nodes':near,'near_x_normal_fraction_of_total_squared_norm':fractions})
 for path,h in pins.items():assert sha(path)==h,path
 review={'status':'passed','reviewer':'scientific_audit','summary_sha256':sha(HERE/'summary.json'),'execution_sha256':sha(HERE/'execution.json'),'source_sha256':sha(Path(__file__)),'verified_pin_count':len(pins),'native_cell_comparisons':native_cells,'findings':findings,'scope':'All original node/status fields, finite/free component inventory, exact binary64-rational totals/axis/near-face fractions/top20 orders, norm arithmetic consistency and four-call terminal provenance independently reconstructed from saved CSVs. No action, gradient, trace, field, inverse or reference evaluation.','limitations':'Descriptive near-face norm concentration is not a stationarity/causation/first-arrival certificate. Original false flags and derivative-disabled source/model status remain unchanged.'}
 with (HERE/'review.json').open('x') as f:json.dump(review,f,indent=2,allow_nan=False);f.write('\n')
 print(sha(HERE/'review.json'))
if __name__=='__main__':main()
