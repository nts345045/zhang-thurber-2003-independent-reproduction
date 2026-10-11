#!/usr/bin/env python3
"""Saved-only transport for exactly two reference-selected curves; no evaluator."""
import argparse
import csv
import gzip
import hashlib
import json
import math
import pathlib
import re
import shutil
import sys
from fractions import Fraction as Q

SOURCE = pathlib.Path(__file__).resolve().parent
ROOT = SOURCE.parents[1]
ORIGINAL = ROOT / 'data/development/integrated_face_ray_candidate_001'
LOM = ROOT / 'tmp/lom24104_endpoint_reference_001'
LON = ROOT / 'data/development/loma_lon_initial_accuracy_001/inputs/reference'
ORDER = ('lom_24104', 'lon_8670')
PINS = {
    'data/development/integrated_face_ray_candidate_001/native_inputs.json': 'af6909b5e6942b0dc424931b715ac7383f996a292beeea6748c816d6fc4db134',
    'tmp/lom24104_endpoint_reference_001/references.json': '35abd5792e404fcb5e073aa30eb790af2d907b458cc94aedb3904dbf297964f9',
    'tmp/lom24104_endpoint_reference_001/identifiers.json': '67c7f903b205261384009a5e4d992f6baae5687031b922f91d0fb9e19bca7229',
    'tmp/lom24104_endpoint_reference_001/execution_receipt.json': 'c99640e62a0531ec6a4e3b57788e963ba6424b1e46b4f25bc65b1d77ff6769aa',
    'tmp/lom24104_endpoint_reference_001/readback.json': '09058af2c84735cbfc5d1f96a1a6b73c6cd62518e16eef266b1d8f4a27c287cc',
    'tmp/lom24104_endpoint_reference_source_001/source_review.json': '230b21f25f70b3d8550c10e74df46951e0aa337d8258cfc65bfc63f75b9438ef',
    'data/development/loma_lon_initial_accuracy_001/inputs/reference/certificates.jsonl.gz': '9e9b2ab541bd97b539d016aa0b229d3192cf8d18110ccd3e0bd470369c28e51b',
    'data/development/loma_lon_initial_accuracy_001/inputs/reference/references.csv.gz': '9fc1ef04877f42395fbe840c24d27d405f62d11af7faf0c98690bdb47e51fa89',
    'data/development/loma_lon_initial_accuracy_001/inputs/reference/summary.json': '6933ca71c17a9795c137884581a44fc82047735a5021fb3ab9815dbc573ffebf',
    'data/development/loma_lon_initial_accuracy_001/inputs/reference/execution.json': '369bc74b2769f02ed7a25b2cd3b0f82567af894ee16fc499116bac0f24bf3baa',
    'data/development/loma_lon_initial_accuracy_001/inputs/reference/review.json': '9660c489b6f3dfe78789d73416c07446ed33fb22bae2ec35a162847ed71c24e4',
    'data/development/loma_lon_initial_accuracy_001/inputs/reference/independent_review.json': '835d14f3e45fab516db9a31666cefb859ee94e0cee280162f8986229a3b95c40',
    'data/development/loma_lon_initial_accuracy_001/inputs/reference/inputs/initial_grid.csv': '121eb9afae309427db7dc579f951d1732ce6f28d674948889bde91ca88d5dcd0',
    'data/development/loma_lon_initial_accuracy_001/inputs/reference/inputs/initial_events.csv': '1804277ec710107e49a7a9140eeb2972c6683198069c00f15d7794bfc4101f48',
    'data/development/loma_lon_initial_accuracy_001/inputs/reference/inputs/stations.csv': '4500b0f7b97a2fa4f90f7dd18a22e5cc08b78843a711af5a39262f6a76d1a7da',
}
INPUTS = {}


def need(condition, message):
    if not condition:
        raise RuntimeError(message)


def pin(path, expected=None):
    path = pathlib.Path(path)
    need(path.is_file() and not path.is_symlink(), 'missing/nonregular/symlink input: ' + str(path))
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    need(expected is None or digest == expected, 'hash mismatch: ' + str(path))
    INPUTS[str(path.relative_to(ROOT))] = digest
    return digest


def read(path):
    pin(path)
    return json.loads(path.read_text())


def output_pins(base, mapping):
    for name, digest in mapping.items():
        path = pathlib.Path(name)
        need(not path.is_absolute() and '..' not in path.parts, 'unsafe relative pin')
        pin(base / path, digest)


def rational(value):
    value = Q(value)
    return '{}/{}'.format(value.numerator, value.denominator)


