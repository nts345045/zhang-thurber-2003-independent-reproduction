#!/usr/bin/env python3
"""Stream-check identified analytic-truth simulation outputs, without solving rays."""
import argparse
import csv
import hashlib
import itertools
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
EPS = sys.float_info.epsilon
META = ['event_i_resource_id', 'origin_i_resource_id', 'event_j_resource_id',
        'origin_j_resource_id', 'network_code', 'station_code', 'location_code',
        'channel_code', 'channel_seed_id', 'channel_fdsn_source_id',
        'metadata_epoch_start', 'metadata_epoch_end', 'synthetic_observation',
        'observation_basis', 'source_position_basis', 'simulation_origin_time_basis',
        'event_geometry_table', 'receiver_geometry_table']
BASES = ['synthetic noisy absolute travel time',
         'synthetic difference of noisy absolute travel times',
         'synthetic difference of rounded noise-free travel times']
RAY = ['ray_converged', 'ray_finite', 'ray_projected_gradient', 'ray_raw_gradient',
       'ray_iterations', 'ray_merged_nodes', 'ray_initialization_attempted',
       'ray_initialization_succeeded', 'ray_selected_fmm_seed', 'ray_direct_seed_time',
       'ray_fmm_seed_time', 'ray_field_time', 'ray_extraction_fallback_steps',
       'ray_extraction_message']
REFERENCE = ['pair_index', 'event', 'station', 'reference_complete', 'reference_valid',
             'candidate_count', 'near_tie_count', 'time_s', 'branch', 'turning_x_km',
             'source_dx_s_per_km', 'source_dy_s_per_km', 'source_dz_s_per_km']
TRUTH_MODE = 'continuous_layered_snell_reference'


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1048576), b''):
            h.update(chunk)
    return h.hexdigest()


def reader(stream, expected=None):
    rows = csv.reader(stream)
    header = next(rows)
    require(len(header) == len(set(header)), 'Duplicate CSV column')
    if expected is not None:
        require(header == expected, 'Unexpected CSV schema')
    return header, rows


def table(path):
    with path.open(newline='') as stream:
        header, rows = reader(stream)
        rows = list(rows)
    require(all(len(row) == len(header) for row in rows), 'Malformed geometry CSV')
    return header, rows


def finite(text):
    value = float(text)
    require(math.isfinite(value), 'Nonfinite numerical output')
    return value


def decimal_half_unit(value):
    """Half the last decimal place for defaultfloat precision(12)."""
    return .5 * 10. ** (math.floor(math.log10(abs(value))) - 11) if value else 0.


def serialization_bound(value, operands=()):
    # Operand and result serialization bounds add under +/- operations. Four
    # eps times absolute magnitudes covers binary parsing and these few sums.
    values = (value,) + tuple(operands)
    return sum(decimal_half_unit(v) for v in values) + 4 * EPS * sum(abs(v) for v in values)


def close(saved, expected, operands=()):
    error = abs(saved - expected)
    bound = serialization_bound(saved, operands) + 4 * EPS * abs(expected)
    require(error <= bound, 'Value exceeds its CSV serialization/arithmetic bound')
    return error, bound


def round_away(value):
    magnitude = abs(value)
    integer = math.floor(magnitude)
    return math.copysign(integer + int(magnitude - integer >= .5), value)


def metadata(events, stations):
    event_ids = [[row[k] for k in ('event_resource_id', 'origin_resource_id')] for row in events]
    receiver_ids = [[row[k] for k in META[4:12]] for row in stations]
    suffix = [['1', basis, 'catalog-defined simulation truth',
               'zero for every truth event; no observed pick times',
               'truth_events.csv', 'stations.csv'] for basis in BASES]
    return event_ids, receiver_ids, suffix


def verify_metadata(values, i, j, k, kind, identities):
    event_ids, receiver_ids, suffix = identities
    require(values[:4] == event_ids[i] + (event_ids[j] if j >= 0 else ['', '']) and
            values[4:12] == receiver_ids[k] and values[12:] == suffix[kind],
            'Native identity, epoch or synthetic-basis mismatch')


