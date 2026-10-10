#!/usr/bin/env python3
"""Compare a completed identified failure subset with continuous layered rays.

The 25 microsecond time and 3e-6 s/km source-vector limits are the existing
analytic-control limits. This subset comparison cannot certify a full run.
"""
import argparse
import collections
import csv
import json
import math
from pathlib import Path
import shutil
import time

from compare_hayward_1d_support import sha, stats, table
from first_arrival_1d_reference import enumerate_arrivals

ROOT = Path(__file__).resolve().parents[1]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    data, out = (ROOT / args.data).resolve(), (ROOT / args.output).resolve()
    for path in (data, out):
        path.relative_to(ROOT)
    require(not out.exists(), 'Choose a fresh output directory')
    summary = json.loads((data / 'summary.json').read_text())
    require(summary['status'] == 'completed' and summary['return_code'] == 0,
            'Subset linearization is not complete')
    expected_command = [summary['binary'], 'linearize', str((data / 'run.cfg').relative_to(ROOT)),
                        str(data.relative_to(ROOT)), 'initial']
    require(summary['command'] == expected_command, 'Unexpected completed command')
    hashes = {data / name: value for name, value in summary['output_sha256'].items()}
    hashes[data / 'summary.json'] = sha(data / 'summary.json')
    sources = [Path(__file__).resolve(), ROOT / 'diagnostics/compare_hayward_1d_support.py',
               ROOT / 'diagnostics/first_arrival_1d_reference.py']
    hashes.update({p: sha(p) for p in sources})
    for path, expected in hashes.items():
        require(sha(path) == expected, 'Frozen input changed: ' + str(path))
    out.mkdir(parents=True)
    (out / 'inputs').mkdir()
    (out / 'source').mkdir()
    for path in hashes:
        target = out / ('source' if path in sources else 'inputs') / path.name
        shutil.copyfile(str(path), str(target))
        require(sha(target) == hashes[path], 'Input changed during snapshot')
    frozen = out / 'inputs'
    _, event_rows = table(frozen / 'initial_events.csv')
    _, station_rows = table(frozen / 'stations.csv')
    _, grid = table(frozen / 'initial_grid.csv')
    obs_names, observations = table(frozen / 'observations.csv')
    row_names, rays = table(frozen / 'initial_linearization_rows.csv')
    _, columns = table(frozen / 'initial_linearization_columns.csv')
    _, original = table(frozen / 'original_failed_rows.csv')
    events = {r['id']: r for r in event_rows}
    stations = {r['id']: r for r in station_rows}
    require(set(events) == set(map(str, range(len(event_rows)))) and
            set(stations) == set(map(str, range(len(station_rows)))), 'Nonunique or noncontiguous native indices')
    require(len(rays) == len(observations) == len(original) == summary['failed_ray_count'], 'Subset support changed')
    levels = sorted(set((float(r['z']), float(r['v'])) for r in grid))
    require(len(levels) == len(set(z for z, _ in levels)), 'Initial grid is not horizontally uniform')
    depths, speeds = map(list, zip(*levels))
    bounds = {k: (min(float(r[k]) for r in grid), max(float(r[k]) for r in grid)) for k in 'xyz'}
    off = 4 * len(events)
    require(len(columns) == off + len(grid), 'Unexpected column count')
    for n, column in enumerate(columns):
        require(column['column'] == str(n), 'Column order changed')
        if n < off:
            require(column['event'] == str(n // 4) and column['parameter'] == 'xyzt'[n % 4], 'Source column changed')
            for key, value in events[str(n // 4)].items():
                if key not in ('id', 'x', 'y', 'z', 't'):
                    require(column['source_' + key] == value, 'Source column metadata changed')
        else:
            require(column['parameter'] == 'q' and column['node'] == str(n - off), 'Model column changed')
    for n, (ray, obs, old) in enumerate(zip(rays, observations, original)):
        require(ray['row'] == ray['observation_row'] == str(n) and obs['type'] == '0', 'Local row mapping changed')
        require(ray['original_observation_row'] == old['observation_row'] and old['ray_converged'] != '1', 'Original failed row changed')
        for key in obs_names:
            if key not in ('j', 'type', 'value'):
                require(ray[key] == obs[key], 'Observation metadata changed: ' + key)
                if key != 'original_observation_row':
                    require(ray[key] == old[key], 'Original metadata changed: ' + key)
        require(float(ray['observed']) == float(format(float(obs['value']), '.12g')), 'Observed time changed')
        event, station = events[ray['i']], stations[ray['station']]
        for key in ('event', 'origin'):
            require(ray[key + '_i_resource_id'] == event[key + '_resource_id'], 'Native event join changed')
        for key in ('network_code', 'station_code', 'location_code', 'channel_code', 'channel_seed_id',
                    'channel_fdsn_source_id', 'metadata_epoch_start', 'metadata_epoch_end'):
            require(ray[key] == station[key], 'Native station join changed: ' + key)
        require(all(math.isfinite(float(native[k])) and bounds[k][0] <= float(native[k]) <= bounds[k][1]
                    for native in (event, station) for k in 'xyz'), 'Endpoint outside finite model')
    derivatives = [[0., 0., 0.] for _ in rays]
    origin_rows, seen = set(), set()
    with (frozen / 'initial_linearization_matrix.csv').open() as stream:
        for item in csv.DictReader(stream):
            r, c, value = int(item['row']), int(item['column']), float(item['value'])
            require(0 <= r < len(rays) and 0 <= c < len(columns) and math.isfinite(value), 'Invalid triplet')
            require((r, c) not in seen, 'Duplicate triplet')
            seen.add((r, c))
            if c < off:
                base = 4 * int(rays[r]['i'])
                require(base <= c < base + 4, 'Absolute row contains another event derivative')
                if c == base + 3:
                    require(value == 1., 'Origin derivative is not unity')
                    origin_rows.add(r)
                else:
                    derivatives[r][c - base] = value
    require(len(origin_rows) == len(rays), 'Origin derivative missing')
    extra = ['reference_valid', 'reference_complete', 'reference_near_ties', 'reference_time_s',
             'reference_branch', 'reference_turning_depth_km', 'time_error_s', 'source_error_norm_s_per_km',
             'source_error_max_component_s_per_km', 'time_limit_pass', 'source_vector_limit_pass', 'both_limits_pass']
    for k in 'xyz':
        extra += ['source_' + k + '_km', 'receiver_' + k + '_km', 'production_source_d' + k,
                  'reference_source_d' + k, 'source_error_d' + k]
    require(not set(extra).intersection(row_names), 'New columns overwrite saved columns')
    started = time.time()
    counts, times, norms = collections.Counter(), [], []
    with (out / 'comparison.csv').open('w', newline='') as stream, (out / 'references.jsonl').open('w') as refs:
        writer = csv.DictWriter(stream, fieldnames=row_names + extra, lineterminator='\n')
        writer.writeheader()
        for n, ray in enumerate(rays):
            source = [float(events[ray['i']][k]) for k in 'xyz']
            receiver = [float(stations[ray['station']][k]) for k in 'xyz']
            ref = enumerate_arrivals(depths, speeds, source, receiver)
            first = ref.get('first_arrival')
            unique = bool(ref['complete'] and ref['reference_valid'] and first and
                          len(ref.get('near_ties', [])) == 1 and first['source_derivative_s_per_km'] is not None)
            item = dict(ray, reference_valid=int(ref['reference_valid']), reference_complete=int(ref['complete']),
                        reference_near_ties=len(ref.get('near_ties', [])))
            for k in 'xyz':
                j = 'xyz'.index(k)
                item.update({'source_' + k + '_km': source[j], 'receiver_' + k + '_km': receiver[j],
                             'production_source_d' + k: derivatives[n][j]})
            if first:
                item.update(reference_time_s=first['time_s'], reference_branch=first['kind'],
                            reference_turning_depth_km=first['turning_depth_km'],
                            time_error_s=float(ray['ray_time']) - first['time_s'])
            if unique:
                error = [a - b for a, b in zip(derivatives[n], first['source_derivative_s_per_km'])]
                norm = math.sqrt(sum(e * e for e in error))
                item.update(source_error_norm_s_per_km=norm, source_error_max_component_s_per_km=max(map(abs, error)),
                            time_limit_pass=int(abs(item['time_error_s']) <= 2.5e-5), source_vector_limit_pass=int(norm <= 3e-6))
                item['both_limits_pass'] = item['time_limit_pass'] * item['source_vector_limit_pass']
                for j, k in enumerate('xyz'):
                    item['reference_source_d' + k] = first['source_derivative_s_per_km'][j]
                    item['source_error_d' + k] = error[j]
                times.append(item['time_error_s'])
                norms.append(norm)
                for key in ('time_limit_pass', 'source_vector_limit_pass', 'both_limits_pass'):
                    counts[key] += item[key]
            counts['unique_valid_reference'] += unique
            counts['reference_complete'] += ref['complete']
            counts['local_converged'] += ray['ray_converged'] == '1'
            counts['initialized'] += ray['ray_initialization_succeeded'] == '1'
            writer.writerow(item)
            refs.write(json.dumps(dict(row=ray['row'], original_observation_row=ray['original_observation_row'],
                                       event_i_resource_id=ray['event_i_resource_id'], pick_i_resource_id=ray['pick_i_resource_id'],
                                       channel_seed_id=ray['channel_seed_id'], channel_fdsn_source_id=ray['channel_fdsn_source_id'],
                                       metadata_epoch_start=ray['metadata_epoch_start'], metadata_epoch_end=ray['metadata_epoch_end'],
                                       reference=ref), allow_nan=False) + '\n')
    _, saved = table(out / 'comparison.csv')
    require(len(saved) == len(rays) and all(all(a[k] == b[k] for k in row_names) for a, b in zip(rays, saved)),
            'Output lost original columns or rows')
    for path, expected in hashes.items():
        require(sha(path) == expected, 'Frozen input/source changed during comparison')
    result = dict(status='completed' if counts['unique_valid_reference'] == len(rays) else 'unresolved_preserved',
                  scope='All previously failed initial rays only; no full-cohort or updated-model accuracy claim',
                  data=str(data.relative_to(ROOT)), rays=len(rays), counts=dict(counts),
                  time_error_s=stats(times), source_vector_error_s_per_km=stats(norms),
                  time_limit_s=2.5e-5, source_euclidean_vector_limit_s_per_km=3e-6,
                  limits_basis='diagnostics/check_fmm_rotated_affine.cpp selected_exact_time and selected_exact_source',
                  path_spacing_km=summary['path_spacing_km'], field_spacing_km=summary['field_spacing_km'],
                  elapsed_seconds=time.time() - started, profile=levels, original_columns_preserved=row_names,
                  original_sha256={str(p.relative_to(ROOT)): h for p, h in hashes.items()},
                  saved_sha256={str(p.relative_to(out)): sha(p) for p in sorted(out.rglob('*')) if p.is_file()},
                  limitations=['Unique valid continuous branches only receive pass/fail comparisons.',
                               'Saved Jacobian/time values have 12-significant-digit serialization.',
                               'No station or event is excluded, and failed local flags remain explicit.'])
    (out / 'summary.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({k: result[k] for k in ('status', 'rays', 'counts', 'time_error_s', 'source_vector_error_s_per_km')}, indent=2))


if __name__ == '__main__':
    main()
