#!/usr/bin/env python3
"""Quantitative audit of saved results; emits machine-readable and LaTeX tables."""
import csv
import argparse
import hashlib
import json
import sys
from pathlib import Path
import numpy as np

D = Path('data/synthetic')

def load_table(path, text_fields=()):
    data = np.atleast_1d(np.genfromtxt(path, delimiter=',', names=True,
                                     dtype=None if text_fields else float,
                                     encoding='utf8'))
    if data.size == 0 or data.dtype.names is None:
        raise RuntimeError('{} contains no tabulated results'.format(path))
    for field in data.dtype.names:
        if field not in text_fields:
            values = np.asarray(data[field], dtype=float)
            if not np.all(np.isfinite(values)):
                raise RuntimeError('{} field {} contains nonfinite results'.format(path, field))
    return data

def load(name):
    return load_table(D / name)

def stats(a):
    a = np.asarray(a, dtype=float)
    if a.size == 0 or not np.all(np.isfinite(a)):
        raise RuntimeError('Statistics require a nonempty array of finite values')
    with np.errstate(over='raise', invalid='raise', divide='raise'):
        return dict(mean=float(np.mean(a)), median=float(np.median(a)),
                    std=float(np.std(a)), rms=float(np.sqrt(np.mean(a*a))),
                    max=float(np.max(a)))

def esc(s):
    return str(s).replace('_', r'\_').replace('&', r'\&').replace('%', r'\%').replace('#', r'\#')

def aligned(a, b, fields, label):
    if len(a) != len(b) or any(not np.array_equal(a[k], b[k]) for k in fields):
        raise RuntimeError('{} rows or coordinates do not match'.format(label))

def location_error(events, truth):
    aligned(events, truth, ('id',), 'Event identities')
    return np.sqrt(sum((events[k]-truth[k])**2 for k in ['x', 'y', 'z']))

def boundary_count(events, grid):
    boundary = np.zeros(len(events), dtype=bool)
    for key in ['x', 'y', 'z']:
        boundary |= ((events[key] <= min(grid[key])+1e-6)
                     | (events[key] >= max(grid[key])-1e-6))
    return int(np.sum(boundary))

def linear_diagnostics(history):
    flags = history['lsqr_converged']
    residual = history['lsqr_relative_normal_residual']
    if np.any((flags != 0) & (flags != 1)) or np.any(residual < 0):
        raise RuntimeError('Invalid LSQR convergence diagnostics')
    return dict(solves=len(history), converged=int(np.sum(flags == 1)),
                unconverged=int(np.sum(flags == 0)),
                max_iterations=int(max(history['lsqr_iterations'])),
                worst_relative_normal_residual=float(max(residual)),
                tolerance=1e-8,
                all_converged=bool(np.all(flags == 1)))

def inversion_metrics(directory, mode, truth):
    events = load_table(directory / (mode+'_events.csv'))
    residual = load_table(directory / (mode+'_residuals.csv'))
    history = load_table(directory / (mode+'_history.csv'))
    slices = load_table(directory / (mode+'_slices.csv'))
    grid = load_table(directory / (mode+'_grid.csv'))
    aligned(events, truth, ('id',), 'Event identities')
    m = dict(location={key: stats(abs(events[key]-truth[key])) for key in ['x','y','z']},
             location_3d=stats(location_error(events, truth)),
             residual={str(t): stats(residual['residual'][residual['type']==t]) for t in range(3)},
             velocity_full_domain=stats(abs(slices['error'])),
             velocity_range=[float(min(grid['v'])),float(max(grid['v']))],
             boundary_sources=boundary_count(events, grid),
             zero_updates=int(np.sum(history['step_fraction']==0)),
             objective_increases=int(np.sum(history['objective_after'] > history['objective_before'] + 1e-8)),
             lsqr=linear_diagnostics(history))
    inside = ((slices['x']>=-15)&(slices['x']<=20)&(slices['y']>=-40)&
              (slices['y']<=20)&(slices['z']>=3)&(slices['z']<=11))
    m['velocity_interior'] = stats(abs(slices['error'][inside]))
    if m['objective_increases']:
        raise RuntimeError('Accepted objective increase in {}'.format(directory / mode))
    if np.any(grid['v'] <= 0):
        raise RuntimeError('Nonpositive recovered velocity in {}'.format(directory / mode))
    return m

def ray_diagnostics(prefix):
    ray = load(prefix+'_convergence.csv')
    derivative = load(prefix+'_derivatives.csv')
    result = dict(rays=len(ray), time_refinement_seconds=stats(abs(ray['difference'])),
                  derivative_components=len(derivative),
                  derivative_components_skipped_at_boundaries=24-len(derivative),
                  derivative_diagnostic_tolerance_seconds_per_km=0.003)
    for setting in ['production', 'refined']:
        flags = ray[setting+'_converged']
        if np.any((flags != 0) & (flags != 1)):
            raise RuntimeError('Invalid ray convergence flag')
        error = abs(derivative[setting+'_error'])
        result[setting] = dict(
            projected_gradient_seconds_per_km=stats(ray[setting+'_gradient']),
            raw_gradient_seconds_per_km=stats(ray[setting+'_raw_gradient']),
            converged=int(np.sum(flags == 1)), unconverged=int(np.sum(flags == 0)),
            max_iterations=int(max(ray[setting+'_iterations'])),
            total_merged_nodes=int(sum(ray[setting+'_merged'])),
            source_derivative_error_seconds_per_km=stats(error),
            source_derivative_components_over_tolerance=int(np.sum(error > 0.003)))
    return result

