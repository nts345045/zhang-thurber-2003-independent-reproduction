#!/usr/bin/env python3
"""Bound two saved segment actions and one fixed-polygon nodal derivative."""
import argparse
import csv
from decimal import localcontext
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import shutil
import time

ROOT = Path(__file__).resolve().parents[1]
OBSERVER = ROOT/'data/development/loma_initial_failure_3426_001'
RUN = 'fmm_0.031250_1000'
NODE = 484
IDS = ('source_event_resource_id', 'source_origin_resource_id',
       'receiver_channel_seed_id', 'receiver_channel_fdsn_source_id',
       'receiver_metadata_epoch_start', 'receiver_metadata_epoch_end')


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


def permute(point):
    # The reviewed primitive varies along its first coordinate. Here velocity
    # varies along physical z: (x,y,z) -> (z,x,y), with no sign change.
    return point[2], point[0], point[1]


def adjacent(arithmetic, square_root, profile, points):
    a, c, b = [permute(p) for p in points]
    left = arithmetic.segment(profile, a, c, square_root)
    right = arithmetic.segment(profile, c, b, square_root)
    local = [arithmetic.add(x, y) for x, y in zip(left['gb'], right['ga'])]
    return arithmetic.add(left['action'], right['action']), [local[1], local[2], local[0]]


def shifted(points, axis, h):
    result = [list(p) for p in points]
    result[1][axis] += h
    return result


def controls(arithmetic, square_root):
    checks = []
    records = []
    def check(name, ok):
        checks.append(dict(name=name, passed=bool(ok)))
        need(ok, name)
    homogeneous = [(Q(-2), Q(5)), (Q(6), Q(5))]
    triangle = [(Q(0), Q(0), Q(0)), (Q(3), Q(0), Q(4)), (Q(6), Q(0), Q(0))]
    value, gradient = adjacent(arithmetic, square_root, homogeneous, triangle)
    check('homogeneous_two_segment_action', value[0] <= 2 <= value[1])
    for axis, exact in enumerate((Q(0), Q(0), Q(8, 25))):
        check('homogeneous_axis_permutation_'+str(axis), gradient[axis][0] <= exact <= gradient[axis][1])
    decrease, _ = adjacent(arithmetic, square_root, homogeneous, shifted(triangle, 2, Q(-1, 4)))
    check('homogeneous_negative_z_has_certified_action_decrease', decrease[1] < value[0])
    affine = [(Q(-2), Q(3)), (Q(4), Q(6))]
    crossing = [(Q(-2), Q(3)), (Q(0), Q(5)), (Q(3), Q(6))]
    oblique = [(Q(-1), Q(2), Q(-1)), (Q(1, 3), Q(1, 4), Q(1, 3)),
               (Q(3, 2), Q(-1), Q(2))]
    tiny = Q(1, 1 << 24)
    near = [(Q(0), Q(0), -tiny), (Q(1, 32), Q(1, 100), tiny),
            (Q(1, 16), Q(0), -tiny/4)]
    equal = [(Q(-2), Q(0), Q(1)), (Q(0), Q(0), Q(1)), (Q(1), Q(0), Q(1))]
    cases = [('affine_oblique', affine, oblique), ('crossing_oblique', crossing, oblique),
             ('near_plane_small_nonzero_depth_difference', crossing, near), ('smooth_equal_depth', affine, equal)]
    with localcontext() as context:
        context.prec = 200
        h = Q(1, 10**35)
        for name, profile, points in cases:
            action, grad = adjacent(arithmetic, square_root, profile, points)
            reverse, reverse_grad = adjacent(arithmetic, square_root, profile, list(reversed(points)))
            check(name+'_endpoint_reversal', action == reverse and grad == reverse_grad)
            for axis in range(3):
                actions = []
                for sign in (-1, 1):
                    a, c, b = [permute(p) for p in shifted(points, axis, sign*h)]
                    actions.append(arithmetic.decimal_action(profile, a, c)+arithmetic.decimal_action(profile, c, b))
                fd = (actions[1]-actions[0])/arithmetic.decimal_value(2*h)
                check(name+'_independent_decimal_fd_'+str(axis),
                      arithmetic.decimal_value(grad[axis][0]) <= fd <= arithmetic.decimal_value(grad[axis][1]))
                records.append(dict(case=name, axis=axis, gradient=interval(grad[axis]),
                                    decimal_central_difference=str(fd), h_rational=str(h)))
            if name == 'smooth_equal_depth':
                check('equal_depth_closed_form', grad[2][0] <= Q(-1, 27) <= grad[2][1])
    return dict(checks=checks, cases=records,
                scope='Invented fixed-polygon arithmetic controls only; Decimal differences are consistency checks, not interval proofs')


