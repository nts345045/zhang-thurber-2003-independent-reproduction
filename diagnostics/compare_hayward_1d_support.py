#!/usr/bin/env python3
"""Compare frozen initial absolute rays with the existing continuous 1D reference.

No solver, inversion, provider request, or input edit occurs. The completed
preflight hashes establish that all linearization tables are ready to read.
"""
import argparse
import collections
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import statistics
import sys
import time

import numpy
import scipy
from first_arrival_1d_reference import enumerate_arrivals

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def table(path):
    with path.open() as stream:
        reader = csv.DictReader(stream)
        names, rows = reader.fieldnames, list(reader)
    if not names or len(names) != len(set(names)) or any(None in row for row in rows):
        raise ValueError('Invalid CSV header/row: ' + str(path.relative_to(ROOT)))
    return names, rows


def stats(values):
    if not values:
        return None
    return dict(count=len(values), minimum=min(values), maximum=max(values),
                median=statistics.median(values), mean=sum(values) / len(values),
                rms=math.sqrt(sum(v * v for v in values) / len(values)),
                maximum_absolute=max(abs(v) for v in values))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', required=True, help='Repository-relative frozen run directory')
    parser.add_argument('--output', required=True, help='Fresh repository-relative evidence directory')
    args = parser.parse_args()
    data, out = (ROOT / args.data).resolve(), (ROOT / args.output).resolve()
    for path in (data, out):
        path.relative_to(ROOT)
    if out.exists():
        parser.error('Choose a fresh output directory; preserve prior evidence')
    names = ['initial_events.csv', 'stations.csv', 'initial_grid.csv', 'observations.csv',
             'initial_linearization_rows.csv', 'initial_linearization_columns.csv',
             'initial_linearization_matrix.csv', 'run_manifest.json', 'preflight.json']
    files = [data / name for name in names]
    module = ROOT / 'diagnostics/first_arrival_1d_reference.py'
    sources = [Path(__file__).resolve(), module]
    hashes = {str(p.relative_to(ROOT)): sha(p) for p in files + sources}
    manifest = json.loads((data / 'run_manifest.json').read_text())
    preflight = json.loads((data / 'preflight.json').read_text())
    for name in ['initial_events.csv', 'stations.csv', 'initial_grid.csv', 'observations.csv']:
        path = str((data / name).relative_to(ROOT))
        if hashes[path] != manifest['sha256'][path]:
            raise ValueError('Geometry/observations differ from the frozen run: ' + name)
    for name in names:
        if name.startswith('initial_') and name.endswith('.csv'):
            if hashes[str((data / name).relative_to(ROOT))] != preflight['sha256'][name]:
                raise ValueError('Linearization/geometry differs from completed preflight: ' + name)
    _, event_rows = table(data / 'initial_events.csv')
    _, station_rows = table(data / 'stations.csv')
    _, grid = table(data / 'initial_grid.csv')
    observation_names, observations = table(data / 'observations.csv')
    row_names, rays = table(data / 'initial_linearization_rows.csv')
    _, columns = table(data / 'initial_linearization_columns.csv')
    events = {r['id']: r for r in event_rows}
    stations = {r['id']: r for r in station_rows}
    if len(events) != len(event_rows) or set(events) != set(map(str, range(len(events)))):
        raise ValueError('Event IDs must be unique contiguous solver indices')
    if len(stations) != len(station_rows) or set(stations) != set(map(str, range(len(stations)))):
        raise ValueError('Station IDs must be unique contiguous native indices')
    levels = sorted(set((float(r['z']), float(r['v'])) for r in grid))
    if len(levels) != len(set(z for z, _ in levels)):
        raise ValueError('The reference is only valid for a horizontally uniform initial grid')
    depths, speeds = map(list, zip(*levels))
    if not all(math.isfinite(q) for q in depths + speeds) or any(v <= 0 for v in speeds):
        raise ValueError('Invalid depth/velocity profile')
    if any(b < a for a, b in zip(speeds, speeds[1:])):
        raise ValueError('The existing reference requires a nondecreasing velocity profile')
    bounds = {key: (min(float(r[key]) for r in grid), max(float(r[key]) for r in grid)) for key in 'xyz'}
    node_count = len(grid)
    off = 4 * len(events)
    if len(columns) != off + node_count:
        raise ValueError('Unexpected Jacobian column count')
    for n, column in enumerate(columns):
        if column['column'] != str(n):
            raise ValueError('Column mapping order changed')
        if n < off:
            event = events[str(n // 4)]
            if column['event'] != str(n // 4) or column['parameter'] != 'xyzt'[n % 4]:
                raise ValueError('Source column mapping changed')
            for key, value in event.items():
                if key not in ('id', 'x', 'y', 'z', 't') and column['source_' + key] != value:
                    raise ValueError('Source column metadata changed: ' + key)
        elif column['parameter'] != 'q' or column['node'] != str(n - off):
            raise ValueError('Nodal log-slowness column mapping changed')
    expected = {str(n): r for n, r in enumerate(observations) if r['type'] == '0'}
    if len(rays) != len(expected) or set(r['observation_row'] for r in rays) != set(expected):
        raise ValueError('Absolute observation support is incomplete')
    support = set((r['i'], r['station']) for r in observations)
    support.update((r['j'], r['station_j']) for r in observations if int(r['j']) >= 0)
    if support != set((r['i'], r['station']) for r in rays):
        raise ValueError('Absolute rays do not cover every differential endpoint pair')
    for n, ray in enumerate(rays):
        if ray['row'] != str(n):
            raise ValueError('Linearization row order changed')
        original = expected[ray['observation_row']]
        if any(ray[key] != original[key] for key in observation_names if key not in ('j', 'type', 'value')):
            raise ValueError('Original observation metadata changed at row ' + str(n))
        if float(ray['observed']) != float(format(float(original['value']), '.12g')):
            raise ValueError('Observed value changed at row ' + str(n))
        event, station = events[ray['i']], stations[ray['station']]
        for key in ('event', 'origin'):
            if ray[key + '_i_resource_id'] != event[key + '_resource_id']:
                raise ValueError('Source native ID mismatch at row ' + str(n))
        for key in ('network_code', 'station_code', 'location_code', 'channel_code',
                    'channel_seed_id', 'channel_fdsn_source_id', 'metadata_epoch_start', 'metadata_epoch_end'):
            if ray[key] != station[key]:
                raise ValueError('Receiver native ID/epoch mismatch at row ' + str(n))
        for native in (event, station):
            if any(not math.isfinite(float(native[key])) or
                   not bounds[key][0] <= float(native[key]) <= bounds[key][1] for key in 'xyz'):
                raise ValueError('Endpoint outside the saved model domain')
        if not all(math.isfinite(float(ray[key])) for key in
                   ('observed', 'predicted', 'residual', 'ray_time', 'ray_projected_gradient', 'ray_raw_gradient')):
            raise ValueError('Nonfinite saved ray result')
    derivatives = [[0., 0., 0.] for _ in rays]
    origin_columns = set()
    previous, seen = -1, set()
    with (data / 'initial_linearization_matrix.csv').open() as stream:
        for item in csv.DictReader(stream):
            row, col, value = int(item['row']), int(item['column']), float(item['value'])
            if not 0 <= row < len(rays) or not 0 <= col < len(columns) or not math.isfinite(value):
                raise ValueError('Invalid/nonfinite Jacobian triplet')
            if row < previous:
                raise ValueError('Expected row-ordered linearization triplets')
            if row != previous:
                seen.clear()
                previous = row
            if col in seen:
                raise ValueError('Duplicate Jacobian triplet')
            seen.add(col)
            if col < off:
                base = 4 * int(rays[row]['i'])
                if not base <= col < base + 4:
                    raise ValueError('Absolute row contains another source derivative')
                if col == base + 3:
                    if value != 1:
                        raise ValueError('Origin-time derivative is not unity')
                    origin_columns.add(row)
                else:
                    derivatives[row][col - base] = value
    if len(origin_columns) != len(rays):
        raise ValueError('Missing absolute origin-time columns')
    out.mkdir(parents=True)
    snapshot = out / 'source'
    snapshot.mkdir()
    for source in sources:
        shutil.copyfile(str(source), str(snapshot / source.name))
    extra = ['reference_complete', 'reference_valid', 'reference_candidate_count',
             'reference_near_tie_count', 'reference_time_s', 'reference_branch',
             'reference_turning_depth_km', 'production_minus_reference_s',
             'reference_distance_closure_max_km', 'reference_isolation_boxes',
             'preserved_metadata_path_base']
    for axis in 'xyz':
        extra += ['source_' + axis + '_km', 'receiver_' + axis + '_km',
                  'production_source_d' + axis, 'reference_source_d' + axis,
                  'production_source_d' + axis + '_minus_reference']
    if set(extra).intersection(row_names):
        raise ValueError('New columns would overwrite original metadata')
    times, gradient_errors, counts = [], [], collections.Counter()
    started = time.time()
    with (out / 'comparison.csv').open('w', newline='') as stream, (out / 'references.jsonl').open('w') as references:
        writer = csv.DictWriter(stream, fieldnames=row_names + extra, lineterminator='\n')
        writer.writeheader()
        for n, ray in enumerate(rays):
            source = [float(events[ray['i']][key]) for key in 'xyz']
            receiver = [float(stations[ray['station']][key]) for key in 'xyz']
            reference = enumerate_arrivals(depths, speeds, source, receiver)
            first = reference.get('first_arrival')
            item = dict(ray)
            item.update(reference_complete=int(reference['complete']), reference_valid=int(reference['reference_valid']),
                        reference_candidate_count=len(reference['candidates']),
                        reference_near_tie_count=len(reference.get('near_ties', [])),
                        reference_time_s=first['time_s'] if first else '', reference_branch=first['kind'] if first else '',
                        reference_turning_depth_km=first['turning_depth_km'] if first and first['turning_depth_km'] is not None else '',
                        production_minus_reference_s=float(ray['ray_time']) - first['time_s'] if first else '',
                        reference_distance_closure_max_km=max([abs(c['distance_residual_km']) for c in reference['candidates']] or [0.]),
                        reference_isolation_boxes=reference['isolation_boxes'],
                        preserved_metadata_path_base=str(data.relative_to(ROOT)))
            if first:
                times.append(item['production_minus_reference_s'])
                counts['branch_' + first['kind']] += 1
            for axis, key in enumerate('xyz'):
                exact = first['source_derivative_s_per_km'][axis] if first and first['source_derivative_s_per_km'] is not None else None
                item['source_' + key + '_km'], item['receiver_' + key + '_km'] = source[axis], receiver[axis]
                item['production_source_d' + key] = derivatives[n][axis]
                item['reference_source_d' + key] = exact if exact is not None else ''
                item['production_source_d' + key + '_minus_reference'] = derivatives[n][axis] - exact if exact is not None else ''
                if exact is not None:
                    gradient_errors.append(derivatives[n][axis] - exact)
            writer.writerow(item)
            references.write(json.dumps(dict(row=ray['row'], observation_row=ray['observation_row'],
                             event=ray['i'], station=ray['station'], reference=reference), allow_nan=False) + '\n')
            counts['reference_complete'] += reference['complete']
            counts['reference_valid'] += reference['reference_valid']
            counts['near_ties'] += len(reference.get('near_ties', [])) > 1
            counts['saved_nonconverged'] += ray['ray_converged'] != '1'
            if (n + 1) % 250 == 0:
                stream.flush()
                references.flush()
                print('Compared {}/{} identified rays; {:.1f} s'.format(n + 1, len(rays), time.time() - started), flush=True)
    _, saved = table(out / 'comparison.csv')
    if len(saved) != len(rays) or any(any(a[k] != b[k] for k in row_names) for a, b in zip(rays, saved)):
        raise ValueError('Saved comparison changed original ray/identity columns')
    for path in files + sources:
        if sha(path) != hashes[str(path.relative_to(ROOT))]:
            raise ValueError('Frozen input or reference source changed during comparison')
    outputs = [out / 'comparison.csv', out / 'references.jsonl'] + list(snapshot.iterdir())
    summary = dict(status='complete' if counts['reference_valid'] == len(rays) else 'unresolved_cases_preserved',
                   command='PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python3 diagnostics/compare_hayward_1d_support.py --data ' + str(data.relative_to(ROOT)) + ' --output ' + str(out.relative_to(ROOT)),
                   scope='Continuous 1D reference versus saved full initial absolute support; no solver or inversion rerun',
                   rays=len(rays), unique_native_pairs=len(support), source_derivative_components=len(gradient_errors),
                   elapsed_reference_seconds=time.time() - started, reference_counts=dict(counts),
                   profile_depth_velocity_km_km_s=levels, preflight_status=preflight['status'],
                   original_columns_preserved=row_names, identity_join=['row', 'observation_row', 'i', 'station'],
                   candidate_join='references.jsonl row/observation_row/event/station join comparison.csv row/observation_row/i/station',
                   production_minus_reference_s=stats(times), production_source_derivative_minus_reference_s_per_km=stats(gradient_errors),
                   input_sha256=hashes, output_sha256={str(p.relative_to(ROOT)): sha(p) for p in outputs},
                   versions=dict(python=sys.version.split()[0], numpy=numpy.__version__, scipy=scipy.__version__),
                   environment=dict(OPENBLAS_NUM_THREADS=os.environ.get('OPENBLAS_NUM_THREADS')),
                   limitations=['Initial horizontally uniform monotone profile only; no claim for updated three-dimensional models.',
                                'Branch enumeration is certified only when complete; time ordering uses ordinary floating-point evaluations and near ties remain explicit.',
                                'A late time relative to the reference alone does not distinguish branch choice, path discretization, or incomplete local convergence.',
                                'Source derivatives are branch derivatives; distinct tied first arrivals need not have a unique derivative.',
                                'No new field pass threshold or inversion gate is imposed; all signed differences and existing stopping flags are retained.',
                                'Saved model/Jacobian values have the solver 12-significant-digit serialization; reference coordinates use the frozen original input precision.'])
    (out / 'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n')
    print(json.dumps({k: summary[k] for k in ['status', 'rays', 'reference_counts', 'production_minus_reference_s']}, indent=2))


if __name__ == '__main__':
    main()