def analyze_hayward(directory=Path('data/hayward'), report=Path('report'), required=False):
    """Audit completed identified field results without imposing recovery gates."""
    directory, report = Path(directory), Path(report)
    methods = ['standard', 'dd', 'loc1d']
    names = ['figure_metrics.json', 'absolute_resolution_manifest.json',
             'absolute_resolution.csv', 'initial_events.csv', 'initial_grid.csv',
             'stations.csv', 'observations.csv', 'selection_manifest.json', 'dd_linearization_rows.csv']
    for mode in methods:
        names += [mode + suffix for suffix in ['_events.csv', '_grid.csv', '_residuals.csv',
                  '_history.csv', '_ray_convergence.csv', '_ray_derivatives.csv', '_ray_identifiers.csv']]
    missing = [name for name in names if not (directory / name).exists()]
    if missing:
        if required or (directory / 'figure_metrics.json').exists():
            raise RuntimeError('Incomplete Hayward results: ' + ', '.join(missing))
        return None
    hashes = {}

    def record(path):
        path = Path(path)
        value = hashlib.sha256(path.read_bytes()).hexdigest()
        hashes[str(path)] = value
        return value

    def finite_json(name):
        path = directory / name
        record(path)
        def invalid(value):
            raise RuntimeError('{} contains nonfinite JSON value {}'.format(path, value))
        return json.loads(path.read_text(), parse_constant=invalid)

    def table(name, fields=None, empty=False, nan_fields=()):
        path = directory / name
        record(path)
        with path.open(newline='') as f:
            reader = csv.DictReader(f)
            columns = reader.fieldnames
            rows = list(reader)
        if not columns or (not rows and not empty):
            raise RuntimeError('{} contains no tabulated results'.format(path))
        fields = columns if fields is None else fields
        values = {}
        for key in fields:
            if key not in columns:
                raise RuntimeError('{} lacks {}'.format(path, key))
            a = np.array([float(r[key]) for r in rows])
            valid = np.isfinite(a) | (np.isnan(a) if key in nan_fields else False)
            if not np.all(valid):
                raise RuntimeError('{} field {} contains nonfinite modeled results'.format(path, key))
            values[key] = a
        return rows, values

    def summary(values):
        a = np.asarray(values, dtype=float)
        if not a.size:
            return None
        result = stats(a)
        result.update(count=int(a.size), min=float(np.min(a)))
        return result

    def flags(values, label):
        if np.any((values != 0) & (values != 1)):
            raise RuntimeError('Invalid {} convergence flags'.format(label))
        return int(np.sum(values == 1))

    def initializer_audit(rows, prefix):
        names = ['initialization_attempted', 'initialization_succeeded', 'selected_fmm_seed',
                 'direct_seed_time', 'fmm_seed_time', 'field_time',
                 'extraction_fallback_steps', 'extraction_message']
        if not rows or not any(prefix+name in rows[0] for name in names):
            return dict(available=False)
        if any(prefix+name not in rows[0] for name in names):
            raise RuntimeError('Incomplete initializer diagnostics: ' + prefix)
        values = {name: np.array([float(r[prefix+name]) for r in rows]) for name in names[:-1]}
        attempted, succeeded, selected = [values[name] for name in names[:3]]
        for name in names[:3]:
            flags(values[name], prefix+name)
        if np.any(succeeded > attempted) or np.any(selected > succeeded):
            raise RuntimeError('Inconsistent initializer flags: ' + prefix)
        fallback = values['extraction_fallback_steps']
        if np.any(~np.isfinite(fallback)) or np.any(fallback < 0) or np.any(fallback != np.floor(fallback)):
            raise RuntimeError('Invalid initializer fallback count: ' + prefix)
        for name in ['direct_seed_time', 'fmm_seed_time', 'field_time']:
            value = values[name]
            if np.any(np.isinf(value)):
                raise RuntimeError('Infinite initializer diagnostic: ' + prefix+name)
        if (np.any(~np.isfinite(values['direct_seed_time'][attempted == 1])) or
                np.any(~np.isfinite(values['field_time'][succeeded == 1])) or
                np.any(~np.isfinite(values['fmm_seed_time'][selected == 1]))):
            raise RuntimeError('Missing time for a used initializer candidate: ' + prefix)
        # A disabled initializer or an unavailable candidate has no finite time.
        # Coincident endpoints also need no separately bent FMM candidate.
        failures = [r for r, a, s in zip(rows, attempted, succeeded) if a and not s]
        return dict(available=True, rows=len(rows), attempted=int(sum(attempted)),
                    succeeded=int(sum(succeeded)), failed=len(failures),
                    selected_fmm=int(sum(selected)), total_extraction_fallback_steps=int(sum(fallback)),
                    failed_extraction_rows=failures)

    figures = finite_json('figure_metrics.json')
    resolution = finite_json('absolute_resolution_manifest.json')
    selection = finite_json('selection_manifest.json')
    # A report must not silently join a new model to old plots or resolution.
    missing_hashes = [name for name in names if name.endswith('.csv') and name not in figures['input_sha256']]
    if missing_hashes:
        raise RuntimeError('Missing Hayward figure input hashes: ' + ', '.join(missing_hashes))
    for name, expected in figures['input_sha256'].items():
        if record(directory / name) != expected:
            raise RuntimeError('Stale Hayward figure input: ' + name)
    for name, expected in resolution['input_sha256'].items():
        if record(Path(name)) != expected:
            raise RuntimeError('Stale Hayward resolution input: ' + name)
    initial_rows, initial = table('initial_events.csv', ['id', 'x', 'y', 'z', 't'])
    _, initial_grid = table('initial_grid.csv')
    observation_rows, observations = table('observations.csv', ['i', 'j', 'station', 'type', 'value'])
    types = observations['type']
    if np.any((types != 0) & (types != 1) & (types != 2)):
        raise RuntimeError('Unexpected Hayward observation type')
    counts = {str(t): int(np.sum(types == t)) for t in range(3)}
    if not counts['0'] or not counts['1']:
        raise RuntimeError('Hayward review requires absolute and catalog-difference observations')
    for r in initial_rows:
        if not r['event_resource_id'] or not r['origin_resource_id']:
            raise RuntimeError('Missing Hayward reference event/origin identity')
    result = dict(dataset='independent authoritative Hayward subset', finite_modeled_results=True,
                  observation_counts=counts, modes={}, resolution=resolution,
                  boundary_tolerance_km=1e-6, objective_audit_tolerance=1e-8,
                  history_scope='Ray and residual diagnostics precede each saved update; the last history row is not generally the final model.',
                  precise_rms_interpretation=('No type-2 waveform-correlation observations; NaN history precise_rms is an empty category, represented by null here.' if counts['2'] == 0 else 'Type-2 observations are present.'),
                  displacement_interpretation='Change from reference catalog coordinates is not location error against truth.',
                  resolution_active_boundary_limitation='The linear covariance eliminates unconstrained source parameters; it does not model the nonlinear estimator with source coordinates active at domain bounds.',
                  resolution_section_interpretation='Sections linearly interpolate nodal resolution and nodal noise standard deviations; they do not compute resolution or sqrt(w^T C_v w) for the interpolated velocity.',
                  uncertainty_interpretation=selection.get('uncertainty_interpretation'),
                  differential_weight_assumption=selection.get('uncertainty_weight'),
                  pair_graph_component_sizes=selection.get('pair_graph_component_sizes', []),
                  unlinked_events=selection.get('unlinked_events'),
                  cross_metadata_epoch_differences=selection.get('cross_metadata_epoch_differences'),
                  timing_calibration_caveat=selection.get('timing_calibration_caveat'))
    saved_events, saved_grids = {}, {}
    for mode in methods:
        event_rows, events = table(mode+'_events.csv', ['id', 'x', 'y', 'z', 't'])
        if len(event_rows) != len(initial_rows) or any(
                any(a[k] != b[k] for k in ['id', 'event_resource_id', 'origin_resource_id'])
                for a, b in zip(event_rows, initial_rows)):
            raise RuntimeError('Hayward event identities do not match: ' + mode)
        _, grid = table(mode+'_grid.csv')
        for k in ['x', 'y', 'z']:
            if not np.array_equal(grid[k], initial_grid[k]):
                raise RuntimeError('Hayward grid coordinates do not match: ' + mode)
        if np.any(grid['v'] <= 0):
            raise RuntimeError('Nonpositive Hayward velocity: ' + mode)
        residual_rows, residual = table(mode+'_residuals.csv', ['i', 'j', 'station', 'type', 'residual'])
        if len(residual_rows) != len(observation_rows) or any(
                any(a[k] != b[k] for k in observation_rows[0] if k != 'value')
                for a, b in zip(residual_rows, observation_rows)):
            raise RuntimeError('Hayward residual observation identities do not match: ' + mode)
        history_rows, history = table(mode+'_history.csv', nan_fields=['precise_rms'] if counts['2'] == 0 else [])
        accepted = history['step_fraction'] > 0
        if np.any(history['step_fraction'] < 0) or np.any(history['step_fraction'] > 1):
            raise RuntimeError('Invalid Hayward step fraction: ' + mode)
        nsolves = len(history_rows)
        nlinear = flags(history['lsqr_converged'], mode+' LSQR')
        if np.any(history['lsqr_relative_normal_residual'] < 0):
            raise RuntimeError('Negative LSQR residual: ' + mode)
        n = history['ray_count']
        nc = history['ray_converged_count']
        if np.any(n <= 0) or np.any(nc < 0) or np.any(nc > n) or np.any(n != np.floor(n)) or np.any(nc != np.floor(nc)):
            raise RuntimeError('Invalid full-ray counts: ' + mode)
        increase = history['objective_after'] - history['objective_before']
        displacement = np.sqrt(sum((events[k]-initial[k])**2 for k in ['x', 'y', 'z']))
        boundary = np.zeros(len(event_rows), dtype=bool)
        outside = np.zeros(len(event_rows), dtype=bool)
        boundary_faces = {}
        for k in ['x', 'y', 'z']:
            lower = events[k] <= min(grid[k])+1e-6
            upper = events[k] >= max(grid[k])-1e-6
            boundary |= lower | upper
            boundary_faces[k+'_min'] = int(np.sum(lower))
            boundary_faces[k+'_max'] = int(np.sum(upper))
            outside |= (events[k] < min(grid[k])-1e-6) | (events[k] > max(grid[k])+1e-6)
        m = dict(final_residual_rms_seconds={str(t): (stats(residual['residual'][types == t])['rms'] if counts[str(t)] else None) for t in range(3)},
                 initial_residual_rms_seconds={str(t): (float(history[name+'_rms'][0]) if counts[str(t)] else None) for t, name in enumerate(['absolute', 'catalog', 'precise'])},
                 iterations_recorded=nsolves, accepted_updates=int(np.sum(accepted)), zero_updates=int(np.sum(~accepted)),
                 last_max_source_coordinate_step_km=float(history['location_step'][-1]),
                 largest_max_source_coordinate_step_km=float(max(history['location_step'])),
                 last_max_log_slowness_step=float(history['velocity_step'][-1]),
                 nonlinear_termination_interpretation='The configured iteration limit and line-search failure are stopping rules, not tests of nonlinear stationarity or small source updates.',
                 accepted_objective_increases_raw=int(np.sum(accepted & (increase > 0))),
                 accepted_objective_increases_above_audit_tolerance=int(np.sum(accepted & (increase > 1e-8))),
                 largest_accepted_objective_increase=max(0., float(np.max(increase[accepted]))) if np.any(accepted) else 0.,
                 objective_interpretation='Frozen-weight objective is compared within each accepted update, not between weight stages.',
                 lsqr=dict(solves=nsolves, converged=nlinear, unconverged=nsolves-nlinear,
                           max_iterations=int(max(history['lsqr_iterations'])),
                           worst_relative_normal_residual=float(max(history['lsqr_relative_normal_residual'])), tolerance=1e-8),
                 all_ray_history=dict(count_min=int(min(n)), count_max=int(max(n)),
                     converged_count_min=int(min(nc)), converged_count_max=int(max(nc)),
                     minimum_converged_percent=float(min(100*nc/n)), last_preupdate_converged_percent=float(100*nc[-1]/n[-1]),
                     projected_gradient_max_seconds_per_km=float(max(history['ray_projected_gradient_max'])),
                     raw_gradient_max_seconds_per_km=float(max(history['ray_raw_gradient_max'])),
                     iterations=[dict(iteration=int(h['iteration']), rays=int(h['ray_count']), converged=int(h['ray_converged_count']),
                        projected_gradient_max_seconds_per_km=float(h['ray_projected_gradient_max']),
                        raw_gradient_max_seconds_per_km=float(h['ray_raw_gradient_max'])) for h in history_rows]),
                 catalog_displacement_3d_km=summary(displacement),
                 catalog_displacement_components_km={k: summary(events[k]-initial[k]) for k in ['x', 'y', 'z']},
                 origin_time_correction_from_catalog_seconds=summary(events['t']-initial['t']),
                 boundary_sources=int(np.sum(boundary)),
                 boundary_face_counts=boundary_faces,
                 outside_grid_sources=int(np.sum(outside)),
                 geoid_depth_range_km=[float(min(events['z'])), float(max(events['z']))],
                 negative_geoid_depth_sources=int(np.sum(events['z'] < 0)),
                 velocity_range_km_per_s=[float(min(grid['v'])), float(max(grid['v']))])
        ray_rows, ray = table(mode+'_ray_convergence.csv',
            ['event', 'station', 'diagnostic_row', 'production_time', 'refined_time', 'difference'] +
            [setting+'_'+field for setting in ['production', 'refined']
             for field in ['gradient', 'raw_gradient', 'iterations', 'converged', 'merged']])
        derivative_rows, derivative = table(mode+'_ray_derivatives.csv',
            ['event', 'station', 'axis', 'diagnostic_row', 'production_derivative',
             'refined_derivative', 'finite_difference', 'production_error', 'refined_error'], empty=True)
        identifiers, _ = table(mode+'_ray_identifiers.csv', [])
        ray_keys = {(r['diagnostic_row'], r['event'], r['station']) for r in identifiers}
        expected_keys = {(str(int(q)), str(int(e)), str(int(s))) for q, e, s in zip(ray['diagnostic_row'], ray['event'], ray['station'])}
        if ray_keys != expected_keys:
            raise RuntimeError('Missing or mismatched final ray identifier mapping: ' + mode)
        derivative_keys = {(str(int(q)), str(int(e)), str(int(s))) for q, e, s in
                           zip(derivative['diagnostic_row'], derivative['event'], derivative['station'])}
        if not derivative_keys.issubset(expected_keys) or np.any(~np.isin(derivative['axis'], [0, 1, 2])):
            raise RuntimeError('Derivative rows do not match final ray samples: ' + mode)
        nrays = len(ray['difference'])
        check = dict(rays=nrays, identifier_associations=len(identifiers),
                     identifier_mapping=str(directory/(mode+'_ray_identifiers.csv')),
                     time_refinement_seconds=summary(abs(ray['difference'])),
                     derivative_components=len(derivative['axis']),
                     derivative_components_skipped_at_boundaries=3*min(8, nrays)-len(derivative['axis']),
                     derivative_half_step_km=0.01, derivative_diagnostic_tolerance_seconds_per_km=0.003)
        for setting in ['production', 'refined']:
            converged = flags(ray[setting+'_converged'], mode+' '+setting)
            error = abs(derivative[setting+'_error'])
            check[setting] = dict(converged=converged, unconverged=nrays-converged,
                converged_percent=100.*converged/nrays,
                projected_gradient_seconds_per_km=summary(ray[setting+'_gradient']),
                raw_gradient_seconds_per_km=summary(ray[setting+'_raw_gradient']),
                max_iterations=int(max(ray[setting+'_iterations'])), total_merged_nodes=int(sum(ray[setting+'_merged'])),
                source_derivative_error_seconds_per_km=summary(error),
                source_derivative_components_over_existing_tolerance=int(np.sum(error > 0.003)))
            check[setting]['initializer'] = initializer_audit(ray_rows, setting+'_')
        perturbation = dict(available=bool(derivative_rows and 'plus_converged' in derivative_rows[0]))
        if perturbation['available']:
            for side in ['plus', 'minus']:
                converged = flags(np.array([float(r[side+'_converged']) for r in derivative_rows]), mode+' '+side)
                perturbation[side] = dict(converged=converged, unconverged=len(derivative_rows)-converged,
                                          initializer=initializer_audit(derivative_rows, side+'_'))
        check['perturbation_convergence'] = perturbation
        spacing_names = ['production_path_spacing', 'refined_path_spacing',
                         'production_requested_fmm_spacing', 'refined_requested_fmm_spacing']
        if all(name in ray_rows[0] for name in spacing_names):
            check['spacing_km'] = {}
            for name in spacing_names:
                value = np.array([float(r[name]) for r in ray_rows])
                if np.any(~np.isfinite(value)) or np.any(value < 0):
                    raise RuntimeError('Invalid ray spacing diagnostic: ' + name)
                check['spacing_km'][name] = [float(min(value)), float(max(value))]
        initializer_counts = ['ray_initialization_attempted_count', 'ray_initialization_succeeded_count', 'ray_selected_fmm_count']
        if any(name in history for name in initializer_counts):
            if not all(name in history for name in initializer_counts):
                raise RuntimeError('Incomplete full-ray initializer history')
            for name in initializer_counts:
                value = history[name]
                if np.any(value < 0) or np.any(value > n) or np.any(value != np.floor(value)):
                    raise RuntimeError('Invalid full-ray initializer counts: ' + name)
            attempted, succeeded, selected = [history[name] for name in initializer_counts]
            if np.any(succeeded > attempted) or np.any(selected > succeeded):
                raise RuntimeError('Inconsistent full-ray initializer counts')
            m['all_ray_history']['initializer_iterations'] = [dict(iteration=int(h['iteration']),
                attempted=int(a), succeeded=int(s), failed=int(a-s), selected_fmm=int(f))
                for h, a, s, f in zip(history_rows, attempted, succeeded, selected)]
        m['final_sampled_rays'] = check
        result['modes'][mode] = m
        saved_events[mode], saved_grids[mode] = events, grid
    delta = saved_grids['dd']['v']-saved_grids['standard']['v']
    result['dd_minus_standard'] = dict(nodal_velocity_km_per_s=summary(delta),
        absolute_nodal_velocity_difference_km_per_s=summary(abs(delta)),
        source_separation_3d_km=summary(np.sqrt(sum((saved_events['dd'][k]-saved_events['standard'][k])**2 for k in ['x', 'y', 'z']))),
        final_residual_rms_difference_seconds={str(t): (result['modes']['dd']['final_residual_rms_seconds'][str(t)]-result['modes']['standard']['final_residual_rms_seconds'][str(t)] if counts[str(t)] else None) for t in range(3)},
        interpretation='Signed differences and source separations compare estimates; no field truth is supplied.')
    _, resolution_values = table('absolute_resolution.csv')
    if np.any(resolution_values['independent_pick_sigma_velocity_km_s'] < 0):
        raise RuntimeError('Negative conditional velocity uncertainty')
    linearization_rows, linearization = table('dd_linearization_rows.csv', ['i', 'station', 'observed', 'predicted', 'residual', 'ray_converged', 'ray_projected_gradient', 'ray_raw_gradient', 'ray_time', 'ray_iterations'])
    _, unique = np.unique(np.column_stack([linearization['i'], linearization['station']]), axis=0, return_index=True)
    converged = flags(linearization['ray_converged'][unique], 'DD absolute linearization')
    result['resolution_linearization_rays'] = dict(unique_rays=len(unique), converged=converged,
        converged_percent=100.*converged/len(unique),
        projected_gradient_max_seconds_per_km=float(max(linearization['ray_projected_gradient'])),
        raw_gradient_max_seconds_per_km=float(max(linearization['ray_raw_gradient'])),
        initializer=initializer_audit([linearization_rows[i] for i in unique], 'ray_'),
        scope='All unique absolute-data rays retraced at the final DD estimate; independent-pick noise calculation uses these derivatives.')
    result['ray_stopping_criterion'] = 'Projected gradient <1e-7 s/km, or time change <1e-11 s and projected gradient <1e-5 s/km.'
    result['ray_limits'] = ['Histories contain maxima over all used rays before each update, not final-model distributions.',
        'Final samples are deterministic and do not certify every production ray or globally earliest arrivals.',
        ('Derivative perturbation stopping and initializer flags are recorded; a failed perturbation trace limits its finite-difference comparison.'
         if all(result['modes'][mode]['final_sampled_rays']['perturbation_convergence']['available'] for mode in methods)
         else 'Some saved derivative perturbation traces lack their own convergence flags; refined traces are numerical comparisons, not exact references.'),
        'The existing 0.003 s/km component tolerance is a diagnostic comparison, not an inversion-error bound.']
    record(Path(__file__))
    result['input_sha256'] = hashes
    # Reject nonfinite values anywhere in the assembled modeled diagnostics.
    output = json.dumps(result, indent=2, allow_nan=False)+'\n'
    report.mkdir(parents=True, exist_ok=True)
    (directory/'numerical_review.json').write_text(output)
    with (report/'hayward_results.tex').open('w') as f:
        f.write('These results use the independently selected authoritative Hayward cohort. '
                'Residuals below are unweighted final residuals; standard tomography fits absolute picks only, '
                'so its catalog-difference RMS is an additional diagnostic. '
                'Catalog displacement measures relocation, not error against known source positions.\n\n')
        components = result['pair_graph_component_sizes']
        if components:
            f.write('The selected pair graph has {} connected components; the largest contains {} events, and {} events have no differential links. '
                    'Unlinked events remain in the inversion with absolute observations. '
                    '{} catalog differences span metadata epochs at identical NSLC and receiver coordinates; this geometry match does not establish unchanged timing calibration.\n\n'.format(
                        len(components), max(components), result['unlinked_events'], result['cross_metadata_epoch_differences']))
        f.write(r'\begin{center}\begin{tabular}{lrrrrr}\toprule Method & $R_{\rm abs}$ (s) & $R_{\rm cat}$ (s) & Updates & LSQR & Min. rays (\%)\\\midrule'+'\n')
        initial_rms = result['modes']['standard']['initial_residual_rms_seconds']
        f.write('Initial & {:.5f} & {:.5f} & -- & -- & --\\\\\n'.format(initial_rms['0'], initial_rms['1']))
        for mode in methods:
            m = result['modes'][mode]
            f.write('{} & {:.5f} & {:.5f} & {}/{} & {}/{} & {:.2f}\\\\\n'.format(
                esc(mode), m['final_residual_rms_seconds']['0'], m['final_residual_rms_seconds']['1'],
                m['accepted_updates'], m['iterations_recorded'], m['lsqr']['converged'], m['lsqr']['solves'],
                m['all_ray_history']['minimum_converged_percent']))
        f.write(r'\bottomrule\end{tabular}\end{center}'+'\n')
        f.write('The initial row uses the first pre-update forward prediction. '
                'Updates counts accepted steps; LSQR counts solves meeting the existing relative normal-residual tolerance of $10^{-8}$. '
                'The last column is the minimum converged fraction over all used rays in any saved pre-update history row. '
                'These history entries precede their update and do not represent the final model. '
                'Frozen-weight objectives are compared within each update; weights can change between iterations. '
                'The solver stops at its iteration limit or when no line-search step is accepted; it does not test nonlinear stationarity or a small-source-update criterion.\n\n')
        if counts['2'] == 0:
            f.write('No waveform-correlation observations are included. The history column for precise-difference RMS is therefore empty (NaN), not a nonfinite modeled residual.\n\n')
        for mode in methods:
            m = result['modes'][mode]
            h, q = m['all_ray_history'], m['final_sampled_rays']
            p, r = q['production'], q['refined']
            f.write('For {}, median and maximum catalog displacements are {:.3f} and {:.3f} km; {} sources lie within $10^{{-6}}$ km of a grid boundary. '
                    'Nodal velocities range from {:.3f} to {:.3f} km/s. '
                    'There are {} zero-update iterations and {} accepted objective increases above the existing $10^{{-8}}$ audit tolerance; '
                    'the worst LSQR relative normal residual is {:.3g}. '.format(
                        esc(mode), m['catalog_displacement_3d_km']['median'], m['catalog_displacement_3d_km']['max'],
                        m['boundary_sources'], *m['velocity_range_km_per_s'], m['zero_updates'],
                        m['accepted_objective_increases_above_audit_tolerance'], m['lsqr']['worst_relative_normal_residual']))
            f.write('The final recorded iteration changes a source coordinate by at most {:.3f} km and nodal log slowness by at most {:.3g}. '.format(
                m['last_max_source_coordinate_step_km'], m['last_max_log_slowness_step']))
            f.write('Geoid depths span {:.3f} to {:.3f} km, with {} negative-depth estimates and {} estimates outside the grid beyond the boundary tolerance. '.format(
                *m['geoid_depth_range_km'], m['negative_geoid_depth_sources'], m['outside_grid_sources']))
            face_details = []
            for k in ['x', 'y', 'z']:
                for side, bound in [('min', min(initial_grid[k])), ('max', max(initial_grid[k]))]:
                    count = m['boundary_face_counts'][k+'_'+side]
                    if count:
                        face_details.append('{} at ${}={:g}$ km'.format(count, k, bound))
            if face_details:
                f.write('Boundary counts by face are {}; a source on intersecting faces contributes to each count. '.format('; '.join(face_details)))
            f.write('Across all {}--{} rays per recorded iteration, the largest projected/raw gradient norms are {:.3g}/{:.3g} s/km. '
                    'At the final model, production/refined convergence counts are {}/{} of {} sampled rays, '
                    'with maximum projected gradients {:.3g}/{:.3g} s/km and raw gradients {:.3g}/{:.3g} s/km. '
                    'Halving the path spacing and any enabled auxiliary-field spacing changes sampled travel times by at most {:.3f} ms. '.format(
                        h['count_min'], h['count_max'], h['projected_gradient_max_seconds_per_km'], h['raw_gradient_max_seconds_per_km'],
                        p['converged'], r['converged'], q['rays'], p['projected_gradient_seconds_per_km']['max'],
                        r['projected_gradient_seconds_per_km']['max'], p['raw_gradient_seconds_per_km']['max'],
                        r['raw_gradient_seconds_per_km']['max'], 1000*q['time_refinement_seconds']['max']))
            if q['derivative_components']:
                f.write('For {} source-coordinate derivatives, maximum production/refined errors against centered travel-time differences are {:.3g}/{:.3g} s/km; '
                        '{}/{} components exceed the existing 0.003 s/km component tolerance. '.format(
                            q['derivative_components'], p['source_derivative_error_seconds_per_km']['max'], r['source_derivative_error_seconds_per_km']['max'],
                            p['source_derivative_components_over_existing_tolerance'], r['source_derivative_components_over_existing_tolerance']))
            f.write('{} derivative components are omitted at domain boundaries. '.format(q['derivative_components_skipped_at_boundaries']))
            if p['initializer']['available']:
                f.write('Production/refined initializer extractions fail for {}/{} sampled rays. '.format(
                    p['initializer']['failed'], r['initializer']['failed']))
            perturbation = q['perturbation_convergence']
            if perturbation['available']:
                f.write('The positive/negative finite-difference perturbations have {}/{} local-stopping failures. '.format(
                    perturbation['plus']['unconverged'], perturbation['minus']['unconverged']))
                if all(perturbation[side]['initializer']['available'] for side in ['plus', 'minus']):
                    f.write('Their initializer extraction failures are {}/{}. '.format(
                        perturbation['plus']['initializer']['failed'], perturbation['minus']['initializer']['failed']))
            f.write('\n\n')
        if any(m['boundary_face_counts']['z_min'] for m in result['modes'].values()):
            f.write('Some source estimates reach the computational top, added to contain elevated receivers. '
                    'These constrained estimates do not establish source-depth recovery. '
                    'Negative geoid depth means elevation above the geoid, not necessarily above local terrain. '
                    'The velocity sections show the complete computational depth range so these estimates remain visible.\n\n')
        d = result['dd_minus_standard']
        f.write('Over the saved model nodes, DD minus standard velocity has mean {:.4f} km/s, RMS {:.4f} km/s, and maximum absolute difference {:.4f} km/s. '
                'The median separation between their source estimates is {:.3f} km. '
                'These differences do not establish which field model is more accurate.\n\n'.format(
                    d['nodal_velocity_km_per_s']['mean'], d['nodal_velocity_km_per_s']['rms'],
                    d['absolute_nodal_velocity_difference_km_per_s']['max'], d['source_separation_3d_km']['median']))
        c = resolution['conditioning']
        lr = result['resolution_linearization_rays']
        f.write('The absolute-data resolution calculation is linearized at the final DD model with fixed uncertainty weights, first-difference log-slowness smoothing, '
                'and column-scaled damping. The model Schur-complement condition number is {:.3g}, its inverse relative residual is {:.3g}, '
                'and the smallest damped source-block eigenvalue is {:.3g}. '
                'Resolution diagonals range from {:.3g} to {:.3g}; conditional velocity-noise standard deviations range from {:.3g} to {:.3g} km/s. '
                'For this final DD linearization, {}/{} unique absolute-data rays meet the ray stopping criterion; '
                'maximum projected/raw gradient norms are {:.3g}/{:.3g} s/km.\n\n'.format(
                    c['model_schur_condition_number'], c['inverse_relative_residual'], c['minimum_source_normal_eigenvalue'],
                    *resolution['resolution_diagonal_min_max'], *resolution['velocity_sigma_min_max_km_s'],
                    lr['converged'], lr['unique_rays'], lr['projected_gradient_max_seconds_per_km'], lr['raw_gradient_max_seconds_per_km']))
        f.write('This is a conditional absolute-data calculation, not full DD resolution. '
                'Reported symmetric pick uncertainties are interpreted as independent one-standard-deviation errors; provider confidence levels are absent. '
                'Propagation through the damped estimator excludes correlated station/model errors, regularization bias, and nonlinear or ray errors. '
                'It eliminates unconstrained source parameters and does not represent the active domain bounds on some inferred source coordinates. '
                'The plotted sections interpolate nodal resolution and nodal noise standard deviations; they do not propagate covariance to interpolated velocity. '
                'Small propagated noise therefore does not establish small total velocity error. '
                'Ray convergence means a projected gradient below $10^{-7}$ s/km, or a travel-time change below $10^{-11}$ s with gradient below $10^{-5}$ s/km. '
                'The source finite-difference half-step is 0.01 km. Small spacing changes alone do not establish derivative convergence or globally earliest arrivals, '
                'and the deterministic final samples do not certify every production ray.\n')
    return result


