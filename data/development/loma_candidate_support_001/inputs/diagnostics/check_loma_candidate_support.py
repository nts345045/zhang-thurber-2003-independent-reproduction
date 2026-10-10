#!/usr/bin/env python3
"""Enclose an existing support for a prescribed saved interface polygon."""
import argparse
import csv
from fractions import Fraction as Q
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import shutil
import sys
import time
import traceback

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
CASE = 'data/development/loma_interface_candidates_002'
NATIVE = 'data/development/loma_outer_accumulation_native_001'
MOMENT = 'data/development/interface_moment_set'
ARITHMETIC = 'diagnostics/check_native_interface_support.py'
SQRT = 'diagnostics/first_arrival_1d_precise_turn_reference.py'
EXPECTED = {
    CASE + '/summary.json': '7bdbabbbd09f4edae34a7f9cae168f892fef11b64479997b38e0d361d66472b4',
    CASE + '/review.json': 'a5e3d874c414a3c07ac5beb6435e0a269c246f99b8b4df49cf4f17146d1735e3',
    MOMENT + '/proof.md': '2947f4df3ef3a1d72741f1ec6d4ed5188a5426f0b4219a8646d8e2751da2f9db',
    MOMENT + '/001/summary.json': 'b26a38144856adc2367bc5b763fd2522819339f8cfba7b648f58517ff64a2662',
    MOMENT + '/001/root_review.json': '0bc18ed1cada7ef7c3f6ad19dd4d185f87721ee9ce3526c4a5279a0748679f95',
    ARITHMETIC: '0ed7c9e024366248cbd4f105a10b17dca3e876dfa24605c4ca984faf15622e67',
    SQRT: '55f3bd520aa472a3e4d4042808403eaa850c952301ea95d461331af9917ab5f2',
}


