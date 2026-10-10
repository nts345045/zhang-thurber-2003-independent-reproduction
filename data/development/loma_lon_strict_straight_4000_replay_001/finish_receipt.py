#!/usr/bin/env python3
"""Attach the observed tool return and verify saved child/process-group state."""
import datetime
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


execution = json.loads((HERE / 'execution.json').read_text())
summary = json.loads((HERE / 'summary.json').read_text())
if execution['status'] != 'completed' or execution['return_code'] != 0:
    raise RuntimeError('Wrapper is not terminal successful')
if execution['native_calls_completed'] != 2 or execution['native_calls_planned'] != 2:
    raise RuntimeError('Unexpected call inventory')
if execution['summary_sha256'] != sha(HERE / 'summary.json'):
    raise RuntimeError('Terminal summary changed')
for name, value in summary['output_sha256'].items():
    if sha(HERE / name) != value:
        raise RuntimeError('Terminal artifact changed: ' + name)
groups = {c['pid']: [] for c in execution['commands']}
for entry in Path('/proc').iterdir():
    if not entry.name.isdigit():
        continue
    try:
        fields = (entry / 'stat').read_text().rsplit(')', 1)[1].split()
        group = int(fields[2])
        if group in groups and fields[0] != 'Z':
            groups[group].append(int(entry.name))
    except (FileNotFoundError, ProcessLookupError):
        continue
if any(groups.values()) or any(c['return_code'] != 0 for c in execution['commands']):
    raise RuntimeError('Unsettled child lifecycle')
names = ['summary.json', 'execution.json', 'RESULTS.md', 'finish_receipt.py',
         'prepared.json', 'prelaunch_review.json', 'run.py']
receipt = {
    'status': 'completed',
    'recorded_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'driver_completion_basis': 'exec_command session 73044, final write_stdin chunk 26d658 returned exit_code 0 and the summary hash; direct tool handle completed',
    'driver_return_code': 0,
    'exec_session_id': 73044,
    'driver_pid': None,
    'driver_pid_basis': 'The exec handle did not expose its shell/driver PID; none is invented',
    'driver_combined_output': sha(HERE / 'summary.json') + '\n',
    'native_calls': 2,
    'field_constructions': 0,
    'recorded_child_return_codes': {c['stage']: c['return_code'] for c in execution['commands']},
    'terminal_non_zombie_process_group_members': groups,
    'input_output_sha256': {name: sha(HERE / name) for name in names},
    'scope': 'Lifecycle and documentation attachment only; no new trace, action or reference calculation',
}
with (HERE / 'controller_completion.json').open('x') as f:
    json.dump(receipt, f, indent=2, allow_nan=False)
    f.write('\n')
print(sha(HERE / 'controller_completion.json'))
