#!/usr/bin/env python3
"""Audit saved native measurement tables and arrays; never call the CC core."""
import argparse
from collections import Counter
import csv
import datetime as dt
from fractions import Fraction as Q
import gzip
import hashlib
import json
import math
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
TOL = 64 * 2.0 ** -52
STEP = 10_000_000
IDENTITY = ('network_code', 'station_code', 'location_code', 'channel_code',
            'channel_seed_id', 'channel_fdsn_source_id')
POSITION = ('x', 'y', 'z', 'latitude_deg', 'longitude_deg', 'sensor_z_geoid_km')
SIDE_FIELDS = ('original_observation_index', 'waveform_status', 'waveform_raw_file',
    'waveform_raw_sha256', 'window_samples_sha256', 'trace_index', 'first_sample_index',
    'stop_sample_index_exclusive', 'first_sample_unix_ns_rational', 'sample_rate_hz',
    'orientation_status', 'provider_dip_deg', 'response_status')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def table(path):
    opener = gzip.open if path.suffix == '.gz' else open
    with opener(str(path), 'rt', newline='') as f:
        return list(csv.DictReader(f))


def utc_ns(value):
    match = re.fullmatch(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d{1,9}))?Z', value)
    require(match is not None, 'Require an explicitly UTC native timestamp')
    seconds = dt.datetime.strptime(match[1], '%Y-%m-%dT%H:%M:%S') - dt.datetime(1970, 1, 1)
    return (seconds.days * 86400 + seconds.seconds) * 10**9 + int((match[2] or '').ljust(9, '0'))


def cell(row, key, value):
    require(row[key] == ('' if value is None else str(value)), 'Saved CSV field differs: ' + key)


