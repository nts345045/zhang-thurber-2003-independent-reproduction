#!/usr/bin/env python3
"""Saved first-edge affine actions only; no ray or reference solver calls."""
import sys
sys.dont_write_bytecode = True
import argparse
import csv
import hashlib
import itertools
import json
import platform
import shutil
from datetime import datetime
from decimal import Decimal, localcontext
from fractions import Fraction as Q
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def exact(text):
    # These are round-trip strings for the solver's binary64 inputs/results.
    value = float(text)
    return Q(value)


def dec(q):
    return Decimal(q.numerator) / Decimal(q.denominator)


def norm(v):
    return sum(x*x for x in v).sqrt()


def sub(a, b):
    return [x-y for x, y in zip(a, b)]


def asinh(x):
    # Stable also for small positive x: avoid forming sqrt(1+x*x)-1.
    return (1 + x + x*x/((1+x*x).sqrt()+1)).ln()


def component(aq, bq, v0q, gq, precision):
    """Real affine action evaluated in Decimal, with exact binary64 inputs."""
    with localcontext() as ctx:
        ctx.prec = precision
        a, b = [dec(x) for x in aq], [dec(x) for x in bq]
        v0, g = dec(v0q), dec(gq)
        d = sub(b, a)
        L = norm(d)
        vaq, vbq = v0q+gq*aq[2], v0q+gq*bq[2]
        va, vb, delta = dec(vaq), dec(vbq), dec(vbq-vaq)
        if not delta:
            I, Ia = 1/va, -1/(2*va*va)
        else:
            logarithm = (vb/va).ln()
            I = logarithm/delta
            Ia = (logarithm-delta/va)/(delta*delta)
        straight_gradient = [-I*x/L for x in d]
        straight_gradient[2] += L*g*Ia
        if not g:
            curved_time = L/va
        else:
            curved_time = 2/abs(g)*asinh(abs(g)*L/(2*(va*vb).sqrt()))
        denominator = (va*vb+(g*L/2)**2).sqrt()
        curved_gradient = [-x/L/denominator for x in d]
        curved_gradient[2] -= g*L/(2*va*denominator)
        return {'precision_digits': precision, 'length_km': str(L),
                'v_a_km_per_s': str(va), 'v_b_km_per_s': str(vb),
                'straight_time_s': str(L*I), 'curved_time_s': str(curved_time),
                'curved_minus_straight_time_s': str(curved_time-L*I),
                'straight_source_s_per_km': list(map(str, straight_gradient)),
                'curved_source_s_per_km': list(map(str, curved_gradient))}


def arc_geometry(a, b, v0, g, bounds):
    """Exact rational containment for the upper circular arc, g>0, R>0."""
    if not g > 0:
        raise ValueError('This native containment check requires positive g')
    d = sub(b, a)
    R2 = d[0]*d[0]+d[1]*d[1]
    if not R2 > 0:
        raise ValueError('This native containment check requires horizontal offset')
    zc = -v0/g
    ua, ub = a[2]-zc, b[2]-zc
    center = (R2+ub*ub-ua*ua)/(2*R2)
    radius2_a = center*center*R2+ua*ua
    radius2_b = (1-center)**2*R2+ub*ub
    assert radius2_a == radius2_b
    assert ua > 0 and ub > 0
    assert all(bounds[k][0] <= p[k] <= bounds[k][1]
               for p in (a, b) for k in range(3))
    assert all(Q(0) <= p[2] <= Q(3) for p in (a, b))
    # x,y are affine in lambda. Upper-circle depth is concave; its minimum
    # is an endpoint. Its maximum is the apex only when 0<center<1.
    if center <= 0:
        maximum_at = 'source'
        maximum_squared_height = ua*ua
    elif center >= 1:
        maximum_at = 'first_saved_knot'
        maximum_squared_height = ub*ub
    else:
        maximum_at = 'interior_apex'
        maximum_squared_height = radius2_a
    margin = (Q(3)-zc)**2-maximum_squared_height
    assert Q(3)-zc > 0 and margin >= 0
    # Exact eikonal identity for the numerator of the analytic source formula.
    va, vb = v0+g*a[2], v0+g*b[2]
    L2 = sum(x*x for x in d)
    denominator2 = va*vb+g*g*L2/4
    numerator_norm2 = 1+g*d[2]/va+g*g*L2/(4*va*va)
    assert numerator_norm2*va*va == denominator2
    return {'horizontal_offset_squared_km2': str(R2),
            'center_scaled_by_horizontal_offset': str(center),
            'center_depth_km': str(zc), 'radius_squared_km2': str(radius2_a),
            'endpoint_radius_squared_residual_exact': str(radius2_a-radius2_b),
            'arc_maximum_location': maximum_at,
            'upper_layer_squared_height_margin_km2': str(margin),
            'straight_and_curved_inside_same_0_3_km_layer': True,
            'straight_and_curved_inside_finite_grid_box': True,
            'source_eikonal_identity_exact': True}


