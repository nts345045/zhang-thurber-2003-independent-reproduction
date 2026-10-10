#!/usr/bin/env python3
"""Retrieve two previously identified response epochs and bounded waveform windows."""
import argparse
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET

import requests

HERE = Path(__file__).resolve().parent
DISCOVERY = HERE.parent / 'discovery_001'
NS = {'s': 'http://www.fdsn.org/xml/station/1'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_xml(element):
    return [element.tag, sorted(element.attrib.items()), (element.text or '').strip(),
            [canonical_xml(child) for child in element]]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['responses', 'waveforms'])
    parser.add_argument('--fetch', action='store_true')
    args = parser.parse_args()
    manifest = json.loads((DISCOVERY / 'summary.json').read_text())
    for name, expected in manifest['output_sha256'].items():
        if sha(DISCOVERY / name) != expected:
            raise ValueError('Discovery source changed: ' + name)
    spec = importlib.util.spec_from_file_location('identified_retrieval', str(DISCOVERY / 'discover.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.HERE = HERE  # Reuse the pinned immutable-response writer in this fresh directory.
    results = []
    for prefix in ['', 'partner_']:
        context_file = DISCOVERY / (prefix + 'probe_identity.json')
        context = json.loads(context_file.read_text())
        saved_context = HERE / context_file.name
        if saved_context.exists():
            if sha(saved_context) != sha(context_file):
                raise ValueError('Native context changed')
        else:
            shutil.copyfile(str(context_file), str(saved_context))
        row = context['original_observation']
        params = dict(net=row['network_code'], sta=row['station_code'], loc=row['location_code'] or '--',
            cha=row['channel_code'], starttime=context['request_start_utc'].rstrip('Z'),
            endtime=context['request_end_utc'].rstrip('Z'), level='response', format='xml')
        url = requests.Request('GET', 'https://service.ncedc.org/fdsnws/station/1/query', params=params).prepare().url
        name = prefix + 'response.xml'
        body, provenance = module.retrieve(name, url, context, args.fetch if args.stage == 'responses' else False)
        if provenance['http_status'] != 200:
            raise ValueError('Missing full response metadata; stop for clarification')
        tree = ET.fromstring(body)
        channels = [(n, s, c) for n in tree.findall('s:Network', NS)
            for s in n.findall('s:Station', NS) for c in s.findall('s:Channel', NS)]
        if len(channels) != 1:
            raise ValueError('Response channel epoch is not unique; stop for clarification')
        network, station, channel = channels[0]
        if [network.get('code'), station.get('code'), channel.get('locationCode'), channel.get('code')] != [
                row[k] for k in ('network_code', 'station_code', 'location_code', 'channel_code')]:
            raise ValueError('Response SEED identity differs; stop for clarification')
        if (channel.get('startDate'), channel.get('endDate')) != (
                row['metadata_epoch_start'], row['metadata_epoch_end']):
            raise ValueError('Response native epoch differs; stop for clarification')
        response = channel.find('s:Response', NS)
        stages = response.findall('s:Stage', NS) if response is not None else []
        sample_rate = float(channel.findtext('s:SampleRate', namespaces=NS))
        if not stages or sample_rate != 100.0:
            raise ValueError('Required response stages or expected sample rate missing; stop for clarification')
        public_ids = [{'element': e.tag.split('}')[-1], 'attribute': k, 'value': v}
            for e in channel.iter() for k, v in e.attrib.items()
            if k.split('}')[-1] in ('resourceId', 'sourceID', 'publicID')]
        record = dict(channel_seed_id=row['channel_seed_id'], channel_fdsn_source_id=row['channel_fdsn_source_id'],
            identifier_basis='Derived FDSN channel identifier; no missing provider response ID is fabricated',
            metadata_epoch_start=channel.get('startDate'), metadata_epoch_end=channel.get('endDate'),
            provider_channel_and_response_resource_ids=public_ids, sample_rate_hz=sample_rate,
            response_stage_count=len(stages),
            canonical_response_sha256=hashlib.sha256(json.dumps(canonical_xml(response), separators=(',', ':')).encode()).hexdigest(),
            response_raw_file=name, response_raw_sha256=provenance['sha256'])
        module.attach_records(name, [record])
        print(name, 'exact epoch', 'stages', len(stages), 'sample rate', sample_rate, flush=True)
        if args.stage == 'waveforms':
            import numpy as np
            import obspy
            url = requests.Request('GET', 'https://service.ncedc.org/fdsnws/dataselect/1/query', params={
                k: v for k, v in params.items() if k not in ('level', 'format')}).prepare().url
            wave_name = prefix + 'waveform.mseed'
            raw, wave_meta = module.retrieve(wave_name, url, context, args.fetch)
            if wave_meta['http_status'] != 200:
                raise ValueError('Missing waveform samples; stop for clarification')
            stream = obspy.read(io.BytesIO(raw), format='MSEED')
            traces = []
            for trace in stream:
                if trace.id != row['channel_seed_id'] or trace.stats.sampling_rate != sample_rate:
                    raise ValueError('Waveform sample identity/rate mismatch; stop for clarification')
                if not np.isfinite(trace.data).all():
                    raise ValueError('Nonfinite decoded samples; stop for review')
                traces.append(dict(channel_seed_id=trace.id, channel_fdsn_source_id=row['channel_fdsn_source_id'],
                    provider_waveform_resource_id=None, metadata_epoch_start=row['metadata_epoch_start'],
                    metadata_epoch_end=row['metadata_epoch_end'], response_raw_file=name,
                    response_raw_sha256=provenance['sha256'], first_sample_utc=str(trace.stats.starttime),
                    last_sample_utc=str(trace.stats.endtime), sample_rate_hz=trace.stats.sampling_rate,
                    sample_count=trace.stats.npts, data_type=str(trace.data.dtype),
                    sample_min=float(trace.data.min()), sample_max=float(trace.data.max()),
                    decoded_sample_byte_order='little',
                    decoded_samples_sha256=hashlib.sha256(trace.data.astype(trace.data.dtype.newbyteorder('<')).tobytes()).hexdigest(),
                    miniseed_quality=trace.stats.mseed.get('dataquality'), miniseed_encoding=trace.stats.mseed.get('encoding')))
            if len(stream) != 1 or stream.get_gaps():
                raise ValueError('Overlapping or discontinuous samples; stop for review')
            module.attach_records(wave_name, traces)
            begin = obspy.UTCDateTime(context['request_start_utc'])
            end = obspy.UTCDateTime(context['request_end_utc'])
            if stream[0].stats.starttime > begin or stream[0].stats.endtime < end:
                raise ValueError('Waveform samples do not cover the requested window; stop for review')
            record.update(waveform_raw_file=wave_name, waveform_raw_sha256=wave_meta['sha256'], traces=traces,
                obspy_version=obspy.__version__, numpy_version=np.__version__)
            print(wave_name, len(raw), 'bytes', traces[0]['sample_count'], 'samples', flush=True)
        results.append(record)
    summary = dict(stage=args.stage, scope='Two previously selected native records; no measured waveform differential time',
        records=results, canonical_provider_responses_identical=results[0]['canonical_response_sha256'] == results[1]['canonical_response_sha256'],
        input_sha256={'discovery_001/summary.json': sha(DISCOVERY / 'summary.json'),
            'discovery_001/discover.py': sha(DISCOVERY / 'discover.py')},
        limitations=['Two records establish no full-cohort coverage.', 'No correlation delay or response correction is applied.',
            'Identical canonical provider response content is distinct from independent calibration verification.'])
    (HERE / (args.stage + '_summary.json')).write_text(json.dumps(summary, indent=2) + '\n')


if __name__ == '__main__':
    main()
