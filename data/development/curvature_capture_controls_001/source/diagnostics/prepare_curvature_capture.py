#!/usr/bin/env python3
"""Freeze neutral hooks around the reviewed B optimizer; do not run native rays."""
import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import shutil
import time

ROOT = Path(__file__).resolve().parents[1]


def need(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            digest.update(block)
    return digest.hexdigest()


def save(path, value):
    temporary = path.with_name(path.name + '.new')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    temporary.replace(path)


def one(text, old, new):
    need(text.count(old) == 1, 'Changed unique hook insertion point: ' + old[:70])
    return text.replace(old, new, 1)


def instrument(optimizer, driver):
    initial = '  audit_step("initial",0,0,g,p,grad,T,NAN,NAN,NAN,NAN,nullptr,0,S.size(),false,0,false);'
    optimizer = one(optimizer, initial, initial + '\n  curvature_begin(p);')
    reset = '      rho.clear();\n    }\n    double slope = dot(grad, q);'
    optimizer = one(optimizer, reset, reset.replace('      rho.clear();',
        '      rho.clear();\n      curvature_memory_clear(iter,"cone_metric_fallback");'))
    merged = '      rho.clear();\n      merged += trial_merged;'
    optimizer = one(optimizer, merged, merged.replace('      rho.clear();',
        '      rho.clear();\n      curvature_memory_clear(iter,"accepted_node_merge");'))
    end_pair = '        rho.push_back(1 / sy);\n      }\n    }\n    p = std::move(trial);'
    optimizer = one(optimizer, end_pair, end_pair.replace('\n    }\n    p =',
        '\n      curvature_pair(iter,updates+1,g,p,trial,grad,ng,q,s,y,sy,audit_curvature,\n'
        '                     step,T,newT,slope,scale,S,Y);\n    }\n    p ='))
    driver = one(driver, '#include "observed_optimizer.hpp"',
                 '#include "curvature_capture.hpp"\n#include "observed_optimizer.hpp"')
    driver = one(driver, '  std::string out=argv[3];',
                 '  std::string out=argv[3];\n  curvature_open(out);')
    run = '    audit_run=(fmm?"fmm_":"straight_")+std::to_string(spacing)+"_"+std::to_string(budget);'
    driver = one(driver, run, run + '\n    curvature_capture_active=fmm;\n    if(fmm)curvature_seed(seed);')
    driver = one(driver, '    audit_history=nullptr;',
                 '    audit_history=nullptr;\n    curvature_capture_active=false;')
    ending = '             <<" gradient="<<ray.gradient<<" observed_matches="<<matches<<std::endl;\n  }\n}'
    driver = one(driver, ending, ending[:-1] + '  curvature_flush();\n}')
    return optimizer, driver


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', default='data/development/loma_outer_accumulation_native_001')
    parser.add_argument('--output', required=True)
    parser.add_argument('--build', required=True)
    args = parser.parse_args()
    os.chdir(str(ROOT))
    baseline, out, build = [(ROOT / value).resolve() for value in (args.baseline, args.output, args.build)]
    for path in (baseline, out, build):
        path.relative_to(ROOT)
        need(path != ROOT, 'Repository root cannot be an evidence/build directory')
    for a in (out, build):
        need(not a.exists(), 'Fresh output/build required')
        for b in (baseline, build if a == out else out):
            need(a != b and a not in b.parents and b not in a.parents, 'Disjoint directories required')
    summary, execution, review = [json.loads((baseline / name).read_text())
                                  for name in ('summary.json', 'execution.json', 'review.json')]
    need(summary['status'] == 'completed_single_change_diagnostic' and execution['status'] == 'completed' and
         execution['return_code'] == 0 and review['status'] == 'passed', 'B baseline is not complete/reviewed')
    need(execution['summary_sha256'] == review['summary_sha256'] == sha(baseline / 'summary.json') and
         review['execution_sha256'] == sha(baseline / 'execution.json'), 'Stale B review/ledger')
    need((summary['path_spacing_km'], summary['field_spacing_km'], summary['maximum_updates'], summary['threads']) ==
         (.03125, .125, 1000, 1), 'Unexpected B numerical settings')
    pins = {}

    def pin(path, expected=None):
        digest = sha(path)
        need(expected is None or digest == expected, 'Changed input: ' + str(path))
        pins[str(path.relative_to(ROOT))] = digest

    for name, digest in summary['output_sha256'].items():
        pin(baseline / name, digest)
    for name in ('summary.json', 'execution.json', 'review.json', 'controller_completion.json'):
        pin(baseline / name)
    need(review['controller_completion_sha256'] == sha(baseline / 'controller_completion.json'), 'Stale controller review')
    need(sha(Path(summary['compiler'])) == summary['compiler_sha256'], 'Compiler changed')
    for name in ('curvature_capture.hpp', 'prepare_curvature_capture.py'):
        pin(ROOT / 'diagnostics' / name)
    out.mkdir(parents=True)
    build.mkdir(parents=True)
    shutil.copytree(str(baseline / 'source'), str(out / 'source'))
    shutil.copytree(str(baseline / 'inputs'), str(out / 'inputs'))
    for name in ('identified_ray.csv', 'summary.json', 'execution.json', 'review.json'):
        shutil.copyfile(str(baseline / name), str(out / ('identified_ray.csv' if name == 'identified_ray.csv' else 'inputs/baseline_' + name)))
    for name in ('curvature_capture.hpp', 'prepare_curvature_capture.py'):
        shutil.copyfile(str(ROOT / 'diagnostics' / name), str(out / 'source/diagnostics' / name))
    old_optimizer = (out / 'source/diagnostics/observed_optimizer.hpp').read_text()
    old_driver = (out / 'source/diagnostics/check_ray_stopping.cpp').read_text()
    optimizer, driver = instrument(old_optimizer, old_driver)
    for name, old, new in [('observed_optimizer.hpp', old_optimizer, optimizer), ('check_ray_stopping.cpp', old_driver, driver)]:
        (out / 'source/diagnostics' / name).write_text(new)
        (out / (name + '.diff')).write_text(''.join(difflib.unified_diff(old.splitlines(True), new.splitlines(True),
                                                                   fromfile='frozen_B/' + name, tofile='neutral_capture/' + name)))
    fixture = one(driver, 'int main(int argc,char **argv)', 'int frozen_capture_driver_main(int argc,char **argv)')
    (out / 'source/diagnostics/fixture_driver.hpp').write_text(fixture)
    for name, digest in summary['source_sha256'].items():
        if name not in ('diagnostics/observed_optimizer.hpp', 'diagnostics/check_ray_stopping.cpp'):
            need(sha(out / 'source' / name) == digest, 'Numerical source changed: ' + name)
    record = dict(status='prepared_neutral_curvature_source', prepared_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                  scope='Neutral logging only; no native ray or production source change', baseline=str(baseline.relative_to(ROOT)),
                  compiler=summary['compiler'], compiler_sha256=summary['compiler_sha256'], build=str(build.relative_to(ROOT)),
                  path_spacing_km=.03125, field_spacing_km=.125, maximum_updates=1000, threads=1,
                  native_context=summary['native_context'], input_sha256=pins,
                  expected_old_table_sha256={name: summary['output_sha256'][name] for name in
                      ('results.csv', 'history.csv', 'paths.csv', 'path_gradient_checks.csv', 'cone_metric.csv')},
                  selected_iterations=[33,34,47,48,433,434,435] + list(range(988,1000)),
                  source_sha256={str(p.relative_to(out / 'source')): sha(p) for p in (out / 'source').rglob('*') if p.is_file()},
                  limitations=['Exact computed sy is observed after the original retention branch, without replacing it.',
                               'Stored s and actual rounded displacement remain separate; no threshold or informative-curvature claim.',
                               'Cut rows reconstruct existing predicates for diagnostics; no action or derivative is evaluated by those hooks.'])
    record['prepared_file_sha256'] = {str(p.relative_to(out)): sha(p) for p in out.rglob('*') if p.is_file()}
    save(out / 'prepared.json', record)
    print(str(out / 'prepared.json'), flush=True)


if __name__ == '__main__':
    main()
