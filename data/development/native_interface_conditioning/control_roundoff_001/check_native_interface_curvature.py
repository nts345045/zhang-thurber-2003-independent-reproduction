#!/usr/bin/env python3
"""Scalar interval curvature on one saved direction; no solve or new path."""
import argparse
import csv
from decimal import Decimal, localcontext
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import time

ROOT = Path(__file__).resolve().parents[1]
SUPPORT_SHA = '0ed7c9e024366248cbd4f105a10b17dca3e876dfa24605c4ca984faf15622e67'
SQRT_SHA = '55f3bd520aa472a3e4d4042808403eaa850c952301ea95d461331af9917ab5f2'
CORE_SHA = '7111f67c896b7b93d344372423259e288533210807392e7da2eec72f0c55caed'
METRIC_SHA = 'a282299431787361ff343dd71fc984fad0abcb675f7bf23b42189d1c61ba8732'
IDS = ['event', 'station', 'source_event_resource_id', 'source_origin_resource_id',
       'receiver_channel_seed_id', 'receiver_channel_fdsn_source_id',
       'receiver_metadata_epoch_start', 'receiver_metadata_epoch_end']
FIELDS = ['action', 'first_variation', 'geometric', 'cross', 'medium', 'total',
          'midpoint_metric', 'mean_metric', 'mean_longitudinal', 'length']


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    with path.open() as stream:
        return list(csv.DictReader(stream))


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def display(interval):
    return dict(lower_rational=str(interval[0]), upper_rational=str(interval[1]),
                lower_display=float(interval[0]), upper_display=float(interval[1]))


def overlap(a, b):
    return max(a[0], b[0]) <= min(a[1], b[1])


def sign_status(value):
    if value[0] > 0:
        return 'strictly_positive'
    if value[1] < 0:
        return 'strictly_negative'
    return 'exact_zero' if value == (0, 0) else 'sign_inconclusive'


def normal_derivatives(profile, x, displacement, arithmetic):
    """Reject moved kink endpoints; no arbitrary side of a cusp is chosen."""
    candidates = [(b-a, vb-va) for (a, va), (b, vb) in zip(profile, profile[1:]) if a <= x <= b]
    require(candidates, 'Endpoint outside finite x profile')
    slopes = set(dv/dx for dx, dv in candidates)
    kink = len(slopes) != 1
    if kink:
        require(displacement == 0, 'Kink endpoint has nonzero normal direction')
        return Q(0), Q(0), True
    slope = next(iter(slopes)); velocity = arithmetic.speed(profile, x)
    return -slope/velocity**2, 2*slope*slope/velocity**3, False


