#!/usr/bin/env python3
"""Frozen candidate-arithmetic checks plus unchanged monotone/near-flat suites."""
import argparse
import contextlib
from decimal import Decimal as D, localcontext
from fractions import Fraction as Q
import hashlib
import importlib.util
import inspect
import io
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OLD_SHA = '13020fef85113c302b27d846e1b4286c13576348a10710ba8a4c6fbd999e1c98'

def require(value, message):
    if not value:
        raise ValueError(message)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load(path, name):
    spec = importlib.util.spec_from_file_location(name, str(path))
    result = importlib.util.module_from_spec(spec); sys.modules[name] = result
    spec.loader.exec_module(result)
    return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--variant', required=True)
    args = parser.parse_args()
    require(args.variant.replace('_', '').isalnum(), 'Simple variant name required')
    require(__debug__, 'Existing regression assertions require Python without -O')
    out = ROOT / 'data/development/precise_turn_reference_checks' / args.variant
    out.mkdir(parents=True); source = out / 'source'; source.mkdir()
    names = ['diagnostics/first_arrival_1d_reference.py', 'diagnostics/first_arrival_1d_precise_turn_reference.py',
             'diagnostics/check_precise_turn_reference.py',
             'data/development/first_arrival_1d_enumeration/check_reference.py',
             'data/development/first_arrival_1d_enumeration/check_near_flat.py',
             'data/hayward/initial_grid.csv',
             'data/development/loma_lon_initial_reference_001/invalid_cases.json',
             'data/development/loma_lon_initial_reference_001/summary.json',
             'data/development/loma_lon_initial_conditioning_001/summary.json']
    hashes = {n:sha(ROOT / n) for n in names}
    require(hashes[names[0]] == OLD_SHA, 'Old validated reference changed')
    for name in names:
        target = source / name; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(str(ROOT / name), str(target))
        require(sha(target) == hashes[name], 'Changed during freeze')
    old = load(source / names[0], 'frozen_old_reference')
    new = load(source / names[1], 'frozen_precise_turn_reference')
    checks, enclosure_cases = [], []
    def check(name, condition, **details):
        checks.append(dict(name=name, passed=bool(condition), **details))
    for name in ('Interval', 'integer_sqrt', 'sqrt', 'constant', 'velocity', 'pieces',
                 'coefficients', 'branch', 'equation', 'point_sign', 'turning_roots', 'leg', 'distance_limit', 'compare_limit'):
        check('unchanged_' + name, inspect.getsource(getattr(old, name)) == inspect.getsource(getattr(new, name)))
    values = [Q(0), Q(1), Q(2), Q(17, 5)]
    for exponent in (-1000, -400, -50, 0, 50, 400, 1000):
        for excess in (Q(0), Q(2) ** -80, Q(2) ** -240):
            values.append(Q(2) ** (2 * exponent) * (1 + excess))
    for index, value in enumerate(values):
        middle, (lo, hi) = new.candidate_sqrt_enclosure(value)
        check('exact_enclosure_' + str(index), lo * lo <= value <= hi * hi and lo <= middle <= hi)
        check('relative_enclosure_' + str(index), value == 0 and lo == hi == 0 or
              value > 0 and (hi - lo) ** 2 <= value * Q(2) ** -254)
        with localcontext() as context:
            context.prec = 120
            exact = (D(value.numerator) / D(value.denominator)).sqrt()
            dl, dh = D(lo.numerator) / D(lo.denominator), D(hi.numerator) / D(hi.denominator)
            # Independently rounded Decimal conversions cannot lie inside a
            # zero-width exact rational interval in every exponent range.
            # An exact squared identity is stronger for a collapsed enclosure.
            check('independent_enclosure_' + str(index), lo * lo == value if lo == hi else dl <= exact <= dh,
                  method='exact_square' if lo == hi else '120_digit_decimal')
        enclosure_cases.append(dict(square=str(value), lower=str(lo), upper=str(hi), midpoint=str(middle)))
    for value, bits in [(Q(-1), 128), (Q(2), 0), (Q(2), 1), (Q(2), 2.5)]:
        rejected = False
        try:
            new.candidate_sqrt_enclosure(value, bits)
        except ValueError:
            rejected = True
        check('reject_invalid_' + str((value, bits)), rejected)
    failure = json.loads((source / names[-3]).read_text())['cases'][0]
    native = failure['saved_row']; original = failure['unchanged_certificate']['reference']
    package = json.loads((source / names[-2]).read_text())
    profile = package['profile_depth_velocity_km_km_s']; z, v = zip(*profile)
    start = [float(native['source_' + k]) for k in 'xyz']
    stop = [float(native['receiver_' + k]) for k in 'xyz']
    corrected = new.enumerate_arrivals(z, v, start, stop)
    check('native_original_still_invalid', not original['reference_valid'] and original['first_arrival'] is None)
    check('native_variant_complete_valid', corrected['complete'] and corrected['reference_valid'])
    check('native_branch_count_unchanged', len(corrected['candidates']) == len(original['candidates']))
    check('native_root_interval_unchanged', corrected['candidates'][0]['root_interval'] == original['candidates'][0]['root_interval'])
    check('native_gates_unchanged', corrected['root_tolerance'] == original['root_tolerance'] == 1e-12 and
          corrected['distance_tolerance_km'] == original['distance_tolerance_km'] == 1e-8)
    first = corrected.get('first_arrival')
    require(first is not None, 'Near-knot candidate remains invalid; preserve this failed control')
    exact = json.loads((source / names[-1]).read_text())['high_precision_controls'][-1]['root']
    time_error = abs(first['time_s'] - float(exact['time']))
    target_gradient = [float(exact[k]) for k in ('source_dx', 'source_dy', 'source_normal')]
    source_error = math.sqrt(sum((a - b) ** 2 for a, b in zip(first['source_derivative_s_per_km'], target_gradient)))
    check('native_existing_time_limit', time_error <= 2.5e-5, absolute_error_s=time_error, unchanged_limit_s=2.5e-5)
    check('native_existing_source_norm_limit', source_error <= 3e-6, euclidean_error_s_per_km=source_error, unchanged_limit_s_per_km=3e-6)
    for candidate in corrected['candidates']:
        lo, hi = map(Q, candidate['turning_u_enclosure_rational']); w = Q(candidate['turning_u_squared_rational'])
        u = Q(candidate['u_rational']); turn = Q(candidate['turning_depth_rational'])
        check('native_saved_exact_enclosure', lo * lo <= w <= hi * hi and u == (lo + hi) / 2)
        qprofile = [(Q(float(a)), Q(float(b))) for a, b in profile]
        check('native_rational_turn_matches_velocity', new.velocity(qprofile, turn) == u and Q(z[0]) <= turn <= Q(z[-1]))
    path = new.sample_path(z, v, start, stop, first, .05)
    check('native_sample_exact_endpoints_finite_domain', path[0] == start and path[-1] == stop and
          all(all(math.isfinite(q) for q in point) and z[0] <= point[2] <= z[-1] for point in path))
    check('native_sample_turn_retained', any(point[2] == first['turning_depth_km'] for point in path))
    original_p = first['p_s_per_km']; altered = dict(first); altered['p_s_per_km'] = original_p * 1.001
    check('native_sampler_uses_rational_u_not_rounded_p', new.sample_path(z, v, start, stop, altered, .05) == path)
    (out / 'native_case.json').write_text(json.dumps(dict(native_row=native, original_reference=original,
        diagnostic_variant_reference=corrected, independent_high_precision_root=exact,
        time_error_s=time_error, source_euclidean_error_s_per_km=source_error,
        sampler_points=path, original_failed_table_unchanged=True), indent=2, allow_nan=False) + '\n')
    # Run the existing suite assertions unchanged, rebinding only its reference
    # API and output directory. Its model/examples and thresholds are untouched.
    legacy = load(ROOT / names[3], 'unchanged_monotone_suite')
    legacy.enumerate_arrivals = new.enumerate_arrivals; legacy.sample_path = new.sample_path
    legacy.OUT = out / 'monotone'; legacy.OUT.mkdir()
    output = io.StringIO(); legacy_code = 0
    try:
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            legacy.main()
    except SystemExit as error:
        legacy_code = error.code
    (out / 'monotone.log').write_text(output.getvalue())
    inherited = json.loads((legacy.OUT / 'checks.json').read_text())
    check('unchanged_monotone_suite_pass', legacy_code == 0 and inherited['passed'], count=inherited['check_count'])
    for case in inherited['cases']:
        for index, candidate in enumerate(case['result']['candidates']):
            without_metadata = {k:v for k,v in candidate.items() if k not in
                ('u_rational','turning_depth_rational','turning_u_squared_rational',
                 'turning_u_enclosure_rational','turning_u_enclosure_relative_bits')}
            args0 = (case['depths_km'],case['velocities_km_s'],case['source_xyz_km'],case['receiver_xyz_km'],without_metadata,.25)
            check('legacy_sampler_parity_' + case['name'] + '_' + str(index), old.sample_path(*args0) == new.sample_path(*args0))
    fraction_source, fraction_receiver = [Q(1,3),Q(1,7),Q(7,13)], [Q(7,5),Q(2,3),Q(3,2)]
    fraction_result = old.enumerate_arrivals([0,10],[4,6],fraction_source,fraction_receiver)
    for index,candidate in enumerate(fraction_result['candidates']):
        args0 = ([0,10],[4,6],fraction_source,fraction_receiver,candidate,.1)
        check('legacy_fraction_input_sampler_parity_' + str(index),old.sample_path(*args0) == new.sample_path(*args0))
    command = ['python3', names[4], '--reference', str((source / names[1]).relative_to(ROOT)),
               '--output', str((out / 'near_flat_checks.json').relative_to(ROOT))]
    with (out / 'near_flat.log').open('w') as stream:
        code = subprocess.call(command, cwd=str(ROOT), env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1'),
                               stdout=stream, stderr=subprocess.STDOUT)
    near_flat = json.loads((out / 'near_flat_checks.json').read_text())
    check('unchanged_near_flat_suite_pass', code == 0 and near_flat['passed'], count=len(near_flat['checks']))
    for name, digest in hashes.items():
        require(sha(ROOT / name) == sha(source / name) == digest, 'Source/input changed during checks: ' + name)
    result = dict(status='passed' if all(r['passed'] for r in checks) else 'failed_checks_preserved',
        checks=checks, check_count=len(checks), failed_checks=[r for r in checks if not r['passed']],
        inherited_monotone_checks=inherited['check_count'], inherited_near_flat_checks=len(near_flat['checks']),
        enclosure_cases=enclosure_cases, source_input_sha256=hashes,
        command='PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python3 diagnostics/check_precise_turn_reference.py --variant ' + args.variant,
        near_flat_command=command, old_reference_unchanged=True,
        scope='Candidate-arithmetic component and one identified diagnostic case; no full batch or forward/inverse run',
        legacy_suite_method='Original assertion functions/model inputs unchanged; enumerate_arrivals and sample_path rebound to the frozen variant, OUT redirected. The overall source map pins the actual numerical variant; legacy internal hashes also retain the original baseline module.',
        limitations=['One corrected diagnostic branch is not a replacement of original failed reference data.',
                    'Root enumeration and ordinary time ranking keep their prior scope; high-precision sqrt enclosure does not certify all downstream floating-point arithmetic.'])
    result['output_sha256']={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()}
    (out / 'summary.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(status=result['status'],checks=len(checks),monotone=inherited['check_count'],
                         near_flat=len(near_flat['checks']),failures=result['failed_checks']),indent=2))
    if result['failed_checks']:
        raise SystemExit(1)

if __name__ == '__main__':
    main()
