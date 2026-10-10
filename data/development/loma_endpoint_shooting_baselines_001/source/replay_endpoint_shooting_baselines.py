#!/usr/bin/env python3
"""Replay only four omitted invented mixed baselines from frozen shooting source."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT / 'data/development/loma_endpoint_shooting_controls_001'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    # Exact terminal selection; no live source or perturbed evaluation is used.
    expected = '0ca944a3fa240721e62b193b7db6361604137d40f34bccabca8566ddf5e61945'
    if sha(ORIGINAL/'summary.json') != expected:
        raise ValueError('Original summary changed')
    original = json.loads((ORIGINAL/'summary.json').read_text())
    for name, digest in original['output_sha256'].items():
        if sha(ORIGINAL/name) != digest:
            raise ValueError('Original output changed: '+name)
    out = (ROOT/args.output).resolve()
    out.relative_to(ROOT)
    out.mkdir(parents=True, exist_ok=False)
    (out/'source').mkdir()
    (out/'inputs').mkdir()
    files = [Path(__file__).resolve(), ORIGINAL/'source/check_endpoint_shooting.py',
             ORIGINAL/'invented_inputs.json', ORIGINAL/'perturbations.json',
             ORIGINAL/'execution.json', ORIGINAL/'summary.json']
    pins = {str(p.relative_to(ROOT)): sha(p) for p in files}
    for path in files:
        where = 'source' if path.suffix=='.py' else 'inputs'
        shutil.copyfile(path, out/where/path.name)
    spec = importlib.util.spec_from_file_location('frozen_shooting_baselines', out/'source/check_endpoint_shooting.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    old_execution = json.loads((out/'inputs/execution.json').read_text())
    environment = dict(python=sys.version, numpy=module.np.__version__, scipy=module.scipy.__version__)
    if environment != old_execution['environment']:
        raise ValueError('Original numerical runtime differs')
    invented = json.loads((out/'inputs/invented_inputs.json').read_text())
    rows = json.loads((out/'inputs/perturbations.json').read_text())
    if invented['settings']['ode'] != module.SETTINGS:
        raise ValueError('Original ODE settings differ')
    case = next(r for r in invented['cases'] if r['name']=='scalar_regime_12')
    nodes = module.np.array(case['nodes']) * module.np.exp(
        -invented['settings']['mixed_amplitude'] * module.np.array(invented['settings']['mixed_log_velocity_coefficients']))
    execution = dict(status='running', command=sys.argv, input_sha256=pins, environment=environment,
                     started_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                     scope='Only omitted mixed unperturbed baselines; no perturbed/native calculations')
    save(out/'execution.json', execution)
    results, comparisons = [], []
    try:
        for setting in module.SETTINGS:
            for both in [False, True]:
                a, b = list(case['a']), list(case['b'])
                b[2] = 0.  # Match the original perturbation-loop literal, including zero's sign.
                if both:
                    a[2] = 0.
                result = module.solve(a, b, nodes, setting)
                results.append(dict(setting=setting['name'], mixed=True, both_bottom=both,
                                    a=a, b=b, original_nodes=nodes.tolist(), result=result))
                save(out/'baseline_candidates.json', results)
                selected = result['selected']
                relevant = [r for r in rows if r['mixed'] and r['setting']==setting['name'] and r['both_bottom']==both]
                for row in relevant:
                    entry = {k:row[k] for k in ['kind','setting','mixed','both_bottom','h','node','side','axis'] if k in row}
                    if selected is None:
                        entry.update(exact_match=False, reason='Supplemental baseline has no selected candidate')
                    else:
                        if row['kind']=='model':
                            value = float(-nodes[row['node']]*selected['kernels'][row['node']])
                            recorded = row['kernel_s']
                        else:
                            value = selected['source' if row['side']==0 else 'receiver'][row['axis']]
                            recorded = row['momentum_component']
                        entry.update(recorded_component=recorded, supplemental_component=value,
                                     exact_match=(value==recorded))
                        if row['kind']=='endpoint' and row['inward_one_sided']:
                            old_perturbed = row['results'][0]['selected']['time']
                            secant = (selected['time']-old_perturbed)/row['h']
                            entry.update(recorded_secant=row['finite_difference_s_per_km'],
                                         supplemental_secant=secant,
                                         exact_secant_match=(secant==row['finite_difference_s_per_km']),
                                         supplemental_minus_recorded_secant=secant-row['finite_difference_s_per_km'])
                    comparisons.append(entry)
                save(out/'comparison.json', comparisons)
                print(setting['name'], 'both_bottom', both, 'selected', selected is not None, flush=True)
        for name, digest in pins.items():
            if sha(ROOT/name) != digest:
                raise ValueError('Pinned input changed: '+name)
        mismatches = sum(not r['exact_match'] or not r.get('exact_secant_match',True) for r in comparisons)
        execution.update(status='completed',return_code=0,
                         finished_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
        save(out/'execution.json',execution)
        summary = dict(status='completed_exact_replay' if mismatches==0 else 'completed_with_preserved_mismatches',
                       original_summary_sha256=expected, input_sha256=pins,
                       replayed_baselines=len(results), stored_component_comparisons=len(comparisons),
                       recomputed_old_boundary_secants=sum('exact_secant_match' in r for r in comparisons),
                       mismatches=mismatches, perturbed_calculations=0, native_calculations=0,
                       limitations=['This is supplemental retention using the same solver/source/settings, not an independent ODE implementation.',
                                    'Dense trajectory checks and successfully solved roots remain numerical candidates, not completeness or envelope certificates.',
                                    'Original raw finite-step failures and frozen artifacts are unchanged.'],
                       output_sha256={str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file()})
        save(out/'summary.json',summary)
        print(json.dumps({k:v for k,v in summary.items() if isinstance(v,(str,int))}),flush=True)
    except Exception as exc:
        execution.update(status='failed',return_code=1,error=str(exc))
        save(out/'execution.json',execution)
        raise


if __name__=='__main__':
    main()
