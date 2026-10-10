#!/usr/bin/env python3
"""Bounded official routing/availability queries for the unchanged Hayward cohort."""
import argparse
import datetime as dt
import gzip
import hashlib
import json
from pathlib import Path
import requests

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PLAN = HERE.parent / 'cohort_plan_001'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    with path.open('x') as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write('\n')


def timestamp(value):
    value = value.rstrip('Z').replace('/', '-').replace(' ', 'T')
    return dt.datetime.strptime(value, '%Y-%m-%dT%H:%M:%S.%f' if '.' in value else '%Y-%m-%dT%H:%M:%S')


def context():
    import csv
    summary = json.loads((PLAN / 'summary.json').read_text())
    for name, expected in summary['output_sha256'].items():
        if sha(PLAN / name) != expected:
            raise ValueError('Original cohort plan changed: ' + name)
    with gzip.open(str(PLAN / 'identified_picks.csv.gz'), 'rt', newline='') as f:
        picks = list(csv.DictReader(f))
    if len(picks) != 14262:
        raise ValueError('Original pick support changed')
    batches = json.loads(gzip.decompress((PLAN / 'planned_batches.json.gz').read_bytes()))
    for batch in batches:
        if batch['stage'] == 'routing_dataselect':
            original = batch['request_body']
            lines = original.splitlines(keepends=True)
            if lines[:2] != ['targetservice=dataselect\n', 'format=request\n']:
                raise ValueError('Unexpected original routing request options')
            batch['request_body'] = ''.join(lines[2:])
            batch['metadata']['original_planned_request_sha256'] = batch['metadata']['request_sha256']
            batch['metadata']['request_sha256'] = hashlib.sha256(batch['request_body'].encode('utf-8')).hexdigest()
            for row in batch['metadata']['rows']:
                row['original_plan_request_line'] = row['request_line']
                row['request_line'] -= 2
    cmw1 = [p for p in picks if p['historical_cmw1_response_gap'] == '1']
    if len(cmw1) != 117 or {p['channel_seed_id'] for p in cmw1} != {
            'NC.CMW1..EP2', 'NC.CMW1..EP3', 'NC.CMW1..HN1', 'NC.CMW1..HN2', 'NC.CMW1..HN3'}:
        raise ValueError('Established CMW1 request identities changed')
    for stage, selection in [('cmw1_availability', cmw1),
            ('routable_availability', [p for p in picks if p['historical_cmw1_response_gap'] != '1'])]:
        for first in range(0, len(selection), 100):
            part = selection[first:first + 100]
            lines = [' '.join([p['network_code'], p['station_code'], p['location_code'] or '--',
                p['channel_code'], p['request_start_utc'].rstrip('Z'), p['request_end_utc'].rstrip('Z')]) for p in part]
            body = 'format=json\n' + '\n'.join(lines) + '\n'
            rows = [dict(request_line=n + 2, channel_seed_id=p['channel_seed_id'],
                channel_fdsn_source_id=p['channel_fdsn_source_id'], metadata_epoch_start=p['metadata_epoch_start'],
                metadata_epoch_end=p['metadata_epoch_end'], native_pick_rows=[p['original_observation_index']],
                provider_pick_resource_ids=[p['pick_i_resource_id']], source_metadata_sha256=p['channel_source_sha256'])
                for n, p in enumerate(part)]
            batches.append(dict(stage=stage, batch=first // 100, request_body=body,
                metadata=dict(endpoint='https://service.ncedc.org/fdsnws/availability/1/query',
                    request_sha256=hashlib.sha256(body.encode('utf-8')).hexdigest(), rows=rows)))
    return picks, batches


