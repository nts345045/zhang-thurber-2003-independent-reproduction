#!/usr/bin/env python3
"""Saved rational readback only: no evaluator import, integration or fit."""
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DATA = ROOT / 'data/development'
RUN = DATA / 'hayward_cmj_final_tangent_support_001'
ITER = DATA / 'hayward_cmj_tangent_iteration_001'
ITER_REVIEW = DATA / 'hayward_cmj_tangent_iteration_review_001'
BENCH = DATA / 'hayward_cmj_fixed_polygon_kernel_001'
EXPECTED = 'cff1fa298a518967563059d378ed68eb068b0b6402f0cf244304778124b462e0'
READER = DATA / 'hayward_cmj_post_half_step_tangent_review_001/check_saved.py'
READER_SHA = '8c300b68d8647ddec4b64acf792625ef3ac68b353d10058c0418f9b169eed46e'
if hashlib.sha256(READER.read_bytes()).hexdigest() != READER_SHA:
    raise ValueError('Changed pure saved-data reader')
spec = importlib.util.spec_from_file_location('saved_rational_reader', str(READER))
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)  # Pure stdlib definitions; never calls its main/evaluators.
require, sha, read, rows, pin = r.require, r.sha, r.read, r.rows, r.pin
interval, add, encoded, trim = r.interval, r.add, r.encoded, r.trim
SETTINGS = dict(terms=8, subdivisions=1, bits=128)
IDENTITY = ('event', 'station', 'native_context', 'catalog_uses')
CACHE = {}


def same_identity(value, identity):
    require(all(value[k] == identity[k] for k in IDENTITY), 'Complete native identity and catalog uses')


def polynomial_product(a, b):
    out = [Q(0)] * (len(a) + len(b) - 1)
    for i, x in enumerate(a):
        for j, y in enumerate(b): out[i + j] += x * y
    return trim(out)


def bernstein_bounds(a):
    n = len(a) - 1
    def choose(i, j):
        return math.factorial(i) // (math.factorial(j) * math.factorial(i - j))
    coefficients = [sum((a[j] * Q(choose(i, j), choose(n, j)) for j in range(i + 1)), Q(0)) for i in range(n + 1)]
    return min(coefficients), max(coefficients)