def small_controls():
    """Closed-form limits and exact center algebra, no optimized paths."""
    records = []
    # Decimal-level agreement bounds here only check these formula controls;
    # they are not ray acceptance or high-precision error certificates.
    with localcontext() as ctx:
        ctx.prec = 120
        c = component([Q(0)]*3, [Q(3), Q(4), Q(0)], Q(5), Q(0), 120)
        assert Decimal(c['straight_time_s']) == Decimal(1)
        assert Decimal(c['curved_time_s']) == Decimal(1)
        assert list(map(Decimal, c['curved_source_s_per_km'])) == [Decimal('-.12'), Decimal('-.16'), Decimal(0)]
        records.append({'name': 'homogeneous_3_4_5', 'passed': True, 'result': c})
        c = component([Q(0)]*3, [Q(0), Q(0), Q(1)], Q(5), Q(1), 120)
        oracle = (Decimal(6)/5).ln()
        residual = Decimal(c['curved_time_s'])-oracle
        assert abs(residual) < Decimal('1e-115')
        assert abs(Decimal(c['curved_source_s_per_km'][2])+Decimal('.2')) < Decimal('1e-115')
        records.append({'name': 'vertical_affine_log_action', 'passed': True,
                        'action_oracle_residual_s': str(residual), 'result': c})
        c = component([Q(0)]*3, [Q(1), Q(0), Q(0)], Q(5), Q(1), 120)
        assert Decimal(c['straight_source_s_per_km'][2]) == Decimal('-.02')
        records.append({'name': 'horizontal_chord_nonzero_affine_normal_partial',
                        'passed': True, 'result': c})
        a, b, v0, g = [Q(0), Q(0), Q(1)], [Q(1), Q(0), Q(2)], Q(5), Q(1)
        geom = arc_geometry(a, b, v0, g, [(Q(-2), Q(2))]*2+[(Q(0), Q(3))])
        assert Q(geom['center_scaled_by_horizontal_offset']) == Q(7)
        records.append({'name': 'corrected_center_exact_radii', 'passed': True, 'result': geom})
    return records