def numeric(case):
    path = ORIGINAL / 'native_inputs' / case['numeric_input']
    pin(path, case['numeric_input_sha256'])
    sidecar = pathlib.Path(str(path) + '.identifiers.json')
    need(read(sidecar) == case, 'complete original numeric identity')
    words = path.read_text().split()
    dims = list(map(int, words[:3])); at = 3; axes = []
    need(dims == case['dimensions'] and all(n >= 2 for n in dims), 'native dimensions')
    for n in dims:
        axis = [float.fromhex(s) for s in words[at:at+n]]; at += n
        need(all(math.isfinite(x) for x in axis) and all(a < b for a, b in zip(axis, axis[1:])), 'axis')
        axes.append(axis)
    count = dims[0] * dims[1] * dims[2]
    values = [float.fromhex(s) for s in words[at:at+count]]; at += count
    need(all(math.isfinite(v) and v > 0 for v in values), 'velocity')
    nodes = int(words[at]); at += 1
    need(nodes == case['nodes'] and len(words) == at + 3 * nodes, 'original polygon token count')
    ends = [[float.fromhex(s) for s in words[at:at+3]], [float.fromhex(s) for s in words[-3:]]]
    for end, key in zip(ends, ('source_native', 'receiver_native')):
        need(end == [float(case[key][k]) for k in ('x', 'y', 'z')], 'exact native endpoints')
    plane = dims[0] * dims[1]
    profile = [values[k*plane] for k in range(dims[2])]
    need(all(values[k*plane+j] == profile[k] for k in range(dims[2]) for j in range(plane)), 'global exact depth-only model')
    return path, sidecar, axes, values, ends, profile


def lom_reference(case, data):
    refs = read(LOM / 'references.json'); receipt = read(LOM / 'execution_receipt.json')
    reviewed = read(LOM / 'readback.json'); ids = read(LOM / 'identifiers.json')
    approval_path = ROOT / 'tmp/lom24104_endpoint_reference_source_001/source_review.json'
    approval = read(approval_path)
    need(approval['status'] == 'passed_source_only', 'LOM source approval')
    output_pins(approval_path.parent, approval['output_sha256'])
    need(receipt['status'] == 'completed_and_reaped' and receipt['return_code'] == 0 and
         receipt['observed_command_exit_code'] == 0 and receipt['child_reaped'] and
         receipt['process_absent'] and receipt['group_absent_including_zombies'] and
         receipt['literal_group_members_including_zombies'] == [], 'LOM actual closure')
    output_pins(LOM, receipt['output_sha256'])
    need(reviewed['status'] == 'passed' and reviewed['execution_receipt_sha256'] == pin(LOM / 'execution_receipt.json'), 'LOM readback')
    need(refs['source_review_sha256'] == receipt['source_review_sha256'] == reviewed['source_review_sha256'] == pin(approval_path), 'LOM source-role join')
    need(receipt['source_sha256'] == pin(approval_path.parent / 'run.py'), 'LOM evaluated source')
    need(receipt['native_case'] == reviewed['native_case'] == ids['native_case'] == case, 'LOM complete native identity')
    record = refs['records'][0]
    need(refs['status'] == 'resolved_three_profile_references' and record['status'] == 'resolved_profile_reference' and
         record['branch'] == 'bottom_boundary' and record['native_case'] == case and record['unresolved'] == [], 'LOM selected branch')
    axes, values, ends, profile = data[2:]
    need([[Q(a), Q(b)] for a, b in refs['profile_exact']] == [[Q(z), Q(v)] for z, v in zip(axes[2], profile)], 'LOM exact model')
    need([[Q(a), Q(b)] for a, b in refs['physical_box_exact']] == [[Q(a[0]), Q(a[-1])] for a in axes], 'LOM physical box')
    need(record['source_xyz_hex'] == [v.hex() for v in ends[0]] and record['receiver_xyz_hex'] == [v.hex() for v in ends[1]], 'LOM exact endpoint record')
    need(refs['identity_sidecar_sha256'] == pin(LOM / 'identifiers.json'), 'LOM reference sidecar')
    guide = [Q(record['horizontal_guide_length_km'][k]) for k in ('lower_exact', 'upper_exact')]
    need(0 < guide[0] <= guide[1] and Q(ends[0][2]) == Q(axes[2][-1]), 'LOM positive bottom guide')
    u = Q(profile[-1]); turn = Q(axes[2][-1])
    return dict(branch='bottom_boundary', u=rational(u), u_enclosure=[rational(u)]*2,
                turn=rational(turn), guide=rational((guide[0]+guide[1])/2),
                guide_enclosure=list(map(rational, guide)), reference_record=record,
                reference_file=str((LOM/'references.json').relative_to(ROOT)), reference_selector={'records_index': 0})


