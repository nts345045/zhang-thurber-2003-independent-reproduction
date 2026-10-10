#!/usr/bin/env python3
"""Invented near-flat analytic/continuity and finite-bottom regressions."""
import argparse
import hashlib
import importlib.util
import json
import math
import sys
from datetime import datetime, timezone
from fractions import Fraction as Q
from pathlib import Path

import numpy as np
from scipy.integrate import quad

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', default='diagnostics/first_arrival_1d_reference.py')
    parser.add_argument('--output', default=str((OUT / 'near_flat_checks.json').relative_to(ROOT)))
    args = parser.parse_args()
    source, output = [(ROOT / value).resolve() for value in (args.reference, args.output)]
    assert ROOT in source.parents and ROOT in output.parents
    spec = importlib.util.spec_from_file_location('reference_under_test', str(source))
    reference = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reference)
    checks, cases = [], []

    def check(name, passed, **detail):
        checks.append(dict(name=name, passed=bool(passed), **detail))

    def close(name, value, expected, tolerance, units):
        check(name, abs(value - expected) <= tolerance, value=value, expected=expected,
              absolute_error=abs(value - expected), tolerance=tolerance, units=units)

    for delta in [0., float(np.nextafter(5., np.inf)) - 5., 1e-12, 1e-8, 1e-4, .1]:
        v = [5., 5. + delta]
        gradient = v[1] - v[0]
        profile = [(Q(0), Q(v[0])), (Q(1), Q(v[1]))]
        for u in [None, Q(10)]:
            x, time = reference.leg(profile, Q(0), Q(1), u)
            def integrand(z):
                velocity = v[0] + gradient * z
                return 1 / velocity if u is None else 10 / (velocity * math.sqrt(100 - velocity * velocity))
            expected, quad_error = quad(integrand, 0., 1., epsabs=1e-13, epsrel=1e-13)
            close('leg_quad_' + str((gradient, u)), time, expected, 1e-13, 's')
        for horizontal in [0., 1., 3.]:
            a, b = [0., 0., 0.], [horizontal, 0., 1.]
            name = str((gradient, horizontal))
            result = reference.enumerate_arrivals([0., 1.], v, a, b)
            length = math.hypot(horizontal, 1.)
            # acosh(1+x)=2*asinh(sqrt(x/2)) avoids loss of x near zero.
            exact = (2 * math.asinh(gradient * length / (2 * math.sqrt(v[0] * v[1]))) / gradient
                     if gradient else length / v[0])
            case = dict(gradient_km_s_per_km=gradient, source_xyz_km=a, receiver_xyz_km=b,
                        velocities_km_s=v, exact_affine_time_s=exact, result=result)
            cases.append(case)
            check('complete_' + name, result['complete'] and result['reference_valid'])
            first = result.get('first_arrival')
            if not first:
                continue
            close('stable_affine_time_' + name, first['time_s'], exact, 1e-13, 's')
            check('bounded_velocity_time_' + name,
                  length / v[1] - 1e-13 <= first['time_s'] <= length / v[0] + 1e-13)
            points = reference.sample_path([0., 1.], v, a, b, first, .05)
            path_length = sum(math.sqrt(sum((y - x) ** 2 for x, y in zip(p, q)))
                              for p, q in zip(points, points[1:]))
            deviation = max(abs(p[0] - horizontal * p[2]) / length for p in points)
            case.update(path_points=points, path_length_km=path_length,
                        maximum_distance_from_straight_line_km=deviation)
            check('path_domain_' + name, points[0] == a and points[-1] == b and
                  all(0 <= p[2] <= 1 for p in points))
            if gradient <= 1.1e-12:
                close('constant_limit_path_length_' + name, path_length, length, 2e-12, 'km')
                close('constant_limit_line_deviation_' + name, deviation, 0., 2e-12, 'km')

    # A rounded midpoint must not certify a turning root beyond the finite bottom.
    boundary_cases = []
    for distance in [float(np.nextafter(40., -np.inf)), 40., float(np.nextafter(40., np.inf))]:
        result = reference.enumerate_arrivals([0., 10.], [3., 5.], [0., 0., 0.], [distance, 0., 0.])
        turns = [c for c in result['candidates'] if c['kind'] == 'turning']
        boundary_cases.append(dict(horizontal_distance_km=distance, result=result))
        if distance > 40:
            check('outside_bottom_no_certified_turn', not turns)
            check('outside_bottom_ambiguous_membership_fails_closed', not result['complete'])
        elif distance == 40:
            check('exact_bottom_turn_retained', result['complete'] and len(turns) == 1 and
                  turns[0]['turning_depth_km'] == 10)
        else:
            check('inside_bottom_turn_retained', result['complete'] and len(turns) == 1)

    document = dict(created_utc=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                    geometry_status='All profiles/endpoints invented; no provider records',
                    reference_file=str(source.relative_to(ROOT)),
                    sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in (source, Path(__file__).resolve())},
                    cases=cases, finite_bottom_cases=boundary_cases, checks=checks,
                    passed=all(c['passed'] for c in checks),
                    failed_checks=[c for c in checks if not c['passed']])
    output.write_text(json.dumps(document, indent=2, allow_nan=False) + '\n')
    print('{} checks; {} failures'.format(len(checks), len(document['failed_checks'])))
    if not document['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