def audit_payload(run):
    """Audit already-terminal files; the CLI additionally validates its ledger."""
    bundle = run / 'analytic_truth'
    require(not (run / 'simulation_ray_status.csv').exists(), 'Analytic truth has fabricated polygon-ray status')
    require((run / 'simulation_truth_mode.txt').read_text().splitlines()[0] == 'truth_mode ' + TRUTH_MODE,
            'Analytic truth mode missing')
    eh, er = table(bundle / 'inputs/truth_events.csv')
    sh, sr = table(bundle / 'inputs/stations.csv')
    require(eh[:5] == sh[:5] == ['id', 'x', 'y', 'z', 't'], 'Unexpected native geometry prefix')
    events = [dict(zip(eh, row)) for row in er]
    stations = [dict(zip(sh, row)) for row in sr]
    ne, ns = len(events), len(stations)
    require(ne > 0 and ns > 0, 'Missing native geometry')
    for rows in (events, stations):
        require(all(row['id'] == str(i) for i, row in enumerate(rows)), 'Native indices changed')
        require(all(finite(row['t']) == 0 for row in rows), 'Nonzero truth origin or receiver time')
    require(table(run / 'stations.csv') == (sh, sr), 'Receiver geometry changed')
    config = {}
    for line in (run / 'run.cfg').read_text().splitlines():
        fields = line.split('#', 1)[0].split()
        if fields:
            require(len(fields) == 2, 'Malformed run configuration')
            config[fields[0]] = finite(fields[1])
    quantum, pair_distance = config.get('time_quantum', .01), config['pair_distance']
    require(config['station_noise'] >= 0., 'Negative declared station-bias support')
    identities = metadata(events, stations)
    gh, gr = table(run / 'initial_grid.csv')
    require(gh == ['x', 'y', 'z', 'v'], 'Unexpected initial grid schema')
    bounds = [(min(finite(row[d]) for row in gr), max(finite(row[d]) for row in gr)) for d in range(3)]
    for name, basis in [('truth_events.csv', 'catalog-defined simulation truth'),
                        ('initial_events.csv', 'perturbed catalog-defined simulation truth')]:
        header, rows = table(run / name)
        require(len(rows) == ne and header[:5] == eh[:5], 'Saved source inventory changed')
        for i, row in enumerate(rows):
            saved = dict(zip(header, row))
            expected = dict(events[i], coordinate_basis=basis,
                origin_resource_id_basis='provider catalog geometry reference, not a simulated pick/origin identifier',
                simulation_origin_time_basis='truth t=0; initial/inverted t is a simulated correction in seconds')
            require(set(saved) == set(expected) and saved['id'] == str(i), 'Saved source schema/index changed')
            require(all(saved[k] == expected[k] for k in expected if k not in 'xyz' and k != 't'),
                    'Source metadata, including full-precision native coordinates, changed')
            for axis in 'xyz':
                value = finite(saved[axis])
                if name == 'truth_events.csv':
                    close(value, finite(events[i][axis]))
                else:
                    lo, hi = bounds['xyz'.index(axis)]
                    require(lo <= value <= hi, 'Initial source lies outside the prepared grid')
            finite(saved['t'])
            if name == 'truth_events.csv':
                require(float(saved['t']) == 0., 'Saved truth origin changed')
    ref_header = REFERENCE + ['source_' + k for k in eh] + ['receiver_' + k for k in sh]
    arrival_header = ['event', 'station', 'true_time', 'rounded_time', 'station_bias', 'pick_noise',
                      'absolute_time'] + META + RAY + ['truth_mode', 'reference_pair_index',
                      'reference_complete', 'reference_valid', 'reference_near_tie_count']
    arrivals, biases = [], [None] * ns
    maxima = dict(true_time_error_s=0., quantized_time_error_s=0., absolute_sum_error_s=0.,
                  absolute_observation_error_s=0., catalog_difference_error_s=0., precise_difference_error_s=0.)
    with (bundle / 'references.csv').open(newline='') as a, (run / 'simulation_truth_status.csv').open(newline='') as b, (run / 'arrivals.csv').open(newline='') as c:
        _, references = reader(a, ref_header)
        _, statuses = reader(b, ['truth_mode'] + ref_header)
        _, raw = reader(c, arrival_header)
        for n, triple in enumerate(itertools.zip_longest(references, statuses, raw)):
            ref, status, row = triple
            require(ref is not None and status is not None and row is not None, 'Truth/arrival support differs')
            require(len(ref) == len(ref_header) and len(row) == len(arrival_header), 'Malformed truth/arrival row')
            i, k = divmod(n, ns)
            require(i < ne and ref[:5] == [str(n), str(i), str(k), '1', '1'] and
                    int(ref[5]) >= 1 and ref[6] == '1', 'Invalid ordered reference')
            require(ref[13:] == er[i] + sr[k], 'Full-precision reference/native geometry changed')
            require(status == [TRUTH_MODE] + ref, 'Truth status differs from the full reference/native row')
            require(row[:2] == [str(i), str(k)], 'Arrival order changed')
            verify_metadata(row[7:25], i, -1, k, 0, identities)
            require(row[25:39] == [''] * 14 and row[39:] == [TRUTH_MODE, str(n), '1', '1', '1'],
                    'Ray flags fabricated or analytic-reference status changed')
            t, rounded, bias, noise, absolute = map(finite, row[2:7])
            require(abs(bias) <= config['station_noise'] + serialization_bound(bias),
                    'Station bias exceeds its declared uniform support and CSV bound')
            exact = finite(ref[7])
            for component in ref[10:13]: finite(component)
            target = round_away(exact / quantum) * quantum if quantum > 0 else exact
            error, _ = close(t, exact); maxima['true_time_error_s'] = max(maxima['true_time_error_s'], error)
            error, _ = close(rounded, target); maxima['quantized_time_error_s'] = max(maxima['quantized_time_error_s'], error)
            error, _ = close(absolute, rounded + bias + noise, (rounded, bias, noise))
            maxima['absolute_sum_error_s'] = max(maxima['absolute_sum_error_s'], error)
            require(biases[k] is None or biases[k] == row[4], 'Station bias varies across events')
            biases[k] = row[4]
            arrivals.append((absolute, rounded))
    require(len(arrivals) == ne * ns, 'Incomplete Cartesian arrival support')
    points = [[finite(row[k]) for k in 'xyz'] for row in events]
    pair_count = sum(math.sqrt(sum((a - b) ** 2 for a, b in zip(points[i], points[j]))) < pair_distance
                     for i in range(ne) for j in range(i + 1, ne))
    counts = [0, 0, 0]
    with (run / 'observations.csv').open(newline='') as stream:
        _, rows = reader(stream, ['i', 'j', 'station', 'type', 'value'] + META)

        def check(i, j, k, kind):
            row = next(rows, None)
            require(row is not None and len(row) == 23, 'Missing/malformed observation')
            require(row[:4] == [str(i), str(j), str(k), str(kind)], 'Observation support/type/order changed')
            verify_metadata(row[5:], i, j, k, kind, identities)
            value = finite(row[4]); a = arrivals[i * ns + k][0 if kind < 2 else 1]
            b = arrivals[j * ns + k][0 if kind < 2 else 1] if j >= 0 else 0.
            error, _ = close(value, a - b, (a, b))
            key = ['absolute_observation_error_s', 'catalog_difference_error_s', 'precise_difference_error_s'][kind]
            maxima[key] = max(maxima[key], error); counts[kind] += 1

        for i in range(ne):
            for k in range(ns): check(i, -1, k, 0)
        for i in range(ne):
            for j in range(i + 1, ne):
                if math.sqrt(sum((a - b) ** 2 for a, b in zip(points[i], points[j]))) < pair_distance:
                    for k in range(ns):
                        check(i, j, k, 1); check(i, j, k, 2)
        require(next(rows, None) is None, 'Extra observation rows')
    require(counts == [ne * ns, pair_count * ns, pair_count * ns], 'Observation count differs')
    return dict(source_count=ne, receiver_count=ns, arrival_count=len(arrivals), selected_event_pair_count=pair_count,
                observation_counts_by_type=counts, total_observations=sum(counts), all_native_fields_match=True,
                full_precision_reference_coordinates_preserved=True, truth_status_all_fields_exact=True,
                ray_status_fields_blank=True, quantization='binary64 T/q rounded to nearest integer, ties away from zero',
                serialization_error_bound='Sum of half-units in the final decimal place at 12 significant digits, plus 4 epsilon times operand/result magnitudes for binary arithmetic; not a scientific tolerance',
                maxima=maxima)


