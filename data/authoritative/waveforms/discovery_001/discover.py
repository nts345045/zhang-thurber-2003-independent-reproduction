#!/usr/bin/env python3
"""One identified waveform-availability probe; never downloads waveform samples."""
import argparse
import csv
import datetime
import hashlib
import json
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
DOCS = {
    'usgs_comcat.html': 'https://earthquake.usgs.gov/data/comcat/',
    'earthscope_fedcatalog.html': 'https://service.earthscope.org/irisws/fedcatalog/1/',
    'ncedc_availability.html': 'https://service.ncedc.org/fdsnws/availability/1/',
    'ncedc_eventdata.html': 'https://service.ncedc.org/ncedcws/eventdata/1/',
    'ncedc_dataselect.html': 'https://service.ncedc.org/fdsnws/dataselect/1/',
    'ncedc_historical_archive.html': 'https://ncedc.org/blog/2004/11/11/ncsn-data-available-in-seed.html',
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_json(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def retrieve(name, url, identities, allow_fetch):
    raw = HERE / name
    provenance = HERE / (name + '.provenance.json')
    if raw.exists():
        meta = json.loads(provenance.read_text())
        if meta['request_url'] != url or sha(raw) != meta['sha256']:
            raise ValueError('Pinned response mismatch: ' + name)
        return raw.read_bytes(), meta
    if not allow_fetch:
        raise ValueError('Offline response missing: ' + name)
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        response = requests.get(url, timeout=30)
    except requests.RequestException as error:
        save_json(HERE / (name + '.failure.json'), dict(request_url=url,
            requested_utc=started, error_type=type(error).__name__, error=str(error),
            native_request=identities, status='stopped_for_access_clarification'))
        raise
    body = response.content
    meta = dict(request_url=url, final_url=response.url, requested_utc=started,
        retrieved_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        http_status=response.status_code, content_type=response.headers.get('Content-Type'),
        byte_count=len(body), sha256=hashlib.sha256(body).hexdigest(),
        response_kind='no_data' if response.status_code == 204 else
            ('success' if response.status_code == 200 else 'http_error'))
    with raw.open('xb') as stream:
        stream.write(body)
    save_json(provenance, meta)
    save_json(HERE / (name + '.identifiers.json'), dict(raw_file=name,
        source_url=url, source_sha256=meta['sha256'], response_kind=meta['response_kind'],
        resource_identifier_basis='Source URL identifies the response; supplied native IDs are request context, not an assertion of waveform availability.',
        native_request=identities))
    if response.status_code not in (200, 204):
        raise ValueError('HTTP {}: stop for access clarification'.format(response.status_code))
    return body, meta


def probe_identity(partner=False):
    path = ROOT / 'data/hayward/observations.csv'
    with path.open() as stream:
        indexed = [(i, row) for i, row in enumerate(csv.DictReader(stream)) if row['type'] == '0']
    indexed.sort(key=lambda item: (item[1]['pick_i_time_utc'], item[1]['channel_seed_id']))
    index, row = indexed[len(indexed) // 2]
    relation = None
    if partner:
        primary = row
        with path.open() as stream:
            for pair_index, pair in enumerate(csv.DictReader(stream)):
                if pair['type'] == '1' and primary['pick_i_resource_id'] in (
                        pair['pick_i_resource_id'], pair['pick_j_resource_id']):
                    other = pair['pick_j_resource_id'] if primary['pick_i_resource_id'] == pair['pick_i_resource_id'] else pair['pick_i_resource_id']
                    matches = [(n, r) for n, r in indexed if r['pick_i_resource_id'] == other]
                    if len(matches) != 1 or matches[0][1]['channel_seed_id'] != primary['channel_seed_id']:
                        raise ValueError('Existing differential partner identity is not unique')
                    index, row = matches[0]
                    relation = dict(original_observation_index=pair_index, original_observation=pair)
                    break
        if relation is None:
            raise ValueError('No selected differential partner; stop for clarification')
    when = datetime.datetime.strptime(row['pick_i_time_utc'], '%Y-%m-%dT%H:%M:%S.%fZ')
    start = (when - datetime.timedelta(seconds=1)).isoformat(timespec='microseconds')
    end = (when + datetime.timedelta(seconds=4)).isoformat(timespec='microseconds')
    context = dict(selection=('Partner from the first existing catalog-difference observation containing the median probe pick; no new pair or cohort' if partner else
        'Chronological median retained absolute pick, ordered by UTC pick time then NSLC; discovery only, no cohort change'),
        original_observation_index=index, input_file=str(path.relative_to(ROOT)),
        input_sha256=sha(path), request_start_utc=start+'Z', request_end_utc=end+'Z',
        original_observation=row, provider_waveform_resource_id=None,
        channel_identifier_basis='FDSN source ID derived by standard in the pinned metadata; QuakeML event/origin/pick/arrival IDs are provider-supplied')
    if partner:
        context['existing_differential_pair'] = relation
    identity_path = HERE / ('partner_probe_identity.json' if partner else 'probe_identity.json')
    if identity_path.exists():
        if json.loads(identity_path.read_text()) != context:
            raise ValueError('Pinned probe identity changed')
    else:
        save_json(identity_path, context)
    return context, row, start, end


def attach_records(name, records):
    """Attach normalized identities to raw routing/span rows without changing replies."""
    path = HERE / (name + '.identifiers.json')
    value = json.loads(path.read_text())
    if 'response_records' in value and value['response_records'] != records:
        raise ValueError('Derived response identifiers changed')
    value['response_records'] = records
    path.write_text(json.dumps(value, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['docs', 'routing', 'availability', 'partner-routing', 'partner-availability'])
    parser.add_argument('--fetch', action='store_true', help='Allow initial HTTP requests; existing replies remain immutable')
    args = parser.parse_args()
    if args.stage == 'docs':
        for name, url in DOCS.items():
            _, meta = retrieve(name, url, dict(record_kind='Official service documentation; no observational records extracted'), args.fetch)
            print(name, meta['http_status'], meta['byte_count'], flush=True)
        return
    partner = args.stage.startswith('partner-')
    stage = args.stage.replace('partner-', '')
    prefix = 'partner_' if partner else ''
    context, row, start, end = probe_identity(partner)
    params = dict(net=row['network_code'], sta=row['station_code'], loc=row['location_code'] or '--',
        cha=row['channel_code'], starttime=start, endtime=end)
    endpoint = 'https://service.earthscope.org/irisws/fedcatalog/1/query'
    route_url = requests.Request('GET', endpoint, params=dict(params, targetservice='dataselect', format='request')).prepare().url
    route_name = prefix + 'earthscope_routing.txt'
    body, meta = retrieve(route_name, route_url, context, args.fetch if stage == 'routing' else False)
    if meta['http_status'] == 204:
        raise ValueError('No routing data for identified request; stop for clarification')
    lines = body.decode('utf-8').splitlines()
    routes = [line.split('=', 1)[1].strip() for line in lines if line.startswith('DATASELECTSERVICE=')]
    rows = [line.split() for line in lines if line and not line.startswith('#') and '=' not in line]
    expected = [row['network_code'], row['station_code'], row['location_code'] or '--', row['channel_code']]
    if not rows or any(len(line) != 6 or line[:4] != expected for line in rows):
        raise ValueError('Unexpected routing identity; stop for clarification')
    if routes != ['https://service.ncedc.org/fdsnws/dataselect/1/']:
        raise ValueError('Unexpected provider route; stop for clarification')
    attach_records(route_name, [dict(source_line=n, network_code=row['network_code'],
        station_code=row['station_code'], location_code=row['location_code'], channel_code=row['channel_code'],
        channel_seed_id=row['channel_seed_id'], channel_fdsn_source_id=row['channel_fdsn_source_id'],
        identifier_basis='Derived FDSN identifier from exact provider-returned SEED codes, not a provider public ID',
        record_kind='Routing request, not a confirmed waveform extent or metadata epoch',
        provider_start=line.split()[4], provider_end=line.split()[5])
        for n, line in enumerate(lines, 1) if line and not line.startswith('#') and '=' not in line])
    print('Exact NSLC routed to NCEDC:', expected, flush=True)
    if stage == 'availability':
        # The routed center documents this companion availability service.
        params = dict(net=row['network_code'], sta=row['station_code'], loc=row['location_code'] or '--',
            cha=row['channel_code'], start=start, end=end, format='json', nodata=204)
        url = requests.Request('GET', 'https://service.ncedc.org/fdsnws/availability/1/query', params=params).prepare().url
        availability_name = prefix + 'ncedc_availability.json'
        body, meta = retrieve(availability_name, url, context, args.fetch)
        print('Availability HTTP', meta['http_status'], 'bytes', meta['byte_count'], flush=True)
        if meta['http_status'] == 204:
            raise ValueError('No availability spans for identified pick window; stop for clarification')
        payload = json.loads(body.decode('utf-8'))
        records = []
        for i, source in enumerate(payload.get('datasources', [])):
            if [source.get(k) for k in ('network', 'station', 'location', 'channel')] != [row[k]
                    for k in ('network_code', 'station_code', 'location_code', 'channel_code')]:
                raise ValueError('Unexpected availability identity; stop for clarification')
            records.append(dict(source_json_pointer='/datasources/'+str(i),
                channel_seed_id=row['channel_seed_id'], channel_fdsn_source_id=row['channel_fdsn_source_id'],
                identifier_basis='Derived FDSN identifier from exact provider-returned SEED codes, not a provider public ID',
                provider_resource_id=None, quality=source['quality'], sample_rate_hz=source['samplerate'],
                provider_timespans=source['timespans']))
        attach_records(availability_name, records)
        covered = any(datetime.datetime.strptime(a, '%Y/%m/%d %H:%M:%S.%f') <= datetime.datetime.strptime(start, '%Y-%m-%dT%H:%M:%S.%f')
            and datetime.datetime.strptime(b, '%Y/%m/%d %H:%M:%S.%f') >= datetime.datetime.strptime(end, '%Y-%m-%dT%H:%M:%S.%f')
            for record in records for a, b in record['provider_timespans'])
        if not covered:
            raise ValueError('No single contiguous span covers the requested window; stop for clarification')
        print(body.decode('utf-8'), flush=True)


if __name__ == '__main__':
    main()
