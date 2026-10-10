#!/usr/bin/env python3
"""Enclose saved B-polygon action changes for three explicit feasible probes."""
import argparse
import csv
from decimal import localcontext
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / 'data/development/loma_outer_accumulation_native_001'
sys.dont_write_bytecode = True


def need(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    out = (ROOT / args.output).resolve()
    out.relative_to(ROOT)
    need(not out.exists(), 'Require a fresh diagnostic directory')
    helpers = ['diagnostics/check_native_interface_support.py',
               'diagnostics/first_arrival_1d_precise_turn_reference.py',
               'diagnostics/check_loma_failed_trials.py']
    files = [Path(__file__).resolve()] + [ROOT / p for p in helpers]
    files += [NATIVE / name for name in ('summary.json', 'review.json', 'paths.csv',
              'paths.csv.identifiers.json', 'identified_ray.csv', 'inputs/initial_grid.csv')]
    pins = {str(p.relative_to(ROOT)): sha(p) for p in files}
    out.mkdir(parents=True)
    for source in files:
        target = out / 'inputs' / source.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(str(source), str(target))
        need(sha(target) == pins[str(source.relative_to(ROOT))], 'Input changed while copying')
    arithmetic = load_module('interface_candidate_arithmetic', out / 'inputs' / helpers[0])
    square_root = load_module('interface_candidate_sqrt', out / 'inputs' / helpers[1]).candidate_sqrt_enclosure
    difference = load_module('interface_candidate_difference', out / 'inputs' / helpers[2])
    checks = []

    def check(name, value):
        checks.append(dict(name=name, passed=bool(value)))
        need(value, name)

    def action_change(profile, base, trial):
        base, trial = [list(map(tuple, points)) for points in (base, trial)]
        bound, edges = difference.action_difference(arithmetic, square_root, profile, base, trial, {})
        decimals = []
        for precision in (80, 120):
            with localcontext() as context:
                context.prec = precision
                total = arithmetic.decimal_value(Q(0))
                for a, b, c, d in zip(base, base[1:], trial, trial[1:]):
                    if a != c or b != d:
                        total += arithmetic.decimal_action(profile, difference.permute(c), difference.permute(d))
                        total -= arithmetic.decimal_action(profile, difference.permute(a), difference.permute(b))
                need(arithmetic.decimal_value(bound[0]) <= total <= arithmetic.decimal_value(bound[1]),
                     'Independent Decimal action lies outside the rational enclosure')
                decimals.append(dict(precision=precision, action_change_s=str(total)))
        return dict(action_change_s=difference.interval(bound), changed_edges=edges,
                    sign='decrease' if bound[1] < 0 else 'increase' if bound[0] > 0 else 'unresolved',
                    decimal_consistency=decimals)

    # Invented homogeneous controls check identity, coordinate permutation,
    # each one-node change, both changes, and endpoint reversal.
    profile = [(Q(-2), Q(5)), (Q(0), Q(5)), (Q(2), Q(5))]
    base = [(Q(0), Q(0), Q(0)), (Q(1), Q(0), Q(1, 10)),
            (Q(2), Q(0), Q(-1, 10)), (Q(3), Q(0), Q(0))]
    identity = action_change(profile, base, base)
    check('unchanged_polygon_cancels_exactly', identity['action_change_s']['lower_rational'] == '0' and
          identity['action_change_s']['upper_rational'] == '0' and identity['changed_edges'] == 0)
    for nodes in ((1,), (2,), (1, 2)):
        trial = [list(p) for p in base]
        for node in nodes:
            trial[node][2] = Q(0)
        result = action_change(profile, base, trial)
        reversed_result = action_change(profile, list(reversed(base)), list(reversed(trial)))
        check('invented_decrease_' + str(nodes), result['sign'] == 'decrease')
        check('invented_reversal_' + str(nodes), result['action_change_s'] == reversed_result['action_change_s'])
        check('invented_changed_edge_count_' + str(nodes), result['changed_edges'] == (3 if len(nodes) == 2 else 2))
        with localcontext() as context:
            context.prec = 120
            d = arithmetic.decimal_value
            old = (2 * d(Q(101, 100)).sqrt() + d(Q(26, 25)).sqrt()) / 5
            new = d(Q(3, 5)) if len(nodes) == 2 else (1 + 2 * d(Q(101, 100)).sqrt()) / 5
            interval = result['action_change_s']
            check('invented_closed_form_' + str(nodes),
                  d(Q(interval['lower_rational'])) <= new - old <= d(Q(interval['upper_rational'])))

    frozen = out / 'inputs' / NATIVE.relative_to(ROOT)
    summary = json.loads((frozen / 'summary.json').read_text())
    review = json.loads((frozen / 'review.json').read_text())
    need(summary['status'] == 'completed_single_change_diagnostic' and review['status'] == 'passed' and
         review['summary_sha256'] == sha(frozen / 'summary.json'), 'Require the reviewed terminal B run')
    for name in ('paths.csv', 'paths.csv.identifiers.json', 'identified_ray.csv'):
        need(sha(frozen / name) == summary['output_sha256'][name], 'Native artifact hash mismatch: ' + name)
    identity = read(frozen / 'identified_ray.csv')
    need(identity == [summary['native_context']], 'Native context mismatch')
    identity = identity[0]
    sidecar = json.loads((frozen / 'paths.csv.identifiers.json').read_text())
    need(sidecar['native_context'] == identity and sidecar['file_sha256'] == sha(frozen / 'paths.csv') and
         sidecar['context_sha256'] == sha(frozen / 'identified_ray.csv'), 'Native sidecar mismatch')
    run = 'fmm_0.031250_1000'
    path = [r for r in read(frozen / 'paths.csv') if r['run_id'] == run]
    need(len(path) == 1134 and [int(r['node']) for r in path] == list(range(1134)) and
         all(r['observation_index'] == '3426' for r in path), 'Native path join mismatch')
    original_result = next(r for r in summary['results'] if r['run_id'] == run)
    need(original_result['converged'] == '0' and original_result['updates'] == '1000', 'Original B flag changed')
    grid = read(frozen / 'inputs/initial_grid.csv')
    need(sha(frozen / 'inputs/initial_grid.csv') == summary['prepared_file_sha256']['inputs/initial_grid.csv'],
         'Initial grid hash mismatch')
    axes = [sorted(set(Q(float(r[a])) for r in grid)) for a in 'xyz']
    profile = sorted(set((Q(float(r['z'])), Q(float(r['v']))) for r in grid))
    need(len(profile) == len(axes[2]) and len(grid) == len(axes[0]) * len(axes[1]) * len(axes[2]) and
         len({tuple(r[a] for a in 'xyz') for r in grid}) == len(grid), 'Grid is not complete and depth-only')
    need(all(v > 0 for z, v in profile) and Q(7) in axes[2], 'Invalid profile/interface')
    base = [tuple(Q(float(r[a])) for a in 'xyz') for r in path]
    need(base[484][2] < 7 < base[485][2] and
         max(abs(base[i][2] - 7) for i in (484, 485)) < Q(1, 10**10), 'Unexpected terminal interface geometry')
    probes = []
    for nodes in ((484,), (485,), (484, 485)):
        trial = [list(p) for p in base]
        for node in nodes:
            trial[node][2] = Q(7)
        need(tuple(trial[0]) == base[0] and tuple(trial[-1]) == base[-1] and
             all(axes[k][0] <= p[k] <= axes[k][-1] for p in trial for k in range(3)), 'Infeasible probe')
        result = action_change(profile, base, trial)
        result.update(nodes_changed=list(nodes), replacement_z_rational='7', all_other_coordinates_unchanged=True,
                      actual_z_displacements_rational={str(n): str(Q(7) - base[n][2]) for n in nodes})
        probes.append(result)
    result = dict(status='completed_saved_action_probes', checks=checks, native_context=identity,
                  original_B_result=original_result, native_run_id=run,
                  original_nodes=path[483:487], depth_profile_rational=[[str(x) for x in p] for p in profile],
                  probes=probes, input_sha256=pins,
                  limitations=['These are explicit feasible diagnostic candidates, not original accepted optimizer steps.',
                               'The original terminal polygon and false flag remain unchanged; no ray was optimized.',
                               'Only action is assessed. At an aligned kink, the helper support vector is not used as an ordinary gradient.',
                               'A lower action does not establish local or generalized stationarity, a corrected stopping test, or inversion readiness.',
                               'Decimal readback checks consistency of the action enclosures; it is not an additional interval proof.'],
                  finished_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
    for name, digest in pins.items():
        need(sha(ROOT / name) == digest, 'Input changed during calculation')
    result['artifact_sha256'] = {str(p.relative_to(out)): sha(p) for p in sorted(out.rglob('*')) if p.is_file()}
    (out / 'summary.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps(dict(checks=len(checks), probes=probes), indent=2))


if __name__ == '__main__':
    main()
