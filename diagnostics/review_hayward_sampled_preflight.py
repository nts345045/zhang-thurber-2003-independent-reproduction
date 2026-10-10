#!/usr/bin/env python3
"""Read saved Hayward samples against pinned continuous 1D references; no rays."""
import argparse
import csv
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import shutil
import sys
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]


def need(value, message):
    if not value:
        raise ValueError(message)


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            digest.update(block)
    return digest.hexdigest()


def load(path):
    return json.loads(path.read_text())


def rows(path):
    with path.open(newline='') as stream:
        reader = csv.DictReader(stream)
        need(reader.fieldnames and len(reader.fieldnames) == len(set(reader.fieldnames)), 'Invalid header')
        result = list(reader)
    need(all(None not in row and all(v is not None for v in row.values()) for row in result), 'Invalid CSV row')
    return result


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def table(path, records):
    need(bool(records), 'Empty comparison table')
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)


def usable(reference):
    first = reference.get('first_arrival')
    return (reference['complete'] and reference['reference_valid'] and
            len(reference.get('near_ties', [])) == 1 and first and
            first.get('source_derivative_s_per_km') is not None and
            all(math.isfinite(float(v)) for v in [first['time_s']] + first['source_derivative_s_per_km']))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', default='data/hayward_first_arrival_004')
    parser.add_argument('--reference', default='data/development/hayward_first_arrival_004_1d_support')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    data, cache, out = [(ROOT / p).resolve() for p in (args.data, args.reference, args.output)]
    for p in (data, cache, out):
        p.relative_to(ROOT)
    need(not out.exists(), 'Fresh output required')
    manifest, ledger, checks = [load(data / n) for n in ('run_manifest.json', 'preflight_execution.json', 'preflight.json')]
    full, review, package = [load(cache / n) for n in ('summary.json', 'independent_review.json', 'packaging.json')]
    need(ledger['status'] == checks['status'] == 'ready_for_accuracy_review' and
         ledger['return_code'] == 0 and not checks['failures'], 'Preflight did not complete its declared gates')
    need(review['status'] == 'passed' and review['summary_sha256'] == sha(cache / 'summary.json') and
         not review['material_issue_found'], 'Unreviewed full reference')
    need(full['accuracy_control_limits']['absolute_time_s'] == 2.5e-5 and
         full['accuracy_control_limits']['source_euclidean_norm_s_per_km'] == 3e-6 and
         full['accuracy']['all']['both_limits_pass'] == full['rays'] == 14262, 'Full reference controls fail')
    pins = dict(manifest['sha256'])
    pins.update({str((data / n).relative_to(ROOT)): v for n, v in checks['sha256'].items()})
    for name in ('run_manifest.json', 'preflight_execution.json', 'preflight.json'):
        pins[str((data / name).relative_to(ROOT))] = sha(data / name)
    for name in ('summary.json', 'independent_review.json', 'packaging.json'):
        pins[str((cache / name).relative_to(ROOT))] = sha(cache / name)
    need(review['packaging_sha256'] == sha(cache / 'packaging.json'), 'Stale reference package review')
    pins[str((cache / package['archive']).relative_to(ROOT))] = package['archive_info']['sha256']
    for name in ('references.jsonl', 'comparison.csv'):
        pins[str((cache / name).relative_to(ROOT))] = package['members'][name]['sha256']
    module = cache / 'source/first_arrival_1d_reference.py'
    pins[str(module.relative_to(ROOT))] = full['output_sha256'][str(module.relative_to(ROOT))]
    pins[str(Path(__file__).resolve().relative_to(ROOT))] = sha(Path(__file__).resolve())

    def verify():
        for name, digest in pins.items():
            need(sha(ROOT / name) == digest, 'Changed input: ' + name)
    verify()
    events, stations, grid, observations = [rows(data / n) for n in
        ('initial_events.csv', 'stations.csv', 'initial_grid.csv', 'observations.csv')]
    samples, derivatives, identities = [rows(data / n) for n in
        ('initial_ray_convergence.csv', 'initial_ray_derivatives.csv', 'initial_ray_identifiers.csv')]
    absolute = {(r['i'], r['station']): (q, r) for q, r in enumerate(observations) if r['type'] == '0'}
    support = {(r['i'], r['station']) for r in observations}
    support.update((r['j'], r['station_j']) for r in observations if int(r['j']) >= 0)
    need(len(absolute) == len(support) == 14262 and set(absolute) == support, 'Native support differs')
    ordered = sorted(support, key=lambda p: tuple(map(int, p)))
    expected = [ordered[n * (len(ordered) - 1) // 31] for n in range(32)]
    need(len(samples) == 32 and [(r['event'], r['station']) for r in samples] == expected and
         [r['diagnostic_row'] for r in samples] == list(map(str, range(32))), 'Sample ordering differs')
    joins = set()
    for n, (i, k) in enumerate(expected):
        for q, row in enumerate(observations):
            if (row['i'], row['station']) == (i, k):
                joins.add((str(n), i, k, str(q), 'i'))
            if (row['j'], row['station_j']) == (i, k):
                joins.add((str(n), i, k, str(q), 'j'))
    keys = ('diagnostic_row', 'event', 'station', 'observation_row', 'observation_event_side')
    need(len(identities) == len(joins) == 210 and {tuple(r[k] for k in keys) for r in identities} == joins,
         'Sample observation associations differ')
    for row in identities:
        for prefix, original, omit in (
            ('source_', events[int(row['event'])], {'id', 'x', 'y', 'z', 't'}),
            ('receiver_', stations[int(row['station'])], {'id', 'x', 'y', 'z', 't'}),
            ('observation_', observations[int(row['observation_row'])], {'i', 'j', 'station', 'type', 'value'})):
            need(all(row[prefix + k] == v for k, v in original.items() if k not in omit), 'Native identity mismatch')
    selected = {}
    with (cache / 'references.jsonl').open() as stream:
        for line in stream:
            item = json.loads(line); pair = (item['event'], item['station'])
            if pair in expected:
                need(pair not in selected and usable(item['reference']), 'Invalid repeated reference')
                need(int(item['observation_row']) == absolute[pair][0], 'Reference/native observation join differs')
                selected[pair] = item
    need(len(selected) == 32, 'Missing sampled references')
    depth_speeds = sorted({(float(r['z']), float(r['v'])) for r in grid})
    need(len(depth_speeds) == len({float(r['z']) for r in grid}) and
         [list(v) for v in depth_speeds] == full['profile_depth_velocity_km_km_s'], 'Not the reviewed depth profile')
    out.mkdir(parents=True)
    (out / 'source').mkdir(); (out / 'inputs').mkdir()
    shutil.copyfile(str(Path(__file__).resolve()), str(out / 'source' / Path(__file__).name))
    shutil.copyfile(str(module), str(out / 'source' / module.name))
    for name in ('initial_ray_convergence.csv', 'initial_ray_derivatives.csv', 'initial_ray_identifiers.csv',
                 'preflight.json', 'preflight_execution.json', 'run_manifest.json'):
        shutil.copyfile(str(data / name), str(out / 'inputs' / name))
    spec = importlib.util.spec_from_file_location('frozen_hayward_sample_reference', str(out / 'source' / module.name))
    ref = importlib.util.module_from_spec(spec); spec.loader.exec_module(ref)
    save(out / 'execution.json', dict(status='running', started_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
         command=[str(Path(__file__).resolve().relative_to(ROOT))] + sys.argv[1:], input_sha256=pins))

    def context(n):
        i, k = expected[n]; q, original = absolute[(i, k)]
        result = dict(original_observation_row=str(q))
        result.update({'original_' + key: value for key, value in original.items()})
        result.update({'source_' + key: value for key, value in events[int(i)].items()})
        result.update({'receiver_' + key: value for key, value in stations[int(k)].items()})
        return result

    compared = []
    for n, row in enumerate(samples):
        need(all(row[p + k] == '1' for p in ('production_', 'refined_') for k in
                 ('converged', 'initialization_attempted', 'initialization_succeeded')), 'Failed sample flag')
        first = selected[expected[n]]['reference']['first_arrival']
        item = dict(row); item.update(context(n)); item['reference_time_s'] = first['time_s']
        item['reference_branch'] = first['kind']
        for mode in ('production', 'refined'):
            error = float(row[mode + '_time']) - first['time_s']
            need(math.isfinite(error), 'Nonfinite sampled time')
            item[mode + '_minus_reference_s'] = error
        compared.append(item)
    saved_selected = [dict(selected[p], native_context=context(n)) for n, p in enumerate(expected)]
    save(out / 'selected_references.json', saved_selected)
    table(out / 'time_comparison.csv', compared)
    component_rows, endpoint_refs = [], []
    need(len(derivatives) == 24 and {(int(r['diagnostic_row']), int(r['axis'])) for r in derivatives} ==
         {(n, a) for n in range(8) for a in range(3)}, 'Derivative support differs')
    for row in derivatives:
        n, axis = int(row['diagnostic_row']), int(row['axis'])
        need((row['event'], row['station']) == expected[n], 'Derivative native pair differs')
        need(all(row[p + k] == '1' for p in ('plus_', 'minus_') for k in
                 ('converged', 'initialization_attempted', 'initialization_succeeded')), 'Failed FD flag')
        source = [float(events[int(row['event'])][a]) for a in 'xyz']
        receiver = [float(stations[int(row['station'])][a]) for a in 'xyz']
        first = selected[expected[n]]['reference']['first_arrival']
        item = dict(row); item.update(context(n))
        item['reference_derivative'] = first['source_derivative_s_per_km'][axis]
        times = {}
        for label, sign in (('plus', 1), ('minus', -1)):
            perturbed = list(source); perturbed[axis] += sign * .01
            answer = ref.enumerate_arrivals([p[0] for p in depth_speeds], [p[1] for p in depth_speeds], perturbed, receiver)
            need(usable(answer), 'Unresolved perturbed reference at ' + str((n, axis, label)))
            times[label] = answer['first_arrival']['time_s']
            endpoint_refs.append(dict(diagnostic_row=n, axis=axis, sign=sign, source_xyz_km=perturbed,
                receiver_xyz_km=receiver, native_context=context(n), reference=answer))
            item[label + '_reference_time_s'] = times[label]
            chosen = label + ('_fmm_seed_time' if row[label + '_selected_fmm_seed'] == '1' else '_direct_seed_time')
            item[label + '_saved_time_minus_reference_s'] = float(row[chosen]) - times[label]
        item['reference_central_difference'] = (times['plus'] - times['minus']) / .02
        item['reference_fd_truncation_s_per_km'] = item['reference_central_difference'] - item['reference_derivative']
        item['saved_fd_minus_reference_fd_s_per_km'] = float(row['finite_difference']) - item['reference_central_difference']
        for mode in ('production', 'refined'):
            item[mode + '_minus_reference_s_per_km'] = float(row[mode + '_derivative']) - item['reference_derivative']
        component_rows.append(item)
    save(out / 'perturbed_references.json', endpoint_refs)
    table(out / 'derivative_comparison.csv', component_rows)
    vectors = []
    for n in range(8):
        item = dict(diagnostic_row=n, event=expected[n][0], station=expected[n][1]); item.update(context(n))
        for mode in ('production', 'refined'):
            item[mode + '_source_error_norm_s_per_km'] = math.sqrt(sum(
                r[mode + '_minus_reference_s_per_km'] ** 2 for r in component_rows if int(r['diagnostic_row']) == n))
        vectors.append(item)
    table(out / 'source_vector_comparison.csv', vectors)
    verify()
    summary = dict(status='completed_saved_sample_comparison', input_sha256=pins,
        source_sha256={p.name: sha(p) for p in (out / 'source').iterdir()},
        counts=dict(sample_rays=32, source_vectors=8, source_components=24, perturbed_references=48,
                    native_observation_associations=210),
        accuracy_control_limits=dict(absolute_time_s=2.5e-5, source_euclidean_norm_s_per_km=3e-6),
        times={mode: dict(maximum_absolute_error_s=max(abs(r[mode + '_minus_reference_s']) for r in compared),
                         passing=sum(abs(r[mode + '_minus_reference_s']) <= 2.5e-5 for r in compared))
               for mode in ('production', 'refined')},
        source_vectors={mode: dict(maximum_error_norm_s_per_km=max(r[mode + '_source_error_norm_s_per_km'] for r in vectors),
                                  passing=sum(r[mode + '_source_error_norm_s_per_km'] <= 3e-6 for r in vectors))
                        for mode in ('production', 'refined')},
        maximum_reference_fd_truncation_s_per_km=max(abs(r['reference_fd_truncation_s_per_km']) for r in component_rows),
        maximum_saved_fd_minus_reference_fd_s_per_km=max(abs(r['saved_fd_minus_reference_fd_s_per_km']) for r in component_rows),
        maximum_saved_perturbed_time_error_s=max(abs(r[p + '_saved_time_minus_reference_s']) for r in component_rows for p in ('plus', 'minus')),
        original_flags_unchanged=True, scientific_acceptance='Requires independent readback and final accuracy review; no inversion launched',
        limitations=['Initial depth-only model and declared samples only; no updated 3D or global branch certificate.',
                     'Only eight full source derivative vectors were saved in the sampled diagnostic; all14262 production vectors have a separate reviewed comparison.',
                     'Central differences use the original0.01km binary64 source perturbation and0.02km denominator, without a new finite-difference acceptance threshold.',
                     'Continuous reference times use reviewed branch enumeration and ordinary floating time ordering; no near-tied or unresolved reference is accepted.',
                     'Selected plus/minus candidate times have12-significant-digit serialization; saved finite differences were formed before that serialization.'])
    save(out / 'execution.json', dict(status='completed', return_code=0,
         finished_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), input_sha256=pins))
    summary['output_sha256'] = {str(p.relative_to(out)): sha(p) for p in sorted(out.rglob('*')) if p.is_file()}
    save(out / 'summary.json', summary)
    print(json.dumps({k: v for k, v in summary.items() if k not in ('input_sha256', 'output_sha256', 'source_sha256')}, indent=2))


if __name__ == '__main__':
    main()
