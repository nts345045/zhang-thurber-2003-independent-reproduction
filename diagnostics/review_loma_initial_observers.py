#!/usr/bin/env python3
"""Saved-record readback only; never invokes a solver or reference enumerator."""
import csv
import difflib
import gzip
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAIRS = (3426, 24104)


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def rows(path):
    with path.open(newline='') as f:
        return list(csv.DictReader(f))


def load(path):
    return json.loads(path.read_text())


def audit(pair, raw):
    out = ROOT / ('data/development/loma_initial_failure_{}_001'.format(pair))
    s = load(out / 'summary.json')
    require(s['status'] == 'completed_with_original_flags_preserved', 'Nonterminal observer')
    require(s['pair_index'] == pair, 'Wrong pair index')
    require(all(r['status'] == 'completed' and r['return_code'] == 0 for r in s['commands']), 'Failed command')
    before = {'summary.json': sha(out / 'summary.json')}
    for names, base in ((s['input_sha256'], ROOT), (s['source_sha256'], out / 'source'),
                        (s['output_sha256'], out)):
        for name, digest in names.items():
            require(sha(base / name) == digest, 'Changed pinned file: ' + name)
    before.update(s['output_sha256'])
    manifest = load(out / 'inputs/preflight_run_manifest.json')
    require(sha(ROOT / manifest['binary']) == manifest['binary_sha256'] == s['frozen_binary_sha256'], 'Frozen binary')
    require(sha(Path(s['compiler'])) == s['compiler_sha256'] == manifest['compiler_sha256'], 'Compiler')
    require(sha(ROOT / s['commands'][1]['command'][0]) == s['binary_sha256'], 'Observer binary')
    for name, digest in manifest['source_sha256'].items():
        if name.startswith('src/'):
            require(s['source_sha256'][name] == digest, 'Frozen production source mismatch')
    identified = rows(out / 'identified_ray.csv')
    require(len(identified) == 1 and identified[0] == s['native_context'], 'Incomplete native context')
    context = identified[0]
    events, stations = rows(out / 'inputs/initial_events.csv'), rows(out / 'inputs/stations.csv')
    i, k = divmod(pair, len(stations))
    require((context['event'], context['station']) == (str(i), str(k)), 'Pair mapping')
    reconstructed = dict(raw)
    for prefix, row in [('source_', events[i]), ('receiver_', stations[k])]:
        for name, value in row.items():
            require(context['native_' + prefix + name] == value, 'Lost native field')
            reconstructed['native_' + prefix + name] = value
            if name not in ('id', 'x', 'y', 'z', 't'):
                require(raw[prefix + name] == value, 'Original metadata does not join')
        for axis in 'xyz':
            require(float(raw[prefix + axis]) == float(format(float(row[axis]), '.12g')), 'Raw serialized coordinate')
            reconstructed[prefix + axis + '_km'] = row[axis]
    reconstructed.update(observation_index=str(pair), observation_index_basis='local original event-times-receiver pair index, not a provider observation ID')
    require(context == reconstructed, 'Observer native mapping differs from declared full-row augmentation')
    require(context['source_t'] == events[i]['t'], 'Source origin correction changed')
    records = {name: rows(out / name) for name in ('results.csv', 'history.csv', 'paths.csv', 'path_gradient_checks.csv', 'cone_metric.csv')}
    for name, values in records.items():
        sidecar = load(out / (name + '.identifiers.json'))
        require(sidecar['file'] == name and sidecar['file_sha256'] == sha(out / name), 'Detached numeric table')
        require(sidecar['join_key'] == 'observation_index' and sidecar['join_value'] == str(pair), 'Wrong identifier join')
        require(sidecar['native_context'] == context and sidecar['context_csv'] == 'identified_ray.csv' and
                sidecar['context_sha256'] == sha(out / 'identified_ray.csv'), 'Changed identifier context')
        require(all(row['observation_index'] == str(pair) for row in values), 'Numerical row has wrong pair')
    results = records['results.csv']
    require(results == s['results'] and len(results) == 2, 'Incomplete method rows')
    require({r['initialization'] for r in results} == {'straight', 'fmm'}, 'Seed inventory')
    require(all(r['logged_matches_unobserved_variant'] == '1' for r in results), 'Recorded observer parity failed')
    selected = min(results, key=lambda row: float(row['time_s']))
    for name, key in [('time_s', 'ray_time'), ('projected_gradient', 'ray_projected_gradient'),
                      ('raw_gradient', 'ray_raw_gradient'), ('source_dx', 'source_dx'),
                      ('source_dy', 'source_dy'), ('source_dz', 'source_dz')]:
        require(float(format(float(selected[name]), '.12g')) == float(raw[key]), 'Selected 12-digit parity: ' + name)
    for name, key in [('updates', 'ray_iterations'), ('converged', 'ray_converged'),
                      ('merged_nodes', 'ray_merged_nodes'), ('path_nodes', 'ray_path_points')]:
        require(selected[name] == raw[key], 'Selected status parity')
    require((selected['initialization'] == 'fmm') == (raw['ray_selected_fmm_seed'] == '1'), 'Selected branch changed')
    for row in results:
        seed_time = 'ray_fmm_seed_time' if row['initialization'] == 'fmm' else 'ray_direct_seed_time'
        require(float(format(float(row['time_s']), '.12g')) == float(raw[seed_time]), 'Both-seed time parity')
    grid = rows(out / 'inputs/initial_grid.csv')
    bounds = [(min(float(r[a]) for r in grid), max(float(r[a]) for r in grid)) for a in 'xyz']
    run_checks = []
    for r in results:
        run = r['run_id']
        p = [row for row in records['paths.csv'] if row['run_id'] == run]
        h = [row for row in records['history.csv'] if row['run_id'] == run]
        require(len(p) == int(r['path_nodes']) and [int(row['node']) for row in p] == list(range(len(p))), 'Incomplete path')
        require(h[0]['phase'] == 'initial' and h[-1]['phase'] == 'final', 'Incomplete history')
        require(len([row for row in h if row['phase'] == 'accepted']) == int(r['updates']), 'Update inventory')
        for key in ('time_s', 'projected_gradient', 'raw_gradient', 'updates', 'path_nodes'):
            require(h[-1][key] == r[key], 'Final history/result mismatch')
        for axis in 'xyz':
            require(float(p[0][axis]) == float(events[i][axis]) and float(p[-1][axis]) == float(stations[k][axis]), 'Exact native endpoint')
        raw2, projected2 = 0.0, 0.0
        for n, row in enumerate(p):
            for axis, name in enumerate('xyz'):
                coordinate, gradient = float(row[name]), float(row['gradient_' + name])
                require(math.isfinite(coordinate) and bounds[axis][0] <= coordinate <= bounds[axis][1], 'Path coordinate/domain')
                if n in (0, len(p)-1):
                    require(math.isnan(gradient), 'Endpoint path-gradient sentinel changed')
                    continue
                require(math.isfinite(gradient), 'Nonfinite internal path gradient')
                raw2 += gradient*gradient
                direction = -gradient
                if ((coordinate <= bounds[axis][0]+1e-10 and direction < 0) or
                        (coordinate >= bounds[axis][1]-1e-10 and direction > 0)):
                    direction = 0.0
                projected2 += direction*direction
        raw_norm, projected_norm = math.sqrt(raw2), math.sqrt(projected2)
        require(raw_norm == float(r['raw_gradient']) and projected_norm == float(r['projected_gradient']), 'Saved gradient norm reconstruction')
        accepted = [row for row in h if row['phase'] == 'accepted']
        times = [float(h[0]['time_s'])]+[float(row['time_s']) for row in accepted]
        require(all(b <= a for a,b in zip(times,times[1:])), 'Accepted action increased')
        require(all(float(row['directional_slope']) < 0 for row in accepted), 'Nonnegative accepted slope')
        require(all(float(row['action_change_s']) == a-b for row,a,b in zip(accepted,times,times[1:])), 'Action change does not join')
        failed = [row for row in h if row['phase'] == 'line_search_failed']
        if r['converged'] == '1':
            require(projected_norm < 1e-7 or (accepted and float(accepted[-1]['action_change_s']) < 1e-11 and projected_norm < 1e-5), 'Unexplained original success flag')
        else:
            require(projected_norm >= 1e-7 and (failed or int(r['updates']) == int(r['max_updates'])), 'Unexplained original failure flag')
        require(all(int(row['line_search_evaluations']) == 24 for row in failed), 'Unexpected failed search budget')
        run_checks.append(dict(run_id=run, path_nodes=len(p), accepted_updates=len(accepted),
                               line_search_failure_rows=len(failed), original_converged=r['converged'],
                               time_s=float(r['time_s']), projected_L2=projected_norm,
                               raw_L2=raw_norm, exact_gradient_norm_reconstruction=True))
    # Independently reconstruct the saved diff from the two frozen functions.
    core = (out / 'source/src/core.hpp').read_text()
    start = core.index('Ray trace(const Grid &g,')
    trace = core[start:core.index('\nstruct Entry {', start)]
    observed = (out / 'source/diagnostics/observed_optimizer.hpp').read_text()
    diff = ''.join(difflib.unified_diff(trace.splitlines(True), observed.splitlines(True), fromfile='frozen_trace', tofile='observed_trace'))
    require(diff == (out / 'instrumentation.diff').read_text(), 'Instrumentation diff changed')
    driver = (out / 'source/diagnostics/check_ray_stopping.cpp').read_text()
    parity = driver[driver.index('bool matches='):driver.index(';\n    results<<', driver.index('bool matches='))]
    required_pairs = ['ray.'+key+'==control.'+key for key in ['time','path','gradient','raw_gradient','source','iterations','converged','dv','length','merged_nodes']]
    require(all(token in parity for token in required_pairs), 'Recorded equality omits path or arrays')
    require('Ray control=trace(g,a,b,spacing,budget,true,fmm?&seed.path:nullptr);' in driver, 'Parity not against unmodified trace')
    for name, digest in before.items(): require(sha(out / name) == digest, 'Artifact changed during review')
    for name, digest in s['input_sha256'].items(): require(sha(ROOT/name) == digest, 'Input changed during review')
    review = dict(status='passed_saved_evidence_review', material_issue_found=False,
                  scope='Read-only source and saved-table audit; no retracing, reference enumeration or inversion.',
                  summary_sha256=before['summary.json'], checker_sha256=sha(Path(__file__)),
                  checker_path=str(Path(__file__).resolve().relative_to(ROOT)),
                  pair_index=pair, native_identifiers={key:context[key] for key in ('event','station','source_event_resource_id','source_origin_resource_id','receiver_channel_seed_id','receiver_channel_fdsn_source_id','receiver_metadata_epoch_start','receiver_metadata_epoch_end')},
                  input_hashes_verified=len(s['input_sha256']), frozen_source_hashes_verified=len(s['source_sha256']),
                  output_hashes_verified=len(s['output_sha256']), native_rows_complete=True,
                  all_native_metadata_fields_preserved=True, original_catalog_coordinates_separately_preserved=True,
                  current_initial_geometry_used=True, source_t_excluded_from_pure_ray_time=True,
                  selected_12_digit_and_original_flags_match=True, both_seed_times_match=True,
                  observed_vs_unobserved_equality_records_passed=2,
                  equality_scope='Frozen driver compares floating-point values of path, source derivative, dv, length, action, gradients, updates, flag and merge count in process. Control arrays are not independently exported; this review checks the equality code and its saved true records, without rerunning it.',
                  rows={name:len(values) for name,values in records.items()}, runs=run_checks,
                  limitations=['No inference of global first arrival or a cause of nonconvergence.',
                               'Path-gradient NaNs occur only at fixed endpoints; history optional diagnostics retain their declared NaN sentinels.',
                               'Source/origin catalog identities describe authoritative geometry provenance, not invented simulated picks.',
                               'Local convergence and continuous-reference source accuracy remain distinct original flags.'],
                  pinned_output_sha256=s['output_sha256'])
    with (out / 'review.json').open('x') as f:
        json.dump(review,f,indent=2,allow_nan=False);f.write('\n')
    return dict(pair=pair, review_sha256=sha(out/'review.json'), rows=review['rows'], runs=run_checks)


def main():
    path=ROOT/'data/development/loma_lom_initial_accuracy_001/inputs/preflight/dd_preflight_ray_status.csv.gz'
    raw={}
    with gzip.open(str(path),'rt',newline='') as f:
        for index,row in enumerate(csv.DictReader(f)):
            if index in PAIRS: raw[index]=row
            if len(raw)==len(PAIRS): break
    require(set(raw)==set(PAIRS),'Incomplete original support')
    print(json.dumps([audit(pair,raw[pair]) for pair in PAIRS],indent=2))


if __name__=='__main__':
    main()
