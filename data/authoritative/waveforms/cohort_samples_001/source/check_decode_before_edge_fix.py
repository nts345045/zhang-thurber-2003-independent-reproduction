#!/usr/bin/env python3
"""Invented miniSEED controls for native sample support; never requests data."""
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('sample_acquisition', str(HERE / 'acquire.py'))
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
versions = module.environment()
import numpy as np
from obspy import Trace, Stream, UTCDateTime


def trace(start=0, count=500, rate=100, location='', quality='D', channel='EHZ'):
    t = Trace(np.arange(count, dtype=np.int32), header=dict(network='XX', station='TEST', location=location,
        channel=channel, sampling_rate=rate, starttime=UTCDateTime(2000, 1, 1) + start))
    t.stats.mseed = dict(dataquality=quality)
    return t


def raw(traces):
    buffer = io.BytesIO(); Stream(traces).write(buffer, format='MSEED', reclen=512)
    return buffer.getvalue()


def pick(location=''):
    return dict(original_observation_index='invented_0', channel_seed_id='XX.TEST.' + location + '.EHZ',
        channel_fdsn_source_id='FDSN:XX_TEST_' + location + '_E_H_Z',
        event_i_resource_id='urn:example:invented-event', pick_i_resource_id='urn:example:invented-pick',
        request_start_utc='2000-01-01T00:00:00Z', request_end_utc='2000-01-01T00:00:05Z',
        metadata_epoch_start='1999-01-01T00:00:00', metadata_epoch_end='2001-01-01T00:00:00',
        availability_sample_rates_hz='[100.0]', availability_quality_codes='["D"]')


def main():
    cases = [
        ('exact_empty_location', [trace()], pick(), True),
        ('preserved_location', [trace(location='02')], pick('02'), True),
        ('native_grid_offset_3ms', [trace(start=.003)], pick(), True),
        ('provider_padding', [trace(start=-1, count=700)], pick(), True),
        ('contiguous_records_standard_decoder', [trace(count=250), trace(start=2.5, count=250)], pick(), True),
        ('one_sample_gap', [trace(count=250), trace(start=2.51, count=249)], pick(), False),
        ('duplicate_overlap', [trace(), trace()], pick(), False),
        ('partial_quality_overlap', [trace(), trace(start=1, count=10, quality='R')], pick(), False),
        ('wrong_channel', [trace(channel='EHN')], pick(), False),
        ('wrong_rate', [trace(count=1000, rate=200)], pick(), False),
        ('wrong_quality', [trace(quality='R')], pick(), False),
        ('missing_last_sample', [trace(count=499)], pick(), False),
        ('missing_first_sample', [trace(start=.012)], pick(), False),
    ]
    short = pick(); short['metadata_epoch_end'] = '2000-01-01T00:00:04'
    cases.append(('epoch_crossing', [trace()], short, False))
    bad = trace(); bad.data = bad.data.astype(np.float32); bad.data[250] = np.nan
    cases.append(('nonfinite_samples', [bad], pick(), False))
    results = []
    for name, traces, native, expected in cases:
        data = raw(traces)
        try:
            decoded = module.decode(data, [native])
        except ValueError as error:
            accepted = False; detail = str(error)
        else:
            accepted = True; detail = decoded
            module.require(decoded['windows'][0]['native_pick'] == native, 'Native metadata changed')
            module.require(decoded['windows'][0]['sample_count'] == 500, 'Half-open count differs')
        module.require(accepted == expected, 'Unexpected fixture outcome: ' + name)
        results.append(dict(case=name, expected_acceptance=expected, accepted=accepted,
            invented_miniseed_sha256=hashlib.sha256(data).hexdigest(), detail=detail))
    result = dict(status='passed', scope='Invented XX.TEST records only; no provider records, queries or waveform correlation',
        versions=versions, checks=len(results), source_sha256={p.name:module.sha(p) for p in (Path(__file__), HERE/'acquire.py')}, results=results)
    module.save(HERE/'decode_checks.json', result)
    print(json.dumps(dict(status='passed', checks=len(results)), indent=2))


if __name__ == '__main__':
    main()
