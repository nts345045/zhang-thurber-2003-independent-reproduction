#!/usr/bin/env python3
"""Compare one saved identified ray with the frozen continuous 1D reference."""
import csv
import hashlib
import importlib.util
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def table(name):
    with (HERE / name).open() as stream:
        reader = csv.DictReader(stream)
        names, rows = reader.fieldnames, list(reader)
    if not names or len(names) != len(set(names)) or any(None in r for r in rows):
        raise ValueError('Invalid CSV: ' + name)
    return names, rows


def main():
    provenance = json.loads((HERE / 'provenance.json').read_text())
    for name, expected in provenance['frozen_sha256'].items():
        if sha(HERE / name) != expected:
            raise ValueError('Frozen input/source changed: ' + name)
    spec = importlib.util.spec_from_file_location('reference', str(HERE / 'source/first_arrival_1d_reference.py'))
    reference_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reference_module)
    _, native = table('inputs/identified_ray.csv')
    if len(native) != 1:
        raise ValueError('Expected one fully identified native ray')
    native = native[0]
    if native['row'] != '9291' or native['observation_row'] != '9291':
        raise ValueError('Unexpected selected row')
    source = [float(native['source_' + k + '_km']) for k in 'xyz']
    receiver = [float(native['receiver_' + k + '_km']) for k in 'xyz']
    _, grid = table('inputs/initial_grid.csv')
    profile = sorted(set((float(r['z']), float(r['v'])) for r in grid))
    if len(profile) != len(set(z for z, _ in profile)):
        raise ValueError('Expected horizontally uniform saved model')
    bounds = {k: [min(float(r[k]) for r in grid), max(float(r[k]) for r in grid)] for k in 'xyz'}
    if any(not bounds[k][0] <= p[d] <= bounds[k][1] for p in (source, receiver) for d, k in enumerate('xyz')):
        raise ValueError('Endpoint outside the finite model box')
    depths, speeds = map(list, zip(*profile))
    reference = reference_module.enumerate_arrivals(depths, speeds, source, receiver)
    if not reference['complete'] or not reference['reference_valid'] or reference['first_arrival'] is None:
        raise ValueError('Reference enumeration did not complete')
    first = reference['first_arrival']
    compared = []
    for name in ('inputs/spacing050_results.csv', 'inputs/spacing025_results.csv'):
        _, rows = table(name)
        for row in rows:
            if row['observation_index'] != native['observation_row'] or row['logged_matches_unobserved_variant'] != '1':
                raise ValueError('Changed support or failed observation parity')
            item = dict(row)
            item.update(event_resource_id=native['event_i_resource_id'],
                        origin_resource_id=native['origin_i_resource_id'],
                        pick_resource_id=native['pick_i_resource_id'],
                        arrival_resource_id=native['arrival_i_resource_id'],
                        channel_seed_id=native['channel_seed_id'],
                        channel_fdsn_source_id=native['channel_fdsn_source_id'],
                        metadata_epoch_start=native['metadata_epoch_start'],
                        metadata_epoch_end=native['metadata_epoch_end'],
                        full_metadata_mapping='inputs/identified_ray.csv: observation_index = observation_row',
                        reference_time_s=first['time_s'],
                        time_minus_reference_s=float(row['time_s']) - first['time_s'])
            errors = []
            for d, key in enumerate('xyz'):
                exact = first['source_derivative_s_per_km'][d]
                item['reference_source_d' + key] = exact
                item['source_d' + key + '_minus_reference'] = float(row['source_d' + key]) - exact
                errors.append(item['source_d' + key + '_minus_reference'])
            item['source_derivative_max_absolute_error_s_per_km'] = max(map(abs, errors))
            item['source_derivative_error_norm_s_per_km'] = math.sqrt(sum(e * e for e in errors))
            if not all(math.isfinite(float(item[k])) for k in ('time_minus_reference_s', 'source_derivative_max_absolute_error_s_per_km')):
                raise ValueError('Nonfinite comparison')
            compared.append(item)
    if len(compared) != 8 or len(set(r['run_id'] for r in compared)) != 8:
        raise ValueError('Expected all eight saved controls')
    with (HERE / 'comparison.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(compared[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(compared)
    result = dict(scope='Continuous finite-depth 1D reference versus eight saved paths; no ray optimization or inversion',
                  identified_observation_row=9291, source_km=source, receiver_km=receiver,
                  full_native_metadata=native, profile_depth_velocity_km_km_s=profile,
                  original_box_km=bounds, reference=reference,
                  frozen_sha256=provenance['frozen_sha256'],
                  helper_sha256=sha(Path(__file__).resolve()),
                  comparison_sha256=sha(HERE / 'comparison.csv'),
                  checks=dict(all_saved_controls_preserved=len(compared) == 8,
                              all_observation_hooks_match=True, finite_comparisons=True,
                              complete_reference=reference['complete'],
                              reference_valid=reference['reference_valid']),
                  limitations=['Time ordering uses floating point; branch enumeration and distance closure have the reference module certificates.',
                               'This monotone initial 1D model result is not a claim about updated three-dimensional models.',
                               'Existing local convergence flags are retained; no new field threshold is imposed.',
                               'Source derivatives refer to the selected exact branch; near ties remain explicit.'])
    (HERE / 'result.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps(dict(reference=first, comparisons=[{k: row[k] for k in
        ('run_id', 'converged', 'time_minus_reference_s', 'source_derivative_max_absolute_error_s_per_km')} for row in compared]), indent=2))


if __name__ == '__main__':
    main()
