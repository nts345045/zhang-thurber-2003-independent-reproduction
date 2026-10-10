#!/usr/bin/env python3
"""Read saved trial polygons with exact reciprocal-affine action bounds."""
import argparse
import csv
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import time

ROOT = Path(__file__).resolve().parents[1]
RUN = 'fmm_0.031250_1000'
ARMIJO = Q(float(1e-4))


def need(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def interval(value):
    return dict(lower_rational=str(value[0]), upper_rational=str(value[1]),
                lower_display=float(value[0]), upper_display=float(value[1]))


def floats(row, names):
    return tuple(Q(float(row[k])) for k in names)


def permute(point):
    return point[2], point[0], point[1]


def segment(arithmetic, square_root, profile, a, b, cache):
    key = (tuple(a), tuple(b))
    if key not in cache:
        cache[key] = arithmetic.segment(profile, permute(a), permute(b), square_root)
    return cache[key]


def base_polygon(arithmetic, square_root, profile, points, cache):
    action = arithmetic.point(0)
    gradients = [[arithmetic.point(0) for k in range(3)] for p in points]
    for n, (a, b) in enumerate(zip(points, points[1:])):
        item = segment(arithmetic, square_root, profile, a, b, cache)
        # An aligned kink would need a directional first variation rather than
        # treating one incident-cell support as the ordinary gradient.
        aligned = item['aligned']
        need(not aligned or aligned['minus'] == aligned['plus'],
             'Aligned nonsmooth edge is outside this ordinary-gradient diagnostic')
        action = arithmetic.add(action, item['action'])
        for side, index in (('ga', n), ('gb', n+1)):
            local = item[side]
            for axis, value in enumerate((local[1], local[2], local[0])):
                gradients[index][axis] = arithmetic.add(gradients[index][axis], value)
    return action, gradients


def action_difference(arithmetic, square_root, profile, original, trial, cache):
    need(len(original) == len(trial), 'Changed path topology')
    delta = arithmetic.point(0)
    changed_edges = 0
    for a, b, c, d in zip(original, original[1:], trial, trial[1:]):
        if a == c and b == d:
            continue  # The same exact segment cancels identically.
        old = segment(arithmetic, square_root, profile, a, b, cache)['action']
        new = segment(arithmetic, square_root, profile, c, d, cache)['action']
        delta = arithmetic.add(delta, arithmetic.sub(new, old))
        changed_edges += 1
    return delta, changed_edges


def slope(arithmetic, gradients, direction):
    value = arithmetic.point(0)
    for grad, vector in zip(gradients, direction):
        for g, q in zip(grad, vector):
            value = arithmetic.add(value, arithmetic.mul(g, arithmetic.point(q)))
    return value


def classification(gap):
    if gap[1] <= 0:
        return 'certified_pass'
    if gap[0] > 0:
        return 'certified_fail'
    return 'unresolved_interval'


def controls(arithmetic, square_root):
    records = []
    def check(name, ok):
        records.append(dict(name=name, passed=bool(ok)))
        need(ok, name)
    profile = [(Q(-2), Q(5)), (Q(6), Q(5))]
    points = [(Q(0), Q(0), Q(0)), (Q(3), Q(0), Q(4)), (Q(6), Q(0), Q(0))]
    direction = [(Q(0), Q(0), Q(0)), (Q(0), Q(0), Q(-1)), (Q(0), Q(0), Q(0))]
    cache = {}
    action, gradients = base_polygon(arithmetic, square_root, profile, points, cache)
    derivative = slope(arithmetic, gradients, direction)
    check('homogeneous_action_two_seconds', action[0] <= 2 <= action[1])
    check('homogeneous_whole_direction_derivative', derivative[0] <= Q(-8,25) <= derivative[1])
    unchanged, count = action_difference(arithmetic, square_root, profile, points, points, cache)
    check('identical_segments_cancel_exactly', unchanged == (0,0) and count == 0)
    check('unchanged_trial_rejects_negative_armijo', classification(arithmetic.sub(unchanged,
          arithmetic.mul(derivative, arithmetic.point(ARMIJO)))) == 'certified_fail')
    for h, label in ((Q(1,4), 'resolved'), (Q(1,1 << 60), 'sub_binary64_action')):
        trial = [tuple(x+h*q for x,q in zip(p,d)) for p,d in zip(points,direction)]
        delta, count = action_difference(arithmetic, square_root, profile, points, trial, cache)
        target = arithmetic.mul(derivative, arithmetic.point(ARMIJO*h))
        check(label+'_exact_descent', delta[1] < 0 and count == 2)
        check(label+'_exact_armijo', classification(arithmetic.sub(delta,target)) == 'certified_pass')
        reverse, _ = action_difference(arithmetic, square_root, profile, trial, points, cache)
        check(label+'_reversed_difference', reverse == arithmetic.neg(delta))
        if label == 'sub_binary64_action':
            check('action_decrease_hidden_by_binary64_rounding', float(sum(action)/2) == float(sum(arithmetic.add(action,delta))/2))
            rounded = [tuple(Q(float(x)) for x in p) for p in trial]
            zero, unchanged_count = action_difference(arithmetic, square_root, profile, points, rounded, cache)
            check('rounded_coordinate_collapse_is_explicit', rounded == points and zero == (0,0) and unchanged_count == 0)
    affine = [(Q(-2),Q(3)),(Q(3),Q(8))]
    line = [(Q(-1),Q(0),Q(1)),(Q(0),Q(0),Q(1)),(Q(1),Q(0),Q(1))]
    value, grad = base_polygon(arithmetic,square_root,affine,line,{})
    check('depth_axis_permutation_action', value[0] <= Q(1,3) <= value[1])
    check('depth_axis_permutation_nodal_gradient', grad[1][2][0] <= Q(-1,36) <= grad[1][2][1])
    check('positive_interval_fails', classification((Q(1),Q(2))) == 'certified_fail')
    check('zero_boundary_passes', classification((Q(-1),Q(0))) == 'certified_pass')
    check('overlapping_interval_unresolved', classification((Q(-1),Q(1))) == 'unresolved_interval')
    return dict(status='passed_controls', checks=records,
                scope='Invented closed-form actions, derivatives, cancellation, coordinate rounding and exact Armijo comparisons')


def native(arithmetic, square_root, replay):
    metadata = read(replay/'identified_ray.csv')
    need(len(metadata) == 1 and metadata[0]['observation_index'] == '3426', 'Expected one identified native ray')
    identity = metadata[0]
    summary = json.loads((replay/'summary.json').read_text())
    need(summary['status'] == 'completed_with_original_flags_preserved' and
         summary['observed_paths_and_arrays_match_unobserved'] and summary['selected_full_preflight_result_matches'],
         'Require completed neutral replay with original flags')
    need(summary['native_context'] == identity and identity['ray_converged'] == '0', 'Native context or original flag differs')
    tables = {}
    for name in ('failed_search_directions.csv','failed_search_trials.csv','failed_search_decisions.csv'):
        sidecar = json.loads((replay/(name+'.identifiers.json')).read_text())
        need(sidecar['file_sha256'] == sha(replay/name) == summary['output_sha256'][name] and
             sidecar['context_sha256'] == sha(replay/'identified_ray.csv') and sidecar['native_context'] == identity,
             'Replay table identity/hash mismatch: '+name)
        tables[name] = [r for r in read(replay/name) if r['run_id'] == RUN]
        need(all(r['observation_index'] == '3426' and r['iteration'] == '53' for r in tables[name]),
             'Unexpected failed-search identity/iteration')
    rows = tables['failed_search_directions.csv']
    need(len(rows) == 1134 and [int(r['node']) for r in rows] == list(range(len(rows))), 'Incomplete ordered failed direction')
    original = [floats(r,'xyz') for r in rows]
    direction = [floats(r,('qx','qy','qz')) for r in rows]
    need(all(q == 0 for d in (direction[0],direction[-1]) for q in d), 'Direction moves fixed endpoints')
    need(sha(replay/'paths.csv') == summary['output_sha256']['paths.csv'], 'Original path table hash differs')
    saved_path = [r for r in read(replay/'paths.csv') if r['run_id'] == RUN]
    need(len(saved_path) == len(rows) and all(int(r['node']) == n and r['observation_index'] == '3426' and
         floats(r,'xyz') == original[n] for n,r in enumerate(saved_path)), 'Failed base differs from original selected path')
    need(all(floats(r,('gradient_x','gradient_y','gradient_z')) ==
             floats(rows[n],('gradient_x','gradient_y','gradient_z')) for n,r in enumerate(saved_path) if 0<n<len(rows)-1),
         'Failed direction gradient differs from original saved path')
    grid = read(replay/'inputs/initial_grid.csv')
    axes = [sorted(set(Q(float(r[k])) for r in grid)) for k in 'xyz']
    profile = sorted(set((Q(float(r['z'])),Q(float(r['v']))) for r in grid))
    need(len(profile) == len(axes[2]) and len(grid) == len(axes[0])*len(axes[1])*len(axes[2]) and
         len({floats(r,'xyz') for r in grid}) == len(grid) and all(v>0 for z,v in profile),
         'Expected complete positive depth-only initial model')
    grid_pins = [v for k,v in summary['input_sha256'].items() if k.endswith('/initial_grid.csv')]
    need(len(grid_pins) == 1 and sha(replay/'inputs/initial_grid.csv') == grid_pins[0], 'Replay grid hash mismatch')
    need(all(axes[k][0] <= p[k] <= axes[k][-1] for p in original for k in range(3)), 'Original path outside domain')
    decisions = tables['failed_search_decisions.csv']
    need(len(decisions) == 24 and [int(r['trial_index']) for r in decisions] == list(range(24)), 'Require all24 original trials')
    trial_rows = tables['failed_search_trials.csv']
    need(len(trial_rows) == len(original)*len(decisions), 'Incomplete full trial-path inventory')
    cache = {}
    base_action, gradients = base_polygon(arithmetic,square_root,profile,original,cache)
    exact_slope = slope(arithmetic,gradients,direction)
    need(exact_slope[1] < 0, 'Saved direction is not certified strict descent')
    gradient_error = []
    for n in range(1,len(rows)-1):
        saved = floats(rows[n],('gradient_x','gradient_y','gradient_z'))
        gradient_error.extend(arithmetic.sub(g,arithmetic.point(s)) for g,s in zip(gradients[n],saved))
    records = []
    for record in decisions:
        index = int(record['trial_index']); step = Q(float(record['step']))
        need(step == Q(1,1 << index), 'Unexpected original evaluated step')
        need(Q(float(record['post_loop_halved_step'])) == Q(1,1 << 24), 'Post-loop step differs from recorded exhausted search')
        need(record['valid'] == '1' and record['merged_nodes'] == '0' and int(record['path_nodes']) == len(original),
             'Invalid or merged trial is outside this fixed-topology diagnostic')
        block = [r for r in trial_rows if int(r['trial_index']) == index]
        need([int(r['node']) for r in block] == list(range(len(original))) and all(Q(float(r['step'])) == step for r in block),
             'Trial path order/step mismatch')
        trial = [floats(r,'xyz') for r in block]
        need(trial[0] == original[0] and trial[-1] == original[-1], 'Trial moves endpoints')
        need(all(axes[k][0] <= p[k] <= axes[k][-1] for p in trial for k in range(3)), 'Trial outside original domain')
        cached = Q(float(record['cached_base_action_s'])); current = Q(float(record['reevaluated_base_action_s']))
        trial_binary = Q(float(record['trial_action_s'])); bound_binary = Q(float(record['armijo_rhs_s']))
        saved_slope = Q(float(record['directional_slope']))
        need(saved_slope < 0 and record['binary64_accepted'] == '0' and trial_binary > bound_binary,
             'Original recorded binary64 rejection is inconsistent')
        need(cached == Q(float(decisions[0]['cached_base_action_s'])) and
             current == Q(float(decisions[0]['reevaluated_base_action_s'])) and
             saved_slope == Q(float(decisions[0]['directional_slope'])), 'Base action or slope changes across one search')
        need((record['path_identical_to_base'] == '1') == (trial == original), 'Incorrect identical-path label')
        delta, changed = action_difference(arithmetic,square_root,profile,original,trial,cache)
        saved_target = arithmetic.point(ARMIJO*step*saved_slope)
        exact_target = arithmetic.mul(exact_slope,arithmetic.point(ARMIJO*step))
        gap = arithmetic.sub(delta,saved_target)
        exact_gap = arithmetic.sub(delta,exact_target)
        records.append(dict(original_decision=record,changed_edges=changed,
            maximum_actual_minus_intended_coordinate_km=float(max(abs(t-x-step*q)
                for p,d,u in zip(original,direction,trial) for x,q,t in zip(p,d,u))),
            exact_action_change_s=interval(delta),exact_saved_slope_armijo_target_s=interval(saved_target),
            exact_saved_slope_armijo_gap_s=interval(gap),exact_saved_slope_armijo=classification(gap),
            exact_gradient_armijo_gap_s=interval(exact_gap),exact_gradient_armijo=classification(exact_gap),
            exact_trial_action_s=interval(arithmetic.add(base_action,delta)),
            exact_minus_binary_trial_action_s=interval(arithmetic.sub(arithmetic.add(base_action,delta),arithmetic.point(trial_binary))),
            exact_minus_cached_base_action_s=interval(arithmetic.sub(base_action,arithmetic.point(cached))),
            exact_minus_reevaluated_base_action_s=interval(arithmetic.sub(base_action,arithmetic.point(current)))))
    return dict(status='completed_exact_saved_trial_comparison',native_context=identity,
        original_local_flag='0',run_id=RUN,iteration=53,path_nodes=len(original),
        profile_depth_speed_rational=[[str(v) for v in r] for r in profile],
        exact_base_action_s=interval(base_action),exact_directional_slope_s=interval(exact_slope),
        maximum_component_gradient_discrepancy_s_per_km=max(float(max(map(abs,g))) for g in gradient_error),
        segment_evaluations=len(cache),trials=records,
        limitations=['The saved rounded trial paths are assessed; no idealized or replacement trial is substituted.',
            'Exact reciprocal-affine action bounds apply to this depth-only model and fixed topology.',
            'The coefficient is the exact binary64 constant used for1e-4 in the original source.',
            'Both the saved binary64 gradient slope and independently enclosed continuous gradient slope are compared.',
            'No solver, path, local flag, scientific threshold or production arithmetic is changed.'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--replay',type=Path)
    parser.add_argument('--controls',type=Path)
    parser.add_argument('--review',type=Path)
    args = parser.parse_args()
    out = args.output.resolve(); out.relative_to(ROOT)
    need(not out.exists(),'Use a fresh output directory')
    sources = [Path(__file__).resolve(),ROOT/'diagnostics/check_native_interface_support.py',
               ROOT/'diagnostics/first_arrival_1d_precise_turn_reference.py']
    inputs = list(sources)
    replay = None
    if args.replay:
        need(args.controls and args.review,'Native comparison requires reviewed controls')
        replay = args.replay.resolve(); replay.relative_to(ROOT)
        control = args.controls.resolve(); control.relative_to(ROOT)
        review_path = args.review.resolve(); review_path.relative_to(ROOT)
        reviewed = json.loads(review_path.read_text()); checked = json.loads((control/'summary.json').read_text())
        need(checked['status'] == 'passed_controls' and reviewed['status'] == 'passed' and
             reviewed['controls_summary_sha256'] == sha(control/'summary.json'),'Controls review mismatch')
        for name,digest in checked['input_sha256'].items():
            need(sha(ROOT/name) == digest,'Reviewed arithmetic/helper source changed')
        inputs += [control/'summary.json',review_path,replay/'summary.json',replay/'identified_ray.csv',
                   replay/'inputs/initial_grid.csv',replay/'paths.csv']
        for name in ('failed_search_directions.csv','failed_search_trials.csv','failed_search_decisions.csv'):
            inputs += [replay/name,replay/(name+'.identifiers.json')]
    pins = {str(p.relative_to(ROOT)):sha(p) for p in inputs}
    out.mkdir(parents=True); frozen = out/'source'
    for p in inputs:
        target = frozen/p.relative_to(ROOT); target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(str(p),str(target)); need(sha(target) == pins[str(p.relative_to(ROOT))],'Changed input while freezing')
    arithmetic = module('failed_trial_arithmetic',frozen/'diagnostics/check_native_interface_support.py')
    square_root = module('failed_trial_sqrt',frozen/'diagnostics/first_arrival_1d_precise_turn_reference.py').candidate_sqrt_enclosure
    started = time.monotonic()
    result = native(arithmetic,square_root,frozen/replay.relative_to(ROOT)) if replay else controls(arithmetic,square_root)
    for name,digest in pins.items():need(sha(ROOT/name) == digest,'Input changed during comparison')
    result.update(input_sha256=pins,elapsed_seconds=time.monotonic()-started,
                  artifact_sha256={str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file()})
    with (out/'summary.json').open('x') as stream:
        json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(str(out/'summary.json'))


if __name__ == '__main__':
    main()
