#!/usr/bin/env python3
"""Read back saved accumulation results; never evaluates a segment or ray."""
from collections import Counter
import csv
from decimal import Decimal, localcontext
from fractions import Fraction as Q
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'data/development/loma_trial_accumulation_001'
REPLAY = ROOT / 'data/development/loma_failed_search_3426_001'
EXACT = ROOT / 'data/development/loma_failed_trial_exact_001'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text())


def rows(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def need(ok, message):
    if not ok:
        raise ValueError(message)


def main():
    result = load(OUT / 'summary.json')
    neutral, exact = load(REPLAY / 'summary.json'), load(EXACT / 'summary.json')
    controls = load(OUT / 'controls_execution.json')
    anchor = sha(OUT / 'summary.json')
    need(result['status'] == 'completed_saved_path_arithmetic_comparison' and result['return_code'] == 0,
         'Not a completed arithmetic comparison')
    need(load(OUT / 'launcher_review.json')['launcher_sha256'] == sha(OUT / 'run_native.py') and
         load(OUT / 'controls_review.json')['controls_execution_sha256'] == sha(OUT / 'controls_execution.json'),
         'Stale source/controls review')

    def rehash():
        for name, value in result['input_sha256'].items():
            need(sha(ROOT / name) == sha(OUT / 'inputs' / name) == value, 'Changed input: ' + name)
        for name, value in result['artifact_sha256'].items():
            need(sha(OUT / name) == value, 'Changed output: ' + name)
        for name, value in controls['source_sha256'].items():
            need(sha(ROOT / name) == value, 'Changed kernel source: ' + name)
        need(sha(ROOT / result['command'][0]) == result['binary_sha256'] == controls['binary_sha256'],
             'Changed tested binary')
        need(sha(OUT / 'summary.json') == anchor, 'Summary changed during review')

    rehash()
    for directory in (REPLAY, EXACT):
        r = load(directory / 'review.json')
        need(r['status'] == 'passed_saved_evidence_review' and r['summary_sha256'] == sha(directory / 'summary.json'),
             'Stale prior review')
    context = neutral['native_context']
    need(context == exact['native_context'] == result['native_context'] and
         rows(REPLAY / 'identified_ray.csv') == [context] and result['original_local_flag'] == '0', 'Native context differs')
    totals, segments = rows(OUT / 'totals.csv'), rows(OUT / 'segments.csv')
    decisions = rows(REPLAY / 'failed_search_decisions.csv')
    base_nodes = rows(REPLAY / 'failed_search_directions.csv')
    trial_nodes = rows(REPLAY / 'failed_search_trials.csv')
    need(len(totals) == 25 and len(segments) == 25*1133 and
         len(decisions) == len(exact['trials']) == len(result['comparisons']) == 24, 'Incomplete support')
    for name in ('totals.csv', 'segments.csv'):
        side = load(OUT / (name + '.identifiers.json'))
        need(side['file'] == name and side['file_sha256'] == sha(OUT / name) and
             side['native_context'] == context and side['source_replay_summary_sha256'] == sha(REPLAY / 'summary.json') and
             side['join_keys'] == ['run_id', 'observation_index'], 'Native sidecar differs')
    groups = {}
    for row in segments:
        need(row['run_id'] == 'fmm_0.031250_1000' and row['observation_index'] == '3426', 'Segment identity differs')
        key = int(row['trial_index'])
        group = groups.setdefault(key, [])
        need(int(row['edge']) == len(group), 'Unordered/duplicate edge')
        group.append(row)
    need(set(groups) == set(range(-1, 24)) and all(len(g) == 1133 for g in groups.values()), 'Incomplete segment groups')
    xyz = lambda row: tuple(float(row[a]) for a in 'xyz')
    base = [xyz(row) for row in base_nodes]
    native_sum = {}
    exact_double_sum = {}
    for index, total in zip(range(-1, 24), totals):
        need(int(total['trial_index']) == index and total['run_id'] == 'fmm_0.031250_1000' and
             total['observation_index'] == '3426' and total['double_mantissa_bits'] == '53' and
             total['extended_mantissa_bits'] == '64', 'Total identity/declared precision differs')
        curve = base if index == -1 else [xyz(row) for row in trial_nodes[index*1134:(index+1)*1134]]
        subtotal, rational, changed = 0., Q(0), 0
        for edge, row in enumerate(groups[index]):
            value = float(row['original_segment_s'])
            subtotal += value
            rational += Q(value)
            unchanged = curve[edge:edge+2] == base[edge:edge+2]
            need(row['unchanged_edge'] == str(int(unchanged)), 'Changed-edge flag differs from actual coordinates')
            changed += not unchanged
            if unchanged:
                need(row['original_segment_s'] == groups[-1][edge]['original_segment_s'] and
                     row['extended_segment_s'] == groups[-1][edge]['extended_segment_s'], 'Unchanged edge action differs')
        need(subtotal == float(total['original_total_s']) and changed == int(total['changed_edges']),
             'Original sequential accumulation or changed count differs')
        native_sum[index], exact_double_sum[index] = subtotal, rational
    need(native_sum[-1] == float(decisions[0]['cached_base_action_s']), 'Original cached base differs')
    counts = Counter()
    with localcontext() as ctx:
        ctx.prec = 80
        for i, (record, decision, bound, total) in enumerate(zip(result['comparisons'], decisions, exact['trials'], totals[1:])):
            need(record['trial_index'] == i == int(decision['trial_index']) and record['step'] == decision['step'] and
                 record['exact_action_change_s'] == bound['exact_action_change_s'] and
                 record['exact_armijo_classification'] == bound['exact_saved_slope_armijo'] == 'certified_pass' and
                 native_sum[i] == float(decision['trial_action_s']), 'Comparison/exact/original join differs')
            lo, hi = (Q(bound['exact_action_change_s'][k]) for k in ('lower_rational', 'upper_rational'))
            target = Q(bound['exact_saved_slope_armijo_target_s']['lower_rational'])
            need(target == Q(bound['exact_saved_slope_armijo_target_s']['upper_rational']), 'Expected a point target')
            values = {
                'original_total_difference_s': Q(native_sum[i])-Q(native_sum[-1]),
                'exact_sum_of_original_segment_changes_s': exact_double_sum[i]-exact_double_sum[-1],
                'extended_sum_of_original_totals_difference_s': Decimal(total['extended_sum_original_segments_s'])-Decimal(totals[0]['extended_sum_original_segments_s']),
                'paired_original_segment_change_s': Decimal(total['paired_original_segment_change_s']),
                'extended_total_difference_s': Decimal(total['extended_total_s'])-Decimal(totals[0]['extended_total_s']),
                'paired_extended_segment_change_s': Decimal(total['paired_extended_segment_change_s'])}
            need(set(values) == set(record['methods']), 'Method inventory differs')
            for name, value in values.items():
                displayed = str(value) if isinstance(value, Decimal) else str(Decimal(value.numerator)/Decimal(value.denominator))
                check = record['methods'][name]
                need(check['value_decimal'] == displayed and check['value_display'] == float(value) and
                     check['minus_exact_change_lower_display'] == float(Q(value)-hi) and
                     check['minus_exact_change_upper_display'] == float(Q(value)-lo) and
                     check['approximate_armijo_pass'] == (Q(value) <= target), 'Method accounting differs: ' + name)
                counts[name] += check['approximate_armijo_pass']
    rehash()
    review = dict(status='passed_saved_evidence_review', summary_sha256=anchor, reviewer='scientific_audit',
                  checker_path=str(Path(__file__).resolve().relative_to(ROOT)), checker_sha256=sha(Path(__file__)),
                  scope='Independent native/hash/output accounting and summation readback; no segment evaluation or ray rerun.',
                  input_hashes_verified=len(result['input_sha256']), artifact_hashes_verified=len(result['artifact_sha256']),
                  kernel_source_hashes_verified=len(controls['source_sha256']), trials=24, segment_records=len(segments),
                  native_context=context, original_local_flag='0', all_prior_review_and_sidecar_joins_passed=True,
                  original_binary64_sequential_totals_reconstructed=True, exact_sum_original_segments_reconstructed=True,
                  every_reported_comparison_and_error_display_reconstructed=True, approximate_pass_counts=dict(counts),
                  findings=['The original outer accumulation rejects all24 saved trials; exact summation of its same segment values recovers17, including the first.',
                            'Paired extended segment changes recover21 of24; this remains approximate arithmetic and misses the smallest three true decreases.'],
                  limitations=['The frozen C++ component establishes original/template segment equality in process; this review checks its reviewed source/binary and saved output rather than rerunning it.',
                               'Printed extended totals include decimal display rounding. Neither their differences nor paired extended changes are exact action certificates.',
                               'No optimizer, convergence criterion, update budget, production source or original failure flag changed.'])
    with (OUT / 'review.json').open('x') as stream:
        json.dump(review, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps(dict(status=review['status'], review_sha256=sha(OUT / 'review.json'), counts=dict(counts)), indent=2))


if __name__ == '__main__':
    main()
