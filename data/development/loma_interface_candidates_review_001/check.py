#!/usr/bin/env python3
"""Read back saved interface probes; evaluate no optimizer or ray solve."""
import argparse
import csv
from decimal import Decimal, localcontext
from fractions import Fraction as Q
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
CASE = ROOT / 'data/development/loma_interface_candidates_002'
EXPECTED = '7bdbabbbd09f4edae34a7f9cae168f892fef11b64479997b38e0d361d66472b4'
NATIVE = 'data/development/loma_outer_accumulation_native_001'


def need(value, message):
    if not value:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def load(name, relative):
    path = CASE / 'inputs' / relative
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def d(q):
    return Decimal(q.numerator) / Decimal(q.denominator)


def velocity(profile, z):
    for (lo, va), (hi, vb) in zip(profile, profile[1:]):
        if lo <= z <= hi:
            return va + (vb - va) * (z - lo) / (hi - lo)
    raise ValueError('Depth outside frozen profile')


def decimal_segment(profile, a, b):
    """Independent t-parameter integration in original xyz coordinates."""
    delta = tuple(y - x for x, y in zip(a, b))
    squared = sum(q * q for q in delta)
    need(squared > 0, 'Zero-length segment')
    cuts = {Q(0), Q(1)}
    if delta[2]:
        cuts.update((z - a[2]) / delta[2] for z, v in profile
                    if 0 < (z - a[2]) / delta[2] < 1)
    cuts = sorted(cuts)
    average = Decimal(0)
    for lo, hi in zip(cuts, cuts[1:]):
        va = velocity(profile, a[2] + lo * delta[2])
        vb = velocity(profile, a[2] + hi * delta[2])
        average += d(hi - lo) * (1 / d(va) if va == vb else
                                (d(vb) / d(va)).ln() / d(vb - va))
    return d(squared).sqrt() * average


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--attach', action='store_true')
    args = parser.parse_args()
    target = (ROOT / args.output).resolve()
    target.relative_to(ROOT)
    need(not target.exists(), 'Review output must be fresh')
    attached = CASE / 'review.json'
    need(not args.attach or not attached.exists(), 'Attached review already exists')
    summary_path = CASE / 'summary.json'
    need(sha(summary_path) == EXPECTED, 'Selected summary changed')
    s = json.loads(summary_path.read_text())
    need(s['status'] == 'completed_saved_action_probes', 'Nonterminal probe package')
    pins = {str(summary_path.relative_to(ROOT)): EXPECTED,
            str(Path(__file__).resolve().relative_to(ROOT)): sha(Path(__file__).resolve())}
    for key, digest in s['input_sha256'].items():
        need(sha(ROOT / key) == digest, 'Current input differs: ' + key)
        need(sha(CASE / 'inputs' / key) == digest, 'Frozen input differs: ' + key)
        pins[key] = digest
    for key, digest in s['artifact_sha256'].items():
        need(sha(CASE / key) == digest, 'Artifact differs: ' + key)
        pins[str((CASE / key).relative_to(ROOT))] = digest
    need(not list(CASE.rglob('*.pyc')) and not list(CASE.rglob('__pycache__')),
         'Unexpected interpreter cache in frozen variant')
    expected_checks = ['unchanged_polygon_cancels_exactly']
    for nodes in ((1,), (2,), (1, 2)):
        expected_checks.extend(prefix + str(nodes) for prefix in
                               ('invented_decrease_', 'invented_reversal_',
                                'invented_changed_edge_count_', 'invented_closed_form_'))
    need([c['name'] for c in s['checks']] == expected_checks and
         all(c['passed'] is True for c in s['checks']), 'Invented checks changed')
    frozen = CASE / 'inputs' / NATIVE
    prior = json.loads((frozen / 'summary.json').read_text())
    review = json.loads((frozen / 'review.json').read_text())
    need(prior['status'] == 'completed_single_change_diagnostic' and review['status'] == 'passed' and
         review['summary_sha256'] == sha(frozen / 'summary.json'), 'B review binding differs')
    identity_rows = read(frozen / 'identified_ray.csv')
    need(len(identity_rows) == 1, 'Native identity not unique')
    identity = identity_rows[0]
    need(identity == s['native_context'] == prior['native_context'], 'Native context differs')
    sidecar = json.loads((frozen / 'paths.csv.identifiers.json').read_text())
    need(sidecar['native_context'] == identity and
         sidecar['context_sha256'] == sha(frozen / 'identified_ray.csv') and
         sidecar['file_sha256'] == sha(frozen / 'paths.csv'), 'Native sidecar differs')
    for name in ('paths.csv', 'paths.csv.identifiers.json', 'identified_ray.csv'):
        need(sha(frozen / name) == prior['output_sha256'][name], 'B artifact differs')
    need(identity['observation_index'] == '3426' and identity['event'] == '65' and
         identity['station'] == '46' and identity['receiver_location_code'] == '', 'Native indices differ')
    rows = [r for r in read(frozen / 'paths.csv') if r['run_id'] == s['native_run_id']]
    need(len(rows) == 1134 and [int(r['node']) for r in rows] == list(range(1134)) and
         all(r['observation_index'] == '3426' for r in rows), 'Native path order differs')
    need(rows[483:487] == s['original_nodes'], 'Saved local path context differs')
    matches = [r for r in prior['results'] if r['run_id'] == s['native_run_id']]
    need(matches == [s['original_B_result']] and matches[0]['converged'] == '0' and
         matches[0]['updates'] == '1000', 'B result or false flag changed')
    base = [tuple(Q(float(r[k])) for k in 'xyz') for r in rows]
    for prefix, point in (('native_source_', base[0]), ('native_receiver_', base[-1])):
        need(tuple(Q(float(identity[prefix+k])) for k in 'xyz') == point,
             'Endpoint differs from native geometry')
    grid_path = frozen / 'inputs/initial_grid.csv'
    need(sha(grid_path) == prior['prepared_file_sha256']['inputs/initial_grid.csv'], 'Grid pin differs')
    grid = read(grid_path)
    axes = [sorted({Q(float(r[k])) for r in grid}) for k in 'xyz']
    points = [tuple(Q(float(r[k])) for k in 'xyz') for r in grid]
    need(len(points) == len(set(points)) and set(points) == set(itertools.product(*axes)),
         'Grid is not a complete unique Cartesian product')
    profile = sorted({(Q(float(r['z'])), Q(float(r['v']))) for r in grid})
    need(len(profile) == len(axes[2]) and all(v > 0 for z, v in profile) and
         [[str(q) for q in p] for p in profile] == s['depth_profile_rational'], 'Depth profile differs')
    need(base[484][2] < 7 < base[485][2], 'Terminal nodes do not straddle z=7')
    arithmetic = load('review_interface_arithmetic', 'diagnostics/check_native_interface_support.py')
    sqrt = load('review_interface_sqrt', 'diagnostics/first_arrival_1d_precise_turn_reference.py').candidate_sqrt_enclosure
    difference = load('review_interface_difference', 'diagnostics/check_loma_failed_trials.py')
    need(difference.permute((Q(2), Q(3), Q(5))) == (5, 2, 3), 'Depth permutation differs')
    probes = []
    need([p['nodes_changed'] for p in s['probes']] == [[484], [485], [484, 485]], 'Probe roster differs')
    for saved in s['probes']:
        nodes = saved['nodes_changed']
        trial = [list(p) for p in base]
        for n in nodes:
            trial[n][2] = Q(7)
        trial = [tuple(p) for p in trial]
        need(all(axes[k][0] <= p[k] <= axes[k][-1] for p in trial for k in range(3)), 'Candidate outside box')
        need(trial[0] == base[0] and trial[-1] == base[-1], 'Candidate endpoint moved')
        need(saved['all_other_coordinates_unchanged'] is True and saved['replacement_z_rational'] == '7' and
             saved['actual_z_displacements_rational'] == {str(n): str(Q(7)-base[n][2]) for n in nodes},
             'Candidate displacement differs')
        changed = [i for i in range(len(base)-1) if (base[i], base[i+1]) != (trial[i], trial[i+1])]
        need(changed == sorted(set(i for n in nodes for i in (n-1, n))) and
             len(changed) == saved['changed_edges'], 'Changed-edge inventory differs')
        bound, count = difference.action_difference(arithmetic, sqrt, profile, base, trial, {})
        need(difference.interval(bound) == saved['action_change_s'] and count == len(changed),
             'Rational enclosure readback differs')
        sign = 'decrease' if bound[1] < 0 else 'increase' if bound[0] > 0 else 'unresolved'
        need(sign == saved['sign'], 'Sign classification differs')
        independent = []
        need([x['precision'] for x in saved['decimal_consistency']] == [80, 120], 'Decimal precisions differ')
        for precision, recorded in zip((80, 120), saved['decimal_consistency']):
            with localcontext() as context:
                context.prec = precision
                value = sum((decimal_segment(profile, trial[i], trial[i+1]) -
                             decimal_segment(profile, base[i], base[i+1]) for i in changed), Decimal(0))
                need(d(bound[0]) <= value <= d(bound[1]), 'Independent xyz Decimal action outside enclosure')
                need(d(bound[0]) <= Decimal(recorded['action_change_s']) <= d(bound[1]),
                     'Saved Decimal action outside enclosure')
                independent.append(dict(precision=precision, action_change_s=str(value)))
        probes.append(dict(nodes_changed=nodes, changed_edge_indices=changed,
                           unchanged_edges_cancelled=len(base)-1-len(changed), sign=sign,
                           rational_enclosure_exactly_reproduced=True,
                           independent_original_xyz_decimal=independent,
                           action_change_s=saved['action_change_s']))
    old_path = ROOT / 'data/development/loma_interface_candidates_001/summary.json'
    old = json.loads(old_path.read_text())
    comparison_keys = ('checks', 'native_context', 'original_B_result', 'native_run_id',
                       'original_nodes', 'depth_profile_rational', 'probes', 'limitations')
    need(all(old[k] == s[k] for k in comparison_keys), '001/002 scientific records differ')
    pins[str(old_path.relative_to(ROOT))] = sha(old_path)
    for name, digest in pins.items():
        need(sha(ROOT / name) == digest, 'Consumed file changed during review: ' + name)
    result = dict(status='passed', summary_sha256=EXPECTED, reviewer='earthscope_discovery',
                  source_sha256={k: v for k, v in s['input_sha256'].items() if k.startswith('diagnostics/')},
                  checker_sha256=sha(Path(__file__).resolve()), input_sha256=pins,
                  original_input_count=len(s['input_sha256']), original_artifact_count=len(s['artifact_sha256']),
                  recorded_invented_checks=13, native_metadata_fields=len(identity), native_context=identity,
                  original_B_false_flag_preserved=True, selected_path_nodes=len(base),
                  all_grid_cells_and_native_joins_verified=True, variant001_scientific_records_identical=True,
                  probes=probes, material_issue_found=False,
                  findings=['The two decreasing candidates and one increasing candidate retain their exact rational signs.',
                            'All unchanged edges cancel identically; only the two or three listed edges are evaluated.',
                            'Independent t-parameter integration uses the original xyz depth coordinate, checking the z permutation.',
                            'The 13 homogeneous controls alone cannot distinguish a mistaken depth-axis permutation.',
                            'The aligned-edge helper gradient is not consumed as an ordinary derivative.'],
                  scope=['Read-only saved-polygon arithmetic and identity audit; no tracing, optimizer or inversion.',
                         'Rational enclosures reuse the previously reviewed helpers; Decimal calculations are independent consistency checks, not new interval proofs.',
                         'No new stationarity, convergence, moment feasibility, full support bound or production correction is established.'])
    payload = json.dumps(result, indent=2, allow_nan=False) + '\n'
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('x') as stream:
        stream.write(payload)
    if args.attach:
        with attached.open('x') as stream:
            stream.write(payload)
    print(json.dumps(dict(status=result['status'], summary_sha256=EXPECTED,
                          review_sha256=sha(target), input_pins=len(pins), probes=len(probes))))


if __name__ == '__main__':
    main()
