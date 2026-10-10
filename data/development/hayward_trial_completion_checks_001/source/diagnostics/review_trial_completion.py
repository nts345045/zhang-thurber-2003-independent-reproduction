"""Saved candidate003 trial evidence; no forward calculation or scientific promotion."""
import math
from pathlib import Path

from run_loma_analytic_simulation import sha
from run_loma_initial_preflight import finite, require, rows

TRIAL_MAIN = 'a10dcdc300d9a4e43f6ae0cba2e354d7cec549438319cf411b577790b2373058'
EVENT_NUMERIC = ('id', 'x', 'y', 'z', 't')
FAILED_BASIS = 'independent failed forward evaluation at recorded coordinates; see companion context for evaluation phase'
TRIAL_BASIS = 'independent failed line_search_trial forward evaluation; not a final inversion result'
ACCEPTED_BASIS = 'independent last accepted inversion state, or starting state before the first accepted update'
REJECTION_FILES = ('ray_status', 'ray_failures', 'ray_paths', 'events', 'grid', 'context', 'accepted_events', 'accepted_grid')
SOLVE_FILES = ('accepted_events', 'accepted_grid', 'delta', 'weights', 'context')


def integer(value):
    n = int(value)
    require(str(n) == value and n >= 0, 'Invalid nonnegative integer: ' + value)
    return n


def shown(value, expected, digits=17):
    require(finite(value) == float(format(expected, '.' + str(digits) + 'g')), 'Recorded numeric value differs')


def metadata(row, reference, prefix='', basis=None):
    for name, value in reference.items():
        if name not in EVENT_NUMERIC:
            require(row[prefix + name] == (basis if name == 'coordinate_basis' and basis is not None else value),
                    'Native metadata differs: ' + prefix + name)
    if basis is not None:
        require(row[prefix + 'coordinate_basis'] == basis, 'Incorrect state coordinate basis')


def native(row, pair, events, stations):
    i, k = pair
    require(integer(row['event']) == i and integer(row['station']) == k, 'Ray native index/order differs')
    metadata(row, events[i], 'source_', FAILED_BASIS)
    metadata(row, stations[k], 'receiver_')