def numeric_diagnostic(d, p, q, pair):
    """Reconstruct indices, selection and acceptance from saved curves only."""
    starts = [Q(x['first_sample_unix_ns_rational']) - utc_ns(x['pick_i_time_utc']) for x in (p, q)]
    require(all(x.denominator == 1 for x in starts), 'Unexpected fractional nanosecond grid')
    si, sj = map(int, starts)
    fractional = Q(-500_000_000 - si, STEP)
    index = fractional.numerator // fractional.denominator
    index += fractional - index > Q(1, 2)  # earlier sample on an exact tie
    template = si + index * STEP
    low = Q(template - 250_000_000 - sj, STEP)
    high = Q(template + 250_000_000 - sj, STEP)
    first = -(-low.numerator // low.denominator); last = high.numerator // high.denominator
    require(0 <= index and index + 256 <= int(p['sample_count']) and
        0 <= first <= last and last + 256 <= int(q['sample_count']), 'Incomplete declared search support')
    expected_indices = dict(template_sample_index=index, search_first_sample_index=first,
        search_last_window_index=last, template_start_from_pick_ns=template,
        search_start_from_pick_ns=sj + first * STEP,
        sample_i_start_from_own_pick_ns=si, sample_j_start_from_own_pick_ns=sj)
    require(all(d[k] == v for k, v in expected_indices.items()), 'Native extraction or grid offset differs')
    require(d['sample_spacing_s'] == .01 and d['formal_timing_uncertainty_s'] is None,
        'A timing uncertainty or spacing was changed')
    require(d['catalog_dt_i_minus_j_s'] == float(pair['value']), 'Catalog i-minus-j convention differs')
    coefficients = d['coefficients']; lags = d['lag_ns']
    require(len(coefficients) == last - first + 1 and lags ==
        [sj + (first + k) * STEP - template for k in range(len(coefficients))], 'Saved lag curve/grid differs')
    require(all(-250_000_000 <= x <= 250_000_000 for x in lags), 'A lag leaves the declared search')
    require(all(x is not None and math.isfinite(x) and abs(x) <= 1 + TOL for x in coefficients),
        'This audit expects the finite coefficient curves recorded in this real run')
    peak = max(coefficients); maxima = [k for k, x in enumerate(coefficients) if abs(x - peak) <= TOL]
    require(d['maximum_cc'] == peak and d['maximum_cc_squared'] == peak ** 2 and
        d['tied_peak_indices'] == maxima, 'Peak, ties or CC squared differs from the saved curve')
    if peak <= 0:
        expected_status = 'nonpositive_peak'
    elif len(maxima) != 1:
        expected_status = 'ambiguous_peak'
    elif maxima[0] in (0, len(coefficients) - 1):
        require(d['peak_index'] == maxima[0], 'Boundary peak index differs')
        expected_status = 'boundary_peak'
    else:
        k = maxima[0]; require(d['peak_index'] == k, 'Selected peak index differs')
        require(d['frequency_hz'] == [n * 100 / 256 for n in range(129) if 2 <= n * 100 / 256 <= 10],
            'Coherence frequency support differs')
        squared = d['squared_coherence']; require(len(squared) == 20, 'Coherence bin count differs')
        resolved = all(x is not None and math.isfinite(x) and 0 <= x <= 1 + TOL for x in squared)
        passing = sum(x is not None and x > .9 for x in squared)
        passed = resolved and 2 * passing >= len(squared)
        require(d['coherence_resolved'] == resolved and d['passing_bins'] == passing and
            d['evaluation_bins'] == len(squared) and d['coherence_pass'] == passed,
            'Strict coherence threshold/count arithmetic differs')
        delay = lags[k] / 1e9; candidate = float(pair['value']) - delay
        require(d['delay_j_minus_i_s'] == delay and d['candidate_dt_cc_i_minus_j_s'] == candidate,
            'Native-grid delay or catalog-minus-delay sign differs')
        expected_status = ('unresolved_coherence' if not resolved else
            'accepted_discrete_measurement' if passed else 'failed_coherence')
    require(d['status'] == expected_status, 'Recorded status differs from saved-array acceptance')
    accepted = expected_status == 'accepted_discrete_measurement'
    require(d['dt_cc_i_minus_j_s'] == (d['candidate_dt_cc_i_minus_j_s'] if accepted else None),
        'A rejected candidate was accepted or an accepted value differs')
    if expected_status in ('nonpositive_peak', 'ambiguous_peak', 'boundary_peak'):
        require(not any(k in d for k in ('delay_j_minus_i_s', 'candidate_dt_cc_i_minus_j_s',
            'squared_coherence')), 'An early rejected peak has a later-stage measurement')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--measurements', type=Path, required=True)
    args = parser.parse_args(); folder = args.measurements.resolve(); folder.relative_to(ROOT)
    output = folder / 'independent_measurement_review.json'
    require(not output.exists(), 'Preserve the existing independent review')
    pins = {}

    def pin(path, expected=None):
        path = path.resolve(); name = str(path.relative_to(ROOT)); digest = sha(path)
        require(expected is None or digest == expected, 'Pinned file changed: ' + name)
        require(name not in pins or pins[name] == digest, 'File changed during read: ' + name)
        pins[name] = digest; return path

    def load(path):
        return json.loads(pin(path).read_text())

    pin(Path(__file__))
    summary_path = folder / 'summary.json'; summary = load(summary_path)
    execution = load(folder / 'execution.json')
    require(summary['status'] == 'completed_identified_measurements' and execution['status'] == 'completed' and
        execution['summary_sha256'] == sha(summary_path) and execution['network_requests'] == 0,
        'Require a terminal, offline measurement result')
    require(summary['original_catalog_values_changed'] is False and summary['solver_observations_added'] == 0 and
        summary['dt_cc_exported'] is False, 'Measurement scope changed')
    for name, digest in summary['input_source_sha256'].items():
        pin(ROOT / name, digest)
    for name, digest in summary['output_sha256'].items():
        path = (folder / name).resolve(); path.relative_to(folder); pin(path, digest)
    command = execution['command']
    source_path = lambda flag: ROOT / command[command.index(flag) + 1]
    sample_path = source_path('--samples-summary'); samples = load(sample_path); sample_digest = sha(sample_path)
    sample_review_path = source_path('--samples-review'); sample_review = load(sample_review_path)
    require(summary['samples_summary_sha256'] == sha(sample_path) and sample_review['status'] == 'passed' and
        sample_review['samples_summary_sha256'] == sha(sample_path) and
        summary['samples_review_sha256'] == sha(sample_review_path), 'Sample audit/measurement links differ')
    plan_path = source_path('--plan'); plan = load(plan_path)
    pairs = table(pin(plan_path.parent / 'identified_catalog_differences.csv.gz'))
    original_picks = table(pin(plan_path.parent / 'identified_picks.csv.gz'))
    sample_name = next(iter(samples['output_sha256']))
    picks = table(pin(sample_path.parent / sample_name, samples['output_sha256'][sample_name]))
    epochs = table(pin(plan_path.parent / 'identified_used_epochs.csv.gz'))
    events = table(pin(source_path('--events')))
    require(len(pairs) == 44718 and len(picks) == len(original_picks) == 14262 and
        all(all(p[k] == v for k, v in original.items()) for p, original in zip(picks, original_picks)),
        'Original pick support or values differ')
    by_pick = {p['pick_i_resource_id']:p for p in picks}; by_epoch = {e['id']:e for e in epochs}
    by_event = {e['id']:e for e in events}
    require(len(by_pick) == len(picks) and len(by_epoch) == len(epochs) and len(by_event) == len(events), 'Duplicate native key')
    for p in picks:
        event, epoch = by_event[p['i']], by_epoch[p['station']]
        require(all(p[k] == epoch[k] for k in IDENTITY + ('metadata_epoch_start', 'metadata_epoch_end')) and
            p['channel_source_sha256'] == epoch['source_sha256'], 'Pick/receiver epoch identity differs')
        require(all(p[k + '_i_resource_id'] == event[k + '_resource_id'] for k in ('event', 'origin')), 'Origin identity differs')
        travel = Q(utc_ns(p['pick_i_time_utc']) - utc_ns(event['reference_origin_time_utc']), 10**9)
        require(float(p['value']) == float(travel), 'Absolute catalog travel time differs')
    rows = table(folder / 'identified_measurements.csv.gz')
    require(len(rows) == len(pairs), 'An original pair was omitted')
    counts = Counter(); attempted = 0; accepted = []; supported = 0; missing_pairs = 0
    expected_ids = set(); consumed_ids = set()
    with gzip.open(str(folder / 'attempted_diagnostics.jsonl.gz'), 'rt') as details:
        for row, pair in zip(rows, pairs):
            require({k[len('original_catalog_'):]:v for k, v in row.items() if k.startswith('original_catalog_')} == pair,
                'Original pair fields/order were modified')
            p, q = [by_pick[pair['pick_' + side + '_resource_id']] for side in ('i', 'j')]
            a, b = [by_epoch[pick['station']] for pick in (p, q)]
            require(float(pair['value']) == float(p['value']) - float(q['value']), 'Catalog differential sign differs')
            for side, pick in (('i', p), ('j', q)):
                require(pair[side] == pick['i'] and pair['station' if side == 'i' else 'station_j'] == pick['station'],
                    'Native numerical index differs')
                require(all(pair[k] == pick[k] for k in IDENTITY), 'Common SEED/resource identity differs')
                require(all(pair[k + '_' + side + '_resource_id'] == pick[k + '_i_resource_id']
                    for k in ('event', 'origin', 'pick', 'arrival')), 'Native pair resource identity differs')
                for bound in ('start', 'end'):
                    require(pair['metadata_epoch_' + ('j_' if side == 'j' else '') + bound] == pick['metadata_epoch_' + bound],
                        'Native epoch differs')
                for key in SIDE_FIELDS:
                    require(row['waveform_' + side + '_' + key] == pick[key], 'Waveform sidecar field differs: ' + key)
            both = all(x['waveform_status'] == 'decoded_native_samples' for x in (p, q)); supported += both
            missing_pairs += any(x['waveform_status'] == 'provider_returned_no_samples' for x in (p, q))
            reasons = []
            if any(float(a[k]) != float(b[k]) for k in POSITION):
                reasons.append('different_reported_receiver_position')
            for side, pick in (('i', p), ('j', q)):
                if pick['waveform_status'] != 'decoded_native_samples':
                    reasons.append('waveform_' + side + ':' + pick['waveform_status'])
                if pick['orientation_status'] != 'provider-declared vertical' or not pick['provider_dip_deg'] or abs(float(pick['provider_dip_deg'])) != 90:
                    reasons.append('orientation_' + side + ':' + pick['orientation_status'])
                if pick['waveform_status'] == 'decoded_native_samples' and float(pick['sample_rate_hz']) != 100:
                    reasons.append('unsupported_native_sample_rate_' + side)
            require(json.loads(row['cc_ineligibility_reasons_json']) == reasons, 'Unattempted reasons differ')
            mid = 'local:native-cc:' + sample_digest[:16] + ':' + pair['original_observation_index']
            require(row['measurement_id'] == mid and mid not in expected_ids, 'Derived measurement ID differs or repeats')
            expected_ids.add(mid)
            require(row['cc_formal_timing_uncertainty_s'] == '', 'An unsupported formal uncertainty was added')
            if reasons:
                require(row['measurement_status'] == 'not_attempted' and row['cc_attempted'] == '0' and
                    row['diagnostics_jsonl_row'] == '', 'An ineligible pair was measured')
                require(all(row[k] == '' for k in ('dt_cc_i_minus_j_s', 'cc_candidate_dt_i_minus_j_s',
                    'cc_delay_j_minus_i_s', 'maximum_cc', 'maximum_cc_squared', 'cc_relative_weight_squared',
                    'cc_sample_spacing_s', 'cc_passing_coherence_bins', 'cc_evaluation_coherence_bins')),
                    'An unattempted pair has measurement values')
            else:
                require(row['cc_attempted'] == '1' and row['diagnostics_jsonl_row'] == str(attempted), 'Attempt/diagnostic line differs')
                line = next(details, None); require(line is not None, 'Missing attempted diagnostic')
                record = json.loads(line); d = record['diagnostics']
                require(record['measurement_id'] == mid and mid not in consumed_ids and record['original_catalog'] == pair and
                    record['waveform_i'] == p and record['waveform_j'] == q and
                    record['receiver_epoch_i'] == a and record['receiver_epoch_j'] == b, 'Diagnostic full native join differs')
                consumed_ids.add(mid)
                require(d['ineligibility_reasons'] == [] and row['measurement_status'] == d['status'], 'Diagnostic status differs')
                numeric_diagnostic(d, p, q, pair)
                for csv_key, diagnostic_key in [('dt_cc_i_minus_j_s', 'dt_cc_i_minus_j_s'),
                    ('cc_candidate_dt_i_minus_j_s', 'candidate_dt_cc_i_minus_j_s'), ('cc_delay_j_minus_i_s', 'delay_j_minus_i_s'),
                    ('maximum_cc', 'maximum_cc'), ('maximum_cc_squared', 'maximum_cc_squared'),
                    ('cc_passing_coherence_bins', 'passing_bins'), ('cc_evaluation_coherence_bins', 'evaluation_bins')]:
                    cell(row, csv_key, d.get(diagnostic_key))
                cell(row, 'cc_sample_spacing_s', .01)
                is_accepted = d['status'] == 'accepted_discrete_measurement'
                cell(row, 'cc_relative_weight_squared', d['maximum_cc_squared'] if is_accepted else None)
                if is_accepted:
                    accepted.append(row)
                attempted += 1
            counts[row['measurement_status']] += 1
        require(next(details, None) is None, 'Extra diagnostic line has no original pair')
    require(attempted == supported == summary['attempted_pairs'] == 1195 and
        dict(counts) == summary['status_counts'] and len(rows) == summary['retained_original_catalog_pairs'],
        'Terminal support/status counts differ')
    controller = load(folder / 'run_controller.json')
    require(controller['status'] == 'completed' and controller['returncode'] == 0, 'Controller was not terminal successful')
    for name, digest in controller['output_sha256'].items():
        pin(folder / name, digest)
    correction = folder / 'run_controller_correction.json'
    require(correction.exists(), 'Preserve the stated controller bookkeeping correction before final review')
    correction_data = load(correction)
    require(correction_data['status'] == 'metadata_correction_preserving_original_record' and
        correction_data['original_run_controller_sha256'] == sha(folder / 'run_controller.json') and
        correction_data['field'] == 'samples_summary_sha256' and
        correction_data['original_value'] == controller['samples_summary_sha256'] and
        correction_data['correct_value'] == sample_digest and
        correction_data['samples_review_sha256_unchanged'] == controller['samples_review_sha256'] == sha(sample_review_path) and
        correction_data['numerical_summary_sha256'] == sha(summary_path) and
        correction_data['numerical_execution_sha256'] == sha(folder / 'execution.json') and
        correction_data['command_unchanged'] is True and correction_data['numerical_inputs_or_results_changed'] is False and
        controller['command'][1:] == execution['command'][1:], 'Controller correction does not bind the exact unchanged run')
    pin(folder / correction_data['frozen_controller_source_file'], correction_data['frozen_controller_source_sha256'])
    for name, digest in pins.items():
        require(sha(ROOT / name) == digest, 'Input changed during audit: ' + name)
    result = dict(status='passed', reviewer='earthscope_discovery',
        scope='Independent saved-table, native identity, hash and diagnostic-array arithmetic audit; no CC/FFT rerun, retrieval, export or solver import',
        measurements_summary_sha256=sha(summary_path), measurement_execution_sha256=sha(folder / 'execution.json'),
        review_source_sha256=sha(Path(__file__)), verified_file_sha256=pins,
        retained_original_catalog_pairs=len(rows), retained_original_picks=len(picks),
        pairs_with_both_decoded_samples=supported, attempted_pairs=attempted, accepted_measurements=len(accepted),
        status_counts=dict(counts), pairs_touching_provider_no_sample_records=missing_pairs,
        original_catalog_fields_and_order_unchanged=True, full_native_diagnostic_joins_match=True,
        all_attempts_have_unique_contiguous_diagnostic_lines=True, native_grid_and_lag_sign_checks_passed=True,
        peak_tie_cc_squared_and_coherence_acceptance_arithmetic_passed=True,
        formal_uncertainty_not_invented=True, solver_observations_added=0, material_issue_found=False,
        accepted_ranges={key:[min(float(row[key]) for row in accepted), max(float(row[key]) for row in accepted)]
            for key in ('maximum_cc', 'cc_delay_j_minus_i_s', 'dt_cc_i_minus_j_s', 'cc_relative_weight_squared')},
        controller_correction=correction_data,
        limitations=['Saved coefficient and coherence arrays are audited; this does not independently recompute NCC or FFT spectra.',
            'The discrete accepted measurements pass the declared screen; this is not formal timing precision, calibration equivalence, or exact manuscript-method reproduction.',
            'All missing/unattempted and rejected catalog rows remain present. No observations have been added to an inverse solve.'])
    with output.open('x') as f:
        json.dump(result, f, indent=2, allow_nan=False); f.write('\n')
    print(json.dumps(dict(status='passed', retained_pairs=len(rows), attempted=attempted,
        accepted=len(accepted), status_counts=dict(counts), review_sha256=sha(output)), indent=2))


if __name__ == '__main__':
    main()