if __name__ == '__main__' and '--hayward-only' in sys.argv[1:]:
    parser = argparse.ArgumentParser(description='Audit a completed, identified Hayward run.')
    parser.add_argument('--hayward-only', action='store_true')
    parser.add_argument('--data-dir', type=Path, default=Path('data/hayward'))
    parser.add_argument('--report-dir', type=Path, default=Path('report'))
    args = parser.parse_args()
    review = analyze_hayward(args.data_dir, args.report_dir, required=True)
    print(json.dumps({'hayward': review['modes']}, indent=2, allow_nan=False))
    sys.exit(0)


truth = load('truth_events.csv')
initial = load('initial_events.csv')
metrics = {'modes': {}, 'publication_reference': {
    'standard_velocity_absolute_error': {'median': 0.164, 'mean': 0.245, 'std': 0.249},
    'dd_velocity_absolute_error': {'median': 0.136, 'mean': 0.178, 'std': 0.164},
    'median_depth_errors': {'loc1d': 1.123, 'loc3d': 0.296, 'standard': 0.460, 'dd': 0.329},
    'caution': 'Published sampling mask is not specified; geometry and initial model differ. These are reference scales, not matched benchmarks.'}}
metrics['initial_location'] = {key: stats(abs(initial[key]-truth[key])) for key in ['x','y','z']}
metrics['initial_location_3d'] = stats(location_error(initial, truth))
for mode in ['standard', 'dd', 'loc1d', 'loc3d']:
    metrics['modes'][mode] = inversion_metrics(D, mode, truth)
