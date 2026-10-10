#!/usr/bin/env python3
"""Saved component sums and native joins only; no primitive or evaluator calls."""
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
RUN = DATA / 'hayward_cmj_original_gradient_bounds_001'
FACE = DATA / 'hayward_cmj_face_action_001'
SAVED = DATA / 'hayward_cmj_saved_gradient_001'
CUT = DATA / 'hayward_cmj_original_cut_inventory_001'
EXPECTED = '85f409745cb3f89fd27c7ea50a91b9339a67349fe660fd77d2ba759e36e5db45'
READER = DATA / 'hayward_cmj_post_half_step_tangent_review_001/check_saved.py'
READER_SHA = '8c300b68d8647ddec4b64acf792625ef3ac68b353d10058c0418f9b169eed46e'
if hashlib.sha256(READER.read_bytes()).hexdigest() != READER_SHA:
    raise ValueError('Changed pure saved-data reader')
spec = importlib.util.spec_from_file_location('original_saved_reader', str(READER))
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)  # Stdlib definitions only; no main or numerical primitive.
require, sha, read, rows, pin = r.require, r.sha, r.read, r.rows, r.pin
interval, add, encoded = r.interval, r.add, r.encoded
SETTINGS = dict(terms=8, subdivisions=1, bits=128)
IDENTITY = ('event', 'station', 'native_context', 'catalog_uses')


def same_identity(record, identity):
    require(all(record[k] == identity[k] for k in IDENTITY), 'Complete native/catalog identity')


def square(bounds):
    lo, hi = bounds
    return max(lo, -hi, Q(0)) ** 2, max(abs(lo), abs(hi)) ** 2


