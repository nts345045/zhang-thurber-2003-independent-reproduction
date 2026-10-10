#!/usr/bin/env python3
"""Invented connector controls only; independent Decimal Snell integrals."""
import argparse
import datetime
from decimal import Decimal as D, localcontext
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def sign(x):
    return D(1) if x > 0 else (D(-1) if x < 0 else D(0))


def reference(a, b, B, V, g):
    """80-digit ray legs; caller supplies Decimal coordinates/parameters.

    The comparison uses Snell distances, leg logarithms and endpoint momenta,
    rather than the tested asinh/atanh action formulas.
    """
    R = abs(b[0] - a[0])
    dz = a[1] - b[1]
    length = (R * R + dz * dz).sqrt()
    va, vb = V + g * (a[1] - B), V + g * (b[1] - B)
    direction = sign(b[0] - a[0])
    if g == 0:
        ga = (-direction * R / (V * length), dz / (V * length))
        return dict(branch='homogeneous', time=length / V,
                    source=ga, receiver=tuple(-v for v in ga),
                    maximum_depth=max(a[1], b[1]), distance=R, guide=None)
    A = (V - va) * (V + va) / (g * g)
    C = (V - vb) * (V + vb) / (g * g)
    left = R * R - A - C
    comparison = left * left - 4 * A * C
    guided = left >= 0 and comparison >= 0

    def leg(vlo, vhi, qlo, qhi, u):
        return ((vhi / vlo).ln() + ((u + qlo) / (u + qhi)).ln()) / g

    if guided:
        qa, qb = (V * V - va * va).sqrt(), (V * V - vb * vb).sqrt()
        x = (qa + qb) / g
        guide = R - x
        time = leg(va, V, qa, D(0), V) + leg(vb, V, qb, D(0), V) + guide / V
        return dict(branch='critical' if comparison == 0 else 'guide', time=time,
                    source=(-direction / V, -qa / (V * va)),
                    receiver=(direction / V, -qb / (V * vb)),
                    maximum_depth=B, distance=x + guide, guide=guide)
    if R == 0:
        return dict(branch='interior', time=abs((vb / va).ln()) / g,
                    source=(D(0), sign(dz) / va),
                    receiver=(D(0), -sign(dz) / vb),
                    maximum_depth=max(a[1], b[1]), distance=D(0), guide=None)
    # Circle center projected on x; these q values avoid u^2-v^2 cancellation.
    center = (g * g * R * R + (vb - va) * (vb + va)) / (2 * g * g * R)
    qa, qb = g * abs(center), g * abs(center - R)
    u = (va * va + qa * qa).sqrt()
    if center <= 0:
        time, x = leg(vb, va, qb, qa, u), (qb - qa) / g
        maximum = max(a[1], b[1])
    elif center >= R:
        time, x = leg(va, vb, qa, qb, u), (qa - qb) / g
        maximum = max(a[1], b[1])
    else:
        time = leg(va, u, qa, D(0), u) + leg(vb, u, qb, D(0), u)
        x, maximum = (qa + qb) / g, B + (u - V) / g
    return dict(branch='interior', time=time,
                source=(-direction / u, -sign(center) * qa / (u * va)),
                receiver=(direction / u, sign(center - R) * qb / (u * vb)),
                maximum_depth=maximum, distance=x, guide=None)


def invented_cases():
    cases = []
    def add(name, a, b, V=6., g=1.):
        cases.append(dict(name=name, a=a, b=b, bottom=1., bottom_speed=V, gradient=g))
    for ell in (0.25, 0.125, 0.0625):
        for power in (None, 22, 20, 18, 16):
            eps = 0. if power is None else 2. ** -power
            add('positive_guide_%g_%s' % (ell, power), (0., 1. - eps), (ell, 1.))
    for R, name in ((math.nextafter(4., 0.), 'below'), (4., 'at'),
                    (math.nextafter(4., math.inf), 'above')):
        add('one_leg_transition_' + name, (0., -1.), (R, 1.), V=5.)
    for R, name in ((math.nextafter(7., 0.), 'below'), (7., 'at'),
                    (math.nextafter(7., math.inf), 'above')):
        add('two_leg_transition_' + name, (0., -1.), (R, 0.), V=5.)
    for power in (26, 24, 22):
        add('near_zero_guide_%d' % power, (0., 1. - 2. ** -power), (0.001, 1.))
    add('homogeneous_oblique', (0., 1.), (1., 0.), g=0.)
    add('positive_gradient_oblique_no_guide', (0., 1.), (1., 0.))
    add('vertical', (0., 1.), (0., 0.))
    for g in (2. ** -20, 2. ** -40):
        add('weak_gradient_oblique_%g' % g, (0., 1.), (1., 0.), g=g)
        add('weak_gradient_horizontal_%g' % g, (0., 1.), (1., 1.), g=g)
        add('weak_gradient_displaced_%g' % g, (0., 1. - 2. ** -22), (0.25, 1.), g=g)
    return cases


