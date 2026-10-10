#!/usr/bin/env python3
"""Independent saved-table readback; no ray tracing or reference evaluation."""
import collections
import csv
import gzip
import hashlib
import itertools
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DATA = ROOT / 'data/development/loma_lon_initial_accuracy_001'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def main():
    summary = read(DATA / 'summary.json')
    assert sha(DATA / 'summary.json') == '27044f9a6e96a55706924eceb85f9a87ba4465ac5ae3e8ef8fb8c87d2637d7ac'
    assert summary['status'] == 'comparison_complete' and not summary['scientific_pass']
    assert not summary['overall_preflight_assessed']
    pins = dict(summary['output_sha256'])
    for name in ['summary.json', 'execution.json', 'controller_completion.json',
                 'failure_groups.json', 'packaging_receipt.json', 'README.md']:
        pins[name] = sha(DATA / name)
    for name, digest in pins.items():
        assert sha(DATA / name) == digest, name
    for original, frozen in summary['frozen_input_mapping'].items():
        raw = (DATA / frozen).read_bytes()
        if frozen.endswith('.gz') and not original.endswith('.gz'):
            raw = gzip.decompress(raw)
        assert hashlib.sha256(raw).hexdigest() == summary['input_source_sha256'][original], original
    execution = read(DATA / 'execution.json')
    controller = read(DATA / 'controller_completion.json')
    assert execution['status'] == controller['status'] == 'completed'
    assert execution['summary_sha256'] == controller['summary_sha256'] == pins['summary.json']
    assert controller['execution_sha256'] == pins['execution.json']
    assert controller['child_reaped'] and controller['child_return_code'] == 0
    assert summary['initial_matrix_command']['return_code'] == 0

    counts, groups = collections.Counter(), collections.Counter()
    failed, seen, maxima = [], set(), [0., 0.]
    with gzip.open(str(DATA / 'comparison.csv.gz'), 'rt') as cf, \
         gzip.open(str(DATA / 'inputs/preflight/dd_preflight_ray_status.csv.gz'), 'rt') as pf, \
         gzip.open(str(DATA / 'inputs/reference/references.csv.gz'), 'rt') as rf:
        for index, (row, native, ref) in enumerate(itertools.zip_longest(
                csv.DictReader(cf), csv.DictReader(pf), csv.DictReader(rf))):
            assert row is not None and native is not None and ref is not None
            key = (native['event'], native['station'])
            assert key not in seen and key == (ref['event'], ref['station'])
            seen.add(key)
            assert int(row['comparison_row']) == int(ref['pair_index']) == index
            assert all(row[k] == v for k, v in native.items())
            for k in set(native).intersection(ref):
                if k.startswith(('source_', 'receiver_')):
                    if k in {prefix + axis for prefix in ('source_', 'receiver_') for axis in 'xyzt'}:
                        # The frozen C++ CSV writer records numerical geometry
                        # with setprecision(12); provider metadata stays verbatim.
                        assert float(native[k]) == float(format(float(ref[k]), '.12g')), (index, k)
                    else:
                        assert native[k] == ref[k], (index, k)
            assert native['source_event_resource_id'] and native['source_origin_resource_id']
            seed = '.'.join(native['receiver_' + k] for k in
                            ['network_code', 'station_code', 'location_code', 'channel_code'])
            assert seed == native['receiver_channel_seed_id']
            assert native['receiver_channel_fdsn_source_id'] and native['receiver_metadata_epoch_start']
            assert ref['reference_complete'] == ref['reference_valid'] == ref['near_tie_count'] == '1'
            time_error = float(native['ray_time']) - float(ref['time_s'])
            delta = [float(native['source_d' + axis]) - float(ref['source_d' + axis + '_s_per_km'])
                     for axis in 'xyz']
            norm = math.sqrt(sum(v * v for v in delta))
            assert time_error == float(row['time_error_s'])
            assert norm == float(row['source_error_euclidean_norm_s_per_km'])
            assert all(delta[i] == float(row['source_d' + axis + '_error_s_per_km'])
                       for i, axis in enumerate('xyz'))
            flags = all(native[k] == '1' for k in ['ray_converged', 'ray_finite',
                'ray_initialization_attempted', 'ray_initialization_succeeded',
                'ray_path_in_domain', 'ray_exact_source_endpoint', 'ray_exact_receiver_endpoint'])
            assert flags and int(native['ray_path_points']) >= 2
            expected = {'time_limit_pass': abs(time_error) <= 2.5e-5,
                'source_vector_limit_pass': norm <= 3e-6,
                'original_flags_and_path_pass': flags,
                'scientific_pass': flags and abs(time_error) <= 2.5e-5 and norm <= 3e-6}
            for name, value in expected.items():
                assert int(row[name]) == int(value)
                counts[name] += value
            maxima = [max(maxima[0], abs(time_error)), max(maxima[1], norm)]
            if not expected['scientific_pass']:
                failed.append(index)
                groups['bottom' if float(native['source_z']) == 16 else 'interior'] += 1
                assert delta[2] < 0
    assert len(seen) == summary['rows'] == 37648
    assert failed == [r['comparison_row'] for r in summary['failures']]
    assert all(summary['counts'][k] == v for k, v in counts.items())
    assert maxima == [summary['maximum_absolute_time_error_s'],
                      summary['maximum_source_error_euclidean_norm_s_per_km']]
    assert dict(groups) == {'interior': 37, 'bottom': 13}
    for name, digest in pins.items():
        assert sha(DATA / name) == digest
    result = dict(status='passed_saved_readback', source_sha256=sha(Path(__file__)),
        summary_sha256=pins['summary.json'], input_sha256=pins,
        frozen_input_mappings_verified=len(summary['frozen_input_mapping']),
        rows_and_full_native_field_joins=len(seen), counts=dict(counts), failure_groups=dict(groups),
        maximum_absolute_time_error_s=maxima[0], maximum_source_error_s_per_km=maxima[1],
        failure_indices=failed, controller_reaped=True,
        limitations=['Saved evidence review only; no new numerical solver or reference evaluation.',
            'Numeric ray coordinates retain the frozen C++ writer\'s 12-significant-digit representation; provider metadata joins are exact.',
            'The prior independent reference review remains the basis for continuous reference eligibility.',
            'Both preflight sample stages and the guarded inversion are separate unfinished runs.',
            'These rays used the older frozen optimizer, not the subsequent integration correction.'])
    with (HERE / 'review.json').open('x') as f:
        json.dump(result, f, indent=2, allow_nan=False)
        f.write('\n')
    print(json.dumps({k: result[k] for k in ['status', 'rows_and_full_native_field_joins',
        'counts', 'failure_groups', 'maximum_absolute_time_error_s', 'maximum_source_error_s_per_km']}))


if __name__ == '__main__':
    main()