def check_case(identity, brief, axes, path_table, status_table, raw_table, norm_table):
    event = identity['event']; n = 1029 if event == 981 else 1031
    output = RUN / ('event_%d.json.gz' % event)
    full = read(output); side = read(Path(str(output) + '.identifiers.json'))
    for record in (full, side, brief): same_identity(record, identity)
    require(side['expected_file'] == str(output.relative_to(ROOT)) and side['prepared_sha256'] == EXPECTED
            and side['original_convergence_flag'] == '0' and side['candidate_convergence_status'] is None, 'Predeclared identified numeric output')
    require(brief['result_file'] == output.name and brief['result_sha256'] == sha(output)
            and full['settings'] == SETTINGS and full['status'] == brief['status'] == 'completed_original_component_bounds', 'Completed case and settings')
    require(full['original_convergence_flag'] == brief['original_convergence_flag'] == '0'
            and full['candidate_convergence_status'] is brief['candidate_convergence_status'] is None, 'No status promotion')
    status = [v for v in status_table if int(v['event']) == event]
    require(len(status) == 1 and status[0] == identity['native_context']['original_status'], 'Entire original status row')
    status = status[0]
    require(status['station'] == '160' and status['ray_converged'] == status['ray_derivatives_evaluated'] == '0'
            and all(status['source_d' + k] == '' for k in 'xyz'), 'Original false flags and blank source partials')
    original = [v for v in path_table if int(v['event']) == event]
    raw = [v for v in raw_table if int(v['event']) == event]
    require(len(original) == len(raw) == n and [int(v['node']) for v in original] == list(range(n))
            and full['original_rows'] == original, 'Complete unchanged ordered original path rows')
    path = []; observed = []; legacy = []
    for node, (row, old) in enumerate(zip(original, raw)):
        require(all(old[k] == v for k, v in row.items()) and old['variant'] == 'old'
                and row['station'] == '160' and int(old['node']) == node, 'Every native coordinate/metadata cell retained')
        require(all(row[k] == v for k, v in status.items() if k.startswith(('source_', 'receiver_')) and k in row), 'Path/status native association')
        point = tuple(Q(float(row[k])) for k in 'xyz')
        require(all(math.isfinite(float(row[k])) and axes[j][0] <= point[j] <= axes[j][-1] for j, k in enumerate('xyz')), 'Finite original binary64 geometry in physical box')
        path.append(point); fixed = node in (0, n - 1)
        require(old['is_free'] == ('0' if fixed else '1'), 'Fixed/free node roster')
        if fixed:
            require(all(old[prefix + k] == '' for prefix in ('raw_g', 'projected_g') for k in 'xyz'), 'Fixed endpoint partials omitted')
            observed.append(None); legacy.append(None)
        else:
            require(all(math.isfinite(float(old[prefix + k])) for prefix in ('raw_g', 'projected_g') for k in 'xyz'), 'Finite saved raw and legacy projected values')
            observed.append(tuple(Q(float(old['raw_g' + k])) for k in 'xyz'))
            legacy.append(tuple(Q(float(old['projected_g' + k])) for k in 'xyz'))
    require(full['path'] == encoded(path) and full['saved_raw'] == encoded(observed)
            and full['legacy_projected'] == encoded(legacy), 'Exact saved raw/binary64 coordinate and gradient mapping')
    context = identity['native_context']
    require(path[0] == tuple(Q(float(context['source_native'][k])) for k in 'xyz')
            and path[-1] == tuple(Q(float(context['receiver_native'][k])) for k in 'xyz'), 'Unchanged identified fixed endpoints')
    old_norm = [v for v in norm_table if int(v['event']) == event]
    require(len(old_norm) == 1 and old_norm[0] == full['saved_norm'] and old_norm[0]['variant'] == 'old'
            and all(old_norm[0][k] == v for k, v in status.items()), 'Legacy norm/status row preserved, not reinterpreted')
    cut_file = CUT / ('event_%d.json.gz' % event); cut = read(cut_file)
    same_identity(cut, identity); require(full['cut_inventory_sha256'] == sha(cut_file), 'Reviewed original cut inventory binding')
    edges = full['tangent_edge_records']; require(len(edges) == len(cut['edge_records']) == n - 1, 'Full original edge inventory')
    vector = [[(Q(0), Q(0)) for k in range(3)] for p in path]; vector[0] = vector[-1] = None
    aligned = []; blocked = set()
    for index, (edge, old) in enumerate(zip(edges, cut['edge_records'])):
        a, b = path[index:index + 2]
        require(a != b and edge['edge'] == old['edge'] == index and edge['endpoint_nodes'] == [index, index + 1]
                and tuple(map(Q, old['a_exact'])) == a and tuple(map(Q, old['b_exact'])) == b, 'Exact original edge geometry and node joins')
        faces = [(k, axis.index(a[k])) for k, axis in enumerate(axes) if a[k] == b[k] and a[k] in axis[1:-1]]
        require(len(faces) <= 1 and edge['blocked_axes'] == [k for k, face in faces] and len(edge['components']) == 2, 'Geometric ordinary-component availability')
        aligned.append(dict(edge=index, aligned_internal_faces=faces))
        for side_index, terms in enumerate(edge['components']):
            node = index + side_index
            if node in (0, n - 1):
                require(terms is None, 'Only fixed endpoint whole sides omitted'); continue
            require(terms is not None and len(terms) == 3, 'All internal side component slots present')
            for axis, value in enumerate(terms):
                require((value is None) == (axis in edge['blocked_axes']), 'Aligned internal normal None is not zero')
                if value is None: blocked.add((node, axis))
                else: vector[node][axis] = add(vector[node][axis], interval(value))
    for node, axis in blocked: vector[node][axis] = None
    require(full['aligned_edge_inventory'] == encoded(aligned) and full['geometric_blocked_slots'] == encoded(sorted(blocked))
            and full['free_node_components'] == encoded([dict(node=i, components=vector[i]) for i in range(1, n - 1)]), 'Adjacent ordinary sums and full incident-edge mask')
    projected = r.norm(path, vector, axes); r.check_norm(full['projected_norm'], projected)
    require(full['available_projected_components'] == encoded(projected[1]) and set(projected[2]) == blocked, 'Exact physical-box projection, no activity band')
    saved_vector = [None if row is None else [(x, x) for x in row] for row in observed]
    saved_projected = r.norm(path, saved_vector, axes); r.check_norm(full['saved_raw_under_true_box'], saved_projected)
    require(full['saved_true_box_components'] == encoded(saved_projected[1]), 'Saved raw vector projected onto the same true box')
    comparisons = []; errors = reference_norm = (Q(0), Q(0)); largest = Q(0)
    for node in range(1, n - 1):
        for axis, bounds in enumerate(vector[node]):
            if bounds is None: continue
            value = observed[node][axis]; error = value - bounds[1], value - bounds[0]
            errors = add(errors, square(error)); reference_norm = add(reference_norm, square(bounds))
            largest = max(largest, abs(error[0]), abs(error[1]))
            comparisons.append(dict(node=node, axis=axis, coordinate_exact=path[node][axis], saved_raw_exact=value,
                saved_raw_hex=float(value).hex(), reference_bounds=bounds, error_bounds=error, legacy_projected_exact=legacy[node][axis]))
    require(full['component_comparison'] == encoded(comparisons) and interval(full['error_squared_norm']) == errors
            and interval(full['raw_available_squared_norm']) == reference_norm, 'Every raw-minus-bound interval and exact squared norm')
    require(brief['component_edges'] == n - 1 and brief['available_components'] == len(comparisons)
            and brief['unavailable_components'] == len(blocked) and interval(brief['error_squared_norm']) == errors
            and brief['projected_norm'] == full['projected_norm'], 'Summary component/norm joins')
    return dict(identity, nodes=n, edges=n - 1, available_components=len(comparisons), unavailable_components=len(blocked),
                raw_error_squared_bounds=errors, largest_absolute_component_error_upper=largest,
                reference_available_squared_bounds=reference_norm, reference_true_box_squared_bounds=projected[0],
                saved_raw_true_box_squared_bounds=saved_projected[0], exact_physical_boundary_components=projected[3],
                original_convergence_flag='0', candidate_convergence_status=None)


