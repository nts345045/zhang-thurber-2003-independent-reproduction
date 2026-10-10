#!/usr/bin/env python3
"""Freeze the same complete LON inputs for the separately reviewed arithmetic variant."""
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'diagnostics'))
from run_loma_initial_precise_turn_reference import (sha, checked_inputs, checked_reference_review,
    table, geometry, REFERENCE_SHA256, REFERENCE_REVIEW, REFERENCE_REVIEW_SHA256,
    REFERENCE_CHECKS, REFERENCE_CHECKS_SHA256)


def main():
    original=ROOT/'data/development/loma_lon_initial_reference_plan_001/plan.json'
    failed=ROOT/'data/development/loma_lon_initial_reference_001'
    data=ROOT/'data/loma_lon_analytic_001'
    plan=json.loads(original.read_text())
    files,expected=checked_inputs(data,original)
    evidence=checked_reference_review()
    summary=json.loads((failed/'summary.json').read_text())
    ledger=json.loads((failed/'execution.json').read_text())
    if ledger['status']!='completed' or ledger['summary_sha256']!=sha(failed/'summary.json'):
        raise ValueError('Original failed-reference attempt is not terminal and hash-bound')
    if summary['invalid_reference_pair_indices']!=[8156] or summary['reference_comparison_ready']:
        raise ValueError('Original failed-reference evidence changed')
    _,events=table(data/'initial_events.csv');_,stations=table(data/'stations.csv');_,grid=table(data/'initial_grid.csv')
    profile,box=geometry(events,stations,grid,expected)
    if profile!=[tuple(row) for row in plan['initial_profile_depth_velocity']] or box!=plan['original_box_km']:
        raise ValueError('Original initial profile or finite box changed')
    paths=[Path(__file__).resolve(),ROOT/'diagnostics/run_loma_initial_precise_turn_reference.py',
        ROOT/'diagnostics/first_arrival_1d_precise_turn_reference.py']
    plan.update(scope='Recompute every unchanged LON initial pair using the independently reviewed rational turning-speed reconstruction; no forward or inverse calculation',
        source_sha256={str(p.relative_to(ROOT)):sha(p) for p in paths},
        numerical_reference_sha256=REFERENCE_SHA256,
        numerical_review_sha256={REFERENCE_REVIEW:REFERENCE_REVIEW_SHA256,REFERENCE_CHECKS:REFERENCE_CHECKS_SHA256},
        preserved_previous_attempt={str(p.relative_to(ROOT)):sha(p) for p in [original,failed/'summary.json',failed/'execution.json',failed/'independent_review.json']},
        arithmetic_change='Retain an exact rational enclosure midpoint of sqrt(u0^2+r^2) during turning-candidate evaluation and sampling; root intervals, physical formulas and gates unchanged',
        comparison_required='Inspect all candidate counts, validity, branch selections and times against preserved attempt001 after completion',
        limitations=plan['limitations']+['Previous attempt001 remains invalid for pair8156; no result is overwritten or accepted retrospectively.'])
    with (HERE/'plan.json').open('x') as f:json.dump(plan,f,indent=2,allow_nan=False);f.write('\n')
    checked_inputs(data,HERE/'plan.json')
    print(json.dumps(dict(status='ready',expected_pairs=expected[0]*expected[1],numerical_reference_sha256=REFERENCE_SHA256)))

if __name__=='__main__':main()
