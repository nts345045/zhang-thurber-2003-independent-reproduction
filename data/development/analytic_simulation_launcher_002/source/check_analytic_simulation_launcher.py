#!/usr/bin/env python3
"""Exercise the frozen simulation launcher with invented constant-speed geometry."""
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
import run_loma_analytic_simulation as launcher


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--build', required=True)
    args = parser.parse_args()
    out = launcher.inside(ROOT, ROOT / args.output)
    out.mkdir(parents=True)
    data = out / 'invented_simulation'; data.mkdir()
    fixture = ROOT / 'data/development/analytic_truth_preparation_checks_001/invented_reference'
    bundle = data / 'analytic_truth'
    shutil.copytree(str(fixture / 'inputs'), str(bundle / 'inputs'))
    import gzip
    with gzip.open(str(fixture / 'references.csv.gz'), 'rb') as source, (bundle / 'references.csv').open('wb') as target:
        shutil.copyfileobj(source, target)
    (bundle / 'provenance').mkdir()
    for name in ('summary.json', 'execution.json', 'review.json', 'independent_review.json', 'certificates.jsonl.gz'):
        shutil.copyfile(str(fixture / name), str(bundle / 'provenance' / name))
    for name in ('truth_events.csv', 'stations.csv', 'truth_grid.csv'):
        shutil.copyfile(str(fixture / 'inputs' / name), str(data / name))
    shutil.copyfile(str(data / 'truth_grid.csv'), str(data / 'initial_grid.csv'))
    (data / 'run.cfg').write_text('authoritative_geometry 1\nseed 2003\nlocation_noise 0.1\nnoise 0.04\nstation_noise 0.3\ntime_quantum 0.01\npair_distance 20\n')
    (data / 'authoritative_geometry').write_text('Invented identified numerical fixture; no real events or stations.\n')
    counts = dict(events=2, receivers=2, unique_rays=4, strict_below_20km_pairs=1,
                  absolute_rows=4, catalog_rows=2, precise_rows=2, total_rows=8)
    (data / 'preparation_manifest.json').write_text(json.dumps(dict(counts=counts, scope='Invented numerical fixture')) + '\n')
    manifest = dict(status='prepared', truth_mode='continuous_layered_reference', source_count=2,
                    receiver_count=2, pairs=4, scope='Invented numerical fixture; no real truth export',
                    prepared_sha256={str(p.relative_to(data)): launcher.sha(p) for p in data.rglob('*') if p.is_file()})
    path = data / 'analytic_truth_manifest.json'
    path.write_text(json.dumps(manifest, indent=2) + '\n')
    baseline = {p: p.read_bytes() for p in data.rglob('*') if p.is_file()}
    checks = []

    def check(name, mutate, reject=True):
        for p, content in baseline.items():
            p.write_bytes(content)
        mutate()
        try:
            launcher.verify_prepared(data)
        except ValueError as error:
            if not reject:
                raise
            checks.append(dict(name=name, passed=True, rejected=True, message=str(error)))
        else:
            if reject:
                raise AssertionError('Accepted invalid fixture: ' + name)
            checks.append(dict(name=name, passed=True, rejected=False))

    def changed_manifest(change):
        record = copy.deepcopy(manifest); change(record)
        path.write_text(json.dumps(record, indent=2) + '\n')

    check('complete_pinned_fixture', lambda: None, False)
    check('changed_run_configuration', lambda: (data / 'run.cfg').write_text('seed 1\n'))
    check('changed_native_station_metadata', lambda: (data / 'stations.csv').write_text('changed\n'))
    check('changed_reference_table', lambda: (bundle / 'references.csv').write_text('changed\n'))
    check('unprepared_status', lambda: changed_manifest(lambda r: r.update(status='failed')))
    check('wrong_truth_mode', lambda: changed_manifest(lambda r: r.update(truth_mode='polygon')))
    check('missing_review_pin', lambda: changed_manifest(lambda r: r['prepared_sha256'].pop('analytic_truth/provenance/independent_review.json')))
    check('wrong_cartesian_count', lambda: changed_manifest(lambda r: r.update(pairs=3)))
    check('escaped_prepared_path', lambda: changed_manifest(lambda r: r['prepared_sha256'].update({'../outside': 'invalid'})))
    for p, content in baseline.items():
        p.write_bytes(content)
    before = out / 'prepared_before_launch'; before.mkdir()
    for p, content in baseline.items():
        target = before / p.relative_to(data); target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(content)
    command = [sys.executable, str(ROOT / 'run_loma_analytic_simulation.py'), '--data', str(data.relative_to(ROOT)), '--build', args.build, '--threads', '2']
    with (out / 'launcher_stdout.log').open('w') as stdout, (out / 'launcher_stderr.log').open('w') as stderr:
        subprocess.check_call(command, cwd=str(ROOT), stdout=stdout, stderr=stderr,
                              env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1', TMPDIR=str(ROOT / 'tmp')))
    execution = json.loads((data / 'simulation_execution.json').read_text())
    assert execution['status'] == 'completed' and execution['return_code'] == 0
    launcher.verify_hashes(data, execution['output_sha256'])
    with (data / 'observations.csv').open() as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 8 and [sum(r['type'] == str(t) for r in rows) for t in range(3)] == [4, 2, 2]
    checks.append(dict(name='real_frozen_build_and_cli_writes_eight_identified_synthetic_rows', passed=True))
    for name in launcher.MUTABLE_INPUTS:
        assert (data / 'inputs_before_simulation' / name).read_bytes() == baseline[data / name]
    checks.append(dict(name='original_mutable_inputs_preserved_exactly', passed=True))
    try:
        launcher.verify_prepared(data)
    except ValueError:
        checks.append(dict(name='completed_simulation_cannot_be_reused', passed=True, rejected=True))
    else:
        raise AssertionError('Completed simulation was accepted as fresh')
    interrupted = out / 'interrupted_simulation'
    shutil.copytree(str(before), str(interrupted))
    interrupt_command = [sys.executable, str(ROOT / 'run_loma_analytic_simulation.py'),
                         '--data', str(interrupted.relative_to(ROOT)), '--build', args.build + '_interrupt', '--threads', '2']
    with (out / 'interruption_stdout.log').open('w') as stdout, (out / 'interruption_stderr.log').open('w') as stderr:
        child = subprocess.Popen(interrupt_command, cwd=str(ROOT), stdout=stdout, stderr=stderr,
                                 env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1', TMPDIR=str(ROOT / 'tmp')))
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            ledger_path = interrupted / 'simulation_execution.json'
            record = json.loads(ledger_path.read_text()) if ledger_path.exists() else {}
            if record.get('current_stage') == 'simulation_compile' and record.get('current_child_pid'):
                break
            if child.poll() is not None:
                raise AssertionError('Interruption fixture exited before compile')
            time.sleep(.05)
        else:
            child.terminate(); child.wait(timeout=20)
            raise AssertionError('Interruption fixture never entered compile')
        child.send_signal(signal.SIGTERM)
        assert child.wait(timeout=20) == 143
    record = json.loads((interrupted / 'simulation_execution.json').read_text())
    assert record['status'] == 'interrupted' and record['return_code'] == 143
    assert record['exception_child']['pid'] == record['current_child_pid']
    assert record['exception_child']['return_code'] is not None
    assert not any((interrupted / name).exists() for name in launcher.NEW_OUTPUTS)
    checks.append(dict(name='driver_signal_records_interruption_and_reaped_child', passed=True))
    for name in baseline:
        assert (interrupted / name.relative_to(data)).read_bytes() == baseline[name]
    checks.append(dict(name='interrupted_build_preserves_all_prepared_input_bytes', passed=True))
    snapshot = out / 'source'; snapshot.mkdir()
    for source in (Path(__file__).resolve(), ROOT / 'run_loma_analytic_simulation.py'):
        shutil.copyfile(str(source), str(snapshot / source.name))
    summary = dict(status='passed', checks=checks, scope='Invented constant-speed fixture only; no actual Loma simulation',
                   command=command, fixture_source=str(fixture.relative_to(ROOT)),
                   output_sha256={str(p.relative_to(out)): launcher.sha(p) for p in out.rglob('*') if p.is_file()})
    (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print('Passed {} launcher checks including frozen build and full invented simulation'.format(len(checks)))


if __name__ == '__main__':
    main()