def main():
    require(not (HERE / 'review.json').exists() and not (HERE / 'review.json').is_symlink(), 'Fresh review output')
    approval = read(HERE / 'source_review.json')
    require(approval['status'] == 'passed' and approval['checker_sha256'] == sha(Path(__file__)), 'Independent source approval')
    for p in (Path(__file__), HERE / 'README.md', HERE / 'source_review.json'): pin(p, sha(p))
    pin(READER, READER_SHA); pin(RUN / 'prepared.json', EXPECTED); prepared = read(RUN / 'prepared.json')
    for base, key in ((ROOT, 'input_sha256'), (RUN, 'output_sha256'), (Path('/'), 'runtime_sha256')):
        for name, digest in prepared[key].items(): pin(base / name, digest)
    pin(Path(sys.executable), prepared['python']['sha256'])
    pin(DATA / 'hayward_cmj_tangent_half_step_001/prepared.json', '85589144a5760543af29011d5df085455bd8a935c7141451ca7e190de5392606')
    summary = read(RUN / 'summary.json'); execution = read(RUN / 'execution.json'); outer = read(RUN / 'outer_reaping.json'); launch = read(RUN / 'prelaunch_review.json')
    require(summary['status'] == execution['status'] == 'completed_original_fixed_polygon_component_audit'
            and summary['error'] is None and execution['return_code'] == 0 and outer['status'] == 'completed_and_reaped'
            and outer['tool_exit_code'] == 0 and outer['wrapper_pid'] == execution['pid'] and outer['wrapper_process_absent'], 'Closed and reaped native calculation')
    for key, name in (('prepared_sha256', 'prepared.json'), ('summary_sha256', 'summary.json'), ('execution_sha256', 'execution.json'), ('prelaunch_review_sha256', 'prelaunch_review.json')): pin(RUN / name, outer[key])
    pin(RUN / 'outer_reaping.json', sha(RUN / 'outer_reaping.json'))
    require(launch['status'] == 'passed' and launch['prepared_sha256'] == summary['prepared_sha256'] == execution['prepared_sha256'] == EXPECTED
            and execution['prelaunch_review_sha256'] == sha(RUN / 'prelaunch_review.json') and execution['summary_sha256'] == sha(RUN / 'summary.json')
            and execution['environment'] == prepared['environment'], 'Preparation/source/terminal ledger bindings')
    require(summary['output_sha256'] == execution['output_sha256'] and set(summary['output_sha256']) == {p.name for p in RUN.glob('event_*') if p.is_file()}, 'Exact closed native result roster')
    for name, digest in summary['output_sha256'].items(): pin(RUN / name, digest)
    require(summary['settings'] == prepared['settings'] == SETTINGS and summary['edge_budget'] == prepared['component_edge_budget'] == 2058
            and all(record[k] == 2058 for record in (summary, execution) for k in ('attempted_component_edges', 'completed_component_edges')), 'Declared complete component budget')
    require(all(summary[k] == 0 for k in ('subprocess_calls', 'trace_calls', 'field_calls', 'metric_solves', 'rounded_trials', 'optimizer_iterations', 'source_model_partials'))
            and summary['original_convergence_flag'] == '0' and summary['candidate_convergence_status'] is None, 'No extra numerical calls or flag promotion')
    identities = read(RUN / 'native_contexts.json')
    require([v['event'] for v in identities] == [981, 987] and identities == read(CUT / 'native_contexts.json')
            == summary['native_contexts'] == execution['native_contexts'] == launch['native_contexts'] == outer['native_contexts'], 'Full native identity through all receipts')
    saved_review = read(SAVED / 'review.json'); cut_review = read(CUT / 'review.json')
    for package, review in ((SAVED, saved_review), (CUT, cut_review)):
        require(review['status'] == 'passed' and review['summary_sha256'] == sha(package / 'summary.json'), 'Reviewed original saved evidence')
    require(saved_review['execution_sha256'] == sha(SAVED / 'execution.json'), 'Reviewed saved raw-gradient execution')
    catalog_count = r.native_joins(identities); axes, unused_speeds = r.model()
    table_paths = [FACE / 'inputs/original_paths.csv', FACE / 'inputs/original_status.csv', SAVED / 'results/old/node_gradients.csv', SAVED / 'results/old/norms.csv']
    tables = [rows(p) for p in table_paths]
    require([len(v) for v in tables] == [2060, 2, 2060, 2] and all(row['event'] in ('981', '987') and row['station'] == '160' for table in tables for row in table), 'Exact original four-table inventory')
    require([v['event'] for v in summary['cases']] == [981, 987], 'Ordered terminal case roster')
    cases = [check_case(identity, brief, axes, *tables) for identity, brief in zip(identities, summary['cases'])]
    require(sum(v['edges'] for v in cases) == 2058, 'All original edges accounted')
    for path, digest in list(r.PINNED.items()): pin(Path(path), digest)
    review = dict(status='passed', reviewer='earthscope_discovery', checker_sha256=sha(Path(__file__)), source_review_sha256=sha(HERE / 'source_review.json'),
        native_prepared_sha256=EXPECTED, native_summary_sha256=sha(RUN / 'summary.json'), native_execution_sha256=sha(RUN / 'execution.json'),
        outer_reaping_sha256=sha(RUN / 'outer_reaping.json'), native_contexts=identities, cases=cases, checks=r.CHECKS, original_catalog_rows=catalog_count,
        input_sha256={str(Path(p).relative_to(ROOT)) if str(p).startswith(str(ROOT) + '/') else p: h for p, h in r.PINNED.items()},
        evaluator_imports=0, numerical_integrations=0, trace_calls=0, field_calls=0, pure_saved_reader_imports=1,
        limitations=['Saved edge intervals rely on the frozen reviewed primitive; no component integration or raw C++ evaluation is repeated.',
                    'Errors compare raw free-knot values only where an ordinary derivative exists. An aligned internal normal is unavailable, never silently zero.',
                    'Exact physical-box projections remain distinct from the separately retained legacy activity-band projection.',
                    'No first-arrival, source/model derivative accuracy, optimizer correction, field acceptance or original-status promotion is inferred.'])
    with (HERE / 'review.json').open('x') as stream: json.dump(encoded(review), stream, indent=2, sort_keys=True, allow_nan=False); stream.write('\n')
    print(json.dumps(dict(status='passed', checks=r.CHECKS, pins=len(r.PINNED), review_sha256=sha(HERE / 'review.json'))))


if __name__ == '__main__':
    main()
