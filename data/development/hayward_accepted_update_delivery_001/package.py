#!/usr/bin/env python3
"""Archive only the verified, closed dependency closure of the saved-state plot."""
import gzip
import hashlib
import json
from pathlib import Path, PurePosixPath
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PLOT = ROOT / 'tmp/hayward_accepted_update_001_figures'
OBS = ROOT / 'tmp/hayward_iteration1_trial0_observation_001'
PRIOR = ROOT / 'tmp/hayward_trial3_observation_001'
PLOT_RECEIPT = '46873b0adb1c2406ff69ccaea1a22e91c97b16e056c6807be105544a939f1cc8'
PLOT_SUMMARY = 'ffb29ff66bfb2fe3b51dd0fc0a3ef4a60f9c0806d02325fe996d479653c720b3'
PLOT_SOURCE = '97434ceddb4f14c9137964d0c510322b809981074fe459ad36fa144939946d79'


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1048576), b''):
            h.update(chunk)
    return h.hexdigest()


def relative(path):
    return str(path.relative_to(ROOT))


def regular(name):
    rel = PurePosixPath(name)
    require(not rel.is_absolute() and name == str(rel) and rel.parts and
            all(p not in ('', '.', '..') for p in rel.parts), 'Unsafe path: ' + name)
    path = ROOT.joinpath(*rel.parts)
    require(path.resolve() == path and path.is_file() and not path.is_symlink(), 'Nonregular/aliased input: ' + name)
    return path


def load(path):
    return json.loads(path.read_text())


def save(path, value):
    with path.open('x') as f:
        json.dump(value, f, indent=2, sort_keys=True)
        f.write('\n')


def consumed_inputs(summary):
    """Reconstruct the actual pin() calls of the unchanged plotting script.

    Historical receipts also mention evidence not consumed by this plot. Their
    other hash maps are provenance, not a reason to sweep unrelated/live files.
    """
    pins = {}

    def add(path, expected):
        name = relative(path)
        require(name not in pins or pins[name] == expected, 'Conflicting input pin: ' + name)
        require(sha(regular(name)) == expected, 'Input hash mismatch: ' + name)
        pins[name] = expected

    add(OBS / 'receipt.json', '8da05d5120abc9e79e66a4d9409da2aa9e87eda0b55d2cfb920652ada81aae63')
    add(OBS / 'execution_receipt.json', 'bc1d6f7eea72b124bf121ba1f95d452ed604c0809da68b36c494e53846cfbbbb')
    r, e = load(OBS / 'receipt.json'), load(OBS / 'execution_receipt.json')
    require(r['status'] == 'passed_closed_iteration1_trial0_observation', 'Observation did not pass')
    require(e['status'] == 'passed' and e['return_code'] == 0 and e['child_reaped'] is True, 'Observation not reaped')
    require(e['receipt_sha256'] == sha(OBS / 'receipt.json') and e['checker_sha256'] == r['checker_sha256'], 'Observation chain mismatch')
    require(e['output_sha256'] == r['output_sha256'], 'Observation output maps differ')
    add(OBS / 'check_saved.py', r['checker_sha256'])
    for name, expected in r['input_sha256'].items():
        add(ROOT / name, expected)
    for name, expected in r['output_sha256'].items():
        add(OBS / name, expected)
    prior = load(PRIOR / 'receipt.json')
    require(prior['status'] == 'passed_closed_trial_three_saved_readback', 'Prior accepted-step readback did not pass')
    accepted = prior['accepted_trial']
    require((accepted['iteration'], accepted['trial'], accepted['status'], accepted['step_fraction']) ==
            ('0', '3', 'accepted', '0.125'), 'Wrong accepted update')
    add(PRIOR / 'check_saved.py', prior['source_sha256'])
    prior_execution_path = PRIOR / 'execution_receipt.json'
    add(prior_execution_path, summary['input_sha256'][relative(prior_execution_path)])
    pe = load(prior_execution_path)
    require(pe['status'] == 'completed_and_reaped' and pe['return_code'] == 0 and pe['checker_reaped'] is True, 'Prior checker not reaped')
    require(pe['file_sha256']['receipt.json'] == sha(PRIOR / 'receipt.json'), 'Prior receipt mismatch')
    for name, expected in pe['file_sha256'].items():
        add(PRIOR / name, expected)
    for name, expected in prior['output_sha256'].items():
        add(PRIOR / name, expected)
    require(len(pins) == 39 and pins == summary['input_sha256'], 'Actual plotting-input closure differs')
    return pins


