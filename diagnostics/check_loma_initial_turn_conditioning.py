#!/usr/bin/env python3
"""Isolate the preserved LON near-knot turning closure failure; never replace it."""
import argparse
import csv
from decimal import Decimal as D, localcontext
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import shutil
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'data/development/loma_lon_initial_reference_001'

def require(value, message):
    if not value:
        raise ValueError(message)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def decimal_fraction(value):
    return D(value.numerator) / D(value.denominator)

def decimal_velocity(profile, depth):
    for (a, va), (b, vb) in zip(profile, profile[1:]):
        if a <= depth <= b:
            return va + (vb - va) * (depth - a) / (b - a)
    raise ValueError('Outside finite profile')

def decimal_leg(profile, start, stop, squared_u):
    """Independent Snell leg: X=int(v/sqrt(u²-v²)) dz, T=int(u/(v sqrt(u²-v²))) dz."""
    distance, time = D(0), D(0)
    u = squared_u.sqrt()
    for (a, va), (b, vb) in zip(profile, profile[1:]):
        lo, hi = max(start, a), min(stop, b)
        if hi <= lo:
            continue
        slope = (vb - va) / (b - a)
        vl, vh = va + slope * (lo - a), va + slope * (hi - a)
        ql, qh = (squared_u - vl * vl).sqrt(), (squared_u - vh * vh).sqrt()
        if slope:
            distance += (hi - lo) * (vl + vh) / (ql + qh)
            time += ((vh / vl) * ((u + ql) / (u + qh))).ln() / slope
        else:
            distance += (hi - lo) * vl / ql
            time += (hi - lo) * u / (vl * ql)
    return distance, time

def decimal_branch(profile, source_z, receiver_z, layer, transverse, r):
    """Use r²=u²-v(layer top)², retaining the small difference before sqrt."""
    a, va = profile[layer]
    b, vb = profile[layer + 1]
    require(source_z <= a and receiver_z <= a, 'This narrow case requires endpoints above the turning layer')
    slope = (vb - va) / (b - a)
    squared_u = va * va + r * r
    u = squared_u.sqrt()
    require(va <= u <= vb, 'Turn outside selected finite layer')
    x1, t1 = decimal_leg(profile, source_z, a, squared_u)
    x2, t2 = decimal_leg(profile, receiver_z, a, squared_u)
    # Each partial leg within the turning layer ends at q=0. This avoids
    # reconstructing a rounded turning depth and then subtracting its velocity.
    distance = x1 + x2 + 2 * r / slope
    time = t1 + t2 + 2 * ((u + r) / va).ln() / slope
    vs = decimal_velocity(profile, source_z)
    return dict(r=r, squared_u=squared_u, u=u,
        turning_depth=a + (u - va) / slope,
        distance=distance, distance_residual=distance - transverse, time=time,
        p=1 / u, source_normal=-(squared_u - vs * vs).sqrt() / (u * vs))

def strings(record):
    return {key: str(value) for key, value in record.items()}

