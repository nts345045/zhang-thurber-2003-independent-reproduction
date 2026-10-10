#!/usr/bin/env python3
"""Plot reviewed static candidate actions and supporting-vector norm bounds."""
import argparse
from fractions import Fraction as Q
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.environ.setdefault('MPLCONFIGDIR', str(ROOT / 'tmp/matplotlib'))
CANDIDATE = ROOT / 'data/development/loma_interface_candidates_002'
SUPPORT = ROOT / 'data/development/loma_candidate_support_001'
EXPECTED_CANDIDATE = '7bdbabbbd09f4edae34a7f9cae168f892fef11b64479997b38e0d361d66472b4'
EXPECTED_SUPPORT = '29f874fe30419411ab31a154d32ded2e17f4aa7a3536247c3c9aa85174eb35d0'


def need(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bounds(value):
    lo, hi = (Q(value[k]) for k in ('lower_rational', 'upper_rational'))
    need(lo <= hi, 'Reversed plotted interval')
    return lo, hi


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--support-review', required=True)
    parser.add_argument('--support-review-sha256', required=True)
    args = parser.parse_args()
    review_path = (ROOT / args.support_review).resolve()
    review_path.relative_to(ROOT)
    need(sha(review_path) == args.support_review_sha256, 'Independent support review hash differs')
    candidate = json.loads((CANDIDATE / 'summary.json').read_text())
    support = json.loads((SUPPORT / 'summary.json').read_text())
    candidate_review = json.loads((CANDIDATE / 'review.json').read_text())
    support_review = json.loads(review_path.read_text())
    need(sha(CANDIDATE / 'summary.json') == EXPECTED_CANDIDATE and
         sha(SUPPORT / 'summary.json') == EXPECTED_SUPPORT, 'Selected scientific summary changed')
    need(candidate['status'] == 'completed_saved_action_probes' and
         support['status'] == 'completed_prescribed_polygon_support_existence' and
         candidate_review['status'] == support_review['status'] == 'passed' and
         candidate_review['summary_sha256'] == EXPECTED_CANDIDATE and
         support_review['summary_sha256'] == EXPECTED_SUPPORT, 'Require both completed independent reviews')
    need(support_review['positive_edges'] == 1133 and support_review['internal_components'] == 3396 and
         support_review['certified_normal_zero_components'] == [[484, 'z'], [485, 'z']] and
         [r['precision'] for r in support_review['decimal_readbacks']] == [80, 120],
         'Full independent component readback missing')
    need(candidate['native_context'] == support['native_context'] == candidate_review['native_context'] and
         candidate['original_B_result'] == support['original_B_result'], 'Native contexts or original results differ')
    need(support['selected_candidate_nodes'] == [484, 485] and
         support['candidate_summary_sha256'] == EXPECTED_CANDIDATE and
         support['candidate_review_sha256'] == sha(CANDIDATE / 'review.json') and
         support['ray_solves'] == support['optimizer_steps'] == 0, 'Wrong prescribed support polygon')
    pins = {}
    for folder, summary in ((CANDIDATE, candidate), (SUPPORT, support)):
        for name in ('summary.json', 'review.json'):
            path = folder / name
            pins[str(path.relative_to(ROOT))] = sha(path)
        for name, digest in summary['input_sha256'].items():
            need(sha(ROOT / name) == digest, 'Changed input: ' + name)
            pins[name] = digest
        for name, digest in summary['artifact_sha256'].items():
            path = folder / name
            need(sha(path) == digest, 'Changed frozen artifact: ' + name)
            pins[str(path.relative_to(ROOT))] = digest
    need(sha(SUPPORT / 'review.json') == args.support_review_sha256, 'Attached support review differs')
    pins[str(review_path.relative_to(ROOT))] = args.support_review_sha256
    source_path = Path(__file__).resolve()
    pins[str(source_path.relative_to(ROOT))] = sha(source_path)
    probes = candidate['probes']
    need([p['nodes_changed'] for p in probes] == [[484], [485], [484, 485]] and
         [p['sign'] for p in probes] == ['decrease', 'increase', 'decrease'] and
         support['action_change_s'] == probes[2]['action_change_s'], 'Candidate action roster changed')
    actions = []
    for probe in probes:
        lo, hi = bounds(probe['action_change_s'])
        actions.append(dict(nodes_changed=probe['nodes_changed'], interval_s=probe['action_change_s'],
                            sign=probe['sign'], plotted_midpoint_1e_minus16_s=float((lo+hi)/2 * 10**16)))
    norms = []
    for label, key in (('Lower-side support', 'alpha0_internal_norm_s_per_km'),
                       ('Support existence with certified cancellation', 'support_internal_norm_s_per_km')):
        lo, hi = bounds(support[key])
        need(lo > 0, 'Nonpositive norm bound')
        norms.append(dict(label=label, interval_s_per_km=support[key],
                          plotted_midpoint_microseconds_per_km=float((lo+hi)/2 * 10**6)))
    out = ROOT / 'figures/diagnostics'
    out.mkdir(parents=True, exist_ok=True)
    names = ['loma_interface_candidate.' + suffix for suffix in ('pdf', 'png', 'json')]

    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(9.4, 4.7))
    fig.subplots_adjust(left=0.085, right=0.985, bottom=0.27, top=0.75, wspace=0.38)
    fig.suptitle('LOM ray 3426: prescribed modified polygons', fontsize=13, y=0.975)
    fig.text(0.5, 0.91, 'NC10090782  |  NC.JSJ..EHZ  |  static diagnostic', ha='center', fontsize=9)
    values = [r['plotted_midpoint_1e_minus16_s'] for r in actions]
    axes[0].bar(range(3), values, color=['#25658c', '#b24c35', '#25658c'], width=0.62, zorder=3)
    axes[0].axhline(0, color='0.4', linewidth=0.8, zorder=2)
    for n, value in enumerate(values):
        axes[0].annotate('{:+.4f}'.format(value), (n, value), xytext=(0, 5 if value > 0 else -5),
                         textcoords='offset points', ha='center', va='bottom' if value > 0 else 'top', fontsize=9)
    axes[0].set_xticks(range(3))
    axes[0].set_xticklabels(['484 only', '485 only', '484 + 485'], fontsize=9)
    axes[0].set_ylim(-2.7, 0.95)
    axes[0].set_ylabel(r'Action change ($10^{-16}$ s)')
    axes[0].set_xlabel('Vertices placed exactly at z = 7 km', fontsize=9)
    axes[0].set_title('A  Explicit coordinate replacements', loc='left', fontsize=10, pad=12)
    values = [r['plotted_midpoint_microseconds_per_km'] for r in norms]
    axes[1].bar(range(2), values, color=['#747d83', '#267e70'], width=0.55, zorder=3)
    for n, value in enumerate(values):
        axes[1].annotate('{:.4f}'.format(value), (n, value), xytext=(0, 5), textcoords='offset points',
                         ha='center', va='bottom', fontsize=9)
    axes[1].set_xticks(range(2))
    axes[1].set_xticklabels(['Lower-side\nsupport', 'Certified support\nexistence'], fontsize=9)
    axes[1].set_ylim(0, 82)
    axes[1].set_ylabel(r'Support norm ($\mu$s/km)')
    axes[1].set_xlabel('Both-vertices candidate only', fontsize=9)
    axes[1].set_title('B  Supporting vectors, not ordinary gradients', loc='left', fontsize=9.5, pad=12)
    for axis in axes:
        axis.grid(axis='y', alpha=0.18, zorder=0)
        axis.spines['top'].set_visible(False)
        axis.spines['right'].set_visible(False)
    fig.text(0.5, 0.07, 'Exact interval widths are below symbol size. Fixed polygon topology; no optimizer step or convergence claim.',
             ha='center', fontsize=8)
    for suffix in ('pdf', 'png'):
        fig.savefig(str(out / ('loma_interface_candidate.' + suffix)), dpi=180)
    plt.close(fig)
    for name, digest in pins.items():
        need(sha(ROOT / name) == digest, 'Input changed during plotting: ' + name)
    metadata = dict(input_sha256=pins, plot_source_sha256=sha(source_path),
                    independent_support_review_sha256=args.support_review_sha256,
                    native_context=candidate['native_context'], actions=actions,
                    same_candidate_support_norms=norms, candidate_nodes=[484, 485],
                    exact_zero_components_by_existence=support['exact_zero_components_by_existence'],
                    interval_display='Bars use rational-interval midpoints; true widths are below symbol size and are not enlarged.',
                    units=dict(panel_A='1e-16 seconds', panel_B='microseconds per kilometre'),
                    limitations=['Prescribed modified polygons; original B result is unchanged.',
                                 'Supporting-vector norms, not ordinary gradients or a computed minimum dual norm.',
                                 'No optimizer steps, thresholds, convergence promotion or production adoption.'],
                    figure_sha256={name: sha(out / name) for name in names[:2]})
    (out / names[2]).write_text(json.dumps(metadata, indent=2, allow_nan=False) + '\n')
    print(json.dumps(dict(figures=metadata['figure_sha256'], metadata_sha256=sha(out / names[2])), indent=2))


if __name__ == '__main__':
    main()
