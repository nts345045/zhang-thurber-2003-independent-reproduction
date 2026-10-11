#!/usr/bin/env python3
"""Read one closed catalog-plus-CC DD attempt; never run a numerical model."""
import argparse
import json
import os
from pathlib import Path
import sys

sys.dont_write_bytecode = True
import plot_hayward_corrected as saved
import rebuild_hayward_corrected as shared

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'tmp/hayward_catalog_cc_backtracking_source_001'
PACKAGE = ROOT / 'data/development/hayward_corrected_rebuild_sources_001'
require, sha, local, table = saved.require, saved.sha, saved.local, saved.table
finite, write_table, tex = saved.finite, saved.write_table, saved.tex
PINS = {
    'plot_hayward_corrected.py': '8eadadaf8b0b1967ff7878fbe82b18c40502490e2ea78e3221c335c4252d9f6c',
    'rebuild_hayward_corrected.py': 'a9a07fa490b8eecdbdc10e3118288fbc3692b04800b75b224a53d8e763182769',
    'data/development/hayward_corrected_rebuild_sources_001/source_mapping.json': 'd462f00bae8443fa32d10e0b1b226651e3712ab32d061a05e50d1b2207db4c95',
    'tmp/hayward_catalog_cc_backtracking_source_001/controller.py': '595ce3b1d4ac57ef41cb45737391ae22439fe8bde0840e35d0a4a97aa47aa4fc',
    'tmp/hayward_catalog_cc_backtracking_source_001/run_hayward_catalog_cc_backtracking.py': '0b9d7c795b765b8314c5b7b4dea80983a5f726e294508a554f0c41457b4e3a06',
    'tmp/hayward_catalog_cc_backtracking_source_001/binding_pins.json': 'c5bab4b1503a528486236ebfd6ac8a7cad3f212b539385761299bdda0197316c',
    'tmp/hayward_catalog_cc_backtracking_source_001/plan.json': 'ee79c790957891fd1c9dfda2cfdfc09babcc5b7d01ca170b01c443bdacab25b8',
}


def read_json(path):
    return json.loads(path.read_text())