def retrieve(batch, picks, fetch):
    """Immutable raw bytes and request/native provenance, including failed replies."""
    stage, number = batch['stage'], batch['batch']
    stem = '{}_{:03d}'.format(stage, number)
    raw = HERE / 'raw' / (stem + ('.txt' if stage == 'routing_dataselect' else '.json'))
    raw.parent.mkdir(exist_ok=True)
    body = batch['request_body'].encode('utf-8')
    expected = batch['metadata']['request_sha256']
    if hashlib.sha256(body).hexdigest() != expected:
        raise ValueError('Planned request hash changed')
    selected = {str(n) for r in batch['metadata']['rows'] for n in r['native_pick_rows']}
    native = [p for p in picks if p['original_observation_index'] in selected]
    if len(native) != len(selected):
        raise ValueError('Incomplete native request join')
    identities = dict(request_rows=batch['metadata']['rows'], native_picks=native,
        original_planned_request_sha256=batch['metadata'].get('original_planned_request_sha256', expected),
        syntax_basis=('Official EarthScope POST example uses selection lines and default request output; native selection lines unchanged'
            if stage == 'routing_dataselect' else 'Official NCEDC availability POST body; exact original identified pick windows'),
        native_context_file=str((PLAN / 'identified_picks.csv.gz').relative_to(ROOT)),
        native_context_sha256=sha(PLAN / 'identified_picks.csv.gz'),
        original_plan_sha256=sha(PLAN / 'planned_batches.json.gz'),
        resource_identifier_basis='Provider event/origin/pick/association IDs preserved; FDSN channel IDs derived from exact SEED codes; request URL is not a provider waveform resource ID',
        provider_waveform_resource_id=None,
        current_scope='User-authorized normalized raw-waveform CC; response calibration is not an acquisition prerequisite; original plan request-state text remains historical')
    provenance = raw.with_name(raw.name + '.provenance.json')
    sidecar = raw.with_name(raw.name + '.identifiers.json')
    request_path = raw.with_name(raw.name + '.request.txt')
    if raw.exists():
        meta = json.loads(provenance.read_text())
        if (sha(raw) != meta['sha256'] or meta['request_sha256'] != expected or
                request_path.read_bytes() != body or json.loads(sidecar.read_text())['request_context'] != identities):
            raise ValueError('Pinned reply, request or identity changed: ' + stem)
        return raw, meta
    if not fetch:
        raise ValueError('Offline reply missing: ' + stem)
    url = batch['metadata']['endpoint']
    started = dt.datetime.utcnow().isoformat() + 'Z'
    with request_path.open('xb') as f:
        f.write(body)
    # Preserve the exact native request even if the HTTP operation fails.
    request_ids = dict(request_file=request_path.name, request_sha256=expected,
        source_url=url, request_context=identities)
    save(request_path.with_name(request_path.name + '.identifiers.json'), request_ids)
    try:
        response = requests.post(url, data=body, headers={'Content-Type': 'text/plain'}, timeout=60)
    except requests.RequestException as error:
        save(raw.with_name(raw.name + '.failure.json'), dict(status='stopped_for_access_clarification',
            requested_utc=started, request_sha256=expected, source_url=url,
            request_identifier_sidecar=request_path.name + '.identifiers.json',
            error_type=type(error).__name__, error=str(error)))
        raise
    content = response.content
    meta = dict(method='POST', request_url=url, final_url=response.url,
        requested_utc=started, retrieved_utc=dt.datetime.utcnow().isoformat() + 'Z',
        request_file=request_path.name, request_sha256=expected,
        http_status=response.status_code, content_type=response.headers.get('Content-Type'),
        byte_count=len(content), sha256=hashlib.sha256(content).hexdigest(),
        response_kind='success' if response.status_code == 200 else ('no_data' if response.status_code == 204 else 'http_error'),
        acquisition_source_sha256=sha(Path(__file__)))
    with raw.open('xb') as f:
        f.write(content)
    save(provenance, meta)
    save(sidecar, dict(raw_file=raw.name, source_url=url, source_sha256=meta['sha256'],
        response_kind=meta['response_kind'], request_context=identities))
    return raw, meta


def routing(raw, batch):
    expected = [line.split() for line in batch['request_body'].splitlines() if '=' not in line and line]
    records = []
    service = None
    for number, line in enumerate(raw.read_text().splitlines(), 1):
        if line.startswith('DATASELECTSERVICE='):
            service = line.split('=', 1)[1]
        elif line and not line.startswith('#') and '=' not in line:
            row = line.split()
            if len(row) != 6 or service != 'https://service.ncedc.org/fdsnws/dataselect/1/':
                raise ValueError('Unexpected routing record or provider')
            if not any(row[:4] == q[:4] for q in expected):
                raise ValueError('Unexpected routing NSLC')
            net, sta, loc, cha = row[:4]
            loc = '' if loc == '--' else loc
            matches = [n for n, q in enumerate(expected) if row[:4] == q[:4] and
                timestamp(row[4]) <= timestamp(q[5]) and timestamp(row[5]) >= timestamp(q[4]).replace(microsecond=0)]
            if not matches:
                raise ValueError('Routing row cannot be joined to an original epoch request')
            records.append(dict(source_line=number, provider_service=service,
                network_code=net, station_code=sta, location_code=loc, channel_code=cha,
                channel_seed_id='.'.join((net, sta, loc, cha)),
                channel_fdsn_source_id='FDSN:{}_{}_{}_{}_{}_{}'.format(net, sta, loc, *cha),
                identifier_basis='Derived standardized FDSN source ID, not a provider public ID',
                provider_start=row[4], provider_end=row[5], request_row_indices=matches,
                record_kind='Provider routing selection, not waveform coverage or response epoch'))
    missing = []
    for n, q in enumerate(expected):
        # EarthScope's request output truncates subsecond endpoints. This is
        # routing only; actual waveform windows retain their exact native times.
        start, end = (timestamp(v).replace(microsecond=0) for v in q[4:])
        intervals = sorted((timestamp(r['provider_start']), timestamp(r['provider_end']))
            for r in records if n in r['request_row_indices'])
        cursor = start
        for a, b in intervals:
            if a > cursor:
                break
            cursor = max(cursor, b)
        if cursor < end:
            missing.append(n)
    return dict(records=records, missing_request_rows=missing,
        interval_interpretation='Whole-second routing output only; no availability or calibration inferred')


