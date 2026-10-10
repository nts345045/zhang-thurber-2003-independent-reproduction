#!/usr/bin/env python3
"""Read back the identified dt.cc export without calling its serializer."""
import argparse
from collections import Counter
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
IDENTITY = ('network_code', 'station_code', 'location_code', 'channel_code',
            'channel_seed_id', 'channel_fdsn_source_id')
POSITION = ('x', 'y', 'z', 'latitude_deg', 'longitude_deg', 'sensor_z_geoid_km')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def table(path):
    with (gzip.open if path.suffix == '.gz' else open)(str(path), 'rt', newline='') as f:
        reader = csv.DictReader(f)
        require(len(reader.fieldnames) == len(set(reader.fieldnames)), 'Duplicate CSV header')
        rows = list(reader)
        require(all(None not in row and None not in row.values() for row in rows), 'Malformed CSV row')
        return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--export', type=Path, required=True)
    args = parser.parse_args(); folder = args.export.resolve(); folder.relative_to(ROOT)
    out = folder / 'independent_export_review.json'
    require(not out.exists(), 'Preserve an existing independent export review')
    pins = {}

    def pin(path, expected=None):
        path = path.resolve(); name = str(path.relative_to(ROOT)); digest = sha(path)
        require(expected is None or digest == expected, 'Pinned file changed: ' + name)
        require(name not in pins or pins[name] == digest, 'File changed during audit: ' + name)
        pins[name] = digest; return path

    def load(path):
        return json.loads(pin(path).read_text())

    pin(Path(__file__))
    summary = load(folder / 'summary.json'); execution = load(folder / 'execution.json')
    require(summary['status'] == 'completed_identified_dt_cc_export' and execution['status'] == 'completed' and
        execution['return_code'] == 0 and execution['summary_sha256'] == sha(folder / 'summary.json') and
        execution['network_requests'] == 0, 'Export is not terminal successful')
    require(summary['solver_observations_added'] == 0 and summary['original_catalog_values_changed'] is False,
        'Export scope changed')
    for name, digest in summary['input_source_sha256'].items():
        pin(ROOT / name, digest)
    for mapping in (summary['output_sha256'], execution['log_sha256']):
        for name, digest in mapping.items():
            path = (folder / name).resolve(); path.relative_to(folder); pin(path, digest)
    command = execution['command']
    path_for = lambda flag: ROOT / command[command.index(flag) + 1]
    measured_path = path_for('--measurements-summary'); measured = load(measured_path)
    review = load(path_for('--measurements-review'))
    require(measured['status'] == 'completed_identified_measurements' and review['status'] == 'passed' and
        review['measurements_summary_sha256'] == sha(measured_path), 'Reviewed measurement linkage differs')
    require(execution['source_sha256'] == sha(folder / 'source/export_identified_dt_cc.py'), 'Frozen exporter source differs')
    originals = table(pin(measured_path.parent / 'identified_measurements.csv.gz'))
    sidecar = table(folder / 'dt.cc.identifiers.csv.gz')
    require(len(originals) == len(sidecar) == summary['retained_original_catalog_pairs'] == 44718,
        'Full original measurement support changed')
    require(all({k:row[k] for k in old} == old for row, old in zip(sidecar, originals)),
        'Measurement columns or original catalog row order changed')
    native_epochs = table(pin(path_for('--epochs'))); by_epoch = {r['id']:r for r in native_epochs}
    require(len(by_epoch) == len(native_epochs), 'Repeated original epoch index')
    event_map = table(folder / 'event_id_map.csv'); receivers = table(folder / 'receiver_epochs.csv.gz')
    event_expected = {}; by_index = {}; accepted = []; row_by_line = {}; used_epochs = set()
    station_meanings = {}; observations = set(); accepted_event_ids = set()
    accepted_counts = Counter()
    original_fields = set(originals[0]); added_fields = set(sidecar[0]) - original_fields
    require(added_fields == {'dt_cc_export_status', 'dt_cc_line_number', 'dt_cc_header_line_number',
        'dt_cc_event_i', 'dt_cc_event_j', 'dt_cc_station', 'dt_cc_phase', 'dt_cc_origin_correction_s'},
        'Unexpected export sidecar schema')
    for row in sidecar:
        get = lambda key: row['original_catalog_' + key]
        for side in ('i', 'j'):
            index = int(get(side)); resource = get('event_' + side + '_resource_id'); origin = get('origin_' + side + '_resource_id')
            expected = dict(dt_cc_event_id=str(index + 1), original_event_index=str(index),
                event_resource_id=resource, origin_resource_id=origin, mapping_basis='local original event index plus one')
            require(event_expected.get(resource, expected) == expected and by_index.get(index, resource) == resource,
                'Event resource/origin/integer collision')
            event_expected[resource] = expected; by_index[index] = resource
            require(row['dt_cc_event_' + side] == str(index + 1), 'Sidecar event number differs')
        if row['measurement_status'] != 'accepted_discrete_measurement':
            require(row['dt_cc_export_status'] == 'not_accepted' and all(row[k] == '' for k in
                ('dt_cc_line_number', 'dt_cc_header_line_number', 'dt_cc_station', 'dt_cc_phase', 'dt_cc_origin_correction_s')),
                'An unaccepted measurement was exported')
            continue
        accepted.append(row)
        require(row['dt_cc_export_status'] == 'exported' and row['dt_cc_phase'] == 'P' and
            row['dt_cc_station'] == get('station_code') and row['dt_cc_origin_correction_s'] == '0.0',
            'Accepted phase/station/origin correction differs')
        line = int(row['dt_cc_line_number']); require(line not in row_by_line, 'Two measurements map to the same text line')
        row_by_line[line] = row
        positions = []
        for side in ('i', 'j'):
            key = get('station' if side == 'i' else 'station_j'); epoch = by_epoch[key]; used_epochs.add(key)
            require(all(get(k) == epoch[k] for k in IDENTITY), 'Accepted native SEED/resource identity differs')
            require(all(get('metadata_epoch_' + ('j_' if side == 'j' else '') + bound) == epoch['metadata_epoch_' + bound]
                for bound in ('start', 'end')), 'Accepted native epoch differs')
            require(get('channel_' + ('j_' if side == 'j' else '') + 'source_sha256') == epoch['source_sha256'],
                'Accepted metadata source differs')
            positions.append(tuple(float(epoch[k]) for k in POSITION))
            accepted_event_ids.add(row['dt_cc_event_' + side])
        require(positions[0] == positions[1] and all(math.isfinite(x) for x in positions[0]), 'Accepted receiver positions differ')
        meaning = tuple(get(k) for k in IDENTITY) + positions[0]; station = row['dt_cc_station']
        require(station_meanings.get(station, meaning) == meaning, 'Legacy station alias collapses distinct NSLC/position')
        station_meanings[station] = meaning
        obs = (tuple(sorted((row['dt_cc_event_i'], row['dt_cc_event_j']))), station, 'P')
        require(obs not in observations, 'Duplicate/reversed event-pair/station/phase'); observations.add(obs)
        accepted_counts[get('channel_seed_id')] += 1
    require(event_map == sorted(event_expected.values(), key=lambda row:int(row['original_event_index'])),
        'Complete event map differs from all original pair events')
    require(receivers == [dict(by_epoch[key], dt_cc_station=by_epoch[key]['station_code']) for key in sorted(used_epochs, key=int)],
        'Accepted receiver epoch map omits or rewrites native metadata')
    lines = (folder / 'dt.cc').read_text().splitlines(); current = None; header_line = None
    seen_headers = set(); used_header_lines = set(); seen_data_lines = set()
    for n, text in enumerate(lines, 1):
        tokens = text.split(); require(tokens, 'Blank legacy text line')
        if tokens[0] == '#':
            require(len(tokens) == 4 and tokens[3] == '0.0', 'Malformed header or nonzero origin correction')
            current = tuple(tokens[1:3]); header_line = n
            require(current not in seen_headers and all(x in {r['dt_cc_event_id'] for r in event_map} for x in current),
                'Duplicate or unmapped event header')
            seen_headers.add(current)
        else:
            require(len(tokens) == 4 and current is not None and n in row_by_line, 'Unmapped or malformed observation line')
            row = row_by_line[n]
            require(current == (row['dt_cc_event_i'], row['dt_cc_event_j']) and
                int(row['dt_cc_header_line_number']) == header_line and tokens[0] == row['dt_cc_station'] and tokens[3] == 'P',
                'Legacy header/row/phase join differs')
            value, weight = map(float, tokens[1:3]); cc = float(row['maximum_cc'])
            require(math.isfinite(value) and math.isfinite(weight) and value == float(row['dt_cc_i_minus_j_s']) ==
                float(row['original_catalog_value']) - float(row['cc_delay_j_minus_i_s']) and
                weight == float(row['cc_relative_weight_squared']) == float(row['maximum_cc_squared']) == cc ** 2,
                'Legacy float roundtrip, i-minus-j sign, or CC squared differs')
            require(tokens[1] == format(value, '.17g') and tokens[2] == format(weight, '.17g'), 'Unexpected numeric serialization')
            seen_data_lines.add(n); used_header_lines.add(header_line)
    require(seen_data_lines == set(row_by_line) and len(used_header_lines) == len(seen_headers), 'Orphan header or missing observation')
    require(len(accepted) == len(seen_data_lines) == summary['exported_observations'] == 98 and
        len(sidecar) - len(accepted) == summary['preserved_unexported_observations'] == 44620,
        'Accepted/unaccepted count differs')
    for name, digest in pins.items():
        require(sha(ROOT / name) == digest, 'File changed during audit: ' + name)
    result = dict(status='passed', reviewer='earthscope_discovery',
        scope='Independent legacy text/native sidecar readback; no exporter rerun, measurement or solver import',
        export_summary_sha256=sha(folder / 'summary.json'), export_execution_sha256=sha(folder / 'execution.json'),
        measurements_summary_sha256=sha(measured_path), measurements_review_sha256=sha(path_for('--measurements-review')),
        review_source_sha256=sha(Path(__file__)), verified_file_sha256=pins,
        retained_original_catalog_pairs=len(sidecar), exported_observations=len(accepted),
        preserved_unexported_observations=len(sidecar)-len(accepted), exported_pair_headers=len(seen_headers),
        mapped_original_pair_events=len(event_map), events_with_exported_observations=len(accepted_event_ids),
        native_receiver_epochs=len(receivers), accepted_channel_counts=dict(accepted_counts),
        every_original_measurement_field_and_order_preserved=True, complete_event_origin_mapping_matches=True,
        full_receiver_epoch_maps_match=True, every_accepted_observation_has_unique_header_line_and_native_sidecar=True,
        exact_binary64_roundtrip_and_i_minus_j_cc_squared_arithmetic_passed=True,
        no_legacy_station_channel_or_position_collisions=True, solver_observations_added=0, material_issue_found=False,
        limitations=['The legacy station token requires its native sidecars to recover NSLC and both epochs.',
            'CC squared remains a relative export weight, not timing inverse variance or a selected solver multiplier.',
            'This verifies serialization of reviewed measurements, not calibration equivalence, formal timing precision or inverse-model validity.'])
    with out.open('x') as f:
        json.dump(result, f, indent=2, allow_nan=False); f.write('\n')
    print(json.dumps({key:result[key] for key in ('status','retained_original_catalog_pairs','exported_observations',
        'preserved_unexported_observations','exported_pair_headers','mapped_original_pair_events','events_with_exported_observations',
        'native_receiver_epochs','accepted_channel_counts')}, indent=2))
    print('review_sha256', sha(out))


if __name__ == '__main__':
    main()
