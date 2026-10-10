#!/usr/bin/env python3
"""Serialize reviewed identified P correlations with lossless native sidecars."""
import argparse
import collections
import csv
import datetime
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
PREFIX = 'original_catalog_'
IDENTITY = ('network_code', 'station_code', 'location_code', 'channel_code',
            'channel_seed_id', 'channel_fdsn_source_id')
POSITION = ('x', 'y', 'z', 'latitude_deg', 'longitude_deg', 'sensor_z_geoid_km')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def table(path):
    with (gzip.open if path.suffix == '.gz' else open)(path, 'rt', newline='') as f:
        return list(csv.DictReader(f))


def csv_save(path, rows, fields):
    with path.open('xb') as raw:
        stream = gzip.GzipFile(filename='', fileobj=raw, mode='wb', mtime=0) if path.suffix == '.gz' else raw
        with io.TextIOWrapper(stream, encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
            writer.writeheader(); writer.writerows(rows)


def serialize(rows, epochs):
    """Return text, all-row line mapping, event map and accepted receiver epochs."""
    require(rows, 'Require the complete nonempty measurement roster')
    by_epoch = {r['id']: r for r in epochs}
    require(len(by_epoch) == len(epochs), 'Duplicate receiver epoch index')
    events = {}; event_indices = {}; seen_rows = set(); seen_measurements = set()
    stations = {}; used_epochs = set(); grouped = collections.OrderedDict(); seen_obs = set()
    mapped = []
    for row in rows:
        get = lambda key: row[PREFIX + key]
        require(get('original_observation_index') not in seen_rows and row['measurement_id'] not in seen_measurements,
                'Duplicate original observation or measurement ID')
        seen_rows.add(get('original_observation_index')); seen_measurements.add(row['measurement_id'])
        require(get('type') == '1' and get('observation_basis') == 'catalog P pick difference', 'Require identified P catalog pairs')
        sides = []
        for side in ('i', 'j'):
            index = int(get(side)); resource = get('event_' + side + '_resource_id')
            origin = get('origin_' + side + '_resource_id')
            require(index >= 0 and str(index) == get(side) and resource and origin, 'Missing or invalid event identity')
            require(events.get(resource, (index, origin)) == (index, origin) and event_indices.get(index, resource) == resource,
                    'Event/resource/origin mapping is not one to one')
            events[resource] = (index, origin); event_indices[index] = resource; sides.append(index + 1)
            require(get('pick_' + side + '_resource_id') and get('arrival_' + side + '_resource_id'), 'Missing native pick/association identity')
        require(sides[0] != sides[1], 'Self event pair')
        saved = dict(row, dt_cc_export_status='not_accepted', dt_cc_line_number='',
                     dt_cc_header_line_number='', dt_cc_event_i=sides[0], dt_cc_event_j=sides[1],
                     dt_cc_station='', dt_cc_phase='', dt_cc_origin_correction_s='')
        mapped.append(saved)
        if row['measurement_status'] != 'accepted_discrete_measurement':
            require(not row['dt_cc_i_minus_j_s'] and not row['cc_relative_weight_squared'], 'Rejected row has an accepted value/weight')
            continue
        require(row['cc_attempted'] == '1' and row['diagnostics_jsonl_row'] != '', 'Accepted row lacks attempted diagnostics')
        value, weight, cc = [float(row[k]) for k in ('dt_cc_i_minus_j_s', 'cc_relative_weight_squared', 'maximum_cc')]
        require(all(math.isfinite(v) for v in (value, weight, cc)) and 0 < cc <= 1 + 64 * sys.float_info.epsilon and weight == cc ** 2 == float(row['maximum_cc_squared']),
                'Accepted relative weight is not finite positive CC squared')
        require(value == float(get('value')) - float(row['cc_delay_j_minus_i_s']), 'Differential-time sign or value changed')
        require(not row['cc_formal_timing_uncertainty_s'], 'No formal timing uncertainty is established')
        receiver_positions = []
        for side in ('i', 'j'):
            key = get('station' if side == 'i' else 'station_j'); epoch = by_epoch[key]
            require(all(get(k) == epoch[k] for k in IDENTITY), 'Receiver SEED identity mismatch')
            for bound in ('start', 'end'):
                require(get('metadata_epoch_' + ('j_' if side == 'j' else '') + bound) == epoch['metadata_epoch_' + bound], 'Receiver epoch mismatch')
            require(get('channel_' + ('j_' if side == 'j' else '') + 'source_sha256') == epoch['source_sha256'], 'Receiver metadata source mismatch')
            position = tuple(float(epoch[k]) for k in POSITION)
            require(all(math.isfinite(v) for v in position), 'Nonfinite receiver position')
            receiver_positions.append(position); used_epochs.add(key)
        require(receiver_positions[0] == receiver_positions[1], 'Paired physical receiver positions differ')
        station = get('station_code')
        require(station and all(ord(c) < 128 and c.isalnum() for c in station) and len(station) <= 7, 'Station cannot be serialized losslessly in the legacy station field')
        identity = tuple(get(k) for k in IDENTITY) + receiver_positions[0]
        require(stations.get(station, identity) == identity, 'Legacy station field would collapse distinct channels or positions')
        stations[station] = identity
        obs_key = (tuple(sorted(sides)), station, 'P')
        require(obs_key not in seen_obs, 'Duplicate or reversed legacy pair/station/phase observation')
        seen_obs.add(obs_key)
        saved.update(dt_cc_export_status='exported', dt_cc_station=station, dt_cc_phase='P', dt_cc_origin_correction_s='0.0')
        grouped.setdefault(tuple(sides), []).append((saved, value, weight))
    lines = []
    for (i, j), observations in grouped.items():
        lines.append(f'# {i} {j} 0.0'); header = len(lines)
        for saved, value, weight in observations:
            lines.append(f"{saved['dt_cc_station']} {value:.17g} {weight:.17g} P")
            saved.update(dt_cc_line_number=len(lines), dt_cc_header_line_number=header)
    event_map = [dict(dt_cc_event_id=index + 1, original_event_index=index, event_resource_id=resource,
                      origin_resource_id=origin, mapping_basis='local original event index plus one')
                 for resource, (index, origin) in sorted(events.items(), key=lambda item: item[1][0])]
    station_epochs = [dict(by_epoch[key], dt_cc_station=by_epoch[key]['station_code']) for key in sorted(used_epochs, key=int)]
    return '\n'.join(lines) + ('\n' if lines else ''), mapped, event_map, station_epochs


def run(summary_path, review_path, epochs_path, output):
    summary_path, review_path, epochs_path, output = [p.resolve() for p in (summary_path, review_path, epochs_path, output)]
    for path in (summary_path, review_path, epochs_path, output):
        path.relative_to(ROOT)
    require(not output.exists(), 'Use a fresh output directory')
    summary = json.loads(summary_path.read_text()); review = json.loads(review_path.read_text())
    execution_path = summary_path.parent / 'execution.json'
    execution = json.loads(execution_path.read_text())
    require(execution['status'] == 'completed' and execution['summary_sha256'] == sha(summary_path) and
            execution['network_requests'] == 0, 'Require the terminal offline measurement execution ledger')
    require(summary['status'] == 'completed_identified_measurements' and summary['solver_observations_added'] == 0 and
            summary['original_catalog_values_changed'] is False and summary['dt_cc_exported'] is False, 'Measurements are not a completed isolated stage')
    require(review['status'] == 'passed' and review['measurements_summary_sha256'] == sha(summary_path), 'Require a hash-bound independent measurement review')
    pins = dict(summary['input_source_sha256'])
    require(pins.get(str(epochs_path.relative_to(ROOT))) == sha(epochs_path), 'Receiver epochs are not bound to measurements')
    for name, digest in summary['output_sha256'].items():
        path = (summary_path.parent / name).resolve(); path.relative_to(summary_path.parent)
        require(sha(path) == digest, 'Measurement output changed: ' + name)
        pins[str(path.relative_to(ROOT))] = digest
    for path in (summary_path, review_path, epochs_path, execution_path, Path(__file__).resolve()):
        pins[str(path.relative_to(ROOT))] = sha(path)
    for name, digest in pins.items():
        require(sha(ROOT / name) == digest, 'Pinned source/input changed: ' + name)
    rows = table(summary_path.parent / 'identified_measurements.csv.gz'); epochs = table(epochs_path)
    require(len(rows) == summary['retained_original_catalog_pairs'] and dict(collections.Counter(r['measurement_status'] for r in rows)) == summary['status_counts'], 'Full measurement roster differs')
    text, mapped, event_map, station_epochs = serialize(rows, epochs)
    output.mkdir(parents=True)
    (output / 'dt.cc').write_text(text)
    csv_save(output / 'dt.cc.identifiers.csv.gz', mapped, list(mapped[0]))
    csv_save(output / 'event_id_map.csv', event_map, list(event_map[0]))
    csv_save(output / 'receiver_epochs.csv.gz', station_epochs, list(epochs[0]) + ['dt_cc_station'])
    source = output / 'source'; source.mkdir(); shutil.copyfile(__file__, source / Path(__file__).name)
    require(table(output / 'dt.cc.identifiers.csv.gz') == [{k: str(v) for k, v in r.items()} for r in mapped], 'Identifier sidecar readback differs')
    for name, digest in pins.items():
        require(sha(ROOT / name) == digest, 'Input changed during export: ' + name)
    result = dict(status='completed_identified_dt_cc_export', created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        input_source_sha256=pins, retained_original_catalog_pairs=len(rows), exported_observations=sum(r['dt_cc_export_status'] == 'exported' for r in mapped),
        preserved_unexported_observations=sum(r['dt_cc_export_status'] != 'exported' for r in mapped),
        event_integer_mapping='Original nonnegative event index plus one; provider resource/origin IDs preserved in event_id_map.csv.',
        relative_weight='CC squared, not formal inverse variance. No solver row weighting is selected.',
        differential_convention='Travel time i minus travel time j; zero additional origin-time correction.',
        source_documentation='https://eqcorrscan.readthedocs.io/en/latest/_modules/eqcorrscan/utils/catalog_to_dd.html',
        numeric_serialization='17 significant digits preserve stored binary64 values; no new decimal rounding or measurement.',
        solver_observations_added=0, original_catalog_values_changed=False,
        limitations=['Legacy station field cannot carry full NSLC/epochs: keep both sidecars with dt.cc.',
                     'No station/channel collisions, duplicate pair/station/phase observations, or origin ambiguities are silently collapsed.',
                     'An exported measurement is not a calibrated timing uncertainty or validated tomography input.'],
        output_sha256={str(p.relative_to(output)): sha(p) for p in output.rglob('*') if p.is_file()})
    (output / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ('measurements-summary', 'measurements-review', 'epochs', 'output'):
        parser.add_argument('--' + flag, required=True, type=Path)
    args = parser.parse_args()
    result = run(args.measurements_summary, args.measurements_review, args.epochs, args.output)
    print(json.dumps({k: result[k] for k in ('status', 'retained_original_catalog_pairs', 'exported_observations')}))
