#!/usr/bin/env python3
"""Offline readback of the preserved first-batch sample-support failure."""
import csv
from fractions import Fraction as Q
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path

import obspy

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
RAW = HERE / 'raw/dataselect_000.response'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def ceiling(value):
    return -(-value.numerator // value.denominator)


def main():
    output = HERE / 'batch_000_offline_diagnosis.json'
    require(not output.exists(), 'Preserve the existing diagnosis')
    paths = [Path(__file__), RAW, RAW.with_name(RAW.name + '.provenance.json'),
        RAW.with_name(RAW.name + '.identifiers.json'),
        RAW.with_name(RAW.name + '.request.txt'),
        RAW.with_name(RAW.name + '.request.txt.identifiers.json'),
        RAW.with_name(RAW.name + '.decode_failure.json'),
        HERE / 'source/acquire.py', HERE / 'acquisition_execution.json',
        HERE.parent / 'cohort_cc_002/identified_pair_availability.csv.gz']
    pins = {str(p.relative_to(ROOT)):sha(p) for p in paths}
    metadata = json.loads(paths[2].read_text())
    identity = json.loads(paths[3].read_text())
    native = identity['request_context']['native_picks']
    require(metadata['http_status'] == 200 and metadata['sha256'] == sha(RAW) ==
        identity['source_sha256'], 'Saved response provenance differs')
    require(sha(paths[4]) == metadata['request_sha256'], 'Saved request differs')
    request = ''.join(' '.join([p['network_code'], p['station_code'],
        p['location_code'] or '--', p['channel_code'],
        p['request_start_utc'].rstrip('Z'), p['request_end_utc'].rstrip('Z')]) + '\n'
        for p in native).encode()
    require(request == paths[4].read_bytes(), 'Native rows do not reproduce the exact request')
    require(sha(HERE / 'source/acquire.py') == metadata['acquisition_source_sha256'],
        'Frozen decoder does not match the request source')
    stream = obspy.read(io.BytesIO(RAW.read_bytes()), format='MSEED', details=True)
    records, complete, missing = [], [], []
    for batch_row, pick in enumerate(native):
        a, b = [obspy.UTCDateTime(pick[k]).ns for k in ('request_start_utc', 'request_end_utc')]
        eligible, intersections = [], []
        for n, trace in enumerate(stream):
            if trace.id != pick['channel_seed_id']:
                continue
            rate = Q(str(float(trace.stats.sampling_rate)))
            first = ceiling(Q(a - trace.stats.starttime.ns) * rate / 10**9)
            stop = ceiling(Q(b - trace.stats.starttime.ns) * rate / 10**9)
            if 0 <= first < stop <= len(trace):
                eligible.append(n)
            left, right = max(0, first), min(len(trace), stop)
            if left < right:
                intersections.append(dict(trace_index=n, first_sample_index=left,
                    stop_sample_index_exclusive=right, intersecting_sample_count=right-left))
        record = dict(batch_row=batch_row, native_pick=pick,
            complete_trace_indices=eligible, returned_sample_intersections=intersections)
        if len(eligible) == 1:
            record['status'] = 'one_complete_trace_pending_original_decoder_checks'
            complete.append(pick)
        elif not intersections:
            record['status'] = 'no_returned_sample_in_requested_window'
            missing.append(pick)
        else:
            record['status'] = 'partial_or_ambiguous_returned_support'
        if len(eligible) != 1:
            source = ROOT / pick['availability_response_file']
            require(sha(source) == pick['availability_response_sha256'], 'Availability raw changed')
            pins[str(source.relative_to(ROOT))] = sha(source)
            data = json.loads(source.read_text())
            record['reported_availability_records'] = [dict(provider_record_index=n,
                provider_record=data['datasources'][n])
                for n in json.loads(pick['availability_provider_record_indices'])]
        records.append(record)
    # This checks the 96 returned windows with the unchanged decoder; it does
    # not authorize excluding the four omitted windows or accepting the batch.
    spec = importlib.util.spec_from_file_location('frozen_acquire', HERE / 'source/acquire.py')
    decoder = importlib.util.module_from_spec(spec); spec.loader.exec_module(decoder)
    decoded = decoder.decode(RAW.read_bytes(), complete)
    require(len(decoded['windows']) == len(complete), 'Complete-window readback differs')
    for record in records:
        if record['status'] == 'one_complete_trace_pending_original_decoder_checks':
            record['status'] = 'complete_native_window_passed_unchanged_decoder'
    missing_ids = {p['pick_i_resource_id'] for p in missing}
    affected = []
    with gzip.open(str(paths[-1]), 'rt', newline='') as f:
        all_pairs = list(csv.DictReader(f))
    require(len(all_pairs) == 44718, 'Original pair roster differs')
    for pair in all_pairs:
        sides = [side for side in ('i', 'j') if pair['pick_' + side + '_resource_id'] in missing_ids]
        if sides:
            affected.append(dict(native_pair=pair, missing_pick_sides=sides))
    for name, digest in pins.items():
        require(sha(ROOT / name) == digest, 'Input changed during offline diagnosis: ' + name)
    result = dict(status='offline_failure_characterization_complete',
        scope='Read-only saved-response diagnosis; no retrieval, waveform measurement, merging, substitution, or exclusion',
        input_sha256=pins, requested_windows=len(native), returned_traces=len(stream),
        complete_native_windows=len(complete), windows_with_no_returned_samples=len(missing),
        partial_or_ambiguous_windows=sum(r['status'] == 'partial_or_ambiguous_returned_support' for r in records),
        all_complete_windows_pass_unchanged_decoder=True, native_windows=records,
        complete_window_decoder_readback=decoded,
        original_catalog_pair_count=len(all_pairs), affected_catalog_pair_count=len(affected),
        affected_catalog_pairs_with_both_spans_reported=sum(p['native_pair']['both_picks_have_reported_span'] == '1' for p in affected),
        affected_catalog_pairs=affected,
        interpretation='Availability reports covering spans but this bulk dataselect response omits all samples for four exact requested windows. The omission mechanism and historical archive coverage remain unresolved.',
        continuation='All further requests and waveform measurements remain paused for review of this concrete discrepancy')
    with output.open('x') as f:
        json.dump(result, f, indent=2, allow_nan=False); f.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k in ('requested_windows', 'returned_traces',
        'complete_native_windows', 'windows_with_no_returned_samples', 'partial_or_ambiguous_windows',
        'affected_catalog_pair_count', 'affected_catalog_pairs_with_both_spans_reported')}, sort_keys=True))


if __name__ == '__main__':
    main()