def curvature(profile, a, b, da, db, arithmetic, square_root):
    p, add, sub, mul, div = arithmetic.point, arithmetic.add, arithmetic.sub, arithmetic.mul, arithmetic.div
    e = [y-x for x, y in zip(a, b)]; r = [y-x for x, y in zip(da, db)]
    squared = sum(x*x for x in e); r_squared = sum(x*x for x in r)
    require(squared > 0, 'Zero-length edge')
    length = square_root(squared, arithmetic.SQRT_BITS)[1]
    require(0 < length[0] and length[0]**2 <= squared <= length[1]**2, 'Invalid length enclosure')
    sp_a, spp_a, kink_a = normal_derivatives(profile, a[0], da[0], arithmetic)
    sp_b, spp_b, kink_b = normal_derivatives(profile, b[0], db[0], arithmetic)
    dx = e[0]; log_terms = 0; log_tail = Q(0)
    sa, sb = 1/arithmetic.speed(profile, a[0]), 1/arithmetic.speed(profile, b[0])
    if dx:
        lo, hi = sorted((a[0], b[0])); cuts = [lo]+[x for x, v in profile if lo < x < hi]+[hi]
        primitive = p(0)
        for left, right in zip(cuts, cuts[1:]):
            va, vb = arithmetic.speed(profile, left), arithmetic.speed(profile, right)
            if va == vb:
                part = p((right-left)/va)
            else:
                logarithm, terms, tail = arithmetic.logarithm(vb/va)
                log_terms = max(log_terms, terms); log_tail = max(log_tail, tail)
                part = div(logarithm, p((vb-va)/(right-left)))
            primitive = add(primitive, part)
        average = div(primitive, p(abs(dx)))
        ja = div(sub(average, p(sa)), p(dx)); jb = div(sub(p(sb), average), p(dx))
        jaa = sub(div(mul(p(2), sub(average, p(sa))), p(dx*dx)), p(sp_a/dx))
        jab = div(sub(p(sa+sb), mul(p(2), average)), p(dx*dx))
        jbb = sub(p(sp_b/dx), div(mul(p(2), sub(p(sb), average)), p(dx*dx)))
        first_j = add(mul(ja, p(da[0])), mul(jb, p(db[0])))
        second_j = add(add(mul(jaa, p(da[0]**2)), mul(jab, p(2*da[0]*db[0]))), mul(jbb, p(db[0]**2)))
    else:
        cuts = [a[0]]; average = p(sa)
        if kink_a:
            require(da[0] == db[0] == 0, 'Aligned kink has normal movement')
            first_j = second_j = p(0)
        else:
            require(sp_a == sp_b and spp_a == spp_b, 'Aligned smooth derivative mismatch')
            first_j = p(sp_a*(da[0]+db[0])/2)
            second_j = p(spp_a*(da[0]**2+da[0]*db[0]+db[0]**2)/3)
    er = sum(x*y for x, y in zip(e, r)); transverse = r_squared-er*er/squared
    require(transverse >= 0, 'Exact transverse square is negative')
    factor = div(average, length); length_first = div(p(er), length)
    geometric = mul(factor, p(transverse))
    cross = mul(mul(p(2), length_first), first_j)
    medium = mul(length, second_j)
    values = dict(action=mul(length, average),
                  first_variation=add(mul(length_first, average), mul(length, first_j)),
                  geometric=geometric, cross=cross, medium=medium,
                  total=add(add(geometric, cross), medium),
                  midpoint_metric=div(p(r_squared/arithmetic.speed(profile, (a[0]+b[0])/2)), length),
                  mean_metric=mul(factor, p(r_squared)),
                  mean_longitudinal=mul(factor, p(er*er/squared)), length=length)
    return dict(values={k: arithmetic.rounded(v) for k, v in values.items()},
                dx=dx, transverse_crossings=max(0, len(cuts)-2), aligned=not dx,
                aligned_kink=not dx and kink_a, endpoint_kinks=int(kink_a)+int(kink_b),
                max_log_terms=log_terms, max_log_tail=log_tail)


