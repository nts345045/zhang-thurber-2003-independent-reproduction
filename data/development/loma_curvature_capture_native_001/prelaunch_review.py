#!/usr/bin/env python3
"""Root readback of the frozen neutral capture; never compiles or traces a ray."""
import argparse
import csv
import difflib
import hashlib
import json
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def need(ok, message):
    if not ok:
        raise ValueError(message)


def read(path):
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default=str(OUT / 'prelaunch_review.json'))
    args = parser.parse_args()
    output = Path(args.output).resolve()
    output.relative_to(ROOT)
    need(not output.exists(), 'Review output must be fresh')
    p = read(OUT / 'prepared.json')
    baseline = ROOT / p['baseline']
    b = read(baseline / 'summary.json')
    need(p['status'] == 'prepared_neutral_curvature_replay', 'Wrong preparation phase')
    need((p['path_spacing_km'], p['field_spacing_km'], p['maximum_updates'], p['threads']) ==
         (.03125, .125, 1000, 1), 'Frozen numerical settings changed')
    counts = {}
    for key, base in (('input_sha256', ROOT), ('prepared_file_sha256', OUT),
                      ('source_sha256', OUT / 'source')):
        for name, expected in p[key].items():
            need(sha(base / name) == expected, 'Changed pin: ' + name)
        counts[key] = len(p[key])
    need(sha(Path(p['compiler'])) == p['compiler_sha256'] == b['compiler_sha256'], 'Compiler changed')
    for path in (ROOT / 'diagnostics/run_curvature_capture.py', OUT / 'launcher.py'):
        need(sha(path) == p['launcher_sha256'], 'Launcher changed')
    for kind, directory in (('capture', ROOT / 'data/development/curvature_capture_controls_001'),
                            ('rational', ROOT / 'data/development/curvature_rational_controls_002')):
        summary_name = 'controls_summary.json' if kind == 'capture' else 'summary.json'
        review_name = 'controls_review.json' if kind == 'capture' else 'review.json'
        c, r = read(directory / summary_name), read(directory / review_name)
        need(c['status'] == r['status'] == 'passed', 'Controls or review not passed')
        need(sha(directory / summary_name) == p[kind + '_controls_sha256'], 'Stale controls')
        need(sha(directory / review_name) == p[kind + '_review_sha256'], 'Stale control review')
    for name, expected in b['source_sha256'].items():
        if name not in ('diagnostics/observed_optimizer.hpp', 'diagnostics/check_ray_stopping.cpp'):
            need(sha(OUT / 'source' / name) == expected, 'Numerical B source changed: ' + name)
    for name in ('observed_optimizer.hpp', 'check_ray_stopping.cpp'):
        old = (baseline / 'source/diagnostics' / name).read_text()
        new = (OUT / 'source/diagnostics' / name).read_text()
        diff = ''.join(difflib.unified_diff(old.splitlines(True), new.splitlines(True),
                      fromfile='frozen_B/' + name, tofile='neutral_capture/' + name))
        need(diff == (OUT / (name + '.diff')).read_text(), 'Recorded insertion diff differs')
    for name, expected in p['expected_old_table_sha256'].items():
        need(sha(baseline / name) == expected == b['output_sha256'][name], 'Baseline table changed')
    with (OUT / 'identified_ray.csv').open() as stream:
        need(list(csv.DictReader(stream)) == [p['native_context']] == [b['native_context']], 'Native identities changed')
    need(p['selected_iterations'] == [33, 34, 47, 48, 433, 434, 435] + list(range(988, 1000)),
         'Selected geometry inventory changed')
    result = dict(status='passed', reviewer='root', reviewed_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        prepared_sha256=sha(OUT / 'prepared.json'), launcher_sha256=p['launcher_sha256'],
        checker_sha256=sha(Path(__file__).resolve()), verified_hash_counts=counts,
        native_context_fields=len(p['native_context']), capture_controls=38, rational_controls=27,
        source_review=['Read complete header, preparation, launcher, rational helper and both exact insertion diffs.',
                       'Read-only pair capture follows the existing retention branch; resets follow the original memory clears.',
                       'Capture is disabled around the unchanged trace used for in-process numerical comparison.',
                       'No logged value enters action, gradient, line search, memory decision or stopping arithmetic.'],
        required_terminal_checks=['All five old CSVs must match the reviewed B hashes exactly.',
                                  'Both observed trace results must numerically equal unchanged B traces.',
                                  'Every capture table must retain the full native identity sidecar.',
                                  'No convergence promotion, threshold change, update-budget change or new inverse.'],
        limitations=['This permits only the frozen diagnostic replay. Native neutrality is assessed after completion.',
                     'The mathematical exact sums describe saved doubles, not continuum curvature or an optimizer correction.'])
    output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps(dict(output=str(output.relative_to(ROOT)), sha256=sha(output), counts=counts)))


if __name__ == '__main__':
    main()
