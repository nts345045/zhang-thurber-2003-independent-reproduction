#!/usr/bin/env python3
"""Read saved invented shooting values; do not execute the shooting evaluator."""
import collections
import hashlib
import json
import math
from pathlib import Path
import sys

sys.dont_write_bytecode = True
folder = Path(sys.argv[1]).resolve()
root = Path(sys.argv[2]).resolve()
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def read(name):
    return json.loads((folder / name).read_text())
summary = read('summary.json')
for name, expected in summary['input_sha256'].items():
    assert digest(root / name) == expected
    assert digest(folder / 'source' / Path(name).name) == expected
for name, expected in summary['output_sha256'].items():
    assert digest(folder / name) == expected
assert read('execution.json')['status'] == 'completed'
rows = read('perturbations.json')
comparisons = read('comparisons.json')
baselines = read('baseline_results.json')
bm = {(r['setting'], r['case']): r['result'] for r in baselines}
assert len(bm) == len(baselines) == 40
assert len(comparisons) == 40 and len(rows) == 160
keys = lambda r: tuple((k, r[k]) for k in ['kind', 'mixed', 'both_bottom', 'node', 'side', 'axis', 'h'] if k in r)
per_setting = {s: {keys(r): r for r in rows if r['setting'] == s} for s in ['base', 'tight']}
assert set(per_setting['base']) == set(per_setting['tight'])
checks = 0
for row in rows:
    if not row.get('same_value_candidates'):
        continue
    pair = row['results']
    if row['kind'] == 'model':
        fd = (pair[1]['selected']['time'] - pair[0]['selected']['time']) / (2 * row['h'])
        assert fd == row['finite_difference_s']
        assert fd - row['kernel_s'] == row['difference_s']
    elif not row['inward_one_sided']:
        fd = (pair[1]['selected']['time'] - pair[0]['selected']['time']) / (2 * row['h'])
        assert fd == row['finite_difference_s_per_km']
        assert fd - row['momentum_component'] == row['difference_s_per_km']
    else:
        # The full unperturbed mixed branch was not saved. Retain the recorded
        # secant; do not reconstruct its baseline action as independent evidence.
        assert row['finite_difference_s_per_km'] - row['momentum_component'] == row['difference_s_per_km']
    checks += 1
model = [r for r in rows if r.get('kind') == 'model']
central = [r for r in rows if r.get('kind') == 'endpoint' and not r['inward_one_sided']]
boundary = [r for r in rows if r.get('kind') == 'endpoint' and r['inward_one_sided']]
groups = collections.defaultdict(list)
for row in boundary:
    groups[(row['setting'], row['mixed'], row['both_bottom'], row['side'])].append(row)
trends = []
for key, group in sorted(groups.items()):
    group.sort(key=lambda r: r['h'], reverse=True)
    errors = [abs(r['difference_s_per_km']) for r in group]
    trends.append(dict(setting=key[0], mixed=key[1], both_bottom=key[2], side=key[3],
                       h_km=[r['h'] for r in group], absolute_secant_discrepancies_s_per_km=errors,
                       successive_error_ratios=[errors[i] / errors[i+1] for i in range(len(errors)-1)],
                       smallest_step_raw_pass_3e_minus_6=errors[-1] <= 3e-6))
precision = []
for key, base in per_setting['base'].items():
    tight = per_setting['tight'][key]
    field = 'finite_difference_s' if base['kind'] == 'model' else 'finite_difference_s_per_km'
    if base.get('same_value_candidates') and tight.get('same_value_candidates'):
        precision.append(dict(key=dict(key), quantity=field, absolute_change=abs(base[field]-tight[field])))
excess = []
for comparison in comparisons:
    if comparison['case'] not in ['scalar_regime_8', 'scalar_regime_12', 'scalar_regime_16']:
        continue
    selected = bm[(comparison['setting'], comparison['case'])]['selected']
    observed = selected['time'] - .25 / 6
    excess.append(dict(setting=comparison['setting'], case=comparison['case'],
                       oracle_excess_s=comparison['oracle']['excess'],
                       observed_excess_s=observed,
                       ratio=observed/comparison['oracle']['excess']))
result = dict(status='saved_arithmetic_readback_passed', summary_sha256=digest(folder/'summary.json'),
              execution_sha256=digest(folder/'execution.json'), source_sha256=digest(Path(__file__)),
              input_pins=len(summary['input_sha256']), output_pins=len(summary['output_sha256']),
              saved_row_arithmetic_checks=checks,
              affine_comparisons=len(comparisons), affine_accuracy_passes=sum(r['accuracy_pass'] for r in comparisons),
              max_affine_time_error_s=max(abs(r['time_error_s']) for r in comparisons),
              max_affine_source_error_s_per_km=max(r['source_error_s_per_km'] for r in comparisons),
              max_affine_receiver_error_s_per_km=max(r['receiver_error_s_per_km'] for r in comparisons),
              model_comparisons=len(model), max_model_discrepancy_s=max(abs(r['difference_s']) for r in model),
              model_discrepancy_by_h=[dict(h=h, comparisons=sum(r['h']==h for r in model),
                                          maximum_absolute_discrepancy_s=max(abs(r['difference_s']) for r in model if r['h']==h))
                                      for h in sorted(set(r['h'] for r in model), reverse=True)],
              central_endpoint_comparisons=len(central),
              max_central_endpoint_discrepancy_s_per_km=max(abs(r['difference_s_per_km']) for r in central),
              boundary_comparisons=len(boundary), boundary_trends=trends,
              boundary_raw_failures_3e_minus_6=sum(abs(r['difference_s_per_km']) > 3e-6 for r in boundary),
              maximum_model_fd_precision_change_s=max(r['absolute_change'] for r in precision if r['quantity']=='finite_difference_s'),
              maximum_endpoint_fd_precision_change_s_per_km=max(r['absolute_change'] for r in precision if r['quantity']=='finite_difference_s_per_km'),
              precision_comparisons=precision, affine_excess_ratios=excess,
              limitations=['No shooting, ODE, root search or native calculation was rerun.',
                           'Mixed unperturbed branch trajectories/actions were not saved; stored baseline kernels/momenta and secants are source-audited outputs, not independently reintegrated here.',
                           'Finite differences do not certify derivatives or global branch selection.',
                           'All raw boundary discrepancies are retained; none are relabeled as numerical accuracy passes.'])
path = folder / 'saved_readback.json'
with path.open('x') as handle:
    json.dump(result, handle, indent=2, allow_nan=False)
    handle.write('\n')
print(json.dumps({k:v for k,v in result.items() if not isinstance(v,list)},indent=2))
