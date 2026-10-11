#!/usr/bin/env python3
"""Summarize six saved final tables; no evaluator, optimizer or history scan."""
import argparse
import csv
from fractions import Fraction as Q
import hashlib
import json
import math
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
AXES = 'xyz'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def encode(value):
    if isinstance(value, Q):
        return str(value)
    if isinstance(value, dict):
        return {str(k): encode(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [encode(v) for v in value]
    return value


def save(path, value):
    with Path(path).open('x') as stream:
        json.dump(encode(value), stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write('\n')


def verify_package():
    manifest = read(HERE / 'manifest.json')
    for name, expected in manifest['sha256'].items():
        relative = Path(name)
        require(not relative.is_absolute() and '..' not in relative.parts, 'Relative manifest path')
        path = HERE / relative
        require(not path.is_symlink() and path.is_file() and sha(path) == expected,
                'Changed package file: ' + name)
    return sha(HERE / 'manifest.json')


def fresh_output(name):
    requested = Path(name).absolute()
    require(not requested.exists() and not requested.is_symlink(), 'Fresh output required')
    output = requested.parent.resolve() / requested.name
    require(ROOT / 'tmp' in output.parents and HERE not in output.parents,
            'Output must be under this repository tmp/, outside the package')
    require(output.parent.is_dir(), 'Create the project-local parent first (for example mkdir -p tmp)')
    return output


def exact(token):
    match = re.fullmatch(r'([+-]?)0x([0-9a-fA-F]+)(?:\.([0-9a-fA-F]*))?p([+-]?\d+)', token)
    require(match is not None, 'Finite hexadecimal scalar required')
    sign, whole, fraction, exponent = match.groups()
    fraction = fraction or ''
    return (-1 if sign == '-' else 1) * Q(int(whole + fraction, 16)) * Q(2) ** (int(exponent) - 4 * len(fraction))


def binary64(token):
    value = exact(token)
    parsed = float.fromhex(token)
    require(math.isfinite(parsed) and Q(parsed) == value, 'Exact binary64 token required')
    return value


def numeric(case):
    path = HERE / 'inputs' / case['numeric_input']
    require(sha(path) == case['numeric_input_sha256'], 'Exact generated numeric input')
    require(read(Path(str(path) + '.identifiers.json')) == case['input_identity'], 'Complete input identity')
    tokens = path.read_text().split()
    dims = tuple(map(int, tokens[:3])); position = 3; axes = []
    require(len(dims) == 3 and all(n >= 2 for n in dims), 'Grid dimensions')
    for n in dims:
        axis = tuple(binary64(t) for t in tokens[position:position+n]); position += n
        require(len(axis) == n and all(a < b for a, b in zip(axis, axis[1:])), 'Increasing axes')
        axes.append(axis)
    count = dims[0] * dims[1] * dims[2]
    values = [binary64(t) for t in tokens[position:position+count]]; position += count
    require(len(values) == count and all(v > 0 for v in values), 'Positive complete velocity grid')
    nodes = int(tokens[position]); position += 1
    require(nodes == case['nodes'] and nodes - 1 == case['edges'] and len(tokens) == position + 3*nodes,
            'Complete original generated topology')
    initial_rows = [dict(node=str(i), **{k+'_hex': tokens[position+3*i+j] for j,k in enumerate(AXES)})
                    for i in range(nodes)]
    start = [tuple(binary64(row[k+'_hex']) for k in AXES) for row in initial_rows]
    grid = dict(axes=tuple(axes), velocities={(i,j,k): values[i+dims[0]*(j+dims[1]*k)]
                for k in range(dims[2]) for j in range(dims[1]) for i in range(dims[0])})
    canonical = json.dumps(encode(dict(axes=axes, velocities_x_fastest=values)),
                           sort_keys=True, separators=(',', ':')).encode('ascii')
    return grid, start, initial_rows, hashlib.sha256(canonical).hexdigest()


def final_files(case, native=None):
    name = case['case_id']
    paths = [(HERE/'final' if native is None else native)/(name+'_final.csv'),
             (HERE/'summaries' if native is None else native)/(name+'_summary.json')]
    for path in paths:
        side = read(Path(str(path) + '.identifiers.json'))
        require(side['identity'] == case and side['expected_file'] == path.name, 'Full output identity')
    with paths[0].open(newline='') as stream:
        reader = csv.DictReader(stream)
        require(reader.fieldnames == ['node'] + [k+'_hex' for k in AXES] +
                ['ordinary_'+k+'_hex' for k in AXES], 'Exact final-table schema')
        rows = list(reader)
    require(all(None not in row and None not in row.values() for row in rows), 'Complete final rows')
    require([int(row['node']) for row in rows] == list(range(case['nodes'])), 'Ordered final nodes')
    summary = read(paths[1])
    require(summary['case_id'] == name and summary['status'] == 'completed_bounded_saved_polygon_reoptimization',
            'Completed identified helper')
    require(summary['limits'] == dict(updates=1000, halvings=24, support_sweeps=10000), 'Unchanged limits')
    require(summary['candidate_convergence_status'] is None and not summary['original_flags_modified'],
            'No inherited flag promotion')
    return rows, summary, {path.name: sha(path) for path in paths}


def reference_for(case, grid, path):
    reference = read(HERE/'references/references.json')
    row = reference['records'][case['reference_record_index']]
    require(reference['status'] == 'resolved_three_profile_references' and not row['unresolved']
            and row['status'] == 'resolved_profile_reference', 'Resolved saved reference')
    require(row['native_case'] == case['input_identity']['native_case'], 'Original complete native reference identity')
    require(tuple(map(binary64, row['source_xyz_hex'])) == path[0]
            and tuple(map(binary64, row['receiver_xyz_hex'])) == path[-1], 'Current exact reference endpoints')
    axes = grid['axes']; profile = [[z, grid['velocities'][0,0,k]] for k,z in enumerate(axes[2])]
    require(all(v == profile[k][1] for (i,j,k),v in grid['velocities'].items())
            and reference['profile_exact'] == encode(profile)
            and reference['physical_box_exact'] == encode([[a[0],a[-1]] for a in axes]), 'Exact reference model/box')
    matches = [m for m in row['mesh_cases'] if m['study_case_id'] == case['case_id']]
    require(len(matches) == 1 and matches[0]['numeric_input_sha256'] == case['numeric_input_sha256']
            and matches[0]['simulation_override'] == case['input_identity']['simulation_override'], 'Exact mesh override/reference join')
    return row


def bound(record):
    lo, hi = Q(record['lower_exact']), Q(record['upper_exact'])
    require(lo <= hi, 'Ordered reference interval')
    return lo, hi


def errors(time, partials, reference):
    lo, hi = bound(reference['time_s']); time_error = (time-hi, time-lo)
    vector = []; squared = [Q(0), Q(0)]
    for value, target in zip(partials, reference['source_gradient_s_per_km']):
        lo, hi = bound(target); a, b = value-hi, value-lo; vector.append((a,b))
        squared[0] += Q(0) if a <= 0 <= b else min(a*a,b*b)
        squared[1] += max(a*a,b*b)
    return dict(time_error_s=time_error, source_error_xyz_s_per_km=vector,
                source_error_squared_norm=squared,
                time_within_limit=max(map(abs,time_error)) <= Q(float('2.5e-5')),
                source_within_limit=squared[1] <= Q(float('3e-6'))**2,
                source_norm_upper_display=math.sqrt(float(squared[1])))


def summarize(case, native=None):
    grid, start, unused, model_sha = numeric(case)
    rows, summary, pins = final_files(case, native)
    path = [tuple(binary64(row[k+'_hex']) for k in AXES) for row in rows]
    require(path[0] == start[0] and path[-1] == start[-1], 'Fixed exact endpoints')
    require(all(a != b for a,b in zip(path,path[1:])), 'Positive edges')
    axes = grid['axes']
    require(all(axes[k][0] <= p[k] <= axes[k][-1] for p in path for k in range(3)), 'True physical box')
    reference = reference_for(case,grid,path)
    squared = Q(0); unavailable = []; nodes = []; boundary = 0
    for i in range(1,len(path)-1):
        total = Q(0)
        for k,axis in enumerate(AXES):
            token = rows[i]['ordinary_'+axis+'_hex']
            if not token:
                unavailable.append((i,k)); continue
            value = exact(token)
            if path[i][k] == axes[k][0]:
                value = min(value,Q(0)); boundary += 1
            elif path[i][k] == axes[k][-1]:
                value = max(value,Q(0)); boundary += 1
            total += value*value
        squared += total; nodes.append((total,i))
    nodes.sort(reverse=True)
    lengths2 = [sum((b[k]-a[k])**2 for k in range(3)) for a,b in zip(path,path[1:])]
    action = exact(summary['final']['action_hex'])
    partials = [exact(v) for v in summary['final']['fixed_polygon_source_partial_hex']]
    require(len(partials) == 3, 'Complete fixed-source vector')
    return dict(identity=case, file_sha256=pins, model_sha256=model_sha,
        updates=summary['updates'], attempts=summary['attempts'], stop_reason=summary['stop_reason'],
        approximate_full_candidate=summary['approximate_full_candidate'], final_action=action,
        projected_squared_norm=None if unavailable else squared,
        projected_norm_display=None if unavailable else math.sqrt(float(squared)),
        unavailable_slots=unavailable, physical_boundary_component_count=boundary,
        largest_ten_node_squared_fraction=None if unavailable or squared==0 else sum(t for t,i in nodes[:10])/squared,
        first_edge_squared_km=lengths2[0], first_edge_m_display=1000*math.sqrt(float(lengths2[0])),
        edge_length_m_display=dict(minimum=1000*math.sqrt(float(min(lengths2))),
                                  maximum=1000*math.sqrt(float(max(lengths2)))),
        analytic_comparison=errors(action,partials,reference),
        interval_witness_assessed=False, optimized_source_derivative_certified=False,
        first_arrival_certified=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', help='absent JSON file under repository tmp/')
    parser.add_argument('--native-directory', type=Path, help='six new observer outputs; default: packaged final tables')
    args=parser.parse_args()
    if hasattr(sys,'set_int_max_str_digits'): sys.set_int_max_str_digits(20000)
    manifest=verify_package(); output=fresh_output(args.output)
    cases=read(HERE/'cases.json')['cases']; require(len(cases)==6, 'Six-case roster')
    results=[summarize(c,args.native_directory) for c in cases]
    require(verify_package()==manifest, 'Package unchanged')
    save(output,dict(status='completed_saved_final_table_summary', cases=results,
         package_manifest_sha256=manifest, source_sha256=sha(Path(__file__).resolve()),
         scope='Exact saved hexadecimal arithmetic and reference subtraction only. No accepted-history/QP validation, interval integration, optimizer, or promotion of solver status. Square roots are rounded displays.'))
    print(json.dumps(dict(status='completed_saved_final_table_summary',cases=6,sha256=sha(output))))


if __name__=='__main__':
    main()
