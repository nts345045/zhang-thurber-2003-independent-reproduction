#!/usr/bin/env python3
"""Invented one-cell Hamiltonian candidates, not a production ray solver."""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import shutil
import sys
import time

sys.dont_write_bytecode = True
import numpy as np
import scipy
from scipy.integrate import solve_ivp
from scipy.optimize import least_squares

ROOT = Path(__file__).resolve().parents[1]
AXES = np.array([[-.25, .5], [-.5, .5], [-1., 0.]])
BITS = np.array([(i, j, k) for k in range(2) for j in range(2) for i in range(2)])
SETTINGS = [dict(name='base', rtol=2e-11, atol=1e-13),
            dict(name='tight', rtol=3e-13, atol=2e-15)]
SOURCE_LIMIT, TIME_LIMIT = 3e-6, 25e-6


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def save(p, value):
    p.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def plain(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {k: plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    return value


def field(x, nodes):
    """Original i-fastest basis; polynomial trial evaluation is never admissibility."""
    q = (x - AXES[:, 0]) / (AXES[:, 1] - AXES[:, 0])
    factors = np.where(BITS, q, 1 - q)
    basis = np.prod(factors, axis=1)
    derivative = np.empty((8, 3))
    for k in range(3):
        derivative[:, k] = ((2 * BITS[:, k] - 1) /
                            (AXES[k, 1] - AXES[k, 0]) *
                            np.prod(factors[:, [j for j in range(3) if j != k]], axis=1))
    return float(basis @ nodes), derivative.T @ nodes, basis


def flow(x, p, duration, nodes, settings, guide=False, inspect=False):
    state = np.r_[x, p, 0., np.zeros(8)]
    if guide:
        if x[2] != 0. or p[2] != 0.:
            raise ValueError('Guide requires exact bottom/tangent initial state')
    if duration == 0:
        return state, dict(points=[state[:6].tolist()], invariant_error=0.,
                           domain_violation=0., minimum_reaction=None,
                           time_minus_signed_duration=0.)

    def rhs(t, y):
        v, gradient, basis = field(y[:3], nodes)
        if not math.isfinite(v) or v <= 0:
            raise ValueError('Nonpositive trial velocity')
        norm = np.linalg.norm(y[3:6])
        dx = v * v * y[3:6]
        dp = -v * norm * norm * gradient
        if guide:
            dx[2] = dp[2] = 0.
        return np.r_[dx, dp, v * norm, -basis * norm]

    solution = solve_ivp(rhs, (0., duration), state, method='DOP853',
                         rtol=settings['rtol'], atol=settings['atol'],
                         max_step=abs(duration) / 8, dense_output=inspect)
    if not solution.success:
        raise ValueError(solution.message)
    final = solution.y[:, -1]
    if not inspect:
        return final, None
    samples = solution.sol(np.linspace(0., duration, 129)).T
    invariants, reactions = [], []
    for y in samples:
        v, gradient, basis = field(y[:3], nodes)
        invariants.append(abs(v * v * np.dot(y[3:6], y[3:6]) - 1))
        if guide:
            reactions.append(v * np.dot(y[3:6], y[3:6]) * gradient[2])
    violation = max(0., float(np.max(AXES[:, 0] - samples[:, :3])),
                    float(np.max(samples[:, :3] - AXES[:, 1])))
    return final, dict(points=samples[:, :6].tolist(),
                       invariant_error=max(invariants), domain_violation=violation,
                       minimum_reaction=min(reactions) if reactions else None,
                       time_minus_signed_duration=float(final[6] - duration))


def solve_branch(a, b, nodes, settings, topology, continuation=None):
    """Find one declared branch root; do not infer enumeration or a global minimum."""
    a, b = np.array(a, float), np.array(b, float)
    length = float(np.linalg.norm(b - a))
    horizontal = float(np.linalg.norm(b[:2] - a[:2]))
    if length == 0 or horizontal == 0:
        return dict(topology=topology, valid=False, reason='unsupported coincident/vertical fixture')
    direction = (b[:2] - a[:2]) / horizontal
    azimuth = math.atan2(direction[1], direction[0])
    va = field(a, nodes)[0]
    vb = field(b, nodes)[0]
    middle = np.r_[(a[:2] + b[:2]) / 2, 0.]
    vtop, grad, _ = field(middle, nodes)
    duration_scale = length / ((va + vb) / 2)
    if not np.all(np.isfinite(nodes)) or np.min(nodes) <= 0:
        raise ValueError('All original cell-node velocities must be positive and finite')
    # The in-box chord is admissible and v >= min(nodes). The full cell diagonal
    # gives a physical time upper bound with slack for this interior roster.
    duration_upper = float(np.linalg.norm(AXES[:, 1] - AXES[:, 0]) / np.min(nodes))
    # A local linearization is only an initial root guess, for every model.
    gseed = max(abs(float(grad[2])), 1e-8)
    ra = math.sqrt(max(0., -2 * vtop * a[2] / gseed))
    rb = math.sqrt(max(0., -2 * vtop * b[2] / gseed))
    ta_scale = max(min(ra / vtop, duration_scale), 1e-8 * duration_scale)
    tb_scale = max(min(rb / vtop, duration_scale), 1e-8 * duration_scale)
    reaction_vertices = [field(np.array([x, y, 0.]), nodes)[1][2]
                         for x in AXES[0] for y in AXES[1]]
    # A bilinear normal derivative is strictly negative everywhere in this case.
    # Mixed-sign faces proceed; their candidate reaction is checked on the arc.
    if topology != 'direct' and max(reaction_vertices) < 0:
        return dict(topology=topology, valid=False,
                    reason='negative guide reaction everywhere on the bottom face',
                    bottom_gradient_min=float(min(reaction_vertices)),
                    bottom_gradient_max=float(max(reaction_vertices)))
    if topology == 'direct':
        initial = [azimuth, math.atan2(b[2] - a[2], horizontal), 1.]
        lower, upper = ([-math.inf, -math.pi / 2, 0.],
                        [math.inf, math.pi / 2, duration_upper / duration_scale])

        def evaluate(q, inspect=False):
            theta, elevation, duration = q
            p = np.array([math.cos(elevation) * math.cos(theta),
                          math.cos(elevation) * math.sin(theta), math.sin(elevation)]) / va
            end, diagnostic = flow(a, p, duration * duration_scale, nodes, settings,
                                   inspect=inspect)
            return ((end[:3] - b) / length,
                    dict(time=float(end[6]), kernels=end[7:], source=-p,
                         receiver=end[3:6], pieces=[diagnostic],
                         parameters=q, endpoint_match=end[:3] - b))
    else:
        zero_a, zero_b = a[2] == 0., b[2] == 0.
        expected = ('both_zero_caps' if zero_a and zero_b else
                    'zero_first_cap' if zero_a else 'zero_last_cap' if zero_b else 'two_caps')
        if topology != expected:
            return dict(topology=topology, valid=False, reason='topology/endpoints mismatch')
        initial, lower, upper = [], [], []
        if not zero_a:
            contact = a[:2] + direction * min(ra, horizontal * .45)
            initial += list((contact - a[:2]) / length)
            lower += list((AXES[:2, 0] - a[:2]) / length)
            upper += list((AXES[:2, 1] - a[:2]) / length)
        initial += [azimuth]
        lower += [-math.inf]
        upper += [math.inf]
        if not zero_a:
            initial += [1.]
            lower += [0.]
            upper += [duration_upper / ta_scale]
        initial += [max(.02, 1 - (ra + rb) / max(horizontal, 1e-30))]
        lower += [0.]
        upper += [duration_upper / duration_scale]
        if not zero_b:
            initial += [1.]
            lower += [0.]
            upper += [duration_upper / tb_scale]

        def evaluate(q, inspect=False):
            n = 0
            if zero_a:
                contact = a.copy()
            else:
                contact = np.r_[a[:2] + length * np.asarray(q[:2]), 0.]
                n = 2
            theta = q[n]
            n += 1
            v = field(contact, nodes)[0]
            p = np.array([math.cos(theta), math.sin(theta), 0.]) / v
            ta = 0. if zero_a else q[n] * ta_scale
            n += 0 if zero_a else 1
            tg = q[n] * duration_scale
            n += 1
            tb = 0. if zero_b else q[n] * tb_scale
            first, d1 = flow(contact, p, -ta, nodes, settings, inspect=inspect)
            guide, d2 = flow(contact, p, tg, nodes, settings, guide=True, inspect=inspect)
            final, d3 = flow(guide[:3], guide[3:6], tb, nodes, settings, inspect=inspect)
            residual = []
            if not zero_a:
                residual.extend((first[:2] - a[:2]) / length)
                residual.append((first[2] - a[2]) / max(-a[2], 1e-30))
            residual.extend((final[:2] - b[:2]) / length)
            if not zero_b:
                residual.append((final[2] - b[2]) / max(-b[2], 1e-30))
            return (np.asarray(residual),
                    dict(time=float(-first[6] + guide[6] + final[6]),
                         kernels=-first[7:] + guide[7:] + final[7:],
                         source=-first[3:6], receiver=final[3:6],
                         pieces=[d1, d2, d3], parameters=q,
                         durations=[ta, tg, tb],
                         endpoint_match=np.r_[first[:3] - a, final[:3] - b]))
    if continuation and len(continuation) == len(initial):
        initial = np.minimum(np.maximum(continuation, lower), upper).tolist()
    failures = []

    def residual(q):
        try:
            r, data = evaluate(q)
            if not np.all(np.isfinite(r)):
                raise ValueError('Nonfinite residual')
            return r
        except (ValueError, FloatingPointError) as exc:
            failures.append(str(exc))
            return np.full(len(initial), 1e6)

    try:
        root = least_squares(residual, initial, bounds=(lower, upper),
                             jac='3-point', xtol=2e-13, ftol=2e-13, gtol=2e-13,
                             max_nfev=60)
        residual_value, result = evaluate(root.x, inspect=True)
        pieces = result['pieces']
        violation = max(p['domain_violation'] for p in pieces)
        invariant = max(p['invariant_error'] for p in pieces)
        match = float(np.max(np.abs(result['endpoint_match'])))
        reactions = [p['minimum_reaction'] for p in pieces if p['minimum_reaction'] is not None]
        valid = (root.success and match < 5e-11 and violation < 5e-11 and
                 invariant < 1e-9 and (not reactions or min(reactions) >= 0) and
                 (topology == 'direct' or result['durations'][1] > 0))
        result.update(topology=topology, valid=bool(valid), root_success=bool(root.success),
                      root_message=root.message, root_evaluations=int(root.nfev),
                      initial_parameters=initial,
                      parameter_lower_bounds=[None if math.isinf(x) else x for x in lower],
                      parameter_upper_bounds=[None if math.isinf(x) else x for x in upper],
                      duration_upper_s=duration_upper,
                      duration_bound='cell diagonal / minimum positive original nodal velocity',
                      maximum_scaled_residual=float(np.max(np.abs(residual_value))),
                      maximum_endpoint_mismatch_km=match,
                      maximum_domain_violation_km=violation,
                      maximum_invariant_error=invariant,
                      trial_failures=failures,
                      numerical_admissibility_only=True,
                      global_minimum_or_root_completeness_certified=False)
        return plain(result)
    except Exception as exc:
        return dict(topology=topology, valid=False, reason=str(exc), trial_failures=failures)


def solve(a, b, nodes, settings, guide_only=False, continuation=None):
    za, zb = a[2] == 0., b[2] == 0.
    topology = ('both_zero_caps' if za and zb else 'zero_first_cap' if za else
                'zero_last_cap' if zb else 'two_caps')
    starts = {r['topology']: r.get('parameters') for r in
              (continuation or {}).get('candidates', [])}
    results = [solve_branch(a, b, nodes, settings, topology, starts.get(topology))]
    if not guide_only:
        results.append(solve_branch(a, b, nodes, settings, 'direct', starts.get('direct')))
    valid = [r for r in results if r['valid']]
    selected = min(valid, key=lambda r: r['time']) if valid else None
    return dict(candidates=results, selected=selected,
                selection='minimum action among successfully solved admissible roots only')


def affine_nodes(g):
    return np.array([6. + g * AXES[2, bit[2]] for bit in BITS])


def oracle(a, b, g, module):
    direction = np.array(b[:2]) - np.array(a[:2])
    distance = float(np.linalg.norm(direction))
    direction /= distance
    flip = -1. if g < 0 else 1.
    bottom = 1. if g < 0 else 0.
    value = module.connector((0., a[2] * flip), (distance, b[2] * flip),
                             bottom, 6. + (-g if g < 0 else 0.), abs(g))
    return dict(time=value['time_s'], branch=value['branch'],
                source=[*(direction * value['source'][0]), value['source'][1] * flip],
                receiver=[*(direction * value['receiver'][0]), value['receiver'][1] * flip],
                excess=value['excess_s'])


def compact(result):
    copy = json.loads(json.dumps(result))
    for candidate in copy['candidates']:
        for piece in candidate.get('pieces', []):
            piece.pop('points', None)
    if copy['selected']:
        for piece in copy['selected']['pieces']:
            piece.pop('points', None)
    return copy


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=False)
    (out / 'source').mkdir()
    sources = [Path(__file__).resolve(), ROOT / 'diagnostics/endpoint_connector.py',
               ROOT / 'data/development/loma_endpoint_connector_next_step_001/shooting_control.md']
    inputs = {str(p.relative_to(ROOT)): sha(p) for p in sources}
    for p in sources:
        shutil.copyfile(p, out / 'source' / p.name)
    spec = importlib.util.spec_from_file_location('independent_affine_oracle', out / 'source/endpoint_connector.py')
    affine = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(affine)
    cases = []
    def add(name, ea, eb, g=1., length=.25):
        cases.append(dict(name=name, a=[0., 0., -ea], b=[.8 * length, .6 * length, -eb],
                          nodes=affine_nodes(g).tolist(), gradient=g))
    add('both_bottom', 0., 0.)
    for power in [8, 12, 16, 20, 24, 28]:
        epsilon = 2. ** -power
        add('scalar_regime_' + str(power), epsilon, 0.)
        add('reciprocal_regime_' + str(power), 0., epsilon)
    add('two_caps', 2. ** -12, 2. ** -12)
    epsilon = 2. ** -8
    critical = 2 * math.sqrt(epsilon * (12 - epsilon))
    for factor, name in [(1 - 2. ** -10, 'below'), (1., 'at'), (1 + 2. ** -10, 'above')]:
        add('transition_' + name, epsilon, epsilon, length=critical * factor)
    add('homogeneous_oblique', 0., .1, g=0.)
    add('weak_gradient', 0., .1, g=2. ** -20)
    add('negative_gradient', 0., .1, g=-1.)
    settings = dict(ode=SETTINGS, source_vector_limit_s_per_km=SOURCE_LIMIT,
                    time_limit_s=TIME_LIMIT, model_steps=[2. ** -16, 2. ** -20],
                    tangential_step_km=2. ** -17,
                    normal_boundary_steps_km=[2. ** -20, 2. ** -24, 2. ** -28],
                    mixed_log_velocity_coefficients=[.2, -.7, .5, .1, -.4, .8, -.6, .3],
                    mixed_amplitude=2. ** -8,
                    root_and_domain_checks_are_numerical_not_certificates=True)
    save(out / 'invented_inputs.json', dict(cases=cases, axes=AXES.tolist(), settings=settings,
         resource_ids=None, geometry='invented only'))
    execution = dict(status='running', command=sys.argv, started_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                     input_sha256=inputs, environment=dict(python=sys.version, numpy=np.__version__, scipy=scipy.__version__))
    save(out / 'execution.json', execution)
    baseline_results, perturbations, comparisons = [], [], []
    try:
        for setting in SETTINGS:
            for case in cases:
                result = solve(case['a'], case['b'], np.array(case['nodes']), setting)
                exact = oracle(case['a'], case['b'], case['gradient'], affine)
                selected = result['selected']
                comparison = dict(setting=setting['name'], case=case['name'], oracle=exact,
                                  selected_valid=selected is not None)
                if selected:
                    comparison.update(time_error_s=selected['time'] - exact['time'],
                        source_error_s_per_km=float(np.linalg.norm(np.array(selected['source']) - exact['source'])),
                        receiver_error_s_per_km=float(np.linalg.norm(np.array(selected['receiver']) - exact['receiver'])))
                    comparison['accuracy_pass'] = (abs(comparison['time_error_s']) <= TIME_LIMIT and
                        max(comparison['source_error_s_per_km'], comparison['receiver_error_s_per_km']) <= SOURCE_LIMIT)
                else:
                    comparison['accuracy_pass'] = False
                baseline_results.append(dict(setting=setting['name'], case=case['name'], result=result))
                comparisons.append(comparison)
                save(out / 'baseline_results.json', baseline_results)
                save(out / 'comparisons.json', comparisons)
                print(setting['name'], case['name'], comparison['accuracy_pass'], flush=True)
            # Same actual trilinear action; no depth-only or affine dispatch.
            for mixed, both_bottom in [(False, False), (True, False), (True, True)]:
                a, b = [0., 0., 0. if both_bottom else -2. ** -12], [.2, .15, 0.]
                nodes = affine_nodes(1.)
                if mixed:
                    nodes *= np.exp(-settings['mixed_amplitude'] * np.array(settings['mixed_log_velocity_coefficients']))
                base = solve(a, b, nodes, setting)
                selected = base['selected']
                if not selected:
                    perturbations.append(dict(setting=setting['name'], mixed=mixed, both_bottom=both_bottom,
                                              status='base_unresolved', result=compact(base)))
                    continue
                for node in range(8):
                    for h in (settings['model_steps'][-1:] if both_bottom else settings['model_steps']):
                        pair = []
                        for sign in [-1, 1]:
                            changed = nodes.copy()
                            changed[node] *= math.exp(-sign * h)
                            pair.append(solve(a, b, changed, setting, continuation=base))
                        valid = all(r['selected'] is not None for r in pair)
                        row = dict(kind='model', setting=setting['name'], mixed=mixed, both_bottom=both_bottom, node=node, h=h,
                                   same_value_candidates=valid, results=[compact(r) for r in pair])
                        if valid:
                            fd = (pair[1]['selected']['time'] - pair[0]['selected']['time']) / (2 * h)
                            kernel = -nodes[node] * selected['kernels'][node]
                            row.update(finite_difference_s=fd, kernel_s=kernel, difference_s=fd - kernel,
                                       selected_topologies=[r['selected']['topology'] for r in pair])
                        perturbations.append(row)
                # All endpoint components: centered inside; one-sided at the physical bottom.
                for side in [0, 1]:
                    for axis in range(3):
                        origin = [a.copy(), b.copy()]
                        boundary = axis == 2 and origin[side][2] == 0.
                        steps = settings['normal_boundary_steps_km'] if boundary else [2. ** -17, 2. ** -19]
                        for h in steps:
                            signs = [-1] if boundary else [-1, 1]
                            pair = []
                            for sign in signs:
                                moved = [origin[0].copy(), origin[1].copy()]
                                moved[side][axis] += sign * h
                                pair.append(solve(moved[0], moved[1], nodes, setting, continuation=base))
                            valid = all(r['selected'] is not None for r in pair)
                            row = dict(kind='endpoint', setting=setting['name'], mixed=mixed, both_bottom=both_bottom,
                                       side=side, axis=axis, h=h, inward_one_sided=boundary,
                                       same_value_candidates=valid, results=[compact(r) for r in pair])
                            if valid:
                                derivative = selected['source' if side == 0 else 'receiver'][axis]
                                fd = ((selected['time'] - pair[0]['selected']['time']) / h if boundary else
                                      (pair[1]['selected']['time'] - pair[0]['selected']['time']) / (2 * h))
                                row.update(finite_difference_s_per_km=fd, momentum_component=derivative,
                                           difference_s_per_km=fd - derivative,
                                           selected_topologies=[r['selected']['topology'] for r in pair])
                            perturbations.append(row)
                save(out / 'perturbations.json', perturbations)
                print(setting['name'], 'mixed' if mixed else 'affine', 'both_bottom', both_bottom,
                      'perturbations complete', flush=True)
        execution.update(status='completed', return_code=0,
                         finished_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
        save(out / 'execution.json', execution)
        for path, digest in inputs.items():
            if sha(ROOT / path) != digest:
                raise ValueError('Source changed: ' + path)
        summary = dict(status='completed_stationary_candidate_controls', input_sha256=inputs,
                       baseline_comparisons=len(comparisons), baseline_accuracy_passes=sum(c['accuracy_pass'] for c in comparisons),
                       perturbation_comparisons=len(perturbations),
                       unresolved_perturbations=sum(not r.get('same_value_candidates', False) for r in perturbations),
                       limitations=[
                         'No native geometry, production changes, inverse solve or global branch enumeration.',
                         'All models use the same trilinear Hamiltonian/action and original basis kernels.',
                         'Polynomial evaluations on inadmissible trial arcs are root-finding continuation only; roots failing the finite-box check are not selected.',
                         'Finite-box, reaction and invariant checks sample dense numerical trajectories; they are not outward certificates.',
                         'One successful stationary root per topology is not a proved minimum or complete search.',
                         'Boundary finite differences contain the physical square-root truncation term; raw disagreement is retained.',
                         'Zero-cap branches are explicit, not clipped durations; singular root and branch-switch outcomes remain visible.'],
                       output_sha256={str(p.relative_to(out)): sha(p) for p in sorted(out.rglob('*')) if p.is_file()})
        save(out / 'summary.json', summary)
        print(json.dumps({k: v for k, v in summary.items() if k.endswith('comparisons') or k.endswith('passes') or k.startswith('unresolved')}), flush=True)
    except Exception as exc:
        execution.update(status='failed', return_code=1, error=str(exc))
        save(out / 'execution.json', execution)
        raise


if __name__ == '__main__':
    main()