initial_grid = load('initial_grid.csv')
initial_velocity = float(initial_grid['v'][0])
if initial_velocity <= 0 or not np.all(initial_grid['v'] == initial_velocity):
    raise RuntimeError('The documented main-experiment baseline requires a positive homogeneous initial grid')
baseline_slices = load('standard_slices.csv')
# The saved signed error is recovered minus true, so this recovers the exact
# sample locations and true values used by every final-model velocity metric.
baseline_error = abs(initial_velocity-(baseline_slices['v']-baseline_slices['error']))
baseline_inside = ((baseline_slices['x']>=-15)&(baseline_slices['x']<=20)&
                   (baseline_slices['y']>=-40)&(baseline_slices['y']<=20)&
                   (baseline_slices['z']>=3)&(baseline_slices['z']<=11))
metrics['initial_velocity'] = dict(
    value_km_per_s=initial_velocity,
    sampling='Same saved full-domain and interior slice samples as the final-model metrics; true velocity is saved v minus error.',
    velocity_full_domain=stats(baseline_error),
    velocity_interior=stats(baseline_error[baseline_inside]))
spatial = dict(
    averaging='Arithmetic mean of saved regular-grid samples, including window endpoints',
    caution='These are independently defined averaging windows, not published recovered-model averages.',
    depths_km=[3,7], along_strike_window_km=[-20,20],
    trough_cross_strike_window_km=[1,5], west_cross_strike_window_km=[-15,0],
    specified_true_velocities_km_per_s=dict(trough=4.0, west=6.0, west_minus_trough=2.0),
    modes={})