def lon_reference(case, data):
    summary = read(LON/'summary.json'); execution = read(LON/'execution.json')
    reviews = [read(LON/n) for n in ('review.json', 'independent_review.json')]
    need(summary['status'] == 'complete' and summary['reference_comparison_ready'] and
         execution['status'] == 'completed' and execution['result_status'] == 'complete' and
         execution['summary_sha256'] == pin(LON/'summary.json'), 'LON inherited completed reference')
    need(all(r['status'] == 'passed' and r['reference_comparison_ready'] and
             r['native_metadata_fields_all_match'] and r['summary_sha256'] == pin(LON/'summary.json') and
             r['execution_sha256'] == pin(LON/'execution.json') for r in reviews), 'LON dual saved reviews')
    # Only consumed inputs and the three executed source files are rehashed.
    names = ['certificates.jsonl.gz', 'references.csv.gz', 'inputs/initial_grid.csv',
             'inputs/initial_events.csv', 'inputs/stations.csv']
    names += sorted(n for n in summary['output_sha256'] if n.startswith('source/'))
    output_pins(LON, {n: summary['output_sha256'][n] for n in names})
    for n in names:
        if n.startswith('source/'):
            need(execution['input_source_sha256']['diagnostics/'+pathlib.Path(n).name] == summary['output_sha256'][n], 'LON executed source join')
    rows = []
    with gzip.open(str(LON/'certificates.jsonl.gz'), 'rt') as stream:
        for line in stream:
            row = json.loads(line)
            if row['pair_index'] == case['pair_index']:
                rows.append(row)
    need(len(rows) == 1, 'LON unique selected certificate'); row = rows[0]
    need(row['event'] == case['event'] and row['station'] == case['station'] and not row['source_time_included'], 'LON local index join')
    ref = row['reference']; selected = ref['first_arrival']
    need(ref['complete'] and ref['reference_valid'] and not ref['unresolved'] and
         ref['candidates'] == [selected] and ref['near_ties'] == [0] and
         ref['best_enumerated_candidate'] == selected and selected['kind'] == 'turning', 'LON unique saved branch')
    with gzip.open(str(LON/'references.csv.gz'), 'rt') as stream:
        matches = [r for r in csv.DictReader(stream) if int(r['pair_index']) == case['pair_index']]
    need(matches == [case['analytic_reference']['row']], 'LON complete original reference metadata')
    for filename, key, index in [('initial_events.csv', 'source_native', case['event']), ('stations.csv', 'receiver_native', case['station'])]:
        with (LON/'inputs'/filename).open() as stream:
            matches = [r for r in csv.DictReader(stream) if int(r['id']) == index]
        need(matches == [case[key]], 'LON complete native input row')
    axes, values, ends, profile = data[2:]
    with (LON/'inputs/initial_grid.csv').open() as stream:
        grid = list(csv.DictReader(stream))
    expected = [(x, y, z, values[(k*len(axes[1])+j)*len(axes[0])+i])
                for k,z in enumerate(axes[2]) for j,y in enumerate(axes[1]) for i,x in enumerate(axes[0])]
    need([tuple(float(r[k]) for k in ('x','y','z','v')) for r in grid] == expected, 'LON all nodal model values/order')
    need(summary['profile_depth_velocity_km_km_s'] == [list(p) for p in zip(axes[2], profile)] and
         summary['original_box_km'] == [[a[0],a[-1]] for a in axes], 'LON profile/box')
    u = selected['u_rational']; enclosure = selected['turning_u_enclosure_rational']
    turn = selected['turning_depth_rational']
    need(Q(enclosure[0]) <= Q(u) <= Q(enclosure[1]) and max(ends[0][2], ends[1][2]) < Q(turn) <= axes[2][-1], 'LON exact saved turn/enclosure')
    return dict(branch='turning', u=u, u_enclosure=enclosure, turn=turn, guide='0/1', guide_enclosure=['0/1','0/1'],
                reference_record=row, reference_file=str((LON/'certificates.jsonl.gz').relative_to(ROOT)),
                reference_selector={'pair_index':case['pair_index'],'event':case['event'],'station':case['station']})


