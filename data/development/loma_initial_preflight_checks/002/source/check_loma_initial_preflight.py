#!/usr/bin/env python3
"""Invented end-to-end, native-join, stopping-flag and lifecycle preflight controls."""
import argparse
import copy
import csv
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import run_loma_initial_preflight as launcher


def process_group(group):
    members = []
    for path in Path('/proc').glob('[0-9]*/stat'):
        try:
            text = path.read_text(); fields = text[text.rfind(')') + 2:].split()
            if int(fields[2]) == group:
                members.append(dict(pid=int(path.parent.name), state=fields[0], start_ticks=fields[19]))
        except (FileNotFoundError, ProcessLookupError):
            pass
    return members


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--build', required=True)
    args = parser.parse_args()
    out = launcher.inside(ROOT, ROOT / args.output)
    build = launcher.inside(ROOT, ROOT / args.build)
    assert not out.exists() and not build.exists()
    out.mkdir(parents=True)
    fixture = ROOT / 'data/development/analytic_simulation_launcher_002/prepared_before_launch'
    simulation = out / 'invented_simulation'
    shutil.copytree(str(fixture), str(simulation))
    with (simulation / 'run.cfg').open('a') as f:
        f.write('stage_length 6\nsmoothing 5\ndamping 0.1\niterations 18\n')
    (simulation / 'ray_samples.csv').write_text('event,station\n0,0\n1,0\n0,1\n1,1\n')
    manifest = json.loads((simulation / 'preparation_manifest.json').read_text())
    manifest['counts']['diagnostic_sample_rays'] = 4
    (simulation / 'preparation_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    prepared = json.loads((simulation / 'analytic_truth_manifest.json').read_text())
    prepared['prepared_sha256'] = {str(p.relative_to(simulation)): launcher.sha(p) for p in simulation.rglob('*')
                                  if p.is_file() and p.name != 'analytic_truth_manifest.json'}
    (simulation / 'analytic_truth_manifest.json').write_text(json.dumps(prepared, indent=2) + '\n')
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', TMPDIR=str(ROOT / 'tmp'))
    commands, checks = [], []

    def command(argv, name):
        with (out / (name + '_stdout.log')).open('w') as stdout, (out / (name + '_stderr.log')).open('w') as stderr:
            code = subprocess.call([str(x) for x in argv], cwd=str(ROOT), env=env, stdout=stdout, stderr=stderr)
        commands.append(dict(stage=name, command=list(map(str, argv)), return_code=code))
        assert code == 0, '{} failed; preserve logs'.format(name)

    command([sys.executable, ROOT / 'run_loma_analytic_simulation.py', '--data', simulation,
             '--build', build / 'simulation', '--threads', '2'], 'simulation')
    command([sys.executable, ROOT / 'diagnostics/review_loma_analytic_simulation.py', '--data', simulation,
             '--output', simulation / 'independent_simulation_review.json'], 'simulation_review')
    expected, pinned = launcher.reviewed_simulation(simulation)
    checks.append(dict(name='requires_genuine_terminal_invented_simulation_and_full_output_review', passed=True))
    baseline = {p: p.read_bytes() for p in simulation.rglob('*') if p.is_file()}

    def reject(name, mutate, function, paths=None):
        originals = {p: p.read_bytes() for p in (paths or baseline)}
        try:
            mutate()
            try: function()
            except (ValueError, KeyError) as error:
                checks.append(dict(name=name, passed=True, message=str(error)))
            else: raise AssertionError('Accepted invalid fixture: ' + name)
        finally:
            for p, content in originals.items(): p.write_bytes(content)

    def change_json(path, update):
        value = json.loads(path.read_text()); update(value)
        path.write_text(json.dumps(value) + '\n')

    check_inputs = lambda: launcher.reviewed_simulation(simulation)
    ledger = simulation / 'simulation_execution.json'
    review = simulation / 'independent_simulation_review.json'
    reject('failed_simulation_rejected', lambda: change_json(ledger, lambda v: v.update(status='failed')), check_inputs, [ledger])
    reject('missing_successful_child_rejected', lambda: change_json(ledger, lambda v: v.update(completed_commands=[])), check_inputs, [ledger])
    reject('failed_review_rejected', lambda: change_json(review, lambda v: v.update(status='failed')), check_inputs, [review])
    reject('stale_review_link_rejected', lambda: change_json(review, lambda v: v.update(simulation_execution_sha256='stale')), check_inputs, [review])
    for name in ('initial_events.csv', 'initial_grid.csv', 'observations.csv', 'ray_samples.csv'):
        p = simulation / name
        reject('changed_' + name + '_rejected', lambda p=p: p.write_text('changed\n'), check_inputs, [p])
    reject('source_nested_output_rejected', lambda: None, lambda: launcher.disjoint(simulation, simulation / 'out', build))
    reject('ancestor_output_rejected', lambda: None, lambda: launcher.disjoint(simulation, simulation.parent, build))
    reject('missing_stage_length_rejected', lambda: None, lambda: launcher.configuration('authoritative_geometry 1\n'))
    reject('invalid_inherited_numeric_token_rejected', lambda: None,
           lambda: launcher.configuration('authoritative_geometry 1\nstage_length nan\n'))
    run = out / 'preflight'
    argv = [sys.executable, ROOT / 'run_loma_initial_preflight.py', '--simulation', simulation,
            '--output', run, '--build', build / 'preflight']
    command(argv, 'preflight')
    execution = json.loads((run / 'preflight_execution.json').read_text())
    result = json.loads((run / 'preflight_checks.json').read_text())
    manifest = json.loads((run / 'preflight_run_manifest.json').read_text())
    assert execution['status'] == 'completed' and execution['return_code'] == 0
    assert result['status'] == 'ready_for_accuracy_review' and result['inversion_accepted'] is False
    assert result['full']['full_rays'] == 4 and result['sample']['sample_rays'] == 4
    assert result['sample']['derivative_components'] == 12
    assert all(row['return_code'] == 0 and 'maximum_resident_set_kbytes' in row for row in execution['completed_commands'])
    launcher.verify_hashes(run, execution['output_sha256']); launcher.verify_hashes(run, manifest['input_sha256'])
    assert manifest['settings'] == launcher.SETTINGS and manifest['matrix_iteration'] == manifest['matrix_stage'] == 0
    assert len([r for r in execution['completed_commands'] if 'invert' in r['command']]) == 1
    assert 'matrix_preflight_only 1\n' in (run / 'run.cfg').read_text()
    assert not list(launcher.rows(run / 'dd_history.csv')) and not (run / 'dd_events.csv').exists()
    assert (run / 'ray_samples.csv').read_bytes() == baseline[simulation / 'ray_samples.csv']
    checks.append(dict(name='real_frozen_build_full_matrix_census_and_geometry_only_refinement', passed=True,
                       full_rays=4, sample_rays=4, valid_fd_components=12))
    checks.append(dict(name='all_child_exit_codes_and_measured_RSS_recorded', passed=True))
    checks.append(dict(name='no_inverse_solve_outputs_or_automatic_accuracy_acceptance', passed=True))
    assert all(p.read_bytes() == content for p, content in baseline.items())
    checks.append(dict(name='raw_simulation_and_native_sample_file_preserved_byte_exactly', passed=True))
    geometry = launcher.inventory(run, expected)

    def edit_csv(path, index, key, value):
        with path.open() as f:
            reader = csv.DictReader(f); header = reader.fieldnames; table = list(reader)
        table[index][key] = value
        with path.open('w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=header); writer.writeheader(); writer.writerows(table)

    full_path = run / 'dd_preflight_ray_status.csv'
    for key, value in [('source_event_resource_id', 'wrong'), ('receiver_channel_seed_id', 'wrong'),
                       ('source_t', '99'), ('source_dx', 'nan'), ('ray_finite', '0'),
                       ('ray_exact_source_endpoint', '0'), ('ray_path_in_domain', '0'),
                       ('ray_initialization_succeeded', '0'), ('event', '1')]:
        reject('full_' + key + '_rejected', lambda key=key, value=value: edit_csv(full_path, 0, key, value),
               lambda: launcher.check_full(run, expected, geometry), [full_path])
    raw = full_path.read_bytes()
    edit_csv(full_path, 0, 'ray_converged', '0')
    failed = launcher.check_full(run, expected, geometry)
    assert failed['local_converged'] == 3 and failed['local_failures'][0]['event_resource_id']
    required_ids = {'event_resource_id', 'origin_resource_id', 'network_code', 'station_code',
                    'location_code', 'channel_code', 'channel_seed_id', 'channel_fdsn_source_id',
                    'metadata_epoch_start', 'metadata_epoch_end'}
    assert required_ids <= set(failed['local_failures'][0])
    full_path.write_bytes(raw)
    checks.append(dict(name='false_full_local_flag_is_retained_scientific_failure_not_missing_diagnostics', passed=True))
    sample_path = run / (launcher.PREFIX + '_convergence.csv')
    derivative_path = run / (launcher.PREFIX + '_derivatives.csv')
    identity_path = run / (launcher.PREFIX + '_identifiers.csv')
    for path, key, value in [(sample_path, 'refined_path_spacing', '1'),
                             (sample_path, 'production_initialization_succeeded', '0'),
                             (sample_path, 'refined_time', 'nan'),
                             (identity_path, 'source_x', '99'),
                             (identity_path, 'receiver_metadata_epoch_end', 'invented'),
                             (derivative_path, 'axis', '9'),
                             (derivative_path, 'plus_initialization_succeeded', '0')]:
        reject('sample_' + key + '_rejected', lambda path=path, key=key, value=value: edit_csv(path, 0, key, value),
               lambda: launcher.check_sample(run, geometry), [path])
    raw = derivative_path.read_bytes()
    edit_csv(derivative_path, 0, 'minus_converged', '0')
    failed = launcher.check_sample(run, geometry)
    assert len(failed['local_failures']) == 1 and required_ids <= set(failed['local_failures'][0])
    derivative_path.write_bytes(raw)
    checks.append(dict(name='false_FD_local_flag_is_retained_scientific_failure', passed=True))
    raw = sample_path.read_bytes()
    edit_csv(sample_path, 0, 'refined_converged', '0')
    failed = launcher.check_sample(run, geometry)
    assert len(failed['local_failures']) == 1 and required_ids <= set(failed['local_failures'][0])
    sample_path.write_bytes(raw)
    checks.append(dict(name='full_sample_and_FD_failures_all_retain_native_IDs_and_valid_blank_epochs', passed=True))
    # The inventory derives central-difference support from actual initial bounds.
    initial = run / 'initial_events.csv'; raw = initial.read_bytes()
    edit_csv(initial, 0, 'z', '-1')
    bounded = launcher.inventory(run, expected)
    assert len(bounded[4]) == 10
    initial.write_bytes(raw)
    checks.append(dict(name='boundary_initial_sources_omit_only_out_of_domain_central_differences', passed=True))
    with (out / 'repeat_stdout.log').open('w') as a, (out / 'repeat_stderr.log').open('w') as b:
        assert subprocess.call(list(map(str, argv)), cwd=str(ROOT), env=env, stdout=a, stderr=b) != 0
    checks.append(dict(name='existing_run_cannot_be_overwritten', passed=True))
    failing_tools = out / 'failed_child_tools'; failing_tools.mkdir()
    (failing_tools / 'cmake').write_text('#!/bin/sh\n# Invented launcher child-failure control only.\nexit 23\n')
    (failing_tools / 'cmake').chmod(0o755)
    failed_run = out / 'failed_child_preflight'
    failed_command = [sys.executable, ROOT / 'run_loma_initial_preflight.py', '--simulation', simulation,
                      '--output', failed_run, '--build', build / 'failed_child']
    with (out / 'failed_child_stdout.log').open('w') as a, (out / 'failed_child_stderr.log').open('w') as b:
        code = subprocess.call(list(map(str, failed_command)), cwd=str(ROOT),
                               env=dict(env, PATH=str(failing_tools) + os.pathsep + env['PATH']), stdout=a, stderr=b)
    assert code != 0
    failure = json.loads((failed_run / 'preflight_execution.json').read_text())
    assert failure['status'] == 'failed' and failure['return_code'] == 23
    assert len(failure['completed_commands']) == 1 and failure['completed_commands'][0]['return_code'] == 23
    launcher.verify_hashes(failed_run, failure['partial_output_sha256'])
    assert not (failed_run / 'dd_history.csv').exists()
    checks.append(dict(name='failed_child_exit_code_and_partial_artifact_hashes_preserved_without_later_stages', passed=True))
    interrupted = out / 'interrupted_preflight'
    interrupt_command = [sys.executable, ROOT / 'run_loma_initial_preflight.py', '--simulation', simulation,
                         '--output', interrupted, '--build', build / 'interrupted']
    with (out / 'interruption_stdout.log').open('w') as stdout, (out / 'interruption_stderr.log').open('w') as stderr:
        child = subprocess.Popen(list(map(str, interrupt_command)), cwd=str(ROOT), env=env, stdout=stdout, stderr=stderr)
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            path = interrupted / 'preflight_execution.json'
            record = json.loads(path.read_text()) if path.exists() else {}
            if record.get('current_stage') == 'compile' and record.get('current_child_pid'):
                descendants = process_group(record['current_child_pid'])
                if len([p for p in descendants if p['pid'] != record['current_child_pid'] and p['state'] != 'Z']) >= 2:
                    break
            assert child.poll() is None, 'Interrupted fixture exited before compile'
            time.sleep(.05)
        else:
            child.terminate(); child.wait(timeout=20)
            raise AssertionError('Interrupted fixture did not enter compile')
        child.send_signal(signal.SIGTERM)
        assert child.wait(timeout=20) == 143
    record = json.loads((interrupted / 'preflight_execution.json').read_text())
    assert record['status'] == 'interrupted' and record['return_code'] == 143
    assert record['exception_child']['return_code'] is not None and record['exception_child']['pid'] == record['current_child_pid']
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        remaining = process_group(record['current_child_pid'])
        if not any(p['state'] != 'Z' for p in remaining): break
        time.sleep(.05)
    assert not any(p['state'] != 'Z' for p in remaining), 'Compiler/executable descendants remain running'
    launcher.verify_hashes(interrupted, record['partial_output_sha256'])
    assert all(p.read_bytes() == content for p, content in baseline.items())
    checks.append(dict(name='signal_during_compile_records_reaped_group_and_preserves_source_inputs', passed=True,
                       process_group_before_signal=descendants, terminal_group_members=remaining))
    sources = out / 'source'; sources.mkdir()
    for p in (Path(__file__).resolve(), ROOT / 'run_loma_initial_preflight.py'):
        shutil.copyfile(str(p), str(sources / p.name))
    summary = dict(status='passed', scope='Invented two-event/two-receiver geometry only; no actual Loma forward run or inversion',
        checks=checks, commands=commands,
        output_sha256={str(p.relative_to(out)): launcher.sha(p) for p in out.rglob('*') if p.is_file()})
    (out / 'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n')
    print('Passed {} initial-preflight controls'.format(len(checks)))


if __name__ == '__main__':
    main()