for mode in ['standard', 'dd']:
    slices = load(mode+'_slices.csv')
    spatial['modes'][mode] = {}
    for depth in spatial['depths_km']:
        section = ((slices['z']==depth) & (slices['y']>=-20) & (slices['y']<=20))
        trough = slices['v'][section & (slices['x']>=1) & (slices['x']<=5)]
        west = slices['v'][section & (slices['x']>=-15) & (slices['x']<=0)]
        trough_mean, west_mean = stats(trough)['mean'], stats(west)['mean']
        spatial['modes'][mode][str(depth)] = dict(
            trough_samples=len(trough), west_samples=len(west),
            trough_mean_velocity=trough_mean, west_mean_velocity=west_mean,
            west_minus_trough_velocity=west_mean-trough_mean,
            trough_error_from_specified_true=trough_mean-4,
            west_error_from_specified_true=west_mean-6,
            contrast_error_from_specified_true=west_mean-trough_mean-2)
metrics['spatial_comparison'] = spatial
metrics['ray_diagnostics'] = {name: ray_diagnostics(prefix) for name, prefix in
                              [('truth', 'ray'), ('standard', 'standard_ray'), ('dd', 'dd_ray')]}
metrics['ray_convergence_seconds'] = metrics['ray_diagnostics']['truth']['time_refinement_seconds']
validation = load_table('data/validation.csv', text_fields=('test',))
if (not np.all(validation['passed'] == 1)
        or np.any(validation['error'] < 0)
        or np.any(validation['tolerance'] < 0)
        or np.any(validation['error'] > validation['tolerance'])):
    raise RuntimeError('Numerical validation failed')
