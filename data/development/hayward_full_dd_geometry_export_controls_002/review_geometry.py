#!/usr/bin/env python3
"""Read saved full-DD geometry; no ray evaluation or covariance calculation."""
import argparse
import csv
import hashlib
import itertools
import json
import math
from pathlib import Path


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def records(path):
    with Path(path).open(newline='') as f:
        table = csv.DictReader(f)
        fields = table.fieldnames or []
        require(fields and len(fields) == len(set(fields)), 'missing/duplicate CSV header: ' + str(path))
        for row in table:
            require(None not in row and all(v is not None for v in row.values()),
                    'incomplete CSV row: ' + str(path))
            yield row


def number(text, label):
    value = float(text)
    require(math.isfinite(value), 'nonfinite ' + label)
    return value


def integer(text, label):
    value = number(text, label)
    require(value == math.floor(value) and -2**31 <= value < 2**31, 'invalid integer ' + label)
    return int(value)


def flag(row, key):
    value = integer(row[key], key)
    require(value in (0, 1), 'invalid flag ' + key)
    return value


def review(data_dir, config_path, mode='dd'):
    data_dir, config_path = Path(data_dir), Path(config_path)
    prefix = data_dir / (mode + '_full_linearization')
    suffixes = ('matrix', 'rows', 'suppressed', 'columns', 'smoothing_matrix',
                'smoothing_rows', 'rays', 'info', 'ray_geometry', 'ray_paths')
    paths = {name: Path(str(prefix) + '_' + name + '.csv') for name in suffixes}
    paths.update(events=data_dir / (mode + '_events.csv'), grid=data_dir / (mode + '_grid.csv'),
                 stations=data_dir / 'stations.csv', observations=data_dir / 'observations.csv', config=config_path)
    # A rejected export may intentionally have only the two diagnostic files.
    # Hash the existing inventory, then require the complete operator only after
    # inspecting its diagnostic flags. A missing file never becomes a pass.
    pins = {key: sha(path) for key, path in paths.items() if path.is_file()}
    native, metadata = [], []
    identities = (('event_resource_id', 'origin_resource_id'),
                  ('network_code', 'station_code', 'location_code', 'channel_code',
                   'channel_seed_id', 'channel_fdsn_source_id', 'metadata_epoch_start', 'metadata_epoch_end'))
    for key, needed in zip(('events', 'stations'), identities):
        rows = list(records(paths[key])); require(rows, 'empty native table')
        fields = set(rows[0]) - {'id', 'x', 'y', 'z', 't'}
        require(set(needed) <= fields, 'missing native identity columns')
        for index, row in enumerate(rows):
            require(integer(row['id'], 'native id') == index, 'native index changed')
            for name in needed:
                require(row[name] or name in ('location_code', 'metadata_epoch_end'), 'empty native identity')
            for axis in 'xyzt':
                number(row[axis], 'native ' + axis)
        native.append(rows); metadata.append(fields)
    events, stations = native
    grid = list(records(paths['grid']))
    axes = [sorted(set(number(r[a], 'grid coordinate') for r in grid)) for a in 'xyz']
    require(all(len(a) >= 2 for a in axes), 'incomplete grid axes')
    positions = [tuple(number(r[a], 'grid coordinate') for a in 'xyz') for r in grid]
    require(len(positions) == len(set(positions)) and set(positions) == set(itertools.product(*axes)),
            'incomplete/duplicate grid nodes')
    require(all(number(r['v'], 'grid velocity') > 0 for r in grid), 'nonpositive grid velocity')
    cfg = {}
    for line in config_path.read_text().splitlines():
        fields = line.split()
        if len(fields) < 2:
            continue
        try:
            cfg[fields[0]] = float(fields[1])
        except ValueError:
            require(fields[0] not in ('ray_initializer', 'fmm_spacing'), 'invalid configured numeric value')
            continue
    initializer = cfg.get('ray_initializer', 0)
    require(initializer in (0, 1), 'invalid configured initializer')
    if initializer:
        require(math.isfinite(cfg['fmm_spacing']) and cfg['fmm_spacing'] > 0, 'invalid configured FMM spacing')
    observations = list(records(paths['observations']))
    support, sides = set(), []
    for row in observations:
        i, j, k, kind = [integer(row[key], key) for key in ('i', 'j', 'station', 'type')]
        second = integer(row['station_j'], 'station_j') if row.get('station_j', '') != '' else -1
        require(0 <= i < len(events) and 0 <= k < len(stations) and kind in (0, 1, 2) and
                (j == -1 if kind == 0 else 0 <= j < len(events) and i != j) and
                -1 <= second < len(stations) and (j >= 0 or second == -1), 'invalid observation indices')
        require(not ('station_j' in row and j >= 0 and second < 0), 'missing explicit second epoch')
        second = -1 if j < 0 else k if second < 0 else second
        for side, event in (('i', i), ('j', j)):
            for name in ('event', 'origin'):
                expected = '' if event < 0 else events[event][name + '_resource_id']
                require(row[name + '_' + side + '_resource_id'] == expected,
                        'observation event/origin association changed')
        for name in identities[1]:
            require(row[name] == stations[k][name], 'observation first channel/epoch changed')
        pair = (i, k); support.add(pair)
        if j >= 0:
            left, right = stations[k], stations[second]
            require(all(float(left[a]) == float(right[a]) for a in 'xyz') and
                    all(left[a] == right[a] for a in identities[1][:6]), 'different DD channel/position')
            if 'station_j' in row or 'metadata_epoch_j_start' in row or 'metadata_epoch_j_end' in row:
                for edge in ('start', 'end'):
                    require(row['metadata_epoch_j_' + edge] == right['metadata_epoch_' + edge],
                            'observation second epoch changed')
            support.add((j, second))
        else:
            require(not row.get('metadata_epoch_j_start') and not row.get('metadata_epoch_j_end'),
                    'absolute second epoch is nonempty')
        sides.append((i, j, k, second, kind))

    def native_join(row, pair):
        for pre, table, fields, index in zip(('source_', 'receiver_'), native, metadata, pair):
            require(all(row[pre + key] == table[index][key] for key in fields), 'native metadata mismatch')

    geometry, order = {}, []
    required_flags = ('ray_finite', 'ray_converged', 'ray_path_in_domain', 'ray_exact_source_endpoint',
                      'ray_exact_receiver_endpoint', 'ray_derivatives_evaluated')
    for row in records(paths['ray_geometry']):
        pair = tuple(integer(row[k], k) for k in ('event', 'station'))
        require(pair in support and pair not in geometry, 'unexpected/duplicate geometry pair')
        native_join(row, pair)
        for pre, table, index in zip(('source_', 'receiver_'), native, pair):
            for axis in 'xyz':
                require(number(row[pre + axis], pre + axis) == float(table[index][axis]),
                        '17-digit native coordinate mismatch')
        require(number(row['source_t'], 'source_t') == float(events[pair[0]]['t']), 'source time changed')
        require(all(flag(row, key) for key in required_flags), 'failed geometry/local/derivative flag')
        attempted, succeeded = [flag(row, 'ray_initialization_' + key) for key in ('attempted', 'succeeded')]
        require(not initializer or attempted, 'required initializer not attempted')
        require(not (initializer or attempted) or succeeded, 'initializer failed')
        for key in ('ray_time', 'ray_projected_gradient', 'ray_raw_gradient'):
            require(number(row[key], key) >= 0, 'negative ray diagnostic')
        for axis in 'xyz':
            number(row['source_d' + axis], 'source derivative')
        require(integer(row['ray_path_points'], 'path count') > 0, 'empty path count')
        geometry[pair] = row; order.append(pair)
    require(order == sorted(support), 'incomplete/unordered geometry support')
    counts = dict.fromkeys(order, 0); last_pair = None; last_point = None; path_rows = 0
    for row in records(paths['ray_paths']):
        pair = tuple(integer(row[k], k) for k in ('event', 'station'))
        require(pair in geometry and (last_pair is None or pair >= last_pair), 'unexpected/unordered path pair')
        node = integer(row['node'], 'path node')
        require(node == counts[pair], 'missing/duplicate/unordered path node')
        native_join(row, pair)
        point = tuple(number(row[a], 'path coordinate') for a in 'xyz')
        require(all(axis[0] <= value <= axis[-1] for axis, value in zip(axes, point)), 'path outside domain')
        if pair != last_pair:
            if last_pair is not None:
                require(last_point == tuple(float(stations[last_pair[1]][a]) for a in 'xyz'), 'receiver endpoint mismatch')
            require(point == tuple(float(events[pair[0]][a]) for a in 'xyz'), 'source endpoint mismatch')
        counts[pair] += 1; path_rows += 1; last_pair, last_point = pair, point
    require(last_pair is not None, 'empty path table')
    require(last_point == tuple(float(stations[last_pair[1]][a]) for a in 'xyz'), 'receiver endpoint mismatch')
    require(all(counts[p] == integer(geometry[p]['ray_path_points'], 'path count') for p in order), 'path count mismatch')
    require(set(pins) == set(paths), 'incomplete original export inventory')
    old = list(records(paths['rays']))
    require(len(old) == len(order), 'incomplete legacy ray support')
    numeric = ('source_x', 'source_y', 'source_z', 'receiver_x', 'receiver_y', 'receiver_z',
               'ray_time', 'ray_projected_gradient', 'ray_raw_gradient', 'ray_direct_seed_time',
               'ray_fmm_seed_time', 'ray_field_time')
    for row, pair in zip(old, order):
        require(tuple(integer(row[k], k) for k in ('event', 'station')) == pair, 'legacy ray order changed')
        for key, value in row.items():
            if key in numeric:
                a, b = float(value), float(format(float(geometry[pair][key]), '.12g'))
                require(a == b or (math.isnan(a) and math.isnan(b)), 'legacy numeric serialization mismatch')
            else:
                require(value == geometry[pair][key], 'legacy ray status/metadata mismatch')
    exported = list(records(paths['rows']))
    require(len(exported) == len(observations), 'original observation row count changed')
    for q, (row, obs, side) in enumerate(zip(exported, observations, sides)):
        require(integer(row['observation_row'], 'observation row') == q, 'observation order changed')
        for key, value in zip(('i', 'j', 'station', 'station_j_index', 'type'), side):
            require(integer(row[key], key) == value, 'export observation index changed')
        require(number(row['observed'], 'observed') == number(obs['value'], 'original value'), 'observed value changed')
        for key in set(obs) - {'i', 'j', 'station', 'type', 'value'}:
            require(row['observation_' + key] == obs[key], 'original observation metadata changed')
    seen_columns = [set() for _ in observations]; source_entries = 0
    for row in records(paths['matrix']):
        q, col = integer(row['observation_row'], 'matrix observation'), integer(row['column'], 'matrix column')
        require(0 <= q < len(sides) and col >= 0, 'matrix index outside inventory')
        if col >= 4 * len(events):
            continue
        event, axis = divmod(col, 4); i, j, k, second, kind = sides[q]
        require(event in (i, j) and col not in seen_columns[q], 'unexpected/duplicate source matrix column')
        pair, sign = ((i, k), 1) if event == i else ((j, second), -1)
        expected = sign * (1 if axis == 3 else float(geometry[pair]['source_d' + 'xyz'[axis]]))
        require(number(row['value'], 'matrix source entry') == expected, 'source partial/matrix mismatch')
        seen_columns[q].add(col); source_entries += 1
    require(all(len(cols) == (4 if side[1] < 0 else 8) for cols, side in zip(seen_columns, sides)),
            'incomplete source matrix columns')
    info_rows = list(records(paths['info'])); info = {r['key']: r['value'] for r in info_rows}
    require(len(info) == len(info_rows) and integer(info['observed_rays'], 'info support') == len(support) and
            integer(info['ray_status_failures'], 'info failures') == 0, 'legacy aggregate ray counts changed')
    require(all(sha(path) == pins[key] for key, path in paths.items()), 'input changed during readback')
    return {'status': 'passed', 'native_rays': len(order), 'path_nodes': path_rows,
            'observations': len(observations), 'source_matrix_entries': source_entries,
            'initializer_required': bool(initializer),
            'unattempted_initializers': sum(not int(geometry[p]['ray_initialization_attempted']) for p in order),
            'input_sha256': {str(paths[k]): pins[k] for k in sorted(paths)},
            'reader_sha256': sha(Path(__file__)),
            'scope': 'Saved local/status/geometry/native/source-entry consistency at the parsed saved model only.',
            'limitations': ['No source/binary execution attestation is created by table agreement alone.',
                            'No first-arrival, derivative-accuracy or nonlinear-convergence certificate.',
                            'The saved 12-digit model is the evaluation point; earlier internal precision is unavailable.',
                            'No covariance calculation or change to its conditional/noise assumptions.']}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data-dir', required=True); p.add_argument('--config', required=True)
    p.add_argument('--mode', default='dd'); p.add_argument('--output', required=True)
    args = p.parse_args(); output = Path(args.output)
    require(not output.exists() and not output.is_symlink(), 'preserve existing geometry review')
    result = review(args.data_dir, args.config, args.mode)
    with output.open('x') as f:
        json.dump(result, f, indent=2, sort_keys=True, allow_nan=False); f.write('\n')


if __name__ == '__main__':
    main()
