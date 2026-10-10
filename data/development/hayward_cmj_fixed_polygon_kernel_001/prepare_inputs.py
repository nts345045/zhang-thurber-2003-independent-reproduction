#!/usr/bin/env python3
"""Serialize eight saved polygons and reviewed oracles; no evaluator imports/calls."""
import csv
from fractions import Fraction as Q
import gzip
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DATA = ROOT / 'data/development'
FACE = DATA / 'hayward_cmj_face_action_001'
FIRST = DATA / 'hayward_cmj_tangent_step_001'
SECOND = DATA / 'hayward_cmj_tangent_step_002'
HALF = DATA / 'hayward_cmj_tangent_half_step_001'
POST = DATA / 'hayward_cmj_post_step_tangent_001'
PINS = {}


def require(ok, message):
    if not ok: raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''): h.update(block)
    return h.hexdigest()


def record(path):
    name = str(path.relative_to(ROOT)); digest = sha(path)
    require(name not in PINS or PINS[name] == digest, 'Changed input: ' + name)
    PINS[name] = digest
    return name


def read(path):
    record(path)
    with (gzip.open(str(path), 'rt') if path.suffix == '.gz' else path.open()) as stream: return json.load(stream)


def rows(path):
    record(path)
    with path.open(newline='') as stream: return list(csv.DictReader(stream))


def encoded(value):
    if isinstance(value, Q): return str(value)
    if isinstance(value, dict): return {k: encoded(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)): return [encoded(v) for v in value]
    return value


def save(path, value):
    content = (json.dumps(encoded(value), indent=2, sort_keys=True, allow_nan=False) + '\n').encode('utf8')
    with path.open('xb') as stream:
        if path.suffix == '.gz':
            with gzip.GzipFile(fileobj=stream, mode='wb', mtime=0) as zipped: zipped.write(content)
        else: stream.write(content)


def bounds(values):
    a, b = map(Q, values); require(a <= b, 'Reversed saved bounds'); return a, b


def add(a, b): return a[0] + b[0], a[1] + b[1]


def total(edges):
    result = (Q(0), Q(0))
    for edge in edges: result = add(result, bounds(edge['bounds']))
    return result


def origin(path, pointer):
    return dict(file=record(path), sha256=sha(path), json_pointer=pointer)


def audited(folder, review_name, face=False):
    review_file = DATA / review_name / 'review.json'; review = read(review_file)
    require(review['status'] == 'passed', 'Passed independent review required')
    prefix = '' if face else 'native_'
    for key, name in [(prefix + 'prepared_sha256', 'prepared.json'), (prefix + 'summary_sha256', 'summary.json'), (prefix + 'execution_sha256', 'execution.json')]:
        require(sha(folder / name) == review[key], 'Reviewed terminal pin'); read(folder / name)
    execution = read(folder / 'execution.json'); summary = read(folder / 'summary.json')
    require(execution['return_code'] == 0 and summary['error'] is None and summary['status'].startswith('completed_'), 'Successful saved calculation')
    if face: require(execution['child_reaped'], 'Reaped face calculation')
    else:
        outer = read(folder / 'outer_reaping.json')
        require(sha(folder / 'outer_reaping.json') == review['outer_reaping_sha256'] and outer['status'] == 'completed_and_reaped'
                and outer['tool_exit_code'] == 0 and outer['wrapper_pid'] == execution['pid'] and outer['wrapper_process_absent'], 'Reaped saved calculation')
    for name, digest in summary['output_sha256'].items():
        p = folder / name
        require(sha(p) == digest, 'Reviewed output bytes'); record(p)
    return origin(review_file, ''), read(folder / 'prepared.json')


def coordinate_rows(path, hexes=None):
    flat = [Q(x) for point in path for x in point]
    if hexes is None: hexes = [float(v).hex() for v in flat]
    require(len(flat) == len(hexes), 'Full coordinate spelling roster')
    floats = [float.fromhex(h) for h in hexes]
    require(all(Q(x) == q for x, q in zip(floats, flat)), 'Exact binary64/rational join')
    tokens = [format(x, '.17g') for x in floats]
    require(all(float(t).hex() == x.hex() for t, x in zip(tokens, floats)), '17-digit round-trip including signed zero')
    lines = [' '.join(tokens[i:i+3]) for i in range(0, len(tokens), 3)]
    return lines, [[x.hex() for x in floats[i:i+3]] for i in range(0, len(floats), 3)]


