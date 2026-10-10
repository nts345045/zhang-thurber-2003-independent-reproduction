#!/usr/bin/env python3
"""Independent saved-only review; never compiles or invokes a ray solver."""
import ast
import csv
import datetime
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = ROOT / 'data/development/loma_lon_straight_curvature_replay_001'

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()

def rows(path):
    with path.open() as stream:
        return list(csv.DictReader(stream))

def main():
    prepared = json.loads((HERE / 'prepared.json').read_text())
    assert sha(HERE / 'prepared.json') == '42160974ce6642cee79363d9910c742ad2db9d5f9dad08b1e92f6b2556837013'
    counts = {}
    for key, root in [('original_sha256', ROOT), ('runtime_sha256', Path('/')), ('output_sha256', HERE), ('source_sha256', HERE)]:
        for name, expected in prepared[key].items():
            assert sha(root / name) == expected, (key, name)
        counts[key] = len(prepared[key])
    assert prepared['native_pairs'] == [8670, 8674] and prepared['native_calls'] == 2
    assert prepared['flags'] == ['-std=gnu++17', '-O3', '-Wall', '-Wextra', '-Wpedantic', '-fopenmp']
    assert prepared['settings'] == {'ray_spacing_km': .03125, 'maximum_updates': 1000,
        'strict_projected_gradient': 1e-7, 'armijo_trials': 24, 'seed': None,
        'time_limit_s': 2.5e-5, 'source_norm_limit_s_per_km': 3e-6}
    original = (BASE / 'source/D/src/core.hpp').read_bytes()
    before = b'if (change < 1e-11 && projected_ray_gradient(g, p, grad) < 1e-5) {'
    after = b'if (false && change < 1e-11 && projected_ray_gradient(g, p, grad) < 1e-5) {'
    assert original.count(before) == 1
    assert (HERE / 'source/strict/src/core.hpp').read_bytes() == original.replace(before, after)
    source_names = sorted(str(p.relative_to(BASE / 'source/D')) for p in (BASE / 'source/D').rglob('*') if p.is_file())
    assert source_names == sorted(str(p.relative_to(HERE / 'source/strict')) for p in (HERE / 'source/strict').rglob('*') if p.is_file())
    for name in source_names:
        if name != 'src/core.hpp':
            assert (BASE / 'source/D' / name).read_bytes() == (HERE / 'source/strict' / name).read_bytes()
    assert (HERE / 'driver.cpp').read_bytes() == (BASE / 'driver.cpp').read_bytes().replace(
        b'// Four calls total are authorized:', b'// Two calls total are authorized:')
    trees = [ast.parse((p).read_text()) for p in [BASE / 'run_v3.py', HERE / 'run.py']]
    preserved_functions = ['group_members', 'signal_group', 'terminate_and_reap', 'interrupted', 'command', 'verify']
    for name in preserved_functions:
        functions = [[node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == name] for tree in trees]
        assert [len(x) for x in functions] == [1, 1]
        assert ast.dump(functions[0][0]) == ast.dump(functions[1][0]), name
    context = json.loads((HERE / 'inputs/native_context.json').read_text())
    events, stations = rows(HERE / 'inputs/initial_events.csv'), rows(HERE / 'inputs/stations.csv')
    assert (len(events), len(stations)) == (724, 52)
    reference = rows(HERE / 'inputs/selected_reference.csv')
    comparison = rows(HERE / 'inputs/selected_comparison.csv')
    baseline = rows(HERE / 'inputs/baseline_D/scalars_17.csv')
    assert len(context) == len(reference) == len(comparison) == len(baseline) == 2
    joined_fields = 0
    for pair, native, ref, comp, old in zip([8670, 8674], context, reference, comparison, baseline):
        i, k = divmod(pair, 52)
        assert native['pair_index'] == pair
        assert native['source_native'] == events[i] and native['receiver_native'] == stations[k]
        assert native['saved_comparison_row'] == comp
        assert int(ref['pair_index']) == pair
        assert ref['reference_complete'] == ref['reference_valid'] == '1' and ref['near_tie_count'] == '1'
        for row in (ref, comp, old):
            assert (int(row['event']), int(row['station'])) == (i, k)
            for prefix, source in [('source_', events[i]), ('receiver_', stations[k])]:
                for key, value in source.items():
                    if key not in ('id', 'x', 'y', 'z', 't'):
                        assert row[prefix + key] == value, (pair, prefix + key)
                        joined_fields += 1
        assert stations[k]['location_code'] == ''
        assert float(comp['reference_time_s']) == float(ref['time_s'])
        for axis in 'xyz':
            assert float(comp['reference_source_d' + axis + '_s_per_km']) == float(ref['source_d' + axis + '_s_per_km'])
    saved_review = json.loads((HERE / 'inputs/baseline_review.json').read_text())
    saved_summary = json.loads((HERE / 'inputs/baseline_summary.json').read_text())
    saved_execution = json.loads((HERE / 'inputs/baseline_execution.json').read_text())
    assert saved_review['status'] == 'passed'
    assert saved_review['summary_sha256'] == saved_execution['summary_sha256'] == sha(HERE / 'inputs/baseline_summary.json')
    assert saved_execution['status'] == 'completed' and saved_execution['return_code'] == 0
    for name, expected in saved_summary['output_sha256'].items():
        assert sha(BASE / name) == expected, name
    for name in ('build', 'logs', 'results', 'execution.json', 'summary.json'):
        assert not (HERE / name).exists(), name
    review = {'status': 'passed', 'reviewer': 'scientific_audit',
        'reviewed_utc': datetime.datetime.utcnow().isoformat() + 'Z',
        'scope': 'Read-only saved-source/hash/native/prelaunch review; no compiler, ray, reference, action, network or live-job invocation.',
        'prepared_sha256': sha(HERE / 'prepared.json'), 'runner_sha256': sha(HERE / 'run.py'),
        'driver_sha256': sha(HERE / 'driver.cpp'), 'checker_sha256': sha(Path(__file__)),
        'pin_counts': counts, 'native_metadata_cells_checked': joined_fields,
        'source_members': len(source_names), 'numerical_change': 'Exactly one false && insertion disables the combined early stop. All other D source bytes and driver arithmetic are unchanged.',
        'preserved_lifecycle_functions_ast_equal': preserved_functions,
        'termination_scope': 'Derived from inspected control flow, not captured history. Accepted-update count 1000 takes budget precedence; returned strict flag is retained independently.',
        'known_wording_correction': 'The frozen runner inherited one scientific_scope string saying four calls. Actual driver, scope, planned/completed counts and authorized execution are exactly two calls; interpret that one string as two. No extra calls authorized.',
        'limits': {'time_s': 2.5e-5, 'source_euclidean_norm_s_per_km': 3e-6, 'strict_gradient_s_per_km': 1e-7, 'maximum_updates': 1000},
        'limitations': ['Two straight-seed cases only; no full-cohort or global-first-arrival certificate.',
            'Strict flags, action decrease and source accuracy are separate outcomes.',
            'Any changed node count or merge count must be reported; no fixed-representation claim if merging occurs.',
            'Maintained source, live sources/binaries/inputs and inverse gates are unchanged.'],
        'native_context': context}
    with (HERE / 'prelaunch_review.json').open('x') as stream:
        json.dump(review, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'status': 'passed', 'review_sha256': sha(HERE / 'prelaunch_review.json'), 'pin_counts': counts, 'native_metadata_cells_checked': joined_fields}))

if __name__ == '__main__':
    main()
