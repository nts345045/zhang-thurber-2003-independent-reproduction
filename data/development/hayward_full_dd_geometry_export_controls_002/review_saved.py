#!/usr/bin/env python3
"""Independent saved-output audit; imports neither exporter nor its reader."""
import csv
import datetime
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def load(name):
    return json.loads((HERE / name).read_text())


def rows(path):
    with path.open(newline='') as f:
        return list(csv.DictReader(f))


def main():
    require(not (HERE / 'review.json').exists(), 'Preserve prior review')
    prepared, summary, execution = [load(n + '.json') for n in ('prepared', 'summary', 'execution')]
    require(summary['status'] == 'passed' and summary['passed'] == summary['total'] == 82,
            'Declared controls did not pass')
    require(len(summary['checks']) == 82 and all(c['passed'] for c in summary['checks']),
            'Incomplete individual controls')
    require(execution['status'] == 'completed' and execution['return_code'] == 0 and
            execution['all_direct_children_reaped'], 'Execution not terminal/reaped')
    require(execution['summary_sha256'] == sha(HERE / 'summary.json') and
            summary['prepared_sha256'] == sha(HERE / 'prepared.json'), 'Changed terminal preparation')
    pin_counts = {}
    for key, base in [('original_sha256', ROOT), ('output_sha256', HERE), ('runtime_sha256', Path('/')),
                      ('artifact_sha256', HERE)]:
        pins = summary[key] if key == 'artifact_sha256' else prepared[key]
        for name, digest in pins.items():
            require(sha(base / name) == digest, 'Changed pin: ' + name)
        pin_counts[key] = len(pins)
    for command in execution['commands']:
        require(command['reaped'] and command['return_code'] == command['expected_return_code'],
                'Unexpected child outcome')
        for stream in ('stdout', 'stderr'):
            require(sha(HERE / 'logs' / (command['label'] + '.' + stream + '.log')) ==
                    command[stream + '_sha256'], 'Changed closed child log')
    actual = HERE / 'results/actual_after'
    prefix = 'dd_full_linearization_'
    original = ('matrix', 'rows', 'suppressed', 'columns', 'smoothing_matrix', 'smoothing_rows', 'rays', 'info')
    for suffix in original:
        name = prefix + suffix + '.csv'
        require((actual / name).read_bytes() == (HERE / 'results/actual_before' / name).read_bytes(),
                'Original export parity failed: ' + suffix)
    events, stations, observations = [rows(actual / n) for n in
                                     ('dd_events.csv', 'stations.csv', 'observations.csv')]
    geometry, paths = [rows(actual / (prefix + n + '.csv')) for n in ('ray_geometry', 'ray_paths')]
    require([(int(r['event']), int(r['station'])) for r in geometry] == [(0, 0), (1, 0), (1, 1)],
            'Actual used-pair support changed')
    joined_metadata = 0
    for ray in geometry:
        i, k = int(ray['event']), int(ray['station'])
        nodes = [p for p in paths if (int(p['event']), int(p['station'])) == (i, k)]
        require(len(nodes) == int(ray['ray_path_points']) and
                [int(p['node']) for p in nodes] == list(range(len(nodes))), 'Incomplete ordered path')
        require(tuple(float(nodes[0][a]) for a in 'xyz') == tuple(float(events[i][a]) for a in 'xyz') and
                tuple(float(nodes[-1][a]) for a in 'xyz') == tuple(float(stations[k][a]) for a in 'xyz'),
                'Saved path/native endpoints differ')
        for item in [ray] + nodes:
            for pre, native in [('source_', events[i]), ('receiver_', stations[k])]:
                for key, value in native.items():
                    if key not in ('id', 'x', 'y', 'z', 't'):
                        require(item[pre + key] == value, 'Native metadata changed')
                        joined_metadata += 1
        for key in ('ray_finite', 'ray_converged', 'ray_path_in_domain', 'ray_exact_source_endpoint',
                    'ray_exact_receiver_endpoint', 'ray_derivatives_evaluated',
                    'ray_initialization_attempted', 'ray_initialization_succeeded'):
            require(ray[key] == '1', 'Actual fixture flag failed')
    lookup = {c['name']: c for c in summary['checks']}
    require(len(lookup) == 82, 'Duplicate control name')
    coordinated = [c for name, c in lookup.items() if name.startswith('malformed_coordinated_')]
    require(len(coordinated) == 11 and all(c['detail']['rejection'] for c in coordinated),
            'Missing coordinated observation/native rejection')
    for suffix in ('geometry', 'paths'):
        c = lookup['array_io_' + suffix]['detail']
        require(c['threw'] == '1' and 'Cannot finish writing ' in c['error'],
                'Real output failure not retained')
    for case in ('short_dv', 'short_length'):
        ray = rows(HERE / ('results/array_' + case) / (prefix + 'ray_geometry.csv'))[0]
        require(ray['ray_derivatives_evaluated'] == '0' and all(ray['source_d' + a] == '' for a in 'xyz'),
                'Missing derivative represented as a computed value')
    require(rows(HERE / 'results/array_local' / (prefix + 'ray_geometry.csv'))[0]['ray_converged'] == '0',
            'Supplied local failure promoted')
    result = dict(status='passed', reviewer='root', reviewed_utc=datetime.datetime.utcnow().isoformat() + 'Z',
                  control_records=82, child_commands=len(execution['commands']), pin_counts=pin_counts,
                  original_files_byte_identical=8, actual_used_pairs=3, actual_path_nodes=len(paths),
                  native_metadata_cells_joined=joined_metadata, coordinated_identity_rejections=11,
                  reader_imported=False, exporter_or_ray_code_imported=False,
                  input_sha256={n: sha(HERE / n) for n in
                                ('prepared.json', 'prelaunch_review.json', 'summary.json', 'execution.json')},
                  checker_sha256=sha(Path(__file__)),
                  limits='Saved invented outputs only. No new field export, covariance, ray accuracy, or scientific success claim.')
    with (HERE / 'review.json').open('x') as f:
        json.dump(result, f, indent=2, sort_keys=True, allow_nan=False)
        f.write('\n')
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
