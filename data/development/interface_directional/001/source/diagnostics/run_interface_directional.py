#!/usr/bin/env python3
"""Freeze directional probes of invented controls and one identified saved guide."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1048576), b''): h.update(chunk)
    return h.hexdigest()


def table(path):
    with path.open(newline='') as f: return list(csv.DictReader(f))


def write(path, header, rows):
    with path.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader(); writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--variant', required=True)
    args = parser.parse_args()
    if not args.variant.replace('_', '').isalnum(): raise ValueError('Use an alphanumeric variant')
    out = ROOT / 'data/development/interface_directional' / args.variant
    build = ROOT / 'tmp/interface_directional' / args.variant
    if out.exists() or build.exists(): raise ValueError('Preserve prior evidence; use a fresh variant')
    out.mkdir(parents=True); build.mkdir(parents=True)
    previous = ROOT / 'data/development/loma_geometry_preflight/reference_seeds_001'
    packaging = json.loads((previous / 'packaging.json').read_text())
    for name in ('paths.csv', 'inputs/truth_grid.csv'):
        if sha(previous / name) != packaging['members_sha256'][name]: raise ValueError('Changed frozen input: ' + name)
    old_summary = json.loads((previous / 'summary.json').read_text())
    for name in ('cases.csv', 'results.csv'):
        if sha(previous / name) != old_summary['output_sha256'][name]: raise ValueError('Changed saved case/result table')
    case = next(r for r in table(previous / 'cases.csv') if r['case_id'] == 'row5_h0.03125')
    original = next(r for r in table(previous / 'results.csv') if r['case_id'] == case['case_id'] and r['stage'] == 'retained_seed_optimized')
    path = [r for r in table(previous / 'paths.csv') if r['case_id'] == case['case_id'] and r['stage'] == 'retained_seed_optimized']
    identities = ['event','station','source_event_resource_id','source_origin_resource_id','receiver_channel_seed_id',
                  'receiver_channel_fdsn_source_id','receiver_metadata_epoch_start','receiver_metadata_epoch_end']
    if not all(r[k] == case[k] for r in path for k in identities): raise ValueError('Native saved-path identities differ')
    if not all(int(r['node']) == i for i, r in enumerate(path)): raise ValueError('Saved path node order differs')
    case.update(original_converged=original['converged'], original_updates=original['updates'])
    inputs = out / 'inputs'; inputs.mkdir()
    write(inputs / 'native_case.csv', list(case), [case])
    header = ['node','x','y','z'] + identities
    write(inputs / 'native_path.csv', header, [{k:r[k] for k in header} for r in path])
    shutil.copyfile(str(previous / 'inputs/truth_grid.csv'), str(inputs / 'truth_grid.csv'))
    source = out / 'source'; source.mkdir()
    shutil.copytree(str(previous / 'source/src'), str(source / 'src'))
    (source / 'diagnostics').mkdir()
    for name in ('check_interface_directional.cpp','interface_directional.hpp','run_interface_directional.py'):
        shutil.copyfile(str(ROOT / 'diagnostics' / name), str(source / 'diagnostics' / name))
    shutil.copyfile(str(previous / 'source/diagnostics/loma_path_checks.hpp'), str(source / 'diagnostics/loma_path_checks.hpp'))
    command = ['g++','-std=c++17','-O2','-fopenmp',str((source / 'diagnostics/check_interface_directional.cpp').relative_to(ROOT)),
               '-lstdc++fs','-o',str((build / 'check').relative_to(ROOT))]
    commands=[]
    env=dict(os.environ,TMPDIR=str(ROOT / 'tmp'),OMP_NUM_THREADS='1')
    def run(name, argv):
        start=time.monotonic()
        with (out / (name + '_stdout.log')).open('w') as a, (out / (name + '_stderr.log')).open('w') as b:
            code=subprocess.call(argv,cwd=str(ROOT),env=env,stdout=a,stderr=b)
        commands.append(dict(stage=name,argv=argv,return_code=code,elapsed_seconds=time.monotonic()-start))
        if code: raise RuntimeError(name+' failed; preserve output')
    run('compiler_version',['g++','--version'])
    run('compile',command)
    run('diagnostic',[str((build/'check').relative_to(ROOT))]+[str((inputs/name).relative_to(ROOT)) for name in
        ('truth_grid.csv','native_case.csv','native_path.csv')]+[str(out.relative_to(ROOT))])
    result,secants=table(out/'directional.csv'),table(out/'secants.csv')
    checks=[]
    def check(name,ok,detail=None):
        checks.append(dict(name=name,passed=bool(ok),detail=detail))
    exact_error=max(abs(float(r['directional_8point'])-float(r['closed_form_directional'])) for r in result if r['closed_form_directional'])
    quad_error=max(abs(float(r['directional_8point'])-float(r['directional_32point'])) for r in result)
    check('invented_directional_closed_forms',exact_error<2e-14,exact_error)
    check('directional_quadrature_subdivision_control',quad_error<2e-12,quad_error)
    check('homogeneous_straight_zero_first_variation',all(abs(float(r['directional_8point']))<2e-14 for r in result if r['case']=='homogeneous_straight'))
    check('plateau_all_sampled_directions_nonnegative',all(float(r['directional_8point'])>=-2e-14 for r in result if r['case']=='fast_plateau_interface'))
    check('cusp_maximum_has_both_signed_guide_descents',all(float(r['directional_8point'])<0 for r in result
        if r['case']=='cusp_maximum_interface' and r['direction'] in ('guide_positive_translation','guide_negative_translation')))
    native=[r for r in result if r['case'].startswith('native_')]
    check('native_original_flags_and_IDs_unchanged',all(r[k]==case[k] for r in native for k in identities+['original_converged','original_updates']))
    check('native_frozen_chosen_gradient_matches',all(abs(float(r['chosen_gradient_norm'])-float(original['raw_gradient']))<1e-13 for r in native))
    witnesses=[]
    for row in native:
        d=float(row['directional_8point'])
        probes=[r for r in secants if r['case']==row['case'] and r['direction']==row['direction']]
        decreasing=[r for r in probes if r['forward_valid']=='1' and float(r['forward_exact_change'])<0]
        both=[r for r in decreasing if float(r['production_forward_change'])<0]
        witnesses.append(dict(direction=row['direction'],directional_slope_s_per_km=d,
            exact_action_decreasing_steps_km=[float(r['step_km']) for r in decreasing],
            exact_and_production_action_decreasing_steps_km=[float(r['step_km']) for r in both],
            exact_action_maximum_decrease_s=max([-float(r['forward_exact_change']) for r in decreasing] or [0.]),
            negative_directional_with_independent_decrease=d<0 and bool(decreasing)))
    summary=dict(status='passed' if all(r['passed'] for r in checks) else 'failed_checks_preserved',
        scope='Directional diagnostics only; no optimizer, production path, stopping flag or tolerance change',
        checks=checks,commands=commands,native_case=case,native_witnesses=witnesses,
        declared_component_controls=dict(closed_form_tolerance_s_per_km=2e-14,quadrature_subdivision_tolerance_s_per_km=2e-12),
        source_sha256={str(p.relative_to(source)):sha(p) for p in source.rglob('*') if p.is_file()},
        input_sha256={str((previous/name).relative_to(ROOT)):sha(previous/name) for name in
                      ('summary.json','packaging.json','cases.csv','results.csv','paths.csv','inputs/truth_grid.csv')},
        binary_sha256=sha(build/'check'),
        output_sha256={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()},
        limitations=['A negative feasible directional derivative establishes descent; nonnegative finitely many probes cannot certify full stationarity.',
          'Long-double exact segment formulas and first variations are floating-point evaluations, not interval certificates.',
          'This does not repair or validate optimized endpoint/model derivatives, and does not relabel the retained false local flag.',
          'The restricted metric vector is only another explicitly saved feasible diagnostic direction; it is not an optimizer or a physical constraint.'])
    (out/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:summary[k] for k in ('status','checks','native_witnesses')},indent=2))
    if summary['status']!='passed': raise SystemExit(1)


if __name__=='__main__': main()
