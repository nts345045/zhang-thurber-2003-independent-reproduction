#!/usr/bin/env python3
"""Read frozen tables and reconstruct their closed-form checks; no solver call."""
import csv
import hashlib
import json
import math
from pathlib import Path
import sys

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    with path.open(newline='') as f:
        return list(csv.DictReader(f))


def load(path):
    return json.loads(path.read_text())


def require(ok, message):
    if not ok:
        raise ValueError(message)


def norm(p):
    return math.sqrt(p[0]*p[0]+p[1]*p[1]+p[2]*p[2])


def main():
    s = load(OUT/'summary.json')
    require(s['status'] == 'completed_scalar_subdivision_diagnostic', 'Nonterminal diagnostic')
    pins = {'summary.json': sha(OUT/'summary.json')}
    pins.update(s['output_sha256'])
    for name,h in s['input_sha256'].items():
        require(sha(ROOT/name) == h, 'Changed original source/input: '+name)
    for name,h in pins.items():
        require(sha(OUT/name) == h, 'Changed artifact: '+name)
    original = load(OUT/'inputs/summary.json')
    observer = ROOT/'data/development/loma_initial_failure_24104_001'
    require(sha(OUT/'inputs/summary.json') == sha(observer/'summary.json'), 'Frozen observer summary differs')
    pins['inputs/summary.json'] = sha(OUT/'inputs/summary.json')
    require(all(c['return_code'] == 0 for c in s['commands']), 'Failed diagnostic command')
    require(sha(ROOT/s['commands'][1]['command'][0]) == s['binary_sha256'], 'Changed binary')
    require(sha(Path(original['compiler'])) == original['compiler_sha256'], 'Changed compiler')
    for name,h in original['source_sha256'].items():
        if name.startswith('src/'):
            require(sha(OUT/'source'/name) == h, 'Changed frozen numerical source')
    for name in ('check_boundary_endpoint.cpp','run_boundary_endpoint_check.py','observe_loma_initial_failure.py'):
        require(sha(OUT/'source/diagnostics'/name) == sha(ROOT/'diagnostics'/name), 'Maintained/frozen source mismatch')
    native = read(OUT/'inputs/identified_ray.csv')
    require(len(native) == 1 and native[0] == s['native_context'] == original['native_context'], 'Changed native context')
    sidecar = load(OUT/'subdivision.csv.identifiers.json')
    require(sidecar['native_context'] == native[0] and sidecar['original_observer_summary_sha256'] == pins['inputs/summary.json'], 'Detached native sidecar')
    require(sidecar['file'] == 'subdivision.csv' and sidecar['file_sha256'] == sha(OUT/'subdivision.csv') and
            sidecar['join_keys'] == ['run_id','observation_index'], 'Invalid numerical sidecar join')
    values = read(OUT/'subdivision.csv')
    require(values == s['results'] and [int(r['leading_subsegments']) for r in values] == [1,2,4,8,16], 'Native support changed')
    selected = min(original['results'],key=lambda r:float(r['time_s']))
    require(s['original_local_flag'] == selected['converged'] == native[0]['ray_converged'], 'Original flag changed')
    run = selected['run_id']
    require(all(r['run_id'] == run and r['observation_index'] == str(original['pair_index']) for r in values), 'Native pair mapping')
    paths = [r for r in read(OUT/'inputs/paths.csv') if r['run_id'] == run]
    require([int(r['node']) for r in paths] == list(range(len(paths))) and len(paths) == int(selected['path_nodes']), 'Frozen path incomplete')
    points = [[float(r[a]) for a in 'xyz'] for r in paths]
    grid = read(OUT/'inputs/initial_grid.csv')
    axes = [sorted(set(float(r[a]) for r in grid)) for a in 'xyz']
    profile = sorted(set((float(r['z']),float(r['v'])) for r in grid))
    require(len(profile) == len(axes[2]) and all(v>0 for z,v in profile), 'Not positive depth-only model')
    require(all(axes[k][0] <= p[k] <= axes[k][-1] for p in points for k in range(3)), 'Original path outside finite box')
    a,b=points[:2]
    require(a[2] == b[2] == axes[2][-1], 'Not an aligned bottom edge')
    e=[y-x for x,y in zip(a,b)];length=norm(e)
    speed=profile[-1][1]
    slope=-(speed-profile[-2][1])/(profile[-1][0]-profile[-2][0])/(speed*speed)
    require(length>0,'Collapsed leading edge')
    max_formula_error=0.0
    for r in values:
        n=int(r['leading_subsegments'])
        require(int(r['path_nodes']) == len(points)+n-1, 'Wrong subdivision path count')
        require(all(math.isfinite(float(v)) for k,v in r.items() if k not in ('run_id','observation_index')), 'Nonfinite scalar')
        require(float(r['original_leading_length_km']) == length, 'Original length mismatch')
        first=[a[k]+e[k]*(1.0/n) for k in range(3)] if n>1 else b
        newlength=norm([first[k]-a[k] for k in range(3)])
        require(float(r['new_leading_length_km']) == newlength, 'Binary first-subsegment length mismatch')
        require(float(r['slowness_depth_slope_s_per_km2']) == slope, 'Wrong depth slope')
        exact_formula=newlength*slope/2
        require(float(r['analytic_fixed_source_dz_s_per_km']) == exact_formula, 'Wrong fixed-edge formula')
        max_formula_error=max(max_formula_error,abs(float(r['fixed_inserted_source_dz'])-exact_formula))
        for axis in 'xyz':
            require(r['original_source_d'+axis] == selected['source_d'+axis], 'Source derivative differs from observer')
        require(float(r['action_minus_original_s']) == float(r['action_s'])-float(values[0]['action_s']), 'Action difference mismatch')
        err=max(abs(float(r['tied_inserted_source_d'+axis])-float(r['original_source_d'+axis])) for axis in 'xyz')
        require(err == float(r['maximum_tied_minus_original_source_error_s_per_km']), 'Tied contraction error mismatch')
        tangent=[x/length for x in e];collinear=0.0
        for j in range(1,n):
            p=[a[k]+e[k]*(j/n) for k in range(3)];d=[p[k]-a[k] for k in range(3)]
            along=d[0]*tangent[0]+d[1]*tangent[1]+d[2]*tangent[2]
            collinear=max(collinear,norm([d[k]-tangent[k]*along for k in range(3)]))
        require(collinear == float(r['maximum_inserted_collinearity_error_km']), 'Binary collinearity mismatch')
    require(float(values[0]['action_s']) == float(selected['time_s']), 'Original action differs from observer')
    invented=read(OUT/'invented/result.csv');checks=[]
    require([int(r['leading_subsegments']) for r in invented] == [1,2,4,8,16], 'Incomplete invented sample')
    for r in invented:
        n=int(r['leading_subsegments'])
        for field,exact in [('action_s',1/6),('fixed_inserted_source_dx',-1/6),
                            ('fixed_inserted_source_dz',-1/(72*n)),('tied_inserted_source_dz',-1/72),
                            ('analytic_fixed_source_dz_s_per_km',-1/(72*n))]:
            error=abs(float(r[field])-exact);allowance=64*sys.float_info.epsilon*abs(exact)
            checks.append(dict(subsegments=n,field=field,error=error,arithmetic_allowance=allowance,passed=error<=allowance))
    require(checks == s['invented_checks'] and len(checks) == 25 and all(c['passed'] for c in checks), 'Invented controls do not reproduce')
    for name,h in pins.items(): require(sha(OUT/name)==h,'Artifact changed during review')
    for name,h in s['input_sha256'].items(): require(sha(ROOT/name)==h,'Input changed during review')
    review=dict(status='passed_read_only_evidence_review',material_issue_found=False,
        review_scope='Source/math and saved-table readback; no compilation, ray tracing, path_eval, optimizer or inversion invoked.',
        checker_sha256=sha(Path(__file__)),summary_sha256=pins['summary.json'],
        input_hashes_verified=len(s['input_sha256']),output_hashes_verified=len(s['output_sha256']),
        additional_copied_observer_summary_hash_verified=pins['inputs/summary.json'],invented_checks_verified=len(checks),
        native_subdivisions_verified=len(values),native_context_fields_all_match=True,original_flags_unchanged=True,
        native_identifiers={k:native[0][k] for k in ('event','station','source_event_resource_id','source_origin_resource_id',
                           'receiver_channel_seed_id','receiver_channel_fdsn_source_id','receiver_metadata_epoch_start','receiver_metadata_epoch_end')},
        native_leading_length_km=length,native_slowness_depth_slope_s_per_km2=slope,
        maximum_saved_fixed_formula_error_s_per_km=max_formula_error,
        maximum_saved_tied_original_error_s_per_km=max(float(r['maximum_tied_minus_original_source_error_s_per_km']) for r in values),
        maximum_binary_collinearity_error_km=max(float(r['maximum_inserted_collinearity_error_km']) for r in values),
        maximum_native_action_change_s=max(abs(float(r['action_minus_original_s'])) for r in values),
        formula_review='For a horizontal bottom edge, normal length variation vanishes and its fixed-knot source partial is L*sprime/2. Affinely tied inserted points contribute raw gradient weights1-j/n by chain rule; projecting those gradients would alter the variation family.',
        limitations=['Saved flags refer to the original observer; no new convergence claim is assigned to subdivided paths.',
                     'The bottom-face normal partial is interpreted from the admissible interior side.',
                     'This establishes dependence on the endpoint variation family, not a replacement optimized travel-time derivative.',
                     'Tied raw gradients are contracted in the reviewed frozen source; individual inserted gradients are not separately exported.'],
        pinned_artifact_sha256=pins)
    with (OUT/'review.json').open('x') as f:json.dump(review,f,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps({k:v for k,v in review.items() if k not in ('pinned_artifact_sha256','native_identifiers')},indent=2))


if __name__=='__main__':
    main()
