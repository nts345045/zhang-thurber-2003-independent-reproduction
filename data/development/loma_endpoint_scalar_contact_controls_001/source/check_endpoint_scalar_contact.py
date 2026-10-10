#!/usr/bin/env python3
"""Invented restricted bottom-contact values with one reciprocal-trilinear action."""
import argparse
from decimal import Decimal as D, localcontext
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
AXES = ((D('-.25'), D('.5')), (D('-.5'), D('.5')), (D('-1'), D('0')))
ELL, V = D('.25'), D('6')
EPSILON_POWERS = (8, 12, 16, 20, 24, 28)
MODEL_POWERS = (12, 16, 20, 24)
BITS = tuple((i, j, k) for k in range(2) for j in range(2) for i in range(2))


def need(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False, default=str) + '\n')


def multiply(a, b):
    out = [D(0)] * (len(a) + len(b) - 1)
    for i, x in enumerate(a):
        for j, y in enumerate(b):
            out[i + j] += x * y
    return out


def value(poly, t):
    result = D(0)
    for x in reversed(poly):
        result = result * t + x
    return result


def basis_polynomials(a, b):
    """Original Grid::id order, with all eight shape functions retained."""
    result = []
    for bits in BITS:
        p = [D(1)]
        for axis, bit in enumerate(bits):
            lo, hi = AXES[axis]
            q = [(a[axis] - lo) / (hi - lo), (b[axis] - a[axis]) / (hi - lo)]
            if not bit:
                q = [1 - q[0], -q[1]]
            p = multiply(p, q)
        result.append(p)
    return result


def field_polynomials(a, b, velocities):
    basis = basis_polynomials(a, b)
    speed = [sum(velocities[n] * basis[n][k] for n in range(8)) for k in range(4)]
    gradients = []
    for axis in range(3):
        p = [D(0)] * 3
        for n, bits in enumerate(BITS):
            term = [(D(1) if bits[axis] else D(-1)) / (AXES[axis][1] - AXES[axis][0])]
            for other in range(3):
                if other == axis:
                    continue
                lo, hi = AXES[other]
                q = [(a[other] - lo) / (hi - lo), (b[other] - a[other]) / (hi - lo)]
                if not bits[other]:
                    q = [1 - q[0], -q[1]]
                term = multiply(term, q)
            for k in range(3):
                p[k] += velocities[n] * term[k]
        gradients.append(p)
    return speed, gradients, basis


