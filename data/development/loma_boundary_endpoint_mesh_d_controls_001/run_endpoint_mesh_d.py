#!/usr/bin/env python3
"""Frozen explicit-knot endpoint experiment; reviewed controls precede native."""
import argparse
import csv
from decimal import Decimal as D, localcontext
import difflib
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
NUMERICAL_SOURCE = ROOT / 'data/development/usable_curvature_integration_prepared_001/after/src'
OBSERVER = ROOT / 'data/development/loma_initial_failure_24104_001'
PLAN = ROOT / 'data/development/loma_boundary_endpoint_next_step/plan.json'


def need(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def table(path, fields, rows):
    with path.open('x', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def explicit_trace(core):
    """Replace only initialization. Retain the optimizer suffix byte for byte."""
    start = core.index('Ray trace(')
    end = core.index('\nstruct Entry {', start)
    original = core[start:end]
    begin = original.index('  std::vector<P> p;\n')
    merge = original.index('  int merged = merge_close_nodes', begin)
    replacement = '''  if (!seed || seed->size() < 2 || seed->front() != a || seed->back() != b)
    throw std::runtime_error("Explicit mesh requires its original endpoints");
  std::vector<P> p = *seed;
  for (const auto &point : p)
    if (!g.contains(point))
      throw std::runtime_error("Explicit mesh is outside the original box");
'''
    changed = original[:begin] + replacement + original[merge:]
    changed = changed.replace('Ray trace(', 'Ray trace_mesh(', 1)
    need(changed[changed.index('  int merged = merge_close_nodes'):] == original[merge:],
         'Optimizer or derivative body changed')
    return original, changed, hashlib.sha256(original[merge:].encode()).hexdigest()


def decimal(x):
    return D.from_float(float(x))


def polygon_reference(points, v0, g):
    """Independent 80-digit reciprocal-affine segment action/endpoint gradient."""
    p = [tuple(decimal(x) for x in point) for point in points]
    v0, g = decimal(v0), decimal(g)
    action = D(0)
    gradients = [[D(0)] * 3 for unused in p]
    for n, (a, b) in enumerate(zip(p, p[1:])):
        d = [y-x for x, y in zip(a, b)]
        length = sum(x*x for x in d).sqrt()
        need(length > 0, 'Zero edge in control polygon')
        va, vb = v0+g*a[2], v0+g*b[2]
        dv = vb-va
        if dv:
            average = (vb/va).ln()/dv
            da, db = g*(average-1/va)/dv, g*(1/vb-average)/dv
        else:
            average = 1/va
            da = db = -g/(2*va*va)
        action += length*average
        for k in range(3):
            gradients[n][k] -= d[k]*average/length
            gradients[n+1][k] += d[k]*average/length
        gradients[n][2] += length*da
        gradients[n+1][2] += length*db
    return action, gradients


def affine_reference(a, b, v0, gradient, bottom):
    """Closed-form continuous affine-medium value with a finite fast bottom."""
    a, b = [tuple(decimal(x) for x in p) for p in (a, b)]
    g, v0, bottom = decimal(gradient), decimal(v0), decimal(bottom)
    d = [x-y for x, y in zip(a, b)]
    length = sum(x*x for x in d).sqrt()
    va, vb = v0+g*a[2], v0+g*b[2]
    if not g:
        return length/va, [x/(length*va) for x in d], 'homogeneous_direct', None
    vmax = v0+g*bottom
    qa, qb = [(vmax*vmax-v*v).sqrt() for v in (va, vb)]
    horizontal = (d[0]*d[0]+d[1]*d[1]).sqrt()
    guide = horizontal-(qa+qb)/g
    if guide >= 0:
        action = (((vmax+qa)/va).ln()+((vmax+qb)/vb).ln())/g+guide/vmax
        derivative = [d[k]/(horizontal*vmax) for k in (0, 1)]
        derivative.append(-((1/va**2)-(1/vmax**2)).sqrt())
        return action, derivative, 'finite_bottom_guide', guide
    q = g*length/(2*(va*vb).sqrt())
    factor = (va*vb).sqrt()*(1+q*q).sqrt()
    action = 2*(q+(1+q*q).sqrt()).ln()/g
    derivative = [d[k]/(length*factor) for k in (0, 1)]
    derivative.append((d[2]/length-g*length/(2*va))/factor)
    return action, derivative, 'affine_interior', guide


def fixtures(out):
    cases = []
    # First two controls are exactly representable, with independent rational
    # baseline actions/partials. The near-transition case retains its actual
    # binary64 rounded circular seed and contact distance.
    near = .001
    arc = [(near+6*math.sin(math.acos(5/6)*i/32), 0.,
            6*math.cos(math.acos(5/6)*i/32)-5) for i in range(33)]
    arc[0] = (near, 0., 1.)
    arc[-1] = (near+math.sqrt(11), 0., 0.)
    definitions = [
        ('positive_guide', 5., 1., [(0.,0.,1.),(.25,0.,1.),(.5,0.,1.),(1.,0.,1.),(2.,0.,1.)],
         [0., 2.**-10, 2.**-14, 2.**-18, 2.**-22]),
        ('homogeneous_oblique', 6., 0., [(i/4,0.,1-i/4) for i in range(5)],
         [0., 2.**-10, 2.**-14, 2.**-18, 2.**-22]),
        ('near_zero_guide', 5., 1., [(0.,0.,1.)]+arc,
         [0., 2.**-30, 2.**-28, 2.**-26, 2.**-24, 2.**-22])]
    for name, v0, g, points, epsilons in definitions:
        directory = out/name
        directory.mkdir()
        grid = [dict(x=x,y=y,z=z,v=v0+g*z) for z in (0.,1.)
                for y in (-1.,1.) for x in (-1.,4.)]
        table(directory/'grid.csv', ['x','y','z','v'], grid)
        table(directory/'input_path.csv', ['run_id','observation_index','node','x','y','z'],
              [dict(run_id=name,observation_index='invented_'+name,node=n,x=p[0],y=p[1],z=p[2])
               for n,p in enumerate(points)])
        cases.append(dict(name=name, v0=v0, gradient=g, bottom=1.,
                          epsilons=epsilons, original_points=points))
    return cases


def assess_control(directory, case):
    rows, points = read(directory/'evaluations.csv'), read(directory/'paths.csv')
    paths = {}
    for row in points:
        key = tuple(row[k] for k in ('subsegments','epsilon_requested_km','family'))
        path = paths.setdefault(key, [])
        need(int(row['node']) == len(path), 'Control path order changed')
        path.append(tuple(float(row[k]) for k in 'xyz'))
    checks, comparisons = [], []
    def check(name, ok, **details):
        checks.append(dict(name=name,passed=bool(ok),**details))
    levels = [1,2,4,8,16]
    expected = {(n, epsilon, family) for n in levels for epsilon in case['epsilons']
                for family in ('fixed','tied','optimized')}
    actual = [(int(r['subsegments']),float(r['epsilon_requested_km']),r['family']) for r in rows]
    check('complete_control_roster', len(actual)==len(expected) and set(actual)==expected)
    parity = read(directory/'parity.csv')
    check('ordinary_and_explicit_mesh_trace_parity', len(parity)==6 and all(r['passed']=='1' for r in parity))
    check('no_optimizer_exceptions', all(not r['error'] for r in rows))
    baseline = {(r['subsegments'],r['family']):r for r in rows if float(r['epsilon_requested_km'])==0}
    for row in rows:
        if row['error']:
            comparisons.append(dict(row,analysis_status='preserved_optimizer_exception'))
            continue
        key = tuple(row[k] for k in ('subsegments','epsilon_requested_km','family'))
        path = paths[key]
        n, epsilon = int(row['subsegments']), float(row['epsilon_requested_km'])
        exact, grad = polygon_reference(path,case['v0'],case['gradient'])
        scale = max(1.,abs(float(exact)))
        action_error = abs(float(row['time_s'])-float(exact))
        source = [float(row['source_d'+axis]) for axis in 'xyz']
        partial_error = max(abs(x-float(y)) for x,y in zip(source,grad[0]))
        check('polygon_action_'+str(key), action_error<=512*sys.float_info.epsilon*scale,
              error_s=action_error,arithmetic_allowance_s=512*sys.float_info.epsilon*scale)
        check('polygon_source_partial_'+str(key), partial_error<=2048*sys.float_info.epsilon,
              maximum_error_s_per_km=partial_error,arithmetic_allowance_s_per_km=2048*sys.float_info.epsilon)
        if row['family']=='tied':
            tied = [grad[0][k]+sum((1-D(j)/n)*grad[j][k] for j in range(1,n)) for k in range(3)]
            error = max(abs(float(row['tied_source_d'+axis])-float(tied[k])) for k,axis in enumerate('xyz'))
            check('tied_chain_rule_'+str(key), error<=2048*sys.float_info.epsilon,
                  maximum_error_s_per_km=error)
        continuous, derivative, branch, guide = affine_reference(path[0],path[-1],case['v0'],case['gradient'],case['bottom'])
        continuous_error = float(row['time_s'])-float(continuous)
        vector_error = math.sqrt(sum((x-float(y))**2 for x,y in zip(source,derivative)))
        check('continuous_value_lower_bound_'+str(key), continuous_error>=-512*sys.float_info.epsilon*scale)
        if case['name']=='homogeneous_oblique' and row['family']=='optimized':
            check('homogeneous_optimized_accuracy_'+str(key),
                  abs(continuous_error)<=2.5e-5 and vector_error<=3e-6 and row['converged']=='1')
        previous = baseline[(row['subsegments'],row['family'])]
        base_continuous = affine_reference(case['original_points'][0],case['original_points'][-1],
                                          case['v0'],case['gradient'],case['bottom'])[0]
        item = dict(row,analysis_status='evaluated',polygon_exact_action_s=str(exact),
                    polygon_action_error_s=action_error,polygon_source_partial_error_s_per_km=partial_error,
                    continuous_time_s=str(continuous),continuous_source_gradient_json=json.dumps(list(map(float,derivative))),
                    continuous_branch=branch,guide_margin_km='' if guide is None else str(guide),
                    continuous_time_error_s=continuous_error,continuous_source_norm_error_s_per_km=vector_error,
                    scientific_time_pass=abs(continuous_error)<=2.5e-5,
                    scientific_source_pass=vector_error<=3e-6,
                    reported_value_secant_dz_s_per_km='',continuous_value_secant_dz_s_per_km='')
        if epsilon:
            actual_epsilon = decimal(row['epsilon_actual_km'])
            item['reported_value_secant_dz_s_per_km'] = -(float(row['time_s'])-float(previous['time_s']))/float(actual_epsilon)
            item['continuous_value_secant_dz_s_per_km'] = str(-(continuous-base_continuous)/actual_epsilon)
        comparisons.append(item)
    if case['name']=='positive_guide':
        first = baseline[('1','fixed')]
        check('rational_guide_baseline', abs(float(first['time_s'])-1/3)<=1e-14 and
              abs(float(first['source_dz'])+1/288)<=1e-14)
    if case['name']=='near_zero_guide':
        branches = {r['continuous_branch'] for r in comparisons if r.get('continuous_branch')}
        check('near_zero_guide_crosses_branch_transition', branches=={'finite_bottom_guide','affine_interior'})
    fields = list(dict.fromkeys(k for r in comparisons for k in r))
    table(directory/'comparisons.csv',fields,comparisons)
    return dict(name=case['name'],checks=checks,rows=len(rows),
                optimizer_false_flags=sum(r['family']=='optimized' and r['converged']=='0' for r in rows),
                optimizer_exceptions=sum(bool(r['error']) for r in rows),
                optimized_source_accuracy_failures=sum(r['family']=='optimized' and not r.get('scientific_source_pass',False) for r in comparisons),
                scope='Arithmetic/parity checks are separate from retained optimizer and continuous-reference accuracy outcomes.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--build',required=True,type=Path)
    args=parser.parse_args()
    os.chdir(str(ROOT))
    out,build=args.output.resolve(),args.build.resolve()
    for p in (out,build):
        p.relative_to(ROOT);need(p!=ROOT and not p.exists(),'Fresh repository-local output/build required')
    need(out not in build.parents and build not in out.parents and out!=build,'Overlapping output/build')
    plan=json.loads(PLAN.read_text())
    for p,h in plan['input_sha256'].items():need(sha(ROOT/p)==h,'Predeclared input changed: '+p)
    observer=json.loads((OBSERVER/'summary.json').read_text())
    compiler=Path(observer['compiler']);need(sha(compiler)==observer['compiler_sha256'],'Compiler changed')
    sources=[Path(__file__).resolve(),ROOT/'diagnostics/check_endpoint_mesh.cpp',PLAN]
    sources += [NUMERICAL_SOURCE/name for name in ('core.hpp','ray_metric.hpp','csv.hpp','usable_ray_curvature.hpp')]
    pins={str(p.relative_to(ROOT)):sha(p) for p in sources}
    out.mkdir(parents=True);build.mkdir(parents=True)
    summary=dict(status='preparing',mode='invented_controls_only',input_sha256=pins,
                 plan_sha256=sha(PLAN),compiler=str(compiler),compiler_sha256=sha(compiler),commands=[],
                 scope='Three invented analytic controls; no native trace, source/flag change or inverse run.')
    def save():
        temp=out/'summary.json.new';temp.write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
        temp.replace(out/'summary.json')
    def command(name,argv):
        record=dict(stage=name,command=[str(x.relative_to(ROOT)) if isinstance(x,Path) else str(x) for x in argv],status='running')
        # The compiler is an external executable; retain its recorded absolute path.
        record['command'][0]=str(argv[0])
        summary['commands'].append(record)
        started=time.monotonic()
        with (out/(name+'_stdout.log')).open('w') as stdout,(out/(name+'_stderr.log')).open('w') as stderr:
            child=subprocess.Popen(record['command'],stdout=stdout,stderr=stderr,start_new_session=True,
                                   env=dict(os.environ,OMP_NUM_THREADS='1',TMPDIR=str(ROOT/'tmp'),PYTHONDONTWRITEBYTECODE='1'))
            record['pid']=child.pid;save()
            try:
                code=child.wait()
            except BaseException:
                os.killpg(child.pid,signal.SIGTERM)
                try:child.wait(timeout=5)
                except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
                raise
        record.update(status='completed',return_code=code,seconds=time.monotonic()-started);save()
        need(code==0,name+' failed')
    try:
        for p in sources:
            if p.parent==NUMERICAL_SOURCE:target=out/'source/src'/p.name
            elif p==PLAN:target=out/'source/plan.json'
            else:target=out/'source/diagnostics'/p.name
            target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(str(p),str(target))
            need(sha(target)==pins[str(p.relative_to(ROOT))],'Source copy mismatch')
        core=(out/'source/src/core.hpp').read_text()
        original,changed,suffix=explicit_trace(core)
        generated=out/'source/diagnostics/explicit_mesh_trace.hpp'
        generated.write_text('#pragma once\n'+changed)
        (out/'initialization.diff').write_text(''.join(difflib.unified_diff(original.splitlines(True),changed.splitlines(True),
                                                       fromfile='frozen_trace',tofile='explicit_mesh_trace')))
        summary['unchanged_optimizer_and_derivative_suffix_sha256']=suffix
        binary=build/'check'
        command('compile',[str(compiler),'-std=gnu++17','-O3','-Wall','-Wextra','-Wpedantic',
                           out/'source/diagnostics/check_endpoint_mesh.cpp','-o',binary])
        summary['binary_sha256']=sha(binary)
        cases=fixtures(out)
        summary['invented_cases']=cases;save()
        results=[]
        for case in cases:
            d=out/case['name']
            command(case['name'],[binary,d/'grid.csv',d/'input_path.csv',case['name'],d,str(plan['optimizer_max_updates']),
                                  ','.join(map(str,case['epsilons'])),','.join(map(str,plan['subdivision_levels'])),'1'])
            with localcontext() as context:
                context.prec=80
                results.append(assess_control(d,case))
            summary['controls']=results;save()
        for p,h in pins.items():need(sha(ROOT/p)==h,'Input changed during controls: '+p)
        passed=all(c['passed'] for result in results for c in result['checks'])
        summary.update(status='passed_analytical_contract_controls' if passed else 'failed_analytical_contract_controls',
                       passing_checks=sum(c['passed'] for r in results for c in r['checks']),
                       total_checks=sum(len(r['checks']) for r in results),
                       native_execution_performed=False,
                       limitations=['Exact analytical polygon checks do not turn coarse endpoint partials into derivatives of a minimized envelope.',
                                    'All optimizer local flags, source-accuracy failures, merges and topology are preserved.',
                                    'No native execution is implemented by this controls-only launcher; source/control review must precede a separate native invocation.'])
        summary['artifact_sha256']={str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*'))
                                   if p.is_file() and p.name not in ('summary.json','summary.json.new')}
        save();need(passed,'Analytical contract controls failed')
    except BaseException as error:
        summary.update(status='failed',failure=repr(error))
        summary['artifact_sha256']={str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*'))
                                   if p.is_file() and p.name not in ('summary.json','summary.json.new')}
        save();raise
    print(str(out/'summary.json'),flush=True)


if __name__=='__main__':
    main()
