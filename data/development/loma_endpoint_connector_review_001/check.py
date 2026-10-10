#!/usr/bin/env python3
"""Read back the fixed native endpoint component without tracing a ray."""
import argparse
import csv
from decimal import Decimal as D, localcontext
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
CASE = ROOT/'data/development/loma_endpoint_connector_native_001'


def need(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def rows(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default=str(Path(__file__).with_name('review.json')))
    args=parser.parse_args()
    output=Path(args.output).resolve()
    output.relative_to(ROOT)
    need(not output.exists(), 'Fresh review output required')
    s=read(CASE/'summary.json')
    need(s['status']=='completed_static_component_original_flags_preserved', 'Incomplete static calculation')
    execution=read(CASE/'execution.json')
    need(execution['status']=='completed' and execution['return_code']==0 and
         execution['summary_sha256']==sha(CASE/'summary.json'), 'Execution binding changed')
    for name,digest in s['input_sha256'].items():
        need(sha(ROOT/name)==digest, 'Changed input: '+name)
    for name,digest in s['output_sha256'].items():
        need(sha(CASE/name)==digest, 'Changed output: '+name)
    for name,copy in s['frozen_input_mapping'].items():
        need(sha(CASE/copy)==s['input_sha256'][name], 'Changed frozen copy')
    identity=rows(CASE/'native_context.csv')
    need(identity==[s['native_context']] and len(identity[0])==199, 'Native context changed')
    for path in CASE.glob('*.identifiers.json'):
        side=read(path)
        data=CASE/path.name[:-len('.identifiers.json')]
        need(side['native_context']==identity[0] and side['file_sha256']==sha(data), 'Identifier attachment changed')
        need(side['context_sha256']==sha(CASE/'native_context.csv'), 'Identifier context binding changed')
    need((CASE/'exact_baseline_formulas.json.identifiers.json').exists(), 'Formula coordinates missing identifiers')
    formula=read(CASE/'exact_baseline_formulas.json')
    snapshot=CASE/'snapshot/data/development/loma_initial_failure_24104_001'
    points=[tuple(Q(float(r[a])) for a in 'xyz') for r in rows(CASE/'selected_path_vertices.csv')]
    need(len(points)==3 and [[str(v) for v in p] for p in points]==formula['point_coordinates_q'], 'Coordinate basis changed')
    grid=rows(snapshot/'inputs/initial_grid.csv')
    profile=sorted({(Q(float(r['z'])),Q(float(r['v']))) for r in grid})
    need(len(profile)==len({r['z'] for r in grid}), 'Not a depth-only grid')
    z0,v0=profile[-2]; B,V=profile[-1]
    slope=(V-v0)/(B-z0)
    need(B==Q(formula['bottom_depth_q']) and V==Q(formula['bottom_speed_q']) and slope>0 and
         slope==Q(formula['velocity_gradient_exact_q']), 'Exact last-layer model changed')
    need(all(p[2]==B for p in points) and all(a!=b for a,b in zip(points,points[1:])), 'Baseline guide geometry changed')
    need(formula['local_action_change_exact_q']=='0' and formula['critical_distance_exact_q']=='0', 'Baseline formula changed')
    helper=ROOT/'data/development/loma_candidate_support_review_001/check.py'
    spec=importlib.util.spec_from_file_location('independent_xyz_first_variation',str(helper))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    derivatives={r['role']:[D(r['d'+a]) for a in 'xyz'] for r in rows(CASE/'derivatives.csv')}
    edges=rows(CASE/'edges.csv')
    residuals={r['comparison']:r for r in rows(CASE/'stored_float_residuals.csv')}
    reference=rows(CASE/'selected_reference.csv')
    need(len(reference)==1 and reference[0]['pair_index']=='24104' and reference[0]['branch']=='bottom_boundary' and
         reference[0]['reference_valid']==reference[0]['reference_complete']=='1', 'Reference branch changed')
    precision=120
    with localcontext() as ctx:
        ctx.prec=precision
        # The original component uses the generic physical-xyz first variation,
        # independently written for arbitrary traversing depth-layer segments.
        first=module.physical_segment(points[0],points[1],profile)
        second=module.physical_segment(points[1],points[2],profile)
        connector_a=first[1][:2]+[D(0)]
        connector_b=first[2][:2]+[D(0)]
        expected={'old_first_edge_source':first[1], 'old_first_edge_x1':first[2],
                  'connector_source':connector_a, 'connector_x1':connector_b,
                  'unchanged_second_edge_x1':second[1],
                  'old_complete_x1':[a+b for a,b in zip(first[2],second[1])],
                  'new_complete_x1':[a+b for a,b in zip(connector_b,second[1])]}
        tolerance=D('1e-95')  # Readback of 100-digit displayed values, not a physical accuracy limit.
        differences=[]
        for role,vector in expected.items():
            differences.extend(abs(a-b) for a,b in zip(vector,derivatives[role]))
        need(max(differences)<tolerance, 'Independent component readback differs')
        need(all(abs(D(row['straight_action_s'])-edge[0])<tolerance for row,edge in zip(edges,(first,second))),
             'Independent segment action differs')
        need(D(edges[0]['straight_action_s'])==D(edges[0]['connector_action_s']) and
             edges[0]['connector_minus_straight_exact_q']=='0', 'Baseline action equality changed')
        need(expected['new_complete_x1'][2]==second[1][2]<0 and
             derivatives['connector_source'][2]==derivatives['connector_x1'][2]==0, 'Second-edge reaction omitted')
        saved_source=[module.dec(Q(float(s['original_result']['source_d'+a]))) for a in 'xyz']
        path=rows(CASE/'selected_path_vertices.csv')
        saved_x1=[module.dec(Q(float(path[1]['gradient_'+a]))) for a in 'xyz']
        saved_reference=[module.dec(Q(float(reference[0]['source_d'+a+'_s_per_km']))) for a in 'xyz']
        pairs=[('saved_source_minus_exact_straight',saved_source,first[1]),
               ('saved_x1_minus_exact_old_complete_x1',saved_x1,expected['old_complete_x1']),
               ('connector_source_minus_saved_reference',connector_a,saved_reference)]
        norm_readbacks={}
        for name,a,b in pairs:
            delta=[x-y for x,y in zip(a,b)]
            norm=sum(v*v for v in delta).sqrt()
            need(abs(norm-D(residuals[name]['euclidean_norm']))<tolerance, 'Stored-float residual norm differs')
            norm_readbacks[name]=str(norm)
    need(s['original_local_convergence_flag']==s['original_result']['converged']=='1' and
         s['new_whole_ray_time_evaluated'] is False and s['no_new_forward_or_accuracy_flags'] is True,
         'Original/new result scope changed')
    result=dict(status='passed', reviewer='root',reviewed_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
        summary_sha256=sha(CASE/'summary.json'),execution_sha256=sha(CASE/'execution.json'),
        checker_sha256=sha(Path(__file__).resolve()),independent_xyz_helper_sha256=sha(helper),
        formula_identity_sidecar_sha256=sha(CASE/'exact_baseline_formulas.json.identifiers.json'),
        verified_inputs=len(s['input_sha256']), verified_outputs=len(s['output_sha256']),
        native_context_fields=199,independent_precision=precision,display_readback_allowance=str(tolerance),
        largest_display_component_difference=str(max(differences)),stored_float_residual_norms=norm_readbacks,
        findings=['Exact binary64 grid values determine the rational affine slope; no rounded replacement model is used.',
                  'The horizontal constrained guide has the same local mathematical action and zero inward normal endpoint limits.',
                  'Independent xyz first variations reproduce both straight edges and all source/first-vertex component accounting.',
                  'The unchanged second edge retains its nonzero full first-vertex normal contribution.',
                  'The standalone formula coordinates now have a complete identifier sidecar.'],
        limitations=['The Decimal readback verifies displayed values; it is not a rigorous interval calculation.',
                     'No whole-ray envelope, perturbed action, general-trilinear connector, nodal Jacobian, stopping or accuracy flag is certified.',
                     'The separately attached metadata sidecar is outside the original numerical-summary inventory and is pinned here.'])
    output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(output=str(output.relative_to(ROOT)),sha256=sha(output),residuals=norm_readbacks),indent=2))


if __name__=='__main__':
    main()
