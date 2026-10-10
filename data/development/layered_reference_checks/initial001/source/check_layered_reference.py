#!/usr/bin/env python3
"""Invented nonmonotone profile controls; no provider records or production rays."""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import shutil
import sys

import numpy as np
from scipy.optimize import brentq

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    out = (ROOT / args.output).resolve(); out.relative_to(ROOT)
    out.mkdir(parents=True)
    snapshot = out / 'source'; snapshot.mkdir()
    sources = [ROOT / 'diagnostics/first_arrival_layered_reference.py',
               ROOT / 'diagnostics/first_arrival_1d_reference.py', Path(__file__).resolve()]
    for p in sources:
        shutil.copyfile(str(p), str(snapshot / p.name))
    sys.path.insert(0, str(snapshot))
    spec = importlib.util.spec_from_file_location('layered', str(snapshot / sources[0].name))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    checks, cases = [], []

    def check(name, passed, **detail):
        checks.append(dict(name=name, passed=bool(passed), **detail))

    def close(name, value, expected, tolerance=1e-10):
        error = abs(value - expected)
        check(name, math.isfinite(error) and error <= tolerance,
              value=value, expected=expected, error=error, tolerance=tolerance)

    def run(name, z, v, s, r, derivative=False):
        bounds = [[min(s[d], r[d]) - 1, max(s[d], r[d]) + 1] for d in range(2)] + [[z[0], z[-1]]]
        a = module.enumerate_arrivals(z, v, s, r, bounds=bounds)
        cases.append(dict(name=name, profile=list(zip(z, v)), source=s, receiver=r, bounds=bounds, reference=a))
        check(name + '_complete', a['complete'] and a['reference_valid'], unresolved=a['unresolved'])
        if not a['reference_valid']:
            return a
        b = module.enumerate_arrivals(z, v, r, s, bounds=bounds)
        check(name + '_reverse_complete', b['reference_valid'])
        if b['reference_valid']:
            close(name + '_reciprocity', a['first_arrival']['time_s'], b['first_arrival']['time_s'])
        check(name + '_finite_normal_domain', all(c['turning_depth_km'] is None or z[0] <= c['turning_depth_km'] <= z[-1] for c in a['candidates']))
        length = math.sqrt(sum((x-y)**2 for x, y in zip(s, r)))
        check(name + '_speed_bounds', length/max(v)-1e-11 <= a['first_arrival']['time_s'] <= length/min(v)+1e-11)
        if derivative:
            check(name + '_unique_first_branch', len(a['near_ties']) == 1)
            for d in range(3):
                plus, minus = list(s), list(s); plus[d] += 1e-5; minus[d] -= 1e-5
                p, m = [module.enumerate_arrivals(z, v, point, r, bounds=bounds, root_tolerance=1e-14) for point in (plus, minus)]
                check(name + '_derivative_complete_' + str(d), p['reference_valid'] and m['reference_valid'])
                if p['reference_valid'] and m['reference_valid']:
                    fd = (p['first_arrival']['time_s'] - m['first_arrival']['time_s']) / 2e-5
                    close(name + '_source_derivative_' + str(d), a['first_arrival']['source_derivative_s_per_km'][d], fd, 2e-7)
        return a

    constant = run('constant', [-2, 0, 3], [5, 5, 5], [0, 0, -.3], [2, 3, 1.2], True)
    close('constant_exact', constant['first_arrival']['time_s'], math.sqrt(15.25)/5, 1e-13)
    for g in (.2, -.2):
        s, r = [.3, -.2, 0.], [8.3, 5.8, 1.]
        z = [-10., 10.]; v = [5 + g*x for x in z]
        a = run('affine_' + str(g), z, v, s, r, True)
        length = math.sqrt(sum((x-y)**2 for x,y in zip(s,r)))
        exact = 2/abs(g)*math.asinh(abs(g)*length/(2*math.sqrt(5*(5+g))))
        close('affine_exact_' + str(g), a['first_arrival']['time_s'], exact, 1e-11)
    peak = run('guide_between_endpoints', [-3, 0, 3], [3, 6, 3], [.2, -.1, -1], [12.2, 15.9, 1], True)
    q = math.sqrt(11)
    close('peak_guide_exact', peak['first_arrival']['time_s'], 2*math.log((6+q)/5)+(20-2*q)/6, 1e-12)
    check('peak_guide_is_between_endpoints', peak['first_arrival']['turning_depth_km'] == 0)
    direct = run('direct_crosses_interior_maximum', [-3, 0, 3], [3, 6, 3], [0, 0, -1], [2, 0, 1], True)
    p = brentq(lambda p: 2*(math.sqrt(1-25*p*p)-math.sqrt(1-36*p*p))/p-2 if p else -2,
               0, 1/6, xtol=1e-15)
    exact = 2*math.log(6*(1+math.sqrt(1-25*p*p))/(5*(1+math.sqrt(1-36*p*p))))
    close('interior_peak_direct_exact', direct['first_arrival']['time_s'], exact, 1e-12)
    check('equal_endpoint_speeds_do_not_create_false_flat_path', not any(c['kind']=='flat_direct' for c in direct['candidates']))
    tied = run('symmetric_valley_two_turns', [-3, 0, 3], [6, 3, 6], [0, 0, 0], [4, 0, 0])
    close('valley_exact_turning_time', tied['first_arrival']['time_s'], 2*math.asinh(4/6), 1e-12)
    check('valley_tied_branch_derivatives_retained', len(tied['near_ties']) == 2 and
          sorted(c['direction'] for c in tied['candidates'] if c['kind']=='turning') == [-1, 1])
    bounded = run('two_equal_fast_boundaries', [-3, 0, 3], [6, 3, 6], [0, 0, 0], [20, 0, 0])
    q = math.sqrt(27)
    close('boundary_guide_exact', bounded['first_arrival']['time_s'], 2*math.log((6+q)/3)+(20-2*q)/6, 1e-12)
    check('both_boundary_ties_retained', len(bounded['near_ties']) == 2)
    equal = run('equal_interior_maxima', [-4, -2, 0, 2, 4], [4, 6, 4, 6, 4], [0, 0, -3], [20, 0, 3], True)
    # Distinct guide allocations on equal maxima have the same endpoint momentum.
    q5, q4 = math.sqrt(11), math.sqrt(20)
    exact = 2*math.log((6+q5)/5)+2*math.log((6+q4)/4)+(20-2*q5-2*q4)/6
    close('equal_maxima_exact', equal['first_arrival']['time_s'], exact, 1e-12)
    check('equal_maxima_guide_allocations_retained', len(equal['near_ties']) >= 2)
    interface = run('plateau_interface_source', [-2, 0, 1], [6, 6, 4], [0, 0, 0], [2, 0, 0])
    close('interface_source_normal_derivative_zero', interface['first_arrival']['source_derivative_s_per_km'][2], 0., 0.)
    blocked = run('preceding_peak_blocks_later_low_turn', [-2, 0, 1, 3, 5], [4, 7, 4, 6, 3], [0, 0, -1], [12, 0, -.5])
    check('blocked_turn_layer_explicit', any('preceding velocity maximum' in f['reason'] for f in blocked['rejected_families']))

    # Regression against every saved, validated monotone invented case.
    prior = ROOT / 'data/development/first_arrival_1d_enumeration/checks.json'
    for case in json.loads(prior.read_text())['cases']:
        a = module.enumerate_arrivals(case['depths_km'], case['velocities_km_s'], case['source_xyz_km'], case['receiver_xyz_km'])
        name = 'monotone_regression_' + case['name']
        check(name + '_complete', a['reference_valid'])
        if a['reference_valid']:
            expected = case['result']['first_arrival']
            close(name + '_time', a['first_arrival']['time_s'], expected['time_s'], 1e-11)
            if expected['source_derivative_s_per_km'] is not None:
                for d in range(3):
                    close(name + '_source_' + str(d), a['first_arrival']['source_derivative_s_per_km'][d], expected['source_derivative_s_per_km'][d], 1e-11)
    for delta in [0., float(np.nextafter(5., np.inf))-5., 1e-12, 1e-8, .1]:
        for direction in (1, -1):
            v = [5., 5.+delta] if direction == 1 else [5.+delta, 5.]
            for transverse in (0., 1., 3.):
                a = module.enumerate_arrivals([0., 1.], v, [0., 0., 0.], [transverse, 0., 1.])
                name = 'near_flat_' + str((delta, direction, transverse))
                check(name + '_complete', a['reference_valid'])
                exact = 2*math.asinh(delta*math.hypot(transverse,1.)/(2*math.sqrt(v[0]*v[1])))/delta if delta else math.hypot(transverse,1.)/5
                if a['reference_valid']:
                    close(name + '_time', a['first_arrival']['time_s'], exact, 1e-13)
    for distance in (float(np.nextafter(40., -np.inf)), 40., float(np.nextafter(40., np.inf))):
        a = module.enumerate_arrivals([0,10], [3,5], [0,0,0], [distance,0,0])
        turns = [c for c in a['candidates'] if c['kind']=='turning']
        check('finite_boundary_membership_' + str(distance), (not a['complete'] and not turns) if distance>40 else a['reference_valid'] and len(turns)==1)
    for point in ([0,0,-np.nextafter(0.,1.)], [0,0,np.nextafter(1.,np.inf)], [2,0,.5]):
        a = module.enumerate_arrivals([0,1],[4,5],point,[.5,0,.5],bounds=[[-1,1],[-1,1],[0,1]])
        check('outside_closed_box_' + str(point), not a['complete'] and not a['reference_valid'])
    limited = module.enumerate_arrivals([-2,0,1,3,5],[4,7,4,6,3],[0,0,-1],[12,0,-.5],max_boxes=1)
    check('limited_root_search_fails_closed', not limited['complete'] and limited['first_arrival'] is None)
    report = dict(scope='Invented profiles/endpoints and saved monotone invented controls; no observational rays',
        command='PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python3 diagnostics/check_layered_reference.py --output ' + str(out.relative_to(ROOT)),
        checks=checks, cases=cases, passed=all(c['passed'] for c in checks),
        failures=[c for c in checks if not c['passed']],
        source_sha256={p.name:sha(snapshot/p.name) for p in sources},
        prior_monotone_fixture_sha256=sha(prior),
        limitations=['Candidate-count certificates do not supply interval bounds on time ranking.',
                     'Distinct tied branch derivatives are retained rather than interpreted as a unique gradient.',
                     'This is an isolated numerical component, not truth generation or a production solver replacement.'])
    (out/'results.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(checks=len(checks),passed=report['passed'],failures=report['failures']),indent=2))
    raise SystemExit(0 if report['passed'] else 1)


if __name__ == '__main__':
    main()
