#!/usr/bin/env python3
"""Read and render one closed catalog-only comparison; no numerical model calls."""
import argparse
import json
import math
import os
from pathlib import Path
import sys

sys.dont_write_bytecode = True
import plot_hayward_corrected as saved
import rebuild_hayward_corrected as shared

ROOT = Path(__file__).resolve().parent
require, sha, local, table = saved.require, saved.sha, saved.local, saved.table
finite, write_table, tex = saved.finite, saved.write_table, saved.tex
MODE_LABEL = {'standard': 'Absolute-data tomography', 'loc1d': 'Fixed-model DD relocation'}
SHARED_SHA256 = {
    'plot_hayward_corrected.py': '8eadadaf8b0b1967ff7878fbe82b18c40502490e2ea78e3221c335c4252d9f6c',
    'rebuild_hayward_corrected.py': 'a9a07fa490b8eecdbdc10e3118288fbc3692b04800b75b224a53d8e763182769',
}
COMPARISON_MANIFEST = 'data/development/hayward_catalog_comparisons_001/manifest.json'
COMPARISON_MANIFEST_SHA256 = 'eea1640a05d5cb9d2ecf45c510173ba8db9b0941e5809a0165d21735d641bf16'


def provenance(data, outcome):
    """Join recorded source/configuration/input hashes, without provider rescans."""
    manifest_path = ROOT / COMPARISON_MANIFEST
    require(sha(manifest_path) == outcome['comparison_manifest_sha256'] == COMPARISON_MANIFEST_SHA256,
            'Outcome is not bound to the reviewed comparison manifest')
    manifest = json.loads(manifest_path.read_text())
    for field, name in (('entrypoint_sha256', 'run_hayward_catalog_comparison.py'),
                        ('helper_sha256', 'rebuild_hayward_corrected.py'),
                        ('source_mapping_sha256', manifest['scientific_source'])):
        require(outcome[field] == manifest['sha256'][name] == sha(ROOT / name),
                'Recorded comparison source differs: ' + field)
    source_path = ROOT / manifest['scientific_source']
    source = json.loads(source_path.read_text())
    built = outcome.get('built_source_sha256')
    if 'built_source_sha256' in outcome:
        require(built == source['numerical_source_sha256'],
                'Compiled source inventory differs from the reviewed numerical source')
    config_name = 'data/development/hayward_catalog_comparisons_001/run.cfg'
    config_sha = manifest['sha256'][config_name]
    require(sha(ROOT / config_name) == config_sha, 'Reviewed comparison configuration changed')
    inputs_path = source_path.parent / 'scientific_inputs.json'
    require(sha(inputs_path) == source['package_sha256']['scientific_inputs.json'],
            'Reviewed original-input bindings changed')
    inputs = json.loads(inputs_path.read_text())['expected_catalog_sha256']
    expected = dict(inputs, **{'run.cfg': config_sha})
    prepared = outcome.get('prepared_input_sha256')
    for name, digest in expected.items():
        if 'prepared_input_sha256' in outcome:
            require(isinstance(prepared, dict) and prepared.get(name) == digest,
                    'Prepared scientific input differs: ' + name)
            require(outcome['output_sha256'].get(name) == digest,
                    'Prepared scientific input missing or changed at closure: ' + name)
        elif name in outcome['output_sha256']:
            require(outcome['output_sha256'][name] == digest,
                    'Recorded original scientific input differs: ' + name)
    config_closed = outcome['output_sha256'].get('run.cfg') == config_sha
    if config_closed:
        require(sha(local(data, 'run.cfg')) == config_sha, 'Closed comparison configuration differs')
    return dict(comparison_manifest_sha256=COMPARISON_MANIFEST_SHA256,
                entrypoint_sha256=outcome['entrypoint_sha256'], helper_sha256=outcome['helper_sha256'],
                source_mapping_sha256=outcome['source_mapping_sha256'],
                built_source_sha256=built, run_config_sha256=config_sha if config_closed else None,
                original_catalog_sha256=inputs if prepared is not None else None,
                scientific_geometry_provenance_complete=built is not None and prepared is not None)


