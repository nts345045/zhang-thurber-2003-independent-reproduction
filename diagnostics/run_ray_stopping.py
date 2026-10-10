#!/usr/bin/env python3
"""Observe a declared ray optimizer for one identified saved-model ray.

Historical direction variants require the pre-promotion optimizer. The explicit
production mode observes the current trace without changing its directions.
"""
import argparse
import csv
import difflib
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
from seeded_bending import write_header

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--variant', required=True)
parser.add_argument('--budgets', default='1000,2000,4000')
parser.add_argument('--spacings', default='0.5,0.25')
direction_group=parser.add_mutually_exclusive_group()
direction_group.add_argument('--reduced-metric', action='store_true',
                    help='Replace only the non-descent fallback by a reduced weighted-Laplacian direction')
direction_group.add_argument('--reduced-all', action='store_true',
                    help='Use the reduced weighted-Laplacian direction on every update, without a curvature correction')
direction_group.add_argument('--cone-metric', action='store_true',
                    help='Solve the full tangent-cone metric quadratic by a feasible active-set method at every update')
direction_group.add_argument('--cone-hybrid', action='store_true',
                    help='Retain feasible descent L-BFGS directions; replace projected or non-descent directions by the full cone metric')
direction_group.add_argument('--production-hybrid', action='store_true',
                    help='Observe the promoted trace directly; change no direction, initialization, or stopping rule')
args = parser.parse_args()
use_cone=args.cone_metric or args.cone_hybrid or args.production_hybrid
use_reduced=args.reduced_metric or args.reduced_all or args.cone_metric or args.cone_hybrid
record_metric=use_reduced or args.production_hybrid
pure_metric=args.reduced_all or args.cone_metric
if not re.fullmatch(r'[a-zA-Z0-9_-]+', args.variant):
    parser.error('Variant must contain only letters, digits, underscores, or hyphens')
if not re.fullmatch(r'[0-9,.]+', args.budgets + args.spacings):
    parser.error('Budgets and spacings must be comma-separated positive numbers')
build = Path('tmp/ray_stopping') / args.variant
out = Path('data/development') / ('ray_stopping_' + args.variant)
if (ROOT / build).exists() or (ROOT / out).exists():
    parser.error('Choose a fresh variant to preserve evidence')
fallback_old = ('      q = grad;\n      for (auto &v : q)\n        v = -v;\n'
                '      project_ray_direction(g, p, q);')
current_core = (ROOT / 'src/core.hpp').read_text()
if args.production_hybrid:
    if current_core.count('      q = cone_ray_direction(g, p, grad);') != 1:
        parser.error('Production mode requires the promoted hybrid trace')
elif current_core.count(fallback_old) != 1:
    parser.error('Historical optimizer modes require the pre-promotion trace and diagnostic helpers; '
                 'use their frozen source snapshot, or --production-hybrid for current trace')
inputs = Path('data/development/hayward_dd_top_layer_rays.csv')
grid = Path('data/hayward/dd_grid.csv')
fixed = [inputs, grid, Path('data/hayward/dd_events.csv'), Path('data/hayward/stations.csv'),
         Path('configs/hayward.cfg'), Path('src/core.hpp'), Path('src/main.cpp'),
         Path('src/csv.hpp'), Path('src/ray_checks.hpp')]
for name in ['src/first_arrival.hpp', 'src/forward.hpp', 'src/ray_metric.hpp']:
    if (ROOT / name).exists():
        fixed.append(Path(name))
def sha(path): return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
input_hashes = {str(path): sha(path) for path in fixed}
with (ROOT / inputs).open() as stream:
    reader = csv.DictReader(stream)
    names = reader.fieldnames
    selected = [r for r in reader if r['i'] == '775' and r['station'] == '184']
if len(selected) != 1 or selected[0]['event_i_resource_id'] != 'quakeml:NC.anss.org/Event/NC/403533' or selected[0]['channel_seed_id'] != 'NC.CMO..EHZ':
    raise ValueError('The requested native event/channel mapping changed')
(ROOT / build).mkdir(parents=True)
(ROOT / out).mkdir(parents=True)
identified = out / 'identified_ray.csv'
with (ROOT / identified).open('w', newline='') as stream:
    writer = csv.DictWriter(stream, fieldnames=names, lineterminator='\n')
    writer.writeheader()
    writer.writerows(selected)
