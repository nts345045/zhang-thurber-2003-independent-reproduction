#!/usr/bin/env python3
"""Plot reviewed fixed-cutoff and positive-curvature saved histories."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.environ.setdefault('MPLCONFIGDIR', str(ROOT / 'tmp/matplotlib'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--positive-review-sha256', required=True)
    args = parser.parse_args()
    records, pins, contexts, straight = {}, {}, [], []
    variants = [
        ('Fixed cutoff', 'loma_seed_loaded_b_native_001', 'completed_seed_loaded_B_neutrality', '0',
         'c49e9ab30fca87597df9ac7a8f5f70536383e8c3be6d4b694e58d73ebdeb5155'),
        ('Positive curvature', 'loma_positive_curvature_native_001', 'completed_positive_curvature_diagnostic', '1',
         args.positive_review_sha256)]
    for label, name, status, flag, review_hash in variants:
        source = ROOT / 'data/development' / name
        summary = json.loads((source / 'summary.json').read_text())
        review = json.loads((source / 'review.json').read_text())
        if (summary['status'] != status or review['status'] != 'passed' or
                sha(source / 'review.json') != review_hash or
                review['summary_sha256'] != sha(source / 'summary.json')):
            raise ValueError('Require the completed independent review: ' + label)
        for filename in ('history.csv', 'results.csv'):
            if sha(source / filename) != summary['output_sha256'][filename]:
                raise ValueError('Changed saved table: ' + filename)
            sidecar = json.loads((source / (filename + '.identifiers.json')).read_text())
            if sidecar['file_sha256'] != sha(source / filename) or sidecar['native_context'] != summary['native_context']:
                raise ValueError('Changed native identity attachment')
        results = summary['results']
        values = [r for r in results if r['initialization'] == 'fmm']
        if len(values) != 1 or values[0]['converged'] != flag:
            raise ValueError('Changed diagnostic FMM flag')
        result = values[0]
        straight.append([r for r in results if r['initialization'] == 'straight'])
        with (source / 'history.csv').open(newline='') as stream:
            plotted = [r for r in csv.DictReader(stream)
                       if r['run_id'] == result['run_id'] and r['phase'] in ('initial', 'accepted')]
        updates = [int(r['updates']) for r in plotted]
        if updates != list(range(int(result['updates']) + 1)):
            raise ValueError('Incomplete accepted-update history')
        pairs, cumulative = 0, []
        for row in plotted:
            pairs += int(row['curvature_pair_accepted'])
            cumulative.append(pairs)
        records[label] = dict(updates=updates,
            projected_gradient_s_per_km=[float(r['projected_gradient']) for r in plotted],
            accepted_curvature_pairs=cumulative, result=result,
            accepted_equal_binary64_actions=sum(float(r['action_change_s']) == 0
                                                for r in plotted if r['phase'] == 'accepted'))
        contexts.append(summary['native_context'])
        for filename in ('summary.json', 'review.json', 'history.csv', 'results.csv',
                         'history.csv.identifiers.json', 'results.csv.identifiers.json'):
            pins[str((source / filename).relative_to(ROOT))] = sha(source / filename)
    if contexts[0] != contexts[1] or straight[0] != straight[1] or len(straight[0]) != 1:
        raise ValueError('Native context or straight-start parity changed')
    if [(len(r['updates']) - 1, r['accepted_curvature_pairs'][-1], r['accepted_equal_binary64_actions'])
            for r in records.values()] != [(1000, 40, 564), (145, 145, 72)]:
        raise ValueError('Saved outcome inventory changed')

    fig, axes = plt.subplots(2, 1, figsize=(7.2, 6), sharex=True,
                             constrained_layout=True, gridspec_kw={'height_ratios': [2, 1]})
    labels = ['Fixed cutoff ($s^T y > 10^{-14}$ s)',
              'Positive curvature ($s^T y > 0$): flag 1 at 145 updates']
    for (name, values), color, label in zip(records.items(), ('#1b6397', '#168477'), labels):
        axes[0].plot(values['updates'], values['projected_gradient_s_per_km'],
                     color=color, linewidth=1.2, label=label)
        axes[0].plot(values['updates'][-1], values['projected_gradient_s_per_km'][-1],
                     'o', color=color, markersize=4)
        axes[1].step(values['updates'], values['accepted_curvature_pairs'],
                     where='post', color=color, linewidth=1.2)
    axes[0].axhline(1e-5, color='0.45', linestyle='--', linewidth=.8,
                   label='Combined stopping: gradient bound')
    axes[0].set_yscale('log')
    axes[0].set_ylabel('Projected gradient norm (s/km)')
    axes[0].set_title('LOM ray 3426: NC/10090782 | NC.JSJ..EHZ\nSame saved FMM initializer and extended outer action sum')
    axes[0].legend(fontsize=8, loc='upper right')
    axes[1].set_ylabel('Retained curvature pairs\n(cumulative)')
    axes[1].set_xlabel('Accepted updates')
    axes[1].set_xscale('symlog', linthresh=1, linscale=.5)
    axes[1].set_xlim(0, 1100)
    ticks = [0, 1, 10, 100, 1000]
    axes[1].set_xticks(ticks)
    axes[1].set_xticklabels([str(value) for value in ticks])
    for axis in axes:
        axis.grid(True, alpha=.2)
    out = ROOT / 'figures/diagnostics'
    out.mkdir(parents=True, exist_ok=True)
    for suffix in ('pdf', 'png'):
        fig.savefig(str(out / ('loma_retention.' + suffix)), dpi=180)
    plt.close(fig)
    metadata = dict(input_sha256=pins, plot_source_sha256=sha(Path(__file__).resolve()),
        native_context=contexts[0], histories=records, unchanged_straight_result=straight[0][0],
        note='The same combined stopping rule also requires a small action change. This isolated result does not establish a safe general retention rule or production adoption. Equal approximate totals are not exact-action classifications.',
        figure_sha256={name: sha(out / name) for name in ('loma_retention.pdf', 'loma_retention.png')})
    (out / 'loma_retention.json').write_text(json.dumps(metadata, indent=2, allow_nan=False) + '\n')


if __name__ == '__main__':
    main()