def accepted_states(data, mode, closed_table):
    """Mode-bound copy of the existing history/trial/snapshot acceptance joins."""
    history_name = mode + '_history.csv'
    if not (data / history_name).exists():
        return [], []
    history = closed_table(history_name, complete_lines=True)
    original, grid = [closed_table(name) for name in ('initial_events.csv', 'initial_grid.csv')]
    bounds = {k: (min(finite(r[k]) for r in grid), max(finite(r[k]) for r in grid)) for k in 'xyz'}
    states, notes, seen = [], [], set()
    content = (data / history_name).read_bytes()
    if content and not content.endswith(b'\n'):
        notes.append('Incomplete final history line retained but excluded from accepted-state joins.')
    for row in history:
        require(None not in row and all(v is not None for v in row.values()), 'Malformed complete history row')
        iteration = int(row['iteration'])
        require(iteration not in seen and 0 <= iteration < 18, 'Invalid/duplicate history iteration')
        seen.add(iteration)
        step = finite(row['step_fraction'])
        require(0 <= step <= 1, 'Invalid history step')
        if step == 0:
            continue
        trials = closed_table(mode + '_iteration_%d_trials.csv' % iteration)
        accepted = [r for r in trials if r['status'] == 'accepted']
        require(len(accepted) == 1 and accepted[0] == trials[-1], 'Accepted history lacks one terminal accepted trial')
        trial = accepted[0]
        require(trial['objective_evaluated'] == '1' and finite(trial['step_fraction']) == step,
                'Accepted history/trial step differs')
        require(finite(trial['objective_after']) <= finite(trial['objective_before']), 'Accepted objective increased')
        for key in ('objective_before', 'objective_after'):
            require(finite(row[key]) == float(format(finite(trial[key]), '.12g')), 'History/trial objective differs')
        names = {kind: mode + '_accepted_it_%d_%s.csv' % (iteration, kind) for kind in ('events', 'grid')}
        events, model = [closed_table(names[kind]) for kind in ('events', 'grid')]
        require(len(events) == len(original) and len(model) == len(grid), 'Snapshot inventory differs')
        for old, new in zip(original, events):
            require(all(new[k] == v for k, v in old.items() if k not in ('x', 'y', 'z', 't', 'coordinate_basis')),
                    'Accepted event native metadata differs')
            require(new['coordinate_basis'] == 'independent accepted inversion state after iteration %d; run incomplete' % iteration,
                    'Accepted snapshot scope differs')
            require(all(math.isfinite(float(new[k])) for k in 'xyzt') and
                    all(bounds[k][0] <= finite(new[k]) <= bounds[k][1] for k in 'xyz'), 'Invalid accepted source')
        for old, new in zip(grid, model):
            require(all(finite(old[k]) == finite(new[k]) for k in 'xyz') and finite(new['v']) > 0,
                    'Invalid accepted model')
            if mode == 'loc1d':
                require(finite(old['v']) == finite(new['v']), 'Fixed-model relocation changed velocity')
        states.append(dict(iteration=iteration, events_file=names['events'], grid_file=names['grid'],
                           sha256s={name: sha(local(data, name)) for name in names.values()}))
    linked = {name for state in states for name in state['sha256s']}
    unlinked = sorted(p.name for p in data.glob(mode + '_accepted_it_*') if p.name not in linked)
    if unlinked:
        notes.append('Unjoined snapshot files are preserved and not presented as accepted: ' + ', '.join(unlinked))
    return states, notes


