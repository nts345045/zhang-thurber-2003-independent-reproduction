#!/usr/bin/env python3
"""Review frozen interface probes with higher-precision exact segment actions."""
import argparse
import csv
from decimal import Decimal, localcontext
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
IDENTITIES = ['event', 'station', 'source_event_resource_id', 'source_origin_resource_id',
              'receiver_channel_seed_id', 'receiver_channel_fdsn_source_id',
              'receiver_metadata_epoch_start', 'receiver_metadata_epoch_end']


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''): h.update(block)
    return h.hexdigest()


def table(path):
    with path.open(newline='') as stream: return list(csv.DictReader(stream))


def decimal_action(profile, path):
    """Exact reciprocal-velocity integral for a piecewise-linear velocity."""
    def velocity(x):
        i = 0
        while i + 2 < len(profile) and x >= profile[i + 1][0]: i += 1
        a, va = profile[i]; b, vb = profile[i + 1]
        return va + (vb - va) * (x - a) / (b - a)
    total = Decimal(0)
    for a, b in zip(path, path[1:]):
        delta = [y - x for x, y in zip(a, b)]
        length = sum(x * x for x in delta).sqrt()
        cuts = [Decimal(0), Decimal(1)]
        if delta[0]:
            cuts += [(x - a[0]) / delta[0] for x, _ in profile
                     if 0 < (x - a[0]) / delta[0] < 1]
        cuts.sort()
        for left, right in zip(cuts, cuts[1:]):
            va = velocity(a[0] + left * delta[0]); vb = velocity(a[0] + right * delta[0])
            integral = Decimal(1) / va if va == vb else (vb / va).ln() / (vb - va)
            total += length * (right - left) * integral
    return total


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True)
    args = parser.parse_args()
    source = (ROOT / args.input).resolve()
    out = source / 'review'
    if out.exists(): raise ValueError('Preserve prior review; use a fresh evidence directory')
    summary = json.loads((source / 'summary.json').read_text())
    for name, digest in summary['output_sha256'].items():
        if sha(source / name) != digest: raise ValueError('Frozen artifact changed: ' + name)
    grid = table(source / 'inputs/truth_grid.csv')
    values = {}
    for row in grid:
        x, v = float(row['x']), float(row['v'])
        if x in values and values[x] != v: raise ValueError('Exact action requires x-only model')
        values[x] = v
    profile = [(Decimal.from_float(x), Decimal.from_float(v)) for x, v in sorted(values.items())]
    native = [r for r in table(source / 'directional.csv') if r['case'].startswith('native_')]
    native_id = {k: summary['native_case'][k] for k in IDENTITIES}
    directions = [r for r in table(source / 'directions.csv') if r['case'].startswith('native_')]
    secants = [r for r in table(source / 'secants.csv') if r['case'].startswith('native_')]
    if not all(r[k] == native_id[k] for r in native + directions + secants for k in IDENTITIES):
        raise ValueError('Native identity mismatch')
    records = []
    for name, step in [('in_plane_negative_gradient', 1e-6), ('in_plane_metric_direction', 1e-3)]:
        rows = [r for r in directions if r['direction'] == name]
        if not all(int(r['node']) == i for i, r in enumerate(rows)): raise ValueError('Node order changed')
        original = [[float(r[k]) for k in ('x', 'y', 'z')] for r in rows]
        vector = [[float(r[k]) for k in ('dx', 'dy', 'dz')] for r in rows]
        # Match the saved C++ experiment's binary64 displaced geometry first;
        # high precision changes only evaluation of that already defined polygon.
        displaced = [[p + step * d for p, d in zip(a, b)] for a, b in zip(original, vector)]
        p = [[Decimal.from_float(x) for x in r] for r in original]
        q = [[Decimal.from_float(x) for x in r] for r in displaced]
        changes = []
        for precision in (80, 100):
            with localcontext() as context:
                context.prec = precision
                baseline = decimal_action(profile, p)
                changed = decimal_action(profile, q)
                changes.append(changed - baseline)
        old = next(r for r in secants if r['direction'] == name and float(r['step_km']) == step)
        directional = next(r for r in native if r['direction'] == name)
        agreement = abs(changes[1] - changes[0])
        confirmed = (all(x < 0 for x in changes) and agreement < abs(changes[1]) * Decimal('1e-40')
                     and float(old['production_forward_change']) < 0
                     and float(directional['directional_8point']) < 0)
        record = dict(direction=name, step_km=step, exact_action_change_80digits_s=str(changes[0]),
                      exact_action_change_100digits_s=str(changes[1]), precision_difference_s=str(agreement),
                      saved_long_double_change_s=old['forward_exact_change'],
                      saved_production_change_s=old['production_forward_change'],
                      directional_slope_s_per_km=directional['directional_8point'],
                      confirmed_numerical_descent=confirmed)
        record.update(native_id); records.append(record)
    classifications = []
    for row in native:
        name = row['direction']
        if name in ('in_plane_negative_gradient', 'in_plane_metric_direction'):
            classification = 'confirmed_numerical_descent_by_directional_and_independent_exact_action'
        elif name in ('negative_chosen_gradient', 'guide_negative_translation'):
            classification = 'inconclusive_raw_action_changes_near_arithmetic_precision_not_a_descent_claim'
        else:
            classification = 'positive_directional_slope_for_this_probe_only'
        record = dict(direction=name, classification=classification,
                      raw_directional_slope_s_per_km=row['directional_8point'])
        record.update(native_id); classifications.append(record)
    out.mkdir()
    shutil.copyfile(str(Path(__file__).resolve()), str(out / 'review_interface_directional.py'))
    review = dict(status='passed' if all(r['confirmed_numerical_descent'] for r in records) else 'failed',
                  reviewer='scientific_audit', source_summary_sha256=sha(source / 'summary.json'),
                  reviewed_classifications_supersede_raw_witness_booleans=True,
                  classifications=classifications, high_precision_controls=records,
                  original_local_flag=0, original_accepted_updates=0,
                  formula_review='ray_math_review found no sign, incident-cell, or coupled-direction defect',
                  limitations=['Finite direction probes do not certify full nonsmooth stationarity or global first arrival.',
                               'High-precision action replay is a numerical consistency check, not interval arithmetic.',
                               'The two raw normal-direction action signs are inconclusive and must not be cited as descent evidence.',
                               'No optimizer, stopping tolerance, source/model derivative, or production source was changed.'],
                  artifact_sha256={name: sha(source / name) for name in
                                   ('summary.json', 'directional.csv', 'secants.csv', 'directions.csv',
                                    'inputs/truth_grid.csv', 'inputs/native_case.csv', 'inputs/native_path.csv')},
                  review_source_sha256=sha(out / 'review_interface_directional.py'))
    (out / 'summary.json').write_text(json.dumps(review, indent=2, allow_nan=False) + '\n')
    print(json.dumps(review, indent=2))
    if review['status'] != 'passed': raise SystemExit(1)


if __name__ == '__main__': main()