def scaled_moment(length, width, value):
    products = [-width * x * y for x in length for y in value]
    lo, hi = min(products), max(products); scale = 1 << SETTINGS['bits']
    return Q((lo * scale).numerator // (lo * scale).denominator, scale), Q(-((-hi * scale).numerator // (-hi * scale).denominator), scale)


def cuts_and_face(a, b, axes):
    faces = [(k, axis.index(a[k])) for k, axis in enumerate(axes) if a[k] == b[k] and a[k] in axis[1:-1]]
    require(a != b and len(faces) <= 1, 'Nondegenerate single-face geometry')
    cuts = {Q(0), Q(1)}
    for k, axis in enumerate(axes):
        if a[k] != b[k]: cuts.update((v - a[k]) / (b[k] - a[k]) for v in axis[1:-1] if 0 < (v - a[k]) / (b[k] - a[k]) < 1)
    return sorted(cuts), faces


def check_moments(record, edge, a, b, axes, speeds):
    cuts, faces = cuts_and_face(a, b, axes); require(len(faces) == 1, 'Exactly one aligned face')
    axis, face = faces[0]; length = interval(record['length']); square = sum((y - x) ** 2 for x, y in zip(a, b))
    require(length[0] > 0 and length[0] ** 2 <= square <= length[1] ** 2, 'Exact positive edge-length enclosure')
    require(record['edge'] == edge and record['endpoint_nodes'] == [edge, edge + 1] and record['normal_axis'] == axis
            and tuple(map(Q, record['a_exact'])) == a and tuple(map(Q, record['b_exact'])) == b, 'Moment outer geometry')
    require(len(record['patches']) == len(cuts) - 1, 'Complete ordered face partition')
    signs = []; extrema = []
    for patch, left, right in zip(record['patches'], cuts, cuts[1:]):
        middle = [a[k] + (left + right) / 2 * (b[k] - a[k]) for k in range(3)]
        cell = [min(len(v) - 2, max(i for i, x in enumerate(v) if x <= middle[k])) for k, v in enumerate(axes)]
        minus = list(cell); plus = list(cell); minus[axis] = face - 1; plus[axis] = face
        require(interval(patch['u']) == (left, right) and patch['normal_axis'] == axis and Q(patch['normal_coordinate']) == axes[axis][face]
                and patch['minus_cell'] == minus and patch['plus_cell'] == plus
                and tuple(map(Q, patch['a_exact'])) == a and tuple(map(Q, patch['b_exact'])) == b, 'Patch parameter/cell/native geometry')
        samples = []
        for side in (minus, plus):
            samples.append([r.basis_value(axes, speeds, side, [a[k] + (left + (right - left) * t) * (b[k] - a[k]) for k in range(3)], axis)
                            for t in (Q(0), Q(1, 2), Q(1))])
        vm, vp = [r.interpolate([v[0] for v in side]) for side in samples]
        gm, gp = [r.interpolate([v[1] for v in side]) for side in samples]
        bm, bp = [(min(side[0][2]), max(side[0][2])) for side in samples]
        bounds = max(bm[0], bp[0]), min(bm[1], bp[1])
        require(vm == vp and 0 < bounds[0] <= bounds[1], 'Positive continuous original eight-node face velocity')
        for key, expected in [('velocity_polynomial', vm), ('minus_velocity_normal_polynomial', gm), ('plus_velocity_normal_polynomial', gp),
                              ('minus_vertex_bounds', bm), ('plus_vertex_bounds', bp), ('velocity_vertex_bounds', bounds)]:
            require(patch[key] == encoded(expected), 'Direct nodal polynomial/bounds: ' + key)
        size = max(len(gm), len(gp)); jump = trim([(gm[i] if i < len(gm) else 0) - (gp[i] if i < len(gp) else 0) for i in range(size)])
        exact, points = r.polynomial_range(jump); eligible = exact[0] >= 0; signs.append(eligible)
        require(patch['jump_numerator'] == encoded(jump) and interval(patch['exact_jump_range']) == exact
                and patch['convex_normal_jump'] == eligible, 'Whole-patch quadratic convex jump, not endpoint-only')
        extrema.append(dict(edge=edge, u=(left, right), extrema_parameters=points, exact_jump_range=exact))
    valid = all(signs)
    require(record['status'] == ('bounded_convex_patch_moments' if valid else 'ineligible_nonconvex_normal_jump')
            and record['normal_patch_integrations'] == (len(signs) if valid else 0), 'Eligibility and completed moment count')
    for patch in record['patches']:
        if not valid:
            require(patch['minus'] is patch['plus'] is patch['tail_record'] is None, 'Ineligible edge never acquires support moments'); continue
        left, right = interval(patch['u']); width = right - left
        numerators = [polynomial_product(list(map(Q, patch[key])), h)
                      for key in ('minus_velocity_normal_polynomial', 'plus_velocity_normal_polynomial')
                      for h in ([1 - left, -width], [left, width])]
        require(patch['numerators'] == encoded(numerators) and len(patch['inverse_square_integral_bounds']) == 4
                and len(patch['minus']) == len(patch['plus']) == 2, 'Four global endpoint-weight numerators and intervals')
        velocity = list(map(Q, patch['velocity_polynomial'])); low, high = bernstein_bounds(velocity)
        vertices = interval(patch['velocity_vertex_bounds']); low, high = max(low, vertices[0]), min(high, vertices[1])
        require(0 < low <= high, 'Positive reciprocal-series bound')
        center = (low + high) / 2; rho = (high - low) / (high + low); degree = 0 if rho == 0 else SETTINGS['terms']
        factor = rho ** (degree + 1) * ((degree + 2) - (degree + 1) * rho) / (center ** 2 * (1 - rho) ** 2)
        tails = [max(abs(x) for x in bernstein_bounds(p)) * factor for p in numerators]
        tail = dict(velocity_bounds=(low, high), rho=rho, series_degree=degree,
                    reciprocal_tail=rho ** (degree + 1) / (center * (1 - rho)), inverse_square_tails=tails)
        require(patch['tail_record'] == encoded(tail), 'Exact saved tail metadata from native polynomials')
        for numerator, raw, saved, error in zip(numerators, patch['inverse_square_integral_bounds'], patch['minus'] + patch['plus'], tails):
            integral = interval(raw)
            require(integral[1] - integral[0] == 2 * error, 'Saved inverse-square interval width equals explicit tail')
            require(interval(saved) == scaled_moment(length, width, integral), 'Outward moment scaling and dyadic rounding')
    return valid, extrema


def cached_action(record):
    name = record['file']; path = ROOT / name
    if name not in CACHE:
        pin(path, record['sha256']); CACHE[name] = read(path)
    else: require(r.PINNED[str(path)] == record['sha256'], 'Consistent cached source hash')
    value = CACHE[name]
    require(record['json_pointer'].startswith('/'), 'Absolute saved JSON pointer')
    for key in record['json_pointer'][1:].split('/'):
        key = key.replace('~1', '/').replace('~0', '~')
        value = value[int(key)] if isinstance(value, list) else value[key]
    require(interval(record['bounds']) == interval(value), 'Original half-edge action cache pointer')
    return interval(value)


def check_case(identity, brief, axes, speeds, oracle, path_rows, gradient_rows, cpp_rows, prepared):
    event = identity['event']; n = 1029 if event == 981 else 1031
    output = RUN / ('event_%d.json.gz' % event); full = read(output); side = read(Path(str(output) + '.identifiers.json'))
    for record in (full, brief, side): same_identity(record, identity)
    require(side['file_sha256'] is None and side['expected_file'] == str(output.relative_to(ROOT)) and side['prepared_sha256'] == EXPECTED
            and side['input_sha256'] == prepared['input_sha256'], 'Predeclared native sidecar')
    require(brief['result_file'] == output.name and brief['result_sha256'] == sha(output) and full['settings'] == SETTINGS, 'Result summary/hash/settings')
    require(full['status'] == brief['status'] and full['original_convergence_flag'] == brief['original_convergence_flag'] == '0'
            and full['candidate_convergence_status'] is brief['candidate_convergence_status'] is None, 'No flag promotion')
    original = identity['native_context']['original_status']
    require(original['ray_converged'] == original['ray_derivatives_evaluated'] == '0' and all(original['source_d' + k] == '' for k in 'xyz'), 'Original false flags and blank source partials')
    states = {}; coordinate_records = []
    for state in ('initial', 'final'):
        selected = [v for v in path_rows if int(v['event']) == event and v['state'] == state]
        require([int(v['node']) for v in selected] == list(range(n)), 'Exact ordered native node roster')
        path = []
        for row in selected:
            point = []
            for key in 'xyz':
                value = float(row[key]); other = float.fromhex(row[key + '_hex'])
                require(math.isfinite(value) and value.hex() == other.hex(), 'Canonical binary64 coordinate token/hex, including signed zero'); point.append(Q(value))
            path.append(tuple(point))
            if state == 'final': coordinate_records.append(dict(node=int(row['node']), exact_rational=point, decimal_tokens=[row[k] for k in 'xyz'], binary64_hex=[row[k + '_hex'] for k in 'xyz']))
        states[state] = path
    path, start = states['final'], states['initial']
    require(full['coordinate_provenance'] == encoded(coordinate_records) and all(axes[k][0] <= p[k] <= axes[k][-1] for p in path for k in range(3)), 'Exact final iterator geometry and finite box')
    require(path[0] == start[0] == tuple(Q(float(identity['native_context']['source_native'][k])) for k in 'xyz')
            and path[-1] == start[-1] == tuple(Q(float(identity['native_context']['receiver_native'][k])) for k in 'xyz'), 'Unchanged authoritative endpoints')
    require(full['iterator_paths_sha256'] == sha(ITER / 'results/paths.csv') and full['iterator_review_sha256'] == sha(ITER_REVIEW / 'review.json')
            and full['starting_oracle_sha256'] == sha(BENCH / 'oracle.json.gz'), 'Geometry/review/oracle linkage')
    polygon = next(v for v in oracle['polygons'] if v['event'] == event and v['stage_integer'] == 3); same_identity(polygon, identity)
    require(polygon['node_count'] == n and [tuple(map(Q, p)) for p in polygon['coordinates_exact_rational']] == start, 'Exact accepted-half starting geometry')
    records = full['edge_records']; require(len(records) == n - 1, 'Complete edge inventory')
    base = [None] + [[(Q(0), Q(0)) for k in range(3)] for i in range(1, n - 1)] + [None]
    inventory = []; blocked = set(); aligned = {}; final_action = (Q(0), Q(0))
    for edge, (a, b, record) in enumerate(zip(path, path[1:], records)):
        cuts, faces = cuts_and_face(a, b, axes); normals = [k for k, index in faces]
        require(record['edge'] == edge and record['endpoint_nodes'] == [edge, edge + 1] and record['blocked_axes'] == normals and len(record['components']) == 2, 'Native edge and aligned-normal inventory')
        inventory.append(dict(edge=edge, aligned_internal_faces=faces, normal_patch_count=len(cuts) - 1 if faces else 0))
        if normals: aligned[str(edge)] = normals[0]
        action = interval(record['action']); require(action[0] > 0, 'Positive finite nondegenerate saved action'); final_action = add(final_action, action)
        for side_index, components in enumerate(record['components']):
            node = edge + side_index
            if node in (0, n - 1): require(components is None, 'Only fixed endpoint whole side omitted'); continue
            require(components is not None and len(components) == 3, 'Complete internal endpoint side')
            for axis, value in enumerate(components):
                require((value is None) == (axis in normals), 'Internal None only on the aligned normal')
                if value is None: blocked.add((node, axis))
                else: base[node][axis] = add(base[node][axis], interval(value))
    ordinary = [dict(edge=v['edge'], side=j, node=v['edge'] + j, axis=k, contribution=interval(value))
                for v in records for j, components in enumerate(v['components']) if components is not None
                for k, value in enumerate(components) if value is not None and (v['edge'] + j, k) in blocked]
    expected_base = dict(components=base, aligned_edges=aligned, blocked_slots=sorted(blocked), ordinary_contributions_in_blocked_slots=ordinary)
    require(full['ordinary_base'] == encoded(expected_base) and full['aligned_edge_inventory'] == encoded(inventory)
            and full['geometric_blocked_slots'] == encoded(sorted(blocked)), 'All ordinary adjacent contributions and exact geometry masks')
    available = [list(v) if v is not None else None for v in base]
    for node, axis in blocked: available[node][axis] = None
    require(full['available_components'] == encoded([dict(node=i, components=available[i]) for i in range(1, n - 1)]), 'Full available component sum')
    available_norm = r.norm(path, available, axes); r.check_norm(full['available_norm'], available_norm)
    require(full['available_projected_components'] == encoded(available_norm[1]) and brief['available_norm'] == full['available_norm'], 'True-box available vector and summary')
    gradient = [v for v in gradient_rows if int(v['event']) == event and v['state'] == 'final']
    require([(int(v['node']), int(v['axis'])) for v in gradient] == [(i, k) for i in range(1, n - 1) for k in range(3)]
            and {(int(v['node']), int(v['axis'])) for v in gradient if v['available'] == '0'} == blocked, 'Complete C++ final gradient/native mask')
    errors = []; error_norm = (Q(0), Q(0))
    for row in gradient:
        node, axis = int(row['node']), int(row['axis']); value = float(row['component'])
        require(math.isfinite(value) and value.hex() == float.fromhex(row['component_hex']).hex() and row['available'] in ('0', '1'), 'C++ derivative decimal/hex/availability')
        if available[node][axis] is None: continue
        lo, hi = available[node][axis]; lower, upper = Q(value) - hi, Q(value) - lo
        error_norm = add(error_norm, (max(lower, -upper, Q(0)) ** 2, max(abs(lower), abs(upper)) ** 2))
        errors.append(dict(node=node, axis=axis, cpp_hex=row['component_hex'], component_bounds=(lo, hi), error_bounds=(lower, upper)))
    require(full['cpp_available_comparison']['component_errors'] == encoded(errors)
            and interval(full['cpp_available_comparison']['error_norm_squared_bounds']) == error_norm, 'Exact available C++ error arithmetic')
    cached = polygon['action']['edges']; account = full['action']; starting = (Q(0), Q(0)); net = (Q(0), Q(0)); changes = []
    require([v['edge'] for v in cached] == list(range(n - 1)), 'Complete half-edge cache roster')
    for edge, (record, prior) in enumerate(zip(records, cached)):
        before = cached_action(prior); after = interval(record['action']); same = path[edge:edge + 2] == start[edge:edge + 2]
        difference = (Q(0), Q(0)) if same else (after[0] - before[1], after[1] - before[0])
        starting = add(starting, before); net = add(net, difference)
        changes.append(dict(edge=edge, identical_endpoint_pair=same, starting_action=before, final_action=after, difference=difference, starting_cache=prior))
    classification = 'resolved_decrease' if net[1] < 0 else 'resolved_increase' if net[0] > 0 else 'inconclusive'
    cpp = next(v for v in cpp_rows if int(v['event']) == event); value = float(cpp['action'])
    require(math.isfinite(value) and value.hex() == float.fromhex(cpp['action_hex']).hex(), 'C++ final action decimal/hex')
    require(account['edges'] == encoded(changes) and interval(account['final_action']) == final_action
            and interval(account['starting_half_action']) == interval(polygon['action']['full_bounds']) == starting
            and interval(account['paired_net_change']) == interval(brief['net_action']) == net
            and account['classification'] == brief['net_action_classification'] == classification
            and Q(account['cpp_final_action_exact']) == Q(value)
            and interval(account['cpp_final_action_error']) == (Q(value) - final_action[1], Q(value) - final_action[0]), 'Complete final/half action accounting and exact unchanged-edge cancellation')
    moments = full['patch_moment_records']; require([v['edge'] for v in moments] == [int(k) for k in aligned], 'All and only aligned edges have moment records')
    flattened = []; failed = []; extrema = []; completed = 0
    for moment in moments:
        edge = moment['edge']; valid, checked = check_moments(moment, edge, path[edge], path[edge + 1], axes, speeds); extrema.extend(checked)
        if valid:
            completed += len(moment['patches'])
            flattened.extend(dict(p, edge=edge, endpoint_nodes=[edge, edge + 1], length=moment['length']) for p in moment['patches'])
        else: failed.append(dict(edge=edge, status=moment['status']))
    require(full['patches'] == flattened and full['normal_ineligibility'] == failed, 'Exact moment flattening and preserved ineligibility')
    proposal = full['proposal']; support = full['full_support']; support_norm = None
    require(brief['proposal_status'] == (proposal['status'] if proposal else None) and brief['full_support_status'] == support['status']
            and brief['full_support_norm'] == support.get('norm'), 'Summary proposal/support linkage')
    if failed:
        require(proposal is None and support == dict(status='inconclusive_unproved_patch_convexity')
                and full['status'] == 'completed_ineligible_support_assessment', 'Unproved convexity remains inconclusive')
    else:
        update_sweeps = min(10000, proposal['sweeps'] + int(proposal['status'] == 'proposal_unusable'))
        require(full['status'] == 'completed_final_action_support_assessment' and proposal['max_sweeps'] == 10000
                and 0 <= proposal['sweeps'] <= 10000 and 0 <= proposal['coordinate_updates'] <= update_sweeps * len(flattened), 'Declared bounded proposal, including a partially failed sweep; no minimum claim')
        require(len(proposal['theta']) == len(proposal['theta_hex']) == len(proposal['theta_exact']) == len(flattened), 'One coefficient shared by both endpoint moments')
        theta = []
        for value, text, exact in zip(proposal['theta'], proposal['theta_hex'], proposal['theta_exact']):
            require(math.isfinite(value) and 0 <= value <= 1 and float(value).hex() == float.fromhex(text).hex() and Q(value) == Q(exact), 'Exact feasible emitted binary64 theta'); theta.append(Q(exact))
        if proposal['status'] == 'proposal_unusable':
            require(proposal['reason'] and proposal['termination'] == 'unusable_midpoint_arithmetic'
                    and support == dict(status='inconclusive_unusable_proposal', reason=proposal['reason']), 'Unusable fit remains inconclusive')
        else:
            require(proposal['status'] == 'bounded_midpoint_proposal' and proposal['reason'] is None
                    and proposal['termination'] in ('coefficients_unchanged', 'sweep_budget')
                    and all(math.isfinite(proposal[k]) and proposal[k] >= 0 for k in ('initial_midpoint_objective', 'final_midpoint_objective')), 'Finite proposal diagnostics without fitting again')
            vector = [list(v) if v is not None else None for v in base]; contributions = []; zero_columns = []
            for index, (patch, weight) in enumerate(zip(flattened, theta)):
                nonzero = False
                for side_index in (0, 1):
                    node, axis = patch['edge'] + side_index, patch['normal_axis']; minus = interval(patch['minus'][side_index]); plus = interval(patch['plus'][side_index])
                    term = ((1 - weight) * minus[0] + weight * plus[0], (1 - weight) * minus[1] + weight * plus[1])
                    contributions.append(dict(patch=index, edge=patch['edge'], side=side_index, node=node, axis=axis, theta_exact=weight, contribution=term, fixed_endpoint=node in (0, n - 1)))
                    if 0 < node < n - 1:
                        vector[node][axis] = add(vector[node][axis], term); nonzero |= sum(plus) != sum(minus)
                if not nonzero: zero_columns.append(index)
            require(proposal['exact_zero_midpoint_columns'] == zero_columns and support['status'] == 'feasible_constant_patch_support'
                    and support['theta_exact'] == encoded(theta) and support['patch_contributions'] == encoded(contributions)
                    and support['ordinary_contributions_in_blocked_slots'] == encoded(ordinary)
                    and support['vector'] == encoded([dict(node=i, components=vector[i]) for i in range(1, n - 1)]), 'Coupled support with every ordinary contribution retained')
            projected = r.norm(path, vector, axes); r.check_norm(support['norm'], projected)
            require(not projected[2] and support['projected_components'] == encoded(projected[1]), 'Complete full-vector true-box projection')
            support_norm = projected[0]
    return dict(identity, nodes=n, saved_edges=n - 1, aligned_edges=len(aligned), normal_patches=len(extrema), completed_normal_patches=completed,
                proposal_calls=int(proposal is not None), available_squared_bounds=available_norm[0], available_cpp_error_squared_bounds=error_norm,
                final_action=final_action, starting_half_action=starting, net_action=net, net_action_classification=classification,
                cpp_final_action_error=interval(account['cpp_final_action_error']), full_support_status=support['status'], feasible_support_squared_bounds=support_norm,
                convexity_extrema=extrema, original_convergence_flag='0', candidate_convergence_status=None)


def main():
    require(not (HERE / 'review.json').exists() and not (HERE / 'review.json').is_symlink(), 'Fresh review output required')
    approval = read(HERE / 'source_review.json')
    require(approval['status'] == 'passed' and approval['checker_sha256'] == sha(Path(__file__)), 'Independent source approval before execution')
    for path in (Path(__file__), HERE / 'README.md', HERE / 'source_review.json', READER): pin(path, sha(path))
    pin(RUN / 'prepared.json', EXPECTED); prepared = read(RUN / 'prepared.json')
    for base, key in ((ROOT, 'input_sha256'), (RUN, 'output_sha256'), (Path('/'), 'runtime_sha256')):
        for name, digest in prepared[key].items(): pin(base / name, digest)
    pin(Path(sys.executable), prepared['python']['sha256'])
    summary = read(RUN / 'summary.json'); execution = read(RUN / 'execution.json'); outer = read(RUN / 'outer_reaping.json'); prelaunch = read(RUN / 'prelaunch_review.json')
    require(summary['status'] == execution['status'] == 'completed_bounded_final_tangent_support_audit' and execution['return_code'] == 0
            and summary['error'] is None and outer['status'] == 'completed_and_reaped' and outer['tool_exit_code'] == 0
            and outer['wrapper_pid'] == execution['pid'] and outer['wrapper_process_absent'], 'Terminal reaped native calculation')
    for key, name in (('prepared_sha256', 'prepared.json'), ('summary_sha256', 'summary.json'), ('execution_sha256', 'execution.json'), ('prelaunch_review_sha256', 'prelaunch_review.json')): pin(RUN / name, outer[key])
    pin(RUN / 'outer_reaping.json', sha(RUN / 'outer_reaping.json'))
    require(prelaunch['status'] == 'passed' and prelaunch['prepared_sha256'] == EXPECTED, 'Reviewed native preparation')
    for record in (summary, execution): require(record['prepared_sha256'] == EXPECTED and record['prelaunch_review_sha256'] == sha(RUN / 'prelaunch_review.json'), 'Preparation/approval ledger binding')
    require(execution['summary_sha256'] == sha(RUN / 'summary.json') and execution['environment'] == prepared['environment'], 'Terminal environment and summary binding')
    require(summary['output_sha256'] == execution['output_sha256'] and {p.name for p in RUN.glob('event_*')} == set(summary['output_sha256']), 'Exact closed output inventory')
    for name, digest in summary['output_sha256'].items(): pin(RUN / name, digest)
    require(summary['settings'] == prepared['settings'] == SETTINGS and summary['budget'] == dict(combined_edges=2058, normal_patches=65, proposal_fits=2, sweeps_per_fit=10000), 'Frozen settings/budget')
    require(all(summary[k] == 0 for k in ('trace_calls', 'field_calls', 'optimizer_iterations', 'metric_solves', 'rounded_trials')) and execution['subprocess_calls'] == 0
            and summary['fixed_endpoint_partials_reported'] is summary['source_model_accuracy_assessed'] is False, 'No extra numerical work or accuracy promotion')
    identities = read(RUN / 'native_contexts.json'); previous = read(ITER_REVIEW / 'review.json')
    require([v['event'] for v in identities] == [981, 987] and identities == summary['native_contexts'] == execution['native_contexts'] == outer['native_contexts']
            == prelaunch['native_contexts'] == previous['native_contexts'] == read(ITER / 'native_contexts.json'), 'Entire native/terminal identity roster')
    require(previous['status'] == 'passed' and read(ITER_REVIEW / 'execution_receipt.json')['child_reaped'], 'Reviewed terminal iterator')
    for key, name in (('native_prepared_sha256', 'prepared.json'), ('native_summary_sha256', 'summary.json'), ('native_execution_sha256', 'execution.json'), ('outer_reaping_sha256', 'outer_reaping.json')): pin(ITER / name, previous[key])
    controls = read(RUN / 'controls/summary.json'); checked = read(RUN / 'controls/review.json'); closed = read(RUN / 'controls/execution_receipt.json')
    require(controls['status'] == checked['status'] == closed['status'] == 'passed' and checked['summary_sha256'] == sha(RUN / 'controls/summary.json')
            and closed['return_code'] == 0 and closed['child_reaped'], 'Reviewed/reaped compact algebra controls')
    for key, name in (('helper_sha256', 'aligned_face_support.py'), ('primitive_sha256', 'source/diagnostics/trilinear_action_bounds.py')):
        require(controls[key] == checked[key] == sha(RUN / name), 'Controlled moment/primitive source')
    for name, digest in closed['output_sha256'].items(): pin(RUN / 'controls' / name, digest)
    catalog_count = r.native_joins(identities); axes, speeds = r.model(); oracle = read(BENCH / 'oracle.json.gz')
    require(oracle['native_contexts'] == identities and read(BENCH / 'review.json')['status'] == 'passed', 'Reviewed cache native roster')
    tables = []
    for name in ('paths.csv', 'gradients.csv', 'summary.csv'):
        path = ITER / 'results' / name; side = read(Path(str(path) + '.identifiers.json')); table = rows(path)
        require(side['native_contexts'] == identities and side['prepared_sha256'] == sha(ITER / 'prepared.json') and side['expected_file'] == str(path.relative_to(ROOT))
                and side['original_convergence_flag'] == '0' and side['candidate_convergence_status'] is None, 'Numeric iterator table native sidecar')
        require(all(v['event'] in ('981', '987') and v['station'] == '160' for v in table), 'No extra numeric native identity')
        if name != 'summary.csv': require(all(v['state'] in ('initial', 'final') for v in table), 'Exact saved state roster')
        else: require([v['event'] for v in table] == ['981', '987'], 'One terminal C++ row per event')
        tables.append(table)
    require([v['event'] for v in summary['cases']] == [981, 987], 'Complete native cases')
    reports = [check_case(identity, brief, axes, speeds, oracle, *tables, prepared=prepared) for identity, brief in zip(identities, summary['cases'])]
    expected_counts = dict(attempted_edges=2058, completed_edges=2058, attempted_normal_patches=65,
                           completed_normal_patches=sum(v['completed_normal_patches'] for v in reports), proposal_calls=sum(v['proposal_calls'] for v in reports))
    require(sum(v['saved_edges'] for v in reports) == 2058 and sum(v['normal_patches'] for v in reports) == 65
            and summary['counts'] == expected_counts and all(execution[k] == v for k, v in expected_counts.items()), 'Exact executed/saved call counts')
    for path, digest in list(r.PINNED.items()): pin(Path(path), digest)
    result = dict(status='passed', reviewer='earthscope_discovery', checker_sha256=sha(Path(__file__)), source_review_sha256=sha(HERE / 'source_review.json'),
                  native_prepared_sha256=EXPECTED, native_summary_sha256=sha(RUN / 'summary.json'), native_execution_sha256=sha(RUN / 'execution.json'), outer_reaping_sha256=sha(RUN / 'outer_reaping.json'),
                  native_contexts=identities, cases=reports, checks=r.CHECKS, original_catalog_rows=catalog_count,
                  input_sha256={str(Path(p).relative_to(ROOT)) if str(p).startswith(str(ROOT) + '/') else p: h for p, h in r.PINNED.items()},
                  numerical_integrations=0, numerical_evaluator_imports=0, fitting_calls=0, native_calls=0, pure_saved_reader_imports=1,
                  limitations=['Saved primitive intervals rely on their pinned source and reviewed controls; no action, tangent or moment reintegration.',
                               'Direct original nodal basis, exact quadratic extrema, explicit tail metadata and outward moment scaling are independently reconstructed.',
                               'One exact binary64 coefficient is shared by both endpoint moments of each convex patch. Every ordinary incident-edge contribution remains.',
                               'The true-box norm encloses one feasible restricted-family support. Its lower bound is not a lower bound on the minimum over all supports; a large witness is inconclusive.',
                               'The fit is not rerun or certified optimal. Net action concerns final versus saved half geometry, not every intermediate decision. No Ray flag, first-arrival, endpoint/model accuracy or field acceptance claim.'])
    with (HERE / 'review.json').open('x') as stream:
        json.dump(encoded(result), stream, indent=2, sort_keys=True, allow_nan=False); stream.write('\n')
    print(json.dumps(dict(status='passed', review_sha256=sha(HERE / 'review.json'), checks=r.CHECKS, pinned_files=len(r.PINNED))))


if __name__ == '__main__':
    main()
