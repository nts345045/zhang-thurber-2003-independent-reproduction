#!/usr/bin/env python3
"""Read saved baseline outputs only; no tracing, references or inverse solves."""
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys
from collections import Counter, defaultdict

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / 'data/hayward'


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1048576), b''):
            h.update(chunk)
    return h.hexdigest()


def table(name):
    with (DATA / name).open(newline='') as f:
        return list(csv.DictReader(f))


def near(a, b, tolerance=1e-10):
    assert abs(float(a) - float(b)) <= tolerance, (a, b)


def main():
    assert __debug__, 'Run without Python optimization.'
    review_path = Path(__file__).with_name('review.json')
    if review_path.exists():
        raise RuntimeError('Preserve existing review; use a fresh checker copy.')
    numerical = json.loads((DATA / 'numerical_review.json').read_text())
    manifest = json.loads((DATA / 'run_manifest.json').read_text())
    pins = dict(numerical['input_sha256'])
    for name, digest in manifest['sha256'].items():
        assert name not in pins or pins[name] == digest
        pins[name] = digest
    for name in ['run_manifest.json', 'rebuild_result.txt', 'numerical_review.json']:
        pins['data/hayward/' + name] = sha(DATA / name)
    pins[str(Path(__file__).resolve().relative_to(ROOT))] = sha(Path(__file__))
    assert 'Exit 0' in (DATA / 'rebuild_result.txt').read_text()
    for name, digest in pins.items():
        assert sha(ROOT / name) == digest, name

    obs, initial, stations, initial_grid = [table(n) for n in [
        'observations.csv', 'initial_events.csv', 'stations.csv', 'initial_grid.csv']]
    assert len(obs) == 58980 and len(initial) == 1092 and len(stations) == 372
    assert Counter(r['type'] for r in obs) == {'0': 14262, '1': 44718}
    for records in [initial, stations]:
        assert [int(r['id']) for r in records] == list(range(len(records)))
    associations = defaultdict(set)
    for q, o in enumerate(obs):
        for side in ['i', 'j']:
            i = int(o[side])
            if i < 0:
                assert side == 'j' and o['type'] == '0'
                continue
            k = int(o['station' if side == 'i' else 'station_j'])
            associations[i, k].add((q, side))
            assert o['event_' + side + '_resource_id'] == initial[i]['event_resource_id']
            assert o['origin_' + side + '_resource_id'] == initial[i]['origin_resource_id']
            for field in ['network_code', 'station_code', 'location_code', 'channel_code',
                          'channel_seed_id', 'channel_fdsn_source_id']:
                assert o[field] == stations[k][field]
            for part in ['start', 'end']:
                field = 'metadata_epoch_' + ('' if side == 'i' else 'j_') + part
                assert o[field] == stations[k]['metadata_epoch_' + part]
            assert o['channel_' + ('' if side == 'i' else 'j_') + 'source_sha256'] == stations[k]['source_sha256']
            assert o['pick_' + side + '_resource_id'] and o['arrival_' + side + '_resource_id']
    pairs = sorted(associations)
    assert len(pairs) == 14262
    samples = [pairs[n * (len(pairs) - 1) // 31] for n in range(32)]
    result = {'status': 'passed_saved_baseline_readback',
              'reviewer': 'earthscope_discovery',
              'scope': 'Original unguarded, straight-initialized legacy baseline; independent saved-table readback, no solver or reference rerun.',
              'solver_base_commit': manifest['base_commit'],
              'input_sha256': pins,
              'unique_native_ray_pairs': len(pairs),
              'sorted_native_pair_sha256': hashlib.sha256(''.join('%d,%d\n' % pair for pair in pairs).encode()).hexdigest(),
              'observation_counts': dict(Counter(r['type'] for r in obs)),
              'modes': {}}
    for mode in ['standard', 'dd', 'loc1d']:
        h, events, grid, rays, fd, ids, coverage = [table(mode + suffix) for suffix in [
            '_history.csv', '_events.csv', '_grid.csv', '_ray_convergence.csv',
            '_ray_derivatives.csv', '_ray_identifiers.csv', '_coverage.csv']]
        assert len(events) == len(initial) and len(grid) == len(initial_grid) == len(coverage) == 462
        for before, after in zip(initial, events):
            assert all(before[k] == after[k] for k in before if k not in ['x', 'y', 'z', 't'])
            assert all(math.isfinite(float(after[k])) for k in ['x', 'y', 'z', 't'])
        assert all(math.isfinite(float(r['v'])) and float(r['v']) > 0 for r in grid)
        assert all(math.isfinite(float(r['path_length'])) and float(r['path_length']) >= 0 for r in coverage)
        bounds = {k: (min(float(r[k]) for r in grid), max(float(r[k]) for r in grid)) for k in ['x', 'y', 'z']}
        assert all(all(bounds[k][0] <= float(r[k]) <= bounds[k][1] for k in bounds) for r in events)
        residual_squares = defaultdict(list)
        with (DATA / (mode + '_residuals.csv')).open(newline='') as f:
            n = 0
            for n, r in enumerate(csv.DictReader(f), 1):
                o = obs[n - 1]
                assert set(o) - {'value'} == set(r) - {'residual'}
                assert all(o[k] == r[k] for k in o if k != 'value')
                value = float(r['residual'])
                assert math.isfinite(value)
                residual_squares[r['type']].append(value * value)
            assert n == len(obs)
        rms = {k: math.sqrt(math.fsum(v) / len(v)) for k, v in residual_squares.items()}
        reported = numerical['modes'][mode]
        for k in rms:
            near(rms[k], reported['final_residual_rms_seconds'][k], 1e-12)
        assert [(int(r['event']), int(r['station'])) for r in rays] == samples
        found = defaultdict(set)
        for r in ids:
            i, k, q = int(r['event']), int(r['station']), int(r['observation_row'])
            side, d = r['observation_event_side'], int(r['diagnostic_row'])
            assert (i, k) == samples[d] and (q, side) in associations[i, k]
            assert (q, side) not in found[i, k]
            found[i, k].add((q, side))
            for prefix, original, skip in [('observation_', obs[q], ['i', 'j', 'station', 'type', 'value']),
                                            ('source_', events[i], ['id', 'x', 'y', 'z', 't']),
                                            ('receiver_', stations[k], ['id', 'x', 'y', 'z', 't'])]:
                assert all(r[prefix + key] == value for key, value in original.items() if key not in skip)
        assert len(ids) == 210 and all(found[pair] == associations[pair] for pair in samples)
        assert len(fd) == 24
        for r in fd:
            assert (int(r['event']), int(r['station'])) == samples[int(r['diagnostic_row'])]
            for setting in ['production', 'refined']:
                near(float(r[setting + '_derivative']) - float(r['finite_difference']), r[setting + '_error'], 1e-12)
        assert all(r['lsqr_converged'] == '1' for r in h)
        assert all(float(r['objective_after']) <= float(r['objective_before']) + 1e-8 for r in h)
        failed_sample_rows = [r for r in rays if r['production_converged'] != '1' or r['refined_converged'] != '1']
        entry = dict(event_count=len(events), residual_count=len(obs), native_metadata_all_match=True,
                     all_finite=True, outside_source_count=0,
                     face_counts={k + '_' + end: sum(float(r[k]) == bounds[k][j] for r in events)
                                  for k in bounds for j, end in enumerate(['min', 'max'])},
                     negative_geoid_depth_sources=sum(float(r['z']) < 0 for r in events),
                     residual_rms_seconds=rms, history_rows=len(h),
                     accepted_updates=sum(float(r['step_fraction']) > 0 for r in h),
                     last_preupdate_local_failures=int(h[-1]['ray_count']) - int(h[-1]['ray_converged_count']),
                     maximum_preupdate_local_failures=max(int(r['ray_count']) - int(r['ray_converged_count']) for r in h),
                     last_source_coordinate_step_km=float(h[-1]['location_step']),
                     sample_count=len(rays), sampled_native_associations=len(ids),
                     sampled_local_failures=failed_sample_rows,
                     sampled_max_time_refinement_seconds=max(abs(float(r['difference'])) for r in rays),
                     sampled_source_FD_component_max_s_per_km={s: max(abs(float(r[s + '_error'])) for r in fd) for s in ['production', 'refined']},
                     median_catalog_displacement_km=statistics.median(math.sqrt(sum((float(a[k]) - float(b[k])) ** 2 for k in ['x', 'y', 'z'])) for a, b in zip(initial, events)),
                     velocity_range_km_per_s=[min(float(r['v']) for r in grid), max(float(r['v']) for r in grid)])
        if mode == 'loc1d':
            assert all(float(a[k]) == float(b[k]) for a, b in zip(initial_grid, grid) for k in ['x', 'y', 'z'])
            entry['fixed_grid_max_serialization_difference_km_per_s'] = max(abs(float(a['v']) - float(b['v'])) for a, b in zip(initial_grid, grid))
            assert entry['fixed_grid_max_serialization_difference_km_per_s'] < 5e-12
        result['modes'][mode] = entry

    rows, columns = table('dd_linearization_rows.csv'), table('dd_linearization_columns.csv')
    final_events = table('dd_events.csv')
    assert len(rows) == 14262 and len(columns) == 4830
    seen = set()
    for n, r in enumerate(rows):
        q = int(r['observation_row'])
        assert int(r['row']) == n and obs[q]['type'] == '0' and q not in seen
        seen.add(q)
        assert all(r[k] == v for k, v in obs[q].items() if k not in ['j', 'type', 'value'])
        near(r['observed'], obs[q]['value'])
        near(float(r['observed']) - float(r['predicted']), r['residual'])
        near(float(r['ray_time']) + float(final_events[int(r['i'])]['t']), r['predicted'])
    assert seen == {q for q, r in enumerate(obs) if r['type'] == '0'}
    for n, r in enumerate(columns):
        assert int(r['column']) == n
        if n < 4 * len(final_events):
            i = int(r['event'])
            assert i == n // 4
            assert all(r['source_' + k] == v for k, v in final_events[i].items() if k not in ['id', 'x', 'y', 'z', 't'])
        else:
            assert int(r['node']) == n - 4 * len(final_events)
    nnz = 0
    with (DATA / 'dd_linearization_matrix.csv').open() as f:
        for r in csv.DictReader(f):
            i, j, v = int(r['row']), int(r['column']), float(r['value'])
            assert 0 <= i < len(rows) and 0 <= j < len(columns) and math.isfinite(v)
            if j < 4 * len(final_events):
                assert j // 4 == int(rows[i]['i'])
            nnz += 1
    resolution = table('absolute_resolution.csv')
    assert len(resolution) == 462
    assert all(all(math.isfinite(float(v)) for v in r.values()) for r in resolution)
    result['resolution_readback'] = dict(rows=len(rows), columns=len(columns), stored_entries=nnz,
        native_all_match=True, failed_rays=[r for r in rows if r['ray_converged'] != '1'],
        interpretation=numerical['resolution'])
    result['limitations'] = [
        'Integrity/readback pass is not a numerical convergence or scientific reproduction pass.',
        'Legacy trace is straight initialized and lacks the later inverse acceptance guard. It is distinct from the guarded integration runs.',
        'loc1d fixes velocity but uses staged catalog-DD weights; its catalog RMS increased, and it terminated after failed line searches.',
        'History diagnostics precede updates. DD accepts its final configured update with a 2.76144 km maximum coordinate step; no nonlinear stationarity certificate is supplied.',
        'The 32 deterministic final rays and centered 0.01 km source differences do not certify all rays or first arrivals. Perturbed-ray flags are not saved.',
        'The legacy local stop permits projected gradient below 1e-5 s/km when time change is below 1e-11 s, besides its 1e-7 gradient condition.',
        'Resolution is an absolute-pick, damped, fixed-weight, unconstrained-source linear calculation. Two final DD linearization rays retain failed local flags.',
        'Independent one-sigma pick calibration is assumed; active domain bounds, shared-pick correlations, station/model error, bias, nonlinearity and ray error are outside that covariance.',
        'Catalog displacement is not location error against truth; negative geoid depths are not necessarily above terrain.',
        'Plot files, plot source, figures and PDF were deliberately excluded during an independent presentation-only update.']
    for name, digest in pins.items():
        assert sha(ROOT / name) == digest, 'Changed while reading: ' + name
    review_path.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'status': result['status'], 'review_sha256': sha(review_path), 'input_count': len(pins)}))


if __name__ == '__main__':
    main()
