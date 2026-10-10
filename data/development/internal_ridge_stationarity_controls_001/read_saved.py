#!/usr/bin/env python3
"""Saved hashes, identities and counts only; no action or derivative reevaluation."""
from pathlib import Path
import hashlib,json
from decimal import Decimal
P=Path(__file__).resolve().parent;R=P.parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
p=json.loads((P/'prepared.json').read_text());s=json.loads((P/'summary.json').read_text());e=json.loads((P/'execution.json').read_text())
for n,h in p['original_sha256'].items():assert sha(R/n)==h
for n,h in p['runtime_sha256'].items():assert sha(Path(n))==h
for n,h in p['output_sha256'].items():assert sha(P/n)==h
for n,h in s['output_sha256'].items():assert sha(P/n)==h
assert e['status']=='completed' and e['return_code']==0 and e['summary_sha256']==sha(P/'summary.json')
assert all(c['return_code']==0 for c in e['commands'])
x=json.loads((P/'results/exact_controls.json').read_text());c=json.loads((P/'results/checks.json').read_text())
assert len(x['checks'])==s['exact_rational_checks']==37 and all(r['passed'] for r in x['checks'])
assert len(c['numerical_checks'])==s['numerical_consistency_checks']==62 and all(r['passed'] for r in c['numerical_checks'])
assert len(c['comparisons'])==14 and s['direct_segment_evaluations']==2 and s['trace_calls']==s['optimizer_calls']==0
for model in ('fast_ridge','slow_face'):
 rows=[r for r in c['comparisons'] if r['recorded']['model']==model]
 assert len(rows)==7 and sum(r['exact_binary64_x']=='0' for r in rows)==1
assert x['identities']['fast_ridge']['normal_directional_coefficient']=='1/72'
assert x['identities']['slow_face']['normal_directional_coefficient']=='-1/50'
assert x['identities']['false_box_component']['coupled_directional_value']=='-1/4'
print(json.dumps({'status':'passed_saved_readback','verified_original':len(p['original_sha256']),'verified_runtime':len(p['runtime_sha256']),
 'verified_prepared':len(p['output_sha256']),'verified_outputs':len(s['output_sha256']),
 'max_abs_quadrature_action_error_s':str(max(abs(Decimal(v['quadrature_action_error_s'])) for v in c['comparisons'])),
 'max_abs_quadrature_gradient_error_s_per_km':str(max(abs(Decimal(v['quadrature_midpoint_gradient_error_s_per_km'])) for v in c['comparisons']))},indent=2))