def main():
    if not __debug__:
        raise RuntimeError('Run without -O/PYTHONOPTIMIZE; integrity assertions required')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root, out = args.root.resolve(), args.output.resolve()
    out.relative_to(root)
    out.mkdir(parents=True, exist_ok=False)
    base = root/'data/development/loma_lon_straight_curvature_replay_001'
    names = ['summary.json', 'execution.json', 'review.json', 'prepared_v3.json',
             'prelaunch_review.json', 'old_parity.json', 'inputs/initial_grid.csv',
             'inputs/initial_events.csv', 'inputs/stations.csv', 'inputs/native_context.json',
             'inputs/selected_reference.csv', 'inputs/reference_summary.json',
             'inputs/reference_execution.json', 'inputs/reference_review.json',
             'inputs/reference_independent_review.json', 'results/old/paths.csv',
             'results/D/paths.csv', 'results/old/scalars_17.csv', 'results/D/scalars_17.csv',
             'source/old/src/core.hpp', 'source/D/src/core.hpp']
    original_pins = {str((base/name).relative_to(root)): sha(base/name) for name in names}
    snapshot = out/'snapshot'
    for name in names:
        target = snapshot/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(str(base/name), str(target))
        assert sha(target) == original_pins[str((base/name).relative_to(root))]
    (out/'source').mkdir()
    shutil.copyfile(str(Path(__file__).resolve()), str(out/'source/check.py'))
    source_hash = sha(out/'source/check.py')
    load = lambda name: json.loads((snapshot/name).read_text())
    summary, execution, review, prepared = [load(name) for name in names[:4]]
    assert summary['status'] == 'completed_four_calls'
    assert execution['status'] == 'completed' and execution['return_code'] == 0
    assert review['status'] == 'passed'
    assert execution['summary_sha256'] == review['summary_sha256'] == sha(snapshot/'summary.json')
    assert review['execution_sha256'] == sha(snapshot/'execution.json')
    assert summary['prepared_sha256'] == sha(snapshot/'prepared_v3.json')
    assert summary['prelaunch_review_sha256'] == sha(snapshot/'prelaunch_review.json')
    assert summary['old_parity_sha256'] == sha(snapshot/'old_parity.json')
    for name in names:
        if name in prepared['output_sha256']:
            assert sha(snapshot/name) == prepared['output_sha256'][name]
        if name in prepared['source_sha256']:
            assert sha(snapshot/name) == prepared['source_sha256'][name]
        if name.startswith('results/'):
            assert sha(snapshot/name) == summary['output_sha256'][name]
    assert sha(snapshot/'results/old/paths.csv') == sha(snapshot/'results/D/paths.csv')
    contexts = load('inputs/native_context.json')
    assert [r['pair_index'] for r in contexts] == [8670, 8674]
    grid = read_csv(snapshot/'inputs/initial_grid.csv')
    coordinates = [[exact(r[k]) for r in grid] for k in ('x', 'y', 'z')]
    axes = [sorted(set(a)) for a in coordinates]
    nodes = {(exact(r['x']), exact(r['y']), exact(r['z'])): exact(r['v']) for r in grid}
    assert len(nodes) == len(grid) == len(axes[0])*len(axes[1])*len(axes[2])
    assert set(nodes) == set(itertools.product(*axes))
    profile = {z: nodes[(axes[0][0], axes[1][0], z)] for z in axes[2]}
    assert all(v == profile[p[2]] for p, v in nodes.items())
    assert all(v > 0 for v in nodes.values())
    assert axes[2][axes[2].index(Q(0))+1] == Q(3)
    v0, g = profile[Q(0)], (profile[Q(3)]-profile[Q(0)])/3
    bounds = [(axis[0], axis[-1]) for axis in axes]
    events, stations = [read_csv(snapshot/('inputs/'+f+'.csv')) for f in ('initial_events', 'stations')]
    assert [r['id'] for r in events] == list(map(str, range(len(events))))
    assert [r['id'] for r in stations] == list(map(str, range(len(stations))))
    paths = read_csv(snapshot/'results/old/paths.csv')
    scalars = {v: {(int(r['event']), int(r['station'])): r for r in read_csv(snapshot/('results/'+v+'/scalars_17.csv'))} for v in ('old', 'D')}
    refs = {int(r['pair_index']): r for r in read_csv(snapshot/'inputs/selected_reference.csv')}
    assert set(refs) == {8670, 8674}
    rows, records = [], []
    native_fields_checked = 0
    for context in contexts:
        pair = context['pair_index']
        event, station = int(context['source_native']['id']), int(context['receiver_native']['id'])
        assert context['source_native'] == events[event]
        assert context['receiver_native'] == stations[station]
        assert pair == event*len(stations)+station
        path = [r for r in paths if int(r['pair_index']) == pair]
        assert [r['node'] for r in path] == list(map(str, range(len(path))))
        assert len(path) == int(scalars['old'][(event, station)]['ray_path_points'])
        assert all((int(r['event']), int(r['station'])) == (event, station) for r in path)
        native = {}
        for prefix, table in [('source', events[event]), ('receiver', stations[station])]:
            for key, value in table.items():
                if key not in ('id', 'x', 'y', 'z', 't'):
                    native[prefix+'_'+key] = value
        for r in path+[scalars[v][(event, station)] for v in ('old', 'D')]+[refs[pair]]:
            assert all(r[k] == value for k, value in native.items())
            native_fields_checked += len(native)
        for prefix, table in [('source', events[event]), ('receiver', stations[station])]:
            assert refs[pair][prefix+'_id'] == table['id']
            for axis in ('x', 'y', 'z', 't'):
                assert exact(refs[pair][prefix+'_'+axis]) == exact(table[axis])
        for endpoint, table in [(path[0], events[event]), (path[-1], stations[station])]:
            assert all(exact(endpoint[k]) == exact(table[k]) for k in ('x', 'y', 'z'))
        for variant in ('old', 'D'):
            r = scalars[variant][(event, station)]
            assert all(exact(r['source_'+k]) == exact(events[event][k]) for k in ('x', 'y', 'z'))
            assert all(exact(r['receiver_'+k]) == exact(stations[station][k]) for k in ('x', 'y', 'z'))
        assert refs[pair]['reference_complete'] == refs[pair]['reference_valid'] == '1'
        assert refs[pair]['candidate_count'] == refs[pair]['near_tie_count'] == '1'
        a, b = [[exact(r[k]) for k in ('x', 'y', 'z')] for r in path[:2]]
        geometry = arc_geometry(a, b, v0, g, bounds)
        values = {str(p): component(a, b, v0, g, p) for p in (80, 120)}
        with localcontext() as ctx:
            ctx.prec = 120
            high = values['120']
            straight = list(map(Decimal, high['straight_source_s_per_km']))
            curved = list(map(Decimal, high['curved_source_s_per_km']))
            saved = [dec(exact(scalars['old'][(event, station)]['source_d'+k])) for k in ('x', 'y', 'z')]
            assert all(exact(scalars['D'][(event, station)]['source_d'+k]) == exact(scalars['old'][(event, station)]['source_d'+k]) for k in ('x', 'y', 'z'))
            reference = [dec(exact(refs[pair]['source_d'+k+'_s_per_km'])) for k in ('x', 'y', 'z')]
            vectors = {'saved_minus_reference': sub(saved, reference),
                       'saved_minus_straight': sub(saved, straight),
                       'straight_minus_curved': sub(straight, curved),
                       'curved_minus_reference': sub(curved, reference)}
            identity_residual = [vectors['saved_minus_reference'][k] - sum(vectors[n][k] for n in ('saved_minus_straight', 'straight_minus_curved', 'curved_minus_reference')) for k in range(3)]
            sensitivity = {}
            for key in ('straight_time_s', 'curved_time_s', 'curved_minus_straight_time_s'):
                sensitivity[key] = str(abs(Decimal(values['80'][key])-Decimal(high[key])))
            for key in ('straight_source_s_per_km', 'curved_source_s_per_km'):
                sensitivity[key] = [str(abs(Decimal(x)-Decimal(y))) for x, y in zip(values['80'][key], high[key])]
            # The circular tangent gives an independent form of curved source momentum.
            center = Q(geometry['center_scaled_by_horizontal_offset'])
            R2 = Q(geometry['horizontal_offset_squared_km2'])
            tangent = [dec(b[0]-a[0]), dec(b[1]-a[1]), dec(center*R2/(a[2]-Q(geometry['center_depth_km'])))]
            tangent_source = [-x/norm(tangent)/dec(v0+g*a[2]) for x in tangent]
            norms = {k: str(norm(v)) for k, v in vectors.items()}
            local = {'pair_index': pair, 'event': event, 'station': station,
                     'path_node_count': len(path), 'native_context': context,
                     'first_two_saved_rows': path[:2], 'saved_scalars': {v: scalars[v][(event, station)] for v in ('old', 'D')},
                     'global_reference_row': refs[pair], 'exact_geometry': geometry,
                     'components': values, 'arithmetic_precision_sensitivity_80_vs_120': sensitivity,
                     'circle_tangent_source_minus_curved_formula_s_per_km': list(map(str, sub(tangent_source, curved))),
                     'vectors_s_per_km': {k: list(map(str, v)) for k, v in vectors.items()},
                     'vector_norms_s_per_km': norms,
                     'decomposition_identity_residual_s_per_km': list(map(str, identity_residual)),
                     'unchanged_source_limit_s_per_km': summary['source_vector_norm_limit_s_per_km'],
                     'saved_source_meets_original_limit': norm(vectors['saved_minus_reference']) <= dec(exact(summary['source_vector_norm_limit_s_per_km'])),
                     'local_curved_component_meets_same_numeric_limit': norm(vectors['curved_minus_reference']) <= dec(exact(summary['source_vector_norm_limit_s_per_km'])),
                     'component_comparison_does_not_change_whole_ray_acceptance': True}
            records.append(local)
            row = dict(native, pair_index=str(pair), event=str(event), station=str(station),
                       source_x=path[0]['x'], source_y=path[0]['y'], source_z=path[0]['z'],
                       first_knot_x=path[1]['x'], first_knot_y=path[1]['y'], first_knot_z=path[1]['z'],
                       straight_time_s=high['straight_time_s'], curved_time_s=high['curved_time_s'],
                       curved_minus_straight_time_s=high['curved_minus_straight_time_s'])
            for name, vector in vectors.items():
                for axis, value in zip(('x', 'y', 'z'), vector):
                    row[name+'_d'+axis+'_s_per_km'] = str(value)
                row[name+'_norm_s_per_km'] = norms[name]
            rows.append(row)
    assert len(paths) == sum(r['path_node_count'] for r in records) == 1068
    controls = small_controls()
    write_json(out/'components.json', records)
    write_json(out/'controls.json', controls)
    with (out/'comparison.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    assert sha(Path(__file__).resolve()) == source_hash
    assert all(sha(root/path) == value for path, value in original_pins.items())
    artifacts = {str(p.relative_to(out)): sha(p) for p in sorted(out.rglob('*')) if p.is_file()}
    write_json(out/'summary.json', {
        'status': 'completed_saved_component_calculation', 'executed_utc': datetime.utcnow().isoformat()+'Z',
        'scope': 'Two saved first-edge components only; no native ray, optimizer, FMM, reference enumeration, observational retrieval or inverse call',
        'command': [sys.executable, str(Path(__file__).resolve().relative_to(root)), '--output', str(out.relative_to(root))],
        'python_version': platform.python_version(), 'source_sha256': source_hash,
        'original_sha256': original_pins, 'output_sha256': artifacts,
        'input_interpretation': 'Exact real values represented by the saved binary64 coordinates and grid nodes; transcendental expressions evaluated at 80 and 120 Decimal digits',
        'grid_dimensions': list(map(len, axes)), 'grid_is_depth_only': True,
        'affine_layer_km': [0, 3], 'v_at_0_exact_km_per_s': str(v0), 'v_at_3_exact_km_per_s': str(profile[Q(3)]), 'gradient_exact_per_s': str(g),
        'native_pairs': [r['pair_index'] for r in records], 'native_fields_checked': native_fields_checked,
        'old_D_paths_byte_identical': True, 'old_D_source_vectors_exactly_equal': True,
        'closed_form_controls_passed': len(controls), 'old_source_limit_s_per_km': summary['source_vector_norm_limit_s_per_km'],
        'results': [{'pair_index': r['pair_index'], 'source_event_resource_id': r['native_context']['source_native']['event_resource_id'],
                     'receiver_channel_seed_id': r['native_context']['receiver_native']['channel_seed_id'],
                     'receiver_metadata_epoch_start': r['native_context']['receiver_native']['metadata_epoch_start'],
                     'receiver_metadata_epoch_end': r['native_context']['receiver_native']['metadata_epoch_end'],
                     'vector_norms_s_per_km': r['vector_norms_s_per_km'],
                     'curved_minus_straight_time_s': r['components']['120']['curved_minus_straight_time_s'],
                     'saved_source_meets_original_limit': r['saved_source_meets_original_limit'],
                     'local_curved_component_meets_same_numeric_limit': r['local_curved_component_meets_same_numeric_limit']} for r in records],
        'limitations': ['Exact rational geometric containment does not bound Decimal transcendental roundoff; 80/120 comparison is sensitivity evidence.',
                        'The local connector holds the first saved knot fixed; the rest of the polygon was neither changed nor reoptimized.',
                        'No whole-path stationary source derivative, updated native flag, or first-arrival/global-minimum claim follows.',
                        'No original-grid model derivatives are replaced; the analytic affine component is a diagnostic, not a dispatch rule for arbitrary trilinear models.',
                        'The authoritative channel epochs describe declared simulation station placements, not event-time waveform observations.']})
    print(json.dumps({'summary': str((out/'summary.json').relative_to(root)),
                      'summary_sha256': sha(out/'summary.json'), 'pairs': [r['pair_index'] for r in records]}))


if __name__ == '__main__':
    main()
