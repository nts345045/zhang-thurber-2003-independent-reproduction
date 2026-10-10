#!/usr/bin/env python3
"""Offline identified waveform measurements; no retrieval, dt.cc export or solver import."""
import argparse
import collections
import csv
import datetime as dt
from fractions import Fraction as Q
import gzip
import hashlib
import importlib.util
import io
import json
import math
from pathlib import Path
import shutil
import sys

import numpy as np
import obspy

import normalized_waveform_cc as method

ROOT = Path(__file__).resolve().parents[1]
CORE_SHA = '98bc3880882e9e117338931ce5c11d0d0b6863a929f2db045a72edb87645740e'
SPEC = ROOT / 'data/development/normalized_correlation_specification/README.md'
IDENTITY = ('network_code', 'station_code', 'location_code', 'channel_code',
            'channel_seed_id', 'channel_fdsn_source_id')
EPOCH = ('metadata_epoch_start', 'metadata_epoch_end')
POSITION = ('x', 'y', 'z', 'latitude_deg', 'longitude_deg', 'sensor_z_geoid_km')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path):
    return str(path.resolve().relative_to(ROOT))


def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def table(path):
    opener = gzip.open if path.suffix == '.gz' else open
    with opener(str(path), 'rt', newline='') as f:
        return list(csv.DictReader(f))


def compressed(path):
    return io.TextIOWrapper(gzip.GzipFile(filename='', fileobj=path.open('xb'),
                                        mode='wb', mtime=0), encoding='utf-8', newline='')