def gauss_rule(n, precision):
    """Decimal Legendre roots; precision agreement is not an interval proof."""
    rule = []
    tolerance = D(10) ** (-(precision - 12))
    for k in range(1, n // 2 + 1):
        x = D(str(math.cos(math.pi * (k - .25) / (n + .5))))
        for iteration in range(40):
            p0, p1 = D(1), x
            for j in range(2, n + 1):
                p0, p1 = p1, ((2 * j - 1) * x * p1 - (j - 1) * p0) / j
            derivative = n * (x * p1 - p0) / (x * x - 1)
            step = p1 / derivative
            x -= step
            if abs(step) < tolerance:
                break
        else:
            raise ValueError('Legendre root did not converge')
        # Recompute derivative at the retained root.
        p0, p1 = D(1), x
        for j in range(2, n + 1):
            p0, p1 = p1, ((2 * j - 1) * x * p1 - (j - 1) * p0) / j
        derivative = n * (x * p1 - p0) / (x * x - 1)
        weight = 1 / ((1 - x * x) * derivative * derivative)
        rule.extend((((1 - x) / 2, weight), ((1 + x) / 2, weight)))
    return sorted(rule)


def segment(a, b, velocities, rule, full=False):
    """One numerical action for every nodal model; no affine dispatch/cutoff."""
    delta = tuple(y - x for x, y in zip(a, b))
    length = sum(x * x for x in delta).sqrt()
    if length == 0:
        return dict(time=D(0), ga=None, gb=None, kernel=[D(0)] * 8, length=D(0))
    speed, gradients, basis = field_polynomials(a, b, velocities)
    total, ga, gb, kernel = D(0), [D(0)] * 3, [D(0)] * 3, [D(0)] * 8
    axes = range(3) if full else (0,)
    for t, w in rule:
        v = value(speed, t)
        need(v > 0, 'Nonpositive trilinear speed')
        u = 1 / v
        total += w * length * u
        for axis in axes:
            du = -value(gradients[axis], t) * u * u
            ga[axis] += w * (-delta[axis] * u / length + length * (1 - t) * du)
            gb[axis] += w * (delta[axis] * u / length + length * t * du)
        if full:
            for n in range(8):
                kernel[n] -= w * length * value(basis[n], t) * u * u
    return dict(time=total, ga=ga, gb=gb, kernel=kernel, length=length)


def family(epsilon, contact, velocities, rule, full=False):
    need(0 <= contact <= ELL and 0 <= epsilon <= 1 and min(velocities) > 0, 'Outside declared family')
    a, c, b = (D(0), D(0), -epsilon), (contact, D(0), D(0)), (ELL, D(0), D(0))
    first, last = segment(a, c, velocities, rule, full), segment(c, b, velocities, rule, full)
    if epsilon == 0:
        # Along this scalar family all contacts split the same horizontal curve.
        derivative = D(0)
    else:
        right = last['ga'][0] if last['ga'] is not None else -1 / value(field_polynomials(b, b, velocities)[0], D(0))
        derivative = first['gb'][0] + right
    return dict(time=first['time'] + last['time'], derivative=derivative,
                source_partial=first['ga'], receiver_partial=last['gb'],
                kernel=[x + y for x, y in zip(first['kernel'], last['kernel'])],
                first_length=first['length'], remainder_length=last['length'])


def minimize(epsilon, velocities, rule):
    """Retain endpoints and sampled derivative brackets; no global claim."""
    if epsilon == 0:
        result = family(epsilon, D(0), velocities, rule)
        return dict(contact=D(0), time=result['time'], derivative=None, candidates=2,
                    bracket=None, classification='all_contacts_same_curve_exact_family_value', minimum_certified=True)
    mesh = [ELL * k / 16 for k in range(17)]
    evaluated = [family(epsilon, r, velocities, rule) for r in mesh]
    candidates = [(evaluated[0]['time'], mesh[0], None), (evaluated[-1]['time'], mesh[-1], None)]
    for i in range(16):
        left, right = mesh[i], mesh[i + 1]
        dl, dr = evaluated[i]['derivative'], evaluated[i + 1]['derivative']
        if dl == 0:
            candidates.append((evaluated[i]['time'], left, (left, left)))
        if dl * dr >= 0:
            continue
        while right - left > D('1e-28'):
            mid = (left + right) / 2
            dm = family(epsilon, mid, velocities, rule)['derivative']
            if dm == 0:
                left = right = mid
                break
            if dl * dm < 0:
                right = mid
            else:
                left, dl = mid, dm
        r = (left + right) / 2
        candidates.append((family(epsilon, r, velocities, rule)['time'], r, (left, right)))
    time_value, r, bracket = min(candidates, key=lambda x: x[0])
    return dict(contact=r, time=time_value, derivative=family(epsilon, r, velocities, rule)['derivative'],
                candidates=len(candidates), bracket=bracket, classification='lowest_sampled_stationary_or_endpoint_candidate',
                minimum_certified=False)


def affine_oracle(epsilon):
    if epsilon == 0:
        return dict(contact=None, excess=D(0), curved_excess=D(0), value=ELL / V,
                    inward_value_derivative=D(0), minimum_certified=True, uniqueness=False)
    alpha = (V / (V - epsilon)).ln() / epsilon
    beta = V * alpha
    root = ((beta - 1) * (beta + 1)).sqrt()
    r = epsilon / root
    need(0 < r < ELL, 'Declared baseline contact lost its guide')
    excess = epsilon * root / V
    alpha_prime = 1 / (epsilon * (V - epsilon)) - (V / (V - epsilon)).ln() / (epsilon * epsilon)
    derivative = alpha_prime * (r * r + epsilon * epsilon).sqrt() + alpha * epsilon / (r * r + epsilon * epsilon).sqrt()
    q = ((epsilon / V) * (2 - epsilon / V)).sqrt()
    # Positive convergent series for atanh(q)-q; no near-equal total subtraction.
    term, curved, n = q * q * q, D(0), 3
    while True:
        updated = curved + term / n
        if updated == curved:
            break
        curved = updated; term *= q * q; n += 2
    need((epsilon * (2 * V - epsilon)).sqrt() < ELL, 'Continuous guide oracle is inapplicable')
    return dict(contact=r, excess=excess, curved_excess=curved, value=ELL / V + excess,
                inward_value_derivative=derivative, minimum_certified=True, uniqueness=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    out = (ROOT / args.output).resolve(); out.relative_to(ROOT)
    need(out != ROOT and not out.exists(), 'Fresh repository-local output required')
    out.mkdir(parents=True); (out / 'source').mkdir()
    sources = [Path(__file__).resolve(), ROOT / 'src/core.hpp',
               ROOT / 'data/development/loma_endpoint_connector_next_step_001/proposal.md',
               ROOT / 'data/development/loma_endpoint_connector_next_step_001/provenance.json']
    pins = {str(p.relative_to(ROOT)): sha(p) for p in sources}
    for p in sources:
        shutil.copyfile(str(p), str(out / 'source' / p.name))
    plan = dict(geometry='invented; no provider identities', axes=AXES, node_order=BITS,
        baseline_node_velocities=[5 + k for i, j, k in BITS], bottom=D(0), ell=ELL,
        epsilon_powers=EPSILON_POWERS, boundary_epsilon=0, model_powers=MODEL_POWERS,
        model_parameter='node velocity multiplied by exp(-h); each of eight nodes separately, both signs',
        precisions=[80, 120], gauss_points=32, scalar_scan_intervals=16, scalar_bracket_width_km='1e-28',
        permitted_family='a=(0,0,-epsilon), c=(r,0,0), b=(1/4,0,0), r in [0,1/4]',
        limits=dict(fixed_curve_model_column_s='1e-10', numerical_candidate_model_column_s='1e-10',
                    endpoint_component_s_per_km='1e-8'),
        certification='Baseline analytic convexity and epsilon=0 path identity only; general perturbed minima unresolved')
    save(out / 'invented_inputs.json', plan)
    execution = dict(status='running', started_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                     command=[str(Path(__file__).resolve().relative_to(ROOT))] + sys.argv[1:], input_sha256=pins)
    save(out / 'execution.json', execution)
    checks, runs = [], []
    def check(name, passed):
        checks.append(dict(name=name, passed=bool(passed)))
        need(passed, name)
    try:
        for precision in (80, 120):
            with localcontext() as ctx:
                ctx.prec = precision
                rule = gauss_rule(32, precision)
                check('positive_gauss_weights_' + str(precision), all(0 < t < 1 and w > 0 for t, w in rule))
                check('gauss_polynomial_moments_' + str(precision),
                      max(abs(sum(w * t ** degree for t, w in rule) - 1 / D(degree + 1)) for degree in range(64)) < D(10) ** (-(precision - 14)))
                velocities = [D(5 + k) for i, j, k in BITS]
                for n, bits in enumerate(BITS):
                    point = tuple(AXES[a][bits[a]] for a in range(3))
                    shape = basis_polynomials(point, point)
                    check('original_node_basis_' + str((precision, n)),
                          [p[0] for p in shape] == [D(int(j == n)) for j in range(8)])
                results = dict(precision=precision, scalar=[], model=[], perturbed_models=[])
                for power in (None,) + EPSILON_POWERS:
                    epsilon = D(0) if power is None else D(2) ** (-power)
                    optimum = minimize(epsilon, velocities, rule)
                    r = optimum['contact']; fixed = family(epsilon, r, velocities, rule, True)
                    oracle = affine_oracle(epsilon)
                    value_error = optimum['time'] - oracle['value']
                    check('baseline_action_' + str((precision, power)), abs(value_error) < D('1e-25'))
                    if power is not None:
                        check('baseline_contact_' + str((precision, power)), abs(r - oracle['contact']) < D('1e-26'))
                        check('source_partial_matches_regular_value_derivative_' + str((precision, power)),
                              abs(-fixed['source_partial'][2] - oracle['inward_value_derivative']) < D('1e-25'))
                        check('receiver_tangential_partial_' + str((precision, power)), abs(fixed['receiver_partial'][0] - 1 / V) < D('1e-60'))
                    else:
                        tied = [family(epsilon, ELL * j / 4, velocities, rule, True) for j in range(5)]
                        check('boundary_contact_value_tie_' + str(precision), max(abs(x['time'] - ELL / V) for x in tied) < D('1e-60'))
                    row = dict(epsilon_power=power, epsilon_km=epsilon, numerical_candidate=optimum,
                        analytic_family_oracle=oracle, quadrature_minus_oracle_s=value_error,
                        fixed_contact_source_partial_xyz=fixed['source_partial'],
                        fixed_contact_receiver_partial_xyz=fixed['receiver_partial'],
                        old_one_segment_source_inward_partial=(None if power is not None else ELL / (2 * V * V)),
                        reoptimized_value_secant_s_per_km=(None if power is None else oracle['excess'] / epsilon),
                        polygon_to_curved_excess_ratio=(None if power is None else oracle['excess'] / oracle['curved_excess']),
                        limiting_ratio=3 / (2 * D(2).sqrt()),
                        coefficient_error_is_discretization_not_zero_limit_failure=True)
                    results['scalar'].append(row)
                    # Kernels refer to original nodal velocities, not affine V,g parameters.
                    columns = [-velocities[j] * fixed['kernel'][j] for j in range(8)]
                    check('negative_log_columns_sum_to_time_' + str((precision, power)), abs(sum(columns) - fixed['time']) < D('1e-60'))
                    for node in range(8):
                        for hp in MODEL_POWERS:
                            h = D(2) ** (-hp); values, frozen_values, candidates = {}, {}, {}
                            for sign in (-1, 1):
                                changed = list(velocities); changed[node] *= (-D(sign) * h).exp()
                                candidates[sign] = minimize(epsilon, changed, rule)
                                values[sign] = candidates[sign]['time']
                                frozen_values[sign] = family(epsilon, r, changed, rule)['time']
                                results['perturbed_models'].append(dict(epsilon_power=power, node=node,
                                    parameter_power=hp, sign=sign, velocities=changed, scalar_candidate=candidates[sign]))
                            fd = (values[1] - values[-1]) / (2 * h)
                            frozen_fd = (frozen_values[1] - frozen_values[-1]) / (2 * h)
                            results['model'].append(dict(epsilon_power=power, node=node, parameter_power=hp,
                                h=h, original_nodal_kernel_s2_per_km=fixed['kernel'][node],
                                negative_log_column_s=columns[node], fixed_curve_central_difference_s=frozen_fd,
                                fixed_curve_error_s=frozen_fd - columns[node],
                                reoptimized_candidate_central_difference_s=fd,
                                candidate_error_s=fd - columns[node],
                                fixed_curve_within_declared_budget=abs(frozen_fd - columns[node]) <= D('1e-10'),
                                candidate_within_declared_budget=abs(fd - columns[node]) <= D('1e-10'),
                                restricted_family_envelope_justified=(power is None),
                                numerical_derivative_error_certified=False,
                                perturbed_global_minima_certified=all(x['minimum_certified'] for x in candidates.values())))
                    save(out / ('progress_' + str(precision) + '.json'), results)
                    print('precision', precision, 'epsilon', power, 'complete', flush=True)
                runs.append(results)
                save(out / ('results_' + str(precision) + '.json'), results)
        # Arithmetic precision agreement is diagnostic evidence, not a certificate.
        with localcontext() as ctx:
            ctx.prec = 120
            differences = []
            for a, b in zip(runs[0]['model'], runs[1]['model']):
                need((a['epsilon_power'], a['node'], a['parameter_power']) == (b['epsilon_power'], b['node'], b['parameter_power']), 'Precision run roster differs')
                differences.append(max(abs(a[k] - b[k]) for k in ('negative_log_column_s', 'fixed_curve_central_difference_s', 'reoptimized_candidate_central_difference_s')))
            check('80_120_digit_model_arithmetic_agreement', max(differences) < D('1e-55'))
        for p in sources:
            need(sha(p) == pins[str(p.relative_to(ROOT))], 'Consumed source changed')
        save(out / 'checks.json', checks)
        execution.update(status='completed', return_code=0, finished_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
        save(out / 'execution.json', execution)
        final = runs[-1]
        summary = dict(status='completed_restricted_family_with_unresolved_perturbed_minima', input_sha256=pins,
            controls_passed=len(checks), scalar_cases_per_precision=len(final['scalar']),
            model_column_comparisons_per_precision=len(final['model']), perturbed_models_per_precision=len(final['perturbed_models']),
            maximum_80_120_digit_model_difference_s=max(differences),
            fixed_curve_budget_failures=sum(not r['fixed_curve_within_declared_budget'] for r in final['model']),
            candidate_budget_failures=sum(not r['candidate_within_declared_budget'] for r in final['model']),
            unresolved_perturbed_family_envelopes=sum(not r['restricted_family_envelope_justified'] for r in final['model']),
            uncertified_numerical_derivative_error_bounds=len(final['model']),
            limits=plan['limits'], limitations=[
                'The family fixes one contact to the bottom; this is not an unrestricted local geodesic or native correction.',
                'All models use identical original eight-node trilinear interpolation, reciprocal action and nodal kernels. Affine formulas are separate oracles only.',
                'The baseline scalar minimum is justified by strict convexity for epsilon>0. At epsilon=0 all contacts describe one curve; no unique endpoint partial is selected.',
                'Sixteen derivative brackets and high precision do not certify general perturbed minima; those model value derivatives remain unresolved.',
                'Gauss rule moments and 80/120-digit agreement are not outward quadrature or arithmetic error bounds. No eta/h derivative certificate is claimed.',
                'Finite-h central-difference truncation is reported rather than hidden by changing budgets.',
                'The two-link value has the correct zero inward derivative limit but a 3/(2sqrt(2)) excess coefficient ratio to the continuous curved connector.',
                'No domain extension, forced normal-zero derivative, production implementation, native geometry, extra link hierarchy or inversion is used.'])
        summary['output_sha256'] = {str(p.relative_to(out)): sha(p) for p in sorted(out.rglob('*')) if p.is_file()}
        save(out / 'summary.json', summary)
    except BaseException as error:
        save(out / 'checks.json', checks)
        save(out / 'failure.json', dict(error=repr(error), input_sha256=pins))
        execution.update(status='failed', failure_sha256=sha(out / 'failure.json'), finished_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
        save(out / 'execution.json', execution)
        raise


if __name__ == '__main__':
    main()
