#!/usr/bin/env python3
"""Saved geometry and binary64 cut decisions only; no kernel evaluation."""
from fractions import Fraction as Q
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
FACE = ROOT / 'data/development/hayward_cmj_face_action_001'
BENCH = ROOT / 'data/development/hayward_cmj_fixed_polygon_kernel_001'
CORE = ROOT / 'data/development/hayward_trial_cmj_old_D_replay_001/source/old/src/core.hpp'
LENGTH_CUTOFF = 1e-12
DIRECTION_CUTOFF = 1e-12
LOWER_CUT = 1e-10
UPPER_CUT = 1 - 1e-10


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def table(path):
    with path.open(newline='') as stream:
        reader = csv.DictReader(stream)
        require(len(reader.fieldnames) == len(set(reader.fieldnames)), 'Unique CSV headers')
        result = list(reader)
    require(all(None not in row and None not in row.values() for row in result), 'Complete CSV rows')
    return result


def encoded(value):
    if isinstance(value, Q):
        return str(value)
    if isinstance(value, dict):
        return {str(k): encoded(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [encoded(v) for v in value]
    return value


def save(path, value):
    payload = (json.dumps(encoded(value), indent=2, sort_keys=True, allow_nan=False) + '\n').encode()
    with path.open('xb') as stream:
        if path.suffix == '.gz':
            with gzip.GzipFile(fileobj=stream, mode='wb', mtime=0) as packed:
                packed.write(payload)
        else:
            stream.write(payload)


def edge_inventory(edge, a, b, axes):
    aq, bq = tuple(map(Q, a)), tuple(map(Q, b))
    exact_d = tuple(y - x for x, y in zip(aq, bq))
    d = tuple(y - x for x, y in zip(a, b))
    squares = tuple(x * x for x in d)
    squared = (squares[0] + squares[1]) + squares[2]
    length = math.sqrt(squared)
    require(all(math.isfinite(x) for x in d) and math.isfinite(length), 'Finite scalar cut arithmetic')
    short = length < LENGTH_CUTOFF
    exact_squared = sum(x * x for x in exact_d)
    require(exact_squared > 0, 'No zero-length original edge')
    planes = []
    added = [0.0, 1.0]
    aligned = []
    for axis, grid_axis in enumerate(axes):
        enabled = abs(d[axis]) > DIRECTION_CUTOFF
        for index, plane in enumerate(grid_axis):
            plane_q = Q(plane)
            if exact_d[axis] == 0:
                if aq[axis] == plane_q:
                    aligned.append(dict(axis=axis, plane_index=index, plane_exact=plane_q))
                exact_t = None
            else:
                exact_t = (plane_q - aq[axis]) / exact_d[axis]
            crossed = exact_t is not None and 0 < exact_t < 1
            numerator = plane - a[axis] if enabled else None
            binary_t = numerator / d[axis] if enabled else None
            candidate = enabled and binary_t > LOWER_CUT and binary_t < UPPER_CUT
            inserted = not short and candidate
            if inserted:
                added.append(binary_t)
            if not (crossed or inserted):
                continue
            reasons = []
            if crossed and not inserted:
                if short:
                    reasons.append('whole_segment_length_below_cutoff')
                if not enabled:
                    reasons.append('axis_displacement_not_above_cutoff')
                elif binary_t <= LOWER_CUT:
                    reasons.append('parameter_not_above_lower_cutoff')
                elif binary_t >= UPPER_CUT:
                    reasons.append('parameter_not_below_upper_cutoff')
            planes.append(dict(axis=axis, plane_index=index, plane_hex=plane.hex(), plane_exact=plane_q,
                               exact_parameter=exact_t, exact_open_segment_crossing=crossed,
                               binary_numerator_hex=None if numerator is None else numerator.hex(),
                               binary_parameter_hex=None if binary_t is None else binary_t.hex(),
                               axis_enabled=enabled, core_inserted=inserted, omission_reasons=reasons,
                               spurious_extra_cut=inserted and not crossed,
                               parameter_rounding_error=None if binary_t is None or exact_t is None else Q(binary_t) - exact_t))
    added.sort()
    return dict(edge=edge, endpoint_nodes=[edge, edge + 1], a_hex=[x.hex() for x in a], b_hex=[x.hex() for x in b],
                a_exact=aq, b_exact=bq, exact_displacement=exact_d, binary_displacement_hex=[x.hex() for x in d],
                exact_length_squared=exact_squared, binary_dot_hex=squared.hex(), binary_length_hex=length.hex(),
                core_skips_whole_segment=short, exact_length_below_binary64_cutoff=exact_squared < Q(LENGTH_CUTOFF) ** 2,
                axis_enabled=[abs(x) > DIRECTION_CUTOFF for x in d], aligned_planes=aligned,
                crossed_or_inserted_planes=planes, core_sorted_cut_hex=[] if short else [x.hex() for x in added],
                duplicate_binary_cut_count=0 if short else len(added) - len(set(added)))


def main():
    prepared = read(HERE / 'prepared.json')
    approval = read(HERE / 'source_review.json')
    require(approval['status'] == 'passed' and approval['source_sha256'] == sha(Path(__file__))
            and approval['prepared_sha256'] == sha(HERE / 'prepared.json'), 'Root source review before saved inventory')
    for base, key in ((ROOT, 'input_sha256'), (HERE, 'output_sha256')):
        for name, digest in prepared[key].items():
            require(sha(base / name) == digest, 'Unchanged pinned source/input')
    require(not (HERE / 'summary.json').exists(), 'Preserve existing inventory')
    identities = read(HERE / 'native_contexts.json')
    require(identities == read(BENCH / 'native_contexts.json') and [r['event'] for r in identities] == [981, 987], 'Exact identified pair roster')
    require(read(BENCH / 'review.json')['status'] == 'passed'
            and read(ROOT / 'data/development/hayward_cmj_face_action_review_001/review.json')['status'] == 'passed', 'Reviewed original geometry and identity mapping')
    model = read(FACE / 'model_provenance.json'); raw_grid = table(FACE / 'inputs/trial_grid.csv')
    require(model['recorded_grid_sha256'] == sha(FACE / 'inputs/trial_grid.csv') and len(raw_grid) == len(model['nodes']) == 462, 'Original complete model')
    axes = tuple(tuple(float(Q(x)) for x in axis) for axis in model['axes_exact_rational'])
    require([[Q(x) for x in axis] for axis in axes] == [[Q(x) for x in axis] for axis in model['axes_exact_rational']], 'Exact binary64 grid axes')
    require(all(all(x < y for x, y in zip(axis, axis[1:])) for axis in axes), 'Strictly increasing grid axes')
    for index, (row, saved) in enumerate(zip(raw_grid, model['nodes'])):
        require(saved['csv_row'] == index, 'Nodal grid ordering')
        for key in ('x', 'y', 'z', 'v'):
            value = float(row[key]); original = saved['values'][key]
            require(math.isfinite(value) and original['raw_text'] == row[key] and original['binary64_hex'] == value.hex()
                    and Q(original['exact_rational']) == Q(value), 'Original nodal scalar mapping')
    original_contexts = read(FACE / 'inputs/native_context.json')
    require(model['native_contexts'] == original_contexts == [r['native_context'] for r in identities], 'Unchanged model/native context')
    events = {int(v['id']): v for v in table(FACE / 'inputs/trial_events.csv')}
    stations = {int(v['id']): v for v in table(FACE / 'inputs/stations.csv')}
    paths = table(FACE / 'inputs/original_paths.csv'); statuses = table(FACE / 'inputs/original_status.csv')
    require(len(statuses) == 2 and len(paths) == 2060, 'Only the two original old-kernel polygons')
    reports = []
    for identity in identities:
        event = identity['event']; context = identity['native_context']; n = 1029 if event == 981 else 1031
        status = next(v for v in statuses if int(v['event']) == event)
        require(status == context['original_status'] and status['ray_converged'] == status['ray_derivatives_evaluated'] == '0'
                and all(status['source_d' + k] == '' for k in 'xyz'), 'Preserved original false flags and blank partials')
        selected = [r for r in paths if int(r['event']) == event]
        require([int(r['node']) for r in selected] == list(range(n)) and all(r['station'] == '160' for r in selected), 'Original ordered nodes')
        metadata = {k: v for k, v in status.items() if k.startswith('source_') or k.startswith('receiver_')}
        for row in selected:
            require(all(row[k] == value for k, value in metadata.items() if k in row), 'Every raw node retains full native metadata')
        polygon = [tuple(float(row[k]) for k in 'xyz') for row in selected]
        require(all(math.isfinite(x) and axes[k][0] <= x <= axes[k][-1] for point in polygon for k, x in enumerate(point)), 'Original finite physical geometry')
        require(polygon[0] == tuple(float(context['source_native'][k]) for k in 'xyz')
                and polygon[-1] == tuple(float(context['receiver_native'][k]) for k in 'xyz'), 'Original exact native endpoints')
        require(len(identity['catalog_uses']) == 9, 'Nine original catalog uses')
        for use in identity['catalog_uses']:
            side, row = use['side'], use['original_row']; receiver = 'station' if side == 'i' else 'station_j'
            require(int(row[side]) == event and int(row[receiver]) == 160
                    and row['event_' + side + '_resource_id'] == context['source_native']['event_resource_id']
                    and row['origin_' + side + '_resource_id'] == context['source_native']['origin_resource_id']
                    and row['channel_seed_id'] == context['receiver_native']['channel_seed_id'], 'Original catalog event/channel association')
            require(set(use['epoch_joins']) == ({'i'} if row['type'] == '0' else {'i', 'j'}), 'Complete both-side catalog epoch roster')
            for which, joined in use['epoch_joins'].items():
                event_id = int(row[which]); station_id = int(row['station' if which == 'i' else 'station_j'])
                station = stations[station_id]
                require(joined['event_index'] == event_id and joined['station_index'] == station_id and joined['receiver_native'] == station
                        and row['event_' + which + '_resource_id'] == events[event_id]['event_resource_id']
                        and row['origin_' + which + '_resource_id'] == events[event_id]['origin_resource_id'], 'Both native event/origin/receiver joins')
                require(all(row[k] == station[k] for k in ('channel_seed_id', 'channel_fdsn_source_id', 'location_code')), 'Literal channel and empty location')
                for end in ('start', 'end'):
                    key = 'metadata_epoch_' + ('' if which == 'i' else 'j_') + end
                    require(row[key] == station['metadata_epoch_' + end], 'Both original receiver epochs')
        destination = HERE / ('event_%d.json.gz' % event)
        save(Path(str(destination) + '.identifiers.json'), dict(identity, expected_file=str(destination.relative_to(ROOT)), prepared_sha256=sha(HERE / 'prepared.json'),
             role='Original old-kernel polygon cut inventory only; no geometry, action, gradient or status changes'))
        records = [edge_inventory(i, a, b, axes) for i, (a, b) in enumerate(zip(polygon, polygon[1:]))]
        omitted = [dict(edge=r['edge'], **p) for r in records for p in r['crossed_or_inserted_planes'] if p['exact_open_segment_crossing'] and not p['core_inserted']]
        extra = [dict(edge=r['edge'], **p) for r in records for p in r['crossed_or_inserted_planes'] if p['spurious_extra_cut']]
        result = dict(identity, original_convergence_flag='0', candidate_convergence_status=None, edge_records=records, omitted_exact_crossings=omitted,
                      spurious_extra_cuts=extra, raw_path_sha256=sha(FACE / 'inputs/original_paths.csv'), model_sha256=sha(FACE / 'model_provenance.json'))
        save(destination, result)
        reports.append(dict(identity, edges=n - 1, result_file=destination.name, result_sha256=sha(destination),
             exact_crossings=sum(p['exact_open_segment_crossing'] for r in records for p in r['crossed_or_inserted_planes']),
             core_plane_insertions=sum(p['core_inserted'] for r in records for p in r['crossed_or_inserted_planes']), omitted_exact_crossings=len(omitted),
             spurious_extra_cuts=len(extra), skipped_segments=sum(r['core_skips_whole_segment'] for r in records),
             duplicate_binary_cuts=sum(r['duplicate_binary_cut_count'] for r in records)))
    for name, digest in prepared['input_sha256'].items():
        require(sha(ROOT / name) == digest, 'Original saved inputs unchanged after inventory')
    summary = dict(status='completed_saved_original_cut_inventory', prepared_sha256=sha(HERE / 'prepared.json'), source_sha256=sha(Path(__file__)),
                   native_contexts=identities, cases=reports, thresholds_hex=dict(length=LENGTH_CUTOFF.hex(), direction=DIRECTION_CUTOFF.hex(), lower=LOWER_CUT.hex(), upper=UPPER_CUT.hex()),
                   output_sha256={p.name: sha(p) for p in sorted(HERE.glob('event_*'))}, evaluator_calls=0, integration_calls=0, field_calls=0, path_mutations=0,
                   limitations=['Binary64 scalar replay of frozen source predicates, not a compiled kernel call or quadrature/gradient accuracy certificate.',
                                'All exact crossed planes and binary inserted planes are inventoried; retained parameters may still be rounded.',
                                'Zero omitted cuts would not establish general off-face sampling or derivative accuracy.'])
    save(HERE / 'summary.json', summary)
    print(json.dumps(dict(status=summary['status'], summary_sha256=sha(HERE / 'summary.json'), cases=[{k: v for k, v in x.items() if k not in ('native_context', 'catalog_uses')} for x in reports])))


if __name__ == '__main__':
    main()
