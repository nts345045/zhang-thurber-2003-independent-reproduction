#!/usr/bin/env python3
"""Quantitative audit of saved results; emits machine-readable and LaTeX tables."""
import csv
import json
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
    f.write(r'\begin{longtable}{p{0.13\textwidth}p{0.28\textwidth}p{0.48\textwidth}}\toprule Panel & Quantity & Status and limiting dependency\\\midrule\endhead'+'\n')
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