snapshot = build / 'source'
sources = ['diagnostics/check_ray_stopping.cpp', 'diagnostics/first_arrival_fmm.hpp',
           'diagnostics/seeded_bending.py', 'diagnostics/run_ray_stopping.py',
           'src/core.hpp', 'src/main.cpp', 'src/csv.hpp', 'src/ray_checks.hpp']
sources += [str(path) for path in fixed if str(path).startswith('src/') and str(path) not in sources]
if use_reduced:
    sources.append('diagnostics/reduced_ray_metric.hpp')
if use_cone and not args.production_hybrid:
    sources.append('diagnostics/cone_ray_metric.hpp')
for relative in sources:
    target = ROOT / snapshot / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(str(ROOT / relative), str(target))
if not args.production_hybrid:
    write_header(ROOT / snapshot / 'diagnostics/seeded_bending.hpp', ROOT / snapshot / 'src/core.hpp')
    sources.append('diagnostics/seeded_bending.hpp')
core = (ROOT / snapshot / 'src/core.hpp').read_text()
start = core.index('Ray trace(const Grid &g,')
end = core.index('\nstruct Entry {', start)
trace_source = core[start:end]
seed_source = '' if args.production_hybrid else (ROOT / snapshot / 'diagnostics/seeded_bending.hpp').read_text()
original_trace_source, original_seed_source = trace_source, seed_source
fallback_new = ('      ReducedRayMetricStats metric_stats;\n'
                '      q = reduced_ray_direction(g,p,grad,&metric_stats);')
if use_reduced:
    if trace_source.count(fallback_old)!=1 or seed_source.count(fallback_old)!=1:
        raise ValueError('Original fallback insertion point changed')
    if args.cone_hybrid:
        def replace_projected_direction(source):
            first=source.index('    project_ray_direction(g, p, q);')
            last=source.index('    double step = 1, newT = T;',first)
            return source[:first]+('    Vec feasible_direction=q;\n'
                '    project_ray_direction(g,p,feasible_direction);\n'
                '    if(feasible_direction!=q||!(dot(grad,q)<0)) {\n'
                '      ConeRayMetricStats metric_stats;\n'
                '      q = cone_ray_direction(g,p,grad,&metric_stats);\n'
                '      S.clear(); Y.clear(); rho.clear();\n'
                '    }\n'
                '    double slope=dot(grad,q);\n'
                '    Vec check_feasible=q;\n'
                '    project_ray_direction(g,p,check_feasible);\n'
                '    if(!std::isfinite(slope)||std::any_of(q.begin(),q.end(),[](double value){return !std::isfinite(value);})||check_feasible!=q||!(slope<0))\n'
                '      throw std::runtime_error("Hybrid ray direction is not feasible strict descent");\n')+source[last:]
        trace_source=replace_projected_direction(trace_source)
        seed_source=replace_projected_direction(seed_source)
    elif pure_metric:
        def replace_direction(source):
            first=source.index('    Vec q = grad, alpha(S.size());')
            last=source.index('    double step = 1, newT = T;',first)
            stats_type='ConeRayMetricStats' if args.cone_metric else 'ReducedRayMetricStats'
            direction_function='cone_ray_direction' if args.cone_metric else 'reduced_ray_direction'
            return source[:first]+('    S.clear(); Y.clear(); rho.clear();\n'
                '    '+stats_type+' metric_stats;\n'
                '    Vec q = '+direction_function+'(g,p,grad,&metric_stats);\n'
                '    double slope = dot(grad,q);\n')+source[last:]
        trace_source=replace_direction(trace_source)
        seed_source=replace_direction(seed_source)
    else:
        trace_source=trace_source.replace(fallback_old,fallback_new,1)
        seed_source=seed_source.replace(fallback_old,fallback_new,1)
    controls=trace_source.replace('Ray trace(', 'Ray control_trace(', 1)+'\n'+seed_source.replace('Ray bend_seed(', 'Ray control_bend_seed(', 1)
    (ROOT / snapshot / 'diagnostics/control_optimizer.hpp').write_text(controls)
    sources.append('diagnostics/control_optimizer.hpp')