metrics['validation_checks_passed'] = len(validation)
recovery_truth=load_table('data/recovery/truth_events.csv')
recovery_initial=load_table('data/recovery/initial_events.csv')
recovery_final=load_table('data/recovery/loc3d_events.csv')
recovery_res=load_table('data/recovery/loc3d_residuals.csv')
recovery={}
for label,events in [('initial',recovery_initial),('final',recovery_final)]:
    error=np.sqrt(sum((events[k]-recovery_truth[k])**2 for k in ['x','y','z']))
    recovery[label+'_3d_error_km']=stats(error)
recovery['absolute_rms_seconds']=stats(recovery_res['residual'][recovery_res['type']==0])['rms']
recovery['lsqr']=linear_diagnostics(load_table('data/recovery/loc3d_history.csv'))
metrics['known_model_recovery']=recovery
if recovery['final_3d_error_km']['median']>=recovery['initial_3d_error_km']['median']:
    raise RuntimeError('Known-model inversion failed to reduce median source error')

# Analytic homogeneous arrivals exercise the same coupled source/velocity solve.
# Scientific acceptance failures remain visible in the report; malformed or
# nonfinite input still stops analysis. None of these gates is fitted to results.
J = Path('data/joint_recovery')
joint_truth = load_table(J/'truth_events.csv')
joint_initial = load_table(J/'initial_events.csv')
joint_events = load_table(J/'dd_events.csv')
joint_grid = load_table(J/'dd_grid.csv')
joint_start = load_table(J/'initial_grid.csv')
joint_residual = load_table(J/'dd_residuals.csv')
joint_history = load_table(J/'dd_history.csv')
coverage = load_table(J/'dd_coverage.csv')
aligned(joint_start, joint_grid, ('x','y','z'), 'Joint grid')
if (len(coverage) != len(joint_grid)
        or not np.array_equal(coverage['node'], np.arange(len(joint_grid)))
        or np.any(coverage['path_length'] < 0)):
    raise RuntimeError('Joint recovery coverage does not match the grid')
if joint_history[0]['iteration'] != 0:
    raise RuntimeError('Joint recovery history must include the initial residual')
covered = coverage['path_length'] > 1e-9
if not np.any(covered):
    raise RuntimeError('Joint recovery has no illuminated velocity nodes')
joint = dict(truth_velocity_km_per_s=6.0, finite_results=True,
             sources=len(joint_truth), grid_nodes=len(joint_grid),
             illuminated_nodes=int(np.sum(covered)),
             illumination_threshold_path_length_km=1e-9,
             initial_3d_error_km=stats(location_error(joint_initial, joint_truth)),
             final_3d_error_km=stats(location_error(joint_events, joint_truth)),
             initial_illuminated_velocity_error=stats(abs(joint_start['v'][covered]-6)),
             final_illuminated_velocity_error=stats(abs(joint_grid['v'][covered]-6)),
             initial_velocity_range=[float(min(joint_start['v'])),float(max(joint_start['v']))],
             final_velocity_range=[float(min(joint_grid['v'])),float(max(joint_grid['v']))],
             boundary_sources=boundary_count(joint_events, joint_grid),
             objective_increases=int(np.sum(joint_history['objective_after'] > joint_history['objective_before']+1e-8)),
             lsqr=linear_diagnostics(joint_history), residual={})
for t, name in enumerate(['absolute', 'catalog', 'precise']):
    first = float(joint_history[0][name+'_rms'])
    last = stats(joint_residual['residual'][joint_residual['type']==t])['rms']
    joint['residual'][name] = dict(initial_rms_seconds=first, final_rms_seconds=last,
                                   reduction_factor=first/last if last > 0 else None,
                                   tenfold_reduction=bool(first > 0 and last <= first/10))
accepted = joint_history['step_fraction'] > 0
joint['accepted_velocity_updates'] = int(np.sum(accepted & (joint_history['velocity_step'] > 1e-12)))
joint['accepted_location_updates'] = int(np.sum(accepted & (joint_history['location_step'] > 1e-12)))
joint['nodes_changed'] = int(np.sum(abs(joint_grid['v']-joint_start['v']) > 1e-12))
joint['sources_changed'] = int(np.sum(location_error(joint_events, joint_initial) > 1e-12))
joint['gates'] = dict(
    finite_positive_velocities=bool(np.all(joint_grid['v'] > 0)),
    no_boundary_sources=joint['boundary_sources'] == 0,
    nonincreasing_accepted_objectives=joint['objective_increases'] == 0,
    absolute_rms_reduced_tenfold=joint['residual']['absolute']['tenfold_reduction'],
    precise_rms_reduced_tenfold=joint['residual']['precise']['tenfold_reduction'],
    median_location_error_reduced=joint['final_3d_error_km']['median'] < joint['initial_3d_error_km']['median'],
    illuminated_median_velocity_error_reduced=(joint['final_illuminated_velocity_error']['median']
                                             < joint['initial_illuminated_velocity_error']['median']),
    velocity_and_location_both_updated=bool(joint['accepted_velocity_updates'] > 0
                                            and joint['accepted_location_updates'] > 0
                                            and joint['nodes_changed'] > 0
                                            and joint['sources_changed'] > 0))