def need(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def interval(value):
    return dict(lower_rational=str(value[0]), upper_rational=str(value[1]),
                lower_display=float(value[0]), upper_display=float(value[1]))


def square(value):
    lo, hi = value
    need(lo <= hi, 'Reversed interval')
    return (Q(0) if lo <= 0 <= hi else min(lo*lo, hi*hi), max(lo*lo, hi*hi))


def margins(ar, c, a, b):
    mass_squared = square(ar.add(a, b))
    return [ar.sub(ar.mul(ar.point(2), ar.mul(c, moment)), mass_squared)
            for moment in (a, b)]


def strictly_feasible(ar, c, a, b):
    bounds = margins(ar, c, a, b)
    return c[0] > 0 and all(v[0] > 0 for v in bounds)


def norm_bound(ar, sqrt, values):
    total = ar.point(0)
    for value in values:
        total = ar.add(total, square(value))
    lo = sqrt(total[0], 128)[1][0]
    hi = sqrt(total[1], 128)[1][1]
    need(0 <= lo and lo*lo <= total[0] <= total[1] <= hi*hi, 'Norm enclosure failed')
    return (lo, hi), total


def permute(point):
    return point[2], point[0], point[1]


def polygon(ar, sqrt, profile, points):
    gradient = [[ar.point(0) for k in range(3)] for p in points]
    action = ar.point(0)
    edges = []
    kinks = []
    for n, (a, b) in enumerate(zip(points, points[1:])):
        need(a != b, 'Zero-length segment')
        item = ar.segment(profile, permute(a), permute(b), sqrt)
        action = ar.add(action, item['action'])
        for side, index in (('ga', n), ('gb', n+1)):
            g = item[side]
            for k, value in enumerate((g[1], g[2], g[0])):
                gradient[index][k] = ar.add(gradient[index][k], value)
        aligned = item['aligned']
        if aligned and Q(aligned['plus']) != Q(aligned['minus']):
            need(Q(aligned['plus']) > Q(aligned['minus']), 'Aligned jump is not convex')
            kinks.append(dict(edge=n, **aligned))
        edges.append(item)
    return action, gradient, edges, kinks


def controls(ar, sqrt):
    checks = []
    def check(name, ok):
        checks.append(dict(name=name, passed=bool(ok)))
        need(ok, name)
    p = ar.point
    check('symmetric_interior_moments', strictly_feasible(ar, p(2), p(Q(1, 2)), p(Q(1, 2))))
    check('asymmetric_interior_moments', strictly_feasible(ar, p(2), p(Q(3, 5)), p(Q(2, 5))))
    check('moment_reversal_swaps_margins', margins(ar, p(2), p(Q(3, 5)), p(Q(2, 5))) ==
          list(reversed(margins(ar, p(2), p(Q(2, 5)), p(Q(3, 5))))))
    check('zero_jump_not_strictly_certified', not strictly_feasible(ar, p(0), p(0), p(0)))
    check('negative_jump_rejected', not strictly_feasible(ar, p(-1), p(0), p(0)))
    check('saturated_density_boundary_unresolved', not strictly_feasible(ar, p(2), p(1), p(1)))
    check('zero_moment_boundary_unresolved', not strictly_feasible(ar, p(2), p(0), p(0)))
    check('one_negative_moment_rejected', not strictly_feasible(ar, p(2), p(Q(-1, 4)), p(Q(1, 2))))
    check('impossible_endpoint_concentration_rejected', not strictly_feasible(ar, p(2), p(0), p(1)))
    narrow = (Q(24, 100), Q(26, 100))
    check('full_interval_interior', strictly_feasible(ar, (Q(9, 10), Q(11, 10)), narrow, narrow))
    broad = (Q(1, 10), Q(4, 10))
    check('midpoint_feasibility_is_insufficient', strictly_feasible(ar, p(1), p(Q(1, 4)), p(Q(1, 4))) and
          not strictly_feasible(ar, p(1), broad, broad))
    # A bounded invented nonconstant density supplies exact endpoint moments.
    pieces = [(Q(0), Q(1, 2), Q(1, 2)), (Q(3, 4), Q(1), Q(1, 3))]
    b = sum(value*(hi*hi-lo*lo)/2 for lo, hi, value in pieces)
    a = sum(value*(hi-lo) for lo, hi, value in pieces) - b
    check('explicit_density_moments_strictly_feasible', strictly_feasible(ar, p(1), p(a), p(b)))
    check('interval_square_spanning_zero', square((Q(-2), Q(3))) == (0, 9))
    check('interval_square_negative', square((Q(-3), Q(-2))) == (4, 9))
    bound, squared = norm_bound(ar, sqrt, [p(3), p(4), p(0)])
    check('complete_vector_norm_3_4_0', bound[0] <= 5 <= bound[1] and squared == (25, 25))
    bound, squared = norm_bound(ar, sqrt, [(Q(-1), Q(1)), p(2)])
    check('norm_retains_uncertain_component', squared == (4, 5) and bound[0] <= 2 and bound[1]**2 >= 5)
    profile = [(Q(-1), Q(4)), (Q(0), Q(5)), (Q(1), Q(5))]
    points = [(Q(0), Q(0), Q(0)), (Q(2), Q(0), Q(0))]
    action, g, edges, kinks = polygon(ar, sqrt, profile, points)
    check('one_exact_depth_kink_edge', len(kinks) == 1 and kinks[0]['edge'] == 0 and
          Q(kinks[0]['minus']) == Q(-1, 25) and Q(kinks[0]['plus']) == 0)
    check('depth_permutation_and_normal_sign', all(g[n][2][0] <= Q(-1, 25) <= g[n][2][1] for n in (0, 1)))
    check('aligned_tangent_signs', g[0][0][0] <= Q(-1, 5) <= g[0][0][1] and
          g[1][0][0] <= Q(1, 5) <= g[1][0][1] and g[0][1] == (0, 0))
    check('aligned_action_closed_form', action[0] <= Q(2, 5) <= action[1])
    c = ar.mul(edges[0]['length'], p(Q(1, 25)))
    # Add an explicitly declared smooth contribution of +1/50 at each end.
    targets = [ar.neg(ar.add(g[n][2], p(Q(1, 50)))) for n in (0, 1)]
    check('exact_cancellation_sign_with_smooth_remainder', strictly_feasible(ar, c, *targets) and
          all(v[0] <= Q(1, 50) <= v[1] for v in targets))
    c0 = Q(2, 25)
    for index, (da, db) in enumerate(((Q(-2), Q(1)), (Q(1), Q(-2)), (Q(1), Q(1)), (Q(-1), Q(-1)))):
        integral = ((da+db)/2 if da >= 0 and db >= 0 else Q(0) if da <= 0 and db <= 0 else
                    da*da/(2*(da-db)) if da > 0 else db*db/(2*(db-da)))
        check('uniform_density_support_' + str(index), (da+db)*c0/4 <= c0*integral)
    return checks


def run(out):
    candidate = json.loads((ROOT / CASE / 'summary.json').read_text())
    pins = dict(EXPECTED)
    for name in ('summary.json', 'review.json', 'paths.csv', 'paths.csv.identifiers.json',
                 'identified_ray.csv', 'inputs/initial_grid.csv'):
        path = NATIVE + '/' + name
        pins[path] = candidate['input_sha256'][path]
    own = str(Path(__file__).resolve().relative_to(ROOT))
    pins[own] = sha(Path(__file__).resolve())
    for name, digest in pins.items():
        need(sha(ROOT / name) == digest, 'Input/source pin changed: ' + name)
        target = out / 'inputs' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(str(ROOT / name), str(target))
        need(sha(target) == digest, 'Input changed during freeze: ' + name)
    frozen = out / 'inputs'
    candidate = json.loads((frozen / CASE / 'summary.json').read_text())
    candidate_review = json.loads((frozen / CASE / 'review.json').read_text())
    need(candidate['status'] == 'completed_saved_action_probes' and candidate_review['status'] == 'passed' and
         candidate_review['summary_sha256'] == pins[CASE + '/summary.json'], 'Candidate review binding differs')
    moment = json.loads((frozen / MOMENT / '001/summary.json').read_text())
    proof_review = json.loads((frozen / MOMENT / '001/root_review.json').read_text())
    need(proof_review['status'] == 'passed' and proof_review['summary_sha256'] == pins[MOMENT + '/001/summary.json'] and
         moment['input_source_sha256'][MOMENT + '/proof.md'] == pins[MOMENT + '/proof.md'], 'Proof review binding differs')
    ar = load('candidate_support_arithmetic', frozen / ARITHMETIC)
    sqrt = load('candidate_support_sqrt', frozen / SQRT).candidate_sqrt_enclosure
    checks = controls(ar, sqrt)
    (out / 'controls.json').write_text(json.dumps(dict(status='passed', checks=checks), indent=2) + '\n')
    native = frozen / NATIVE
    prior = json.loads((native / 'summary.json').read_text())
    prior_review = json.loads((native / 'review.json').read_text())
    need(prior['status'] == 'completed_single_change_diagnostic' and prior_review['status'] == 'passed' and
         prior_review['summary_sha256'] == pins[NATIVE + '/summary.json'], 'Native B review binding differs')
    identities = read(native / 'identified_ray.csv')
    need(len(identities) == 1, 'Native row must be unique')
    identity = identities[0]
    need(identity == candidate['native_context'] == prior['native_context'] == candidate_review['native_context'],
         'Native identity mismatch')
    sidecar = json.loads((native / 'paths.csv.identifiers.json').read_text())
    need(sidecar['native_context'] == identity and sidecar['file_sha256'] == pins[NATIVE + '/paths.csv'] and
         sidecar['context_sha256'] == pins[NATIVE + '/identified_ray.csv'], 'Native path sidecar differs')
    for name in ('paths.csv', 'paths.csv.identifiers.json', 'identified_ray.csv'):
        need(prior['output_sha256'][name] == pins[NATIVE + '/' + name], 'B artifact binding differs')
    need(prior['prepared_file_sha256']['inputs/initial_grid.csv'] == pins[NATIVE + '/inputs/initial_grid.csv'], 'Grid binding differs')
    run_id = 'fmm_0.031250_1000'
    results = [r for r in prior['results'] if r['run_id'] == run_id]
    need(results == [candidate['original_B_result']] and results[0]['converged'] == '0' and
         results[0]['updates'] == '1000', 'Original B result changed')
    rows = [r for r in read(native / 'paths.csv') if r['run_id'] == run_id]
    need(len(rows) == 1134 and [int(r['node']) for r in rows] == list(range(1134)) and
         all(r['observation_index'] == identity['observation_index'] == '3426' for r in rows), 'Native path join differs')
    base = [tuple(Q(float(r[k])) for k in 'xyz') for r in rows]
    for prefix, point in (('native_source_', base[0]), ('native_receiver_', base[-1])):
        need(tuple(Q(float(identity[prefix+k])) for k in 'xyz') == point, 'Native endpoint differs')
    grid = read(native / 'inputs/initial_grid.csv')
    axes = [sorted({Q(float(r[k])) for r in grid}) for k in 'xyz']
    coordinates = [tuple(Q(float(r[k])) for k in 'xyz') for r in grid]
    need(len(coordinates) == len(set(coordinates)) and set(coordinates) == set(itertools.product(*axes)), 'Incomplete Cartesian grid')
    profile = sorted({(Q(float(r['z'])), Q(float(r['v']))) for r in grid})
    need(len(profile) == len(axes[2]) and all(v > 0 for z, v in profile) and
         [[str(q) for q in row] for row in profile] == candidate['depth_profile_rational'], 'Grid is not the reviewed positive depth profile')
    selected = [p for p in candidate['probes'] if p['nodes_changed'] == [484, 485]]
    need(len(selected) == 1 and selected[0]['replacement_z_rational'] == '7' and
         selected[0]['all_other_coordinates_unchanged'] is True, 'Candidate roster differs')
    selected = selected[0]
    points = [list(p) for p in base]
    for n in (484, 485):
        points[n][2] = Q(7)
    points = [tuple(p) for p in points]
    need(selected['actual_z_displacements_rational'] == {str(n): str(points[n][2]-base[n][2]) for n in (484, 485)},
         'Candidate exact displacement differs')
    need(points[0] == base[0] and points[-1] == base[-1] and
         all(axes[k][0] < p[k] < axes[k][-1] for p in points[1:-1] for k in range(3)) and
         all(axes[k][0] <= p[k] <= axes[k][-1] for p in points for k in range(3)), 'Candidate endpoint/domain guard failed')
    action, original_g, edges, kinks = polygon(ar, sqrt, profile, points)
    need(len(kinks) == 1 and kinks[0]['edge'] == 484 and Q(kinks[0]['x']) == 7 and
         kinks[0]['on_grid_face'] and kinks[0]['alpha'] == '0', 'Require exactly one aligned convex kink at edge484/z7')
    change = ar.point(0)
    changed = []
    for n, (a, b) in enumerate(zip(base, base[1:])):
        if (a, b) == (points[n], points[n+1]):
            continue
        old = ar.segment(profile, permute(a), permute(b), sqrt)['action']
        change = ar.add(change, ar.sub(edges[n]['action'], old))
        changed.append(n)
    need(changed == [483, 484, 485] and interval(change) == selected['action_change_s'], 'Reviewed candidate action changed')
    jump = Q(kinks[0]['plus']) - Q(kinks[0]['minus'])
    c = ar.mul(edges[484]['length'], ar.point(jump))
    a, b = ar.neg(original_g[484][2]), ar.neg(original_g[485][2])
    need(strictly_feasible(ar, c, a, b), 'Moment interval margins unresolved; no cancellation certificate')
    margin_a, margin_b = margins(ar, c, a, b)
    supported = [row[:] for row in original_g]
    for n in (484, 485):
        supported[n][2] = ar.point(0)  # Existence proved for the actual enclosed exact moments.
    norm, squared = norm_bound(ar, sqrt, [v for row in supported[1:-1] for v in row])
    alpha_norm, alpha_squared = norm_bound(ar, sqrt, [v for row in original_g[1:-1] for v in row])
    shutil.copyfile(str(native / 'identified_ray.csv'), str(out / 'identified_ray.csv'))
    table = []
    for n, point in enumerate(points):
        row = dict(node=n, original_run_id=run_id, observation_index=identity['observation_index'],
                   endpoint_fixed=int(n in (0, len(points)-1)), normal_cancelled_by_existence=int(n in (484, 485)))
        for k, axis in enumerate('xyz'):
            row[axis + '_rational'] = str(point[k])
            row[axis + '_display_km'] = repr(float(point[k]))
            for label, vector in (('alpha0', original_g), ('support', supported)):
                for bound_index, bound_name in enumerate(('lower', 'upper')):
                    row[label+'_'+axis+'_'+bound_name+'_rational'] = ('' if row['endpoint_fixed'] else
                                                                    str(vector[n][k][bound_index]))
        table.append(row)
    table_path = out / 'candidate_support.csv'
    with table_path.open('x', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(table[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(table)
    attachment = dict(file_sha256=sha(table_path), context_file='identified_ray.csv',
                      context_sha256=sha(out / 'identified_ray.csv'), native_context=identity,
                      geometry_basis='Prescribed modified B polygon; only nodes484/485 z replaced by exact7km',
                      value_basis='Existence of a continuous supporting vector for fixed polygon topology',
                      fixed_endpoint_components='Blank; source/receiver derivatives are not selected', input_sha256=pins)
    (out / 'candidate_support.csv.identifiers.json').write_text(json.dumps(attachment, indent=2) + '\n')
    for name, digest in pins.items():
        need(sha(ROOT / name) == sha(frozen / name) == digest, 'Input changed during calculation')
    result = dict(status='completed_prescribed_polygon_support_existence', input_sha256=pins,
                  native_context=identity, original_B_result=results[0], candidate_summary_sha256=pins[CASE+'/summary.json'],
                  candidate_review_sha256=pins[CASE+'/review.json'], controls_passed=len(checks),
                  selected_candidate_nodes=[484, 485], changed_edges=changed, original_nodes=len(base),
                  movable_nodes=len(points)-2, complete_internal_components=3*(len(points)-2),
                  exact_zero_components_by_existence=[[484, 'z'], [485, 'z']],
                  other_components_unchanged=True, fixed_endpoints_excluded=True, depth_profile_rational=[[str(q) for q in r] for r in profile],
                  aligned_convex_kinks=kinks, action_s=interval(action), action_change_s=interval(change),
                  edge_length_km=interval(edges[484]['length']), slowness_normal_jump_rational=str(jump),
                  c_s_per_km=interval(c), target_A_s_per_km=interval(a), target_B_s_per_km=interval(b),
                  feasibility_margin_A=interval(margin_a), feasibility_margin_B=interval(margin_b),
                  alpha0_internal_norm_s_per_km=interval(alpha_norm), alpha0_squared_norm=interval(alpha_squared),
                  support_internal_norm_s_per_km=interval(norm), support_squared_norm=interval(squared),
                  original_B_flag_preserved=results[0]['converged'], ray_solves=0, optimizer_steps=0,
                  command=[sys.executable, str(Path(__file__).resolve().relative_to(ROOT))] + sys.argv[1:],
                  python_version=sys.version, finished_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                  limitations=['The certificate concerns an explicitly prescribed modified polygon, not the original B polygon.',
                               'Both moment inequalities use rational outward intervals; strict margins certify the actual correlated exact values.',
                               'Zero is used only for the two normal components whose simultaneous cancellation is proved by the pinned moment-set theorem.',
                               'This is a continuous first-variation supporting-vector existence bound, not an ordinary gradient or a computed minimizing dual solution.',
                               'The constant-jump proof assumes this depth-only profile and fixed positive-length polygon topology; no arbitrary trilinear model or inserted-knot result follows.',
                               'No source/model derivative, production function, convergence flag, first arrival or inversion is changed or certified.'])
    result['artifact_sha256'] = {str(p.relative_to(out)): sha(p) for p in sorted(out.rglob('*')) if p.is_file()}
    (out / 'summary.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps(dict(status=result['status'], controls=len(checks), alpha0_norm=result['alpha0_internal_norm_s_per_km'],
                          support_norm=result['support_internal_norm_s_per_km'], margins=[interval(margin_a), interval(margin_b)]), indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    out = (ROOT / args.output).resolve()
    out.relative_to(ROOT)
    out.mkdir(parents=True, exist_ok=False)
    try:
        run(out)
    except Exception as error:
        (out / 'failure.json').write_text(json.dumps(dict(status='failed', error=str(error), traceback=traceback.format_exc()), indent=2) + '\n')
        raise


if __name__ == '__main__':
    main()
