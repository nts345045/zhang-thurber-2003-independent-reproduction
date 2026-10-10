#!/usr/bin/env python3
"""Independent rational saved-data readback; no project imports or integration."""
import csv
from fractions import Fraction as Q
import gzip
import hashlib
from itertools import product
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DATA = ROOT / 'data/development'
RUN = DATA / 'hayward_cmj_post_step_zero_support_001'
POST = DATA / 'hayward_cmj_post_step_tangent_001'
PRIOR_REVIEW = DATA / 'hayward_cmj_post_step_tangent_review_001/review.json'
STEP = DATA / 'hayward_cmj_tangent_step_001'
START = DATA / 'hayward_cmj_face_action_001'
EXPECTED = 'ea979bbbb2cd056e809ba6e9a78e8b30c9e52b1b200a945f95f85e63b0e6b47f'
CHECKS = 0
PINNED = {}


def require(ok, message):
    global CHECKS
    CHECKS += 1
    if not ok:
        raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def read(path):
    with (gzip.open(str(path), 'rt') if path.suffix == '.gz' else path.open()) as stream:
        return json.load(stream)


def rows(path):
    with path.open(newline='') as stream:
        reader = csv.DictReader(stream)
        require(len(reader.fieldnames) == len(set(reader.fieldnames)), 'Duplicate CSV header')
        result = list(reader)
    require(all(None not in row for row in result), 'Malformed CSV row')
    return result


