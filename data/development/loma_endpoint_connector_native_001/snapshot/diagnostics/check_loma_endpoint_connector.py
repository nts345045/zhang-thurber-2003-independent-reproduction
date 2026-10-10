#!/usr/bin/env python3
"""Static first-edge connector comparison on the frozen pair-24104 polygon.

No path perturbation, quadrature, ray solver, optimization or flag change.
At the horizontal baseline the exact formulas use the stored binary64 grid
values as rational numbers. Decimal square roots provide displayed values,
not outward intervals. The general affine connector is not invoked with a
rounded replacement for the exact grid-derived gradient.
"""
import argparse
import csv
import datetime
from decimal import Decimal as D, localcontext
from fractions import Fraction as Q
import gzip
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
OBS = Path('data/development/loma_initial_failure_24104_001')
CONTROLS = Path('data/development/endpoint_connector_controls_001')
PROPOSAL = Path('data/development/loma_endpoint_connector_proposal_001')
ACCURACY = Path('data/development/loma_lom_initial_accuracy_001')
RUN = 'fmm_0.031250_1000'
PAIR = '24104'
PINS = {
    str(OBS / 'summary.json'): '05ee19cbfb2a8619e9613084354fa5d66f158794caa1b0159486171bd633c573',
    str(OBS / 'review.json'): '4d0fead4b92bff7504b2eb702d7d8b4450a1abafd7e03508d52a759d2c8ec3db',
    str(CONTROLS / 'summary.json'): '67c848b3c880a5492b17432afab6efd1be3f2571ee8202536382418799fb1497',
    str(CONTROLS / 'review.json'): '25d06bb30e02ff4af85829d4bf1e0406373b8ab7eabf3bab34f1672f4df842d7',
    str(ACCURACY / 'summary.json'): '72ed25dbde4bc14b1e0967f6a1880ff396683735c723b41f633e081a085fe6bb',
}


