#!/usr/bin/env python3
"""Compare saved original and modified-accumulator histories; no ray solve."""
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
    records, pins, contexts = {}, {}, []
    variants = [('Original', 'loma_initial_failure_3426_001',
                 'completed_with_original_flags_preserved', 'passed_saved_evidence_review'),
                ('Extended outer sum', 'loma_outer_accumulation_native_001',
                 'completed_single_change_diagnostic', 'passed')]
    for label, name, summary_status, review_status in variants:
        source = ROOT / 'data/development' / name
        summary = json.loads((source / 'summary.json').read_text())
        review = json.loads((source / 'review.json').read_text())
        if (summary['status'] != summary_status or review['status'] != review_status or
                review['summary_sha256'] != sha(source / 'summary.json')):
            raise ValueError('Require the completed, reviewed ' + label + ' run')
        for filename in ('history.csv', 'results.csv'):
            if sha(source / filename) != summary['output_sha256'][filename]:
                raise ValueError('Changed saved table: ' + filename)
        values = [r for r in summary['results'] if r['initialization'] == 'fmm']
        if len(values) != 1 or values[0]['converged'] != '0':
            raise ValueError('Expected the preserved false FMM convergence flag')
        result = values[0]
        with (source / 'history.csv').open(newline='') as stream:
            history = [r for r in csv.DictReader(stream) if r['run_id'] == result['run_id']]
        plotted = [r for r in history if r['phase'] in ('initial', 'accepted')]
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
        for filename in ('summary.json', 'review.json', 'history.csv', 'results.csv'):
            pins[str((source / filename).relative_to(ROOT))] = sha(source / filename)
    if contexts[0] != contexts[1]:
        raise ValueError('Native contexts differ')
    if [(len(r['updates']) - 1, r['accepted_curvature_pairs'][-1], r['accepted_equal_binary64_actions'])
            for r in records.values()] != [(53, 34, 5), (1000, 40, 564)]:
        raise ValueError('Saved outcome inventory changed')

    fig, axes = plt.subplots(2, 1, figsize=(7.2, 6.0), sharex=True,
                             constrained_layout=True, gridspec_kw={'height_ratios': [2, 1]})
    for (label, values), color in zip(records.items(), ('#b24336', '#1b6397')):
        style = '--' if label == 'Original' else '-'
        order = 3 if label == 'Original' else 2
        axes[0].plot(values['updates'], values['projected_gradient_s_per_km'],
                     color=color, linewidth=1.2, linestyle=style, zorder=order, label=label)
        axes[0].plot(values['updates'][-1], values['projected_gradient_s_per_km'][-1],
                     'o', color=color, markersize=4)
        axes[1].step(values['updates'], values['accepted_curvature_pairs'],
                     where='post', color=color, linewidth=1.2, linestyle=style, zorder=order)
    axes[0].axhline(1e-5, color='0.45', linestyle='--', linewidth=0.8,
                   label='Combined stopping: gradient bound')
    axes[0].set_yscale('log')
    axes[0].set_ylabel('Projected gradient norm (s/km)')
    axes[0].set_title('LOM initial ray 3426: NC.JSJ..EHZ, FMM start')
    axes[0].legend(fontsize=8, loc='upper right')
    axes[1].set_ylabel('Curvature pairs accepted\n(cumulative)')
    axes[1].set_xlabel('Accepted updates')
    axes[1].set_xscale('symlog', linthresh=1, linscale=0.5)
    axes[1].set_xlim(0, 1100)
    ticks = [0, 1, 10, 53, 100, 435, 1000]
    axes[1].set_xticks(ticks)
    axes[1].set_xticklabels([str(value) for value in ticks])
    for axis in axes:
        axis.grid(True, alpha=0.2)
    out = ROOT / 'figures/diagnostics'
    out.mkdir(parents=True, exist_ok=True)
    for suffix in ('pdf', 'png'):
        fig.savefig(str(out / ('loma_outer_accumulation.' + suffix)), dpi=180)
    plt.close(fig)
    metadata = dict(input_sha256=pins, plot_source_sha256=sha(Path(__file__).resolve()),
        native_context=contexts[0], histories=records,
        note='Both FMM runs retain false local flags. The gradient bound also requires an action-change condition; it is not a standalone convergence test. Extended outer accumulation still returns binary64 totals.',
        figure_sha256={name: sha(out / name) for name in
                       ('loma_outer_accumulation.pdf', 'loma_outer_accumulation.png')})
    (out / 'loma_outer_accumulation.json').write_text(json.dumps(metadata, indent=2, allow_nan=False) + '\n')


if __name__ == '__main__':
    main()