def encoded(value):
    if isinstance(value, Q):
        return str(value)
    if isinstance(value, dict):
        return {key: encoded(v) for key, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [encoded(v) for v in value]
    return value


def pin(path, digest):
    require(path.is_file() and sha(path) == digest, 'Changed pin: ' + str(path))
    require(str(path) not in PINNED or PINNED[str(path)] == digest, 'Conflicting pin')
    PINNED[str(path)] = digest


def interval(value):
    lo, hi = map(Q, value)
    require(lo <= hi, 'Reversed interval')
    return lo, hi


def add(a, b):
    return a[0] + b[0], a[1] + b[1]


def trim(values):
    result = list(values)
    while len(result) > 1 and result[-1] == 0:
        result.pop()
    return result


def interpolate(values):
    """Three direct basis evaluations determine the degree-at-most-two face polynomial."""
    f0, fm, f1 = values
    c2 = 2 * (f1 - 2 * fm + f0)
    return trim([f0, f1 - f0 - c2, c2])


def polynomial_range(coefficients):
    require(1 <= len(coefficients) <= 3, 'Quadratic degree')
    c = list(coefficients) + [Q(0)] * (3 - len(coefficients))
    points = [Q(0), Q(1)]
    if c[2] and 0 < -c[1] / (2 * c[2]) < 1:
        points.append(-c[1] / (2 * c[2]))
    values = [c[0] + t * (c[1] + t * c[2]) for t in points]
    return (min(values), max(values)), points


def basis_value(axes, speeds, cell, position, normal):
    """Original eight nodal values, direct shape products and spatial normal derivatives."""
    widths = [axes[k][cell[k] + 1] - axes[k][cell[k]] for k in range(3)]
    f = [(position[k] - axes[k][cell[k]]) / widths[k] for k in range(3)]
    require(all(0 <= x <= 1 for x in f), 'Closed-cell containment')
    value = Q(0); derivative = Q(0); vertices = []
    for corner in product((0, 1), repeat=3):
        speed = speeds[tuple(cell[k] + corner[k] for k in range(3))]
        factors = [f[k] if corner[k] else 1 - f[k] for k in range(3)]
        value += speed * factors[0] * factors[1] * factors[2]
        tangent = [k for k in range(3) if k != normal]
        derivative += speed * (1 if corner[normal] else -1) / widths[normal] * factors[tangent[0]] * factors[tangent[1]]
        vertices.append(speed)
    return value, derivative, vertices


def check_proof(proof, edge, a, b, face, axes, speeds):
    normal, index = face
    require(proof['edge'] == edge and proof['endpoint_nodes'] == [edge, edge + 1], 'Proof edge join')
    delta = [b[k] - a[k] for k in range(3)]
    cuts = {Q(0), Q(1)}
    for k in range(3):
        if delta[k]:
            cuts.update((x - a[k]) / delta[k] for x in axes[k][1:-1] if 0 < (x - a[k]) / delta[k] < 1)
    cuts = sorted(cuts)
    require(len(proof['patches']) == len(cuts) - 1, 'Complete partition')
    passed = True; extrema = []
    for patch, left, right in zip(proof['patches'], cuts, cuts[1:]):
        middle = [a[k] + (left + right) / 2 * delta[k] for k in range(3)]
        cell = [min(len(axis) - 2, max(i for i, x in enumerate(axis) if x <= middle[k])) for k, axis in enumerate(axes)]
        minus = list(cell); minus[normal] = index - 1
        plus = list(cell); plus[normal] = index
        require(interval(patch['u']) == (left, right) and patch['normal_axis'] == normal
                and Q(patch['normal_coordinate']) == axes[normal][index]
                and patch['minus_cell'] == minus and patch['plus_cell'] == plus, 'Independent cell/face/parameter join')
        sampled = []
        for side_cell in (minus, plus):
            side = []
            for t in (Q(0), Q(1, 2), Q(1)):
                u = left + (right - left) * t
                side.append(basis_value(axes, speeds, side_cell, [a[k] + u * delta[k] for k in range(3)], normal))
            sampled.append(side)
        vm, vp = [interpolate([v[0] for v in side]) for side in sampled]
        gm, gp = [interpolate([v[1] for v in side]) for side in sampled]
        vertices = sampled[0][0][2] + sampled[1][0][2]
        require(vm == vp and min(vertices) > 0, 'Continuous positive native face model')
        require(encoded(vm) == patch['velocity_polynomial'] and encoded((min(vertices), max(vertices))) == patch['velocity_vertex_bounds'], 'Native velocity polynomial/bounds')
        require(encoded(gm) == patch['minus_velocity_normal_polynomial'] and encoded(gp) == patch['plus_velocity_normal_polynomial'], 'Native normal polynomial coefficients')
        rm, tm = polynomial_range(gm); rp, tp = polynomial_range(gp)
        require(encoded(rm) == patch['minus_exact_range'] and encoded(rp) == patch['plus_exact_range'], 'Exact quadratic extrema')
        ok = rm[0] >= 0 and rp[1] <= 0
        require(patch['zero_normal_supported'] == ok and patch['both_polynomials_zero'] == all(x == 0 for x in gm + gp), 'Whole-interval sign status')
        size = max(len(gm), len(gp)); m = gm + [Q(0)] * (size - len(gm)); p = gp + [Q(0)] * (size - len(gp))
        denominator = trim([m[k] - p[k] for k in range(size)])
        require(encoded(gm) == patch['theta_numerator'] and encoded(denominator) == patch['theta_denominator'], 'Same pointwise mixture for both endpoints')
        # theta=gm/(gm-gp): (1-theta)*(-gm)+theta*(-gp)=0 identically.
        require(all(-m[k] + (m[k] - p[k]) + p[k] == 0 for k in range(size)), 'Mixture polynomial identity')
        passed = passed and ok
        extrema.append(dict(edge=edge, u=(left, right), minus_extrema_parameters=tm, plus_extrema_parameters=tp))
    require(proof['status'] == ('proved_zero_normal_support' if passed else 'inconclusive_sign_condition_failed'), 'Proof status')
    return passed, extrema


def norm(path, vector, axes):
    total = (Q(0), Q(0)); records = []; blocked = []; boundary = 0
    for node in range(1, len(path) - 1):
        for axis, term in enumerate(vector[node]):
            if term is None:
                blocked.append((node, axis)); continue
            lo, hi = interval(term); x = path[node][axis]; a, b = lo, hi; position = 'interior'
            if x == axes[axis][0]:
                a, b = min(lo, Q(0)), min(hi, Q(0)); position = 'exact_lower'
            elif x == axes[axis][-1]:
                a, b = max(lo, Q(0)), max(hi, Q(0)); position = 'exact_upper'
            square = max(a, -b, Q(0)) ** 2, max(abs(a), abs(b)) ** 2
            total = add(total, square); boundary += int(position != 'interior')
            records.append(dict(node=node, axis=axis, coordinate_exact=x, component_bounds=(lo, hi), physical_box_position=position, projected_bounds=(a, b), squared_bounds=square))
    return total, records, blocked, boundary


def check_norm(saved, result):
    (lo, hi), records, blocked, boundary = result
    require(interval((saved['lower_squared'], saved['upper_squared'])) == (lo, hi), 'Exact squared-norm sum')
    require(saved['available_component_count'] == len(records) and saved['unavailable_component_count'] == len(blocked)
            and saved['exact_physical_boundary_component_count'] == boundary and saved['units'] == 's^2/km^2', 'Norm component inventory/units')
    for name, scale in [('strict_gradient_scale', Q(1, 10 ** 7)), ('combined_gradient_scale', Q(1, 10 ** 5))]:
        record = saved['threshold_scales'][name]
        require(Q(record['scale_squared']) == scale ** 2 and record['diagnostic_only'] is True
                and record['classification'] == ('strictly_above' if lo > scale ** 2 else 'strictly_below' if hi < scale ** 2 else 'overlapping'), 'Diagnostic scale comparison')


def model():
    saved = read(START / 'model_provenance.json'); raw = rows(START / 'inputs/trial_grid.csv')
    axes = [list(map(Q, axis)) for axis in saved['axes_exact_rational']]; speeds = {}
    require(len(axes) == 3 and all(len(a) >= 2 and all(x < y for x, y in zip(a, a[1:])) for a in axes), 'Increasing Cartesian axes')
    require(len(raw) == len(saved['nodes']) == 462 and saved['recorded_grid_sha256'] == sha(START / 'inputs/trial_grid.csv'), 'Native model inventory/hash')
    for i, (row, record) in enumerate(zip(raw, saved['nodes'])):
        require(record['csv_row'] == i, 'Native grid order')
        for k in ('x', 'y', 'z', 'v'):
            v = record['values'][k]
            require(v['raw_text'] == row[k] and v['binary64_hex'] == float(row[k]).hex() and Q(v['exact_rational']) == Q(float(row[k])), 'Native binary64 model mapping')
        key = tuple(axes[k].index(Q(float(row[c]))) for k, c in enumerate('xyz'))
        require(key not in speeds, 'Unique native grid node'); speeds[key] = Q(float(row['v']))
    require(set(speeds) == set(product(*(range(len(a)) for a in axes))) and min(speeds.values()) > 0, 'Positive complete Cartesian model')
    return axes, speeds


def native_joins(identities):
    step_prepared = read(STEP / 'prepared.json')
    paths = [START / 'inputs/trial_events.csv', START / 'inputs/stations.csv', ROOT / 'data/hayward/observations.csv']
    for p in paths:
        pin(p, step_prepared['input_sha256'][str(p.relative_to(ROOT))])
    events, stations, observations = [rows(p) for p in paths]
    require([r['id'] for r in events] == list(map(str, range(len(events)))) and [r['id'] for r in stations] == list(map(str, range(len(stations)))), 'Contiguous native indices')
    for identity in identities:
        e, s = identity['event'], identity['station']; context = identity['native_context']
        require(context['event'] == e and context['station'] == s and context['native_flat_index'] == e * len(stations) + s
                and context['source_native'] == events[e] and context['receiver_native'] == stations[s], 'Complete source/receiver native table join')
        expected = []
        for i, row in enumerate(observations):
            for side in ('i', 'j'):
                station = int(row['station'] if side == 'i' or row.get('station_j', '') == '' else row['station_j'])
                if int(row[side]) == e and station == s:
                    expected.append((i, side))
        require([(u['zero_based_observation_row'], u['side']) for u in identity['catalog_uses']] == expected and len(expected) == 9, 'Complete original catalog uses')
        for use in identity['catalog_uses']:
            row = observations[use['zero_based_observation_row']]
            require(use['original_row'] == row, 'Every original pick/association/native catalog field')
            sides = ['i'] + (['j'] if int(row['j']) >= 0 else [])
            require(set(use['epoch_joins']) == set(sides), 'Exact two-side epoch inventory')
            for side in sides:
                ei = int(row[side]); si = int(row['station'] if side == 'i' or row.get('station_j', '') == '' else row['station_j'])
                source, receiver = events[ei], stations[si]; joined = use['epoch_joins'][side]
                require(joined == dict(event_index=ei, station_index=si, receiver_native=receiver), 'Both native receiver epochs')
                require(row['event_' + side + '_resource_id'] == source['event_resource_id'] and row['origin_' + side + '_resource_id'] == source['origin_resource_id'], 'Provider event/origin join')
                for k in ('network_code', 'station_code', 'location_code', 'channel_code', 'channel_seed_id', 'channel_fdsn_source_id'):
                    require(row[k] == receiver[k], 'Exact NSLC/FDSN including empty location')
                suffix = '' if side == 'i' else '_j'
                require(row['metadata_epoch' + suffix + '_start'] == receiver['metadata_epoch_start']
                        and row['metadata_epoch' + suffix + '_end'] == receiver['metadata_epoch_end']
                        and row['channel' + suffix + '_source_sha256'] == receiver['source_sha256'], 'Provider channel epoch/hash join')
    return len(observations)


def check_case(identity, brief, axes, speeds, prior_review):
    event = identity['event']; output = RUN / ('event_' + str(event) + '.json.gz')
    full = read(output); post_file = POST / output.name; post = read(post_file)
    trial = read(STEP / ('event_' + str(event)) / 'result.json.gz'); attached = read(Path(str(output) + '.identifiers.json'))
    for record in (full, post, trial, attached, brief):
        require(all(record[k] == identity[k] for k in ('event', 'station', 'native_context', 'catalog_uses')), 'Full native result/sidecar join')
    require(attached['file_sha256'] is None and attached['expected_file'] == str(output.relative_to(ROOT)) and attached['prepared_sha256'] == EXPECTED
            and attached['evidence_sha256'] == read(RUN / 'prepared.json')['input_sha256'], 'Predeclared sidecar binding')
    require(full['status'] == brief['status'] == 'completed_saved_support_assessment' and full['original_convergence_flag'] == brief['original_convergence_flag'] == '0'
            and full['candidate_convergence_status'] is brief['candidate_convergence_status'] is None and full['source_partials_evaluated'] is False, 'Unchanged flags and limited scope')
    status = identity['native_context']['original_status']
    require(status['ray_converged'] == status['ray_derivatives_evaluated'] == '0' and all(status['source_d' + k] == '' for k in 'xyz'), 'Original failed status/blank partials')
    require(full['saved_components_sha256'] == sha(post_file) and full['coordinate_provenance'] == post['coordinate_provenance']
            and post['status'] == 'completed_available_tangent_bounds' and post['ineligibility'] == [] and trial['result']['status'] == 'diagnostic_trial_accepted', 'Accepted first trial and saved component binding')
    path = [tuple(map(Q, p)) for p in trial['result']['trial']]; n = len(path)
    require(n == (1029 if event == 981 else 1031), 'Native path roster')
    for i, (p, c) in enumerate(zip(path, full['coordinate_provenance'])):
        require(c['node'] == i and tuple(map(Q, c['exact_rational'])) == p
                and [float(x).hex() for x in c['decimal_tokens']] == c['binary64_hex']
                and tuple(Q(float(x)) for x in c['decimal_tokens']) == p, 'Actual binary64 coordinates')
    require(len(full['coordinate_provenance']) == n and all(axes[k][0] <= p[k] <= axes[k][-1] for p in path for k in range(3)), 'Complete in-box geometry')
    require(path[0] == tuple(Q(float(identity['native_context']['source_native'][k])) for k in 'xyz')
            and path[-1] == tuple(Q(float(identity['native_context']['receiver_native'][k])) for k in 'xyz'), 'Native fixed endpoints')
    edges = post['tangent_edge_records']; require(len(edges) == n - 1, 'Complete ordinary edge records')
    faces = []; blocked = set(); summed = [None] + [[(Q(0), Q(0)) for k in range(3)] for i in range(1, n - 1)] + [None]
    zero = []; aligned = []
    for e, (a, b, record) in enumerate(zip(path, path[1:], edges)):
        face = [(k, axis.index(a[k])) for k, axis in enumerate(axes) if a[k] == b[k] and a[k] in axis[1:-1]]
        require(a != b and len(face) <= 1 and record['edge'] == e and record['endpoint_nodes'] == [e, e + 1] and record['blocked_axes'] == [k for k, j in face], 'Actual edge geometry/availability')
        aligned.append(dict(edge=e, aligned_internal_faces=face))
        if face: faces.append((e, face[0]))
        for side in (0, 1):
            node = e + side
            if node in (0, n - 1):
                require(record['components'][side] is None, 'Fixed endpoint omitted'); continue
            require(len(record['components'][side]) == 3, 'Three incident components')
            for k, term in enumerate(record['components'][side]):
                require((term is None) == (k in record['blocked_axes']), 'No arbitrary component clipping')
                if term is None:
                    blocked.add((node, k)); zero.append(dict(edge=e, side=side, node=node, axis=k, contribution=(Q(0), Q(0))))
                else: summed[node][k] = add(summed[node][k], interval(term))
    require(encoded(aligned) == post['aligned_edge_inventory'] and encoded(sorted(blocked)) == post['geometric_blocked_slots'], 'Independent face inventory')
    available = [None if v is None else list(v) for v in summed]
    for i, k in blocked: available[i][k] = None
    require(encoded([dict(node=i, components=available[i]) for i in range(1, n - 1)]) == post['free_node_components'], 'Prior ordinary adjacent-edge assembly')
    partial = norm(path, available, axes); check_norm(full['available_tangent_norm'], partial)
    require(full['available_tangent_norm'] == post['post_step_norm'] == brief['available_tangent_norm'] and encoded(partial[1]) == post['available_projected_components'], 'Unchanged available tangent lower bound')
    prior = next(r for r in prior_review['cases'] if r['event'] == event)
    require(interval(prior['post_squared_bounds']) == partial[0] and all(prior[k] == identity[k] for k in ('event', 'station', 'native_context', 'catalog_uses')), 'Independent prior review binding')
    proofs = full['zero_normal_support_proofs']; require([r['edge'] for r in proofs] == [e for e, face in faces], 'All and only aligned edges proved')
    failed = []; extrema = []
    for proof, (edge, face) in zip(proofs, faces):
        ok, points = check_proof(proof, edge, path[edge], path[edge + 1], face, axes, speeds)
        if not ok: failed.append(edge)
        extrema.extend(points)
    support = full['full_support']; require(support['status'] == brief['support_status'] and support['norm'] == brief['feasible_full_support_norm'], 'Summary support join')
    if failed:
        require(support['status'] == 'inconclusive_sign_condition_failed' and support['failed_edges'] == failed
                and support['vector'] is support['projected_components'] is support['norm'] is None, 'Failed proof remains inconclusive')
    else:
        require(support['status'] == 'feasible_zero_aligned_normal_support', 'One feasible support status')
        ordinary = []
        for record in edges:
            for side in (0, 1):
                node = record['edge'] + side
                if node in (0, n - 1): continue
                for k, term in enumerate(record['components'][side]):
                    if term is not None and (node, k) in blocked:
                        ordinary.append(dict(edge=record['edge'], side=side, node=node, axis=k, contribution=interval(term)))
        require(encoded(ordinary) == support['ordinary_contributions_in_blocked_slots'] and encoded(zero) == support['zero_aligned_contributions'], 'All ordinary entry/exit terms retained; only proved edge normals zero')
        require(encoded([dict(node=i, components=summed[i]) for i in range(1, n - 1)]) == support['vector'], 'Complete feasible vector from original saved edge terms')
        full_norm = norm(path, summed, axes); check_norm(support['norm'], full_norm)
        require(not full_norm[2] and encoded(full_norm[1]) == support['projected_components'], 'Every projected support component')
    return dict(identity, nodes=n, saved_edges=n-1, sign_edges=len(faces), sign_patches=len(extrema), exact_extrema=extrema,
                failed_edges=failed, available_tangent_squared_bounds=partial[0], feasible_full_support_norm=support['norm'],
                ordinary_contributions_retained=len(support.get('ordinary_contributions_in_blocked_slots', [])), original_convergence_flag='0', candidate_convergence_status=None)


def main():
    require(not (HERE / 'review.json').exists(), 'Fresh review output required')
    approval = read(HERE / 'source_review.json')
    require(approval['status'] == 'passed' and approval['checker_sha256'] == sha(Path(__file__)), 'Independent source review before execution')
    for path in [Path(__file__), HERE / 'README.md', HERE / 'source_review.json']:
        pin(path, sha(path))
    prepared = read(RUN / 'prepared.json'); summary = read(RUN / 'summary.json'); execution = read(RUN / 'execution.json'); outer = read(RUN / 'outer_reaping.json')
    pin(RUN / 'prepared.json', EXPECTED)
    require(summary['status'] == execution['status'] == 'completed_bounded_saved_support' and execution['return_code'] == 0 and summary['error'] is None, 'Terminal successful calculation')
    require(outer['status'] == 'completed_and_reaped' and outer['tool_exit_code'] == 0 and outer['wrapper_pid'] == execution['pid'] and outer['wrapper_process_absent'], 'Reaped native calculation')
    for key, name in [('prepared_sha256', 'prepared.json'), ('summary_sha256', 'summary.json'), ('execution_sha256', 'execution.json'), ('prelaunch_review_sha256', 'prelaunch_review.json')]:
        pin(RUN / name, outer[key])
    prelaunch = read(RUN / 'prelaunch_review.json')
    require(prelaunch['status'] == 'passed' and prelaunch['prepared_sha256'] == EXPECTED and prelaunch['source_sha256'] == sha(RUN / 'run.py'), 'Reviewed native source')
    for record in (summary, execution):
        require(record['prepared_sha256'] == EXPECTED and record['prelaunch_review_sha256'] == sha(RUN / 'prelaunch_review.json'), 'Terminal preparation linkage')
    require(execution['input_sha256'] == prepared['input_sha256'] and execution['environment'] == prepared['environment'] and execution['summary_sha256'] == sha(RUN / 'summary.json'), 'Executed input/environment/summary closure')
    for base, key in [(ROOT, 'input_sha256'), (RUN, 'output_sha256'), (Path('/'), 'runtime_sha256')]:
        for name, digest in prepared[key].items(): pin(base / name, digest)
    require(summary['output_sha256'] == execution['output_sha256'] and {p.name for p in RUN.glob('event_*')} == set(summary['output_sha256']), 'Exact output inventory')
    for name, digest in summary['output_sha256'].items(): pin(RUN / name, digest)
    pin(RUN / 'outer_reaping.json', sha(RUN / 'outer_reaping.json'))
    require(all(summary[k] == 0 for k in ('tangent_integrations', 'normal_integrations', 'action_integrations', 'metric_solves', 'rounded_trials', 'trace_calls', 'field_calls', 'optimizer_iterations', 'subprocess_calls')), 'No numerical primitive or native calls')
    identities = read(RUN / 'native_contexts.json')
    require(identities == summary['native_contexts'] == execution['native_contexts'] == read(POST / 'native_contexts.json') == read(STEP / 'native_contexts.json'), 'Unchanged full identity roster')
    require([v['event'] for v in identities] == [981, 987] and [v['event'] for v in summary['cases']] == [981, 987], 'Exact two-case roster')
    prior = read(PRIOR_REVIEW); require(prior['status'] == 'passed', 'Passed prior component review')
    for key, name in [('native_prepared_sha256', 'prepared.json'), ('native_summary_sha256', 'summary.json'), ('native_execution_sha256', 'execution.json'), ('outer_reaping_sha256', 'outer_reaping.json')]:
        pin(POST / name, prior[key])
    catalog_count = native_joins(identities); axes, speeds = model(); reports = []
    for identity, brief in zip(identities, summary['cases']):
        require(brief['result_file'] == 'event_' + str(identity['event']) + '.json.gz', 'Expected result path')
        pin(RUN / brief['result_file'], brief['result_sha256'])
        reports.append(check_case(identity, brief, axes, speeds, prior))
    for field in ('sign_edges', 'sign_patches'):
        count = sum(r[field] for r in reports)
        require(count == summary[field + '_completed'] == execution[field + '_completed'], 'Completed proof inventory')
    for path, digest in list(PINNED.items()): pin(Path(path), digest)
    result = dict(status='passed', reviewer='earthscope_discovery', checker_sha256=sha(Path(__file__)), source_review_sha256=sha(HERE / 'source_review.json'),
                  native_prepared_sha256=EXPECTED, native_summary_sha256=sha(RUN / 'summary.json'), native_execution_sha256=sha(RUN / 'execution.json'), outer_reaping_sha256=sha(RUN / 'outer_reaping.json'),
                  prior_component_review_sha256=sha(PRIOR_REVIEW), checks=CHECKS, original_catalog_rows=catalog_count, cases=reports,
                  input_sha256={str(Path(p).relative_to(ROOT)) if str(p).startswith(str(ROOT) + '/') else p: h for p, h in PINNED.items()},
                  numerical_integrations=0, project_module_imports=0, native_calls=0,
                  limitations=['Direct nodal basis/interpolation and exact rational saved-array arithmetic; no tangent, normal or action reintegration.',
                               'Continuous positive velocity and gm>=0>=gp make the same pointwise convex mixture normal-zero for both endpoint moments. Ordinary adjacent-edge terms remain.',
                               'The full squared norm encloses one feasible supporting vector, not the minimum support residual; a large witness is inconclusive.',
                               'Existing primitive enclosures are inherited from the pinned independent component review. No flag, optimized ray, source-derivative, first-arrival or field-accuracy promotion.'])
    with (HERE / 'review.json').open('x') as stream:
        json.dump(encoded(result), stream, indent=2, sort_keys=True, allow_nan=False); stream.write('\n')
    print(json.dumps(dict(status='passed', review_sha256=sha(HERE / 'review.json'), checks=CHECKS, pinned_files=len(PINNED))))


if __name__ == '__main__':
    main()