def closed_attempt(data, controller_path):
    """Read the existing schemas without rewriting or relabeling their receipts."""
    for name, digest in PINS.items():
        require(sha(ROOT / name) == digest, 'Reviewed source changed: ' + name)
    mapping = read_json(PACKAGE / 'source_mapping.json')
    for name in ('scientific_inputs.json', 'run.cfg'):
        require(sha(PACKAGE / name) == mapping['package_sha256'][name], 'Reviewed scientific binding changed: ' + name)
    expected = read_json(PACKAGE / 'scientific_inputs.json')
    config_sha = mapping['package_sha256']['run.cfg']
    require(sha(SOURCE / 'run.cfg') == config_sha, 'Combined configuration changed')
    plan_path = SOURCE / 'plan.json'
    plan, outer = read_json(plan_path), read_json(controller_path)
    evidence = {str(p.relative_to(ROOT)): sha(p) for p in (plan_path, controller_path)}
    require(outer['controller_sha256'] == PINS[str((SOURCE / 'controller.py').relative_to(ROOT))] and
            outer['plan_sha256'] == sha(plan_path) and outer['command'] == plan['command'], 'Outer source/plan/command join')
    require(outer['status'] in ('launcher_reaped', 'failed_preserved', 'interrupted') and outer.get('finished_utc'),
            'Actual closed controller receipt required')
    require(outer['launcher_reaped'] is True and outer['remaining_live_group_members'] == [] and
            not outer.get('group_inventory_unresolved'), 'Closed launcher and no unresolved live writers required')
    require(plan['mode'] == 'dd' and ROOT / plan['output'] == data and
            plan['source_sha256'] == mapping['numerical_source_sha256'], 'Prepared mode/output/numerical source differs')
    for name in ('controller.py', 'run_hayward_catalog_cc_backtracking.py', 'binding_pins.json'):
        key = str((SOURCE / name).relative_to(ROOT))
        require(plan['combined_source_sha256'][key] == PINS[key], 'Plan source differs: ' + name)
    require(plan['combined_source_sha256'][str((SOURCE / 'run.cfg').relative_to(ROOT))] == config_sha,
            'Prepared combined configuration differs')
    intended = dict(expected['expected_catalog_sha256'])
    intended.update({'observations.csv': expected['expected_combined_observations_sha256'], 'run.cfg': config_sha})
    require(all(plan['numerical_input_sha256'].get(n) == h for n, h in intended.items()),
            'Prepared scientific inputs differ from the reviewed combined experiment')
    info = dict(controller_status=outer['status'], controller_return_code=outer.get('return_code'),
                launcher_return_code=outer.get('launcher_return_code', outer.get('return_code')),
                inner_status=None, inner_return_code=None, dd_invert_return_code=None,
                dd_return_code_scope='Recorded GNU-time-supervised dd_invert return, not an invented direct-child observation.',
                last_recorded_command_stage=None, error=outer.get('error'), evidence_sha256=evidence,
                scientific_source_sha256=mapping['numerical_source_sha256'], input_sha256=None,
                unavailable_reason=None)
    inner_path = data / 'dd_inversion_execution.json'
    if not inner_path.is_file():
        require(outer['status'] != 'launcher_reaped', 'Successful launcher has no inner receipt')
        info['unavailable_reason'] = 'The launcher closed before an inner numerical receipt was available.'
        return info, None, None
    require(outer['inner_execution_sha256'] == sha(inner_path), 'Inner receipt changed after controller closure')
    evidence[str(inner_path.relative_to(ROOT))] = sha(inner_path)
    inner = read_json(inner_path)
    require(inner['mode'] == 'dd' and inner['driver_pid'] == outer['launcher_pid'] and
            inner['command'] == plan['command'][1:], 'Inner launcher identity/mode/command differs')
    if 'inner_status' in outer:
        require(outer['inner_status'] == inner['status'], 'Outer/inner status differs')
    info.update(inner_status=inner['status'], inner_return_code=inner.get('return_code'),
                last_recorded_command_stage=inner.get('current_stage'), error=inner.get('error', outer.get('error')))
    commands = inner['completed_commands']
    for command in commands:
        require(isinstance(command['return_code'], int) and command['remaining_live_group_members'] == [],
                'Recorded completed command retains live writers')
    inverse = [c for c in commands if c['stage'] == 'dd_invert']
    require(len(inverse) <= 1, 'Multiple inverse commands are outside this attempt')
    exception = inner.get('exception_child')
    if exception is not None:
        require(exception['remaining_live_group_members'] == [], 'Exception cleanup did not settle live writers')
    if inverse:
        info['dd_invert_return_code'] = inverse[0]['return_code']
    elif exception is not None and inner.get('current_stage') == 'dd_invert':
        require(exception['pid'] == inner['current_child_pid'], 'Exception child identity differs')
        info['dd_invert_return_code'] = exception.get('return_code')
    complete = inner['status'] == 'completed_pending_final_diagnostics'
    if complete:
        require(outer['status'] == 'launcher_reaped' and outer['return_code'] == inner['return_code'] == 0 and
                len(inverse) == 1 and inverse[0]['return_code'] == 0 and
                all(c['return_code'] == 0 for c in commands), 'Successful inner/outer command joins differ')
        require(inner['immutable_inputs_verified'] and inner['original_preflight_verified'], 'Missing completed input checks')
        generated = inner['output_sha256']
    else:
        require(outer['status'] != 'launcher_reaped', 'Successful outer receipt lacks completed inner disposition')
        generated = inner.get('partial_output_sha256') if inner['status'] in ('failed', 'interrupted') else None
    if generated is None or 'dd_inversion_run_manifest.json' not in generated:
        info['unavailable_reason'] = 'No closed scientific file inventory and run manifest are available; no geometry is admitted.'
        return info, None, None
    manifest_path = local(data, 'dd_inversion_run_manifest.json')
    require(sha(manifest_path) == generated[manifest_path.name], 'Closed run manifest hash differs')
    evidence[str(manifest_path.relative_to(ROOT))] = sha(manifest_path)
    manifest = read_json(manifest_path)
    require(manifest['mode'] == 'dd' and manifest['input_sha256'] == plan['numerical_input_sha256'] and
            manifest['combined_configuration'] == plan['numerical_settings'] and
            manifest['expected_counts'] == plan['expected_counts'], 'Actual inputs/settings/counts differ from preparation')
    require({n: manifest['source_sha256'].get(n) for n in mapping['numerical_source_sha256']} ==
            mapping['numerical_source_sha256'], 'Actual compiled numerical source differs')
    for source_name, original_name in (('run_hayward_catalog_cc_backtracking.py', 'run_hayward_catalog_cc_backtracking.py'),
                                       ('binding_pins.json', 'binding_pins.json')):
        require(manifest['source_sha256'][source_name] == PINS[str((SOURCE / original_name).relative_to(ROOT))],
                'Actual launcher source differs: ' + source_name)
    require(manifest['source_sha256']['combined_run.cfg'] == config_sha and
            manifest['source_sha256']['diagnostics/review_old_kernel_trial_completion.py'] ==
            '8406148ed92afa18c43bf96693aaa78185f7961e99e567e4f8aced6d1d858392', 'Actual configuration/completion helper differs')
    inventory = dict(manifest['input_sha256'])
    for name, digest in generated.items():
        require(name not in inventory or inventory[name] == digest, 'Conflicting input/output hash: ' + name)
        inventory[name] = digest
    require(sha(local(data, 'run.cfg')) == config_sha == inventory['run.cfg'], 'Consumed configuration differs')
    info['input_sha256'] = manifest['input_sha256']
    contract = None
    if 'dd_output_contract.json' in generated:
        path = local(data, 'dd_output_contract.json')
        require(sha(path) == generated[path.name], 'Closed output contract changed')
        evidence[str(path.relative_to(ROOT))] = sha(path)
        contract = read_json(path)
    if complete:
        require(contract is not None and contract['status'] == inner['status'] and
                contract['final_full_gate']['source_sha256'] == mapping['numerical_source_sha256']['src/main.cpp'],
                'Completed attempt lacks its source-bound saved-output contract')
    return info, dict(output_sha256=inventory, accepted_states=[]), contract