joint['passed'] = all(joint['gates'].values())
joint['failed_gates'] = [name for name, passed in joint['gates'].items() if not passed]
metrics['joint_recovery'] = joint

# These experiments change only the documented initial velocity profile.
sensitivity = {'homogeneous': metrics['modes']['dd']}
for profile in ['lom', 'lon']:
    directory = Path('data/synthetic_'+profile)
    for filename in ['truth_events.csv', 'initial_events.csv', 'stations.csv', 'observations.csv']:
        reference, comparison = load(filename), load_table(directory/filename)
        aligned(reference, comparison, reference.dtype.names, profile+' '+filename)
    profile_start = load_table(directory/'initial_grid.csv')
    aligned(load('initial_grid.csv'), profile_start, ('x','y','z'), profile+' inversion grid')
    m = inversion_metrics(directory, 'dd', truth)
    m['identical_observations_and_initial_locations'] = True
    m['initial_velocity_range'] = [float(min(profile_start['v'])),float(max(profile_start['v']))]
    m['change_from_homogeneous_dd'] = dict(
        full_domain_mean_velocity_error=m['velocity_full_domain']['mean']-metrics['modes']['dd']['velocity_full_domain']['mean'],
        interior_mean_velocity_error=m['velocity_interior']['mean']-metrics['modes']['dd']['velocity_interior']['mean'],
        median_3d_location_error_km=m['location_3d']['median']-metrics['modes']['dd']['location_3d']['median'],
        absolute_rms_seconds=m['residual']['0']['rms']-metrics['modes']['dd']['residual']['0']['rms'],
        precise_rms_seconds=m['residual']['2']['rms']-metrics['modes']['dd']['residual']['2']['rms'])
    sensitivity[profile] = m
metrics['initial_model_sensitivity'] = sensitivity
Path('data/metrics.json').write_text(json.dumps(metrics, indent=2, allow_nan=False)+'\n')

R = Path('report')
with open(R/'spatial_table.tex','w') as f:
    f.write(r'\begin{tabular}{lrrrr}\toprule Model & Depth (km) & Trough & West block & West minus trough\\\midrule'+'\n')
    for mode, sections in spatial['modes'].items():
        for depth, values in sections.items():
            f.write('{} & {} & {:.3f} & {:.3f} & {:.3f}\\\\\n'.format(
                mode,depth,values['trough_mean_velocity'],values['west_mean_velocity'],
                values['west_minus_trough_velocity']))
    f.write(r'Specified true model & 3, 7 & 4.000 & 6.000 & 2.000\\\bottomrule\end{tabular}'+'\n')

with open(R/'joint_findings.tex','w') as f:
    f.write('The analytic homogeneous joint-inversion recovery gates \\textbf{'+('PASSED' if joint['passed'] else 'FAILED')+'}. ')
    f.write('Median three-dimensional location error changed from {:.4f} to {:.4f} km, while median velocity error at the {} illuminated nodes changed from {:.4f} to {:.4f} km/s. '.format(
        joint['initial_3d_error_km']['median'],joint['final_3d_error_km']['median'],joint['illuminated_nodes'],
        joint['initial_illuminated_velocity_error']['median'],joint['final_illuminated_velocity_error']['median']))
    for name in ['absolute', 'precise']:
        rr = joint['residual'][name]
        f.write('The {} residual RMS changed from {:.5f} to {:.5f} s. '.format(name,rr['initial_rms_seconds'],rr['final_rms_seconds']))
    f.write('There were {} accepted velocity updates, {} accepted location updates, and {} sources on a boundary. '.format(
        joint['accepted_velocity_updates'],joint['accepted_location_updates'],joint['boundary_sources']))
    linear = joint['lsqr']
    f.write('LSQR met its normal-residual tolerance in {} of {} solves; the worst relative normal residual was {:.3g}.\n\n'.format(
        linear['converged'],linear['solves'],linear['worst_relative_normal_residual']))
    f.write('The fixed recovery criteria require positive finite velocities, no boundary sources, nonincreasing accepted frozen-weight objectives, at least tenfold reductions of both absolute and precise residual RMS, lower median location and illuminated-node velocity errors, and nonzero updates to both locations and velocity. ')
    if joint['failed_gates']:
        labels = dict(finite_positive_velocities='positive finite velocities',
                      no_boundary_sources='no boundary sources',
                      nonincreasing_accepted_objectives='nonincreasing accepted objectives',
                      absolute_rms_reduced_tenfold='tenfold absolute-RMS reduction',
                      precise_rms_reduced_tenfold='tenfold precise-RMS reduction',
                      median_location_error_reduced='lower median location error',
                      illuminated_median_velocity_error_reduced='lower illuminated-node median velocity error',
                      velocity_and_location_both_updated='nonzero location and velocity updates')
        f.write('Failed criteria: '+ '; '.join(labels[name] for name in joint['failed_gates'])+'. ')
    f.write('Illumination means accumulated interpolated path length greater than $10^{-9}$ km on final rays; it does not establish resolution or recovery at every node. The arrivals are analytic and unrounded. This test examines a coupled homogeneous limiting case; it does not establish heterogeneous model recovery.\n')

with open(R/'sensitivity_table.tex','w') as f:
    f.write(r'\begin{tabular}{lrrrrr}\toprule Start & Median 3D error & Mean $|\Delta v|$ & Interior $|\Delta v|$ & $R_{\rm abs}$ & $R_{\rm prec}$\\\midrule'+'\n')
    for name, m in sensitivity.items():
        vals = [m['location_3d']['median'],m['velocity_full_domain']['mean'],m['velocity_interior']['mean'],
                m['residual']['0']['rms'],m['residual']['2']['rms']]
        f.write(('Homogeneous' if name == 'homogeneous' else name.upper())+' & '+' & '.join('{:.4f}'.format(v) for v in vals)+r'\\'+'\n')
    f.write(r'\bottomrule\end{tabular}'+'\n')

with open(R/'ray_findings.tex','w') as f:
    f.write('Ray diagnostics compare production traces with half-spacing, 1000-iteration traces at the saved true, final standard, and final DD models and event locations. Source derivatives are compared with central differences of refined travel times using 0.01 km endpoint perturbations. A diagnostic exceedance uses the existing single-ray tolerance of 0.003 s/km; it is not a demonstrated inversion-error bound.\n\n')
    for name, diagnostic in metrics['ray_diagnostics'].items():
        times = diagnostic['time_refinement_seconds']
        production, refined = diagnostic['production'], diagnostic['refined']
        f.write('For the {} model, {} rays had median and maximum absolute refinement changes of {:.3f} and {:.3f} ms. '.format(
            esc(name),diagnostic['rays'],1000*times['median'],1000*times['max']))
        f.write('Production/refined convergence counts were {}/{} out of {}; maximum projected gradients were {:.3g}/{:.3g} s/km and maximum raw gradients were {:.3g}/{:.3g} s/km. '.format(
            production['converged'],refined['converged'],diagnostic['rays'],
            production['projected_gradient_seconds_per_km']['max'],refined['projected_gradient_seconds_per_km']['max'],
            production['raw_gradient_seconds_per_km']['max'],refined['raw_gradient_seconds_per_km']['max']))
        if production['unconverged'] or refined['unconverged']:
            f.write('Thus {}/{} production/refined traces failed the optimizer stopping criterion. '.format(
                production['unconverged'],refined['unconverged']))
        f.write('Across {} eligible source-coordinate derivatives, maximum production/refined errors were {:.3g}/{:.3g} s/km, with {}/{} components exceeding the diagnostic tolerance; {} components were skipped at boundaries.\n\n'.format(
            diagnostic['derivative_components'],production['source_derivative_error_seconds_per_km']['max'],
            refined['source_derivative_error_seconds_per_km']['max'],
            production['source_derivative_components_over_tolerance'],refined['source_derivative_components_over_tolerance'],
            diagnostic['derivative_components_skipped_at_boundaries']))
    f.write('Raw and projected gradients differ at active domain boundaries. Small changes in travel time do not establish derivative convergence, and unconverged refined traces are not exact references. These deterministic samples cannot establish global first-arrival optimality or the accuracy of every production ray.\n')