def availability(raw, batch, picks):
    payload = json.loads(raw.read_text())
    requested = {str(n) for row in batch['metadata']['rows'] for n in row['native_pick_rows']}
    native = [p for p in picks if p['original_observation_index'] in requested]
    records = []
    for index, row in enumerate(payload.get('datasources', [])):
        code = '.'.join(row[k] for k in ('network', 'station', 'location', 'channel'))
        matches = [p for p in native if p['channel_seed_id'] == code]
        if not matches:
            raise ValueError('Unexpected availability NSLC')
        records.append(dict(source_json_pointer='/datasources/' + str(index),
            channel_seed_id=code, channel_fdsn_source_id=matches[0]['channel_fdsn_source_id'],
            identifier_basis='FDSN source ID derived from returned SEED codes; no waveform public ID supplied',
            provider_waveform_resource_id=None, quality=row['quality'], sample_rate_hz=row['samplerate'],
            provider_timespans=row['timespans']))
    coverage = []
    for pick in native:
        matches = []
        for n, record in enumerate(records):
            if record['channel_seed_id'] != pick['channel_seed_id']:
                continue
            rate = float(record['sample_rate_hz'])
            if rate <= 0:
                raise ValueError('Invalid provider sample rate')
            a, b = timestamp(pick['request_start_utc']), timestamp(pick['request_end_utc'])
            if any(timestamp(lo) <= a and timestamp(hi) >= b - dt.timedelta(seconds=1 / rate)
                   for lo, hi in record['provider_timespans']):
                matches.append(n)
        coverage.append(dict(original_observation_index=pick['original_observation_index'],
            event_resource_id=pick['event_i_resource_id'], pick_resource_id=pick['pick_i_resource_id'],
            channel_seed_id=pick['channel_seed_id'], covering_provider_record_indices=matches))
    return dict(records=records, pick_coverage=coverage,
        missing_pick_rows=[r['original_observation_index'] for r in coverage if not r['covering_provider_record_indices']],
        scope='Reported contiguous spans; overlaps, quality and sample-grid identity remain for standard waveform decoding')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['routing_dataselect', 'availability', 'cmw1_availability', 'routable_availability'])
    parser.add_argument('--fetch', action='store_true')
    parser.add_argument('--batches', type=int, default=1, help='Bound this request session; never removes remaining planned records')
    parser.add_argument('--summary', required=True, help='Fresh summary filename inside this package')
    parser.add_argument('--allow-known-cmw1-routing-gap', action='store_true',
        help='User-authorized continuation using the already recovered exact NCEDC historical CMW1 identities')
    args = parser.parse_args()
    if Path(args.summary).name != args.summary or (HERE / args.summary).exists() or args.batches <= 0:
        raise ValueError('Use a fresh simple summary name and positive session batch count')
    picks, plan = context()
    batches = [b for b in plan if b['stage'] == args.stage]
    results = []
    status = 'completed_requested_batches'
    error = None
    try:
        for batch in batches[:args.batches]:
            raw, meta = retrieve(batch, picks, args.fetch)
            if meta['http_status'] != 200:
                raise ValueError('Provider returned {}; stop for access/data clarification'.format(meta['http_status']))
            parsed = routing(raw, batch) if args.stage == 'routing_dataselect' else availability(raw, batch, picks)
            derived = raw.with_name(raw.name + '.parsed.json')
            if derived.exists():
                if json.loads(derived.read_text()) != parsed:
                    raise ValueError('Saved parsed provider records changed')
            else:
                save(derived, parsed)
            results.append(dict(batch=batch['batch'], raw_file=str(raw.relative_to(HERE)),
                raw_sha256=sha(raw), parsed_file=str(derived.relative_to(HERE)), parsed_sha256=sha(derived)))
            missing = parsed.get('missing_request_rows', parsed.get('missing_pick_rows', []))
            print(args.stage, batch['batch'], 'records', len(parsed['records']), 'missing', len(missing), flush=True)
            if missing:
                known = (args.stage == 'routing_dataselect' and args.allow_known_cmw1_routing_gap and
                    all(batch['metadata']['rows'][n]['channel_seed_id'] in {
                        'NC.CMW1..EP2', 'NC.CMW1..EP3', 'NC.CMW1..HN1', 'NC.CMW1..HN2', 'NC.CMW1..HN3'} for n in missing))
                if not known:
                    raise ValueError('Missing identified provider coverage; stop for clarification without removing records')
                results[-1]['documented_cmw1_routing_gap_rows'] = missing
    except Exception as caught:
        status = 'stopped_for_access_or_identity_clarification'
        error = dict(type=type(caught).__name__, message=str(caught))
    summary = dict(status=status, stage=args.stage, requested_session_batches=min(args.batches, len(batches)),
        total_planned_batches=len(batches), results=results, error=error,
        complete_original_picks=14262, complete_original_catalog_differences=44718,
        selection_changed=False, observations_added=0, response_calibration_required=False,
        known_cmw1_routing_gap_authorized=args.allow_known_cmw1_routing_gap,
        plan_sha256=sha(PLAN / 'planned_batches.json.gz'), source_sha256=sha(Path(__file__)))
    save(HERE / args.summary, summary)
    print(json.dumps(summary, indent=2))
    if error:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