def accepted_geometry(data, view, contract, complete):
    """Pin only consumed tables, then call the unchanged accepted-state and DD readers."""
    names = {'initial_events.csv', 'initial_grid.csv', 'stations.csv', 'observations.csv'}

    def verify(name):
        require(name in view['output_sha256'] and sha(local(data, name)) == view['output_sha256'][name],
                'Consumed scientific table absent or changed: ' + name)

    for name in names:
        verify(name)
    if (data / 'dd_history.csv').exists():
        verify('dd_history.csv'); names.add('dd_history.csv')
        for row in table(local(data, 'dd_history.csv'), complete_lines=True):
            if finite(row['step_fraction']) <= 0:
                continue
            iteration = int(row['iteration'])
            require(0 <= iteration < 18, 'Accepted iteration outside the original budget')
            names.add('dd_iteration_%d_trials.csv' % iteration)
            names.update('dd_accepted_it_%d_%s.csv' % (iteration, kind) for kind in ('events', 'grid'))
    for name in names:
        verify(name)
    states, notes = shared.accepted_states(data)
    view['accepted_states'] = states
    if complete:
        pins = {name: digest for state in states for name, digest in state['sha256s'].items()}
        snapshot = contract['accepted_snapshot_evidence']
        require(snapshot['artifact_sha256'] == pins and snapshot['accepted_updates'] == len(states) ==
                contract['accepted_iterations'] and snapshot['snapshot_files'] == 2 * len(states),
                'Existing output contract and accepted-state readback differ')
    geometry = saved.geometry(data, view)
    require(geometry is not None, 'Complete identified geometry required')
    events, stations, cc, points, nodes, selected = geometry
    require((len(events), len(stations), len(nodes), len(cc)) == (1092, 372, 462, 98), 'Combined geometry/CC inventory differs')
    return geometry, states, notes, {name: view['output_sha256'][name] for name in sorted(names)}