def terminal_inputs(run):
    ledger_path = run / 'simulation_execution.json'
    ledger = json.loads(ledger_path.read_text())
    require(ledger['status'] == 'completed' and ledger['return_code'] == 0 and
            ledger['result_status'] == 'simulation_complete_awaiting_independent_output_review',
            'Require terminal successful simulation execution, not live or failed outputs')
    stages = [row for row in ledger['completed_commands'] if row['stage'] == 'simulate']
    require(len(stages) == 1 and stages[0]['return_code'] == 0, 'No unique successful simulation command')
    prepared_path = run / 'analytic_truth_manifest.json'
    require(sha(prepared_path) == ledger['analytic_truth_manifest_sha256'], 'Prepared manifest changed')
    prepared = json.loads(prepared_path.read_text())
    require(prepared['status'] == 'prepared' and prepared['truth_mode'] == 'continuous_layered_reference',
            'Missing explicitly prepared analytic truth')
    outputs = ledger['output_sha256']
    required = {'truth_events.csv', 'initial_events.csv', 'arrivals.csv', 'observations.csv',
                'simulation_truth_status.csv', 'simulation_truth_mode.txt', 'authoritative_geometry',
                'simulation_run_manifest.json'}
    require(required <= set(outputs), 'Terminal output hash inventory incomplete')
    hashes = dict(outputs)
    mutable = {'truth_events.csv', 'authoritative_geometry'}
    for name, digest in prepared['prepared_sha256'].items():
        key = 'inputs_before_simulation/' + name if name in mutable else name
        require(key not in hashes or hashes[key] == digest, 'Conflicting prepared/output hashes')
        hashes[key] = digest
    require({'run.cfg', 'stations.csv', 'initial_grid.csv', 'analytic_truth/references.csv',
             'analytic_truth/inputs/truth_events.csv', 'analytic_truth/inputs/stations.csv'} <= set(hashes),
            'Prepared reference/geometry inventory incomplete')
    hashes['simulation_execution.json'] = sha(ledger_path)
    hashes['analytic_truth_manifest.json'] = sha(prepared_path)
    for name, digest in hashes.items():
        path = (run / name).resolve()
        path.relative_to(run.resolve())
        require(sha(path) == digest, 'Pinned artifact changed: ' + name)
    manifest = json.loads((run / 'simulation_run_manifest.json').read_text())
    require(manifest['prepared_manifest_sha256'] == hashes['analytic_truth_manifest.json'] and
            manifest['simulation_command'] == stages[0]['command'], 'Run provenance/command differs')
    require(sha(run / 'simulation_source.tar.gz') == manifest['source_archive_sha256'], 'Source archive changed')
    hashes['simulation_source.tar.gz'] = manifest['source_archive_sha256']
    return manifest, hashes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    run, output = [(ROOT / name).resolve() for name in (args.data, args.output)]
    run.relative_to(ROOT); output.relative_to(ROOT)
    require(not output.exists(), 'Preserve the prior independent review')
    manifest, hashes = terminal_inputs(run)
    result = audit_payload(run)
    expected = manifest['expected_counts']
    actual = dict(events=result['source_count'], receivers=result['receiver_count'],
                  unique_rays=result['arrival_count'], absolute_rows=result['observation_counts_by_type'][0],
                  catalog_rows=result['observation_counts_by_type'][1], precise_rows=result['observation_counts_by_type'][2],
                  total_rows=result['total_observations'])
    require(all(actual[k] == expected[k] for k in actual), 'Full declared simulation support differs')
    for name, digest in hashes.items():
        require(sha(run / name) == digest, 'Artifact changed during streaming review: ' + name)
    result.update(status='passed', reviewer='ray_math_review',
        scope='Exhaustive streaming numerical/native-identity audit of completed synthetic observations; no reference or ray rerun',
        input_sha256=hashes, review_source_sha256=sha(Path(__file__)),
        simulation_run_manifest_sha256=hashes['simulation_run_manifest.json'],
        simulation_execution_sha256=hashes['simulation_execution.json'],
        command='python3 diagnostics/review_loma_analytic_simulation.py --data ' + str(run.relative_to(ROOT)) +
                ' --output ' + str(output.relative_to(ROOT)),
        limitations=['The continuous reference and its mathematical/source reviews remain separate prerequisites.',
                     'This checks saved noise algebra, not a reimplementation of the C++ random-number generator.',
                     'Simulation completion does not establish inverse forward-ray accuracy or inversion convergence.'])
    with output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False); stream.write('\n')
    print(json.dumps({k: result[k] for k in ('status', 'arrival_count', 'total_observations', 'maxima')}, indent=2))


if __name__ == '__main__':
    main()