def need(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def load(path):
    return json.loads(path.read_text())


def records(path):
    opener = gzip.open if path.suffix == '.gz' else open
    with opener(str(path), 'rt', newline='') as f:
        return list(csv.DictReader(f))


def binary(text):
    value = float(text)
    need(math.isfinite(value), 'Nonfinite modeled input')
    return Q.from_float(value)


def decimal(q):
    return D(q.numerator) / D(q.denominator)


def save(path, value):
    with path.open('x') as f:
        json.dump(value, f, indent=2, sort_keys=True, allow_nan=False)
        f.write('\n')


def table(path, rows):
    with path.open('x', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def values(points, speed, slope, precision):
    """Closed horizontal-edge formulas with exact rational geometric inputs."""
    with localcontext() as ctx:
        ctx.prec = precision
        v, sp = decimal(speed), decimal(-slope / (speed * speed))
        edges = []
        for a, b in zip(points, points[1:]):
            delta = [y - x for x, y in zip(a, b)]
            squared = sum((x*x for x in delta), Q(0))
            length = decimal(squared).sqrt()
            tangent = [decimal(x) / length for x in delta]
            ga = [-tangent[0] / v, -tangent[1] / v, length * sp / 2]
            gb = [tangent[0] / v, tangent[1] / v, length * sp / 2]
            edges.append(dict(length=length, action=length / v, ga=ga, gb=gb))
        # The same mathematical L/v is shared; no subtraction of rounded actions
        # is used to prove equality. The connector is the straight bottom guide.
        connector_ga = [edges[0]['ga'][0], edges[0]['ga'][1], D(0)]
        connector_gb = [edges[0]['gb'][0], edges[0]['gb'][1], D(0)]
        old_x1 = [x+y for x, y in zip(edges[0]['gb'], edges[1]['ga'])]
        new_x1 = [x+y for x, y in zip(connector_gb, edges[1]['ga'])]
        return dict(edges=edges, connector_action=edges[0]['action'],
                    connector_ga=connector_ga, connector_gb=connector_gb,
                    old_x1=old_x1, new_x1=new_x1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    out = (ROOT / args.output).resolve()
    out.relative_to(ROOT)
    need(not out.exists(), 'Fresh output directory required')
    for raw in (OBS, CONTROLS, PROPOSAL, ACCURACY):
        base = (ROOT / raw).resolve()
        need(out != base and out not in base.parents and base not in out.parents, 'Output overlaps frozen inputs')
    pins = dict(PINS)
    for name, digest in pins.items():
        need(sha(ROOT / name) == digest, 'Changed release pin: ' + name)
    obs, obs_review = load(ROOT / OBS / 'summary.json'), load(ROOT / OBS / 'review.json')
    controls, control_review = load(ROOT / CONTROLS / 'summary.json'), load(ROOT / CONTROLS / 'review.json')
    accuracy = load(ROOT / ACCURACY / 'summary.json')
    need(obs['status'] == 'completed_with_original_flags_preserved' and
         obs_review['status'] == 'passed_saved_evidence_review' and
         obs_review['summary_sha256'] == pins[str(OBS/'summary.json')], 'Observer review is incomplete')
    need(controls['status'] == 'passed' and controls['passing_checks'] == controls['total_checks'] == 304 and
         control_review['status'] == 'passed' and control_review['summary_sha256'] == pins[str(CONTROLS/'summary.json')],
         'Connector controls/review incomplete')
    for name, digest in obs['output_sha256'].items():
        need(sha(ROOT / OBS / name) == digest, 'Changed observer artifact: ' + name)
    for name, digest in controls['input_sha256'].items():
        need(sha(ROOT / name) == digest, 'Changed connector input: ' + name)
    for name, digest in controls['artifact_sha256'].items():
        need(sha(ROOT / CONTROLS / name) == digest, 'Changed control artifact: ' + name)
    obs_names = ['identified_ray.csv', 'paths.csv', 'paths.csv.identifiers.json', 'results.csv',
                 'results.csv.identifiers.json', 'inputs/initial_grid.csv', 'inputs/initial_events.csv',
                 'inputs/stations.csv']
    for name in obs_names:
        pins[str(OBS/name)] = obs['output_sha256'][name]
    for name, digest in obs['source_sha256'].items():
        pins[str(OBS/'source'/name)] = digest
    for name, digest in controls['artifact_sha256'].items():
        pins[str(CONTROLS/name)] = digest
    for name in ['proposal.md', 'native_saved_path_plan.md', 'provenance.json']:
        pins[str(PROPOSAL/name)] = sha(ROOT/PROPOSAL/name)
    for name in ['inputs/reference/references.csv.gz', 'inputs/reference/summary.json',
                 'inputs/reference/review.json', 'inputs/reference/independent_review.json']:
        pins[str(ACCURACY/name)] = accuracy['output_sha256'][name]
    pins[str(Path(__file__).resolve().relative_to(ROOT))] = sha(Path(__file__).resolve())
    for name, digest in pins.items():
        need(sha(ROOT/name) == digest, 'Changed concrete input: ' + name)

    out.mkdir()
    started = datetime.datetime.utcnow().isoformat() + 'Z'
    save(out/'started.json', dict(status='started_static_component', started_utc=started, input_sha256=pins))
    # Preserve all small input files. The full reference table stays in its
    # existing immutable package; the complete selected row is copied below.
    mapping = {}
    for name in pins:
        if name.endswith('references.csv.gz'):
            continue
        target = out/'snapshot'/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(str(ROOT/name), str(target))
        need(sha(target) == pins[name], 'Frozen copy mismatch')
        mapping[name] = str(target.relative_to(out))
    context_rows = records(out/'snapshot'/OBS/'identified_ray.csv')
    need(len(context_rows) == 1, 'Expected one complete native context')
    context = context_rows[0]
    need(len(context) == 199 and context == obs['native_context'] and context['observation_index'] == PAIR,
         'Native context/identity mismatch')
    results = records(out/'snapshot'/OBS/'results.csv')
    selected = [r for r in results if r['run_id'] == RUN and r['observation_index'] == PAIR]
    need(len(selected) == 1, 'Selected observer result missing/duplicated')
    selected = selected[0]
    paths = records(out/'snapshot'/OBS/'paths.csv')
    path = [r for r in paths if r['run_id'] == RUN and r['observation_index'] == PAIR]
    need(len(path) == int(selected['path_nodes']) and all(int(r['node']) == i for i, r in enumerate(path)),
         'Selected path inventory mismatch')
    for name in ['paths.csv', 'results.csv']:
        side = load(out/'snapshot'/OBS/(name+'.identifiers.json'))
        need(side['native_context'] == context and side['join_value'] == PAIR and
             side['file_sha256'] == pins[str(OBS/name)], 'Native sidecar mismatch')
    events, stations = (records(out/'snapshot'/OBS/'inputs'/name) for name in ['initial_events.csv', 'stations.csv'])
    event, station = events[int(context['event'])], stations[int(context['station'])]
    for prefix, row in [('native_source_', event), ('native_receiver_', station)]:
        need(all(context[prefix+k] == v for k, v in row.items()), 'Complete native table join mismatch')
    need(int(PAIR) == int(context['event'])*len(stations)+int(context['station']), 'Pair index mismatch')
    points = [[binary(r[a]) for a in 'xyz'] for r in path[:3]]
    need(points[0] == [binary(event[a]) for a in 'xyz'], 'Initial source endpoint changed')
    need([binary(path[-1][a]) for a in 'xyz'] == [binary(station[a]) for a in 'xyz'], 'Receiver endpoint changed')
    grid = records(out/'snapshot'/OBS/'inputs/initial_grid.csv')
    axes = [sorted(set(binary(r[a]) for r in grid)) for a in 'xyz']
    node_values = {(binary(r['x']), binary(r['y']), binary(r['z'])): binary(r['v']) for r in grid}
    need(len(node_values) == len(grid) == len(axes[0])*len(axes[1])*len(axes[2]), 'Grid nodes incomplete/duplicated')
    need(all((x,y,z) in node_values for x in axes[0] for y in axes[1] for z in axes[2]), 'Grid lattice incomplete')
    bottom, lower = axes[2][-1], axes[2][-2]
    profile = {}
    for z in (lower, bottom):
        speeds = {node_values[x,y,z] for x in axes[0] for y in axes[1]}
        need(len(speeds) == 1 and min(speeds) > 0, 'Last layer is not depth-only positive speed')
        profile[z] = speeds.pop()
    speed = profile[bottom]
    slope = (speed-profile[lower])/(bottom-lower)
    need(slope > 0, 'This roster requires increasing last-layer speed')
    need(all(p[2] == bottom for p in points), 'Source/x1/x2 not exactly on bottom')
    all_points = [[binary(r[a]) for a in 'xyz'] for r in path]
    need(all(all(axis[0] <= p[a] <= axis[-1] for a, axis in enumerate(axes)) for p in all_points), 'Saved path leaves box')
    need(all(sum(((b-a)**2 for a,b in zip(p,q)),Q(0)) > 0 for p,q in zip(all_points,all_points[1:])),
         'Saved path has a zero-length edge')
    reference_rows = []
    with gzip.open(str(ROOT/ACCURACY/'inputs/reference/references.csv.gz'), 'rt', newline='') as f:
        for row in csv.DictReader(f):
            if row['pair_index'] == PAIR:
                reference_rows.append(row)
    need(len(reference_rows) == 1, 'Reference pair missing/duplicated')
    reference = reference_rows[0]
    need(reference['reference_valid'] == reference['reference_complete'] == '1' and
         reference['near_tie_count'] == '1' and reference['branch'] == 'bottom_boundary', 'Reference ineligible')
    for prefix, row in [('source_', event), ('receiver_', station)]:
        need(all(reference[prefix+k] == v for k,v in row.items()), 'Reference native/geometry mismatch')

    data = {p: values(points,speed,slope,p) for p in (80,100)}
    detail = data[100]
    def textvec(v):
        return [str(x) for x in v]
    edge_rows = []
    for i in range(2):
        squared = sum(((b-a)**2 for a,b in zip(points[i],points[i+1])),Q(0))
        e = detail['edges'][i]
        row = dict(observation_index=PAIR, run_id=RUN, edge=i, from_node=i, to_node=i+1,
                   squared_length_exact_q=str(squared), length_km=str(e['length']),
                   straight_action_s=str(e['action']), connector_action_s=str(detail['connector_action']) if i==0 else '',
                   connector_minus_straight_exact_q='0' if i==0 else '',
                   connector_kind='positive_bottom_guide' if i==0 else 'unchanged_straight')
        for end,vector in [('source',e['ga']),('receiver',e['gb'])]:
            row.update({end+'_d'+a:str(v) for a,v in zip('xyz',vector)})
        edge_rows.append(row)
    table(out/'edges.csv',edge_rows)
    vectors = [('old_first_edge_source',detail['edges'][0]['ga']),('old_first_edge_x1',detail['edges'][0]['gb']),
               ('connector_source',detail['connector_ga']),('connector_x1',detail['connector_gb']),
               ('unchanged_second_edge_x1',detail['edges'][1]['ga']),('old_complete_x1',detail['old_x1']),
               ('new_complete_x1',detail['new_x1'])]
    with localcontext() as ctx:
        ctx.prec=100
        saved_source=[decimal(binary(selected['source_d'+a])) for a in 'xyz']
        saved_x1=[decimal(binary(path[1]['gradient_'+a])) for a in 'xyz']
        ref_source=[decimal(binary(reference['source_d'+a+'_s_per_km'])) for a in 'xyz']
        differences=[('saved_source_minus_exact_straight', [a-b for a,b in zip(saved_source,detail['edges'][0]['ga'])]),
                     ('saved_x1_minus_exact_old_complete_x1',[a-b for a,b in zip(saved_x1,detail['old_x1'])]),
                     ('connector_source_minus_saved_reference',[a-b for a,b in zip(detail['connector_ga'],ref_source)])]
        norms={name:str(sum((x*x for x in vector),D(0)).sqrt()) for name,vector in differences}
        def flat(value):
            if isinstance(value,D):return [value]
            if isinstance(value,list):return [x for v in value for x in flat(v)]
            return [x for v in value.values() for x in flat(v)]
        spread=max(abs(a-b) for a,b in zip(flat(data[80]),flat(data[100])))
    table(out/'derivatives.csv',[dict(observation_index=PAIR,run_id=RUN,role=name,dx=str(v[0]),dy=str(v[1]),dz=str(v[2]))
          for name,v in vectors+[('saved_original_source',saved_source),('saved_original_complete_x1',saved_x1),('saved_continuous_reference_source',ref_source)]])
    table(out/'stored_float_residuals.csv',[dict(observation_index=PAIR,run_id=RUN,comparison=name,dx=str(v[0]),dy=str(v[1]),dz=str(v[2]),euclidean_norm=norms[name]) for name,v in differences])
    table(out/'native_context.csv',[context]);table(out/'selected_path_vertices.csv',path[:3]);table(out/'selected_reference.csv',[reference])
    exact = dict(coordinate_basis='Fraction.from_float of each stored binary64 coordinate; no Decimal-text reinterpretation',
                 bottom_depth_q=str(bottom),last_layer_top_q=str(lower),bottom_speed_q=str(speed),
                 top_speed_q=str(profile[lower]),velocity_gradient_exact_q=str(slope),
                 velocity_gradient_rounded_binary64_hex=float(slope).hex(),
                 rounded_gradient_minus_exact_q=str(Q.from_float(float(slope))-slope),
                 slowness_depth_derivative_exact_q=str(-slope/(speed*speed)),
                 point_coordinates_q=[[str(x) for x in p] for p in points],
                 action_equality='S(a,x1)=G(a,x1)=sqrt(sum_k(x1_k-a_k)^2)/vB exactly at the horizontal bottom baseline',
                 local_action_change_exact_q='0', critical_distance_exact_q='0',
                 guide_length='positive first-edge length',
                 endpoint_formulas='Straight ga=(-tx/vB,-ty/vB,L*sprime/2), gb=(tx/vB,ty/vB,L*sprime/2); connector replaces only both normal entries by the inward limiting value 0.',
                 complete_x1_formula='connector_gb(first edge)+straight_ga(unchanged second edge)',
                 display_precision_digits=[80,100], maximum_absolute_display_precision_difference=str(spread),
                 precision_interpretation='Numerical stability comparison, not a rigorous interval bound')
    save(out/'exact_baseline_formulas.json',exact)
    for filename in ['edges.csv','derivatives.csv','stored_float_residuals.csv','selected_path_vertices.csv','selected_reference.csv']:
        save(out/(filename+'.identifiers.json'),dict(file=filename,file_sha256=sha(out/filename),join_key='observation_index' if filename!='selected_reference.csv' else 'pair_index',join_value=PAIR,native_context=context,context_csv='native_context.csv',context_sha256=sha(out/'native_context.csv'),basis='Authoritative simulation geometry provenance; no simulated pick identity or new forward result.'))
    for name,digest in pins.items():
        need(sha(ROOT/name)==digest,'Original input changed during static evaluation: '+name)
    for name,dest in mapping.items():
        need(sha(out/dest)==pins[name],'Frozen copy changed during static evaluation')
    summary=dict(status='completed_static_component_original_flags_preserved',scope='One fixed baseline first-edge action substitution and complete first-vertex derivative accounting; no perturbations, ray trace, optimizer, model Jacobian or inverse',
                 started_utc=started,finished_utc=datetime.datetime.utcnow().isoformat()+'Z',
                 command=[sys.executable,'diagnostics/check_loma_endpoint_connector.py','--output',str(out.relative_to(ROOT))],
                 input_sha256=pins,frozen_input_mapping=mapping,native_context=context,
                 original_result=selected,source_t_excluded=context['source_t'],
                 original_saved_total_time_s=selected['time_s'],new_whole_ray_time_evaluated=False,
                 geometry_checks=dict(full_native_fields=199,source_x1_x2_exact_bottom=True,last_layer_depth_only=True,
                                      grid_nodes=len(grid),path_nodes=len(path),all_original_edges_positive=True,
                                      original_path_in_closed_box=True,connector_in_affine_layer_and_box=True,positive_guide=True),
                 exact_model=exact,original_local_convergence_flag=selected['converged'],
                 no_new_forward_or_accuracy_flags=True,
                 baseline_source_old_dz=str(detail['edges'][0]['ga'][2]),baseline_source_connector_dz='0',
                 baseline_x1_old_dz=str(detail['old_x1'][2]),baseline_x1_new_dz=str(detail['new_x1'][2]),
                 stored_float_residual_norms=norms,
                 limitations=['The source and first-knot normal derivatives are inward one-sided derivatives at the fixed bottom; no outward continuation is used.',
                              'The unchanged second edge leaves a nonzero complete x1 normal derivative. No full gradient is zeroed.',
                              'Exact equality of the local mathematical actions does not certify the cached whole-ray sum or reoptimized ray action.',
                              'Decimal80/100 values are displayed approximations; algebraic equality and exact rational geometry/model membership are stated separately.',
                              'A source component comparison with a reviewed reference does not promote the original full-ray flags or validate a general forward correction.',
                              'The affine component supplies no consistent arbitrary-nodal or general-trilinear Jacobian; no production use is proposed by this calculation.'])
    summary['output_sha256']={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()}
    save(out/'summary.json',summary)
    save(out/'execution.json',dict(status='completed',return_code=0,summary_sha256=sha(out/'summary.json'),command=summary['command'],finished_utc=summary['finished_utc']))
    print(json.dumps(dict(status=summary['status'],summary_sha256=sha(out/'summary.json'),source_old_z=summary['baseline_source_old_dz'],x1_new_z=summary['baseline_x1_new_dz'])))


if __name__ == '__main__':
    main()