def neighbours(value, steps=4):
    result = {0:value}
    lo = hi = value
    for count in range(1, steps + 1):
        lo, hi = float(np.nextafter(lo, -math.inf)), float(np.nextafter(hi, math.inf))
        result[-count], result[count] = lo, hi
    return sorted(result.items())

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    out = (ROOT / args.output).resolve()
    require(out != PACKAGE and PACKAGE not in out.parents and out not in PACKAGE.parents, 'Preserve original package')
    out.mkdir(parents=True)
    inputs = out / 'inputs'; inputs.mkdir()
    names = ['summary.json', 'execution.json', 'invalid_cases.json', 'review.json', 'independent_review.json',
             'inputs/initial_grid.csv', 'source/first_arrival_1d_reference.py']
    hashes = {name:sha(PACKAGE / name) for name in names}
    for name in names:
        dest = inputs / name; dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(str(PACKAGE / name), str(dest))
        require(sha(dest) == hashes[name], 'Changed while freezing ' + name)
    shutil.copyfile(str(Path(__file__).resolve()), str(out / 'check.py'))
    summary = json.loads((inputs / 'summary.json').read_text())
    ledger = json.loads((inputs / 'execution.json').read_text())
    require(ledger['status'] == 'completed' and ledger['summary_sha256'] == hashes['summary.json'], 'Not completed original reference')
    case = json.loads((inputs / 'invalid_cases.json').read_text())['cases']
    require(len(case) == 1 and case[0]['saved_row']['pair_index'] == '8156', 'Unexpected preserved failure')
    row = case[0]['saved_row']; reference = case[0]['unchanged_certificate']['reference']
    require(not reference['reference_valid'] and reference['first_arrival'] is None, 'Original invalid status changed')
    candidate = reference['candidates'][0]
    profile_q = [(Q(float(z)), Q(float(v))) for z, v in summary['profile_depth_velocity_km_km_s']]
    source = [float(row['source_' + axis]) for axis in 'xyz']
    receiver = [float(row['receiver_' + axis]) for axis in 'xyz']
    dx, dy = receiver[0] - source[0], receiver[1] - source[1]
    distance = math.hypot(dx, dy)
    module_path = inputs / 'source/first_arrival_1d_reference.py'
    spec = importlib.util.spec_from_file_location('unchanged_reference', str(module_path))
    old = importlib.util.module_from_spec(spec); spec.loader.exec_module(old)
    zs, zr = Q(source[2]), Q(receiver[2]); layer = candidate['layer']
    branch = old.branch(profile_q, zs, zr, layer)
    lo, hi = candidate['root_interval']; middle = (lo + hi) / 2
    original_u = Q(math.sqrt(float(branch['u0'] ** 2 + Q(middle) ** 2)))
    (a, va), (b, vb) = profile_q[layer:layer + 2]
    original_turn = a + (original_u - va) * (b - a) / (vb - va)
    x1, t1 = old.leg(profile_q, zs, original_turn, original_u)
    x2, t2 = old.leg(profile_q, zr, original_turn, original_u)
    require(x1 + x2 - distance == candidate['distance_residual_km'] and t1 + t2 == candidate['time_s'], 'Original candidate replay differs')
    require(float(original_turn) == candidate['turning_depth_km'], 'Original turn replay differs')
    controls = []
    fine = None
    for precision in (80, 100):
        with localcontext() as context:
            context.prec = precision
            profile = [(decimal_fraction(z), decimal_fraction(v)) for z, v in profile_q]
            sd, rd, target = D.from_float(source[2]), D.from_float(receiver[2]), D.from_float(distance)
            def evaluate(r):
                return decimal_branch(profile, sd, rd, layer, target, r)
            left, right = D.from_float(lo), D.from_float(hi)
            fl, fr = evaluate(left)['distance_residual'], evaluate(right)['distance_residual']
            require(fl * fr < 0, 'Independent leg evaluation does not bracket the saved root')
            iterations = 0
            while right - left > D(10) ** (20 - precision):
                mid = (left + right) / 2
                fm = evaluate(mid)['distance_residual']
                if fm == 0:
                    left = right = mid
                    break
                if (fm > 0) == (fl > 0):
                    left, fl = mid, fm
                else:
                    right, fr = mid, fm
                iterations += 1
                require(iterations < 500, 'Independent bisection did not terminate')
            root = evaluate((left + right) / 2)
            root['source_dx'] = -root['p'] * D.from_float(dx) / target
            root['source_dy'] = -root['p'] * D.from_float(dy) / target
            original_r = (decimal_fraction(original_u) ** 2 - profile[layer][1] ** 2).sqrt()
            controls.append(dict(decimal_precision=precision, root=strings(root),
                iterations=iterations, original_u_evaluated_independently=strings(evaluate(original_r)),
                saved_bracket_midpoint_without_u_rounding=strings(evaluate(D.from_float(middle)))))
            if precision == 100:
                rows = []
                for parameter, center in [('u', float(root['u'])), ('turning_depth', float(root['turning_depth'])), ('r', float(root['r']))]:
                    for offset, value in neighbours(center):
                        d = D.from_float(value)
                        if parameter == 'u':
                            rr = (d * d - profile[layer][1] ** 2).sqrt()
                        elif parameter == 'turning_depth':
                            v = decimal_velocity(profile, d)
                            rr = (v * v - profile[layer][1] ** 2).sqrt()
                        else:
                            rr = d
                        record = evaluate(rr)
                        rows.append(dict(parameter=parameter, binary64_offset=offset, value=value,
                            hex=value.hex(), distance_residual_km=str(record['distance_residual']),
                            absolute_residual_within_original_gate=abs(record['distance_residual']) <= D('1e-8'),
                            u=str(record['u']), turning_depth_km=str(record['turning_depth']), time_s=str(record['time'])))
                fine = root
    with (out / 'nearby_parameters.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    result = dict(status='diagnostic_complete_original_failure_preserved',
        scope='One previously isolated turning branch only; independent high-precision action/distance and representable-parameter diagnosis',
        native_row=row, original_candidate=candidate, original_reference_valid=False,
        original_selected_time_and_derivatives_remain_blank=True, original_distance_tolerance_km=1e-8,
        original_reconstruction_reproduced_exactly=True, original_turn_rational=str(original_turn),
        original_u_binary64=float(original_u), original_u_hex=float(original_u).hex(),
        original_squared_velocity_excess=str(original_u * original_u - branch['u0'] ** 2),
        saved_bracket_midpoint_binary64=middle,
        exact_squared_velocity_excess_before_u_rounding=str(Q(middle) ** 2),
        high_precision_controls=controls,
        nearby_minimum_absolute_residual_km={p:str(min(abs(D(r['distance_residual_km'])) for r in rows if r['parameter']==p)) for p in ('u','turning_depth','r')},
        numerical_geometry_basis='Binary64 source/receiver coordinates, their binary64 transverse coordinate differences and math.hypot target are treated as exact; geometry is not recomputed at higher precision.',
        limitations=['This diagnoses arithmetic for one already isolated branch, not a new completeness or interval time-ordering proof.',
            '80/100-digit agreement is independent high-precision numerical evidence, not directed-rounding interval certification.',
            'No candidate is promoted to an accepted reference and no original numerical helper, reference table, forward model or inverse calculation is changed.'],
        input_sha256=hashes, diagnostic_source_sha256=sha(out / 'check.py'))
    for name, digest in hashes.items():
        require(sha(PACKAGE / name) == sha(inputs / name) == digest, 'Original changed during diagnosis: ' + name)
    result['output_sha256'] = {str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()}
    (out / 'summary.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps(dict(status=result['status'], min_closure=result['nearby_minimum_absolute_residual_km']), indent=2))

if __name__ == '__main__':
    main()
