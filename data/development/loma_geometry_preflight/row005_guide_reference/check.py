#!/usr/bin/env python3
"""Evaluate one bounded, declared Snell guide candidate; no ray trace or inversion."""
import argparse
import csv
from fractions import Fraction as Q
import hashlib
import io
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'diagnostics'))
from first_arrival_1d_reference import leg, velocity


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def table(path):
    content = path.read_bytes()
    reader = csv.DictReader(io.StringIO(content.decode('utf-8')))
    return reader.fieldnames, list(reader), hashlib.sha256(content).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', default='data/loma_lom_001')
    parser.add_argument('--output', default='data/development/loma_geometry_preflight/row005_guide_reference')
    args = parser.parse_args()
    data, output = (ROOT / args.data).resolve(), (ROOT / args.output).resolve()
    data.relative_to(ROOT)
    output.relative_to(ROOT)
    if (output / 'result.json').exists():
        parser.error('Choose a fresh output directory; preserve existing evidence')
    hashes = {}
    def read(name):
        names, rows, digest = table(data / name)
        hashes[str((data / name).relative_to(ROOT))] = digest
        return names, rows
    _, grid = read('truth_grid.csv')
    _, events = read('truth_events.csv')
    _, receivers = read('stations.csv')
    sample_names, samples = read('ray_samples.csv')
    saved_names, saved = read('geometry_truth_ray_convergence.csv')
    sample = samples[5]
    source, receiver = events[473], receivers[2]
    if sample['event'] != '473' or sample['station'] != '2':
        raise ValueError('Sample row 5 mapping changed')
    if source['event_resource_id'] != 'quakeml:NC.anss.org/Event/NC/20091683' or receiver['channel_seed_id'] != 'NC.BSL..EHZ':
        raise ValueError('Native event/channel identity changed')
    for prefix, record in [('source_', source), ('receiver_', receiver)]:
        if any(sample.get(prefix + key) != value for key, value in record.items()):
            raise ValueError('Sample metadata differs from native table')
    selected = [r for r in saved if r['diagnostic_row'] == '5']
    if len(selected) != 1 or selected[0]['event'] != '473' or selected[0]['station'] != '2':
        raise ValueError('Saved diagnostic mapping changed')
    selected = selected[0]
    levels = sorted({(float(r['x']), float(r['v'])) for r in grid})
    if len(levels) != len({x for x, v in levels}):
        raise ValueError('Model is not x-only')
    profile = [(Q(x), Q(v)) for x, v in levels]
    bounds = {axis: [min(float(r[axis]) for r in grid), max(float(r[axis]) for r in grid)] for axis in 'xyz'}
    a, b = ([float(record[k]) for k in 'xyz'] for record in (source, receiver))
    if not all(bounds[k][0] <= point[i] <= bounds[k][1] for point in (a, b) for i, k in enumerate('xyz')):
        raise ValueError('Endpoint outside original box')
    if not bounds['x'][0] <= 0 < min(a[0], b[0]) or velocity(profile, Q(0)) != 6:
        raise ValueError('The declared x=0, v=6 guide is absent')
    if any(v != 6 for x, v in levels if x <= 0) or any(v > 6 for x, v in levels):
        raise ValueError('Declared plateau/model maximum changed')

    def candidate(start):
        distance = math.hypot(b[1] - start[1], b[2] - start[2])
        # The leg formulas integrate either sign of linear dv/dx. The full
        # branch enumerator is deliberately not called on this nonmonotone v.
        legs = [leg(profile, Q(0), Q(point[0]), Q(6)) for point in (start, b)]
        guide = distance - sum(x for x, t in legs)
        if guide < 0:
            raise ValueError('Candidate would require a negative guide length')
        return sum(t for x, t in legs) + guide / 6, distance, guide, legs

    time, distance, guide, legs = candidate(a)
    vs = float(velocity(profile, Q(a[0])))
    gradient = [math.sqrt(1 / vs**2 - 1 / 36),
                (a[1] - b[1]) / (6 * distance),
                (a[2] - b[2]) / (6 * distance)]
    differences = []
    for axis in range(3):
        for step in (1e-4, 1e-5, 1e-6):
            plus, minus = list(a), list(a)
            plus[axis] += step
            minus[axis] -= step
            numerical = (candidate(plus)[0] - candidate(minus)[0]) / (2 * step)
            differences.append(dict(axis='xyz'[axis], step_km=step,
                                    analytic_s_per_km=gradient[axis],
                                    numerical_s_per_km=numerical,
                                    signed_error_s_per_km=numerical-gradient[axis]))
    module = ROOT / 'diagnostics/first_arrival_1d_reference.py'
    hashes[str(module.relative_to(ROOT))] = sha(module)
    hashes[str(Path(__file__).resolve().relative_to(ROOT))] = sha(Path(__file__).resolve())
    frozen = ROOT / 'data/development/loma_geometry_preflight/001/source/src'
    hashes.update({str(p.relative_to(ROOT)): sha(p) for p in sorted(frozen.glob('*')) if p.is_file()})
    output.mkdir(parents=True, exist_ok=True)
    for name, names, row in [('identified_ray.csv', sample_names, sample), ('saved_ray_result.csv', saved_names, selected)]:
        with (output / name).open('x', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=names, lineterminator='\n')
            writer.writeheader()
            writer.writerow(row)
    result = dict(scope='Declared bounded x=0 plateau-grazing candidate for identified Loma sample row 5; not a complete first-arrival reference',
                  command='PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python3 ' + str(Path(__file__).resolve().relative_to(ROOT)) + ' --data ' + str(data.relative_to(ROOT)) + ' --output ' + str(output.relative_to(ROOT)),
                  diagnostic_row=5, event=473, station=2,
                  event_resource_id=source['event_resource_id'], origin_resource_id=source['origin_resource_id'],
                  channel_seed_id=receiver['channel_seed_id'], channel_fdsn_source_id=receiver['channel_fdsn_source_id'],
                  metadata_epoch_start=receiver['metadata_epoch_start'], metadata_epoch_end=receiver['metadata_epoch_end'],
                  source_xyz_km=a, receiver_xyz_km=b, original_domain_km=bounds,
                  profile_x_velocity_km_km_s=levels, candidate_time_s=time,
                  transverse_distance_km=distance, guide_length_km=guide,
                  legs_transverse_distance_km_and_time_s=legs,
                  candidate_x_range_km=[0, max(a[0], b[0])],
                  domain_reason='Each Snell leg stays between x=0 and its endpoint; the guide stays at x=0. Positive transverse slowness makes (y,z) advance monotonically along the endpoint line, inside the original convex rectangle.',
                  source_derivative_s_per_km=gradient,
                  source_eikonal_residual_s2_per_km2=sum(q*q for q in gradient)-1/vs**2,
                  source_derivative_finite_differences=differences,
                  saved_production_minus_candidate_s=float(selected['production_time'])-time,
                  saved_refined_minus_candidate_s=float(selected['refined_time'])-time,
                  interface_slowness_dx_left_s_per_km2=0,
                  interface_slowness_dx_right_s_per_km2=1/18,
                  input_sha256=hashes,
                  output_sha256={name: sha(output/name) for name in ('identified_ray.csv','saved_ray_result.csv')},
                  limitations=['The full monotone-profile enumerator rejects this sandwich. Only this explicitly constructed candidate is evaluated; no global branch-completeness or first-arrival claim is made.',
                               'No model continuation outside the saved finite box, new data selection, ray trace or inversion is used.',
                               'Source derivatives belong to this candidate. They do not certify derivatives of a nonconverged saved path or of a tied first-arrival minimum.',
                               'The active preflight may append further rows to its convergence table. saved_ray_result.csv preserves the complete selected row and its original-table hash at capture; it does not assert completion of that run.',
                               'A sustained interface path has unequal one-sided normal derivatives. This possible stopping mechanism requires inspection of the actual optimizer paths before attribution.'])
    (output / 'result.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps({key:result[key] for key in ['candidate_time_s','guide_length_km','source_derivative_s_per_km','saved_production_minus_candidate_s','saved_refined_minus_candidate_s']},indent=2))


if __name__ == '__main__':
    main()