def plain(value):
    if isinstance(value, D):
        return str(value)
    if isinstance(value, dict):
        return {k: plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    return value


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--output', required=True)
    args = p.parse_args()
    out = (ROOT / args.output).resolve()
    if ROOT not in out.parents:
        raise ValueError('Project-local fresh output required')
    out.mkdir(parents=True, exist_ok=False)
    (out / 'source').mkdir()
    inputs = {}
    for name in ('diagnostics/endpoint_connector.py', 'diagnostics/check_endpoint_connector.py',
                 'data/development/loma_endpoint_connector_proposal_001/proposal.md',
                 'data/development/loma_endpoint_connector_proposal_001/provenance.json'):
        inputs[name] = sha(ROOT / name)
        shutil.copyfile(str(ROOT / name), str(out / 'source' / Path(name).name))
    spec = importlib.util.spec_from_file_location('frozen_connector', str(out / 'source/endpoint_connector.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    cases = invented_cases()
    (out / 'invented_inputs.json').write_text(json.dumps(cases, indent=2) + '\n')
    checks, rows = [], []
    def check(name, passed, **details):
        checks.append(dict(name=name, passed=bool(passed), **plain(details)))
    with localcontext() as ctx:
        ctx.prec = 80
        for case in cases:
            name = case['name']
            try:
                a, b = tuple(map(D, case['a'])), tuple(map(D, case['b']))
                B, V, g = (D(case[k]) for k in ('bottom', 'bottom_speed', 'gradient'))
                result = module.connector(case['a'], case['b'], case['bottom'],
                                          case['bottom_speed'], case['gradient'])
                ref = reference(a, b, B, V, g)
                R = abs(b[0] - a[0])
                excess = ref['time'] - R / V
                time_error = abs(D(result['time_s']) - ref['time'])
                source_error = max(abs(D(x) - y) for x, y in zip(result['source'], ref['source']))
                receiver_error = max(abs(D(x) - y) for x, y in zip(result['receiver'], ref['receiver']))
                check(name + '/branch', result['branch'] == ref['branch'])
                if '_transition_' in name:
                    expected = {'below': 'interior', 'at': 'critical', 'above': 'guide'}[name.rsplit('_', 1)[1]]
                    check(name + '/declared_transition', result['branch'] == expected)
                if name.startswith('near_zero_guide_'):
                    expected = 'interior' if name.endswith('_22') else 'guide'
                    check(name + '/declared_transition', result['branch'] == expected)
                check(name + '/time', time_error <= D('2e-14'), error_s=time_error)
                check(name + '/momenta', max(source_error, receiver_error) <= D('2e-13'),
                      source_error_s_per_km=source_error, receiver_error_s_per_km=receiver_error)
                excess_error = abs(D(result['excess_s']) - excess)
                allowance = D('8e-14') * abs(excess) + D('1e-65')
                check(name + '/stable_excess', excess_error <= allowance,
                      error_s=excess_error, allowance_s=allowance)
                check(name + '/distance', abs(ref['distance'] - R) <= D('1e-55'))
                check(name + '/finite_box', ref['maximum_depth'] <= B + D('1e-55') and
                      min(a[1], b[1]) >= -3 and min(a[0], b[0]) >= -1 and max(a[0], b[0]) <= 8)
                reverse = module.connector(case['b'], case['a'], case['bottom'],
                                           case['bottom_speed'], case['gradient'])
                check(name + '/reciprocity', result['time_s'] == reverse['time_s'] and
                      result['source'] == reverse['receiver'] and result['receiver'] == reverse['source'])
                fd_errors = []
                h = D('1e-32')
                for endpoint in range(2):
                    for axis in range(2):
                        points = [list(a), list(b)]
                        def value(offset):
                            displaced = [v[:] for v in points]
                            displaced[endpoint][axis] += offset
                            return reference(displaced[0], displaced[1], B, V, g)['time']
                        if axis == 1 and points[endpoint][axis] == B:
                            fd = (3 * ref['time'] - 4 * value(-h) + value(-2 * h)) / (2 * h)
                        else:
                            fd = (value(h) - value(-h)) / (2 * h)
                        expected = result['source' if endpoint == 0 else 'receiver'][axis]
                        fd_errors.append(abs(fd - D(expected)))
                check(name + '/own_value_derivatives', max(fd_errors) <= D('2e-13'),
                      max_error_s_per_km=max(fd_errors), increment_km=h)
                if name == 'homogeneous_oblique':
                    expected = 1 / (D(6) * D(2).sqrt())
                    check(name + '/nonzero_bottom_normal', abs(D(result['source'][1]) - expected) < D('2e-15'))
                if name == 'positive_gradient_oblique_no_guide':
                    check(name + '/nonzero_bottom_normal', result['branch'] == 'interior' and result['source'][1] > 0)
                if name.startswith('weak_gradient_oblique_'):
                    homogeneous = D(2).sqrt() / V
                    upper = D(2).sqrt() / (V - g)
                    check(name + '/homogeneous_limit_bound',
                          homogeneous - D('2e-14') <= D(result['time_s']) <= upper + D('2e-14'))
                if name.startswith('positive_guide_'):
                    eps = B - a[1]
                    if eps:
                        leading = D(2) / 3 * (2 * g / (V ** 3)).sqrt() * eps * eps.sqrt()
                        ratio = excess / leading
                        check(name + '/fractional_power', 1 <= ratio <= 1 / (1 - g * eps / V), ratio=ratio)
                    # Old first-edge action has a finite inward partial at eps=0.
                    if not eps:
                        old_partial = -g * R / (2 * V * V)
                        h_old = D('1e-24')
                        def old_value(inward):
                            speed = V - g * inward
                            length = (R * R + inward * inward).sqrt()
                            return (length / V if not inward else
                                    length * (V / speed).ln() / (g * inward))
                        old_fd = (3 * old_value(D(0)) - 4 * old_value(h_old) +
                                  old_value(2 * h_old)) / (2 * h_old)
                        check(name + '/old_action_partial', abs(old_fd - old_partial) < D('2e-20'),
                              old_value_inward_fd=old_fd, old_partial=old_partial)
                        check(name + '/reject_derivative_only_substitution',
                              abs(old_fd - D(result['source'][1])) > D('3e-6'),
                              fixed_straight_partial=old_partial, old_value_inward_fd=old_fd,
                              connector_partial=result['source'][1])
                rows.append(dict(case=case, computed=result, independent_snell=plain(ref),
                                 exact_excess_s=str(excess), derivative_fd_errors=plain(fd_errors)))
            except Exception as error:
                check(name + '/exception', False, error=repr(error))
                rows.append(dict(case=case, error=repr(error)))

        # The horizontal remainder leaves the reduced action and source vector
        # invariant as the first knot changes; no polygon relaxation is involved.
        for power in (None, 22, 20, 18, 16):
            chosen = [r for r in rows if r['case']['name'].startswith('positive_guide_') and
                      r['case']['name'].endswith('_' + str(power)) and 'computed' in r]
            check('first_knot_invariance_%s' % power, len(chosen) == 3 and
                  len({r['computed']['excess_s'] for r in chosen}) == 1 and
                  len({tuple(r['computed']['source']) for r in chosen}) == 1)
    for name, h in inputs.items():
        check('unchanged_input/' + name, sha(ROOT / name) == h)
    summary = dict(status='passed' if all(c['passed'] for c in checks) else 'failed',
                   scope='Invented affine/homogeneous connector controls only; no native/production/global optimizer or inverse run.',
                   created_utc=datetime.datetime.utcnow().isoformat() + 'Z',
                   command=['tmp/waveform_env/bin/python', 'diagnostics/check_endpoint_connector.py',
                            '--output', str(out.relative_to(ROOT))],
                   python_version=sys.version,
                   input_sha256=inputs, passing_checks=sum(c['passed'] for c in checks),
                   total_checks=len(checks), cases=len(cases), checks=checks, results=rows,
                   scientific_source_allowance_s_per_km=3e-6,
                   control_time_allowance_s=2e-14, control_derivative_allowance_s_per_km=2e-13,
                   limitations=['80-digit Snell readback is independent arithmetic, not an outward interval proof.',
                                'Finite-box checks allow 1e-55 km Decimal roundoff only; binary input branch membership is exact rational.',
                                'No arbitrary-scale robustness or full nodal-grid Jacobian is established.',
                                'This is a changed discrete action; it is never substituted into the old polygon derivative alone.',
                                'Small stable action increments are reported separately from rounded totals. No production accumulation claim.'])
    summary['artifact_sha256'] = {str(f.relative_to(out)): sha(f) for f in sorted(out.rglob('*'))
                                 if f.is_file() and '__pycache__' not in f.parts}
    (out / 'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'status': summary['status'], 'passing_checks': summary['passing_checks'],
                      'total_checks': len(checks), 'cases': len(cases)}))
    return 0 if summary['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
