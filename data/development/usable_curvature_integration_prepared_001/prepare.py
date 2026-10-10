#!/usr/bin/env python3
"""Prepare a production-source candidate; do not edit, compile or run production."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def need(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    out = (ROOT / args.output).resolve()
    out.relative_to(ROOT)
    need(out != ROOT and not out.exists(), 'Fresh repository subdirectory required')
    native = ROOT / 'data/development/loma_usable_curvature_native_001'
    summary = json.loads((native / 'summary.json').read_text())
    review = json.loads((native / 'review.json').read_text())
    ledger = json.loads((native / 'execution.json').read_text())
    need(summary['status'] == 'completed_usable_curvature_diagnostic' and
         review['status'] == 'passed' and review['summary_sha256'] == sha(native / 'summary.json') and
         ledger['status'] == 'completed' and ledger['return_code'] == 0 and
         ledger['summary_sha256'] == sha(native / 'summary.json'), 'Reviewed terminal D required')
    need(summary['native_C_neutrality_pass'] and all(summary['baseline_table_equalities'].values()) and
         summary['observed_paths_and_arrays_match_unobserved_variant'], 'Native C/D neutrality required')
    pins = {}

    def pin(path, expected=None):
        digest = sha(path)
        need(expected is None or digest == expected, 'Changed input: ' + str(path))
        pins[str(path.relative_to(ROOT))] = digest
        return digest

    for name, digest in summary['input_sha256'].items():
        pin(ROOT / name, digest)
    for name, digest in summary['output_sha256'].items():
        pin(native / name, digest)
    for name in ('summary.json', 'review.json', 'execution.json', 'controller_completion.json'):
        pin(native / name)
    pin(Path(__file__).resolve())
    names = ['CMakeLists.txt'] + [str(p.relative_to(ROOT)) for p in sorted((ROOT / 'src').glob('*')) if p.is_file()]
    before = {name: pin(ROOT / name) for name in names}
    production = (ROOT / 'src/core.hpp').read_text()
    c_source = ROOT / summary['baseline_directory'] / 'source/src/core.hpp'
    c_text = c_source.read_text()
    accumulator = '  double T = 0;\n  for (size_t i = 1; i < p.size(); i++) {'
    need(production.count(accumulator) == 1 and production.count('      if (sy > 1e-14) {') == 1,
         'Unexpected production accumulator or retention baseline')
    need(c_text == production.replace(accumulator, accumulator.replace('double T', 'long double T'), 1)
         .replace('      if (sy > 1e-14) {', '      if (sy > 0) {', 1),
         'Current production differs from the reviewed C prerequisite')
    d_text = (native / 'source/src/core.hpp').read_text()
    include = '#include "../diagnostics/usable_ray_curvature.hpp"'
    need(d_text.count(include) == 1, 'Expected reviewed D helper include')
    candidate = d_text.replace(include, '#include "usable_ray_curvature.hpp"', 1)
    helper = (native / 'source/diagnostics/usable_ray_curvature.hpp').read_text()
    diagnostic_comment = '// Diagnostic copy only. Include after Vec, dot and inverse_ray_metric.'
    need(helper.count(diagnostic_comment) == 1, 'Expected reviewed helper declaration')
    candidate_helper = helper.replace(diagnostic_comment,
        '// Include after Vec, dot and inverse_ray_metric; checked L-BFGS arithmetic.', 1)
    out.mkdir(parents=True)
    for label in ('before', 'after'):
        for name in names:
            target = out / label / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(str(ROOT / name), str(target))
    (out / 'after/src/core.hpp').write_text(candidate)
    (out / 'after/src/usable_ray_curvature.hpp').write_text(candidate_helper)
    shutil.copyfile(str(Path(__file__).resolve()), str(out / 'prepare.py'))
    patch = ''.join(difflib.unified_diff(production.splitlines(True), candidate.splitlines(True),
        fromfile='a/src/core.hpp', tofile='b/src/core.hpp'))
    patch += ''.join(difflib.unified_diff([], candidate_helper.splitlines(True),
        fromfile='/dev/null', tofile='b/src/usable_ray_curvature.hpp'))
    (out / 'candidate.patch').write_text(patch)
    after = {str(p.relative_to(out / 'after')): sha(p) for p in sorted((out / 'after').rglob('*')) if p.is_file()}
    need({name for name in before if before[name] != after[name]} == {'src/core.hpp'} and
         set(after) - set(before) == {'src/usable_ray_curvature.hpp'}, 'Unexpected candidate source change')
    for name, digest in before.items():
        need(sha(ROOT / name) == digest, 'Production changed while preparing')
    manifest = dict(status='prepared_only_not_applied', created_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        baseline_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=str(ROOT)).decode().strip(),
        input_sha256=pins, baseline_source_sha256=before, candidate_source_sha256=after,
        native_summary_sha256=sha(native / 'summary.json'), native_review_sha256=sha(native / 'review.json'),
        native_context=summary['native_context'], candidate_patch_sha256=sha(out / 'candidate.patch'),
        prepared_file_sha256={str(p.relative_to(out)): sha(p) for p in sorted(out.rglob('*')) if p.is_file()},
        semantic_equivalence_to_reviewed_D=dict(core_except_include_path=True, helper_except_comment=True),
        changes=['Extend only the outer path-action sum to long double, returning double.',
                 'Use the reviewed shared positive-finite/representability checks for curvature and direction arithmetic.',
                 'Preserve existing cone fallback, failure exceptions, action kernels, derivatives, Armijo and stopping.'],
        untouched=['All other production source bytes and CMakeLists.txt.', 'All configurations, data, live binaries and executions.'],
        limitations=['Prepared patch only: not applied, compiled, run or adopted.',
                     'Existing D evidence exercises the identical numerical core/helper at a different include path.',
                     'The changed optimizer invalidates any claim that previous full-cohort ray outcomes are byte-equivalent.',
                     'Endpoint discretization, interface nonsmoothness and global branch completeness are separate issues.'])
    (out / 'prepared.json').write_text(json.dumps(manifest, indent=2, allow_nan=False) + '\n')
    print(json.dumps(dict(output=str(out.relative_to(ROOT)), prepared_sha256=sha(out / 'prepared.json'))))


if __name__ == '__main__':
    main()
