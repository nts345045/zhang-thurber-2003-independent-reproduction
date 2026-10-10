#!/usr/bin/env python3
"""Compare captured Loma diagnostics with one explicit bounded x=0 guide family."""
import argparse
from collections import Counter
import csv
import datetime
from fractions import Fraction as Q
import hashlib
import io
import json
import math
from pathlib import Path
import shutil
import sys

from first_arrival_1d_reference import Interval, compare_limit, distance_limit, leg, velocity

ROOT = Path(__file__).resolve().parents[1]


def sha(content):
    return hashlib.sha256(content).hexdigest()


def table(content):
    reader = csv.DictReader(io.StringIO(content.decode('utf-8')), strict=True)
    rows = list(reader)
    if any(set(row) != set(reader.fieldnames) or None in row.values() for row in rows):
        raise ValueError('Incomplete or extra CSV fields')
    return reader.fieldnames, rows


def captured_prefix(path):
    """Retain only complete CSV records, never a partly flushed final record."""
    raw = path.read_bytes()
    stream = io.StringIO(raw.decode('utf-8'))
    reader = csv.reader(stream, strict=True)
    names = next(reader)
    end, rows = stream.tell(), []
    while True:
        try:
            values = next(reader)
        except (StopIteration, csv.Error):
            break
        position = stream.tell()
        if len(values) != len(names) or not stream.getvalue()[:position].endswith('\n'):
            break
        rows.append(dict(zip(names, values)))
        end = position
    prefix = stream.getvalue()[:end].encode('utf-8')
    return names, rows, prefix, dict(path=str(path.relative_to(ROOT)), bytes_at_capture=len(raw),
                                   captured_bytes=len(prefix), complete_records=len(rows),
                                   captured_prefix_sha256=sha(prefix), raw_at_capture_sha256=sha(raw))


def guide(profile, a, b, bounds):
    """A declared feasible family only. No global branch enumeration is attempted."""
    result = dict(candidate_status='inapplicable', candidate_reason='')
    if not all(bounds[axis][0] <= p[i] <= bounds[axis][1]
               for p in (a, b) for i, axis in enumerate('xyz')):
        result['candidate_reason'] = 'endpoint_outside_original_box'
        return result
    if min(a[0], b[0]) < 0:
        result['candidate_reason'] = 'negative_x_endpoint_has_no_finite_critical_leg_through_v6_plateau'
        return result
    distance = math.hypot(b[1]-a[1], b[2]-a[2])
    legs = [leg(profile, Q(0), Q(p[0]), Q(6)) for p in (a, b)]
    result['transverse_distance_km'] = distance
    if not all(math.isfinite(value) for pair in legs for value in pair):
        result['candidate_reason'] = 'positive_length_v6_interval_gives_infinite_critical_leg'
        return result
    limit = sum((distance_limit(profile, Q(0), Q(p[0]), Q(6)) for p in (a, b)), Q(0))
    sign = compare_limit(Q(distance), limit)
    result.update(source_leg_transverse_km=legs[0][0], receiver_leg_transverse_km=legs[1][0],
                  source_leg_time_s=legs[0][1], receiver_leg_time_s=legs[1][1],
                  required_transverse_lower_km=limit.lo if isinstance(limit, Interval) else float(limit),
                  required_transverse_upper_km=limit.hi if isinstance(limit, Interval) else float(limit))
    if sign is None:
        result.update(candidate_status='unresolved', candidate_reason='guide_length_sign_not_resolved_by_outward_interval')
        return result
    if sign < 0:
        result['candidate_reason'] = 'transverse_distance_shorter_than_two_critical_legs'
        return result
    length = 0. if sign == 0 else distance-sum(pair[0] for pair in legs)
    if length < 0 or (sign > 0 and length == 0):
        result.update(candidate_status='unresolved', candidate_reason='ordinary_float_guide_length_disagrees_with_proved_sign')
        return result
    result.update(candidate_status='applicable', candidate_reason='explicit_bounded_critical_legs_and_nonnegative_guide',
                  guide_length_km=length, candidate_time_s=sum(pair[1] for pair in legs)+length/6,
                  source_derivative_status='branch_derivative' if a[0] > 0 else 'right_x_branch_derivative_at_interface')
    if distance == 0:
        result['source_derivative_status'] = 'undefined_for_coincident_endpoints'
    else:
        v = float(velocity(profile, Q(a[0])))
        result.update(candidate_source_dx_s_per_km=math.sqrt(1/v**2-1/36),
                      candidate_source_dy_s_per_km=(a[1]-b[1])/(6*distance),
                      candidate_source_dz_s_per_km=(a[2]-b[2])/(6*distance))
    return result


