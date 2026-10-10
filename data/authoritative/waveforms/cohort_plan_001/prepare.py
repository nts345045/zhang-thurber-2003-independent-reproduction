#!/usr/bin/env python3
"""Offline full-cohort waveform request plan; never sends a network request."""
import csv
import datetime as dt
import gzip
import hashlib
import io
import json
from pathlib import Path
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
NS = {'s': 'http://www.fdsn.org/xml/station/1'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def table(path, rows):
    with path.open('xb') as raw:
        with gzip.GzipFile(filename='', fileobj=raw, mode='wb', mtime=0) as compressed:
            with io.TextIOWrapper(compressed, encoding='utf-8', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
                writer.writeheader()
                writer.writerows(rows)


def main():
    if not __debug__:
        raise RuntimeError('Integrity checks require Python without -O')
    inputs = {}

    def pin(path):
        path = path.resolve()
        name = str(path.relative_to(ROOT))
        if name not in inputs:
            inputs[name] = sha(path)
        return path

    def read(name):
        return list(csv.DictReader(pin(ROOT/name).open()))

    observations = read('data/hayward/observations.csv')
    stations = read('data/hayward/stations.csv')
    events = read('data/hayward/initial_events.csv')
    pin(ROOT/'data/hayward/selection_manifest.json')
    assert len(events) == 1092
    assert all(int(r['id']) == i for i, r in enumerate(stations))
    assert all(int(r['id']) == i for i, r in enumerate(events))
    picks, pairs = [], []
    source_xml = {}
    orientations = {}
    for index, row in enumerate(observations):
        assert row['type'] in ('0', '1')
        item = dict(original_observation_index=index, **row)
        (picks if row['type'] == '0' else pairs).append(item)
    assert len(picks) == 14262 and len(pairs) == 44718
    by_pick = {p['pick_i_resource_id']: p for p in picks}
    assert len(by_pick) == len(picks)
    for row in picks:
        i, k = int(row['i']), int(row['station'])
        assert 0 <= i < len(events) and 0 <= k < len(stations)
        native = stations[k]
        for field in ('channel_seed_id', 'channel_fdsn_source_id', 'network_code', 'station_code',
                      'location_code', 'channel_code', 'metadata_epoch_start', 'metadata_epoch_end'):
            assert row[field] == native[field], (index, field)
        for field in ('event_resource_id', 'origin_resource_id'):
            assert row[field.replace('_resource_id', '_i_resource_id')] == events[i][field]
        path = pin((ROOT/'data/hayward'/native['source_file']).resolve())
        assert inputs[str(path.relative_to(ROOT))] == row['channel_source_sha256'] == native['source_sha256']
        if k not in orientations:
            if native['metadata_source_kind'] == 'NCSN master station/channel history':
                info = dict(provider_azimuth_deg='', provider_dip_deg='', provider_sample_rate_hz='',
                            orientation_status='not supplied by historical operation record',
                            response_status='historical response epoch not established')
            else:
                if path not in source_xml:
                    source_xml[path] = ET.parse(str(path)).getroot()
                found = []
                for network in source_xml[path].findall('s:Network', NS):
                    for station in network.findall('s:Station', NS):
                        for channel in station.findall('s:Channel', NS):
                            if [network.get('code'), station.get('code'), channel.get('locationCode'), channel.get('code'),
                                channel.get('startDate', ''), channel.get('endDate', '')] == [native[f] for f in
                                ('network_code', 'station_code', 'location_code', 'channel_code', 'channel_epoch_start', 'channel_epoch_end')]:
                                found.append(channel)
                assert len(found) == 1, ('native XML epoch', k, len(found))
                channel = found[0]
                dip = channel.findtext('s:Dip', default='', namespaces=NS)
                info = dict(provider_azimuth_deg=channel.findtext('s:Azimuth', default='', namespaces=NS),
                    provider_dip_deg=dip, provider_sample_rate_hz=channel.findtext('s:SampleRate', default='', namespaces=NS),
                    orientation_status=('provider-declared vertical' if dip and abs(float(dip)) == 90 else
                        ('provider-declared nonvertical' if dip else 'dip missing in cached channel metadata')),
                    response_status='full response not yet retrieved for this plan')
            orientations[k] = info
        when = dt.datetime.strptime(row['pick_i_time_utc'], '%Y-%m-%dT%H:%M:%S.%fZ')
        row.update(orientations[k])
        row.update(request_start_utc=(when-dt.timedelta(seconds=1)).isoformat(timespec='microseconds')+'Z',
                   request_end_utc=(when+dt.timedelta(seconds=4)).isoformat(timespec='microseconds')+'Z',
                   historical_cmw1_response_gap=int(row['station_code'] == 'CMW1'),
                   before_documented_march_1984_archive=int(row['pick_i_time_utc'] < '1984-03-01'),
                   non_z_channel_name=int(not row['channel_code'].endswith('Z')),
                   request_state='not submitted; retrieval paused for clarification',
                   provider_waveform_resource_id='')
    for row in pairs:
        for side in ('i', 'j'):
            pick = by_pick[row['pick_'+side+'_resource_id']]
            for field in ('event', 'origin', 'arrival', 'pick'):
                assert row[field+'_'+side+'_resource_id'] == pick[field+'_i_resource_id']
            assert row['pick_'+side+'_time_utc'] == pick['pick_i_time_utc']
            assert row[side] == pick['i']
            assert row['station' if side == 'i' else 'station_j'] == pick['station']
            assert row['channel_seed_id'] == pick['channel_seed_id']
            assert row['channel_fdsn_source_id'] == pick['channel_fdsn_source_id']
            for edge in ('start', 'end'):
                assert row['metadata_epoch_'+('j_' if side == 'j' else '')+edge] == pick['metadata_epoch_'+edge]
        left, right = (by_pick[row['pick_'+side+'_resource_id']] for side in ('i', 'j'))
        row.update(historical_cmw1_response_gap=max(left['historical_cmw1_response_gap'], right['historical_cmw1_response_gap']),
            before_documented_march_1984_archive=max(left['before_documented_march_1984_archive'], right['before_documented_march_1984_archive']),
            non_z_channel_name=max(left['non_z_channel_name'], right['non_z_channel_name']),
            orientation_i_status=left['orientation_status'], orientation_j_status=right['orientation_status'],
            waveform_measurement_status='not measured; unchanged catalog-derived difference')
    table(HERE/'identified_picks.csv.gz', picks)
    table(HERE/'identified_catalog_differences.csv.gz', pairs)
    epoch_rows = []
    for k in sorted(orientations):
        matching = [p for p in picks if int(p['station']) == k]
        epoch_rows.append(dict(stations[k], **orientations[k], pick_count=len(matching),
            first_request_utc=min(p['request_start_utc'] for p in matching),
            last_request_utc=max(p['request_end_utc'] for p in matching)))
    assert len(epoch_rows) == 372
    table(HERE/'identified_used_epochs.csv.gz', epoch_rows)
    # These are planned bodies, never a statement that providers received them.
    batches = []
    for stage, records, size in [('routing_station', epoch_rows, 25), ('responses', epoch_rows, 25),
                                ('routing_dataselect', epoch_rows, 25), ('availability', picks, 100),
                                ('waveforms', picks, 100)]:
        headers = {'routing_station': 'targetservice=station\nlevel=response\nformat=request\n',
                   'responses': 'level=response\nformat=xml\n',
                   'routing_dataselect': 'targetservice=dataselect\nformat=request\n',
                   'availability': 'format=json\n', 'waveforms': ''}[stage]
        endpoint = {'routing_station': 'https://service.earthscope.org/irisws/fedcatalog/1/query',
            'routing_dataselect': 'https://service.earthscope.org/irisws/fedcatalog/1/query',
            'responses': 'https://service.ncedc.org/fdsnws/station/1/query',
            'availability': 'https://service.ncedc.org/fdsnws/availability/1/query',
            'waveforms': 'https://service.ncedc.org/fdsnws/dataselect/1/query'}[stage]
        for first in range(0, len(records), size):
            part = records[first:first+size]
            lines, identifiers = [], []
            for n, row in enumerate(part):
                start = row.get('request_start_utc', row.get('first_request_utc'))
                end = row.get('request_end_utc', row.get('last_request_utc'))
                lines.append(' '.join([row['network_code'], row['station_code'], row['location_code'] or '--',
                    row['channel_code'], start.rstrip('Z'), end.rstrip('Z')]))
                native = [row] if 'pick_i_resource_id' in row else [p for p in picks if p['station'] == row['id']]
                identifiers.append(dict(request_line=len(headers.splitlines())+n+1,
                    channel_seed_id=row['channel_seed_id'], channel_fdsn_source_id=row['channel_fdsn_source_id'],
                    metadata_epoch_start=row['metadata_epoch_start'], metadata_epoch_end=row['metadata_epoch_end'],
                    native_pick_rows=[p['original_observation_index'] for p in native],
                    provider_pick_resource_ids=[p['pick_i_resource_id'] for p in native],
                    source_metadata_sha256=row.get('channel_source_sha256', row.get('source_sha256'))))
            body = headers+'\n'.join(lines)+'\n'
            metadata = dict(method='POST', endpoint=endpoint, status='planned; not submitted',
                content_type='text/plain', request_sha256=hashlib.sha256(body.encode('utf-8')).hexdigest(),
                batch_size_choice='client bound, not a provider limit',
                native_context_file='identified_picks.csv.gz', native_context_sha256=sha(HERE/'identified_picks.csv.gz'),
                identifier_basis='Provider pick IDs; standardized FDSN channel identifiers derived from exact native SEED codes; no provider waveform ID invented',
                rows=identifiers)
            batches.append(dict(stage=stage, batch=first//size, request_body=body, metadata=metadata))
    with (HERE/'planned_batches.json.gz').open('xb') as raw:
        with gzip.GzipFile(filename='', fileobj=raw, mode='wb', mtime=0) as compressed:
            compressed.write((json.dumps(batches, separators=(',', ':'))+'\n').encode('utf-8'))
    evidence = []
    for stem in ('earthscope', 'ncedc'):
        path = pin(ROOT/('data/authoritative/stations/investigation/cmw1_'+stem+'_station_all_epochs.xml'))
        meta = json.loads(pin(path.with_suffix('.xml.provenance.json')).read_text())
        pin(path.with_suffix('.xml.identifiers.json'))
        assert sha(path) == meta['sha256']
        starts = [c.get('startDate') for c in ET.parse(str(path)).getroot().findall('.//s:Channel', NS)]
        evidence.append(dict(file=str(path.relative_to(ROOT)), source_url=meta['source_url'],
            sha256=sha(path), earliest_channel_epoch=min(starts), returned_channel_epochs=len(starts)))
    for name in ('usgs_comcat', 'earthscope_fedcatalog', 'ncedc_availability', 'ncedc_dataselect', 'ncedc_historical_archive'):
        path = pin(ROOT/('data/authoritative/waveforms/discovery_001/'+name+'.html'))
        meta = json.loads(pin(path.with_suffix('.html.provenance.json')).read_text())
        assert sha(path) == meta['sha256']
    counts = {flag:dict(picks=sum(r[flag] for r in picks),catalog_differences=sum(r[flag] for r in pairs))
              for flag in ('historical_cmw1_response_gap','before_documented_march_1984_archive','non_z_channel_name')}
    from collections import Counter
    summary = dict(status='offline plan complete; observational retrieval paused for user clarification',
        network_requests=0, retained_events=len(events), retained_picks=len(picks), retained_catalog_differences=len(pairs),
        used_nslcs=len({p['channel_seed_id'] for p in picks}), used_native_epochs=len(epoch_rows),
        affected_counts=counts, all_pick_orientation_counts=dict(Counter(p['orientation_status'] for p in picks)),
        non_z_pick_orientation_counts=dict(Counter(p['orientation_status'] for p in picks if p['non_z_channel_name'])),
        historical_response_gap_evidence=evidence, batch_counts=dict(Counter(b['stage'] for b in batches)),
        planned_batch_manifest='planned_batches.json.gz', input_sha256=inputs,
        selections_changed=False, waveform_measurements_added=0,
        scope='Full original cohort preserved; request planning is not availability or calibration validation')
    for name, expected in inputs.items():
        assert sha(ROOT/name) == expected
    summary['source_sha256'] = sha(Path(__file__))
    summary['output_sha256'] = {str(p.relative_to(HERE)):sha(p) for p in sorted(HERE.rglob('*')) if p.is_file()}
    write_json(HERE/'summary.json', summary)
    print(json.dumps({k:summary[k] for k in ('retained_picks','retained_catalog_differences','affected_counts',
        'non_z_pick_orientation_counts','batch_counts')}, indent=2))


if __name__ == '__main__':
    main()
