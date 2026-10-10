#!/usr/bin/env python3
"""Join a terminal availability inventory to every unchanged pick and catalog pair."""
import collections
import csv
import datetime as dt
import gzip
import hashlib
import io
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PLAN = HERE.parent / 'cohort_plan_001'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def table(path):
    with gzip.open(str(path), 'rt', newline='') as f:
        return list(csv.DictReader(f))


def write_table(path, rows):
    with path.open('xb') as raw, gzip.GzipFile(filename='', fileobj=raw, mode='wb', mtime=0) as compressed:
        with io.TextIOWrapper(compressed, encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator='\n')
            writer.writeheader(); writer.writerows(rows)


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def provider_coverage(raw, parsed, native, no_data):
    """Recheck reported spans directly from raw bytes; this does not decode samples."""
    payload = {} if no_data else json.loads(raw.read_text())
    sources = payload.get('datasources', [])
    require(len(sources) == len(parsed['records']), 'Provider record count changed')
    def time(value):
        value = value.rstrip('Z').replace('/', '-').replace(' ', 'T')
        return dt.datetime.strptime(value, '%Y-%m-%dT%H:%M:%S.%f' if '.' in value else '%Y-%m-%dT%H:%M:%S')
    for n, (source, record) in enumerate(zip(sources, parsed['records'])):
        code = '.'.join(source[k] for k in ('network', 'station', 'location', 'channel'))
        require(record['source_json_pointer'] == '/datasources/' + str(n) and
            record['channel_seed_id'] == code and record['quality'] == source['quality'] and
            record['sample_rate_hz'] == source['samplerate'] and
            record['provider_timespans'] == source['timespans'], 'Parsed span differs from raw provider record')
        rate = float(source['samplerate'])
        require(math.isfinite(rate) and rate > 0, 'Invalid raw provider sample rate')
    by_id = {p['original_observation_index']: p for p in native}
    for row in parsed['pick_coverage']:
        pick = by_id[row['original_observation_index']]
        start, end = time(pick['request_start_utc']), time(pick['request_end_utc'])
        matches = []
        for n, source in enumerate(sources):
            code = '.'.join(source[k] for k in ('network', 'station', 'location', 'channel'))
            if code != pick['channel_seed_id']:
                continue
            last = end - dt.timedelta(seconds=1 / float(source['samplerate']))
            if any(time(a) <= start and time(b) >= last for a, b in source['timespans']):
                matches.append(n)
        require(row['covering_provider_record_indices'] == matches, 'Coverage differs from raw provider spans')