def instrument(source):
    source = source.replace('Ray trace(', 'Ray observed_trace(', 1).replace('Ray bend_seed(', 'Ray observed_bend_seed(', 1)
    def substitute(old, new):
        nonlocal source
        if source.count(old) != 1:
            raise ValueError('Optimizer observation insertion point changed: ' + old)
        source = source.replace(old, new, 1)
    substitute('  for (; iter < maxit; iter++) {',
               '  audit_step("initial",0,0,g,p,grad,T,NAN,NAN,NAN,NAN,nullptr,0,S.size(),false,0,false);\n'
               '  for (; iter < maxit; iter++) {\n'
               '    int audit_searches=0;\n    bool audit_reset=false,audit_curvature=false;')
    if not pure_metric and not args.cone_hybrid and not args.production_hybrid:
        substitute('    if (slope >= 0) {', '    if (slope >= 0) {\n      audit_reset=true;')
    if args.production_hybrid:
        substitute('      q = cone_ray_direction(g, p, grad);',
                   '      ConeRayMetricStats metric_stats;\n'
                   '      q = cone_ray_direction(g, p, grad, &metric_stats);\n'
                   '      audit_reset=true; audit_metric(metric_stats);')
    elif args.cone_hybrid:
        substitute('      q = cone_ray_direction(g,p,grad,&metric_stats);',
                   '      q = cone_ray_direction(g,p,grad,&metric_stats);\n      audit_reset=true; audit_metric(metric_stats);')
    elif pure_metric:
        call='    Vec q = '+('cone_ray_direction' if args.cone_metric else 'reduced_ray_direction')+'(g,p,grad,&metric_stats);'
        substitute(call,call+'\n    audit_reset=true; audit_metric(metric_stats);')
    elif args.reduced_metric:
        substitute('      q = reduced_ray_direction(g,p,grad,&metric_stats);',
                   '      q = reduced_ray_direction(g,p,grad,&metric_stats);\n      audit_metric(metric_stats);')
    substitute('    for (int ls = 0; ls < 24; ls++, step *= 0.5) {',
               '    const double audit_feasible_step=step;\n'
               '    for (int ls = 0; ls < 24; ls++, step *= 0.5) {\n      ++audit_searches;')
    substitute('    if (!accepted)\n      break;',
               '    if (!accepted) {\n'
               '      audit_step("line_search_failed",iter,updates,g,p,grad,T,NAN,step,audit_feasible_step,slope,&q,audit_searches,S.size(),audit_reset,0,false);\n'
               '      break;\n    }')
    substitute('      if (sy > 1e-14) {', '      if (sy > 1e-14) {\n        audit_curvature=true;')
    substitute('    updates++;',
               '    updates++;\n'
               '    audit_step("accepted",iter,updates,g,p,grad,T,change,step,audit_feasible_step,slope,&q,audit_searches,S.size(),audit_reset,trial_merged,audit_curvature);')
    substitute('  Ray r;',
               '  audit_step("final",iter,updates,g,p,grad,T,NAN,NAN,NAN,NAN,nullptr,0,S.size(),false,0,false);\n'
               '  Ray r;')
    return source
observed_trace = instrument(trace_source)
observed_seed = '' if args.production_hybrid else instrument(seed_source)
(ROOT / snapshot / 'diagnostics/observed_optimizer.hpp').write_text(observed_trace + '\n' + observed_seed)
patch = ''.join(difflib.unified_diff(original_trace_source.splitlines(True), observed_trace.splitlines(True),
                                   fromfile='original_trace.cpp', tofile='observed_trace.cpp'))
patch += ''.join(difflib.unified_diff(original_seed_source.splitlines(True), observed_seed.splitlines(True),
                                    fromfile='original_bend_seed.hpp', tofile='observed_bend_seed.hpp'))
(ROOT / out / 'instrumentation.diff').write_text(patch)
sources.append('diagnostics/observed_optimizer.hpp')
archive_path = out / 'source_snapshot.tar.gz'
with (ROOT / archive_path).open('wb') as raw:
    with gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0) as zipped:
        with tarfile.open(fileobj=zipped, mode='w') as archive:
            for relative in sources:
                data = (ROOT / snapshot / relative).read_bytes()
                info = tarfile.TarInfo(relative)
                info.size = len(data)
                info.mode = 0o644
                info.uid = info.gid = info.mtime = 0
                info.uname = info.gname = ''
                archive.addfile(info, io.BytesIO(data))