def render(data, out, controller_path):
    info, view, contract = closed_attempt(data, controller_path)
    out = shared.fresh_path(out, ROOT / 'tmp')
    geometry, states, notes, consumed, error = None, [], [], {}, None
    if view is not None:
        try:
            geometry, states, notes, consumed = accepted_geometry(
                data, view, contract, info['inner_status'] == 'completed_pending_final_diagnostics')
        except (ValueError, KeyError, IndexError) as exception:
            error = str(exception)
    out.mkdir(parents=True)
    summary = dict(status='rendered_closed_catalog_cc_attempt', mode='dd',
                   data_directory=str(data.relative_to(ROOT)), receipt_disposition=info,
                   source_sha256=sha(Path(__file__)), reused_source_sha256=PINS,
                   saved_output_validation='failed' if error else 'passed' if geometry is not None else 'unavailable',
                   plotting_validation_error=error, accepted_states=states, accepted_state_notes=notes,
                   accepted_iterations=len(states) if geometry is not None else None, selected_iteration=None,
                   consumed_table_sha256=consumed, recovery_plot_created=False, scientific_success=False,
                   history_metrics_scope='pre-update',
                   scope='Saved accepted geometry; no solver, ray, covariance, final-accuracy or convergence calculation.')
    description = info['unavailable_reason'] or 'No accepted update is verified; no recovery plot is produced.'
    if error is not None:
        description = 'Saved-output validation failed; no recovery plot is produced: ' + error
    if geometry is not None and geometry[-1] is not None:
        events, stations, cc, points, nodes, selected = geometry
        for name in ('matplotlib', 'cache', 'tmp'):
            (out / name).mkdir()
        os.environ.update(MPLCONFIGDIR=str(out / 'matplotlib'), XDG_CACHE_HOME=str(out / 'cache'), TMPDIR=str(out / 'tmp'))
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        for name, rows in (('event_points.csv', points), ('model_nodes.csv', nodes),
                           ('receiver_epochs.csv', stations), ('cc_observations.csv', cc)):
            write_table(out / name, rows)
        fig, axes = plt.subplots(1, 2, figsize=(10, 4.8), constrained_layout=True)
        section = [r for r in nodes if finite(r['z']) == 8.0]
        require(bool(section), 'Declared 8 km saved grid section')
        values = [r['delta_v_km_s'] for r in section]; limit = max(map(abs, values))
        if limit:
            artist = axes[0].scatter([finite(r['x']) for r in section], [finite(r['y']) for r in section],
                                     c=values, s=65, marker='s', cmap='RdBu_r', vmin=-limit, vmax=limit)
            fig.colorbar(artist, ax=axes[0], label='Velocity change (km/s)', shrink=.8)
        else:
            axes[0].scatter([finite(r['x']) for r in section], [finite(r['y']) for r in section],
                            color='0.5', s=65, marker='s', label='Velocity change = 0 km/s')
            axes[0].legend(fontsize=8)
        axes[0].set_title('Accepted minus initial, z = 8 km')
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
            margin = .02 * (upper - lower); limits[coordinate] = [lower - margin, upper + margin]
        for ax in axes:
            ax.set(xlabel='Local x (km)', ylabel='Local y (km)', aspect='equal', xlim=limits['x'], ylim=limits['y'])
            ax.grid(alpha=.15)
        fig.suptitle('Catalog plus CC DD: accepted iteration ' + str(selected['iteration']))
        for suffix in ('pdf', 'png'):
            fig.savefig(out / ('combined_figure.' + suffix), **({'dpi': 180} if suffix == 'png' else {}))
        plt.close(fig)
        summary.update(recovery_plot_created=True, selected_iteration=selected['iteration'], events=len(events),
                       receiver_epochs=len(stations), cc_rows=len(cc), plot_limits_km=limits,
                       displacement_3d_max_km=max(r['displacement_3d_km'] for r in points),
                       velocity_change_range_km_s=[min(r['delta_v_km_s'] for r in nodes), max(r['delta_v_km_s'] for r in nodes)],
                       matplotlib_version=matplotlib.__version__)
        companion = dict(events='event_points.csv', receiver_epochs='receiver_epochs.csv', cc_observations='cc_observations.csv',
                         output_sha256={p.name: sha(p) for p in out.glob('*.csv')},
                         full_source_tables={os.path.relpath(data / n, out): h for n, h in consumed.items()},
                         closure_evidence={os.path.relpath(ROOT / n, out): h for n, h in info['evidence_sha256'].items()},
                         identities='Complete event/origin/pick/association and CC measurement fields, both native receiver epochs and SEED/FDSN codes are preserved. Empty locations remain valid.')
        for name in ('combined_figure.pdf', 'combined_figure.png', 'event_points.csv', 'model_nodes.csv',
                     'receiver_epochs.csv', 'cc_observations.csv'):
            shared.write_json(out / (name + '.identifiers.json'), dict(companion, artifact_sha256=sha(out / name)))
        description = 'The display uses verified accepted iteration %d relative to the identified initial state; it does not establish a converged final solution.' % selected['iteration']
    body = [r'\documentclass[11pt]{article}', r'\usepackage[margin=1in]{geometry}',
            r'\usepackage{graphicx,hyperref}', r'\begin{document}',
            r'\section*{Catalog-plus-CC DD: closed saved outcome}',
            'Controller status: ' + tex(info['controller_status']) + '. Launcher return: ' + tex(info['launcher_return_code']) + '.',
            'Inner status: ' + tex(info['inner_status']) + '. Inner return: ' + tex(info['inner_return_code']) + '.',
            'Recorded inverse-command return: ' + tex(info['dd_invert_return_code']) + '. Last command stage: ' + tex(info['last_recorded_command_stage']) + '.',
            tex(description),
            'A missing return code remains unknown. The last command stage is not necessarily the cause of a later saved-output validation failure.',
            'This is the declared catalog-plus-CC data and weighting experiment. Saved CC squared is an empirical row multiplier; its squared-objective factor is CC to the fourth power. CC timing uncertainty remains unestimated.',
            'History RMS and ray diagnostics describe pre-update states. No final accuracy, first-arrival, covariance or convergence claim follows from this display. The manuscript audit remains one reproduced and 61 partial panels.']
    if summary['recovery_plot_created']:
        body += [r'\begin{figure}[ht]\centering\includegraphics[width=\linewidth]{combined_figure.pdf}',
                 r'\caption{Saved velocity change and source displacement from the identified initial state; arrows retain kilometre scale.}', r'\end{figure}']
    body.append(r'\end{document}')
    (out / 'report.tex').write_text('\n\n'.join(body) + '\n')
    for name, digest in info['evidence_sha256'].items():
        require(sha(ROOT / name) == digest, 'Closed receipt changed during readback: ' + name)
    for name, digest in consumed.items():
        require(sha(local(data, name)) == digest, 'Consumed table changed during readback: ' + name)
    summary['output_sha256'] = {p.name: sha(p) for p in out.iterdir() if p.is_file()}
    shared.write_json(out / 'render_summary.json', summary)
    print(json.dumps({k: summary[k] for k in ('status', 'saved_output_validation', 'recovery_plot_created')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', required=True, type=Path)
    parser.add_argument('--controller-receipt', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    arguments = parser.parse_args()
    data = local(ROOT, arguments.data)
    require(data == ROOT / 'data/hayward_catalog_cc_backtracking_001', 'Use the identified combined attempt')
    render(data, arguments.output, local(ROOT, arguments.controller_receipt))