def clean(value):
    """Undefined diagnostic coefficients remain explicit JSON nulls."""
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items()}
    if isinstance(value, (np.ndarray, list, tuple)):
        return [clean(v) for v in value]
    if isinstance(value, np.generic):
        return clean(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def checked_inputs(samples_path, review_path, plan_path, events_path, out):
    pins = {}

    def pin(path, expected=None):
        path = path.resolve(); name = relative(path); digest = sha(path)
        require(expected is None or digest == expected, 'Pinned input changed: ' + name)
        require(name not in pins or pins[name] == digest, 'Input changed during read: ' + name)
        pins[name] = digest
        return path

    def load(path):
        return json.loads(pin(path).read_text())

    summary = load(samples_path); review = load(review_path); plan = load(plan_path)
    require(review['status'] == 'passed' and review['samples_summary_sha256'] == sha(samples_path),
            'A completed hash-bound independent sample review is required')
    require(summary['status'] == 'completed_requested_batches' and
            summary.get('all_reported_available_non_cmw1_windows_assessed', summary['all_reported_available_non_cmw1_windows_acquired']) is True and
            summary['started_or_cached_batches'] == summary['total_planned_batches'] == len(summary['results']) and
            summary['waveform_measurements_added'] == 0, 'Sample acquisition is incomplete or already transformed')
    require(summary['provider'] == 'https://service.ncedc.org/fdsnws/dataselect/1/query', 'Unexpected sample provider')
    require(plan['selections_changed'] is False, 'The original plan changed its cohort')
    for name, digest in summary['input_sha256'].items():
        pin(ROOT / name, digest)
    require(summary['input_sha256'].get(relative(plan_path)) == sha(plan_path), 'Sample provenance does not bind this plan')
    for name, digest in plan['input_sha256'].items():
        pin(ROOT / name, digest)
    for name, digest in plan['output_sha256'].items():
        path = (plan_path.parent / name).resolve(); path.relative_to(plan_path.parent.resolve())
        pin(path, digest)
    require(plan['input_sha256'].get(relative(events_path)) == sha(events_path), 'Plan does not bind reference origins')
    outputs = summary['output_sha256']
    require(len(outputs) == 1, 'Require one complete identified sample-pick table')
    name = next(iter(outputs)); picks_path = (samples_path.parent / name).resolve()
    picks_path.relative_to(samples_path.parent.resolve()); pin(picks_path, outputs[name])
    picks = table(picks_path); original = table(plan_path.parent / 'identified_picks.csv.gz')
    pairs = table(plan_path.parent / 'identified_catalog_differences.csv.gz')
    epochs = table(plan_path.parent / 'identified_used_epochs.csv.gz'); events = table(pin(events_path))
    require(len(picks) == len(original) == plan['retained_picks'] == summary['retained_original_picks'] and
            len(pairs) == plan['retained_catalog_differences'] == summary['retained_catalog_differences'], 'Full cohort counts differ')
    require(all(all(p[k] == v for k, v in old.items()) for old, p in zip(original, picks)), 'Original pick metadata or order changed')
    require(len({p['original_observation_index'] for p in pairs}) == len(pairs), 'Duplicate original catalog pair')
    by_pick = {p['pick_i_resource_id']: p for p in picks}
    by_epoch = {e['id']: e for e in epochs}; by_event = {e['id']: e for e in events}
    require(len(by_pick) == len(picks) and len(by_epoch) == len(epochs) and len(by_event) == len(events), 'Nonunique native keys')
    for p in picks:
        e, station = by_event[p['i']], by_epoch[p['station']]
        require(all(p[k] == station[k] for k in IDENTITY + EPOCH), 'Pick/receiver identity differs: ' + p['pick_i_resource_id'])
        require(p['channel_source_sha256'] == station['source_sha256'], 'Pick metadata source differs')
        for key in ('provider_dip_deg', 'orientation_status'):
            require(p[key] == station[key], 'Pick/epoch orientation differs')
        for key in ('event', 'origin'):
            require(p[key + '_i_resource_id'] == e[key + '_resource_id'], 'Pick/origin identity differs')
        travel = Q(obspy.UTCDateTime(p['pick_i_time_utc']).ns - obspy.UTCDateTime(e['reference_origin_time_utc']).ns, 10**9)
        require(float(p['value']) == float(travel), 'Catalog travel time differs from identified origin and pick')
        require(all(math.isfinite(float(station[k])) for k in POSITION), 'Nonfinite receiver position')
    for pair in pairs:
        require(pair['type'] == '1', 'Roster contains a non-catalog differential observation')
        side_picks = []
        for side in ('i', 'j'):
            p = by_pick[pair['pick_' + side + '_resource_id']]; side_picks.append(p)
            require(pair[side] == p['i'] and pair['station' if side == 'i' else 'station_j'] == p['station'], 'Pair native index mismatch')
            require(all(pair[k] == p[k] for k in IDENTITY), 'Pair common channel differs')
            for kind in ('event', 'origin', 'pick', 'arrival'):
                require(pair[kind + '_' + side + '_resource_id'] == p[kind + '_i_resource_id'], 'Pair resource identity differs')
            require(pair['pick_' + side + '_time_utc'] == p['pick_i_time_utc'], 'Pair pick time differs')
            for bound in ('start', 'end'):
                require(pair['metadata_epoch_' + ('j_' if side == 'j' else '') + bound] == p['metadata_epoch_' + bound], 'Pair native epoch differs')
            require(pair['channel_' + ('j_' if side == 'j' else '') + 'source_sha256'] == p['channel_source_sha256'], 'Pair metadata source differs')
        require(float(pair['value']) == float(side_picks[0]['value']) - float(side_picks[1]['value']), 'Catalog differential convention differs')
    decoder_path = samples_path.parent / 'source/acquire.py'; pin(decoder_path, summary['source_sha256'])
    sources = [Path(__file__).resolve(), ROOT / 'diagnostics/normalized_waveform_cc.py', SPEC, decoder_path]
    require(sha(sources[1]) == CORE_SHA, 'Reviewed correlation core changed')
    frozen = out / 'source'; frozen.mkdir()
    for path in sources:
        pin(path); shutil.copyfile(str(path), str(frozen / ('sample_decoder.py' if path == decoder_path else path.name)))
    spec = importlib.util.spec_from_file_location('frozen_sample_decoder', str(frozen / 'sample_decoder.py'))
    decoder = importlib.util.module_from_spec(spec); spec.loader.exec_module(decoder)
    windows = {}; missing = set()
    record_missing = summary.get('explicit_record_no_samples_mode', False)
    require(isinstance(record_missing, bool), 'Missing-sample mode must be explicit boolean')
    by_observation = {p['original_observation_index']: p for p in picks}
    require(len(by_observation) == len(picks), 'Duplicate original pick row')
    for number, batch in enumerate(summary['results']):
        require(batch['batch'] == number, 'Acquisition batch order differs')
        raw = (samples_path.parent / batch['raw_file']).resolve(); raw.relative_to(samples_path.parent.resolve())
        pin(raw, batch['raw_sha256'])
        decoded_path = (samples_path.parent / batch['decoded_file']).resolve(); decoded_path.relative_to(samples_path.parent.resolve())
        pin(decoded_path, batch['decoded_sha256']); saved = load(decoded_path)
        meta = load(raw.with_name(raw.name + '.provenance.json')); ids = load(raw.with_name(raw.name + '.identifiers.json'))
        request = pin(raw.with_name(raw.name + '.request.txt')); request_ids = load(request.with_name(request.name + '.identifiers.json'))
        require(meta['http_status'] == 200 and meta['method'] == 'POST' and meta['request_url'] == summary['provider'] and
                meta['sha256'] == ids['source_sha256'] == sha(raw) and meta['byte_count'] == raw.stat().st_size and
                meta['acquisition_source_sha256'] in set(pins.values()) and meta['final_url'] == summary['provider'], 'Raw sample provenance differs')
        require(meta['request_sha256'] == request_ids['request_sha256'] == sha(request) and
                ids['request_context'] == request_ids['request_context'] and
                all(summary['input_sha256'].get(k) == v for k, v in ids['request_context']['input_sha256'].items()), 'Waveform request provenance differs')
        native = ids['request_context']['native_picks']
        require(len(native) == batch['native_window_count'] and all(all(by_observation[p['original_observation_index']][k] == v for k, v in p.items()) for p in native), 'Waveform native context differs')
        expected = ''.join(' '.join([p['network_code'], p['station_code'], p['location_code'] or '--', p['channel_code'],
                                    p['request_start_utc'].rstrip('Z'), p['request_end_utc'].rstrip('Z')]) + '\n' for p in native)
        require(request.read_text() == expected, 'Exact waveform request changed')
        decoded = decoder.decode(raw.read_bytes(), native, record_no_samples=True) if record_missing else decoder.decode(raw.read_bytes(), native)
        require(decoded == saved, 'Independent raw re-decode differs from saved windows')
        stream = obspy.read(io.BytesIO(raw.read_bytes()), format='MSEED', details=True)
        for window in saved['windows']:
            n = window['original_observation_index']; p = by_observation[n]
            require(n not in windows and p['waveform_status'] == 'decoded_native_samples', 'Duplicate/unexpected decoded window')
            require(p['waveform_raw_file'] == relative(raw) and p['waveform_raw_sha256'] == sha(raw), 'Pick raw source mismatch')
            for k, v in window.items():
                if k != 'native_pick':
                    require(p[k] == str(v), 'Pick decoded field differs: ' + k)
            trace = stream[window['trace_index']]; values = trace.data[window['first_sample_index']:window['stop_sample_index_exclusive']]
            require(trace.id == p['channel_seed_id'] and len(values) == window['sample_count'], 'Decoded sample identity/length mismatch')
            require(hashlib.sha256(values.astype(values.dtype.newbyteorder('<')).tobytes()).hexdigest() == window['window_samples_sha256'], 'Decoded sample hash mismatch')
            windows[n] = values.copy()
        for absent in saved.get('missing_windows', []):
            n = absent['original_observation_index']; p = by_observation[n]
            require(record_missing and absent['status'] == p['waveform_status'] == 'provider_returned_no_samples', 'Unapproved missing-sample status')
            require(n not in missing and n not in windows and absent['native_pick'] in native, 'Missing-window native identity differs')
            require(p['waveform_raw_file'] == relative(raw) and p['waveform_raw_sha256'] == sha(raw), 'Missing-window raw provenance differs')
            missing.add(n)
    require(len(windows) == summary['decoded_native_windows'] and
            set(windows) == {p['original_observation_index'] for p in picks if p['waveform_status'] == 'decoded_native_samples'}, 'Decoded full-window inventory differs')
    selected = {p['original_observation_index'] for p in picks if p['station_code'] != 'CMW1' and p['availability_status'] == 'provider_reports_covering_span'}
    require(not set(windows).intersection(missing) and set(windows).union(missing) == selected and
            len(selected) == summary['selected_reported_available_non_cmw1_windows'], 'Reported-available original windows were omitted from complete assessment')
    require(summary['all_reported_available_non_cmw1_windows_acquired'] == (len(windows) == len(selected)), 'Acquired flag differs from actual sample inventory')
    if record_missing:
        require(summary['assessed_native_windows'] == len(selected) and summary['provider_returned_no_sample_windows'] == len(missing), 'Assessed/missing counts differ')
    return pins, summary, picks, pairs, by_pick, by_epoch, windows


def pair_result(pair, by_pick, epochs, windows):
    p, q = [by_pick[pair['pick_' + side + '_resource_id']] for side in ('i', 'j')]
    a, b = epochs[p['station']], epochs[q['station']]
    reasons = []
    if any(float(a[k]) != float(b[k]) for k in POSITION):
        reasons.append('different_reported_receiver_position')
    for side, pick in (('i', p), ('j', q)):
        if pick['waveform_status'] != 'decoded_native_samples':
            reasons.append('waveform_' + side + ':' + pick['waveform_status'])
        if pick['orientation_status'] != 'provider-declared vertical' or not pick['provider_dip_deg'] or abs(float(pick['provider_dip_deg'])) != 90:
            reasons.append('orientation_' + side + ':' + pick['orientation_status'])
        if pick['waveform_status'] == 'decoded_native_samples' and float(pick['sample_rate_hz']) != 100:
            reasons.append('unsupported_native_sample_rate_' + side)
    if reasons:
        return dict(status='not_attempted', ineligibility_reasons=reasons), p, q
    offsets = []
    for pick in (p, q):
        start = Q(pick['first_sample_unix_ns_rational'])
        require(start.denominator == 1, '100 Hz sample start is not an integer nanosecond')
        offsets.append(int(start) - obspy.UTCDateTime(pick['pick_i_time_utc']).ns)
    result = method.measure(windows[p['original_observation_index']], offsets[0],
                            windows[q['original_observation_index']], offsets[1], float(pair['value']))
    result.update(sample_i_start_from_own_pick_ns=offsets[0], sample_j_start_from_own_pick_ns=offsets[1],
                  ineligibility_reasons=[])
    return result, p, q


def run(samples, review, plan, events, output):
    paths = [p.resolve() for p in (samples, review, plan, events, output)]
    samples, review, plan, events, output = paths
    for p in paths:
        p.relative_to(ROOT)
    require(all(output != p and output not in p.parents and p.parent not in output.parents for p in paths[:-1]), 'Output overlaps input evidence')
    output.mkdir(parents=True, exist_ok=False)
    ledger = dict(status='validating_inputs', started_utc=utc(), network_requests=0,
                  command=[sys.executable, 'diagnostics/run_native_waveform_cc.py', '--samples-summary', relative(samples),
                           '--samples-review', relative(review), '--plan', relative(plan), '--events', relative(events), '--output', relative(output)])
    save(output / 'execution.json', ledger)
    try:
        require(np.__version__ == '2.4.6' and obspy.__version__ == '1.5.1', 'Use the pinned waveform environment')
        pins, acquisition, picks, pairs, by_pick, epochs, windows = checked_inputs(samples, review, plan, events, output)
        ledger['status'] = 'measuring'; save(output / 'execution.json', ledger)
        counts = collections.Counter(); attempted = 0; sample_digest = sha(samples)
        csv_path = output / 'identified_measurements.csv.gz'; details_path = output / 'attempted_diagnostics.jsonl.gz'
        with compressed(csv_path) as f, compressed(details_path) as details:
            writer = None
            for pair in pairs:
                result, p, q = pair_result(pair, by_pick, epochs, windows)
                measured = result['status'] != 'not_attempted'
                measurement_id = 'local:native-cc:' + sample_digest[:16] + ':' + pair['original_observation_index']
                row = {'original_catalog_' + k: v for k, v in pair.items()}
                row.update(measurement_id=measurement_id, measurement_status=result['status'], cc_attempted=int(measured),
                    cc_ineligibility_reasons_json=json.dumps(result['ineligibility_reasons']),
                    dt_cc_i_minus_j_s=result.get('dt_cc_i_minus_j_s'),
                    cc_candidate_dt_i_minus_j_s=result.get('candidate_dt_cc_i_minus_j_s'),
                    cc_delay_j_minus_i_s=result.get('delay_j_minus_i_s'), maximum_cc=result.get('maximum_cc'), maximum_cc_squared=result.get('maximum_cc_squared'),
                    cc_relative_weight_squared=result.get('maximum_cc_squared') if result['status'] == 'accepted_discrete_measurement' else None,
                    cc_formal_timing_uncertainty_s=None, cc_sample_spacing_s=.01 if measured else None,
                    cc_passing_coherence_bins=result.get('passing_bins'), cc_evaluation_coherence_bins=result.get('evaluation_bins'),
                    diagnostics_jsonl_row=attempted if measured else None)
                for side, pick in (('i', p), ('j', q)):
                    for key in ('original_observation_index', 'waveform_status', 'waveform_raw_file', 'waveform_raw_sha256',
                                'window_samples_sha256', 'trace_index', 'first_sample_index', 'stop_sample_index_exclusive',
                                'first_sample_unix_ns_rational', 'sample_rate_hz', 'orientation_status', 'provider_dip_deg', 'response_status'):
                        row['waveform_' + side + '_' + key] = pick[key]
                if writer is None:
                    writer = csv.DictWriter(f, fieldnames=list(row), lineterminator='\n'); writer.writeheader()
                writer.writerow(row); counts[result['status']] += 1
                if measured:
                    record = dict(measurement_id=measurement_id, original_catalog=dict(pair), waveform_i=dict(p), waveform_j=dict(q),
                                  receiver_epoch_i=dict(epochs[p['station']]), receiver_epoch_j=dict(epochs[q['station']]), diagnostics=clean(result))
                    details.write(json.dumps(record, separators=(',', ':'), allow_nan=False) + '\n'); attempted += 1
        saved = table(csv_path)
        require(len(saved) == len(pairs) and all(all(row['original_catalog_' + k] == v for k, v in old.items()) for row, old in zip(saved, pairs)), 'Full original pair table readback differs')
        with gzip.open(str(details_path), 'rt') as f:
            require(sum(1 for line in f) == attempted, 'Attempted diagnostic inventory differs')
        for name, digest in pins.items():
            require(sha(ROOT / name) == digest, 'Input/source changed during measurements: ' + name)
        summary = dict(status='completed_identified_measurements', scope=__doc__, input_source_sha256=pins,
            samples_summary_sha256=sha(samples), samples_review_sha256=sha(review), retained_original_picks=len(picks),
            retained_original_catalog_pairs=len(pairs), attempted_pairs=attempted, status_counts=dict(counts),
            original_catalog_values_changed=False, solver_observations_added=0, dt_cc_exported=False,
            weights='Accepted CC squared is a declared relative weight, not inverse variance and not a solver row multiplier.',
            null_diagnostic_values='Undefined/nonfinite diagnostic array entries are stored as JSON null; statuses retain their rejection reason.',
            versions=dict(python=sys.version.split()[0], numpy=np.__version__, obspy=obspy.__version__),
            output_sha256={relative(p).replace(relative(output) + '/', '', 1):sha(p) for p in output.rglob('*') if p.is_file() and p.name != 'execution.json'},
            limitations=['Native 100 Hz, provider-declared vertical components and the fixed documented discrete method only.',
                'Missing samples/orientations and mismatched receiver positions remain identified unattempted rows; no study exclusion is inferred.',
                'Empirical correlation/coherence acceptance does not establish formal timing uncertainty or instrument phase equivalence.',
                'The next dt.cc export requires explicit event-resource integer mapping and collision checks with a full native sidecar; no solver import is performed.'])
        save(output / 'summary.json', summary)
        ledger.update(status='completed', finished_utc=utc(), summary_sha256=sha(output / 'summary.json')); save(output / 'execution.json', ledger)
        return summary
    except BaseException as error:
        ledger.update(status='failed', finished_utc=utc(), error_type=type(error).__name__, error=str(error))
        save(output / 'execution.json', ledger)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ('samples-summary', 'samples-review', 'plan', 'events', 'output'):
        parser.add_argument('--' + flag, type=Path, required=True)
    args = parser.parse_args()
    result = run(args.samples_summary, args.samples_review, args.plan, args.events, args.output)
    print(json.dumps({k: result[k] for k in ('status', 'retained_original_catalog_pairs', 'attempted_pairs', 'status_counts')}, indent=2))


if __name__ == '__main__':
    main()