with open(R/'metrics.tex','w') as f:
    f.write(r'\begin{tabular}{lrrrrrr}\toprule Method & Median $|\Delta x|$ & Median $|\Delta y|$ & Median $|\Delta z|$ & $R_{\rm abs}$ & $R_{\rm cat}$ & $R_{\rm prec}$\\\midrule'+'\n')
    for mode,m in metrics['modes'].items():
        vals=[m['location'][key]['median'] for key in ['x','y','z']]+[m['residual'][str(t)]['rms'] for t in range(3)]
        f.write(esc(mode)+' & '+' & '.join('{:.4f}'.format(v) for v in vals)+r'\\'+'\n')
    f.write(r'\bottomrule\end{tabular}'+'\n')
with open(R/'velocity_metrics.tex','w') as f:
    f.write(r'\begin{tabular}{llrrr}\toprule Method & Domain & Median & Mean & Standard deviation\\\midrule'+'\n')
    for field,name in [('velocity_full_domain','Full domain'),('velocity_interior','Interior')]:
        m=metrics['initial_velocity'][field]
        f.write('Initial & {} & {:.3f} & {:.3f} & {:.3f}\\\\\n'.format(name,m['median'],m['mean'],m['std']))
    for mode in ['standard','dd']:
        for field,name in [('velocity_full_domain','Full domain'),('velocity_interior','Interior')]:
            m=metrics['modes'][mode][field]
            f.write('{} & {} & {:.3f} & {:.3f} & {:.3f}\\\\\n'.format(mode,name,m['median'],m['mean'],m['std']))
        m=metrics['publication_reference'][mode+'_velocity_absolute_error']
        f.write('{} & Published reference & {:.3f} & {:.3f} & {:.3f}\\\\\n'.format(mode,m['median'],m['mean'],m['std']))
    f.write(r'\bottomrule\end{tabular}'+'\n')
with open(R/'validation_table.tex','w') as f:
    f.write(r'\begin{longtable}{lrr}\toprule Check & Error & Tolerance\\\midrule'+'\n')
    for r in validation:
        f.write('{} & {:.3g} & {:.3g}\\\\\n'.format(esc(r['test']),r['error'],r['tolerance']))
    f.write(r'\bottomrule\end{longtable}'+'\n')
with open(R/'run_findings.tex','w') as f:
    rc=metrics['ray_convergence_seconds']
    f.write('All {} implementation consistency checks passed. Across 32 deterministic source--receiver pairs, halving the ray segment spacing and increasing the iteration limit changed travel times by a median of {:.3f} ms and a maximum of {:.3f} ms. This check does not establish global ray optimality.\n\n'.format(len(validation),1000*rc['median'],1000*rc['max']))
    f.write('In the small known-model recovery check, the median three-dimensional location error decreased from {:.4f} to {:.4f} km; the final absolute-time RMS was {:.4f} s. Only 0.01 s time quantization remains in this check.\n\n'.format(recovery['initial_3d_error_km']['median'],recovery['final_3d_error_km']['median'],recovery['absolute_rms_seconds']))
    baseline=metrics['initial_velocity']
    f.write('Before the main inversions, the median three-dimensional source error was {:.4f} km. The homogeneous {:.2f} km/s initial model had mean absolute velocity errors of {:.3f} km/s over the full domain and {:.3f} km/s in the interior, evaluated at the same saved slice samples as the recovered models.\n\n'.format(
        metrics['initial_location_3d']['median'],baseline['value_km_per_s'],
        baseline['velocity_full_domain']['mean'],baseline['velocity_interior']['mean']))
    for mode,m in metrics['modes'].items():
        f.write('The {} run ended with median three-dimensional source error {:.4f} km, {} sources on a model boundary, {} zero-update iterations, and nodal velocities ranging from {:.2f} to {:.2f} km/s. '.format(esc(mode),m['location_3d']['median'],m['boundary_sources'],m['zero_updates'],*m['velocity_range']))
        linear=m['lsqr']
        f.write('LSQR converged in {} of {} solves, with worst relative normal residual {:.3g}.\n'.format(linear['converged'],linear['solves'],linear['worst_relative_normal_residual']))
    f.write('\n\n')
    a,b=metrics['modes']['standard'],metrics['modes']['dd']
    f.write('Relative to standard tomography, DD changed the full-domain mean absolute velocity error by {:.3f} km/s and the median depth error by {:.3f} km. Negative differences indicate improvement. These comparisons refer only to the independent experiment.\n'.format(b['velocity_full_domain']['mean']-a['velocity_full_domain']['mean'],b['location']['z']['median']-a['location']['z']['median']))
with open(R/'panel_table.tex','w') as f:
    f.write(r'\begin{longtable}{>{\raggedright\arraybackslash}p{0.13\textwidth}>{\raggedright\arraybackslash}p{0.28\textwidth}>{\raggedright\arraybackslash}p{0.48\textwidth}}\toprule Panel & Quantity & Status and limiting dependency\\\midrule\endhead'+'\n')
    for row in json.loads(Path('data/panel_audit.json').read_text()):
        f.write('{} & {} & {}. {}\\\\\n'.format(esc(row['panel']),esc(row['quantity']),esc(row['status']),esc(row['limitation'])))
    f.write(r'\bottomrule\end{longtable}'+'\n')
print(json.dumps(metrics,indent=2,allow_nan=False))
# Detailed record includes commands and specifications; repeat sections at different
# y positions inherit the explicitly listed common settings.
with open(R/'panel_details.tex','w') as f:
    groups={}
    for row in json.loads(Path('data/panel_audit.json').read_text()):
        key=row['panel'].split(' (')[0]
        groups.setdefault(key,[]).append(row)
    for key, group in groups.items():
        r=group[0]
        title='Panel '+key
        if len(group)>1:
            title+=': all seven sections at y=-30,-20,-10,0,10,20,30 km'
        f.write('\\subsubsection*{'+esc(title)+'}\n')
        for field,label in [('quantity','Quantity'),('documentation','Written specification'),('parameters','Parameters'),('status','Status'),('limitation','Attempt and limitation')]:
            value=r[field]
            if len(group)>1 and field=='parameters':
                value=value.replace('y=-30 km','all seven y sections listed above')
            f.write('\\noindent\\textbf{'+label+':} '+esc(value)+'\\par\n')
        for field,label in [('data_command','Generate data'),('plot_command','Create plot')]:
            f.write('\\noindent\\textbf{'+label+':}\n\\begin{lstlisting}\n'+r[field]+'\n\\end{lstlisting}\n')

# Optional field-data review; the synthetic baseline above is unchanged.
analyze_hayward()
