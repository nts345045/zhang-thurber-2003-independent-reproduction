#!/usr/bin/env python3
"""Read saved invented-case objectives, without invoking solver code."""
import csv
import hashlib
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def rows(path):
    with path.open(newline='') as handle:
        return list(csv.DictReader(handle))

def main():
    case = HERE / 'results/after/worse'
    names = ['loc1d_iteration_0_solve_' + suffix + '.csv'
             for suffix in ('context', 'delta', 'weights')]
    names += ['loc1d_iteration_0_trials.csv']
    pins = {str((case / name).relative_to(HERE)): sha(case / name) for name in names}
    pins['summary.json'] = sha(HERE / 'summary.json')
    pins['review.json'] = sha(HERE / 'review.json')
    summary = json.loads((HERE / 'summary.json').read_text())
    assert summary['status'] == 'passed'
    for name in names:
        rel = str((case / name).relative_to(HERE))
        assert summary['artifact_sha256'][rel] == pins[rel]
    context = rows(case / names[0])[0]
    delta, weights = rows(case / names[1]), rows(case / names[2])
    assert context['mode'] == 'loc1d' and int(context['model_columns']) == 0
    assert len(delta) == 8 and all(float(r['increment']) == 0
                                 for r in delta if r['component'] != 't')
    dt = {int(r['event']): float(r['increment']) for r in delta if r['component'] == 't'}
    # Geometry and homogeneous velocity stay fixed; the smoothing penalty is
    # zero. Only the event-time increments change the saved residuals.
    results = []
    for trial in rows(case / names[3]):
        if trial['objective_evaluated'] != '1':
            assert trial['objective_after'] == ''
            continue
        step = float(trial['step_fraction'])
        terms = []
        for row in weights:
            i, j = int(row['i']), int(row['j'])
            predicted_change = step * (dt[i] - (dt[j] if j >= 0 else 0.0))
            residual = float(row['current_residual']) - predicted_change
            terms.append((float(row['fixed_row_multiplier']) * residual) ** 2)
        expected = math.fsum(terms)
        saved = float(trial['objective_after'])
        bound = 64 * sys.float_info.epsilon * max(expected, saved)
        assert expected > float(context['objective_before']) > 0
        assert trial['status'] == 'objective_rejected' and abs(expected - saved) <= bound
        results.append({'trial': int(trial['trial']), 'step_fraction': step,
                        'saved_objective': saved, 'reconstructed_objective': expected,
                        'absolute_difference': abs(expected - saved)})
    assert len(results) == 11
    assert all(sha(HERE / name) == value for name, value in pins.items())
    result = {'status': 'passed', 'reviewer': 'scientific_audit',
              'source_sha256': sha(Path(__file__)), 'input_sha256': pins,
              'scope': 'Saved invented fixture only; fixed row multipliers and original time increments; no solver rerun.',
              'floating_comparison': '64 binary64 eps times positive objective scale, not a scientific accuracy threshold.',
              'results': results,
              'maximum_absolute_difference': max(r['absolute_difference'] for r in results)}
    output = HERE / 'nonzero_objective_review.json'
    with output.open('x') as handle:
        json.dump(result, handle, indent=2)
        handle.write('\n')
    print(sha(output))

if __name__ == '__main__':
    main()