def write_archive(raw, members):
    with gzip.GzipFile(filename='', fileobj=raw, mode='wb', mtime=0, compresslevel=9) as zipped:
        with tarfile.open(fileobj=zipped, mode='w', format=tarfile.PAX_FORMAT) as archive:
            for name, item in sorted(members.items()):
                info = tarfile.TarInfo(name)
                info.size, info.mode, info.mtime = item['bytes'], item['mode'], 0
                info.uid = info.gid = 0
                info.uname = info.gname = ''
                with regular(name).open('rb') as source:
                    archive.addfile(info, source)


class HashSink:
    def __init__(self):
        self.h = hashlib.sha256()

    def write(self, data):
        self.h.update(data)
        return len(data)

    def flush(self):
        pass


def main():
    require(all(not (HERE / n).exists() for n in ('evidence.tar.gz', 'members.json', 'packaging.json')), 'Use a fresh delivery directory')
    for ext in ('pdf', 'png'):
        for suffix in ('', '.identifiers.json'):
            target = ROOT / ('figures/hayward_accepted_update_001.' + ext + suffix)
            require(not target.exists() and not target.is_symlink(), 'Refusing to replace ' + relative(target))
    require(sha(PLOT / 'execution_receipt.json') == PLOT_RECEIPT, 'Plot execution receipt changed')
    require(sha(PLOT / 'summary.json') == PLOT_SUMMARY and sha(PLOT / 'plot_accepted_update.py') == PLOT_SOURCE, 'Plot summary/source changed')
    summary, execution = load(PLOT / 'summary.json'), load(PLOT / 'execution_receipt.json')
    require(summary['status'] == 'completed_saved_update_visualization', 'Plot did not finish')
    require(execution['status'] == 'completed_and_reaped' and execution['return_code'] == 0 and
            execution['child_reaped'] is True and execution['plot_process_absent'] is True, 'Plot process not closed')
    require(execution['summary_sha256'] == PLOT_SUMMARY and execution['input_sha256'] == summary['input_sha256'], 'Plot execution chain differs')
    require(len(execution['artifact_sha256']) == 14 and len(summary['output_sha256']) == 9, 'Wrong plot roster')
    require(execution['artifact_sha256']['plot_accepted_update.py'] == summary['plot_source_sha256'] == PLOT_SOURCE, 'Plot source pin mismatch')
    require(execution['artifact_sha256']['README.md'] == summary['readme_sha256'], 'Plot README pin mismatch')
    pins = consumed_inputs(summary)
    roles = {name: 'consumed_plot_input' for name in pins}
    for name, expected in execution['artifact_sha256'].items():
        key = relative(PLOT / name)
        require(sha(regular(key)) == expected, 'Plot artifact changed: ' + name)
        if name in summary['output_sha256']:
            require(summary['output_sha256'][name] == expected, 'Output hash mismatch: ' + name)
        require(key not in pins, 'Unexpected overlapping artifact')
        pins[key], roles[key] = expected, 'closed_plot_artifact'
    pins[relative(PLOT / 'execution_receipt.json')] = PLOT_RECEIPT
    roles[relative(PLOT / 'execution_receipt.json')] = 'closed_plot_execution_receipt'
    require(len(pins) == 54, 'Wrong closed archive member count')
    members = {}
    for name, expected in sorted(pins.items()):
        path = regular(name)
        require(not any(p in ('cache', '__pycache__', 'sessions', 'shell_snapshots') for p in Path(name).parts), 'Generated state excluded')
        require(sha(path) == expected, 'Member changed: ' + name)
        members[name] = {'type': 'file', 'mode': path.stat().st_mode & 0o777,
                         'bytes': path.stat().st_size, 'sha256': expected, 'role': roles[name]}
    save(HERE / 'members.json', {'scope': 'Exact saved plotting closure, not a runnable inverse-solver archive.',
                               'consumed_input_count': 39, 'plot_artifact_count': 14,
                               'plot_receipt_count': 1, 'members': members})
    archive_path = HERE / 'evidence.tar.gz'
    with archive_path.open('xb') as raw:
        write_archive(raw, members)
    with tarfile.open(str(archive_path), 'r:gz') as archive:
        records = archive.getmembers()
        require(len(records) == 54 and {m.name for m in records} == set(members), 'Archive roster changed')
        for member in records:
            item = members[member.name]
            require(member.isfile() and member.size == item['bytes'] and member.mode == item['mode'] and
                    member.mtime == member.uid == member.gid == 0 and member.uname == member.gname == '', 'Archive metadata changed')
            require(hashlib.sha256(archive.extractfile(member).read()).hexdigest() == item['sha256'] == sha(regular(member.name)), 'Archive bytes changed')
    with gzip.open(str(archive_path), 'rb') as f:
        while f.read(1048576):
            pass
    duplicate = HashSink()
    write_archive(duplicate, members)
    archive_hash = sha(archive_path)
    require(duplicate.h.hexdigest() == archive_hash, 'Archive not deterministic on reconstruction')
    figure_pins = {}
    for ext in ('pdf', 'png'):
        source = PLOT / ('accepted_update_1.' + ext)
        target = ROOT / ('figures/hayward_accepted_update_001.' + ext)
        with target.open('xb') as out:
            out.write(source.read_bytes())
        require(sha(target) == sha(source), 'Figure copy differs')
        figure_pins[relative(target)] = sha(target)
        sidecar = target.with_name(target.name + '.identifiers.json')
        original_sidecar = source.with_name(source.name + '.identifiers.json')
        mapping = PLOT / 'native_identifiers.json.gz'
        save(sidecar, {'title': summary['title'], 'figure': relative(target), 'figure_sha256': sha(target),
                       'archive': relative(archive_path), 'archive_sha256': archive_hash,
                       'members_manifest': relative(HERE / 'members.json'), 'members_manifest_sha256': sha(HERE / 'members.json'),
                       'original_figure_member': relative(source),
                       'full_figure_identifiers_member': relative(original_sidecar), 'full_figure_identifiers_sha256': sha(original_sidecar),
                       'full_native_mapping_member': relative(mapping), 'full_native_mapping_sha256': sha(mapping),
                       'plot_summary_member': relative(PLOT / 'summary.json'), 'plot_summary_sha256': PLOT_SUMMARY,
                       'scope': 'Accepted update 1; run incomplete. No postupdate RMS, final convergence or manuscript-panel claim.'})
        figure_pins[relative(sidecar)] = sha(sidecar)
    result = {'status': 'verified_lossless', 'archive': archive_path.name, 'archive_sha256': archive_hash,
              'archive_bytes': archive_path.stat().st_size, 'members_sha256': sha(HERE / 'members.json'),
              'member_count': len(members), 'regular_file_bytes': sum(m['bytes'] for m in members.values()),
              'symbolic_links': 0, 'deterministic_reconstruction_sha256': duplicate.h.hexdigest(),
              'plot_summary_sha256': PLOT_SUMMARY, 'plot_execution_receipt_sha256': PLOT_RECEIPT,
              'input_sha256': summary['input_sha256'], 'figure_sha256': figure_pins,
              'source_sha256': {name: sha(HERE / name) for name in ('package.py', 'restore.py', 'README.md')},
              'runtime_policy': 'No binaries or environment copied; the recorded Python/Matplotlib/NumPy plotting environment is an external prerequisite.',
              'original_file_writes': 0, 'solver_calls': 0, 'integration_calls': 0,
              'scope': 'Closed saved evidence only; reports and top-level README unchanged. Historical checkers are retained as provenance, not rerun.'}
    save(HERE / 'packaging.json', result)
    print(json.dumps({'status': result['status'], 'members': len(members), 'archive_sha256': archive_hash,
                      'archive_bytes': result['archive_bytes'], 'packaging_sha256': sha(HERE / 'packaging.json')}))


if __name__ == '__main__':
    main()
