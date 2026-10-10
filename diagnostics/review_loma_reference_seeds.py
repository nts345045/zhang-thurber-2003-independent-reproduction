#!/usr/bin/env python3
"""Review frozen exact-seed outputs without tracing or changing convergence flags."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def table(path):
    with path.open() as stream:
        reader=csv.DictReader(stream)
        for row in reader:
            if None in row or None in row.values():raise ValueError('Incomplete CSV record')
            yield row

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',required=True)
    args=parser.parse_args()
    base=(ROOT/args.input).resolve();base.relative_to(ROOT)
    manifest=json.loads((base/'summary.json').read_text())
    if manifest['status']!='completed_with_original_flags_preserved':raise ValueError('Require terminal diagnostic')
    for name,expected in manifest['output_sha256'].items():
        if sha(base/name)!=expected:raise ValueError('Frozen artifact changed: '+name)
    cases={r['case_id']:r for r in table(base/'cases.csv')}
    ids=['diagnostic_row','event','station','source_event_resource_id','source_origin_resource_id',
         'receiver_channel_seed_id','receiver_channel_fdsn_source_id','receiver_metadata_epoch_start','receiver_metadata_epoch_end']
    stages=['analytic_seed_polygon','uniform_resampled_zero_updates','retained_seed_zero_updates',
            'uniform_resampled_optimized','retained_seed_optimized']
    values={}
    def native(row):
        case=cases[row['case_id']]
        if any(row[k]!=case[k] for k in ids):raise ValueError('Native identity mismatch')
        return case
    for row in table(base/'results.csv'):
        case=native(row);key=(row['case_id'],row['stage'])
        if key in values:raise ValueError('Duplicate stage')
        for k in ['time_s','exact_polygon_time_s','time_error_s','source_error_norm','projected_gradient']:
            if not math.isfinite(float(row[k])):raise ValueError('Nonfinite result')
        error=math.sqrt(sum((float(row['source_d'+k])-float(case['reference_source_d'+k]))**2 for k in 'xyz'))
        if abs(error-float(row['source_error_norm']))>1e-15:raise ValueError('Source norm mismatch')
        if float(row['time_s'])-float(case['reference_time_s'])!=float(row['time_error_s']):raise ValueError('Time error mismatch')
        values[key]=row
    if set(values)!={(k,s) for k in cases for s in stages}:raise ValueError('Incomplete stage inventory')
    paths={k:[] for k in values}
    for row in table(base/'paths.csv'):
        native(row);key=(row['case_id'],row['stage']);path=paths[key]
        if int(row['node'])!=len(path):raise ValueError('Nonconsecutive path')
        path.append([float(row[k]) for k in 'xyz'])
    for key,path in paths.items():
        case=cases[key[0]]
        if len(path)!=int(values[key]['path_nodes']):raise ValueError('Path count mismatch')
        if path[0]!=[float(case['source_'+k]) for k in 'xyz'] or path[-1]!=[float(case['receiver_'+k]) for k in 'xyz']:
            raise ValueError('Path endpoint identity mismatch')
    fd=list(table(base/'finite_difference.csv'))
    for row in fd:native(row)
    source_fd=max(abs(float(r['analytic_gradient'])-float(r['exact_central'])) for r in fd
                  if r['test']=='fixed_polygon_source' and float(r['step_km'])==1e-5)
    rows=[]
    for case_id,case in cases.items():
        row={k:case[k] for k in ids};row.update(case_id=case_id,spacing_km=float(case['spacing_km']))
        for stage in stages:
            result=values[(case_id,stage)]
            row[stage]={k:float(result[k]) for k in ['time_error_s','source_error_norm','projected_gradient','quadrature_error_s']}
            row[stage].update(updates=int(result['updates']),converged=bool(int(result['converged'])),
                exact_guide_nodes=int(result['exact_interface_nodes']),
                exact_velocity_kink_nodes={str(x):sum(p[0]==x for p in paths[(case_id,stage)]) for x in [0.,1.,5.,6.]})
        row['resampling_added_action_s']=float(values[(case_id,'uniform_resampled_zero_updates')]['time_s'])-float(values[(case_id,'analytic_seed_polygon')]['time_s'])
        row['coupled_guide_one_sided_checks']=[{k:float(r[k]) for k in ['step_km','analytic_gradient','exact_forward','exact_backward','exact_central']}
            for r in fd if r['case_id']==case_id and r['stage']=='analytic_seed_polygon' and r['test']=='coupled_exact_guide_nodes']
        rows.append(row)
    output=base/'review';output.mkdir(exist_ok=False)
    shutil.copyfile(str(Path(__file__).resolve()),str(output/'review_loma_reference_seeds.py'))
    review=dict(scope='Saved-output numerical and native-identity checks for four exact-guide branch controls; no new solver runs',
        original_summary_sha256=sha(base/'summary.json'),validated_original_hashes=len(manifest['output_sha256']),
        source_sha256=sha(output/'review_loma_reference_seeds.py'),cases=len(cases),stage_rows=len(values),
        path_rows=sum(map(len,paths.values())),finite_difference_rows=len(fd),native_identities_preserved=True,
        maximum_quadrature_vs_exact_polygon_error_s=max(abs(float(r['quadrature_error_s'])) for r in values.values()),
        maximum_fixed_polygon_source_central_fd_error_at_1e_minus5_km=source_fd,
        convergence_counts={s:sum(int(values[(k,s)]['converged']) for k in cases) for s in stages[-2:]},
        results=rows,limitations=manifest['limitations']+[
            'The exact-circle/guide reference is continuous; its chordal samples have a separate polygon discretization error.',
            'The C++ strict_interface_crossings field counts all x grid planes; review exact_velocity_kink_nodes counts only changes of velocity slope at x0,1,5,6km.',
            'The one-sided coupled perturbation tests one direction and does not prove full nonsmooth stationarity.',
            'Retaining knots only at initialization does not constrain their subsequent locations and is not a convergence repair.'])
    (output/'summary.json').write_text(json.dumps(review,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:review[k] for k in ['cases','stage_rows','path_rows','native_identities_preserved','maximum_quadrature_vs_exact_polygon_error_s','maximum_fixed_polygon_source_central_fd_error_at_1e_minus5_km','convergence_counts']},indent=2))

if __name__=='__main__':main()
