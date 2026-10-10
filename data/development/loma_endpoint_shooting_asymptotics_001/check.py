#!/usr/bin/env python3
"""Read saved invented values only; no shooting, quadrature, or ray imports."""
import argparse
import collections
import csv
import hashlib
import json
import math
import sys
from decimal import Decimal, localcontext
from fractions import Fraction as Q
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ORIGINAL = ROOT / 'data/development/loma_endpoint_shooting_controls_001'
SUPPLEMENT = ROOT / 'data/development/loma_endpoint_shooting_baselines_001'
MESH = ROOT / 'data/development/loma_boundary_endpoint_mesh_controls_001'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def rational(value):
    return dict(numerator=str(value.numerator), denominator=str(value.denominator))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default=str(HERE / 'summary.json'))
    args = parser.parse_args()
    output = Path(args.output).resolve()
    require(not output.exists(), 'Output must be new')
    require(output.parent == HERE or (ROOT not in output.parents and output != ROOT),
            'Use this evidence directory or a fresh path outside the repository')
    pins = {}

    def pin(path, expected=None):
        actual = sha(path)
        require(expected is None or expected == actual, 'Hash mismatch: ' + str(path))
        pins[str(path.relative_to(ROOT))] = actual

    for directory, expected in [(ORIGINAL, '0ca944a3fa240721e62b193b7db6361604137d40f34bccabca8566ddf5e61945'),
                                (SUPPLEMENT, '616ff5cb6ff2e0150faf546802ea8ae4b7edd54074928f894af02552fa60fbd1')]:
        pin(directory / 'summary.json', expected)
        summary = read(directory / 'summary.json')
        for relative, digest in summary['input_sha256'].items():
            pin(ROOT / relative, digest)
        for relative, digest in summary['output_sha256'].items():
            pin(directory / relative, digest)
        review = read(directory / 'review.json')
        require(review['status'] == 'passed' and review['summary_sha256'] == expected,
                'Independent review does not match')
        pin(directory / 'review.json')
        require(read(directory / 'execution.json')['return_code'] == 0, 'Nonterminal input')
    pin(MESH / 'summary.json', '534fa492a55bb167f6b751efdb46642c235369a806d8e308d490cca6afac622c')
    mesh_summary = read(MESH / 'summary.json')
    for name in ['positive_guide/evaluations.csv', 'positive_guide/grid.csv']:
        pin(MESH / name, mesh_summary['artifact_sha256'][name])
    for path in [Path(__file__).resolve(), HERE / 'README.md']:
        pin(path)

    inputs = read(ORIGINAL / 'invented_inputs.json')
    require(inputs['settings']['normal_boundary_steps_km'] == [2. ** -20, 2. ** -24, 2. ** -28],
            'Unexpected original ladder')
    cases = {c['name']: c for c in inputs['cases']}
    affine_case = cases['scalar_regime_12']
    require(affine_case['gradient'] == 1. and affine_case['nodes'] == [5.] * 4 + [6.] * 4,
            'Affine coefficient must use the original model')
    baseline = {(r['setting'], r['case']): r['result']['selected']
                for r in read(ORIGINAL / 'baseline_results.json')}
    mixed_baseline = {(r['setting'], r['both_bottom']): r['result']['selected']
                      for r in read(SUPPLEMENT / 'baseline_candidates.json')}
    rows = [r for r in read(ORIGINAL / 'perturbations.json') if r.get('inward_one_sided')]
    require(len(rows) == 24, 'Boundary support changed')
    groups = collections.defaultdict(list)
    for row in rows:
        require(row['kind'] == 'endpoint' and row['axis'] == 2 and row['same_value_candidates'],
                'Wrong comparison kind')
        groups[(row['setting'], row['mixed'], row['both_bottom'], row['side'])].append(row)
    require(len(groups) == 8, 'Expected all eight ladders')
    ladders, extrapolates, affine_coefficient_checks, guide_checks = [], [], [], []
    with localcontext() as ctx:
        ctx.prec = 80
        coefficient = Decimal(2) / 3 * Decimal(2).sqrt() / (Decimal(6) * Decimal(6).sqrt())
        for key, group in sorted(groups.items()):
            setting, mixed, both_bottom, side = key
            group.sort(key=lambda r: r['h'], reverse=True)
            require([r['h'] for r in group] == [2. ** -20, 2. ** -24, 2. ** -28], 'Incomplete ladder')
            base = mixed_baseline[(setting, both_bottom)] if mixed else baseline[(setting, 'scalar_regime_12')]
            require(base['valid'] and base['durations'][1] > 0, 'Missing positive base guide')
            identity = dict(setting=setting, mixed=mixed, both_bottom=both_bottom, side=side,
                            geometry='invented', resource_ids=None)
            saved_rows = []
            for row in group:
                selected = row['results'][0]['selected']
                require(selected['valid'] and selected['durations'][1] > 0, 'Missing perturbed guide')
                derivative = base['source' if side == 0 else 'receiver'][2]
                fd = (base['time'] - selected['time']) / row['h']
                require(fd == row['finite_difference_s_per_km'] and derivative == row['momentum_component'],
                        'Saved value/derivative join differs')
                require(fd - derivative == row['difference_s_per_km'], 'Saved difference differs')
                require(all(math.isfinite(x) for x in [fd, derivative, row['h']]), 'Nonfinite comparison')
                reactions = [p['minimum_reaction'] for p in selected['pieces']
                             if p.get('minimum_reaction') is not None]
                require(reactions and min(reactions) > 0, 'Nonpositive sampled reaction')
                guide_checks.append(dict(identity=identity, h=row['h'], topology=selected['topology'],
                    guide_duration_s=selected['durations'][1], sampled_minimum_reaction=min(reactions),
                    endpoint_residual_km=selected['maximum_endpoint_mismatch_km'],
                    invariant_residual=selected['maximum_invariant_error']))
                saved_rows.append(dict(h_km=row['h'], base_time_s=base['time'],
                    perturbed_time_s=selected['time'], finite_difference_s_per_km=fd,
                    limiting_branch_momentum_s_per_km=derivative,
                    difference_s_per_km=row['difference_s_per_km'],
                    raw_within_existing_limit=abs(row['difference_s_per_km']) <= 3e-6,
                    base_topology=base['topology'], perturbed_topology=selected['topology']))
                if not mixed:
                    h = Decimal.from_float(row['h'])
                    predicted = -coefficient * h.sqrt()
                    observed = Decimal.from_float(fd)
                    affine_coefficient_checks.append(dict(identity=identity, h_km=row['h'],
                        leading_prediction_s_per_km=str(predicted),
                        recorded_minus_leading_s_per_km=str(observed - predicted),
                        recorded_over_leading=str(observed / predicted),
                        meaning='Leading asymptotic term, not an exact finite-step oracle or enclosure'))
            ladders.append(dict(identity=identity, rows=saved_rows,
                raw_error_reduction_factors=[abs(a['difference_s_per_km'] / b['difference_s_per_km'])
                                            for a, b in zip(group, group[1:])]))
            for pair_index, (coarse, fine) in enumerate(zip(group, group[1:])):
                require(coarse['h'] == 16 * fine['h'], 'Incorrect step ratio')
                value = (4 * Q(fine['finite_difference_s_per_km']) - Q(coarse['finite_difference_s_per_km'])) / 3
                error = value - Q(fine['momentum_component'])
                extrapolates.append(dict(identity=identity, pair_index=pair_index,
                    coarse_h_km=coarse['h'], fine_h_km=fine['h'], exact_combination_q=rational(value),
                    extrapolated_s_per_km=float(value), difference_s_per_km=float(error),
                    comparison_with_existing_limit=abs(error) <= Q(3e-6),
                    interval_error_certificate=False))

    with (MESH / 'positive_guide/grid.csv').open() as stream:
        grid = list(csv.DictReader(stream))
    require(all(Q(r['v']) == 5 + Q(r['z']) for r in grid), 'Old polygon model differs')
    with (MESH / 'positive_guide/evaluations.csv').open() as stream:
        mesh_rows = [r for r in csv.DictReader(stream)
                     if r['family'] == 'optimized' and Q(r['epsilon_actual_km']) == 0]
    require([int(r['subsegments']) for r in mesh_rows] == [1, 2, 4, 8, 16], 'Mesh roster differs')
    old_polygon = []
    for row in mesh_rows:
        length = Q(1, 4 * int(row['subsegments']))
        slope = -length / 72
        require(Q(row['leading_length_km']) == length and int(row['iterations']) == 0,
                'Expected unchanged zero-update horizontal polygon')
        old_polygon.append(dict(subsegments=int(row['subsegments']), iterations=0,
            saved_converged=row['converged'], saved_source_dz=float(row['source_dz']),
            saved_projected_gradient=float(row['projected_gradient']),
            exact_fixed_other_knots_source_dz_q=rational(slope),
            exact_fixed_other_knots_source_dz_s_per_km=float(slope),
            continuous_guide_limiting_source_dz_s_per_km=0.))
    for relative, digest in pins.items():
        require(sha(ROOT / relative) == digest, 'Input changed while reading: ' + relative)
    maxima = [max(abs(r['difference_s_per_km']) for r in extrapolates if r['pair_index'] == i)
              for i in [0, 1]]
    summary = dict(status='completed_saved_output_consistency_check', source_sha256=sha(Path(__file__)),
        input_sha256=pins, scientific_acceptance_changed=False, numerical_solve_performed=False,
        action_reintegration_performed=False, native_execution_performed=False,
        ladder_count=len(ladders), raw_secant_count=len(rows), extrapolate_count=len(extrapolates),
        raw_existing_limit_failures=sum(abs(r['difference_s_per_km']) > 3e-6 for r in rows),
        extrapolates_within_existing_numeric_limit=sum(r['comparison_with_existing_limit'] for r in extrapolates),
        maximum_extrapolated_error_by_pair_s_per_km=maxima,
        fine_pair_maximum_error_exceeds_coarse_pair=maxima[1] > maxima[0],
        affine_coefficient=dict(g_km_per_s_per_km=1., bottom_velocity_km_per_s=6.,
            c_s_per_km_to_three_halves=str(coefficient), precision_digits=80,
            formula='(2/3)*sqrt(2*g)/v_b^(3/2)', checks=affine_coefficient_checks),
        ladders=ladders, extrapolates=extrapolates, saved_guide_eligibility=guide_checks,
        old_fixed_polygon_linear_term=old_polygon,
        limitations=['Exact fractions refer to saved binary64 secants, not exact travel times.',
            'All 24 raw finite-step failures remain failures; extrapolation does not overwrite them.',
            'Mixed-field expansion is conditional on a stable regular guide branch and positive reaction.',
            'No global branch enumeration, uniform numerical error bound, or error certificate is established.',
            'The finer extrapolate worsens; two ODE settings do not bound common root/roundoff errors.',
            'Fixed-knot polygon partial is correct for that polygon, but differs from continuous guide sensitivity.',
            'No optimizer, native path, production stopping flag, or model derivative is changed.'])
    with output.open('x') as stream:
        json.dump(summary, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
    print(json.dumps(dict(status=summary['status'], ladders=len(ladders), extrapolates=len(extrapolates),
        raw_failures=summary['raw_existing_limit_failures'], maximum_errors=maxima,
        summary_sha256=sha(output)), sort_keys=True))


if __name__ == '__main__':
    main()
