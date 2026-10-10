#!/usr/bin/env python3
"""Invented two-ray readiness controls; no solver or real data."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BUILD = ROOT / 'tmp/hayward_1d_linearization_mode_checks'
HELPER = ROOT / 'diagnostics/compare_hayward_1d_support.py'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    BUILD.mkdir()
    checks = []
    for case in ('valid_running_preflight', 'failed_command', 'wrong_command', 'changed_input', 'default_completed_preflight'):
        folder, output = BUILD / case, BUILD / (case + '_output')
        shutil.copytree(str(HERE / 'fixture'), str(folder))
        (folder / 'run.cfg').write_text('# Invented fixture, no executable\n')
        manifest = dict(binary='tmp/invented_unused_binary', threads=4,
                        sha256={str(p.relative_to(ROOT)): sha(p) for p in folder.glob('*.csv')
                                if 'linearization' not in p.name})
        manifest['sha256'][str((folder / 'run.cfg').relative_to(ROOT))] = sha(folder / 'run.cfg')
        (folder / 'run_manifest.json').write_text(json.dumps(manifest))
        command = [manifest['binary'], 'linearize', str((folder / 'run.cfg').relative_to(ROOT)),
                   str(folder.relative_to(ROOT)), 'initial']
        ledger = dict(phase='preflight', status='running', threads=4,
                      current_stage='initial_raycheck', completed_commands=[dict(
                          stage='initial_linearize', return_code=0, command=command)])
        if case == 'failed_command':
            ledger['completed_commands'][0]['return_code'] = 1
        if case == 'wrong_command':
            ledger['completed_commands'][0]['command'][-1] = 'dd'
        if case == 'changed_input':
            with (folder / 'observations.csv').open('a') as stream:
                stream.write('\n')
        (folder / 'preflight_execution.json').write_text(json.dumps(ledger))
        args = ['python3', str(HELPER.relative_to(ROOT)), '--data', str(folder.relative_to(ROOT)),
                '--output', str(output.relative_to(ROOT))]
        if case == 'default_completed_preflight':
            (folder / 'preflight.json').write_text(json.dumps(dict(status='invented_completed_fixture',
                sha256={p.name: sha(p) for p in folder.glob('initial_*.csv')})))
        else:
            args.append('--completed-linearization-only')
        result = subprocess.run(args, cwd=str(ROOT), env=dict(os.environ,
            PYTHONDONTWRITEBYTECODE='1', OPENBLAS_NUM_THREADS='1'), stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, universal_newlines=True)
        success = case in ('valid_running_preflight', 'default_completed_preflight')
        passed = (result.returncode == 0) == success
        if success:
            summary = json.loads((output / 'summary.json').read_text())
            passed = passed and summary['rays'] == 2 and summary['reference_counts']['reference_valid'] == 2
            if case == 'valid_running_preflight':
                saved = json.loads((output / 'inputs/preflight_execution_at_capture.json').read_text())
                passed = passed and saved == ledger and summary['preflight_status'] is None
                passed = passed and not summary['overall_preflight_assessed']
                passed = passed and not (output / 'inputs/preflight.json').exists()
                # A later controller update cannot alter the captured readiness record.
                ledger['status'] = 'later_changed'; (folder / 'preflight_execution.json').write_text(json.dumps(ledger))
                passed = passed and json.loads((output / 'inputs/preflight_execution_at_capture.json').read_text())['status'] == 'running'
        else:
            expected = 'Frozen run manifest mismatch' if case == 'changed_input' else 'No matching successful completed'
            passed = passed and expected in result.stderr and not output.exists()
        checks.append(dict(name=case, passed=bool(passed), command=args,
                           return_code=result.returncode, stdout=result.stdout,
                           stderr=result.stderr.replace(str(ROOT) + '/', '')))
    report = dict(scope='Invented readiness and immutable-ledger controls only',
                  command='PYTHONDONTWRITEBYTECODE=1 python3 data/development/hayward_1d_linearization_mode_checks/check.py',
                  source_sha256={str(p.relative_to(ROOT)): sha(p) for p in
                                 [Path(__file__).resolve(), HELPER] + list((HERE / 'fixture').glob('*.csv'))},
                  checks=checks, passed=all(r['passed'] for r in checks))
    (HERE / 'results.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(passed=report['passed'], checks=[(r['name'], r['passed']) for r in checks])))
    raise SystemExit(0 if report['passed'] else 1)


if __name__ == '__main__':
    main()
