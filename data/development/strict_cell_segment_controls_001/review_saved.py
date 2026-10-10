#!/usr/bin/env python3
"""Exact saved handoffs and error arithmetic; no evaluator or oracle import."""
from bisect import bisect_right
from fractions import Fraction as Q
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PRIOR = HERE.parent / 'internal_face_contact_controls_001/results/summary.json'
EXPECTED = 'a5c23ccdbcde56ee800c9c4faba204baa0dc15f55732d1958780ef50f24d63a6'
NODES = tuple(map(Q, (0.1834346424956498, 0.5255324099163290, 0.7966664774136267, 0.9602898564975363)))
WEIGHTS = tuple(map(Q, (0.3626837833783620, 0.3137066458778873, 0.2223810344533745, 0.1012285362903763)))
CHECKS = 0
PINS = {}


def require(ok, message):
    global CHECKS
    CHECKS += 1
    if not ok: raise ValueError(message)


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path): return json.loads(path.read_text())
def bounds(value):
    lo, hi = map(Q, value); require(lo <= hi, 'Ordered interval'); return lo, hi
def encode(v):
    if isinstance(v, Q): return str(v)
    if isinstance(v, dict): return {k: encode(x) for k, x in v.items()}
    if isinstance(v, (tuple, list)): return [encode(x) for x in v]
    return v
def pin(path, digest):
    require(sha(path) == digest and (str(path) not in PINS or PINS[str(path)] == digest), 'Exact consistent pin: ' + str(path)); PINS[str(path)] = digest
def handoff(record, value):
    x = float(value)
    require(math.isfinite(x) and Q(record['exact']) == value and record['binary64_hex'] == x.hex()
            and Q(record['represented_exact']) == Q(x), 'Exact rational to binary64 handoff')
    return record['binary64_hex']
def values(record, key):
    result = []; require(len(record[key]) == len(record[key + '_hex']), 'Decimal/hex dimensions')
    for v, h in zip(record[key], record[key + '_hex']):
        if v is None or h is None:
            require(v is h is None, 'Unavailable decimal/hex'); result.append(None)
        else:
            x = float.fromhex(h); require(math.isfinite(x) and float(v).hex() == x.hex(), 'Exact finite decimal/hex'); result.append(Q(x))
    return result
def check_errors(actual, reference, saved):
    require(len(actual) == len(reference) == len(saved['components']) == 6, 'Six endpoint components')
    total = [Q(0), Q(0)]; widths = []
    for i, (value, interval, item) in enumerate(zip(actual, reference, saved['components'])):
        require(item['component'] == i, 'Ordered error component')
        if interval is None:
            require(item['ordinary_unavailable'] and item['observed_branch_value'] == (None if value is None else str(value)), 'Aligned ordinary normal unavailable'); continue
        lo, hi = bounds(interval); error = value - hi, value - lo; widths.append(hi - lo)
        require(bounds(item['error']) == error, 'Saved raw-minus-reference error')
        total[0] += max(error[0], -error[1], Q(0)) ** 2; total[1] += max(abs(v) for v in error) ** 2
    require(bounds(saved['squared_norm']) == tuple(total) and list(map(Q, saved['reference_component_widths'])) == widths
            and saved['squared_norm_units'] == 's^2/km^2', 'Squared error sum and reference widths')
    return tuple(total), max(widths)