def review_trials(data, mode, config, history, matrix):
    """Consume only computed filenames. Ledger path strings never select a file.

    Exact 17-digit state/delta joins are distinct from the existing scientific
    ray limits. History has 12-digit serialization. No new accuracy cutoff is
    applied; successful final rays are enforced by the pinned zero-exit binary.
    """
    data = Path(data)
    require(mode in ('dd', 'loc1d', 'loc3d'), 'Unsupported trial completion mode')
    pinned, required_files = {}, set()

    def take(name):
        path = data / name
        require(path.is_file() and not path.is_symlink(), 'Missing/nonregular trial evidence: ' + name)
        pinned.setdefault(name, sha(path))
        return path

    def table(name):
        return list(rows(take(name)))

    events, stations, grid = [table(n) for n in ('initial_events.csv', 'stations.csv', 'initial_grid.csv')]
    observations = table('observations.csv')
    take(mode + '_history.csv'); take(mode + '_matrix_preflight.csv')
    require(events and stations and grid, 'Empty native geometry')
    for group in (events, stations):
        require([r['id'] for r in group] == list(map(str, range(len(group)))), 'Nonconsecutive native geometry indices')
    support = set()
    for r in observations:
        i, k, j = integer(r['i']), integer(r['station']), int(r['j'])
        require(i < len(events) and k < len(stations), 'Invalid native i-side')
        support.add((i, k))
        if j >= 0:
            # The actual loader uses k only when station_j is absent. An
            # explicitly present empty/negative differential station_j fails.
            k2 = integer(r['station_j']) if 'station_j' in r else k
            require(j < len(events) and k2 < len(stations), 'Invalid native j-side')
            support.add((j, k2))
    support = sorted(support)
    bounds = {a: (min(finite(r[a]) for r in grid), max(finite(r[a]) for r in grid)) for a in 'xyz'}
    locate = mode in ('loc1d', 'loc3d')
    n = 4 * len(events) + (0 if locate else len(grid))
    required_initializer = config.get('ray_initializer', 0) == 1

    def state(event_name, grid_name, basis):
        e, g = table(event_name), table(grid_name)
        require(len(e) == len(events) and len(g) == len(grid), 'State inventory differs')
        for a, b in zip(events, e):
            require(a['id'] == b['id'], 'State event index differs')
            metadata(b, a, basis=basis)
            for axis in 'xyz':
                require(bounds[axis][0] <= finite(b[axis]) <= bounds[axis][1], 'Source outside finite box')
            finite(b['t'])
        for a, b in zip(grid, g):
            require(all(finite(a[k]) == finite(b[k]) for k in 'xyz') and finite(b['v']) > 0, 'State grid geometry/velocity differs')
        return e, g

    def same_state(e, g, other_e, other_g):
        require(all(all(finite(a[k]) == finite(b[k]) for k in 'xyzt') for a, b in zip(e, other_e)), 'Accepted source states differ')
        require(all(finite(a['v']) == finite(b['v']) for a, b in zip(g, other_g)), 'Accepted model states differ')

    def stepped(e, g, delta, fraction):
        moved = [dict(r) for r in e]
        for i, r in enumerate(moved):
            for k, axis in enumerate('xyz'):
                r[axis] = str(min(bounds[axis][1], max(bounds[axis][0], finite(e[i][axis]) + fraction * delta[4*i+k])))
            r['t'] = str(finite(e[i]['t']) + fraction * delta[4*i+3])
        model = [dict(r) for r in g]
        if not locate:
            for k, r in enumerate(model):
                try:
                    r['v'] = str(finite(g[k]['v']) * math.exp(-fraction * delta[4*len(e)+k]))
                except OverflowError:
                    r['v'] = 'inf'
        return moved, model

    def snapshot(it, stage, before, h):
        prefix = mode + '_iteration_' + str(it) + '_solve'
        required_files.update(prefix + '_' + name + '.csv' for name in SOLVE_FILES)
        basis = 'independent accepted inversion state at iteration ' + str(it) + '; original unscaled solve recorded separately'
        accepted, model = state(prefix+'_accepted_events.csv', prefix+'_accepted_grid.csv', basis)
        context = table(prefix+'_context.csv')
        require(len(context) == 1, 'Solve context row count differs')
        c = context[0]
        require(c['mode'] == mode and integer(c['iteration']) == it and integer(c['stage']) == stage,
                'Solve context iteration/mode differs')
        require(integer(c['columns']) == n and integer(c['source_columns']) == 4*len(events) and
                integer(c['model_columns']) == n-4*len(events), 'Solve context dimensions differ')
        shown(c['objective_before'], before)
        require(c['lsqr_converged'] in ('0', '1') and integer(c['lsqr_iterations']) == integer(h['lsqr_iterations']), 'LSQR status differs')
        require(c['lsqr_converged'] == h['lsqr_converged'], 'LSQR convergence status differs')
        shown(h['lsqr_relative_normal_residual'], finite(c['lsqr_relative_normal_residual']), 12)
        shown(c['smoothing_weight'], config['smoothing']); shown(c['damping_parameter'], config['damping'])
        require(c['weight_basis'] == 'stage/robust/distance/prior row multipliers computed at the accepted state and fixed through this line search' and
                c['objective_basis'] == 'sum of squared fixed-weight data residuals plus final log-slowness smoothing; damping enters the solve only',
                'Snapshot changes the declared weight/objective basis')
        increments = table(prefix+'_delta.csv')
        require(len(increments) == n, 'Incomplete original solve increment')
        delta = []
        for q, r in enumerate(increments):
            require(integer(r['parameter_index']) == q, 'Duplicate/reordered solve column')
            delta.append(finite(r['increment']))
            if q < 4*len(events):
                i, component = divmod(q, 4)
                require(r['parameter_type'] == 'source' and r['event'] == str(i) and not r['node'] and
                        r['component'] == 'xyzt'[component] and not r['reference_v'], 'Invalid source increment identity')
                for key in 'xyzt': shown(r['reference_'+key], finite(accepted[i][key]))
                metadata(r, events[i], 'source_', basis)
            else:
                k = q-4*len(events)
                require(r['parameter_type'] == 'model' and r['node'] == str(k) and not r['event'] and
                        r['component'] == 'log_slowness' and not r['reference_t'], 'Invalid model increment identity')
                for key in 'xyzv': shown(r['reference_'+key], finite(model[k][key]))
                require(all(not v for key, v in r.items() if key.startswith('source_')), 'Model increment invents event identity')
        weight_rows = rows(take(prefix+'_weights.csv'))
        count = 0
        for q, r in enumerate(weight_rows):
            require(q < len(observations), 'Extra frozen observation weight')
            original = observations[q]
            require(integer(r['observation_index']) == q, 'Frozen weight row index differs')
            for key in ('i', 'j', 'station', 'type'): require(r[key] == original[key], 'Frozen weight numeric index differs')
            station_j = (int(original.get('station_j', original['station'])) if int(original['j']) >= 0 else -1)
            require(r['station_j'] == str(station_j), 'Frozen second receiver epoch differs')
            shown(r['value'], finite(original['value']))
            finite(r['current_residual']); require(finite(r['fixed_row_multiplier']) >= 0, 'Invalid fixed row multiplier')
            expected_metadata = {'original_'+k: v for k, v in original.items() if k not in ('i', 'j', 'station', 'type', 'value')}
            actual_metadata = {k: v for k, v in r.items() if k.startswith('original_')}
            require(actual_metadata == expected_metadata, 'Frozen original native observation metadata differs')
            count += 1
        require(count == len(observations), 'Incomplete frozen all-observation weights')
        return accepted, model, delta

    def rejected(it, ls, step, accepted, model, delta):
        prefix = mode + '_rejected_trial_it_' + str(it) + '_ls_' + str(ls)
        required_files.update(prefix+'_'+name+'.csv' for name in REJECTION_FILES)
        e, g = state(prefix+'_events.csv', prefix+'_grid.csv', TRIAL_BASIS)
        ae, ag = state(prefix+'_accepted_events.csv', prefix+'_accepted_grid.csv', ACCEPTED_BASIS)
        same_state(ae, ag, accepted, model)
        expected_e, expected_g = stepped(accepted, model, delta, step)
        same_state(e, g, expected_e, expected_g)
        context = table(prefix+'_context.csv')
        require(len(context) == 1, 'Trial context row count differs')
        c = context[0]
        require(c['mode'] == mode and integer(c['iteration']) == it and integer(c['line_search_trial']) == ls and
                c['phase'] == 'line_search_trial' and c['derivatives_requested'] == '0' and c['significant_digits'] == '17' and
                c['initialization_required'] == str(int(required_initializer)), 'Trial context differs')
        failed = {}; status_count = 0
        for q, r in enumerate(rows(take(prefix+'_ray_status.csv'))):
            require(q < len(support), 'Extra native ray status')
            pair = support[q]; native(r, pair, e, stations)
            i, k = pair
            for axis in 'xyz':
                shown(r['source_'+axis], finite(e[i][axis])); shown(r['receiver_'+axis], finite(stations[k][axis]))
            shown(r['source_t'], finite(e[i]['t']))
            finite(r['ray_time'])
            require(r['ray_converged'] in ('0', '1'), 'Invalid local flag')
            require(all(r[key] == '1' for key in ('ray_finite', 'ray_path_in_domain', 'ray_exact_source_endpoint', 'ray_exact_receiver_endpoint')),
                    'Rejected trial contains a nonlocal failure')
            require(r['ray_derivatives_evaluated'] == '0' and all(not r[k] for k in ('source_dx', 'source_dy', 'source_dz')),
                    'Trial invents evaluated source partials')
            for key in ('ray_projected_gradient', 'ray_raw_gradient'): require(finite(r[key]) >= 0, 'Invalid displayed gradient norm')
            for key in ('ray_iterations', 'ray_merged_nodes', 'ray_extraction_fallback_steps'): integer(r[key])
            for key in ('ray_initialization_attempted', 'ray_initialization_succeeded', 'ray_selected_fmm_seed'):
                require(r[key] in ('0', '1'), 'Invalid initialization flag')
            if required_initializer or r['ray_initialization_attempted'] == '1':
                require(r['ray_initialization_attempted'] == r['ray_initialization_succeeded'] == '1', 'Rejected trial has an initializer failure')
            points = integer(r['ray_path_points']); require(points > 0, 'Empty rejected path')
            if r['ray_converged'] == '0': failed[pair] = points
            status_count += 1
        require(status_count == len(support) and failed, 'Incomplete status support or no rejected local ray')
        roster = table(prefix+'_ray_failures.csv')
        require(len(roster) == len(failed), 'Failure roster count differs')
        for r, pair in zip(roster, sorted(failed)):
            native(r, pair, e, stations)
            require(r['reasons'] == 'local_stopping_failed' and r['derivatives_requested'] == '0' and
                    integer(r['expected_velocity_nodes']) == len(grid), 'Failure roster is not pure local stopping')
            integer(r['velocity_derivatives']); integer(r['path_lengths'])
        expected_nodes = ((pair, node) for pair in sorted(failed) for node in range(failed[pair]))
        path_count = 0
        for r in rows(take(prefix+'_ray_paths.csv')):
            expected = next(expected_nodes, None); require(expected is not None, 'Extra failed path node')
            pair, node = expected; native(r, pair, e, stations)
            require(integer(r['node']) == node, 'Failed path node order differs')
            i, k = pair
            for axis in 'xyz':
                value = finite(r[axis]); require(bounds[axis][0] <= value <= bounds[axis][1], 'Failed path leaves model box')
                if node == 0: shown(r[axis], finite(e[i][axis]))
                if node == failed[pair]-1: shown(r[axis], finite(stations[k][axis]))
            path_count += 1
        require(next(expected_nodes, None) is None, 'Incomplete failed path nodes')
        return prefix, len(failed), path_count

    require(history and len(history) == len(matrix), 'Missing history/matrix iterations')
    iterations = [integer(r['iteration']) for r in history]
    require(iterations == sorted(set(iterations)) and iterations[0] == 0 and
            iterations == [integer(r['iteration']) for r in matrix], 'History/matrix iteration join differs')
    quality_count = failure_count = node_count = snapshots = 0
    latest = None; expected_iteration = 0
    for h in history:
        it, stage = integer(h['iteration']), integer(h['stage'])
        require(it == expected_iteration and stage == min(2, int(it/config['stage_length'])), 'Iteration/stage progression differs')
        ledger_name = mode+'_iteration_'+str(it)+'_trials.csv'; required_files.add(ledger_name)
        ledger = table(ledger_name)
        require(0 < len(ledger) <= 12, 'Invalid existing trial budget')
        before = finite(ledger[0]['objective_before']); shown(h['objective_before'], before, 12)
        accepted_trial = None; quality = []; objective_count = 0
        for ls, r in enumerate(ledger):
            step = math.ldexp(1., -ls)
            require(integer(r['iteration']) == it and integer(r['stage']) == stage and integer(r['trial']) == ls,
                    'Duplicate/reordered trial ledger')
            shown(r['step_fraction'], step); shown(r['objective_before'], before)
            status = r['status']
            require(status in ('invalid_trial_model', 'local_stopping_rejected', 'objective_rejected', 'accepted'), 'Unknown trial status')
            evaluated = status in ('objective_rejected', 'accepted')
            require(r['objective_evaluated'] == str(int(evaluated)), 'Objective status differs')
            if evaluated:
                objective_count += 1; after = finite(r['objective_after'])
                require((after <= before) == (status == 'accepted'), 'Objective acceptance criterion differs')
            else: require(not r['objective_after'], 'Rejected trial assigned an objective')
            if status == 'local_stopping_rejected':
                expected = mode+'_rejected_trial_it_'+str(it)+'_ls_'+str(ls)
                recorded = Path(r['failure_prefix'])
                require(recorded.name == expected and '..' not in recorded.parts, 'Ledger failure prefix differs')
                quality.append(ls)
            else: require(not r['failure_prefix'], 'Nonrejected trial has failure artifacts')
            if status == 'accepted':
                require(ls == len(ledger)-1, 'Accepted trial is not last'); accepted_trial = r
        require(accepted_trial is not None or len(ledger) == 12, 'Incomplete unsuccessful line search')
        require(not quality or objective_count > 0, 'No objective-evaluable trial after quality rejection')
        shown(h['step_fraction'], finite(accepted_trial['step_fraction']) if accepted_trial else 0, 12)
        shown(h['objective_after'], finite(accepted_trial['objective_after']) if accepted_trial else before, 12)
        if quality:
            snapshots += 1; ae, ag, delta = snapshot(it, stage, before, h)
            for ls in quality:
                latest, failures, nodes = rejected(it, ls, math.ldexp(1., -ls), ae, ag, delta)
                quality_count += 1; failure_count += failures; node_count += nodes
        expected_iteration = it+1 if accepted_trial else ((stage+1)*int(config['stage_length']))
    require(expected_iteration >= int(config['iterations']) or (not accepted_trial and stage == 2),
            'History ends before the configured loop finishes')
    actual_files = {p.name for p in data.iterdir() if p.name.startswith((mode+'_iteration_', mode+'_rejected_trial', mode+'_last_accepted'))}
    if latest:
        for kind in ('events', 'grid'):
            name = mode+'_last_accepted_'+kind+'.csv'; required_files.add(name)
            require(take(name).read_bytes() == take(latest+'_accepted_'+kind+'.csv').read_bytes(), 'Conventional accepted snapshot is stale')
    require(actual_files == required_files, 'Missing/orphan trial, solve or last-accepted artifact: '+str(sorted(actual_files ^ required_files)))
    require(not list(data.glob(mode+'_failed_forward*')), 'Fatal failure evidence cannot coexist with completion')
    for name, digest in pinned.items(): require(sha(data/name) == digest, 'Trial evidence changed during readback: '+name)
    return dict(history_iterations=len(history), trial_ledgers=len(history), retriable_trials=quality_count,
                solve_snapshots=snapshots, rejected_native_ray_instances=failure_count, failed_path_nodes=node_count,
                artifact_sha256=pinned, orphan_files=0,
                limitation='Saved trial closure only; no recomputation of forward residuals, first arrivals or final-model accuracy.')
