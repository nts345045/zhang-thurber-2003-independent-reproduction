#!/usr/bin/env python3
"""Two already identified NCEDC event-gather windows; no archive search."""
import argparse
import csv
import datetime as dt
import gzip
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
DOC = 'https://service.ncedc.org/ncedcws/eventdata/1/'
URL = DOC + 'query'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def table(path):
    opener = gzip.open if path.suffix == '.gz' else open
    with opener(str(path), 'rt', newline='') as stream:
        return list(csv.DictReader(stream))


def write_table(path, rows):
    with path.open('x', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def prepare():
    sample_dir = ROOT / 'data/authoritative/waveforms/cohort_samples_002'
    measurement_dir = ROOT / 'data/development/native_waveform_cc_001'
    sample = json.loads((sample_dir / 'samples_002.json').read_text())
    measured = json.loads((measurement_dir / 'summary.json').read_text())
    pins = {}
    def pin(path, expected=None):
        digest = sha(path)
        require(expected is None or digest == expected, 'Changed input: ' + str(path))
        pins[str(path.relative_to(ROOT))] = digest
    for directory, summary, name in [(sample_dir, sample, 'samples_002.json'),
                                     (measurement_dir, measured, 'summary.json')]:
        pin(directory / name)
        for name, digest in summary['output_sha256'].items():
            if name.endswith('.csv.gz'):
                pin(directory / name, digest)
    picks = [p for p in table(sample_dir / 'samples_002.picks.csv.gz')
             if p['original_observation_index'] in ('133', '159')]
    require([p['original_observation_index'] for p in picks] == ['133', '159'], 'Pilot pick roster changed')
    pair = [p for p in table(measurement_dir / 'identified_measurements.csv.gz')
            if p['original_catalog_original_observation_index'] == '21796']
    require(len(pair) == 1 and pair[0]['measurement_status'] == 'not_attempted', 'Pilot pair changed')
    pair = {k[len('original_catalog_'):]: v for k, v in pair[0].items() if k.startswith('original_catalog_')}
    events_path = ROOT / 'data/authoritative/hayward/selected_events.csv'
    events = {e['event_resource_id']: e for e in table(events_path)}
    epoch_path = ROOT / 'data/authoritative/waveforms/cohort_plan_001/identified_used_epochs.csv.gz'
    epochs = {e['id']: e for e in table(epoch_path)}
    pin(events_path); pin(epoch_path)
    xml_path = ROOT / 'data/authoritative/hayward/raw/picks_00000.xml'
    station_path = ROOT / 'data/authoritative/stations/raw/ncedc_channels_NC_987aa2b70b3c.xml'
    ns = {'b': 'http://quakeml.org/xmlns/bed/1.2'}
    catalog_ns = '{http://anss.org/xmlns/catalog/0.1}'
    raw_events = {e.get('publicID'): e for e in ET.parse(str(xml_path)).findall('.//b:event', ns)}
    stations = ET.parse(str(station_path)); stns = {'s': 'http://www.fdsn.org/xml/station/1'}
    selected_events = []
    for side, pick, eventid in zip(('i', 'j'), picks, ('12434', '12437')):
        require(pick['channel_seed_id'] == 'NC.CMC..EHZ' and pick['location_code'] == '' and
                pick['channel_fdsn_source_id'] == 'FDSN:NC_CMC__E_H_Z', 'NSLC changed')
        require(pick['waveform_status'] == 'not_requested_no_reported_span' and
                pick['orientation_status'] == 'provider-declared vertical' and
                float(pick['provider_sample_rate_hz']) == 100 and float(pick['provider_dip_deg']) == -90,
                'Pilot metadata or prior outcome changed')
        for field in ('event', 'origin', 'arrival', 'pick'):
            require(pair[field + '_' + side + '_resource_id'] == pick[field + '_i_resource_id'], 'Native pair identity changed')
        event = events[pick['event_i_resource_id']]
        require(event['provider_event_eventid'] == eventid and event['provider_event_datasource'] == 'nc' and
                event['provider_event_dataid'] == 'nc' + eventid and 'catalog=NCSS' in event['source_url'],
                'Provider event/catalog identity is not established')
        require(event['origin_resource_id'] == pick['origin_i_resource_id'], 'Origin changed')
        pin(ROOT / 'data/authoritative/hayward' / event['source_file'], event['source_sha256'])
        pin(xml_path, pick['pick_i_source_sha256']); pin(station_path, pick['channel_source_sha256'])
        raw = raw_events[pick['event_i_resource_id']]
        require(raw.get(catalog_ns + 'eventid') == eventid and raw.get(catalog_ns + 'datasource') == 'nc', 'Raw provider event ID changed')
        nodes = [p for p in raw.findall('b:pick', ns) if p.get('publicID') == pick['pick_i_resource_id']]
        require(len(nodes) == 1, 'Raw pick missing or repeated')
        waveform = nodes[0].find('b:waveformID', ns)
        require([waveform.get(k) for k in ('networkCode', 'stationCode', 'locationCode', 'channelCode')] == ['NC', 'CMC', '', 'EHZ'], 'Raw pick NSLC changed')
        provider_time = nodes[0].findtext('b:time/b:value', namespaces=ns)
        parse = lambda value: dt.datetime.strptime(value.rstrip('Z'), '%Y-%m-%dT%H:%M:%S.%f')
        require(parse(provider_time) == parse(pick['pick_i_time_utc']), 'Raw pick time changed')
        epoch = epochs[pick['station']]
        require(all(epoch[k] == pick[k] for k in ('channel_seed_id', 'channel_fdsn_source_id', 'metadata_epoch_start', 'metadata_epoch_end')), 'Epoch join changed')
        channels = [c for n in stations.findall('s:Network', stns) if n.get('code') == 'NC'
                    for s in n.findall('s:Station', stns) if s.get('code') == 'CMC'
                    for c in s.findall('s:Channel', stns) if c.get('code') == 'EHZ' and c.get('locationCode') == ''
                    and c.get('startDate').rstrip('Z') == pick['metadata_epoch_start']
                    and c.get('endDate').rstrip('Z') == pick['metadata_epoch_end']]
        require(len(channels) == 1 and float(channels[0].findtext('s:SampleRate', namespaces=stns)) == 100 and
                float(channels[0].findtext('s:Dip', namespaces=stns)) == -90, 'Raw StationXML epoch/rate/dip changed')
        selected_events.append(event)
    route = ROOT / 'data/authoritative/waveforms/cohort_cc_002/raw/routing_dataselect_005.txt'
    require('NC CMC -- EHZ 1984' in route.read_text() and 'https://service.ncedc.org/fdsnws/dataselect/1/' in route.read_text(), 'Saved EarthScope NCEDC route missing')
    for suffix in ('', '.provenance.json', '.identifiers.json'):
        pin(Path(str(route) + suffix))
    for name in ('usgs_comcat.html', 'earthscope_fedcatalog.html', 'ncedc_eventdata.html'):
        pin(ROOT / 'data/authoritative/waveforms/discovery_001' / name)
    pin(Path(__file__))
    write_table(HERE / 'native_picks.csv', picks)
    write_table(HERE / 'native_pair.csv', [pair])
    write_table(HERE / 'native_events.csv', selected_events)
    write_table(HERE / 'native_epoch.csv', [epochs[picks[0]['station']]])
    save(HERE / 'plan.json', dict(status='native_identity_verified', original_catalog_row=21796,
        native_picks=picks, native_pair=pair, native_events=selected_events,
        native_epoch=epochs[picks[0]['station']], input_sha256=pins,
        request_scope='Two existing P-1 to P+4 second windows only; exact NCSS event IDs and NC.CMC..EHZ; no aliases or CMW1 work',
        no_response_correction=True, availability_asserted=False, selection_changed=False,
        missing_provider_waveform_resource_id=None))


def request(name, url, body, context):
    import requests
    raw = HERE / name
    request_path = HERE / (name + '.request.txt')
    with request_path.open('xb') as stream:
        stream.write(body)
    save(HERE / (name + '.request.txt.identifiers.json'), dict(source_url=url,
        request_sha256=sha(request_path), request_context=context))
    start = utc()
    response = (requests.get(url, timeout=120, allow_redirects=False) if not body else
                requests.post(url, data=body, headers={'Content-Type': 'text/plain'}, timeout=120, allow_redirects=False))
    with raw.open('xb') as stream:
        stream.write(response.content)
    provenance = dict(request_url=url, final_url=response.url, method='GET' if not body else 'POST',
        requested_utc=start, retrieved_utc=utc(), http_status=response.status_code,
        content_type=response.headers.get('Content-Type'), location_header=response.headers.get('Location'),
        byte_count=len(response.content), sha256=sha(raw), request_sha256=sha(request_path),
        source_sha256=sha(Path(__file__)), response_kind='official_documentation' if not body else 'event_waveform_response_pending_inspection')
    save(HERE / (name + '.provenance.json'), provenance)
    save(HERE / (name + '.identifiers.json'), dict(source_url=url, source_sha256=sha(raw), request_context=context,
        provider_waveform_resource_id=None, identifier_basis='Provider event/origin/pick/arrival IDs and exact SEED codes retained; FDSN source IDs derived by standard; no waveform resource ID invented'))
    require(response.status_code in (200, 204), 'Unexpected provider HTTP status: ' + str(response.status_code))
    return provenance


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['prepare', 'docs', 'fetch'])
    args = parser.parse_args()
    if args.stage == 'prepare':
        prepare(); return
    plan = json.loads((HERE / 'plan.json').read_text())
    for path, digest in plan['input_sha256'].items():
        require(sha(ROOT / path) == digest, 'Pinned input changed: ' + path)
    context = dict(plan_sha256=sha(HERE / 'plan.json'), native_picks=plan['native_picks'], native_pair=plan['native_pair'], native_events=plan['native_events'], native_epoch=plan['native_epoch'])
    if args.stage == 'docs':
        result = request('current_eventdata.html', DOC, b'', context)
        require(result['http_status'] == 200, 'Current documentation unavailable')
        text = (HERE / 'current_eventdata.html').read_text()
        require(all(value in text for value in ('catalog=NCSS', '/ncedcws/eventdata/1/query', 'N S L C starttime endtime', '&quot;--&quot;')), 'Current supported syntax differs from saved request')
        save(HERE / 'current_documentation_review.json', dict(status='supported_syntax_verified', source_url=DOC,
            source_sha256=sha(HERE / 'current_eventdata.html'), saved_document_sha256=sha(ROOT / 'data/authoritative/waveforms/discovery_001/ncedc_eventdata.html'),
            scope='Current official page retains catalog+event IDs, exact SEED selection and per-channel times; empty location is -- in POST'))
        return
    doc_review = json.loads((HERE / 'current_documentation_review.json').read_text())
    require(doc_review['status'] == 'supported_syntax_verified' and doc_review['source_sha256'] == sha(HERE / 'current_eventdata.html'), 'Documentation gate failed')
    results = []
    for pick, event in zip(plan['native_picks'], plan['native_events']):
        body = ('eventid=' + event['provider_event_eventid'] + '\ncatalog=NCSS\n' +
                ' '.join(['NC', 'CMC', '--', 'EHZ', pick['request_start_utc'].rstrip('Z'), pick['request_end_utc'].rstrip('Z')]) + '\n').encode()
        name = 'event_' + event['provider_event_eventid'] + '.response'
        result = request(name, URL, body, dict(context, requested_pick=pick, requested_event=event))
        result['raw_file'] = name
        result['outcome'] = 'provider_returned_no_data' if result['http_status'] == 204 else 'received_pending_standard_decode'
        results.append(result)
    save(HERE / 'acquisition_summary.json', dict(status='completed_two_declared_requests', results=results,
        plan_sha256=sha(HERE / 'plan.json'), documentation_review_sha256=sha(HERE / 'current_documentation_review.json'),
        measurements_added=0, calibration_corrections=0, catalog_edits=0, availability_asserted=False))


if __name__ == '__main__':
    args = list(sys.argv)
    stage = args[1] if len(args) > 1 else 'unknown'
    started = utc()
    try:
        main()
    except Exception as error:
        save(HERE / (stage + '_execution.json'), dict(status='stopped_for_review', command=['python', str(Path(__file__).relative_to(ROOT))] + args[1:],
            started_utc=started, finished_utc=utc(), source_sha256=sha(Path(__file__)), error_type=type(error).__name__, error=str(error)))
        raise
    save(HERE / (stage + '_execution.json'), dict(status='completed', return_code=0,
        command=['python', str(Path(__file__).relative_to(ROOT))] + args[1:], started_utc=started, finished_utc=utc(), source_sha256=sha(Path(__file__))))
