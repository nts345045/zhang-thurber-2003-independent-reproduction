#!/usr/bin/env python3
"""Freeze prospective seed-load/control variants; do not compile or trace."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import shutil
import time

ROOT = Path(__file__).resolve().parents[1]


def need(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def one(text, old, new):
    need(text.count(old) == 1, 'Changed unique source insertion: ' + old[:80])
    return text.replace(old, new, 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    out = (ROOT / args.output).resolve()
    out.relative_to(ROOT)
    need(out != ROOT and not out.exists(), 'Fresh output required')
    baseline = ROOT / 'data/development/loma_outer_accumulation_native_001'
    summary, review = [json.loads((baseline/name).read_text()) for name in ('summary.json','review.json')]
    need(summary['status'] == 'completed_single_change_diagnostic' and review['status'] == 'passed' and
         review['summary_sha256'] == sha(baseline/'summary.json'), 'Require reviewed frozen B')
    pins = {}
    for name in ('summary.json','review.json','prepared.json','execution.json','identified_ray.csv'):
        pins[str((baseline/name).relative_to(ROOT))] = sha(baseline/name)
    for name, digest in summary['source_sha256'].items():
        path = baseline/'source'/name
        need(sha(path) == digest, 'Changed frozen B source: ' + name)
        pins[str(path.relative_to(ROOT))] = digest
    for name in ('saved_candidate.hpp','prepare_seeded_retention.py'):
        pins['diagnostics/'+name] = sha(ROOT/'diagnostics'/name)
    pins['data/development/seeded_retention_plan_001/README.md'] = sha(ROOT/'data/development/seeded_retention_plan_001/README.md')
    out.mkdir(parents=True)
    variants = {}
    for variant in ('seed_loaded_B','positive_curvature'):
        source = out/'source'/variant
        shutil.copytree(str(baseline/'source'), str(source))
        shutil.copyfile(str(ROOT/'diagnostics/saved_candidate.hpp'), str(source/'diagnostics/saved_candidate.hpp'))
        driver = (source/'diagnostics/check_ray_stopping.cpp').read_text()
        original_driver = driver
        driver = one(driver, '#include "observed_optimizer.hpp"',
                     '#include "observed_optimizer.hpp"\n#include "saved_candidate.hpp"')
        driver = one(driver,
            '  if(argc!=7)throw std::runtime_error("Usage: check_ray_stopping GRID.csv IDENTIFIED_RAY.csv OUT BUDGETS SPACINGS FIELD_SPACING");',
            '  if(argc!=9)throw std::runtime_error("Usage: check_ray_stopping GRID.csv IDENTIFIED_RAY.csv OUT BUDGET SPACING DECLARED_FIELD_SPACING SAVED_PATHS.csv SAVED_CANDIDATE.csv");')
        driver = one(driver,
            '  first_arrival::Field field(g,b,std::stod(argv[6]),2,true);\n  auto seed=field.candidate(a);',
            '  const auto saved_spacings=values(argv[5]),saved_budgets=values(argv[4]);\n'
            '  if(saved_spacings.size()!=1||saved_budgets.size()!=1||\n'
            '     !std::isfinite(saved_spacings[0])||saved_spacings[0]<=0||\n'
            '     !std::isfinite(saved_budgets[0])||saved_budgets[0]<=0||\n'
            '     saved_budgets[0]>std::numeric_limits<int>::max()||std::floor(saved_budgets[0])!=saved_budgets[0]||\n'
            '     !(csv_double(argv[6])>0))throw std::runtime_error("Invalid single saved-seed declaration");\n'
            '  // The frozen wrapper binds declared field spacing/model/native IDs to the captured candidate; no field is rebuilt.\n'
            '  const std::string saved_run="fmm_"+std::to_string(saved_spacings[0])+"_"+std::to_string(int(saved_budgets[0]));\n'
            '  auto seed=read_saved_candidate(g,a,b,saved_run,audit_observation,argv[7],argv[8]);')
        (source/'diagnostics/check_ray_stopping.cpp').write_text(driver)
        if variant == 'seed_loaded_B':
            (out/'seed_loader_driver.diff').write_text(''.join(difflib.unified_diff(original_driver.splitlines(True),driver.splitlines(True),
                                                       fromfile='frozen_B/check_ray_stopping.cpp',tofile='seed_loaded_B/check_ray_stopping.cpp')))
        else:
            for name in ('src/core.hpp','diagnostics/observed_optimizer.hpp'):
                path=source/name
                before=path.read_text()
                after=one(before,'      if (sy > 1e-14) {','      if (sy > 0) {')
                path.write_text(after)
                (out/(Path(name).name+'.retention.diff')).write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),
                    fromfile='seed_loaded_B/'+name,tofile='positive_curvature/'+name)))
        fixture=one(driver,'int main(int argc,char **argv) {','int frozen_seed_driver_main(int argc,char **argv) {')
        (source/'diagnostics/fixture_driver.hpp').write_text(fixture)
        # Tests compile a predicate extracted from the actual frozen trace.
        core=(source/'src/core.hpp').read_text()
        marker='      if (sy > '+('1e-14' if variant=='seed_loaded_B' else '0')+') {'
        need(core.count(marker)==1,'Ambiguous extracted predicate')
        predicate=marker.strip()[4:-3]
        (source/'diagnostics/extracted_retention.hpp').write_text('bool extracted_retention(double sy) { return '+predicate+'; }\n')
        variants[variant] = dict(source_sha256={str(p.relative_to(source)):sha(p) for p in source.rglob('*') if p.is_file()},
                                 mathematical_retention_predicate=predicate)
    b,c=[out/'source'/name for name in ('seed_loaded_B','positive_curvature')]
    changed=[name for name in variants['seed_loaded_B']['source_sha256'] if sha(b/name)!=sha(c/name)]
    need(set(changed)=={'src/core.hpp','diagnostics/observed_optimizer.hpp','diagnostics/extracted_retention.hpp'},
         'Unexpected difference between variants')
    result=dict(status='prepared_for_invented_controls_only',prepared_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
        native_context=summary['native_context'],input_sha256=pins,variants=variants,
        between_variant_changed_files=changed,compiler=summary['compiler'],compiler_sha256=summary['compiler_sha256'],
        limitations=['No native candidate is loaded, no compilation or ray is performed by preparation.',
                     'Both variants share the same diagnostic seed loader; only two numerical retention literals differ.',
                     'The extracted predicate header is for tests and is not included by either native driver.',
                     'Actual B seed-load replay and five-file parity must pass review before a positive-curvature native run.'])
    result['output_sha256']={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()}
    (out/'prepared.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(str(out/'prepared.json'),flush=True)


if __name__ == '__main__':
    main()
