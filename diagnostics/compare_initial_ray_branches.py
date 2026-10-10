#!/usr/bin/env python3
"""Compare one completed frozen ray diagnosis with all continuous 1D branches."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys

import numpy as np
from first_arrival_1d_reference import enumerate_arrivals, sample_path

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def table(path):
    with path.open() as stream:
        reader = csv.DictReader(stream)
        rows = list(reader)
    if any(None in row or None in row.values() for row in rows):
        raise ValueError('Incomplete CSV: '+str(path))
    return reader.fieldnames, rows


def exact_action(points, profile):
    """Independent reciprocal-affine line integral, split at every z plane."""
    D = np.longdouble
    terms = []
    for aa, bb in zip(points, points[1:]):
        a, b = [np.array(point, dtype=D) for point in (aa, bb)]
        delta = b-a
        length = np.sqrt(np.dot(delta, delta))
        cuts = [D(0), D(1)]
        if delta[2] != 0:
            cuts += [(D(z)-a[2])/delta[2] for z, v in profile
                     if min(a[2], b[2]) < D(z) < max(a[2], b[2])]
        cuts.sort()
        for lo, hi in zip(cuts, cuts[1:]):
            mid = a[2]+delta[2]*(lo+hi)/2
            index = next((i for i in range(len(profile)-1)
                          if D(profile[i][0]) <= mid <= D(profile[i+1][0])), None)
            if index is None:
                raise ValueError('Saved path outside finite normal domain')
            z0, v0 = map(D, profile[index]); z1, v1 = map(D, profile[index+1])
            gradient = (v1-v0)/(z1-z0)
            va = v0+gradient*(a[2]+lo*delta[2]-z0)
            dv = gradient*delta[2]*(hi-lo)
            average = np.log1p(dv/va)/dv if dv != 0 else 1/va
            terms.append(length*(hi-lo)*average)
    return sum(terms, D(0))


def write(path, records):
    columns = list(dict.fromkeys(k for row in records for k in row))
    with path.open('x', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, lineterminator='\n')
        writer.writeheader(); writer.writerows(records)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--diagnosis', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    diagnosis, out = [(ROOT/value).resolve() for value in (args.diagnosis, args.output)]
    for path in (diagnosis, out):
        path.relative_to(ROOT)
    if out.exists():
        parser.error('Preserve prior evidence; choose a fresh output directory')
    run = json.loads((diagnosis/'summary.json').read_text())
    if run['status'] != 'completed_with_original_flags_preserved':
        raise ValueError('The frozen diagnosis has not completed')
    for name, expected in run['output_sha256'].items():
        if sha(diagnosis/name) != expected:
            raise ValueError('Frozen output changed: '+name)
    field_spacings = {r['run_id']:float(r['field_spacing_km']) for r in run['results']}
    identity = table(diagnosis/'identified_ray.csv')[1]
    if len(identity) != 1:
        raise ValueError('Expected one identified ray')
    identity = identity[0]
    grid = table(diagnosis/'initial_grid.csv')[1]
    profile = sorted({(float(row['z']), float(row['v'])) for row in grid})
    if len(profile) != len({z for z, v in profile}):
        raise ValueError('Require a horizontally uniform initial velocity')
    depths, speeds = [list(v) for v in zip(*profile)]
    source, receiver = [[float(identity[prefix+axis+'_km']) for axis in 'xyz']
                        for prefix in ('source_', 'receiver_')]
    reference = enumerate_arrivals(depths, speeds, source, receiver)
    if not reference['complete'] or not reference['reference_valid']:
        raise ValueError('Independent branch enumeration is incomplete or inaccurate')
    first = reference['first_arrival']
    controls = []
    for label, points, layers, expected in [
        ('constant',[[0.,0.,0.],[3.,4.,0.]],[[-1.,5.],[2.,5.]],1.),
        ('affine_vertical',[[0.,0.,0.],[0.,0.,1.]],[[-1.,4.],[2.,7.]],math.log(6/5)),
        ('crossing',[[0.,0.,-.5],[1.,0.,1.5]],[[-1.,6.],[0.,6.],[1.,4.],[2.,4.]],math.sqrt(5)/2*(.5/6+math.log(6/4)/2+.5/4))]:
        error=abs(float(exact_action(points,layers))-expected)
        reverse_error=abs(float(exact_action(list(reversed(points)),layers))-expected)
        controls.append(dict(name=label,error_s=error,reverse_error_s=reverse_error))
        if max(error,reverse_error)>1e-14:
            raise AssertionError('Independent exact-action control failed: '+label)
    native_keys = ['observation_index', 'event_i_resource_id', 'origin_i_resource_id',
                   'arrival_i_resource_id', 'pick_i_resource_id', 'channel_seed_id',
                   'channel_fdsn_source_id', 'metadata_epoch_start', 'metadata_epoch_end',
                   'pick_i_source_sha256', 'channel_source_sha256']
    native = {key:identity[key] for key in native_keys}
    bounds = {axis:[min(float(r[axis]) for r in grid), max(float(r[axis]) for r in grid)] for axis in 'xyz'}
    analytic_paths=[]
    for index, candidate in enumerate(reference['candidates']):
        points = sample_path(depths, speeds, source, receiver, candidate, spacing_km=.03125)
        if points[0] != source or points[-1] != receiver or any(
                not bounds[axis][0] <= p[d] <= bounds[axis][1] for p in points for d, axis in enumerate('xyz')):
            raise ValueError('Reference path endpoint/domain mismatch')
        for n, point in enumerate(points):
            analytic_paths.append(dict(native, branch_index=index, node=n,
                x_km=point[0], y_km=point[1], z_km=point[2]))
    rows, derivatives, histories, inputs = [], [], [], {}
    for directory in sorted(p for p in diagnosis.glob('spacing*') if p.is_dir()):
        result_rows = table(directory/'results.csv')[1]
        paths = table(directory/'paths.csv')[1]
        history = table(directory/'history.csv')[1]
        for name in ['results.csv','paths.csv','history.csv','path_gradient_checks.csv']:
            inputs[str((directory/name).relative_to(ROOT))] = sha(directory/name)
        for result in result_rows:
            if result['logged_matches_unobserved_variant'] != '1':
                raise ValueError('Observed trace differs from frozen production trace')
            points = [[float(row[axis]) for axis in 'xyz'] for row in paths if row['run_id'] == result['run_id']]
            if points[0] != source or points[-1] != receiver:
                raise ValueError('Production path endpoints differ from native geometry')
            time = float(result['time_s'])
            gradient = [float(result['source_d'+axis]) for axis in 'xyz']
            deepest = max(point[2] for point in points)
            closest = min(range(len(reference['candidates'])), key=lambda i: abs(
                (reference['candidates'][i]['turning_depth_km'] if reference['candidates'][i]['turning_depth_km'] is not None else max(source[2],receiver[2]))-deepest))
            branch = reference['candidates'][closest]
            action = exact_action(points, profile)
            row = dict(identity);row.update(result)
            row.update(field_spacing_km=field_spacings[result['run_id']], path_min_z_km=min(point[2] for point in points), path_max_z_km=deepest,
                       nearest_turning_depth_branch_index=closest, nearest_branch_kind=branch['kind'],
                       nearest_branch_turning_depth_km=branch['turning_depth_km'],
                       time_minus_nearest_branch_s=time-branch['time_s'], time_minus_first_arrival_s=time-first['time_s'],
                       source_norm_error_nearest_branch_s_per_km=math.sqrt(sum((a-b)**2 for a,b in zip(gradient,branch['source_derivative_s_per_km']))),
                       source_norm_error_first_arrival_s_per_km=math.sqrt(sum((a-b)**2 for a,b in zip(gradient,first['source_derivative_s_per_km']))),
                       quadrature_minus_exact_saved_path_s=float(np.longdouble(time)-action))
            rows.append(row)
            for axis in range(3):
                for h in [1e-4,1e-5,1e-6]:
                    plus, minus = [list(map(list, points)) for unused in range(2)]
                    plus[0][axis]+=h;minus[0][axis]-=h
                    numerical=float((exact_action(plus,profile)-exact_action(minus,profile))/(2*np.longdouble(h)))
                    derivatives.append(dict(native,run_id=result['run_id'],axis='xyz'[axis],step_km=h,
                        source_gradient_s_per_km=gradient[axis],exact_fixed_path_fd_s_per_km=numerical,
                        signed_error_s_per_km=numerical-gradient[axis]))
            hh=[r for r in history if r['run_id']==result['run_id']]
            accepted=[r for r in hh if r['phase']=='accepted']
            histories.append(dict(native,run_id=result['run_id'],phases={phase:sum(r['phase']==phase for r in hh) for phase in sorted({r['phase'] for r in hh})},
                last_accepted_updates=accepted[-1]['updates'] if accepted else None,
                final_projected_gradient_s_per_km=float(hh[-1]['projected_gradient']),
                final_normal_gradient_s_per_km=float(hh[-1]['normal_gradient_norm']),
                last100_action_drop_s=float(accepted[max(0,len(accepted)-101)]['time_s'])-float(accepted[-1]['time_s']) if accepted else None))
    out.mkdir(parents=True)
    write(out/'identified_branch_comparison.csv',rows)
    write(out/'exact_source_gradient_checks.csv',derivatives)
    write(out/'reference_paths.csv',analytic_paths)
    shutil.copyfile(str(diagnosis/'identified_ray.csv'),str(out/'identified_ray.csv'))
    (out/'source').mkdir()
    source_files=[Path(__file__).resolve(),ROOT/'diagnostics/first_arrival_1d_reference.py']
    for path in source_files:
        shutil.copyfile(str(path),str(out/'source'/path.name))
    inputs.update({str((diagnosis/name).relative_to(ROOT)):sha(diagnosis/name) for name in ['summary.json','identified_ray.csv','initial_grid.csv']})
    report=dict(scope='One identified frozen Hayward initial ray; all continuous monotone 1D branches, exact saved-polygon action and fixed-path endpoint gradients',
        command=['python3']+sys.argv,native_identity=native,source_xyz_km=source,receiver_xyz_km=receiver,
        profile_depth_velocity_km_km_s=profile,finite_domain_km=bounds,reference=reference,
        production_source_sha256=run['source_sha256'],production_diagnostic_binary_sha256=run['binary_sha256'],
        exact_action_controls=controls,exact_observer_parity_cases=len(rows),saved_initial_ray_reproduced=run['selected_initial_ray_matches'],
        maximum_absolute_quadrature_minus_exact_saved_path_s=max(abs(r['quadrature_minus_exact_saved_path_s']) for r in rows),
        maximum_exact_fixed_path_source_fd_error_at1e_minus5_s_per_km=max(abs(r['signed_error_s_per_km']) for r in derivatives if r['step_km']==1e-5),
        cases=[{key:r[key] for key in ['run_id','initialization','path_spacing_km','max_updates','updates','converged','time_s','projected_gradient','path_max_z_km','nearest_turning_depth_branch_index','time_minus_nearest_branch_s','time_minus_first_arrival_s','source_norm_error_nearest_branch_s_per_km','source_norm_error_first_arrival_s_per_km','quadrature_minus_exact_saved_path_s']} for r in rows],
        histories=histories,input_sha256=inputs,source_sha256={str(path.relative_to(ROOT)):sha(path) for path in source_files},
        limitations=['Nearest branch by path turning depth is a diagnostic association, checked independently using time and source derivative; it does not substitute one branch for another.',
                     'Exact action/gradient checks concern the retained polygon, not the globally optimized ray.',
                     'Branch enumeration and distance closure are certified as recorded; minimum-time ranking uses ordinary floating-point arithmetic.',
                     'No observation, cohort, production source, inversion or original frozen diagnostic was changed.'])
    report['output_sha256']={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()}
    (out/'summary.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({key:report[key] for key in ['exact_observer_parity_cases','maximum_absolute_quadrature_minus_exact_saved_path_s','maximum_exact_fixed_path_source_fd_error_at1e_minus5_s_per_km','cases']},indent=2))


if __name__=='__main__':
    main()