binary = build / 'check_ray_stopping'
command = ['c++', '-O3', '-std=c++17', '-Wall', '-Wextra', '-Wpedantic', '-fopenmp',
           str(snapshot / 'diagnostics/check_ray_stopping.cpp'), '-o', str(binary), '-lstdc++fs']
if use_reduced:
    command.insert(1,'-DAUDIT_REDUCED_METRIC')
if use_cone:
    command.insert(1,'-DAUDIT_CONE_METRIC')
if args.production_hybrid:
    command.insert(1,'-DAUDIT_PRODUCTION_HYBRID')
environment = dict(os.environ, TMPDIR=str(ROOT / 'tmp'), OMP_NUM_THREADS='1')
compiled = subprocess.run(command, cwd=str(ROOT), env=environment, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, universal_newlines=True)
(ROOT / out / 'compile_stderr.txt').write_text(compiled.stderr)
if compiled.returncode:
    print(compiled.stderr, end='')
    raise SystemExit(compiled.returncode)
run_command = [str(binary), str(grid), str(identified), str(out), args.budgets, args.spacings]
with (ROOT / out / 'stdout.txt').open('w') as stdout, (ROOT / out / 'stderr.txt').open('w') as stderr:
    result = subprocess.run(run_command, cwd=str(ROOT), env=environment, stdout=stdout, stderr=stderr)
for path in fixed:
    if sha(path) != input_hashes[str(path)]:
        raise ValueError('Frozen input changed during the component: ' + str(path))
with (ROOT / out / 'results.csv').open() as stream:
    rows = list(csv.DictReader(stream))
files = [binary, archive_path, out / 'instrumentation.diff'] + sorted(p.relative_to(ROOT) for p in (ROOT / out).glob('*.csv')) + sorted(p.relative_to(ROOT) for p in (ROOT / out).glob('*.txt'))
matches_column='logged_matches_unobserved_variant' if record_metric else 'logged_matches_unmodified'
summary = {'purpose': ('Observation-only hooks in the current promoted trace, tested against direct calls to that trace, including source/dv/length/path equality.' if args.production_hybrid else 'Reduced weighted-Laplacian direction comparison; original objective, Armijo/domain and stopping rules retained.' if use_reduced else 'Unchanged ray stopping and update rules, with observation-only hooks tested against unmodified functions for one identified ray.'),
           'command': 'PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/run_ray_stopping.py ' + ' '.join(shlex.quote(a) for a in sys.argv[1:]),
           'compile_command': command, 'run_command': run_command, 'TMPDIR': 'tmp', 'OMP_NUM_THREADS': 1,
           'budgets': args.budgets, 'spacings_km': args.spacings, 'return_code': result.returncode,
           'reduced_metric': use_reduced,
           'direction_mode': 'production_hybrid' if args.production_hybrid else 'cone_hybrid' if args.cone_hybrid else 'cone_all' if args.cone_metric else 'reduced_all' if args.reduced_all else 'reduced_fallback' if args.reduced_metric else 'original',
           'identity_mapping': str(identified), 'identity_join_column': 'observation_index',
           'observation_index': selected[0]['observation_index'], 'cases': len(rows),
           'observation_changed_result': [r for r in rows if r[matches_column] != '1'],
           'nonconverged': [r for r in rows if r['converged'] != '1'],
           'input_sha256': input_hashes,
           'source_sha256': {name: hashlib.sha256((ROOT / snapshot / name).read_bytes()).hexdigest() for name in sources},
           'sha256': {str(path): sha(path) for path in files},
           'limitations': ['Identical stopping rules do not constitute an accuracy certificate or identify a first arrival.',
                          'Longer-update and path-spacing comparisons are isolated components, not changes to the active inversion.',
                          'Initial/final history rows have undefined step fields; endpoint path rows have no internal-node gradient. Their nan entries are explicit not-applicable values.',
                          'Finite-difference perturbations diagnose the path gradient and do not impose new science gates.']}
summary['status'] = 'observation_mismatch' if summary['observation_changed_result'] or result.returncode else 'completed_with_stopping_flags_preserved'
(ROOT / out / 'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n')
print(json.dumps({k: summary[k] for k in ['status', 'cases', 'observation_changed_result', 'nonconverged']}, indent=2))
raise SystemExit(1 if summary['observation_changed_result'] or result.returncode else 0)