def action_edges(full, path, source, previous=None):
    if previous is None:
        unique = full['unique_action_edge_records']; ids = full['candidate_edge_record_ids']; edges = []
        require(len(ids) == len(path) - 1, 'Face edge inventory')
        for e, index in enumerate(ids):
            r = unique[index]; require(r['cache_id'] == index and list(map(Q, r['a_exact'])) == path[e]
                                      and list(map(Q, r['b_exact'])) == path[e+1], 'Face edge geometry/cache join')
            edges.append(dict(edge=e, bounds=r['record']['action'], **origin(source, '/unique_action_edge_records/' + str(index) + '/record/action')))
        full_bounds = full['candidate_action']['exact_rational_bounds']
    else:
        action = full['result']['action']; edges = []; new = action['new_edge_records']
        require(len(action['edge_joins']) == len(path) - 1, 'Trial edge inventory')
        for e, join in enumerate(action['edge_joins']):
            require(join['edge'] == e, 'Trial edge order'); item = join['trial_record']
            if item['source'] == 'new_trial':
                index = item['record_id']; r = new[index]
                require(r['record_id'] == index and list(map(Q, r['a'])) == path[e] and list(map(Q, r['b'])) == path[e+1], 'New edge exact geometry')
                pointer = '/result/action/new_edge_records/' + str(index) + '/record/action'
                edge = dict(edge=e, bounds=r['record']['action'], **origin(source, pointer))
            else:
                require(item['source'] == 'saved_start', 'Known cached edge source'); index = item['edge']
                require(previous['path'][index:index+2] == path[e:e+2], 'Inherited edge exact geometry')
                edge = dict(previous['edges'][index], edge=e)
            require(bounds(edge['bounds']) == bounds(item['action']), 'Joined edge action bounds'); edges.append(edge)
        full_bounds = action['trial_action']
        require(bounds(action['starting_action']) == total(previous['edges']), 'Starting full-action join')
    require(total(edges) == bounds(full_bounds), 'Exact saved full/per-edge sum')
    return edges, full_bounds


def derivatives(full, post, source, review, path, stage):
    if stage not in ('face', 'first'):
        return dict(status='unavailable', reason='No saved derivative evaluation at this polygon.' if stage == 'second' else 'Post-half derivative oracle pending separate completed independent review.', component_bounds=None)
    raw = full['candidate_edge_tangent_records'] if stage == 'face' else post['tangent_edge_records']
    components = full['candidate_free_node_tangent_components'] if stage == 'face' else post['free_node_components']
    require(len(raw) == len(path)-1 and len(components) == len(path)-2, 'Saved tangent inventory')
    sums = [[(Q(0), Q(0)) for k in range(3)] for p in path]; blocked = set()
    for e, edge in enumerate(raw):
        require(edge['edge'] == e, 'Tangent edge order')
        for side in (0, 1):
            node = e + side
            if node in (0, len(path)-1): require(edge['components'][side] is None, 'Fixed endpoints have no derivative oracle'); continue
            for k, value in enumerate(edge['components'][side]):
                require((value is None) == (k in edge['blocked_axes']), 'Available tangent slots')
                if value is None: blocked.add((node, k))
                else: sums[node][k] = add(sums[node][k], bounds(value))
    for node, k in blocked: sums[node][k] = None
    require(encoded([dict(node=i, components=sums[i]) for i in range(1, len(path)-1)]) == components, 'Saved tangent component assembly')
    pointer = '/candidate_free_node_tangent_components' if stage == 'face' else '/free_node_components'
    return dict(status='reviewed_available_internal_components', component_bounds=components, unavailable_slots=sorted(blocked),
                fixed_endpoint_derivatives='unavailable', source=origin(source, pointer), review=review,
                interpretation='Raw available components, not projected norms; null normal slots have no ordinary-gradient oracle.')