def geometry(data, outcome, mode):
    """Existing complete native joins and geometry checks, with explicit mode names."""
    consumed = set()

    def closed_table(name, complete_lines=False):
        require(name in outcome['output_sha256'], 'Consumed table absent from closed inventory: ' + name)
        path = local(data, name)
        require(sha(path) == outcome['output_sha256'][name], 'Consumed closed table changed: ' + name)
        consumed.add(name)
        return table(path, complete_lines=complete_lines)

    names = ('initial_events.csv', 'initial_grid.csv', 'stations.csv', 'observations.csv')
    if not all((data / name).is_file() for name in names):
        return None
    events, grid, stations, observations = [closed_table(name) for name in names]
    require(events and grid and stations and observations, 'Nonempty geometry and observations')
    require([r['id'] for r in events] == [str(i) for i in range(len(events))], 'Event index order')
    require([r['id'] for r in stations] == [str(i) for i in range(len(stations))], 'Receiver index order')
    require(all(r['event_resource_id'] and r['origin_resource_id'] for r in events), 'Provider source identities')
    for row in stations:
        codes = [row[k] for k in ('network_code', 'station_code', 'location_code', 'channel_code')]
        require(row['channel_seed_id'] == '.'.join(codes), 'SEED channel identity')
        require(row['channel_fdsn_source_id'] == 'FDSN:' + '_'.join(codes[:3] + list(codes[3])), 'FDSN identity')
    for row in observations:
        require(row['type'] in ('0', '1'), 'Catalog-only comparison cannot contain waveform rows')
        for side in ('i', 'j'):
            index = int(row[side])
            if index < 0:
                require(side == 'j' and row['type'] == '0', 'Absolute second endpoint')
                continue
            receiver = int(row['station' if side == 'i' else 'station_j'])
            require(0 <= index < len(events) and 0 <= receiver < len(stations), 'Endpoint index')
            for kind in ('event', 'origin'):
                require(row[kind + '_' + side + '_resource_id'] == events[index][kind + '_resource_id'], 'Provider endpoint join')
            require(row['pick_' + side + '_resource_id'] and row['arrival_' + side + '_resource_id'], 'Pick and association identities')
            station = stations[receiver]
            require(row['channel_seed_id'] == station['channel_seed_id'], 'Common channel join')
            for edge in ('start', 'end'):
                require(row['metadata_epoch_' + ('j_' if side == 'j' else '') + edge] == station['metadata_epoch_' + edge], 'Native endpoint epoch')
    states, notes = accepted_states(data, mode, closed_table)
    require([s['iteration'] for s in states] == sorted(set(s['iteration'] for s in states)), 'Unique accepted iteration order')
    history_name = mode + '_history.csv'
    if (data / history_name).exists():
        history = closed_table(history_name, complete_lines=True)
        accepted = [int(r['iteration']) for r in history if finite(r['step_fraction']) > 0]
        require(accepted == [s['iteration'] for s in states], 'Accepted snapshots agree with closed history')
    else:
        require(not states, 'An accepted state requires its closed iteration history')
    selected = states[-1] if states else None
    final_events, final_grid = events, grid
    if selected:
        for name in ('events_file', 'grid_file'):
            require(sha(local(data, selected[name])) == selected['sha256s'][selected[name]], 'Closed accepted snapshot hash')
        final_events, final_grid = [closed_table(selected[k]) for k in ('events_file', 'grid_file')]
    require(len(events) == len(final_events) and len(grid) == len(final_grid), 'Complete saved-state geometry')
    bounds = {a: (min(finite(r[a]) for r in grid), max(finite(r[a]) for r in grid)) for a in 'xyz'}
    points = []
    for before, after in zip(events, final_events):
        require(all(before[k] == after[k] for k in before if k not in ('x', 'y', 'z', 't', 'coordinate_basis')), 'Unchanged event metadata')
        require(all(bounds[k][0] <= finite(after[k]) <= bounds[k][1] for k in 'xyz'), 'Source inside physical grid')
        delta = [finite(after[k]) - finite(before[k]) for k in 'xyz']
        points.append(dict(after, initial_x_km=before['x'], initial_y_km=before['y'], initial_z_km=before['z'],
                           dx_km=delta[0], dy_km=delta[1], dz_km=delta[2],
                           displacement_3d_km=math.sqrt(sum(v * v for v in delta))))
    nodes = []
    for before, after in zip(grid, final_grid):
        require(all(finite(before[k]) == finite(after[k]) for k in 'xyz'), 'Fixed model nodes')
        initial, final = finite(before['v']), finite(after['v'])
        require(initial > 0 and final > 0, 'Positive velocities')
        nodes.append(dict(after, initial_v_km_s=initial, delta_v_km_s=final - initial))
    return events, stations, points, nodes, selected, states, notes, consumed