def write_json(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False); stream.write('\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-approval-sha256', default='PENDING')
    parser.add_argument('--output', type=pathlib.Path, default=ROOT/'tmp/layered_reference_selected_curve_001')
    args = parser.parse_args()
    need(re.fullmatch(r'[0-9a-f]{64}', args.source_approval_sha256) is not None, 'source approval binding PENDING')
    approval_path = SOURCE/'source_review.json'; pin(approval_path, args.source_approval_sha256)
    approval = read(approval_path)
    need(approval['status'] == 'passed_source_only', 'own source approval')
    output_pins(SOURCE, approval['output_sha256'])
    for name in ('prepare.py','reference_selected_curve.hpp','observe_reference_curve.cpp','layered_curved_ray.hpp'):
        need(name in approval['output_sha256'], 'missing approved source '+name)
    for name, digest in PINS.items():
        pin(ROOT/name, digest)
    manifest = read(ORIGINAL/'native_inputs.json')
    need(manifest['status'] == 'prepared_saved_inputs_only', 'original input manifest')
    cases = [next(c for c in manifest['cases'] if c['case_id'] == key) for key in ORDER]
    staged = []
    for case in cases:
        data = numeric(case)
        for path in data[:2]:
            pin(path, manifest['output_sha256'][str(path.relative_to(ORIGINAL))])
        selected = (lom_reference if case['case_id'] == ORDER[0] else lon_reference)(case, data)
        tokens = ['reference_selected_curve_v1', case['case_id'], selected['branch'], selected['u'], selected['turn'],
                  selected['guide'], 'not_assessed_by_this_component', 'selected_curve_only']
        need(len(tokens) == 8 and all(len(t.split()) == 1 and '/' in t for t in tokens[3:6]), 'eight-token rational spec')
        envelope = dict(native_case=case, selected_reference=selected,
                        original_numeric_sha256=case['numeric_input_sha256'],
                        source_xyz_hex=[x.hex() for x in data[4][0]], receiver_xyz_hex=[x.hex() for x in data[4][1]],
                        curve_spec_tokens=tokens, reference_selection_independent_of_this_component=True,
                        scope='Selected-curve diagnostic only; no branch enumeration, uniqueness promotion, endpoint snap, polygon solve, or inversion.',
                        conversion='C++ strtold numerator and denominator, then working long-double division; no correct-rounding claim.')
        staged.append((case, data, tokens, envelope))
    requested = args.output.absolute()
    need(not requested.exists() and not requested.is_symlink(), 'requested output must be absent, including dangling links')
    out = requested.parent.resolve() / requested.name
    need(ROOT in out.parents and out.parent.is_dir() and not out.exists() and not out.is_symlink(),
         'resolved output must be fresh and project-local')
    compiler = pathlib.Path('/usr/bin/g++').resolve()
    runtime = {str(compiler): hashlib.sha256(compiler.read_bytes()).hexdigest(),
               str(pathlib.Path(sys.executable).resolve()): hashlib.sha256(pathlib.Path(sys.executable).resolve().read_bytes()).hexdigest()}
    # All semantic and closed-evidence checks precede the first output write.
    out.mkdir(); (out/'inputs').mkdir(); (out/'results').mkdir(); (out/'build').mkdir(); (out/'tmp').mkdir()
    commands = []; transports = []
    for case, data, tokens, envelope in staged:
        name = case['case_id']; numeric_out = out/'inputs'/(name+'.input'); curve = out/'inputs'/(name+'.curve')
        result = out/'results'/(name+'.result.json')
        shutil.copyfile(str(data[1]), str(numeric_out)+'.identifiers.json')
        write_json(pathlib.Path(str(curve)+'.identifiers.json'), envelope)
        write_json(pathlib.Path(str(result)+'.identifiers.json'), envelope)
        shutil.copyfile(str(data[0]), str(numeric_out))
        with curve.open('x') as stream: stream.write('\n'.join(tokens)+'\n')
        commands.append([str(out/'build/observe_reference_curve'),str(numeric_out),str(curve),str(result)])
        transports.append(dict(native_case=case, numeric_input=str(numeric_out.relative_to(out)),
                               curve_spec=str(curve.relative_to(out)), result=str(result.relative_to(out)), selected_reference=envelope['selected_reference']))
    outputs = {str(p.relative_to(out)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.rglob('*')) if p.is_file()}
    need(len(outputs) == 10, 'ten copied/generated inputs and preattached identity sidecars')
    prepared = dict(status='prepared_saved_reference_transport', native_cases=cases, cases=transports,
                    input_sha256=INPUTS, output_sha256=outputs, runtime_sha256=runtime,
                    source_review_sha256=args.source_approval_sha256,
                    compile_command=[str(compiler),'-std=c++17','-O2','-Wall','-Wextra','-Wpedantic',str(SOURCE/'observe_reference_curve.cpp'),'-o',str(out/'build/observe_reference_curve')],
                    observer_commands=commands, environment={'LC_ALL':'C','TMPDIR':str(out/'tmp'),'PYTHONDONTWRITEBYTECODE':'1',
                                                            'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1'},
                    case_count=2, compiler_calls=0, observer_calls=0, reference_calls=0, solver_calls=0,
                    pending_execution='Root/parent-owned one compiler and exactly two observers only after concrete source/call inventory review.')
    write_json(out/'prepared.json', prepared)
    print(json.dumps({'status':prepared['status'],'output':str(out),'case_ids':list(ORDER),'transport_files':len(outputs)},sort_keys=True))


if __name__ == '__main__':
    main()