def main():
    pinned = {}
    def pin(path):
        name = str(path.relative_to(ROOT))
        value = sha(path)
        require(name not in pinned or pinned[name] == value, 'Input changed: ' + name)
        pinned[name] = value
        return path
    def load(path):
        return json.loads(pin(path).read_text())
    execution = load(HERE / 'inventory_execution.json')
    require(execution['status'] == 'completed', 'Inventory must be terminal completed')
    require(len(execution['stages']) == 2, 'Inventory stages incomplete')
    plan = load(PLAN / 'summary.json')
    for name, digest in plan['output_sha256'].items():
        require(sha(pin(PLAN / name)) == digest, 'Original cohort plan changed')
    picks = table(pin(PLAN / 'identified_picks.csv.gz'))
    pairs = table(pin(PLAN / 'identified_catalog_differences.csv.gz'))
    require(len(picks) == 14262 and len(pairs) == 44718, 'Original support changed')
    original = {p['original_observation_index']: p for p in picks}
    by_pick = {p['pick_i_resource_id']: p for p in picks}
    require(len(original) == len(by_pick) == len(picks), 'Original pick keys not unique')
    coverage = {}
    for stage in execution['stages']:
        require(stage['status'] == 'completed' and stage['returncode'] == 0, 'Stage did not complete')
        for name, digest in stage['output_sha256'].items():
            require(sha(pin(HERE / name)) == digest, 'Terminal stage artifact changed')
        summary = load(HERE / (stage['stage'] + '_all_001.json'))
        require(summary['status'] == 'completed_requested_batches' and summary['no_span_inventory_authorized'], 'Unsupported stage state')
        require(len(summary['results']) == summary['total_planned_batches'], 'Not all batches inventoried')
        for expected_batch, result in enumerate(summary['results']):
            require(result['batch'] == expected_batch, 'Batch order mismatch')
            raw = pin(HERE / result['raw_file'])
            require(sha(raw) == result['raw_sha256'], 'Raw response hash mismatch')
            parsed_path = pin(HERE / result['parsed_file'])
            require(sha(parsed_path) == result['parsed_sha256'], 'Parsed response hash mismatch')
            parsed = load(parsed_path)
            meta = load(raw.with_name(raw.name + '.provenance.json'))
            identities = load(raw.with_name(raw.name + '.identifiers.json'))
            request = pin(raw.with_name(raw.name + '.request.txt'))
            request_ids = load(request.with_name(request.name + '.identifiers.json'))
            require(sha(raw) == meta['sha256'] == identities['source_sha256'], 'Raw provenance mismatch')
            require(raw.stat().st_size == meta['byte_count'] and meta['http_status'] in (200, 204), 'Unsupported provider outcome')
            require(sha(request) == meta['request_sha256'] == request_ids['request_sha256'], 'Request body changed')
            require(meta['request_url'] == 'https://service.ncedc.org/fdsnws/availability/1/query', 'Unexpected authoritative endpoint')
            native = identities['request_context']['native_picks']
            require(identities['request_context'] == request_ids['request_context'], 'Request/response native context differs')
            for row in native:
                require(row == original[row['original_observation_index']], 'Native request row differs from original')
            lines = request.read_text().splitlines()
            for selection in request_ids['request_context']['request_rows']:
                require(len(selection['native_pick_rows']) == 1, 'Availability request must retain one exact pick window per line')
                p = original[str(selection['native_pick_rows'][0])]
                expected = [p['network_code'], p['station_code'], p['location_code'] or '--', p['channel_code'],
                    p['request_start_utc'].rstrip('Z'), p['request_end_utc'].rstrip('Z')]
                require(lines[selection['request_line'] - 1].split() == expected, 'Posted native channel/time selection changed')
                require(selection['metadata_epoch_start'] == p['metadata_epoch_start'] and
                    selection['metadata_epoch_end'] == p['metadata_epoch_end'], 'Request epoch identity changed')
            require(len(native) == len(parsed['pick_coverage']), 'Coverage rows incomplete')
            native_ids = {p['original_observation_index'] for p in native}
            require({p['original_observation_index'] for p in parsed['pick_coverage']} == native_ids, 'Coverage identifiers differ')
            provider_coverage(raw, parsed, native, meta['http_status'] == 204)
            for row in parsed['pick_coverage']:
                n = row['original_observation_index']; p = original[n]
                require(n not in coverage, 'Duplicate inventoried pick')
                require(row['event_resource_id'] == p['event_i_resource_id'] and
                    row['pick_resource_id'] == p['pick_i_resource_id'] and row['channel_seed_id'] == p['channel_seed_id'], 'Coverage native identity changed')
                records = [parsed['records'][i] for i in row['covering_provider_record_indices']]
                require(all(r['channel_seed_id'] == p['channel_seed_id'] and r['channel_fdsn_source_id'] == p['channel_fdsn_source_id'] for r in records), 'Provider span channel mismatch')
                coverage[n] = dict(availability_status='provider_reports_covering_span' if records else 'no_covering_span_reported',
                    availability_response_file=str(raw.relative_to(ROOT)), availability_response_sha256=sha(raw),
                    availability_provider_record_indices=json.dumps(row['covering_provider_record_indices']),
                    availability_quality_codes=json.dumps(sorted({r['quality'] for r in records})),
                    availability_sample_rates_hz=json.dumps(sorted({r['sample_rate_hz'] for r in records})),
                    waveform_samples_status='not acquired in this inventory')
    require(set(coverage) == set(original), 'Complete original pick support not inventoried')
    for p in picks:
        p.update(coverage[p['original_observation_index']])
    for pair in pairs:
        for side in ('i', 'j'):
            p = by_pick[pair['pick_' + side + '_resource_id']]
            for key in ('event', 'origin', 'pick', 'arrival'):
                require(pair[key + '_' + side + '_resource_id'] == p[key + '_i_resource_id'], 'Original pair/pick identity changed')
            require(pair['metadata_epoch_' + ('j_' if side == 'j' else '') + 'start'] == p['metadata_epoch_start'] and
                pair['metadata_epoch_' + ('j_' if side == 'j' else '') + 'end'] == p['metadata_epoch_end'], 'Original pair epoch mismatch')
            pair['availability_' + side + '_status'] = p['availability_status']
            pair['availability_' + side + '_response_file'] = p['availability_response_file']
            pair['availability_' + side + '_response_sha256'] = p['availability_response_sha256']
        pair['both_picks_have_reported_span'] = int(all(pair['availability_' + side + '_status'] == 'provider_reports_covering_span' for side in ('i', 'j')))
    groups = {}
    for key in ('station_code', 'channel_seed_id'):
        counts = collections.defaultdict(collections.Counter)
        for p in picks:
            counts[p[key]][p['availability_status']] += 1
        groups[key] = {k:dict(v) for k, v in sorted(counts.items())}
    years = collections.defaultdict(collections.Counter)
    for p in picks:
        years[p['pick_i_time_utc'][:4]][p['availability_status']] += 1
    for name, digest in pinned.items():
        require(sha(ROOT / name) == digest, 'Input changed during readback: ' + name)
    write_table(HERE / 'identified_pick_availability.csv.gz', picks)
    write_table(HERE / 'identified_pair_availability.csv.gz', pairs)
    for name, expected in [('identified_pick_availability.csv.gz', picks), ('identified_pair_availability.csv.gz', pairs)]:
        actual = table(HERE / name)
        require(actual == [{k:str(v) for k,v in row.items()} for row in expected], 'Saved native table readback differs: ' + name)
    summary = dict(status='complete_inventory_native_readback_passed',
        scope='Authoritative reported availability only; no sample identity/continuity or correlation acceptance asserted',
        retained_picks=len(picks), retained_catalog_differences=len(pairs),
        pick_counts=dict(collections.Counter(p['availability_status'] for p in picks)),
        pair_counts=dict(collections.Counter(str(p['both_picks_have_reported_span']) for p in pairs)),
        by_year={k:dict(v) for k,v in sorted(years.items())}, by_channel_or_station=groups,
        cmw1_pick_counts=dict(collections.Counter(p['availability_status'] for p in picks if p['station_code'] == 'CMW1')),
        selections_changed=False, waveform_measurements_added=0,
        raw_provider_spans_and_coverage_rechecked=True,
        coverage_convention='Provider timespan ends are last-sample times; a covering span reaches the requested half-open end minus one provider sample interval. Actual sample-grid alignment, continuity and overlap validity remain unverified until waveform decoding.',
        source_sha256=sha(Path(__file__)), input_sha256=pinned,
        output_sha256={n:sha(HERE / n) for n in ('identified_pick_availability.csv.gz', 'identified_pair_availability.csv.gz')})
    with (HERE / 'inventory_summary.json').open('x') as f:
        json.dump(summary, f, indent=2, allow_nan=False); f.write('\n')
    print(json.dumps({k:summary[k] for k in ('status','retained_picks','retained_catalog_differences','pick_counts','pair_counts','cmw1_pick_counts')}, indent=2))


if __name__ == '__main__':
    main()