def main():
    require(not (HERE / 'inputs').exists() and not (HERE / 'oracle.json.gz').exists() and not (HERE / 'input_preparation.json').exists(), 'Fresh input preparation only')
    record(Path(__file__).resolve())
    review_face, unused = audited(FACE, 'hayward_cmj_face_action_review_001', True)
    review_first, first_prep = audited(FIRST, 'hayward_cmj_tangent_step_review_001')
    review_second, unused = audited(SECOND, 'hayward_cmj_tangent_step_review_002')
    review_half, unused = audited(HALF, 'hayward_cmj_tangent_half_step_review_001')
    review_post, unused = audited(POST, 'hayward_cmj_post_step_tangent_review_001')
    identities = read(FIRST / 'native_contexts.json')
    require([r['event'] for r in identities] == [981, 987] and all(r['station'] == 160 and len(r['catalog_uses']) == 9 for r in identities), 'Full native roster')
    require(identities == read(SECOND / 'native_contexts.json') == read(HALF / 'native_contexts.json') == read(POST / 'native_contexts.json'), 'All stages have identical native context')
    events = rows(FACE / 'inputs/trial_events.csv'); stations = rows(FACE / 'inputs/stations.csv'); observations = rows(ROOT / 'data/hayward/observations.csv')
    for p in (FACE / 'inputs/trial_events.csv', FACE / 'inputs/stations.csv', ROOT / 'data/hayward/observations.csv'):
        require(sha(p) == first_prep['input_sha256'][str(p.relative_to(ROOT))], 'Pinned original native table')
    for identity in identities:
        c = identity['native_context']; require(c['source_native'] == events[identity['event']] and c['receiver_native'] == stations[160], 'Full native table fields')
        for use in identity['catalog_uses']:
            r = observations[use['zero_based_observation_row']]; require(r == use['original_row'], 'All original pick/association fields')
            require(int(r[use['side']]) == identity['event'] and int(r['station' if use['side']=='i' else 'station_j']) == identity['station'], 'Catalog event/receiver side')
            for side, joined in use['epoch_joins'].items():
                e = int(r[side]); s = int(r['station' if side == 'i' else 'station_j'])
                require(joined == dict(event_index=e, station_index=s, receiver_native=stations[s]), 'Both complete native epochs')
                require(r['event_' + side + '_resource_id'] == events[e]['event_resource_id'] and r['origin_' + side + '_resource_id'] == events[e]['origin_resource_id'], 'Provider event/origin identity')
    model = read(FACE / 'model_provenance.json'); grid_rows = rows(FACE / 'inputs/trial_grid.csv'); axes = [list(map(Q, a)) for a in model['axes_exact_rational']]
    require(model['recorded_grid_sha256'] == sha(FACE / 'inputs/trial_grid.csv') and len(grid_rows) == len(model['nodes']) == 462, 'Original model identity')
    velocities = {}
    for i, (row, saved) in enumerate(zip(grid_rows, model['nodes'])):
        require(saved['csv_row'] == i, 'Grid row order')
        for k in ('x', 'y', 'z', 'v'):
            v = saved['values'][k]; require(v['raw_text'] == row[k] and v['binary64_hex'] == float(row[k]).hex() and Q(v['exact_rational']) == Q(float(row[k])), 'Exact original grid value')
        key = tuple(axes[k].index(Q(float(row[c]))) for k, c in enumerate('xyz'))
        require(key not in velocities, 'Unique Cartesian grid node'); velocities[key] = Q(float(row['v']))
    require(len(velocities) == len(axes[0])*len(axes[1])*len(axes[2]) and min(velocities.values()) > 0, 'Complete positive grid')
    inputs = []; polygons = []; pairs = []
    grid_values = [' '.join(format(float(x), '.17g') for x in a) for a in axes]
    ordered = [velocities[x,y,z] for z in range(len(axes[2])) for y in range(len(axes[1])) for x in range(len(axes[0]))]
    require(all(Q(float(format(float(v), '.17g'))) == v for v in ordered), 'Grid decimal round-trip')
    grid_text = ' '.join(str(len(a)) for a in axes) + '\n' + '\n'.join(grid_values) + '\n' + ' '.join(format(float(v), '.17g') for v in ordered) + '\n'
    inputs.append(('grid.txt', grid_text, dict(native_contexts=identities, role='Shared original binary64 model; x-fastest Grid::id order.', model_source=origin(FACE/'model_provenance.json',''))))
    for identity in identities:
        event = identity['event']; face_file = FACE / ('event_' + str(event) + '.json.gz'); face = read(face_file)
        files = [FIRST / ('event_' + str(event)) / 'result.json.gz', SECOND / ('event_' + str(event)) / 'result.json.gz', HALF / ('event_' + str(event)) / 'result.json.gz']
        records = [face] + [read(p) for p in files]; post_file = POST / ('event_' + str(event) + '.json.gz'); post = read(post_file)
        require(face['native_context'] == identity['native_context'], 'Native face context')
        for r in records[1:] + [post]: require(all(r[k] == identity[k] for k in ('event','station','native_context','catalog_uses')), 'Every native stage/catalog join')
        paths = [[list(map(Q, p['candidate_exact_rational'])) for p in face['coordinate_provenance']]] + [[list(map(Q,p)) for p in r['result']['trial']] for r in records[1:]]
        require([list(map(Q,p['exact_rational'])) for p in post['coordinate_provenance']] == paths[1], 'First derivative oracle is on first geometry')
        require(all(len(path) == (1029 if event == 981 else 1031) and path[0] == paths[0][0] and path[-1] == paths[0][-1] for path in paths), 'Fixed native topology/endpoints')
        saved = []
        for stage, (name, full, path, source, review) in enumerate(zip(('face','first','second','half'), records, paths, [face_file]+files, [review_face,review_first,review_second,review_half])):
            require(all(a != b for a,b in zip(path,path[1:])) and all(axes[k][0] <= p[k] <= axes[k][-1] for p in path for k in range(3)), 'Positive in-box saved polygon')
            if stage:
                require(full['result']['status'] == ('diagnostic_trial_not_accepted' if stage == 2 else 'diagnostic_trial_accepted'), 'Preserved trial decision')
            spelling = None if not stage else full['result']['rounded_record']['trial_hex']
            lines, hexes = coordinate_rows(path, spelling); numeric = '{} 160 {} {}\n'.format(event, stage, len(path)) + '\n'.join(lines) + '\n'
            pointer = '/coordinate_provenance/*/candidate_exact_rational' if not stage else '/result/trial'
            edges, full_bounds = action_edges(full, path, source, None if not stage else saved[0] if stage == 1 else saved[1])
            name_file = '{}_{}.txt'.format(event,name); input_file = 'inputs/' + name_file
            item = dict(identity, case_id='{}_{}'.format(event,name), stage=name, stage_integer=stage, node_count=len(path), input_file=input_file,
                        input_sha256=hashlib.sha256(numeric.encode()).hexdigest(), coordinates_exact_rational=path, coordinate_hex=hexes, geometry_source=origin(source,pointer),
                        action=dict(full_bounds=full_bounds,edges=edges,review=review),
                        derivatives=derivatives(face,post,face_file if not stage else post_file,review_face if not stage else review_post,path,name))
            polygons.append(item); saved.append(dict(path=path,edges=edges))
            inputs.append((name_file,numeric,dict(identity,case_id=item['case_id'],stage_integer=stage,role='Saved fixed polygon; no new trial or stationarity claim.',geometry_source=item['geometry_source'],coordinate_hex=hexes)))
        direction = records[2]['result']['direction']; metric = records[2]['result']['metric']; n = len(paths[1])
        direction_hex = [float(0).hex()]*3 + metric['direction_hex'] + [float(0).hex()]*3
        require(len(metric['direction_hex']) == 3*(n-2) and direction == records[3]['result']['direction'], 'Same actual second-trial direction reused for half')
        for component in post['free_node_components']:
            for k,value in enumerate(component['components']):
                if value is None: require(Q(direction[component['node']][k]) == 0, 'Unavailable first-step normal has exactly zero direction')
        lines, hexes = coordinate_rows(direction,direction_hex); text = '{} 160 {}\n'.format(event,n) + '\n'.join(lines) + '\n'; name='{}_direction.txt'.format(event)
        require(all(Q(x)==0 for p in (direction[0],direction[-1]) for x in p), 'Fixed endpoint direction')
        inputs.append((name,text,dict(identity,role='Same binary64 metric direction from second trial; no solve.',direction_source=origin(files[1],'/result/metric/direction_hex'),coordinate_hex=hexes)))
        for stage, full, source, review in [('second',records[2],files[1],review_second),('half',records[3],files[2],review_half)]:
            r=full['result']; a=r['action']; alpha=Q(float.fromhex(r['alpha_hex'])); slope=bounds(r['nominal_slope']); coefficient=Q(float('1e-4'))
            require(alpha == (Q(1) if stage=='second' else Q(1,2)) and Q(a['nominal_armijo_rhs_lower']) == coefficient*alpha*slope[0], 'Exact binary64 Armijo coefficient and alpha')
            require(bounds(a['starting_action']) == total(saved[1]['edges']) and bool(a['conservative_nominal_armijo']) == (bounds(a['paired_difference'])[1] <= coefficient*alpha*slope[0]), 'Same first geometry and saved acceptance arithmetic')
            pairs.append(dict(identity,from_stage='first',to_stage=stage,direction_file='inputs/'+name,direction_sha256=hashlib.sha256(text.encode()).hexdigest(),
                              direction_source=origin(files[1],'/result/metric/direction_hex'),alpha_hex=r['alpha_hex'],alpha_exact=alpha,nominal_slope=r['nominal_slope'],
                              actual_displacement_slope=r['actual_displacement_slope'],paired_difference=a['paired_difference'],full_difference=a['full_difference'],
                              armijo_coefficient_exact=coefficient,armijo_coefficient_hex=float('1e-4').hex(),Armijo_rhs_lower=a['nominal_armijo_rhs_lower'],
                              conservative_nominal_armijo=a['conservative_nominal_armijo'],status=r['status'],source=origin(source,'/result'),review=review))
    require(len(polygons)==8 and len(pairs)==4 and len(inputs)==11 and sum(p['node_count']-1 for p in polygons)==8232,'Fixed benchmark inventory')
    for name,digest in PINS.items(): require(sha(ROOT/name)==digest,'Input changed during mapping')
    (HERE/'inputs').mkdir()
    for name,text,context in inputs:
        path=HERE/'inputs'/name; payload=text.encode('utf8'); digest=hashlib.sha256(payload).hexdigest()
        save(Path(str(path)+'.identifiers.json'),dict(context,expected_file=str(path.relative_to(ROOT)),file_sha256=digest,input_sha256=PINS,coordinate_basis='Exact saved binary64 values; 17-digit decimal transport; no new evaluation.'))
        with path.open('xb') as stream: stream.write(payload)
        require(sha(path)==digest,'Serialized numeric readback')
    save(HERE/'native_contexts.json',identities)
    save(HERE/'oracle.json.gz',dict(schema='fixed_polygon_saved_oracles_1',model=dict(grid_input='inputs/grid.txt',node_order='z outer, y middle, x inner: Grid::id',axes_exact_rational=axes,
         raw_grid=origin(FACE/'inputs/trial_grid.csv',''),provenance=origin(FACE/'model_provenance.json','')),native_contexts=identities,polygons=polygons,pairs=pairs,input_sha256=PINS,
         limitations=['Only saved action bounds and reviewed available internal derivative bounds; no evaluator was called.',
                      'Second-trial derivative oracle absent. Half derivative oracle intentionally pending a separate terminal reviewed calculation.',
                      'Unavailable normals are null, never an ordinary derivative zero. No convergence/source/first-arrival claim.']))
    for name,digest in PINS.items(): require(sha(ROOT/name)==digest,'Input changed after mapping')
    outputs={str(p.relative_to(HERE)):sha(p) for p in sorted((HERE/'inputs').iterdir())}
    outputs.update({n:sha(HERE/n) for n in ['oracle.json.gz','native_contexts.json']})
    save(HERE/'input_preparation.json',dict(status='prepared_saved_inputs_no_evaluation',source_sha256=sha(Path(__file__)),input_sha256=PINS,output_sha256=outputs,
        polygons=8,edges=8232,numeric_files=11,catalog_uses=18,action_oracles=8,derivative_oracles=4,derivative_oracle_unavailable_cases=['981_second','981_half','987_second','987_half'],
        evaluator_calls=0,compiler_calls=0,integrations=0,trace_calls=0,field_calls=0,note='Overall benchmark prepared.json/source/runtime and numerical execution are owned separately.'))
    print(json.dumps(dict(status='prepared_saved_inputs_no_evaluation',input_preparation_sha256=sha(HERE/'input_preparation.json'),input_pins=len(PINS),output_pins=len(outputs))))


if __name__=='__main__': main()
