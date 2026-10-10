#!/usr/bin/env python3
"""Compare further saved path refinements with the existing identified reference."""
import csv
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
INPUT = HERE / 'fine_inputs'
manifest = json.loads((INPUT / 'provenance.json').read_text())
for name, expected in manifest['sha256'].items():
    if hashlib.sha256((INPUT / name).read_bytes()).hexdigest() != expected:
        raise ValueError('Changed frozen fine-path input: ' + name)
if (INPUT / 'identified_ray.csv').read_bytes() != (HERE / 'inputs/identified_ray.csv').read_bytes():
    raise ValueError('Different native identities or geometry')
reference = json.loads((HERE / 'result.json').read_text())
first = reference['reference']['first_arrival']
summary = json.loads((INPUT / 'summary.json').read_text())
rows = []
for name in ('spacing0_125000_results.csv', 'spacing0_062500_results.csv'):
    with (INPUT / name).open() as stream:
        for row in csv.DictReader(stream):
            match = [r for r in summary['results'] if r['run_id'] == row['run_id']]
            if len(match) != 1 or any(match[0][k] != v for k, v in row.items()):
                raise ValueError('Fine result differs from captured summary')
            if row['observation_index'] != '9291' or row['logged_matches_unobserved_variant'] != '1':
                raise ValueError('Wrong support or failed optimizer observation parity')
            row['field_spacing_km'] = match[0]['field_spacing_km']
            row['time_minus_reference_s'] = float(row['time_s']) - first['time_s']
            row['source_derivative_max_error_s_per_km'] = max(abs(float(row['source_d' + k]) -
                first['source_derivative_s_per_km'][d]) for d, k in enumerate('xyz'))
            row['existing_analytic_time_control_pass'] = abs(row['time_minus_reference_s']) <= 2.5e-5
            row['existing_analytic_source_control_pass'] = row['source_derivative_max_error_s_per_km'] <= 3e-6
            row['full_metadata_mapping'] = 'inputs/identified_ray.csv: observation_index = observation_row'
            for key in ('event_i_resource_id', 'origin_i_resource_id', 'pick_i_resource_id',
                        'arrival_i_resource_id', 'channel_seed_id', 'channel_fdsn_source_id',
                        'metadata_epoch_start', 'metadata_epoch_end'):
                row[key] = reference['full_native_metadata'][key]
            rows.append(row)
if len(rows) != 4:
    raise ValueError('Expected four saved path-refinement controls')
with (HERE / 'fine_path_comparison.csv').open('w', newline='') as stream:
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
    writer.writeheader(); writer.writerows(rows)
report = dict(scope='Saved path-only refinements at fixed 0.5 km FMM field spacing; no ray rerun',
    command='PYTHONDONTWRITEBYTECODE=1 python3 data/development/initial_ray_first_arrival_003_9291_reference001/check_fine_paths.py',
    reference_time_s=first['time_s'], existing_control_tolerances=dict(time_s=2.5e-5, source_component_s_per_km=3e-6),
    comparisons=rows, input_sha256=manifest['sha256'],
    reference_result_sha256=hashlib.sha256((HERE / 'result.json').read_bytes()).hexdigest(),
    helper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    limitations=['One identified initial 1D ray only.', 'Local flags remain unchanged.',
                 'Passing these component tolerances is not a full-cohort or three-dimensional accuracy certificate.'])
(HERE / 'fine_path_review.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
print(json.dumps([{k: r[k] for k in ('run_id', 'time_minus_reference_s',
    'source_derivative_max_error_s_per_km', 'existing_analytic_time_control_pass',
    'existing_analytic_source_control_pass')} for r in rows], indent=2))
