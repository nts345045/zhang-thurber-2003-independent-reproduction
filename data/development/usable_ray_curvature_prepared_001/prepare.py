#!/usr/bin/env python3
"""Prepare, but never execute, a diagnostic C/D curvature comparison."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import shutil
import time

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('Expected exactly one frozen source fragment: ' + old[:60])
    return text.replace(old, new, 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = (ROOT / args.output).resolve()
    output.relative_to(ROOT)
    if output.exists():
        raise ValueError('Fresh output required')
    baseline = ROOT / 'data/development/loma_positive_curvature_native_001'
    summary_path, review_path = baseline / 'summary.json', baseline / 'review.json'
    summary, review = json.loads(summary_path.read_text()), json.loads(review_path.read_text())
    if review['status'] != 'passed' or review['summary_sha256'] != sha(summary_path):
        raise ValueError('Reviewed terminal C source is required')
    source_pins = {name: value for name, value in summary['output_sha256'].items()
                   if name.startswith('source/')}
    if len(source_pins) != 20:
        raise ValueError('Unexpected frozen C source inventory')
    for name, value in source_pins.items():
        if sha(baseline / name) != value:
            raise ValueError('Stale C source: ' + name)
    output.mkdir(parents=True)
    for name in ('C', 'D'):
        shutil.copytree(str(baseline / 'source'), str(output / name))
    helper = ROOT / 'diagnostics/usable_ray_curvature.hpp'
    shutil.copyfile(str(helper), str(output / 'D/diagnostics/usable_ray_curvature.hpp'))
    core = (output / 'C/src/core.hpp').read_text()
    start = core.index('    Vec q = grad, alpha(S.size());')
    end = core.index('    Vec feasible_direction = q;', start)
    original_loop = core[start:end]
    replacement = ('    Vec q;\n'
                   '    const bool usable_memory = usable_lbfgs_ray_direction(\n'
                   '        [&] { return ray_metric_weights(g, p); }, grad, S, Y, rho, q);\n')
    for name in ('src/core.hpp', 'diagnostics/observed_optimizer.hpp'):
        original = (output / 'C' / name).read_text()
        text = once(original, original_loop, replacement)
        text = once(text, '    if (feasible_direction != q || !(dot(grad, q) < 0)) {',
                    '    if (!usable_memory || feasible_direction != q || !(dot(grad, q) < 0)) {')
        text = once(text, '      if (sy > 0) {',
                    '      double reciprocal = 0;\n'
                    '      if (usable_ray_curvature(s, y, sy, reciprocal)) {')
        text = once(text, '        rho.push_back(1 / sy);',
                    '        rho.push_back(reciprocal);')
        if name == 'src/core.hpp':
            text = once(text, '// Independently implemented limited-memory BFGS',
                        '#include "../diagnostics/usable_ray_curvature.hpp"\n\n'
                        '// Independently implemented limited-memory BFGS')
        (output / 'D' / name).write_text(text)
        (output / (Path(name).name + '.diff')).write_text(''.join(difflib.unified_diff(
            original.splitlines(True), text.splitlines(True), fromfile='C/' + name,
            tofile='D/' + name)))
    shutil.copyfile(str(Path(__file__).resolve()), str(output / 'prepare.py'))
    manifest = dict(status='prepared_invented_controls_only', created_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                    baseline_summary_sha256=sha(summary_path), baseline_review_sha256=sha(review_path),
                    baseline_source_sha256=source_pins, helper_sha256=sha(helper),
                    preparer_sha256=sha(Path(__file__).resolve()),
                    source_sha256={str(p.relative_to(output)): sha(p)
                                   for p in sorted(output.rglob('*')) if p.is_file()},
                    changes=['Positive finite computed curvature and usable reciprocal admission.',
                             'Representable current metric and existing two-loop arithmetic, with no magnitude threshold.',
                             'Unusable memory uses the existing cone fallback and memory reset; unusable fallback still throws.',
                             'C action, gradient, line search, stopping and budgets are unchanged.'],
                    limitations=['Computed curvature is not an exact-sign or information certificate.',
                                 'No native replay, production edit, or live binary/input change.'])
    (output / 'prepared.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(dict(output=str(output.relative_to(ROOT)), files=len(manifest['source_sha256']),
                          prepared_sha256=sha(output / 'prepared.json'))))


if __name__ == '__main__':
    main()
