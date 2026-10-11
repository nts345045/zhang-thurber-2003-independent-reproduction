#!/usr/bin/env python3
"""Render a closed corrected Hayward attempt; never run or restart a solver."""
import argparse
import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            result.update(block)
    return result.hexdigest()


def local(base, name):
    path = base / name
    require(not path.is_symlink(), 'Symlink input/output: ' + str(path))
    resolved = path.resolve()
    require(base.resolve() in resolved.parents, 'Path must be inside its stated directory')
    return resolved


def table(path, complete_lines=False):
    with path.open(newline='') as stream:
        if complete_lines:
            content = stream.read()
            complete = content[:content.rfind('\n') + 1]
            if not complete:
                return []
            reader = csv.DictReader(io.StringIO(complete))
        else:
            reader = csv.DictReader(stream)
        require(reader.fieldnames and len(set(reader.fieldnames)) == len(reader.fieldnames), 'CSV header')
        rows = list(reader)
    require(all(None not in row and all(v is not None for v in row.values()) for row in rows), 'CSV shape')
    return rows


def write_table(path, rows):
    require(bool(rows), 'Empty identified table')
    with path.open('x', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def finite(value):
    result = float(value)
    require(math.isfinite(result), 'Nonfinite saved value')
    return result


def tex(value):
    replacements = {'\\': r'\textbackslash{}', '&': r'\&', '%': r'\%', '$': r'\$',
                    '#': r'\#', '_': r'\_', '{': r'\{', '}': r'\}',
                    '~': r'\textasciitilde{}', '^': r'\textasciicircum{}'}
    return ''.join(replacements.get(c, c) for c in str(value))


def geometry(data, outcome):
    def closed_table(name, complete_lines=False):
        require(name in outcome['output_sha256'], 'Consumed table absent from closed inventory: ' + name)
        path = local(data, name)
        require(sha(path) == outcome['output_sha256'][name], 'Consumed closed table changed: ' + name)
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
    cc = [r for r in observations if r['type'] == '2']
    for row in observations:
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
    states = outcome['accepted_states']
    require([s['iteration'] for s in states] == sorted(set(s['iteration'] for s in states)), 'Unique accepted iteration order')
    if (data / 'dd_history.csv').exists():
        history = closed_table('dd_history.csv', complete_lines=True)
        accepted = [int(r['iteration']) for r in history if finite(r['step_fraction']) > 0]
        require(accepted == [s['iteration'] for s in states], 'Accepted snapshots agree with closed history')
    else:
        require(not states, 'An accepted state requires its closed iteration history')
    selected = states[-1] if states else None
    final_events, final_grid = events, grid
    if selected:
        for name in ('events_file', 'grid_file'):
            path = local(data, selected[name])
            require(sha(path) == selected['sha256s'][selected[name]], 'Closed accepted snapshot hash')
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
    return events, stations, cc, points, nodes, selected


def render(data, out):
    outcome_path = data / 'rebuild_outcome.json'
    outcome = json.loads(outcome_path.read_text())
    require(outcome['status'] in ('completed_dd_attempt_pending_scientific_review', 'failed_preserved'), 'Closed numerical outcome required')
    require(outcome['outputs_stable'] is True, 'No live scientific-output writer may remain')
    for command in outcome['commands']:
        require(command['outputs_stable'] is True, 'Closed child process group required')
        if command.get('launch_failed'):
            require(not command.get('pid') and not command['child_reaped'], 'Failed launch must not claim an executed child')
        else:
            require(command['child_reaped'] and isinstance(command['return_code'], int), 'Every executed child must be reaped')
    for name, digest in outcome['output_sha256'].items():
        require(sha(local(data, name)) == digest, 'Closed numerical output changed: ' + name)
    history_bytes = ((data / 'dd_history.csv').read_bytes()
                     if 'dd_history.csv' in outcome['output_sha256'] else b'')
    require(not out.exists() and not out.is_symlink(), 'Fresh rendering directory required')
    saved = None
    plotting_error = outcome.get('accepted_state_readback_error')
    if plotting_error is None:
        try:
            saved = geometry(data, outcome)
        except (ValueError, KeyError, IndexError) as error:
            plotting_error = str(error)
    out.mkdir(parents=True)
    for name in ('matplotlib', 'cache', 'tmp'):
        (out / name).mkdir()
    os.environ.update(MPLCONFIGDIR=str(out / 'matplotlib'), XDG_CACHE_HOME=str(out / 'cache'), TMPDIR=str(out / 'tmp'))
    summary = dict(status='rendered_closed_outcome', numerical_status=outcome['status'],
                   numerical_return_code=outcome['return_code'], failed_stage=outcome.get('failed_stage'),
                   outcome_sha256=sha(outcome_path), source_sha256=sha(Path(__file__)),
                   scientific_success=False, history_metrics_scope='pre-update',
                   plotting_validation_error=plotting_error,
                   incomplete_history_tail_ignored=bool(history_bytes) and not history_bytes.endswith(b'\n'),
                   scope='A saved-state diagnostic; no manuscript panel promotion, ray validation, covariance or final convergence inferred.')
    description = 'Preparation stopped before a complete identified plotting input was available.'
    if plotting_error is not None:
        description = 'No scientific plot was made because saved-output validation failed: ' + plotting_error
    if saved is not None:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        events, stations, cc, points, nodes, selected = saved
        write_table(out / 'event_points.csv', points)
        write_table(out / 'model_nodes.csv', nodes)
        write_table(out / 'receiver_epochs.csv', stations)
        if cc:
            write_table(out / 'cc_observations.csv', cc)
        fig, axes = plt.subplots(1, 3, figsize=(15, 4.8), constrained_layout=True)
        section = [r for r in nodes if finite(r['z']) == 8.0]
        require(bool(section), 'Declared 8 km model section')
        values = [r['delta_v_km_s'] if selected else finite(r['v']) for r in section]
        style = dict(cmap='viridis')
        if selected:
            limit = max(map(abs, values))
            if limit:
                style = dict(cmap='RdBu_r', vmin=-limit, vmax=limit)
        artist = axes[0].scatter([finite(r['x']) for r in section], [finite(r['y']) for r in section], c=values, s=65, marker='s', **style)
        fig.colorbar(artist, ax=axes[0], label=('Velocity change' if selected else 'Initial P velocity') + ' (km/s)', shrink=.8)
        axes[0].set_title(('Accepted minus initial' if selected else 'Initial model') + ', z = 8 km')
        axes[1].scatter([finite(r['x']) for r in events], [finite(r['y']) for r in events], s=3, color='0.6')
        if selected:
            axes[1].quiver([finite(r['x']) for r in events], [finite(r['y']) for r in events],
                           [r['dx_km'] for r in points], [r['dy_km'] for r in points],
                           angles='xy', scale_units='xy', scale=1, width=.002, color='tab:blue')
        axes[1].set_title('Source displacements, scale 1:1' if selected else 'Initial source positions')
        used_events, used_stations = set(), set()
        for row in cc:
            i, j = int(row['i']), int(row['j'])
            used_events.update((i, j)); used_stations.update((int(row['station']), int(row['station_j'])))
            axes[2].plot([finite(events[k]['x']) for k in (i, j)], [finite(events[k]['y']) for k in (i, j)], color='tab:blue', alpha=.4, linewidth=.6)
        axes[2].scatter([finite(events[k]['x']) for k in sorted(used_events)], [finite(events[k]['y']) for k in sorted(used_events)], s=8, label='CC events')
        axes[2].scatter([finite(stations[k]['x']) for k in sorted(used_stations)], [finite(stations[k]['y']) for k in sorted(used_stations)], s=25, marker='^', color='tab:orange', label='Receiver epochs')
        axes[2].set_title('CC pairs at initial source positions')
        if cc:
            axes[2].legend(fontsize=8)
        for ax in axes:
            ax.set(xlabel='Local x (km)', ylabel='Local y (km)', aspect='equal', xlim=(-35, 35), ylim=(-30, 30))
            ax.grid(alpha=.15)
        fig.savefig(out / 'rebuild_figure.pdf')
        fig.savefig(out / 'rebuild_figure.png', dpi=180)
        plt.close(fig)
        summary.update(events=len(events), receiver_epochs=len(stations), cc_rows=len(cc),
                       accepted_iterations=len(outcome['accepted_states']), selected_iteration=selected['iteration'] if selected else None,
                       displacement_3d_max_km=max(r['displacement_3d_km'] for r in points),
                       velocity_change_range_km_s=[min(r['delta_v_km_s'] for r in nodes), max(r['delta_v_km_s'] for r in nodes)])
        description = ('The figure uses accepted iteration %s and its original identified initial state.' % selected['iteration']
                       if selected else 'No accepted update is reported. The figure shows only the identified initial model, sources and CC support.')
        input_names = ['initial_events.csv', 'initial_grid.csv', 'stations.csv', 'observations.csv']
        if (data / 'dd_history.csv').exists():
            input_names.append('dd_history.csv')
        if selected:
            input_names += [selected['events_file'], selected['grid_file']]
        companion = dict(events='event_points.csv', receiver_epochs='receiver_epochs.csv', cc_observations='cc_observations.csv' if cc else None,
                         output_sha256={p.name: sha(p) for p in out.glob('*.csv')}, outcome_sha256=sha(outcome_path),
                         full_source_tables={os.path.relpath(data / name, out): sha(data / name) for name in input_names},
                         identities='Provider event/origin/pick/association IDs, both native receiver epochs and SEED/FDSN codes remain in the attached tables. Empty location codes are valid.')
        for name in ('rebuild_figure.pdf', 'rebuild_figure.png', 'model_nodes.csv'):
            (out / (name + '.identifiers.json')).write_text(json.dumps(dict(companion, artifact_sha256=sha(out / name)), indent=2) + '\n')
        summary['matplotlib_version'] = matplotlib.__version__
    body = [r'\documentclass[11pt]{article}', r'\usepackage[margin=1in]{geometry}',
            r'\usepackage{graphicx,hyperref}', r'\begin{document}',
            r'\section*{Corrected Hayward rebuild: saved outcome}',
            'Numerical status: ' + tex(outcome['status']) + r'. Exit code: ' + tex(outcome['return_code']) + '.\n',
            'Stopped stage: ' + tex(outcome.get('failed_stage') or 'none') + '.\n', tex(description) + '\n',
            'The intended workflow uses the documented authoritative subset and saved normalized waveform cross-correlations. '
            'Historical calibration responses are not prerequisites. The mixed stage weights make this a data and weighting experiment. '
            'Squared correlation is a row multiplier, not an estimated timing variance.\n',
            'Saved accepted states are intermediate models. History RMS values describe pre-update states. '
            'No final convergence, updated-model accuracy, global first arrival or combined covariance is established by this rendering. '
            'The manuscript audit remains one reproduced panel and 61 partial panels.\n']
    if summary['incomplete_history_tail_ignored']:
        body.append('The raw history file ends with an incomplete line. Only its complete newline-terminated rows '
                    'were joined to accepted snapshots; the original bytes remain preserved.\n')
    if saved is not None:
        body += [r'\begin{figure}[ht]\centering\includegraphics[width=\linewidth]{rebuild_figure.pdf}',
                 r'\caption{Saved model nodes and local source geometry. Arrows use native kilometre scale. '
                 r'CC lines join event pairs at their initial positions; they are not ray paths.}', r'\end{figure}']
    body += [r'\href{https://github.com/nts345045/zhang-thurber-2003-independent-reproduction/blob/main/report/report.pdf}{Comprehensive manuscript reproduction report}.',
             r'\end{document}']
    (out / 'report.tex').write_text('\n\n'.join(body) + '\n')
    summary['output_sha256'] = {p.name: sha(p) for p in out.iterdir() if p.is_file()}
    (out / 'render_summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n')
    print(json.dumps({k: summary[k] for k in ('status', 'numerical_status', 'scientific_success')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    render(local(ROOT, args.data), local(ROOT, args.output))