def main():
    require(not (HERE / 'review.json').exists() and not (HERE / 'review.json').is_symlink(), 'Fresh review only')
    pin(Path(__file__), sha(Path(__file__))); pin(HERE / 'results/summary.json', EXPECTED)
    pre = read(HERE / 'prepared.json'); s = read(HERE / 'results/summary.json'); ex = read(HERE / 'execution.json'); outer = read(HERE / 'outer_reaping.json')
    for base, mapping in ((ROOT, pre['input_sha256']), (HERE, pre['output_sha256']), (Path('/'), pre['runtime_sha256']),
                          (ROOT, s['source_sha256']), (ROOT, s['input_sha256']), (HERE / 'results', s['output_sha256']), (HERE, ex['output_sha256'])):
        for name, digest in mapping.items(): pin(base / name, digest)
    pin(Path(pre['python']['executable']), pre['python']['sha256'])
    for key, name in (('prepared_sha256', 'prepared.json'), ('summary_sha256', 'results/summary.json'), ('execution_sha256', 'execution.json'), ('prelaunch_review_sha256', 'prelaunch_review.json')): pin(HERE / name, outer[key])
    pin(HERE / 'outer_reaping.json', sha(HERE / 'outer_reaping.json'))
    require(s['status'] == 'passed' and ex['status'] == 'completed' and ex['return_code'] == 0 and ex['outputs_stable'] and not ex['unsettled_groups']
            and outer['status'] == 'completed_and_reaped' and outer['tool_exit_code'] == 0 and outer['wrapper_pid'] == ex['controller_pid'] and outer['wrapper_process_absent'], 'Terminal reaped calculation')
    require(ex['prepared_sha256'] == s['prepared_sha256'] == sha(HERE / 'prepared.json') and ex['summary_sha256'] == EXPECTED
            and ex['prelaunch_review_sha256'] == sha(HERE / 'prelaunch_review.json') and ex['environment'] == pre['environment'], 'Source/environment/terminal joins')
    launch = read(HERE / 'prelaunch_review.json'); require(launch['status'] == 'passed' and launch['prepared_sha256'] == s['prepared_sha256'], 'Independent prelaunch approval')
    require(len(ex['commands']) == 2 and all(c['return_code'] == 0 and c['child_reaped'] for c in ex['commands']), 'Compiler and driver reaped')
    require(len(s['checks']) == 59 and all(v['passed'] for v in s['checks']) and not s['unresolved_children'], 'All 59 recorded controls passed')
    require(s['counts'] == s['budgets'] == dict(cases=9, helpers=9, old_segment_calls=9, strict_edge_calls=9, strict_pieces=17, strict_samples=136,
            affine_references=7, homogeneous_references=1, trilinear_references=1), 'Declared exact call inventory')
    require(s['reference_settings'] == dict(affine_terms=16, affine_length_bits=192, trilinear=dict(terms=16, subdivisions=4, bits=192)), 'Fixed reference settings')
    require(s['invented_only'] and all(s[k] == 0 for k in ('native_calls', 'trace_calls', 'field_calls'))
            and s['generic_subtraction_supported'] is s['production_cut_patch'] is False and s['candidate_convergence_status'] is None, 'No unsupported generalization or status claim')
    require({str(p.relative_to(HERE / 'results')) for p in (HERE / 'results').rglob('*') if p.is_file() and p.name != 'summary.json'} == set(s['output_sha256']), 'Exact closed results inventory')
    for p in (HERE / 'logs').glob('*.log'):
        if 'stderr' in p.name or 'compile.stdout' in p.name: require(p.read_bytes() == b'', 'Empty compiler/stderr log')
    prior = read(PRIOR); require(prior['status'] == 'passed', 'Completed original contact controls')
    old_cases = {v['name']: v for f in prior['families'] if f['family'] == 'near_cut_inventory' for v in f['cases']}
    names = ['below_displacement_cutoff', 'above_displacement_cutoff', 'below_endpoint_cutoff', 'above_endpoint_cutoff', 'translated_nextafter', 'constant_velocity', 'translated_reversal', 'aligned_face', 'genuine_trilinear']
    require([v['case']['name'] for v in s['cases']] == names and len(s['commands']) == 9, 'Exact nine-case roster')
    reports = []; sample_count = piece_count = 0
    for index, (item, cmd) in enumerate(zip(s['cases'], s['commands'])):
        case = item['case']; name = case['name']; p = item['partition']; raw = item['observed']; axes = [list(map(Q, axis)) for axis in case['axes']]
        a, b = tuple(map(Q, case['a'])), tuple(map(Q, case['b'])); delta = tuple(y - x for x, y in zip(a, b))
        require(item['status'] == 'completed' and cmd['index'] == index and cmd['return_code'] == 0 and cmd['child_reaped'], 'Completed/reaped case')
        stem = HERE / 'results/calls' / ('%02d_%s' % (index, name))
        for suffix, key in (('.input', 'input_sha256'), ('.stdout.json', 'stdout_sha256'), ('.stderr.log', 'stderr_sha256')): pin(stem.with_suffix(suffix), cmd[key])
        require(stem.with_suffix('.stderr.log').read_bytes() == b'' and read(stem.with_suffix('.stdout.json')) == raw, 'Embedded observer and closed log match')
        require(tuple(values(raw, 'delta')) == delta == tuple(Q(float(y) - float(x)) for x, y in zip(a, b))
                and tuple(map(Q, p['a'])) == a and tuple(map(Q, p['b'])) == b and tuple(map(Q, p['delta_exact'])) == tuple(map(Q, p['delta_binary64_exact'])) == delta, 'One exact endpoint line')
        cuts = {Q(0): [], Q(1): []}; aligned = []
        for k, axis in enumerate(axes):
            if delta[k]:
                for j, plane in enumerate(axis[1:-1], 1):
                    if min(a[k], b[k]) < plane < max(a[k], b[k]): cuts.setdefault((plane - a[k]) / delta[k], []).append(dict(axis=k, plane_index=j, plane=plane))
            elif a[k] in axis[1:-1]: aligned.append(k)
        order = sorted(cuts)
        require(p['cuts'] == encode([dict(u=u, events=cuts[u]) for u in order]) and p['aligned_axes'] == aligned and len(p['pieces']) == len(order) - 1, 'Exact partition and aligned availability')
        tokens = ['3', '2', '2', str(len(p['pieces']))] + [float(x).hex() for axis in axes for x in axis]
        for k in range(2):
            for j in range(2):
                for i in range(3):
                    x, y, z = axes[0][i], axes[1][j], axes[2][k]
                    v = (2 + x) * (3 + y) * (4 + z) if case['kind'] == 'trilinear' else Q(6) if case['kind'] == 'constant' else 6 - abs(x - Q(case['center']))
                    require(Q(item['nodal_velocities'][str((i, j, k))]) == v > 0 and Q(float(v)) == v, 'Original manufactured nodal values/order'); tokens.append(float(v).hex())
        tokens += [float(x).hex() for point in (a, b) for x in point] + [str(int(k in aligned)) for k in range(3)]
        mismatches = []; coincident_points = set()
        for piece_index, (piece, left, right) in enumerate(zip(p['pieces'], order, order[1:])):
            width = right - left; middle = [a[k] + (left + right) * delta[k] / 2 for k in range(3)]
            cell = [min(len(axis) - 2, max(0, bisect_right(axis, middle[k]) - 1)) for k, axis in enumerate(axes)]
            require(Q(piece['left']) == left and Q(piece['right']) == right and piece['cell'] == cell and len(piece['samples']) == 8, 'Exact open-piece cell')
            tokens += list(map(str, cell)) + [handoff(piece['width'], width)]
            for slot, sample in enumerate(piece['samples']):
                j, sign = slot // 2, -1 if slot % 2 == 0 else 1; u = left + width * (1 + sign * NODES[j]) / 2
                point = tuple(a[k] + u * delta[k] for k in range(3))
                require(sample['node'] == j and sample['sign'] == sign and Q(sample['u_exact']) == u and tuple(map(Q, sample['point_exact'])) == point
                        and sample['point_binary64_hex'] == [float(x).hex() for x in point], 'Exact quadrature parameter and prepared global point')
                tokens += [handoff(sample['endpoint_shapes'][0], 1 - u), handoff(sample['endpoint_shapes'][1], u), handoff(sample['weight'], width * WEIGHTS[j] / 2)]
                for k, axis in enumerate(axes):
                    f = (point[k] - axis[cell[k]]) / (axis[cell[k] + 1] - axis[cell[k]])
                    require(0 <= f <= 1, 'Closed explicit-cell containment')
                    tokens += [handoff(sample['basis'][k][0], 1 - f), handoff(sample['basis'][k][1], f)]
                rounded = tuple(float.fromhex(v) for v in sample['point_binary64_hex']); coincident_points.add(rounded)
                rounded_cell = [min(len(axis) - 2, max(0, bisect_right(axis, Q(rounded[k])) - 1)) for k, axis in enumerate(axes)]
                if rounded_cell != cell: mismatches.append(dict(piece=piece_index, sample=slot, exact_cell=cell, rounded_global_cell=rounded_cell, axes=[k for k in range(3) if cell[k] != rounded_cell[k]]))
            piece_count += 1; sample_count += 8
        require(stem.with_suffix('.input').read_text() == ' '.join(tokens) + '\n', 'Whole numeric handoff file')
        require(raw['strict_pieces'] == len(p['pieces']) and raw['strict_samples'] == 8 * len(p['pieces']) and raw['old_segment_calls'] == raw['strict_edge_calls'] == 1
                and raw['invented_only'] and raw['trace_calls'] == raw['field_calls'] == 0, 'Actual helper counts/scope')
        old_cuts = [Q(0), Q(1)]
        for k, axis in enumerate(axes):
            d = float(b[k]) - float(a[k])
            if abs(d) > 1e-12:
                for plane in axis:
                    u = (float(plane) - float(a[k])) / d
                    if u > 1e-10 and u < 1 - 1e-10: old_cuts.append(Q(u))
        require(values(raw, 'reconstructed_old_cuts') == sorted(old_cuts) and (len(old_cuts) < len(order)) == case['expected_old_omission'], 'Frozen old cut classification')
        if name in old_cases:
            old = old_cases[name]['assessment']; old_raw = old['observed']['record']
            require([list(map(Q, v)) for v in old['path']] == [list(a), list(b)] and values(raw, 'old_action') == values(old_raw, 'action')
                    and values(raw, 'old_endpoint_gradient') == values(old_raw, 'endpoint_gradient') and values(raw, 'reconstructed_old_cuts') == values(old_raw, 'reconstructed_core_cuts')
                    and all(item['prior_old_output_parity'].values()), 'Four unchanged old outputs')
        reference = item['reference']; ref = [v for side in reference['components'] for v in side]
        strict = values(raw, 'strict_continuous_endpoint_gradient'); old = values(raw, 'old_endpoint_gradient')
        require(len(ref) == len(strict) == len(old) == 6 and all((v is None) == (k % 3 in aligned) for k, v in enumerate(strict))
                and all((v is None) == (w is None) for v, w in zip(strict, ref)), 'Aligned ordinary normal not compared')
        old_error, width = check_errors(old, ref, item['old_gradient_error']); strict_error, width2 = check_errors(strict, ref, item['strict_gradient_error'])
        require(width == width2 and item['strict_gradient_error_resolved_smaller_than_old'] == (strict_error[1] < old_error[0]), 'Resolved improvement is only saved interval comparison')
        lo, hi = bounds(reference['length']); length_squared = sum(x * x for x in delta)
        require(0 < lo and lo * lo <= length_squared <= hi * hi and bounds(item['binary64_length_error']) == (values(raw, 'length')[0] - hi, values(raw, 'length')[0] - lo), 'Saved length enclosure and error')
        action = bounds(reference['action'])
        for label in ('old', 'strict'):
            value = values(raw, label + '_action')[0]; require(bounds(item['action_errors'][label]) == (value - action[1], value - action[0]), 'Action error arithmetic')
        require(Q(item['reference_action_width']) == action[1] - action[0] and len(values(raw, 'strict_sample_velocity_and_gradient')) == 4 * raw['strict_samples'], 'Reference width/sample inventory')
        reports.append(dict(name=name, old_error_squared_bounds=old_error, strict_error_squared_bounds=strict_error,
            approximate_old_error_norm_s_per_km=math.sqrt(float(old_error[1])), approximate_strict_error_norm_s_per_km=math.sqrt(float(strict_error[1])),
            maximum_reference_component_width=width, reference_action_width=action[1] - action[0], action_errors=item['action_errors'],
            prepared_global_cell_mismatches=mismatches, mismatch_sample_count=len(mismatches), rounded_unique_global_points=len(coincident_points),
            prepared_samples=raw['strict_samples'], ordinary_unavailable_components=sum(v is None for v in ref)))
    require((piece_count, sample_count) == (17, 136), 'Complete saved quadrature roster')
    for path, digest in list(PINS.items()): pin(Path(path), digest)
    result = dict(status='passed', checker_sha256=sha(Path(__file__)), prepared_sha256=sha(HERE / 'prepared.json'), summary_sha256=EXPECTED,
        execution_sha256=sha(HERE / 'execution.json'), outer_reaping_sha256=sha(HERE / 'outer_reaping.json'), checks=CHECKS, unique_pins=len(PINS), cases=reports,
        input_sha256={str(Path(p).relative_to(ROOT)) if str(p).startswith(str(ROOT) + '/') else p: h for p, h in PINS.items()},
        evaluator_calls=0, oracle_calls=0, compiler_calls=0, numerical_integrations=0,
        limitations=['Only saved handoffs, reference bounds and error arithmetic were inspected; no numerical primitive or oracle was imported or rerun.',
                    'Rounded global-cell counts concern prepared strict quadrature points, not sample locations used by the old runtime evaluator.',
                    'The translated old case also omits a cut. This combined intervention cannot isolate the cause of its improvement.',
                    'Returned vectors approximate continuous first variations, not exact derivatives of the finite quadrature action. No generic subtraction, production or native accuracy claim.'])
    with (HERE / 'review.json').open('x') as stream: json.dump(encode(result), stream, indent=2, sort_keys=True, allow_nan=False); stream.write('\n')
    print(json.dumps(dict(status='passed', checks=CHECKS, pins=len(PINS), review_sha256=sha(HERE / 'review.json'), mismatch_counts={v['name']: v['mismatch_sample_count'] for v in reports})))


if __name__ == '__main__':
    main()