def checks(profile, bounds):
    records = []
    def check(name, passed):
        records.append(dict(name=name, passed=bool(passed)))
        if not passed:
            raise AssertionError(name)
    same = guide(profile, [0., 0., 0.], [0., 2., 0.], bounds)
    check('pure_interface_guide', same['candidate_status'] == 'applicable' and same['candidate_time_s'] == 1/3)
    zero = guide(profile, [0., 0., 0.], [0., 0., 0.], bounds)
    check('coincident_endpoints_derivative_undefined', zero['candidate_time_s'] == 0 and zero['source_derivative_status'] == 'undefined_for_coincident_endpoints')
    check('negative_x_not_removed_or_substituted', guide(profile, [-1., 0., 0.], [1., 20., 0.], bounds)['candidate_status'] == 'inapplicable')
    check('short_offset_candidate_inapplicable', guide(profile, [1., 0., 0.], [1., 0., 0.], bounds)['candidate_status'] == 'inapplicable')
    flat = [(Q(-2), Q(6)), (Q(2), Q(6))]
    check('flat_critical_leg_infinite', guide(flat, [1., 0., 0.], [1., 2., 0.], bounds)['candidate_reason'] == 'positive_length_v6_interval_gives_infinite_critical_leg')
    check('unresolved_distance_sign_is_retained', compare_limit(Q(1), Interval(0.999, 1.001)) is None)
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', default='data/loma_lom_001')
    parser.add_argument('--run-manifest', default='data/development/loma_geometry_preflight/001/summary.json')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    paths = [(ROOT / value).resolve() for value in (args.data, args.run_manifest, args.output)]
    for path in paths:
        path.relative_to(ROOT)
    data, manifest_path, output = paths
    if output.exists():
        parser.error('Choose a fresh output directory; captured comparisons are immutable')
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes.decode('utf-8'))
    for name, expected in manifest['source_sha256'].items():
        if sha((manifest_path.parent/'source'/name).read_bytes()) != expected:
            raise ValueError('Frozen solver source changed: '+name)
    inputs, names, rows = {}, {}, {}
    for name in ['truth_grid.csv', 'truth_events.csv', 'stations.csv', 'ray_samples.csv']:
        inputs[name] = (data/name).read_bytes()
        if sha(inputs[name]) != manifest['input_sha256'][name]:
            raise ValueError('Frozen input changed: '+name)
        names[name], rows[name] = table(inputs[name])
    grid, events, receivers, samples = [rows[name] for name in
                                      ['truth_grid.csv', 'truth_events.csv', 'stations.csv', 'ray_samples.csv']]
    if [len(events), len(receivers), len(samples)] != [724, 52, 104]:
        raise ValueError('Frozen cohort or diagnostic sample changed')
    if any([int(r['id']) for r in values] != list(range(len(values))) for values in (events, receivers)):
        raise ValueError('Native numerical indices are not contiguous')
    levels = sorted({(float(r['x']), float(r['v'])) for r in grid})
    if len(levels) != len({x for x, v in levels}) or not all(math.isfinite(x) and math.isfinite(v) and 0 < v <= 6 for x, v in levels):
        raise ValueError('Require the saved finite positive x-only profile with maximum speed 6 km/s')
    profile = [(Q(x), Q(v)) for x, v in levels]
    if velocity(profile, Q(0)) != 6 or any(v != 6 for x, v in levels if x <= 0):
        raise ValueError('The declared x<=0, v=6 plateau changed')
    bounds = {axis: [min(float(r[axis]) for r in grid), max(float(r[axis]) for r in grid)] for axis in 'xyz'}
    controls = checks(profile, bounds)
    candidates, fd = [], []
    for n, sample in enumerate(samples):
        i, k = int(sample['event']), int(sample['station'])
        if not (0 <= i < len(events) and 0 <= k < len(receivers)):
            raise ValueError('Sample index outside native tables')
        for prefix, native in [('source_', events[i]), ('receiver_', receivers[k])]:
            if any(sample[prefix+key] != value for key, value in native.items()):
                raise ValueError('Sample metadata differs from native input')
        a, b = [[float(native[axis]) for axis in 'xyz'] for native in (events[i], receivers[k])]
        result = guide(profile, a, b, bounds)
        candidates.append(dict(sample, diagnostic_row=n, **result))
        if result['candidate_status'] == 'applicable' and a[0] > 0 and result['guide_length_km'] > 0:
            reverse = guide(profile, b, a, bounds)
            if abs(reverse['candidate_time_s']-result['candidate_time_s']) > 1e-13:
                raise AssertionError('Guide reciprocity')
            for axis in range(3):
                h = 1e-5
                plus, minus = list(a), list(a)
                plus[axis] += h
                minus[axis] -= h
                pp, mm = guide(profile, plus, b, bounds), guide(profile, minus, b, bounds)
                if pp['candidate_status'] == mm['candidate_status'] == 'applicable':
                    numerical = (pp['candidate_time_s']-mm['candidate_time_s'])/(2*h)
                    analytic = result['candidate_source_d'+'xyz'[axis]+'_s_per_km']
                    fd.append(dict(diagnostic_row=n,
                                   event_resource_id=sample['source_event_resource_id'],
                                   origin_resource_id=sample['source_origin_resource_id'],
                                   channel_seed_id=sample['receiver_channel_seed_id'],
                                   channel_fdsn_source_id=sample['receiver_channel_fdsn_source_id'],
                                   metadata_epoch_start=sample['receiver_metadata_epoch_start'],
                                   metadata_epoch_end=sample['receiver_metadata_epoch_end'],
                                   source_data_sha256=sample['source_source_sha256'],
                                   receiver_data_sha256=sample['receiver_source_sha256'],
                                   axis='xyz'[axis], step_km=h,
                                   analytic_s_per_km=analytic, central_s_per_km=numerical,
                                   signed_error_s_per_km=numerical-analytic))
    if max((abs(r['signed_error_s_per_km']) for r in fd), default=0.) > 1e-8:
        raise AssertionError('Candidate source derivative differs from central differences by more than 1e-8 s/km')
    captures = [captured_prefix(data/('geometry_truth_ray_'+name+'.csv')) for name in ('convergence', 'identifiers')]
    convergence, identities = captures[0][1], captures[1][1]
    for values in (convergence, identities):
        if [int(r['diagnostic_row']) for r in values] != list(range(len(values))):
            raise ValueError('Captured diagnostic rows are not a complete ordered prefix')
    count = min(len(convergence), len(identities))
    comparisons = []
    for n in range(count):
        candidate, observed, identity = candidates[n], convergence[n], identities[n]
        for record in (observed, identity):
            if (record['event'], record['station']) != (candidate['event'], candidate['station']):
                raise ValueError('Diagnostic native index join changed')
        for key, value in identity.items():
            if key in ['diagnostic_row', 'event', 'station']:
                continue
            expected = candidate[key]
            if key in [prefix+axis for prefix in ['source_', 'receiver_'] for axis in 'xyz']:
                if float(value) != float(format(float(expected), '.12g')):
                    raise ValueError('Printed diagnostic coordinate differs from native input')
            elif value != expected:
                raise ValueError('Diagnostic metadata differs from native input: '+key)
        joined = dict(candidate)
        joined.update(observed)
        if candidate['candidate_status'] == 'applicable':
            for prefix in ('production', 'refined'):
                time = float(observed[prefix+'_time'])
                if not math.isfinite(time):
                    raise ValueError('Captured solver time is nonfinite')
                joined[prefix+'_minus_candidate_s'] = time-candidate['candidate_time_s']
        comparisons.append(joined)
    output.mkdir(parents=True)
    (output/'inputs').mkdir()
    for name, content in inputs.items():
        (output/'inputs'/name).write_bytes(content)
    (output/'run_manifest_at_capture.json').write_bytes(manifest_bytes)
    for label, capture in zip(('convergence', 'identifiers'), captures):
        (output/('captured_'+label+'.csv')).write_bytes(capture[2])
    def write(name, values):
        fields = list(dict.fromkeys(key for row in values for key in row))
        with (output/name).open('x', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n')
            writer.writeheader()
            writer.writerows(values)
    write('identified_candidates.csv', candidates)
    write('identified_comparison.csv', comparisons)
    write('source_derivative_checks.csv', fd)
    (output/'source').mkdir()
    sources = [Path(__file__).resolve(), ROOT/'diagnostics/first_arrival_1d_reference.py']
    for path in sources:
        shutil.copyfile(str(path), str(output/'source'/path.name))
    applicable = [r for r in comparisons if r['candidate_status'] == 'applicable']
    counts = {key: dict(Counter(r[key] for r in candidates)) for key in ('candidate_status', 'candidate_reason')}
    summary = dict(scope='One explicit bounded x=0 guide candidate for each of 104 declared rays; no global first-arrival claim or generation gate override',
                   captured_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), command=['python3']+sys.argv,
                   status='complete_comparison' if count == 104 else 'partial_comparison',
                   expected_diagnostic_rays=104, captured_compared_rays=count, compared_diagnostic_rows=list(range(count)),
                   candidate_counts=counts, compared_applicable_candidates=len(applicable),
                   input_geometry_unchanged=True, native_metadata_verified=True, no_rays_excluded=True,
                   original_domain_km=bounds, profile_x_velocity_km_km_s=levels, controls=controls,
                   distance_sign_basis='Exact binary64-derived rational input R=math.hypot(dy,dz), exact rational or outward interval leg distances; unresolved signs retained',
                   finite_domain_reason='Each leg remains between x=0 and its endpoint. Its transverse coordinates advance along the endpoint line; the guide follows that line at x=0. Nonnegative guide length keeps the path in the original convex box.',
                   arithmetic_scope='Candidate times and derivatives are ordinary floating-point evaluations, not interval bounds on minimum-time ordering',
                   maximum_source_derivative_fd_error_s_per_km=max((abs(r['signed_error_s_per_km']) for r in fd), default=None),
                   derivative_check_rows=len(fd), captures=[r[3] for r in captures],
                   run_source_commit=manifest['commit'], run_binary_sha256=manifest['binary_sha256'],
                   frozen_run_source_sha256=manifest['source_sha256'],
                   source_sha256={str(path.relative_to(ROOT)): sha(path.read_bytes()) for path in sources},
                   input_sha256={str((data/name).relative_to(ROOT)): sha(content) for name, content in inputs.items()},
                   limitations=['Candidate inapplicability does not make a diagnostic ray inadmissible or remove it from any cohort.',
                                'No exact-interface stopping diagnosis is assigned to these saved paths without inspecting their geometry.',
                                'Source derivatives refer only to this candidate family, not necessarily the optimized first arrival; ties require branch interpretation.',
                                'Production diagnostic times are saved with 12 significant digits. Comparisons inherit that rounding.',
                                'Local convergence and initializer flags remain unchanged. No observations or inversion are generated.'])
    summary['comparison'] = {}
    for prefix in ('production', 'refined'):
        values = [r[prefix+'_minus_candidate_s'] for r in applicable]
        summary['comparison'][prefix] = dict(minimum_minus_candidate_s=min(values) if values else None,
            maximum_minus_candidate_s=max(values) if values else None,
            positive_gap_rows=[int(r['diagnostic_row']) for r in applicable if r[prefix+'_minus_candidate_s'] > 0],
            positive_gap_local_converged_rows=[int(r['diagnostic_row']) for r in applicable if r[prefix+'_minus_candidate_s'] > 0 and r[prefix+'_converged'] == '1'])
    summary['output_sha256'] = {str(p.relative_to(output)): sha(p.read_bytes()) for p in sorted(output.rglob('*')) if p.is_file()}
    (output/'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False)+'\n')
    print(json.dumps({key:summary[key] for key in ['status', 'captured_compared_rays', 'candidate_counts', 'compared_applicable_candidates', 'comparison', 'maximum_source_derivative_fd_error_s_per_km']}, indent=2))


if __name__ == '__main__':
    main()
