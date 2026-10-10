#!/usr/bin/env python3
"""Audit saved exact-trial results and independently check two Decimal actions."""
from collections import Counter
import csv
from decimal import Decimal, localcontext
from fractions import Fraction as Q
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUT = ROOT / 'data/development/loma_failed_trial_exact_001'
REPLAY_NAME = 'data/development/loma_failed_search_3426_001'
ARMIJO = Q(float(1e-4))


def need(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            value.update(block)
    return value.hexdigest()


def load(path):
    return json.loads(path.read_text())


def rows(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def bounds(value):
    lo, hi = Q(value['lower_rational']), Q(value['upper_rational'])
    need(lo <= hi and float(lo) == value['lower_display'] and float(hi) == value['upper_display'],
         'Invalid saved interval/display')
    return lo, hi


def classify(gap):
    return 'certified_pass' if gap[1] <= 0 else ('certified_fail' if gap[0] > 0 else 'unresolved_interval')


def difference(a, b):
    return a[0]-b[1], a[1]-b[0]


def decimal(value):
    return Decimal(value.numerator) / Decimal(value.denominator)


def decimal_segment(profile, a, b):
    """Independent exact-Q geometry plus Decimal ln/sqrt; original xyz axes."""
    squared = sum((y-x)**2 for x, y in zip(a, b))
    need(squared > 0, 'Zero-length segment')
    length = decimal(squared).sqrt()

    def velocity(depth):
        for (za, va), (zb, vb) in zip(profile, profile[1:]):
            if za <= depth <= zb:
                return va + (vb-va)*(depth-za)/(zb-za)
        raise ValueError('Depth outside native model')

    dz = b[2]-a[2]
    if not dz:
        return length / decimal(velocity(a[2]))
    low, high = sorted((a[2], b[2]))
    cuts = [low] + [z for z, v in profile if low < z < high] + [high]
    mean_slowness = Decimal(0)
    for left, right in zip(cuts, cuts[1:]):
        vl, vr = velocity(left), velocity(right)
        fraction = decimal((right-left)/abs(dz))
        mean_slowness += (fraction/decimal(vl) if vl == vr else
                         fraction*decimal(vr/vl).ln()/decimal(vr-vl))
    return length * mean_slowness


def main():
    result = load(OUT / 'summary.json')
    execution = load(OUT / 'execution_execution.json')
    need(result['status'] == 'completed_exact_saved_trial_comparison' and
         execution['status'] == 'completed' and execution['return_code'] == 0 and
         execution['summary_sha256'] == sha(OUT / 'summary.json'), 'Exact comparison is not terminal')
    anchors = {name: sha(OUT / name) for name in ('summary.json', 'execution_execution.json',
        'execution_controller.py', 'execution_stdout.log', 'execution_stderr.log', 'input_replay_review.json')}
    need(anchors['execution_controller.py'] == execution['controller_sha256'] and
         anchors['execution_stdout.log'] == execution['stdout_sha256'] and
         anchors['execution_stderr.log'] == execution['stderr_sha256'], 'Controller/log pins differ')

    def rehash():
        for name, digest in result['input_sha256'].items():
            need(sha(ROOT/name) == sha(OUT/'source'/name) == digest, 'Input/source hash differs: '+name)
        for name, digest in result['artifact_sha256'].items():
            need(sha(OUT/name) == digest, 'Artifact hash differs: '+name)
        for name, digest in execution['input_sha256'].items():
            need(sha(ROOT/name) == digest, 'Controller input hash differs: '+name)
        for name, digest in anchors.items():
            need(sha(OUT/name) == digest, 'Anchor changed during review: '+name)

    rehash()
    replay = OUT/'source'/REPLAY_NAME
    neutral = load(OUT/'input_replay_review.json')
    native_rows = rows(replay/'identified_ray.csv')
    need(len(native_rows) == 1 and native_rows[0] == result['native_context'], 'Native context differs')
    native = native_rows[0]
    need(neutral['status'] == 'passed_saved_evidence_review' and
         neutral['summary_sha256'] == sha(replay/'summary.json') and
         sha(ROOT/REPLAY_NAME/'review.json') == anchors['input_replay_review.json'], 'Neutral replay review differs')
    need(result['original_local_flag'] == native['ray_converged'] == '0' and
         result['run_id'] == 'fmm_0.031250_1000' and result['iteration'] == 53 and result['path_nodes'] == 1134,
         'Original run, flag or support changed')
    replay_summary = load(replay/'summary.json')
    for name in ('failed_search_directions.csv', 'failed_search_trials.csv', 'failed_search_decisions.csv'):
        side = load(replay/(name+'.identifiers.json'))
        need(side['file_sha256'] == sha(replay/name) == replay_summary['output_sha256'][name] and
             side['context_sha256'] == sha(replay/'identified_ray.csv') and side['native_context'] == native,
             'Native capture sidecar differs')
    controls = OUT/'source/data/development/loma_failed_trial_controls_002'
    control_review = load(controls/'review.json')
    need(control_review['status'] == 'passed' and
         control_review['controls_summary_sha256'] == sha(controls/'summary.json'), 'Control review differs')
    direction_rows = rows(replay/'failed_search_directions.csv')
    decision_rows = rows(replay/'failed_search_decisions.csv')
    trial_rows = rows(replay/'failed_search_trials.csv')
    xyz = lambda r: tuple(Q(float(r[k])) for k in 'xyz')
    base = [xyz(r) for r in direction_rows]
    q = [tuple(Q(float(r[k])) for k in ('qx', 'qy', 'qz')) for r in direction_rows]
    need(len(base) == 1134 and len(trial_rows) == 24*len(base) and len(decision_rows) == len(result['trials']) == 24,
         'Incomplete trial inventory')
    base_action = bounds(result['exact_base_action_s'])
    derivative = bounds(result['exact_directional_slope_s'])
    need(derivative[1] < 0, 'No certified strict descent direction')
    polygons = []
    for index, (record, decision) in enumerate(zip(result['trials'], decision_rows)):
        need(record['original_decision'] == decision and int(decision['trial_index']) == index,
             'Decision linkage differs')
        block = trial_rows[index*len(base):(index+1)*len(base)]
        need(all(int(row['node']) == n and int(row['trial_index']) == index and
                 row['run_id'] == result['run_id'] and row['observation_index'] == '3426'
                 for n, row in enumerate(block)), 'Trial identity/order differs')
        trial = [xyz(row) for row in block]
        polygons.append(trial)
        changed = sum(a != c or b != d for a, b, c, d in zip(base, base[1:], trial, trial[1:]))
        need(changed == record['changed_edges'], 'Changed-edge count differs')
        step = Q(float(decision['step']))
        need(step == Q(1, 1 << index), 'Attempted step differs')
        intended_error = max(abs(t-x-step*dx) for p, d, u in zip(base, q, trial) for x, dx, t in zip(p, d, u))
        need(float(intended_error) == record['maximum_actual_minus_intended_coordinate_km'],
             'Rounded-coordinate discrepancy differs')
        delta = bounds(record['exact_action_change_s'])
        saved_target = ARMIJO*step*Q(float(decision['directional_slope']))
        need(bounds(record['exact_saved_slope_armijo_target_s']) == (saved_target, saved_target), 'Saved slope target differs')
        saved_gap = difference(delta, (saved_target, saved_target))
        exact_gap = difference(delta, (ARMIJO*step*derivative[0], ARMIJO*step*derivative[1]))
        need(bounds(record['exact_saved_slope_armijo_gap_s']) == saved_gap and
             record['exact_saved_slope_armijo'] == classify(saved_gap), 'Saved slope classification differs')
        need(bounds(record['exact_gradient_armijo_gap_s']) == exact_gap and
             record['exact_gradient_armijo'] == classify(exact_gap), 'Exact slope classification differs')
        action = (base_action[0]+delta[0], base_action[1]+delta[1])
        need(bounds(record['exact_trial_action_s']) == action, 'Trial action interval arithmetic differs')
        for field, origin, scalar in [('exact_minus_binary_trial_action_s', action, 'trial_action_s'),
                                      ('exact_minus_cached_base_action_s', base_action, 'cached_base_action_s'),
                                      ('exact_minus_reevaluated_base_action_s', base_action, 'reevaluated_base_action_s')]:
            value = Q(float(decision[scalar]))
            need(bounds(record[field]) == difference(origin, (value, value)), 'Saved action discrepancy differs')
    passing = [j for j, r in enumerate(result['trials']) if r['exact_saved_slope_armijo'] == 'certified_pass']
    selected = sorted(set(([passing[0]] if passing else [0]) + [23]))
    grid = rows(replay/'inputs/initial_grid.csv')
    profile = sorted(set((Q(float(row['z'])), Q(float(row['v']))) for row in grid))
    need([[str(z), str(v)] for z, v in profile] == result['profile_depth_speed_rational'], 'Profile differs')
    decimal_checks = []
    values = {}
    for precision in (80, 100):
        with localcontext() as ctx:
            ctx.prec = precision
            homogeneous = [(Q(-2), Q(5)), (Q(6), Q(5))]
            need(decimal_segment(homogeneous, (Q(0), Q(0), Q(0)), (Q(3), Q(0), Q(4))) == 1,
                 'Independent homogeneous geometric action control failed')
            affine = [(Q(0), Q(5)), (Q(1), Q(6))]
            need(decimal_segment(affine, (Q(0), Q(0), Q(0)), (Q(0), Q(0), Q(1))) == (Decimal(6)/5).ln(),
                 'Independent affine depth-axis action control failed')
            old_segments = [decimal_segment(profile, a, b) for a, b in zip(base, base[1:])]
            total = sum(old_segments, Decimal(0))
            need(base_action[0] <= Q(total) <= base_action[1], 'Decimal base action outside saved enclosure')
            for index in selected:
                trial = polygons[index]
                delta = Decimal(0)
                calls = 0
                for n, (a, b, c, d) in enumerate(zip(base, base[1:], trial, trial[1:])):
                    if a != c or b != d:
                        delta += decimal_segment(profile, c, d)-old_segments[n]
                        calls += 1
                enclosure = bounds(result['trials'][index]['exact_action_change_s'])
                need(enclosure[0] <= Q(delta) <= enclosure[1], 'Independent Decimal change outside saved enclosure')
                values[(precision, index)] = Q(delta)
                decimal_checks.append(dict(trial_index=index, decimal_precision=precision,
                    base_action_s=str(total), action_change_s=str(delta), changed_edge_evaluations=calls,
                    value_within_saved_rational_enclosure=True))
    agreement = []
    for index in selected:
        difference_precision = abs(values[(80, index)]-values[(100, index)])
        agreement.append(dict(trial_index=index, absolute_precision_difference_rational=str(difference_precision),
                              absolute_precision_difference_s=float(difference_precision)))
    rehash()
    numeric = dict(scope='Independent 80/100-digit Decimal ln/sqrt actions for two saved trial polygons only; not an interval proof.',
        selected_trial_indices=selected, first_passing_trial_available=bool(passing),
        summary_sha256=anchors['summary.json'], checker_sha256=sha(Path(__file__)),
        native_context=native, checks=decimal_checks, precision_agreement=agreement,
        limitations=['Rational binary64 inputs and all grid-plane splits are preserved.',
            'Decimal rounding is not an outward-error bound; enclosure membership and two precisions provide numerical consistency only.',
            'No path optimization, ray tracing, idealized trial substitution or production acceptance occurs.'])
    with (HERE/'decimal_checks.json').open('x') as stream:
        json.dump(numeric, stream, indent=2, allow_nan=False); stream.write('\n')
    review = dict(status='passed_saved_evidence_review', material_issue_found=False,
        summary_sha256=anchors['summary.json'], execution_sha256=anchors['execution_execution.json'],
        neutral_replay_review_sha256=anchors['input_replay_review.json'],
        checker_path=str(Path(__file__).resolve().relative_to(ROOT)), checker_sha256=sha(Path(__file__)),
        decimal_checks_path=str((HERE/'decimal_checks.json').relative_to(ROOT)),
        decimal_checks_sha256=sha(HERE/'decimal_checks.json'), input_hashes_verified=len(result['input_sha256']),
        artifact_hashes_verified=len(result['artifact_sha256']), controller_input_hashes_verified=len(execution['input_sha256']),
        native_identifiers={key: native[key] for key in ('event', 'station', 'source_event_resource_id',
            'source_origin_resource_id', 'receiver_channel_seed_id', 'receiver_channel_fdsn_source_id',
            'receiver_metadata_epoch_start', 'receiver_metadata_epoch_end')},
        all_native_context_and_sidecars_match=True, original_local_flag_preserved='0',
        verified_trials=24, saved_slope_classifications=dict(Counter(r['exact_saved_slope_armijo'] for r in result['trials'])),
        exact_gradient_classifications=dict(Counter(r['exact_gradient_armijo'] for r in result['trials'])),
        every_saved_rational_interval_relation_and_classification_verified=True,
        selected_decimal_trials=selected, decimal_enclosure_membership_checks_passed=4,
        scope='Saved classifications/native/hash readback plus two selected independent high-precision action checks; no ray solve.',
        limitations=numeric['limitations']+['Classifications concern fixed saved rounded polygons, not optimized first arrivals.',
            'No stopping tolerance, scientific accuracy gate, convergence flag or production rule is changed.'])
    with (OUT/'review.json').open('x') as stream:
        json.dump(review, stream, indent=2, allow_nan=False); stream.write('\n')
    print(json.dumps(dict(status=review['status'], review_sha256=sha(OUT/'review.json'),
                         classifications=review['saved_slope_classifications'], selected_decimal_trials=selected), indent=2))


if __name__ == '__main__':
    main()