def controls(arithmetic, square_root):
    checks = []; records = []
    def check(name, ok):
        checks.append(dict(name=name, passed=bool(ok))); require(ok, name)
    p = arithmetic.point
    homogeneous = [(Q(-2), Q(6)), (Q(3), Q(6))]
    affine = [(Q(-2), Q(4)), (Q(3), Q(9))]
    crossing = [(Q(-2), Q(4)), (Q(0), Q(5)), (Q(3), Q(8))]
    zero = (Q(0),)*3
    cases = [
        ('homogeneous_transverse', homogeneous, (-1, 0, 0), (1, 0, 0), zero, (0, 1, 0), Q(1, 12)),
        ('homogeneous_longitudinal', homogeneous, (-1, 0, 0), (1, 0, 0), zero, (1, 0, 0), Q(0)),
        ('affine_oblique', affine, (-1, Q(1, 3), Q(1, 2)), (2, Q(-1, 4), Q(3, 2)),
         (Q(1, 4), Q(-1, 3), Q(1, 5)), (Q(-1, 6), Q(1, 2), Q(-1, 7)), None),
        ('affine_equal_x', affine, (Q(1, 2), 0, 0), (Q(1, 2), 2, 1),
         (Q(1, 4), Q(1, 5), 0), (Q(-1, 3), 0, Q(-1, 7)), None),
        ('crossing_fixed_normals', crossing, (-1, Q(1, 3), Q(1, 2)), (2, Q(-1, 4), Q(3, 2)),
         (0, Q(-1, 3), Q(1, 5)), (0, Q(1, 2), Q(-1, 7)), None),
        ('affine_tiny_nonzero_dx', affine, (Q(1, 2), 0, 0), (Q(1, 2)+Q(1, 2**100), 2, 1),
         (1, 0, 0), (1, 0, 0), None)]
    with localcontext() as context:
        context.prec = 170
        h = Q(1, 10**30)
        for name, profile, a, b, da, db, known in cases:
            a, b, da, db = [tuple(map(Q, v)) for v in (a, b, da, db)]
            result = curvature(profile, a, b, da, db, arithmetic, square_root)
            value = result['values']; decimal = arithmetic.decimal_value
            action = arithmetic.decimal_action(profile, a, b)
            plus = arithmetic.decimal_action(profile, [x+h*d for x, d in zip(a, da)], [x+h*d for x, d in zip(b, db)])
            minus = arithmetic.decimal_action(profile, [x-h*d for x, d in zip(a, da)], [x-h*d for x, d in zip(b, db)])
            fd = (plus-2*action+minus)/decimal(h*h)
            check(name+'_independent_action_enclosed', decimal(value['action'][0]) <= action <= decimal(value['action'][1]))
            check(name+'_independent_second_difference_enclosed', decimal(value['total'][0]) <= fd <= decimal(value['total'][1]))
            if known is not None:
                check(name+'_exact_curvature', value['total'][0] <= known <= value['total'][1])
            reverse = curvature(profile, b, a, db, da, arithmetic, square_root)
            check(name+'_reversal', all(overlap(value[k], reverse['values'][k]) for k in FIELDS))
            check(name+'_metric_decomposition', overlap(value['mean_metric'], arithmetic.add(value['geometric'], value['mean_longitudinal'])))
            if name == 'affine_tiny_nonzero_dx':
                check('tiny_dx_retained_exactly', result['dx'] == Q(1, 2**100) and not result['aligned'])
            if name == 'crossing_fixed_normals':
                fraction = -a[0]/(b[0]-a[0])
                c = tuple(x+fraction*(y-x) for x, y in zip(a, b))
                dc = tuple(x+fraction*(y-x) for x, y in zip(da, db))
                left = curvature(profile, a, c, da, dc, arithmetic, square_root)['values']
                right = curvature(profile, c, b, dc, db, arithmetic, square_root)['values']
                check('fixed_fraction_crossing_action_additivity', overlap(value['action'], arithmetic.add(left['action'], right['action'])))
                check('fixed_fraction_crossing_curvature_additivity', overlap(value['total'], arithmetic.add(left['total'], right['total'])))
                check('fixed_fraction_crossing_fd_in_split_enclosure', decimal(left['total'][0]+right['total'][0]) <= fd <= decimal(left['total'][1]+right['total'][1]))
            records.append(dict(name=name, curvature=display(value['total']), curvature_sign=sign_status(value['total']),
                                independent_decimal_second_difference=str(fd), exact_dx=str(result['dx']),
                                contributions={k: display(v) for k, v in value.items()}))
        try:
            curvature(crossing, (Q(0), Q(0), Q(0)), (Q(1), Q(1), Q(0)), (Q(1), Q(0), Q(0)), zero, arithmetic, square_root)
        except ValueError as error:
            check('moving_kink_endpoint_explicitly_ineligible', 'Kink endpoint' in str(error))
        else:
            check('moving_kink_endpoint_explicitly_ineligible', False)
    return checks, records


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--output', required=True)
    args = parser.parse_args(); out = (ROOT/args.output).resolve(); out.relative_to(ROOT)
    out.mkdir(parents=True); start = time.monotonic(); frozen = out/'source'; frozen.mkdir()
    base = ROOT/'data/development/native_interface_support/001'
    step = ROOT/'data/development/native_interface_step/001'
    native_base = base/'source/data/development/interface_directional/001/inputs'
    secants = ROOT/'data/development/interface_moment_set/001/native_tangent_curvature.csv'
    inputs = [Path(__file__).resolve(), ROOT/'diagnostics/check_native_interface_support.py',
              ROOT/'diagnostics/first_arrival_1d_precise_turn_reference.py', ROOT/'src/core.hpp', ROOT/'src/ray_metric.hpp',
              ROOT/'data/development/native_interface_conditioning/proposal.md', base/'summary.json', base/'support_vector.csv',
              step/'summary.json', step/'directions.csv', secants]+[native_base/n for n in ('truth_grid.csv', 'native_path.csv', 'native_case.csv')]
    hashes = {str(p.relative_to(ROOT)): sha(p) for p in inputs}
    def copied(p): return frozen/p.relative_to(ROOT)
    for path in inputs:
        target = copied(path); target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(str(path), str(target))
        require(sha(target) == hashes[str(path.relative_to(ROOT))], 'Changed frozen input')
    for path, digest in [('diagnostics/check_native_interface_support.py', SUPPORT_SHA),
                         ('diagnostics/first_arrival_1d_precise_turn_reference.py', SQRT_SHA),
                         ('src/core.hpp', CORE_SHA), ('src/ray_metric.hpp', METRIC_SHA)]:
        require(sha(frozen/path) == digest, 'Reviewed source changed: '+path)
    arithmetic = load_module('frozen_support', frozen/'diagnostics/check_native_interface_support.py')
    square_root = load_module('frozen_sqrt', frozen/'diagnostics/first_arrival_1d_precise_turn_reference.py').candidate_sqrt_enclosure
    checks, invented = controls(arithmetic, square_root)
    with (out/'invented_controls.json').open('x') as stream:
        json.dump(dict(checks=checks, cases=invented), stream, indent=2, allow_nan=False); stream.write('\n')
    original = json.loads(copied(base/'summary.json').read_text()); steps = json.loads(copied(step/'summary.json').read_text())
    require(sha(copied(base/'summary.json')) == '4ab53a668bda8332b16259af18dd667ac3fff88382c6d38bf0ef61c02c43dbd1', 'Original support summary changed')
    require(sha(copied(step/'summary.json')) == '167bfd760019f461bdfcf373ce699575739bcc0704874c3ffde94044eedc23eb', 'One-step summary changed')
    native_rows = read(copied(native_base/'native_case.csv')); require(len(native_rows) == 1, 'Nonunique native case'); native = native_rows[0]
    require(native == original['native_case'] == steps['native_case'], 'Native context mismatch')
    rows = read(copied(native_base/'native_path.csv')); saved = read(copied(base/'support_vector.csv'))
    directions = [r for r in read(copied(step/'directions.csv')) if r['direction'] == 'tangent_projection']
    require(len(rows) == len(saved) == len(directions) == original['path_nodes'], 'Incomplete saved direction')
    points = []; d = []
    for n, (row, support, direction) in enumerate(zip(rows, saved, directions)):
        require(int(row['node']) == int(direction['node']) == n and all(support[k] == v for k, v in row.items()), 'Native row/index mismatch')
        require(all(row[k] == direction[k] == native[k] for k in IDS), 'Native identity mismatch')
        point = tuple(Q(float(row[k])) for k in 'xyz')
        require(all(Q(float(direction[k])) == point[axis] for axis, k in enumerate('xyz')), 'Direction geometry mismatch')
        points.append(point); d.append(tuple(Q(direction['d'+k+'_rational']) for k in 'xyz'))
    require(all(value == 0 for endpoint in (d[0], d[-1]) for value in endpoint), 'Fixed endpoints moved')
    grid = read(copied(native_base/'truth_grid.csv'))
    axes = [sorted(set(Q(float(r[k])) for r in grid)) for k in 'xyz']
    profile = sorted(set((Q(float(r['x'])), Q(float(r['v']))) for r in grid))
    require(len(profile) == len(axes[0]) and all(v > 0 for x, v in profile), 'Model is not positive and x-only')
    require(len(grid) == len(axes[0])*len(axes[1])*len(axes[2]) and len(set(tuple(r[k] for k in 'xyz') for r in grid)) == len(grid), 'Incomplete model grid')
    require(all(axes[k][0] <= p[k] <= axes[k][-1] for p in points for k in range(3)), 'Native path outside domain')
    require(all(axes[k][0] < p[k] < axes[k][-1] for p in points[1:-1] for k in range(3)), 'Movable native knot not interior')
    for n, prefix in [(0, 'source_'), (-1, 'receiver_')]:
        require(all(points[n][k] == Q(float(native[prefix+axis])) for k, axis in enumerate('xyz')), 'Native endpoint changed')
    totals = {k: arithmetic.point(0) for k in FIELDS if k != 'length'}; failures = []; edge_rows = []
    groups = {}; length_intervals = []; max_terms = 0; max_tail = Q(0)
    for n, (a, b, da, db) in enumerate(zip(points, points[1:], d, d[1:])):
        row = dict({k: native[k] for k in IDS}, edge=n, node_a=n, node_b=n+1, exact_dx=str(b[0]-a[0]), original_local_flag=native['original_converged'])
        for prefix, vector in [('a', a), ('b', b), ('da', da), ('db', db)]:
            for axis, value in zip('xyz', vector): row[prefix+'_'+axis+'_rational'] = str(value)
        try:
            result = curvature(profile, a, b, da, db, arithmetic, square_root)
        except (ValueError, ArithmeticError) as error:
            row.update(status='inconclusive', reason=str(error)); failures.append(dict(row))
        else:
            kind = 'aligned_kink' if result['aligned_kink'] else 'transverse_crossing' if result['transverse_crossings'] else 'smooth_or_contact_leg'
            row.update(status='computed', reason='', edge_kind=kind, transverse_crossings=result['transverse_crossings'],
                       endpoint_kinks=result['endpoint_kinks'], total_sign=sign_status(result['values']['total']))
            if kind not in groups: groups[kind] = dict(edges=0, contributions={k: arithmetic.point(0) for k in totals})
            groups[kind]['edges'] += 1
            for key, value in result['values'].items():
                row[key+'_lower_rational'], row[key+'_upper_rational'] = map(str, value)
                row[key+'_lower_display'], row[key+'_upper_display'] = map(float, value)
                if key != 'length':
                    totals[key] = arithmetic.add(totals[key], value)
                    groups[kind]['contributions'][key] = arithmetic.add(groups[kind]['contributions'][key], value)
            length_intervals.append(result['values']['length']); max_terms = max(max_terms, result['max_log_terms']); max_tail = max(max_tail, result['max_log_tail'])
        edge_rows.append(row)
    fieldnames = list(dict.fromkeys(k for row in edge_rows for k in row))
    with (out/'native_edge_curvature.csv').open('x', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator='\n'); writer.writeheader(); writer.writerows(edge_rows)
    comparison = []
    for row in read(copied(secants)):
        require(all(row[k] == native[k] for k in IDS), 'Saved secant identity mismatch')
        lo, hi = [Q(row['secant_coefficient_'+side+'_rational']) for side in ('lower', 'upper')]
        record = dict(row); record['full_curvature_available'] = not failures
        if not failures:
            difference = arithmetic.sub((2*lo, 2*hi), totals['total'])
            record.update(two_secant_minus_curvature=display(difference))
        comparison.append(record)
    require(len(comparison) == 20, 'Saved tangent secant inventory changed')
    if not failures:
        expected_action = tuple(Q(v) for v in original['total_action_interval_rational'])
        tangent = next(r for r in steps['results'] if r['direction'] == 'tangent_projection')
        expected_slope = tuple(Q(tangent['actual_directional_derivative'][k]) for k in ('lower_rational', 'upper_rational'))
        for name, ok in [('native_action_matches_saved_enclosure', overlap(totals['action'], expected_action)),
                         ('native_first_variation_matches_saved_enclosure', overlap(totals['first_variation'], expected_slope)),
                         ('native_metric_decomposition', overlap(totals['mean_metric'], arithmetic.add(totals['geometric'], totals['mean_longitudinal'])))]:
            checks.append(dict(name=name, passed=bool(ok))); require(ok, name)
    with (out/'saved_secant_comparison.json').open('x') as stream:
        json.dump(comparison, stream, indent=2, allow_nan=False); stream.write('\n')
    for name, digest in hashes.items(): require(sha(ROOT/name) == sha(frozen/name) == digest, 'Pinned source/input changed')
    summary = dict(status='completed_scalar_curvature_diagnostic', full_curvature_available=not failures,
                   native_case=native, original_local_flag=native['original_converged'], checks=checks,
                   path_nodes=len(points), edge_count=len(edge_rows), inconclusive_edges=failures,
                   total_curvature_sign=sign_status(totals['total']) if not failures else 'incomplete',
                   contributions={k: display(v) for k, v in totals.items()}, contributions_complete=not failures,
                   groups={k: dict(edges=v['edges'], contributions={j: display(w) for j, w in v['contributions'].items()}) for k, v in groups.items()},
                   min_length_bounds=display((min(v[0] for v in length_intervals), min(v[1] for v in length_intervals))) if length_intervals else None,
                   max_length_bounds=display((max(v[0] for v in length_intervals), max(v[1] for v in length_intervals))) if length_intervals else None,
                   arithmetic=dict(sqrt_relative_bits=arithmetic.SQRT_BITS, log_absolute_tail_bits=arithmetic.LOG_BITS,
                                   component_outward_absolute_bits=arithmetic.COMPONENT_BITS, max_log_terms=max_terms, max_log_tail_rational=str(max_tail)),
                   input_source_sha256=hashes, elapsed_seconds=time.monotonic()-start,
                   limitations=['Only the frozen original polygon and saved tangent direction; no new solve, direction, step or optimizer.',
                                'A scalar second variation does not determine the Hessian spectrum or the production convergence rate.',
                                'Midpoint metric is the continuous exact-coordinate formula used by production; this is not a bitwise replay of its binary64 sampling.',
                                'Moved kink endpoints are ineligible; finite interval cancellation is preserved without a changed threshold.',
                                'Native flags and all source/model derivative choices remain unchanged.',
                                'Decimal finite differences are independent controls, not interval proofs; exact rational enclosures are authoritative.'])
    summary['artifact_sha256'] = {str(p.relative_to(out)): sha(p) for p in out.rglob('*') if p.is_file()}
    with (out/'summary.json').open('x') as stream:
        json.dump(summary, stream, indent=2, allow_nan=False); stream.write('\n')
    print(json.dumps(dict(status=summary['status'], checks=len(checks), inconclusive_edges=len(failures),
                          contributions={k: [float(x) for x in v] for k, v in totals.items()})), flush=True)


if __name__ == '__main__':
    main()