def native(arithmetic, square_root, frozen):
    base = frozen/OBSERVER.relative_to(ROOT)
    summary = json.loads((base/'summary.json').read_text())
    review = json.loads((base/'review.json').read_text())
    need(summary['status'] == 'completed_with_original_flags_preserved' and
         summary['selected_full_preflight_result_matches'] and summary['observed_paths_and_arrays_match_unobserved'],
         'Require completed neutral observer')
    need(review['status'] == 'passed_saved_evidence_review' and review['summary_sha256'] == sha(base/'summary.json'),
         'Require hash-bound independent observer review')
    for name in ('paths.csv', 'results.csv', 'history.csv', 'path_gradient_checks.csv', 'identified_ray.csv'):
        need(sha(base/name) == summary['output_sha256'][name], 'Changed observer artifact '+name)
    contexts = read(base/'identified_ray.csv')
    need(len(contexts) == 1, 'Nonunique native identity')
    identity = contexts[0]
    need(summary['native_context'] == identity, 'Observer summary native context differs')
    sidecar = json.loads((base/'paths.csv.identifiers.json').read_text())
    need(sidecar['file_sha256'] == sha(base/'paths.csv') and
         sidecar['context_sha256'] == sha(base/'identified_ray.csv') and sidecar['native_context'] == identity,
         'Path identity sidecar mismatch')
    path = [r for r in read(base/'paths.csv') if r['run_id'] == RUN]
    need([int(r['node']) for r in path] == list(range(len(path))) and len(path) == 1134, 'Native path inventory')
    need(all(r['observation_index'] == '3426' for r in path), 'Wrong native observation')
    result = next(r for r in read(base/'results.csv') if r['run_id'] == RUN)
    need(result['converged'] == identity['ray_converged'] == '0' and result['logged_matches_unobserved_variant'] == '1',
         'Original failure/parity changed')
    points = [tuple(Q(float(r[k])) for k in ('x', 'y', 'z')) for r in path[NODE-1:NODE+2]]
    grid = read(base/'inputs/initial_grid.csv')
    grid_pins = [digest for name,digest in summary['input_sha256'].items() if name.endswith('/initial_grid.csv')]
    need(len(grid_pins) == 1 and sha(base/'inputs/initial_grid.csv') == grid_pins[0], 'Grid differs from reviewed observer input')
    axes = [sorted(set(Q(float(r[k])) for r in grid)) for k in ('x', 'y', 'z')]
    profile = sorted(set((Q(float(r['z'])), Q(float(r['v']))) for r in grid))
    need(len(profile) == len(axes[2]) and len(grid) == len(axes[0])*len(axes[1])*len(axes[2]) and
         len({tuple(Q(float(r[k])) for k in ('x','y','z')) for r in grid}) == len(grid), 'Expected complete depth-only grid')
    need(all(v > 0 for z,v in profile), 'Nonpositive velocity')
    z = points[1][2]
    need(all(z != face for face,v in profile), 'Focus node is exactly on a depth plane')
    lower = max(face for face,v in profile if face < z)
    upper = min(face for face,v in profile if face > z)
    need(lower == 7 and upper == 11 and all(axes[k][0] < p[k] < axes[k][-1] for p in points for k in range(3)),
         'Unexpected saved local geometry')
    action, gradient = adjacent(arithmetic, square_root, profile, points)
    saved = [Q(float(path[NODE]['gradient_'+k])) for k in ('x', 'y', 'z')]
    records = []
    gaps = z-lower
    steps = [('within_current_depth_piece', gaps/(1 << power), power) for power in (1,2,4,8,12,16,20,24,28)]
    old_fd = [r for r in read(base/'path_gradient_checks.csv') if r['run_id'] == RUN and
              int(r['node']) == NODE and int(r['axis']) == 2 and r['scheme'] == 'central']
    need(len(old_fd) == 1 and old_fd[0]['observation_index'] == '3426', 'Missing identified original focus-node difference')
    old_h = Q(float(old_fd[0]['step_km']))
    need(old_h > gaps, 'Original difference no longer crosses the break')
    steps.append(('original_break_crossing_central_difference', old_h, None))
    for label, h, power in steps:
        for coordinate_mode in ('exact_rational_perturbation', 'binary64_rounded_perturbation'):
            trials = []
            for sign in (-1, 1):
                intended = z+sign*h
                actual = intended if coordinate_mode == 'exact_rational_perturbation' else Q(float(intended))
                moved = shifted(points, 2, actual-z)
                trial_action, _ = adjacent(arithmetic, square_root, profile, moved)
                delta = arithmetic.sub(trial_action, action)
                trials.append((actual, trial_action))
                records.append(dict({key:identity[key] for key in IDS}, observation_index=3426, run_id=RUN,
                    focus_node=NODE, original_local_flag='0', label=label, coordinate_mode=coordinate_mode,
                    halving_power=power, sign=sign, h_rational=str(h), intended_z_rational=str(intended),
                    actual_z_rational=str(actual), actual_delta_z_rational=str(actual-z),
                    crosses_depth_break=not (lower < actual < upper), coordinate_changed=actual != z,
                    adjacent_action=interval(trial_action), exact_action_change=interval(delta),
                    action_change_sign='strict_decrease' if delta[1] < 0 else 'strict_increase' if delta[0] > 0 else 'inconclusive'))
            span = trials[1][0]-trials[0][0]
            central = arithmetic.div(arithmetic.sub(trials[1][1],trials[0][1]), arithmetic.point(span)) if span else None
            for r in records[-2:]:
                r['actual_central_span_rational'] = str(span)
                r['actual_central_difference'] = interval(central) if central is not None else None
    history = [r for r in read(base/'history.csv') if r['run_id'] == RUN and r['phase'] == 'line_search_failed']
    need(len(history) == 1, 'Missing original terminal line-search failure')
    time_value = Q(float(result['time_s']))
    ulp = Q(2)**(math.frexp(float(time_value))[1]-53)
    slope = Q(float(history[0]['directional_slope']))
    return dict(native_context=identity, original_result=result, original_failed_search=history[0],
        focus_node=NODE, original_focus_node_fd=old_fd[0], adjacent_original_nodes=path[NODE-1:NODE+2],
        axis_permutation='(physical z, physical x, physical y)',
        exact_saved_points_xyz_rational=[[str(v) for v in p] for p in points],
        depth_profile_rational=[[str(v) for v in row] for row in profile],
        adjacent_action=interval(action), exact_node_gradient_xyz=[interval(v) for v in gradient],
        saved_node_gradient_xyz_rational=[str(v) for v in saved],
        exact_minus_saved_gradient_xyz=[interval(arithmetic.sub(v, arithmetic.point(w))) for v,w in zip(gradient,saved)],
        original_full_action_ulp_s_rational=str(ulp), original_slope_s_rational=str(slope),
        original_full_step_linear_decrease_in_ulps=float(-slope/ulp),
        original_full_step_armijo_decrease_in_ulps=float(-Q(float(1e-4))*slope/ulp),
        probes=records, limitations=[
            'Only the two adjacent saved segments change; their exact action difference is the whole fixed polygon action difference with every other node fixed.',
            'Rational and binary64-rounded diagnostic perturbations are distinguished; none is an exported original line-search trial.',
            'The last L-BFGS direction and trials were not saved, so this cannot replay or prove the cause of that failed line search.',
            'No new ray solve, optimizer direction, stopping rule, source derivative or inverse-acceptance decision is made.'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--native', action='store_true')
    parser.add_argument('--controls', type=Path)
    parser.add_argument('--review', type=Path)
    args = parser.parse_args()
    out = args.output.resolve(); out.relative_to(ROOT)
    need(not out.exists(), 'Use a fresh output directory')
    inputs = [Path(__file__).resolve(), ROOT/'diagnostics/check_native_interface_support.py',
              ROOT/'diagnostics/first_arrival_1d_precise_turn_reference.py']
    if args.native:
        need(args.controls and args.review, 'Native evaluation requires independently reviewed invented controls')
        control = args.controls.resolve(); control.relative_to(ROOT)
        review_path = args.review.resolve(); review_path.relative_to(ROOT)
        control_summary = json.loads((control/'summary.json').read_text())
        review = json.loads(review_path.read_text())
        need(control_summary['status'] == 'passed_controls' and review['status'] == 'passed' and
             review['controls_summary_sha256'] == sha(control/'summary.json'), 'Control review mismatch')
        for name,digest in control_summary['input_source_sha256'].items():
            need(sha(ROOT/name) == sha(control/'source'/name) == digest, 'Reviewed control source changed')
        inputs += [control/'summary.json', review_path]
        inputs += [OBSERVER/name for name in ('summary.json','review.json','paths.csv','paths.csv.identifiers.json',
                   'identified_ray.csv','results.csv','history.csv','path_gradient_checks.csv','inputs/initial_grid.csv')]
    pins = {str(p.relative_to(ROOT)):sha(p) for p in inputs}
    out.mkdir(parents=True); frozen = out/'source'
    for p in inputs:
        dest = frozen/p.relative_to(ROOT); dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(str(p),str(dest))
    start = time.monotonic()
    arithmetic = module('saved_action_arithmetic',frozen/'diagnostics/check_native_interface_support.py')
    square_root = module('saved_action_sqrt',frozen/'diagnostics/first_arrival_1d_precise_turn_reference.py').candidate_sqrt_enclosure
    result = native(arithmetic,square_root,frozen) if args.native else controls(arithmetic,square_root)
    result.update(status='completed_native_two_segment_diagnostic' if args.native else 'passed_controls',
                  input_source_sha256=pins,elapsed_seconds=time.monotonic()-start)
    for name,digest in pins.items():
        need(sha(ROOT/name) == sha(frozen/name) == digest, 'Input/source changed')
    result['artifact_sha256'] = {str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()}
    with (out/'summary.json').open('x') as stream:
        json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps(dict(status=result['status'],checks=len(result.get('checks',[])),probes=len(result.get('probes',[])))))


if __name__ == '__main__':
    main()
