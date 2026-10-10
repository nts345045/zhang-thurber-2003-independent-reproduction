#!/usr/bin/env python3
"""Invented miniSEED controls for native sample support; never requests data."""
import argparse
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='decode_checks_001.json')
    args = parser.parse_args()
    module.require(Path(args.output).name == args.output, 'Output must be a fresh local filename')
    cases = [
        ('exact_empty_location', [trace()], pick(), True),
        ('preserved_location', [trace(location='02')], pick('02'), True),
        ('native_grid_offset_3ms', [trace(start=.003)], pick(), True),
        ('provider_padding', [trace(start=-1, count=700)], pick(), True),
        ('contiguous_records_standard_decoder', [trace(count=250), trace(start=2.5, count=250)], pick(), True),
        ('one_sample_gap', [trace(count=250), trace(start=2.51, count=249)], pick(), False),
        ('duplicate_overlap', [trace(), trace()], pick(), False),
        ('partial_quality_overlap', [trace(), trace(start=1, count=10, quality='R')], pick(), False),
        ('alternate_grid_trailing_edge', [trace(), trace(start=4.995, count=1, quality='R')], pick(), False),
        ('alternate_grid_leading_edge', [trace(start=.003), trace(count=1, quality='R')], pick(), False),
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
    for mode in (False, True):
        for name, traces, native, expected in cases:
            data = raw(traces)
            try:
                decoded = module.decode(data, [native], record_no_samples=mode)
            except ValueError as error:
                accepted = False; detail = str(error)
            else:
                accepted = True; detail = decoded
                module.require(decoded['windows'][0]['native_pick'] == native, 'Native metadata changed')
                module.require(decoded['windows'][0]['sample_count'] == 500, 'Half-open count differs')
                module.require(not decoded['missing_windows'], 'An originally complete window became missing')
            module.require(accepted == expected, 'Unexpected fixture outcome: ' + name)
            results.append(dict(case=name, record_no_samples=mode, expected_acceptance=expected, accepted=accepted,
                invented_miniseed_sha256=hashlib.sha256(data).hexdigest(), detail=detail))
    later = pick(); later.update(original_observation_index='invented_1',
        event_i_resource_id='urn:example:invented-event-1', pick_i_resource_id='urn:example:invented-pick-1',
        request_start_utc='2000-01-01T00:00:10Z', request_end_utc='2000-01-01T00:00:15Z')
    adjacent = dict(later, request_start_utc='2000-01-01T00:00:05Z', request_end_utc='2000-01-01T00:00:10Z')
    extras = [
        ('absent_without_explicit_mode', [trace()], [pick(), later], False, False, None),
        ('absent_explicit_native_row', [trace()], [pick(), later], True, True, later),
        ('missing_end_sample_still_partial', [trace(), trace(start=10, count=499)], [pick(), later], True, False, None),
        ('one_returned_sample_still_partial', [trace(), trace(start=10, count=1)], [pick(), later], True, False, None),
        ('exact_end_sample_not_inside_missing_window', [trace(start=5)], [pick(), adjacent], True, True, pick()),
        ('exact_start_sample_is_partial_support', [trace(count=1), trace(start=10)], [pick(), later], True, False, None),
    ]
    for name, traces, native, mode, expected, missing in extras:
        data = raw(traces)
        try:
            decoded = module.decode(data, native, record_no_samples=mode)
        except ValueError as error:
            accepted = False; detail = str(error)
        else:
            accepted = True; detail = decoded
            module.require(decoded['missing_windows'] == [dict(status='provider_returned_no_samples',
                original_observation_index=missing['original_observation_index'], native_pick=missing)],
                'Missing native identity/status differs')
            ids = [r['original_observation_index'] for key in ('windows', 'missing_windows') for r in decoded[key]]
            module.require(len(ids) == len(set(ids)) == len(native) and
                set(ids) == {r['original_observation_index'] for r in native}, 'Disjoint full support differs')
        module.require(accepted == expected, 'Unexpected fixture outcome: ' + name)
        results.append(dict(case=name, record_no_samples=mode, expected_acceptance=expected, accepted=accepted,
            invented_miniseed_sha256=hashlib.sha256(data).hexdigest(), detail=detail))
    result = dict(status='passed', scope='Invented XX.TEST records only; no provider records, queries or waveform correlation',
        versions=versions, checks=len(results), source_sha256={p.name:module.sha(p) for p in (Path(__file__), HERE/'acquire.py')}, results=results)
    module.save(HERE/args.output, result)
    print(json.dumps(dict(status='passed', checks=len(results)), indent=2))


if __name__ == '__main__':
    main()
