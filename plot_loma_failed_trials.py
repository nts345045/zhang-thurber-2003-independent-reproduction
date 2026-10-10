#!/usr/bin/env python3
"""Plot the saved binary64 rejections and exact action changes; no ray solve."""
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.environ.setdefault('MPLCONFIGDIR', str(ROOT/'tmp/matplotlib'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    source = ROOT/'data/development/loma_failed_trial_exact_001'
    summary = json.loads((source/'summary.json').read_text())
    review = json.loads((source/'review.json').read_text())
    if (summary['status'] != 'completed_exact_saved_trial_comparison' or
            review['status'] != 'passed_saved_evidence_review' or
            review['summary_sha256'] != sha(source/'summary.json')):
        raise ValueError('Require the reviewed exact comparison')
    records = summary['trials']
    trial = [int(r['original_decision']['trial_index']) for r in records]
    binary = [float(r['original_decision']['trial_action_s'])-
              float(r['original_decision']['cached_base_action_s']) for r in records]
    exact = [r['exact_action_change_s']['lower_display'] for r in records]
    if (trial != list(range(24)) or not all(x > 0 for x in binary) or
            not all(r['exact_saved_slope_armijo'] == 'certified_pass' and
                    r['exact_gradient_armijo'] == 'certified_pass' for r in records)):
        raise ValueError('Saved trial inventory or classification changed')
    out = ROOT/'figures/diagnostics'
    out.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7.2, 4.3), constrained_layout=True)
    ax.axhline(0, color='0.45', linewidth=0.8)
    ax.plot(trial, binary, 'o-', markersize=3.5, color='#b24336', label='Original binary64: recorded increase')
    ax.plot(trial, exact, 'o-', markersize=3.5, color='#1b6397', label='Exact action: certified decrease')
    ax.set_yscale('symlog', linthresh=1e-22, linscale=0.6)
    ax.set_xticks([0, 4, 8, 12, 16, 20, 23])
    ax.set_xlabel(r'Trial index $j$ (step $2^{-j}$)')
    ax.set_ylabel('Trial action minus base action (s)')
    ax.set_title('LOM initial ray 3426: all 24 rounded trial paths')
    ax.grid(True, alpha=0.2)
    ax.legend(loc='center right', fontsize=8)
    for suffix in ('pdf', 'png'):
        fig.savefig(str(out/('loma_failed_trials.'+suffix)), dpi=180)
    plt.close(fig)
    metadata = dict(source_summary_sha256=sha(source/'summary.json'),
        source_review_sha256=sha(source/'review.json'), plot_source_sha256=sha(Path(__file__).resolve()),
        native_context=summary['native_context'], trial_index=trial,
        original_binary64_action_change_s=binary, exact_action_change_lower_display_s=exact,
        note='Enclosure widths are below symbol size; original false local flag is unchanged.',
        figure_sha256={name: sha(out/name) for name in ('loma_failed_trials.pdf','loma_failed_trials.png')})
    (out/'loma_failed_trials.json').write_text(json.dumps(metadata, indent=2, allow_nan=False)+'\n')


if __name__ == '__main__':
    main()
