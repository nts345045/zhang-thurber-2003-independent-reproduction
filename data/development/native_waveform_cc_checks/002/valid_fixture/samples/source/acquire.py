#!/usr/bin/env python3
"""Retrieve reviewed, reported-available native windows; never measure a delay."""
import argparse
import csv
import datetime as dt
from fractions import Fraction as Q
import gzip
import hashlib
import io
import json
import math
import os
from pathlib import Path
import platform

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
INVENTORY = HERE.parent / 'cohort_cc_002'
URL = 'https://service.ncedc.org/fdsnws/dataselect/1/query'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    with path.open('x') as f:
        json.dump(value, f, indent=2, allow_nan=False); f.write('\n')


def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def environment():
    cache = ROOT / 'tmp/waveform_cache'
    for name, directory in [('MPLCONFIGDIR', 'mpl'), ('XDG_CACHE_HOME', 'xdg'), ('TMPDIR', 'tmp')]:
        path = cache / directory; path.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault(name, str(path))
    import numpy as np
    import obspy
    require(obspy.__version__ == '1.5.1' and np.__version__ == '2.4.6', 'Use the pinned project ObsPy environment')
    return dict(python=platform.python_version(), obspy=obspy.__version__, numpy=np.__version__)


def ceiling(value):
    return -(-value.numerator // value.denominator)


def decode(raw, native, record_no_samples=False):
    """Standard miniSEED decoding, followed by exact native-grid sample indexing."""
    import numpy as np
    import obspy
    stream = obspy.read(io.BytesIO(raw), format='MSEED', details=True)
    channels = {p['channel_seed_id'] for p in native}
    traces = []
    for n, trace in enumerate(stream):
        rate = float(trace.stats.sampling_rate)
        require(trace.id in channels and math.isfinite(rate) and rate > 0, 'Unexpected waveform channel or sample rate')
        require(not np.ma.isMaskedArray(trace.data) and len(trace.data) and np.isfinite(trace.data).all(), 'Masked, empty or nonfinite decoded samples')
        matched = [p for p in native if p['channel_seed_id'] == trace.id and
            trace.stats.starttime < obspy.UTCDateTime(p['request_end_utc']) and
            trace.stats.endtime >= obspy.UTCDateTime(p['request_start_utc'])]
        require(matched, 'Returned trace cannot be associated with a requested native window')
        traces.append(dict(trace_index=n, channel_seed_id=trace.id,
            channel_fdsn_source_id=matched[0]['channel_fdsn_source_id'],
            identifier_basis='FDSN source ID derived from verified provider SEED codes',
            provider_waveform_resource_id=None, first_sample_utc=str(trace.stats.starttime),
            first_sample_unix_ns=trace.stats.starttime.ns, last_sample_utc=str(trace.stats.endtime),
            sample_rate_hz=rate, sample_count=len(trace.data), data_type=str(trace.data.dtype),
            miniseed_quality=trace.stats.mseed.get('dataquality'), miniseed_encoding=trace.stats.mseed.get('encoding'),
            miniseed_record_length_bytes=trace.stats.mseed.get('record_length'),
            miniseed_record_count=trace.stats.mseed.get('number_of_records'),
            miniseed_byte_order=trace.stats.mseed.get('byteorder'),
            miniseed_timing_quality=trace.stats.mseed.get('blkt1001', {}).get('timing_quality'),
            miniseed_calibration_type=trace.stats.mseed.get('calibration_type'),
            decoded_samples_sha256=hashlib.sha256(trace.data.astype(trace.data.dtype.newbyteorder('<')).tobytes()).hexdigest(),
            decoded_sample_byte_order='little', native_pick_rows=[p['original_observation_index'] for p in matched]))
    windows, missing_windows = [], []
    for pick in native:
        a, b = (obspy.UTCDateTime(pick[k]).ns for k in ('request_start_utc', 'request_end_utc'))
        lo = obspy.UTCDateTime(pick['metadata_epoch_start']).ns
        hi = obspy.UTCDateTime(pick['metadata_epoch_end']).ns if pick['metadata_epoch_end'] else None
        require(lo <= a < b and (hi is None or b <= hi), 'Requested native window crosses its metadata epoch')
        eligible, intersections = [], []
        for n, trace in enumerate(stream):
            if trace.id != pick['channel_seed_id']:
                continue
            rate = Q(str(float(trace.stats.sampling_rate))); start = trace.stats.starttime.ns
            first = ceiling(Q(a - start) * rate / 10**9)
            stop = ceiling(Q(b - start) * rate / 10**9)
            if max(0, first) < min(len(trace.data), stop):
                intersections.append(n)
            if 0 <= first < stop <= len(trace.data):
                quality = trace.stats.mseed.get('dataquality')
                require(float(rate) in json.loads(pick['availability_sample_rates_hz']) and
                    quality in json.loads(pick['availability_quality_codes']), 'Decoded rate/quality differs from reported availability')
                eligible.append((n, first, stop, rate))
        if record_no_samples and not eligible and not intersections:
            missing_windows.append(dict(status='provider_returned_no_samples',
                original_observation_index=pick['original_observation_index'], native_pick=dict(pick)))
            continue
        require(len(eligible) == 1, 'Native window lacks unique continuous sample support; do not merge gaps or select overlapping qualities')
        n, first, stop, rate = eligible[0]; trace = stream[n]
        first_ns = Q(trace.stats.starttime.ns) + first * Q(10**9) / rate
        last_ns = Q(trace.stats.starttime.ns) + (stop - 1) * Q(10**9) / rate
        require(Q(a) <= first_ns < Q(a) + Q(10**9) / rate and Q(b) - Q(10**9) / rate <= last_ns < Q(b), 'Native samples do not cover the half-open requested window')
        # Any other native sample anywhere in the requested half-open interval
        # makes the grid/quality ambiguous, including its sub-sample edge margins.
        for j, other in enumerate(stream):
            if j != n and other.id == trace.id:
                other_rate = Q(str(float(other.stats.sampling_rate)))
                left = max(0, ceiling(Q(a - other.stats.starttime.ns) * other_rate / 10**9))
                right = min(len(other.data), ceiling(Q(b - other.stats.starttime.ns) * other_rate / 10**9))
                require(left >= right,
                    'Overlapping returned traces require explicit review')
        values = trace.data[first:stop]
        windows.append(dict(original_observation_index=pick['original_observation_index'],
            native_pick=dict(pick),
            trace_index=n, first_sample_index=first, stop_sample_index_exclusive=stop,
            sample_count=stop-first, sample_rate_hz=float(rate), miniseed_quality=trace.stats.mseed.get('dataquality'),
            first_sample_unix_ns_rational=str(first_ns), last_sample_unix_ns_rational=str(last_ns),
            window_samples_sha256=hashlib.sha256(values.astype(values.dtype.newbyteorder('<')).tobytes()).hexdigest(),
            decoded_sample_byte_order='little', no_response_correction=True))
    return dict(traces=traces, windows=windows, missing_windows=missing_windows,
        scope='Decoded native sample identity and continuity only; no correlation, calibration or waveform-quality acceptance')


def request_batch(number, native, fetch, input_hashes, record_no_samples):
    import requests
    stem = 'dataselect_{:03d}'.format(number); raw = HERE / 'raw' / (stem + '.response')
    raw.parent.mkdir(exist_ok=True)
    body = ''.join(' '.join([p['network_code'], p['station_code'], p['location_code'] or '--', p['channel_code'],
        p['request_start_utc'].rstrip('Z'), p['request_end_utc'].rstrip('Z')]) + '\n' for p in native).encode()
    body_sha = hashlib.sha256(body).hexdigest()
    context = dict(native_picks=native, input_sha256=input_hashes,
        provider_waveform_resource_id=None,
        resource_identifier_basis='Original provider event/origin/pick/association IDs preserved; FDSN IDs derived from exact SEED codes; missing waveform public IDs remain absent',
        scope='Reported-available non-CMW1 original windows only; catalog cohort and missing/paused rows remain unchanged')
    request = raw.with_name(raw.name + '.request.txt'); meta_path = raw.with_name(raw.name + '.provenance.json')
    ids_path = raw.with_name(raw.name + '.identifiers.json'); parsed_path = raw.with_name(raw.name + '.decoded.json')
    if raw.exists():
        meta = json.loads(meta_path.read_text()); ids = json.loads(ids_path.read_text())
        require(sha(raw) == meta['sha256'] == ids['source_sha256'] and request.read_bytes() == body and
            meta['request_sha256'] == body_sha and ids['request_context'] == context, 'Cached raw/request/native identity changed')
    else:
        require(fetch, 'Uncached waveform request; --fetch required')
        with request.open('xb') as f:
            f.write(body)
        save(request.with_name(request.name + '.identifiers.json'), dict(source_url=URL, request_sha256=body_sha, request_context=context))
        started = utc()
        try:
            response = requests.post(URL, data=body, headers={'Content-Type': 'text/plain'}, timeout=120)
        except requests.RequestException as error:
            save(raw.with_name(raw.name + '.failure.json'), dict(status='stopped_for_access_clarification', requested_utc=started,
                request_sha256=body_sha, source_url=URL, error_type=type(error).__name__, error=str(error)))
            raise
        with raw.open('xb') as f:
            f.write(response.content)
        meta = dict(request_url=URL, final_url=response.url, method='POST', requested_utc=started, retrieved_utc=utc(),
            request_sha256=body_sha, http_status=response.status_code, content_type=response.headers.get('Content-Type'),
            byte_count=len(response.content), sha256=sha(raw), acquisition_source_sha256=sha(Path(__file__)),
            response_kind='waveform_response_pending_decode' if response.status_code == 200 else 'http_error_or_no_data')
        save(meta_path, meta); save(ids_path, dict(source_url=URL, source_sha256=sha(raw), request_context=context))
    require(meta['http_status'] == 200, 'Authoritative waveform request did not return data; stop for clarification')
    try:
        decoded = decode(raw.read_bytes(), native, record_no_samples=record_no_samples)
    except Exception as error:
        failed = raw.with_name(raw.name + '.decode_failure.json')
        if not failed.exists():
            save(failed, dict(status='stopped_for_sample_identity_or_coverage_review', source_sha256=sha(raw), error_type=type(error).__name__, error=str(error)))
        raise
    if parsed_path.exists():
        require(json.loads(parsed_path.read_text()) == decoded, 'Cached decoded identity differs')
    else:
        save(parsed_path, decoded)
    return dict(batch=number, raw_file=str(raw.relative_to(HERE)), raw_sha256=sha(raw),
        decoded_file=str(parsed_path.relative_to(HERE)), decoded_sha256=sha(parsed_path), native_window_count=len(native)), decoded


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fetch', action='store_true')
    parser.add_argument('--record-no-samples', action='store_true',
        help='Retain an explicit missing status only when no returned sample intersects the requested window')
    parser.add_argument('--batches', type=int, default=1)
    parser.add_argument('--summary', required=True)
    args = parser.parse_args()
    require(args.batches > 0 and Path(args.summary).name == args.summary and args.summary.endswith('.json'), 'Use a fresh local summary filename')
    require(not (HERE / args.summary).exists(), 'Summary already exists')
    versions = environment()
    manifest = INVENTORY / 'inventory_summary.json'; review = INVENTORY / 'independent_inventory_review.json'
    summary = json.loads(manifest.read_text()); audit = json.loads(review.read_text())
    require(summary['status'] == 'complete_inventory_native_readback_passed' and audit['status'] == 'passed' and
        audit['inventory_summary_sha256'] == sha(manifest), 'Completed independent inventory review is required before requests')
    pinned = {str(manifest.relative_to(ROOT)):sha(manifest), str(review.relative_to(ROOT)):sha(review)}
    for name, digest in summary['input_sha256'].items():
        require(sha(ROOT / name) == digest, 'Inventory input changed: ' + name); pinned[name] = digest
    for name, digest in summary['output_sha256'].items():
        path = INVENTORY / name; require(sha(path) == digest, 'Inventory output changed'); pinned[str(path.relative_to(ROOT))] = digest
    with gzip.open(str(INVENTORY / 'identified_pick_availability.csv.gz'), 'rt', newline='') as f:
        picks = list(csv.DictReader(f))
    require(len(picks) == 14262, 'Original pick support changed')
    selected = [p for p in picks if p['station_code'] != 'CMW1' and p['availability_status'] == 'provider_reports_covering_span']
    require(len({p['original_observation_index'] for p in selected}) == len(selected), 'Selected native indices repeat')
    reuse_path = HERE / 'cached_first_response.json'
    reuse = json.loads(reuse_path.read_text())
    require(reuse['status'] == 'byte_identical_cached_response' and
        str((HERE / 'raw/dataselect_000.response').relative_to(ROOT)) in reuse['input_sha256'],
        'The original first response must be reused without another request')
    reuse_pins = dict(reuse['input_sha256']); reuse_pins[str(reuse_path.relative_to(ROOT))] = sha(reuse_path)
    for name, digest in reuse_pins.items():
        require(sha(ROOT / name) == digest, 'Cached first-response reuse changed: ' + name)
    source = HERE / 'source/acquire.py'; source.parent.mkdir(exist_ok=True)
    if source.exists():
        require(source.read_bytes() == Path(__file__).read_bytes(), 'Acquisition source changed; preserve this attempt and use a new variant')
    else:
        source.write_bytes(Path(__file__).read_bytes())
    total = (len(selected) + 99) // 100; results = []; windows = {}; missing = {}
    for n in range(min(args.batches, total)):
        requested = selected[100*n:100*(n+1)]
        result, decoded = request_batch(n, requested, args.fetch, pinned, args.record_no_samples)
        results.append(result)
        for row in decoded['windows']:
            windows[row['original_observation_index']] = dict({k:v for k,v in row.items() if k != 'native_pick'},
                waveform_raw_file=str((HERE / result['raw_file']).relative_to(ROOT)),
                waveform_raw_sha256=result['raw_sha256'])
        for row in decoded['missing_windows']:
            missing[row['original_observation_index']] = dict(waveform_status=row['status'],
                waveform_raw_file=str((HERE / result['raw_file']).relative_to(ROOT)),
                waveform_raw_sha256=result['raw_sha256'])
        require(not set(windows).intersection(missing), 'Decoded and absent native identities overlap')
        require({p['original_observation_index'] for p in requested} ==
            {r['original_observation_index'] for key in ('windows', 'missing_windows') for r in decoded[key]},
            'Decoded and absent rows do not preserve the full batch')
        print('batch', n, 'native_windows', result['native_window_count'],
            'decoded', len(decoded['windows']), 'no_returned_samples', len(decoded['missing_windows']), flush=True)
    fields = ['waveform_status','trace_index','first_sample_index','stop_sample_index_exclusive','sample_count','sample_rate_hz',
        'miniseed_quality','first_sample_unix_ns_rational','last_sample_unix_ns_rational','window_samples_sha256',
        'decoded_sample_byte_order','no_response_correction','waveform_raw_file','waveform_raw_sha256']
    require(not set(fields).intersection(picks[0]), 'New waveform fields would overwrite native metadata')
    for pick in picks:
        for name in fields:
            pick[name] = ''
        n = pick['original_observation_index']
        pick['waveform_status'] = ('paused_CMW1_access_clarification' if pick['station_code'] == 'CMW1' else
            'not_requested_no_reported_span' if pick['availability_status'] != 'provider_reports_covering_span' else 'pending_waveform_request')
        if n in windows:
            pick.update(windows[n]); pick['waveform_status'] = 'decoded_native_samples'
        elif n in missing:
            pick.update(missing[n])
    pinned.update(reuse_pins)
    for name, digest in pinned.items():
        require(sha(ROOT / name) == digest, 'Input changed during acquisition: ' + name)
    output = HERE / (Path(args.summary).stem + '.picks.csv.gz')
    with output.open('xb') as raw, gzip.GzipFile(filename='', fileobj=raw, mode='wb', mtime=0) as compressed:
        with io.TextIOWrapper(compressed, encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(picks[0]), lineterminator='\n'); writer.writeheader(); writer.writerows(picks)
    with gzip.open(str(output), 'rt', newline='') as f:
        require(list(csv.DictReader(f)) == [{k:str(v) for k,v in p.items()} for p in picks], 'Saved full native table readback mismatch')
    save(HERE / args.summary, dict(status='completed_requested_batches', started_or_cached_batches=len(results), total_planned_batches=total,
        all_reported_available_non_cmw1_windows_acquired=len(windows) == len(selected), retained_original_picks=len(picks),
        all_reported_available_non_cmw1_windows_assessed=len(windows)+len(missing) == len(selected),
        assessed_native_windows=len(windows)+len(missing), provider_returned_no_sample_windows=len(missing),
        explicit_record_no_samples_mode=args.record_no_samples,
        retained_catalog_differences=summary['retained_catalog_differences'], selected_reported_available_non_cmw1_windows=len(selected),
        decoded_native_windows=len(windows), waveform_measurements_added=0, provider=URL, versions=versions,
        source_sha256=sha(Path(__file__)), input_sha256=pinned, results=results,
        output_sha256={output.name:sha(output)},
        limitations=['Reported availability and sample identity do not establish correlation quality.',
            'A provider_returned_no_samples row records zero samples in this response, not historical archive absence.',
            'CMW1 samples and alternative-source retrieval remain paused; no catalog record is removed.',
            'Response calibration is not required; absent responses and orientations retain their original metadata statuses.',
            'No merging across gaps/overlaps/quality or resampling is performed.']))


if __name__ == '__main__':
    main()