def render(data, out, mode):
    for name, digest in SHARED_SHA256.items():
        require(sha(ROOT / name) == digest, 'Reviewed shared helper changed: ' + name)
    require(mode in MODE_LABEL, 'Unsupported comparison mode')
    outcome_path = local(data, 'comparison_outcome.json')
    outcome = json.loads(outcome_path.read_text())
    require(outcome['mode'] == mode, 'Requested mode differs from closed outcome')
    require(outcome['status'] in ('completed_attempt_pending_scientific_review', 'failed_preserved'), 'Closed numerical outcome required')
    require(isinstance(outcome['return_code'], int), 'Actual numerical exit code required')
    require(outcome['status'] != 'completed_attempt_pending_scientific_review' or outcome['return_code'] == 0,
            'Completed attempt must have a zero numerical exit code')
    require(outcome['outputs_stable'] is True, 'No live scientific-output writer may remain')
    source_bindings = provenance(data, outcome)
    for command in outcome['commands']:
        require(command['outputs_stable'] is True, 'Closed child process group required')
        if command.get('launch_failed'):
            require(not command.get('pid') and not command['child_reaped'], 'Failed launch must not claim an executed child')
        else:
            require(command['child_reaped'] and isinstance(command['return_code'], int), 'Every executed child must be reaped')
    for name, digest in outcome['output_sha256'].items():
        require(sha(local(data, name)) == digest, 'Closed numerical output changed: ' + name)
    history_name = mode + '_history.csv'
    history_bytes = ((data / history_name).read_bytes() if history_name in outcome['output_sha256'] else b'')
    out = shared.fresh_path(out, ROOT / 'tmp')
    result, error = None, None
    if source_bindings['scientific_geometry_provenance_complete']:
        try:
            result = geometry(data, outcome, mode)
        except (ValueError, KeyError, IndexError) as exception:
            error = str(exception)
    out.mkdir(parents=True)
    summary = dict(status='rendered_closed_comparison', mode=mode, data_directory=str(data.relative_to(ROOT)),
                   saved_output_validation='failed' if error else 'passed' if result is not None else 'unavailable',
                   numerical_status=outcome['status'], numerical_return_code=outcome['return_code'],
                   failed_stage=outcome.get('failed_stage'), outcome_sha256=sha(outcome_path),
                   source_sha256=sha(Path(__file__)), numerical_source_bindings=source_bindings,
                   shared_source_sha256={p.name: sha(p) for p in (Path(saved.__file__), Path(shared.__file__))},
                   scientific_success=False, history_metrics_scope='pre-update',
                   plotting_validation_error=error, recovery_plot_created=False,
                   accepted_states=[], selected_iteration=None,
                   incomplete_history_tail_ignored=bool(history_bytes) and not history_bytes.endswith(b'\n'),
                   scope='Saved accepted geometry or an explicit failed/interrupted disposition; no ray, inverse, covariance or convergence calculation.')
    description = 'Preparation left no complete identified plotting input; no recovery plot is produced.'
    if not source_bindings['scientific_geometry_provenance_complete']:
        description = 'The closed attempt lacks complete compiled-source/input bindings; no recovery geometry is admitted or plotted.'
    if error is not None:
        description = 'Saved-output validation failed; no recovery plot is produced: ' + error
    if result is not None:
        events, stations, points, nodes, selected, states, notes, consumed = result
        summary.update(events=len(events), receiver_epochs=len(stations), accepted_states=states,
                       accepted_state_notes=notes, accepted_iterations=len(states),
                       consumed_table_sha256={n: outcome['output_sha256'][n] for n in sorted(consumed)})
        description = 'No accepted update is verified. The closed attempt has no recovered model or relocated-source result to plot.'
        if not states and outcome['return_code'] < 0:
            description += ' Its numerical child ended by signal %d; this is an interrupted attempt, not evidence of nonlinear convergence failure.' % (-outcome['return_code'])
        if selected:
            for name in ('matplotlib', 'cache', 'tmp'):
                (out / name).mkdir()
            os.environ.update(MPLCONFIGDIR=str(out / 'matplotlib'), XDG_CACHE_HOME=str(out / 'cache'), TMPDIR=str(out / 'tmp'))
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            write_table(out / 'event_points.csv', points)
            write_table(out / 'model_nodes.csv', nodes)
            write_table(out / 'receiver_epochs.csv', stations)
            fig, axes = plt.subplots(1, 2, figsize=(10, 4.8), constrained_layout=True)
            section = [r for r in nodes if finite(r['z']) == 8.0]
            require(bool(section), 'Declared 8 km model section')
            values = [r['delta_v_km_s'] for r in section]
            limit = max(map(abs, values))
            if limit:
                artist = axes[0].scatter([finite(r['x']) for r in section], [finite(r['y']) for r in section],
                                         c=values, s=65, marker='s', cmap='RdBu_r', vmin=-limit, vmax=limit)
                fig.colorbar(artist, ax=axes[0], label='Velocity change (km/s)', shrink=.8)
            else:
                axes[0].scatter([finite(r['x']) for r in section], [finite(r['y']) for r in section],
                                color='0.5', s=65, marker='s', label='Velocity change = 0 km/s')
                axes[0].legend(fontsize=8)
            axes[0].set_title(('Fixed model: no change' if mode == 'loc1d' else 'Accepted minus initial') + ', z = 8 km')
            axes[1].scatter([finite(r['x']) for r in events], [finite(r['y']) for r in events], s=3, color='0.6')
            axes[1].quiver([finite(r['x']) for r in events], [finite(r['y']) for r in events],
                           [r['dx_km'] for r in points], [r['dy_km'] for r in points],
                           angles='xy', scale_units='xy', scale=1, width=.002, color='tab:blue')
            axes[1].set_title('Source displacements, scale 1:1')
            limits = {}
            for coordinate in 'xy':
                values = [finite(r[coordinate]) for rows in (nodes, events, points) for r in rows]
                lower, upper = min(values), max(values)
                require(upper > lower, 'Nonzero saved plotting extent required')
                margin = .02 * (upper - lower)
                limits[coordinate] = [lower - margin, upper + margin]
            for ax in axes:
                ax.set(xlabel='Local x (km)', ylabel='Local y (km)', aspect='equal',
                       xlim=limits['x'], ylim=limits['y'])
                ax.grid(alpha=.15)
            fig.suptitle(MODE_LABEL[mode] + ': accepted iteration ' + str(selected['iteration']))
            fig.savefig(out / 'comparison_figure.pdf')
            fig.savefig(out / 'comparison_figure.png', dpi=180)
            plt.close(fig)
            summary.update(recovery_plot_created=True, selected_iteration=selected['iteration'],
                           displacement_3d_max_km=max(r['displacement_3d_km'] for r in points),
                           velocity_change_range_km_s=[min(r['delta_v_km_s'] for r in nodes), max(r['delta_v_km_s'] for r in nodes)],
                           matplotlib_version=matplotlib.__version__, plot_limits_km=limits)
            companion = dict(mode=mode, events='event_points.csv', receiver_epochs='receiver_epochs.csv',
                             output_sha256={p.name: sha(p) for p in out.glob('*.csv')}, outcome_sha256=sha(outcome_path),
                             full_source_tables={os.path.relpath(data / n, out): outcome['output_sha256'][n] for n in sorted(consumed)},
                             identities='Complete provider event/origin/pick/association IDs, receiver SEED/FDSN codes and both metadata epochs are retained in the attached and referenced source tables; empty locations remain valid.')
            for name in ('comparison_figure.pdf', 'comparison_figure.png', 'event_points.csv', 'model_nodes.csv', 'receiver_epochs.csv'):
                shared.write_json(out / (name + '.identifiers.json'), dict(companion, artifact_sha256=sha(out / name)))
            description = 'The display uses verified accepted iteration %d relative to the identified initial state. It does not establish a converged final solution.' % selected['iteration']
    body = [r'\documentclass[11pt]{article}', r'\usepackage[margin=1in]{geometry}',
            r'\usepackage{graphicx,hyperref}', r'\begin{document}',
            r'\section*{' + tex(MODE_LABEL[mode]) + ': saved outcome}',
            'Numerical status: ' + tex(outcome['status']) + '. Exit code: ' + tex(outcome['return_code']) + '.',
            'Stopped stage: ' + tex(outcome.get('failed_stage') or 'none') + '.', tex(description),
            'The comparison uses identified catalog observations. History RMS and ray diagnostics describe pre-update states. '
            'A fixed-weight objective decrease is distinct from a change in unweighted RMS across iterations. '
            'No final convergence, updated-model accuracy, first-arrival or covariance claim follows from this saved-output display. '
            'The manuscript audit remains one reproduced panel and 61 partial panels.']
    if summary['incomplete_history_tail_ignored']:
        body.append('The incomplete final history line is preserved and excluded from accepted-state joins.')
    if summary['recovery_plot_created']:
        body += [r'\begin{figure}[ht]\centering\includegraphics[width=\linewidth]{comparison_figure.pdf}',
                 r'\caption{Saved model change and source displacement from the initial state. Arrows retain kilometre scale.}', r'\end{figure}']
    body += [r'\end{document}']
    (out / 'report.tex').write_text('\n\n'.join(body) + '\n')
    require(sha(outcome_path) == summary['outcome_sha256'], 'Closed comparison outcome changed during readback')
    summary['output_sha256'] = {p.name: sha(p) for p in out.iterdir() if p.is_file()}
    shared.write_json(out / 'render_summary.json', summary)
    print(json.dumps({k: summary[k] for k in ('status', 'mode', 'saved_output_validation', 'numerical_status', 'recovery_plot_created')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', required=True, choices=tuple(MODE_LABEL))
    parser.add_argument('--data', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path, help='Fresh immediate child of repository tmp/')
    arguments = parser.parse_args()
    data_path = Path(os.path.abspath(str(arguments.data)))
    require(data_path.parent == ROOT / 'data' and data_path.is_dir() and not data_path.is_symlink(),
            'Use an identified immediate child of repository data/')
    render(data_path, arguments.output, arguments.mode)
