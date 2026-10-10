#!/usr/bin/env python3
"""Invented native-table accounting controls; no authoritative ray is traced."""
import argparse
import csv
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    out = (ROOT / args.output).resolve()
    out.relative_to(ROOT)
    if out.exists():
        raise ValueError('Fresh control output required')
    (out / 'source').mkdir(parents=True)
    pins = {}
    for name in ('run_curvature_capture.py', 'check_curvature_launcher.py'):
        path = ROOT / 'diagnostics' / name
        pins[str(path.relative_to(ROOT))] = sha(path)
        shutil.copyfile(str(path), str(out / 'source' / name))
    spec = importlib.util.spec_from_file_location('frozen_launcher', str(out / 'source/run_curvature_capture.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    fixture = out / 'invented'
    fixture.mkdir()
    checks = []

    def check(name, passed):
        checks.append(dict(name=name, passed=bool(passed)))
        if not passed:
            raise ValueError('Failed check: ' + name)

    def write(name, rows, fields=None):
        opener = gzip.open if name.endswith('.gz') else open
        with opener(str(fixture / name), 'wt', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=fields or list(rows[0]), lineterminator='\n')
            writer.writeheader()
            writer.writerows(rows)

    identity = dict(run_id='fmm_invented', observation_index='invented')
    results = [dict(identity, initialization='fmm', logged_matches_unobserved_variant='1', path_nodes='3'),
               dict(run_id='straight_invented', observation_index='invented', initialization='straight',
                    logged_matches_unobserved_variant='1', path_nodes='3')]
    history = [dict(identity, phase='accepted', iteration=str(i), updates=str(i+1), curvature_pair_accepted='0',
                    time_s='1', accepted_step='0.5', memory_pairs='0') for i in range(1000)]
    pairs = [dict(identity, iteration=str(i), update=str(i+1), retained='0', accepted_action_s='1',
                  step='0.5', memory_after_size='0') for i in range(1000)]
    selected = [33, 34, 47, 48, 433, 434, 435, 988, 989, 990, 991, 992, 993, 994, 995, 996, 997, 998, 999]
    geometry = [dict(identity, iteration=str(i), state=state, node=str(node), x=str(node), y='0', z='0')
                for i in selected for state in ('base', 'accepted') for node in range(3)]
    seeds = [dict(identity, kind=kind, node=str(node), x=str(node), y='0', z='0')
             for kind in ('raw_fmm_seed', 'post_resampling_and_merge') for node in range(3)]
    write('results.csv', results)
    write('history.csv', history)
    for name in ('paths.csv', 'path_gradient_checks.csv', 'cone_metric.csv'):
        write(name, [identity])
    write('curvature_pairs.csv', pairs)
    write('curvature_selected_geometry.csv', geometry)
    write('curvature_initialization.csv', seeds)
    for name in ('curvature_components.csv.gz', 'curvature_selected_cuts.csv', 'curvature_seed_metadata.csv'):
        write(name, [identity])
    write('curvature_memory_events.csv', [], fields=list(identity))
    prepared = dict(expected_old_table_sha256={name:sha(fixture/name) for name in module.OLD_TABLES},
                    native_context=dict(observation_index='invented', source_x_km='0', source_y_km='0', source_z_km='0',
                                        receiver_x_km='2', receiver_y_km='0', receiver_z_km='0'),
                    selected_iterations=selected)
    original = {p.name:p.read_bytes() for p in fixture.iterdir()}
    try:
        values, counts, kinds = module.validate_capture(fixture, prepared)
        check('valid_inventory_and_both_start_ids', values == results and counts['curvature_pairs.csv'] == 1000)
        check('all_19_selected_pre_post_paths', counts['curvature_selected_geometry.csv'] == 19*2*3)
        check('header_only_memory_events_valid', counts['curvature_memory_events.csv'] == 0)
        check('raw_and_resampled_seed_inventory', kinds == dict(raw_fmm_seed=3, post_resampling_and_merge=3))
        for name, mutate in [
                ('old_byte_change', lambda: (fixture/'paths.csv').write_text('changed\n')),
                ('missing_pair', lambda: write('curvature_pairs.csv', pairs[:-1])),
                ('duplicate_pair', lambda: write('curvature_pairs.csv', pairs+[pairs[-1]])),
                ('wrong_native_pair', lambda: write('curvature_pairs.csv', [dict(pairs[0], observation_index='other')]+pairs[1:])),
                ('changed_retention', lambda: write('curvature_pairs.csv', [dict(pairs[0], retained='1')]+pairs[1:])),
                ('changed_accepted_step', lambda: write('curvature_pairs.csv', [dict(pairs[0], step='0.25')]+pairs[1:])),
                ('changed_memory_size', lambda: write('curvature_pairs.csv', [dict(pairs[0], memory_after_size='1')]+pairs[1:])),
                ('missing_selected_geometry', lambda: write('curvature_selected_geometry.csv', geometry[3:])),
                ('wrong_endpoint', lambda: write('curvature_selected_geometry.csv', [dict(geometry[0], x='0.001')]+geometry[1:])),
                ('nonfinite_geometry', lambda: write('curvature_selected_geometry.csv', [dict(geometry[0], x='nan')]+geometry[1:])),
                ('wrong_new_table_identity', lambda: write('curvature_selected_cuts.csv', [dict(identity, run_id='other')])),
                ('duplicate_seed_metadata', lambda: write('curvature_seed_metadata.csv', [identity, identity])),
                ('incomplete_saved_seed', lambda: write('curvature_initialization.csv', seeds[:3])),
                ('wrong_seed_node_order', lambda: write('curvature_initialization.csv', [dict(seeds[0], node='1')]+seeds[1:]))]:
            mutate()
            rejected = False
            try:
                module.validate_capture(fixture, prepared)
            except ValueError:
                rejected = True
            check('reject_' + name, rejected)
            for filename, data in original.items():
                (fixture/filename).write_bytes(data)
        check('restored_fixture_passes', module.validate_capture(fixture, prepared)[1] == counts)
        check('sources_unchanged', all(sha(ROOT/name) == digest for name,digest in pins.items()))
        result = dict(status='passed', check_count=len(checks), checks=checks, source_sha256=pins,
            scope='Invented table inventory and identity controls only; no compiler, signal, numerical kernel or native trace validation',
            output_sha256={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()})
    except BaseException as error:
        result = dict(status='failed', failure=repr(error), checks=checks, source_sha256=pins)
        raise
    finally:
        (out/'summary.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(str(out/'summary.json'),flush=True)


if __name__ == '__main__':
    main()
