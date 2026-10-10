#!/usr/bin/env python3
"""Plot the identified full initial-support comparisons, without tracing rays."""
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('MPLCONFIGDIR', str(ROOT / 'tmp/matplotlib'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def sha(content):
    return hashlib.sha256(content).hexdigest()


def main():
    output = ROOT / 'figures/diagnostics'
    output.mkdir(parents=True, exist_ok=True)
    figures, axes = plt.subplots(1, 2, figsize=(9.2, 3.4), sharey=True)
    records, native = {}, None
    for variant, color, label in [('003', '#D55E00', '003: path 0.5 km, field 0.5 km'),
                                  ('004', '#0072B2', '004: path 0.03125 km, field 0.125 km')]:
        directory = ROOT / ('data/development/hayward_first_arrival_' + variant + '_1d_support')
        summary_bytes = (directory / 'summary.json').read_bytes()
        summary = json.loads(summary_bytes)
        with tarfile.open(str(directory / 'frozen_tables.tar.gz'), 'r:gz') as archive:
            content = archive.extractfile('comparison.csv').read()
        name = str((directory / 'comparison.csv').relative_to(ROOT))
        if sha(content) != summary['output_sha256'][name] or summary['status'] != 'complete':
            raise ValueError('Incomplete or altered comparison: ' + variant)
        reader = csv.DictReader(io.StringIO(content.decode()))
        rows = list(reader)
        metadata = reader.fieldnames[reader.fieldnames.index('station_j'):reader.fieldnames.index('reference_complete')]
        keys = ['row', 'observation_row', 'i', 'station', 'observed'] + metadata
        keys += ['source_' + a + '_km' for a in 'xyz'] + ['receiver_' + a + '_km' for a in 'xyz']
        keys += ['reference_time_s', 'reference_branch'] + ['reference_source_d' + a for a in 'xyz']
        joined = [[row[key] for key in keys] for row in rows]
        if len(rows) != 14262 or (native is not None and joined != native):
            raise ValueError('Comparisons do not share every native observation and reference')
        native = joined
        if not all(row['reference_complete'] == row['reference_valid'] == row['reference_near_tie_count'] == '1' for row in rows):
            raise ValueError('Require complete unique references for every displayed ray')
        time = np.array([abs(float(row['production_minus_reference_s'])) for row in rows])
        source = np.array([np.linalg.norm([float(row['production_source_d' + a + '_minus_reference']) for a in 'xyz']) for row in rows])
        for panel, values in zip(axes, [time * 1e6, source]):
            if not np.all(np.isfinite(values) & (values > 0)):
                raise ValueError('Logarithmic plot requires positive finite saved errors')
            panel.step(np.sort(values), np.arange(1, len(values) + 1) / len(values), where='post', color=color, label=label, linewidth=1.6)
        records[variant] = dict(comparison_sha256=sha(content), summary_sha256=sha(summary_bytes),
            underlying_identified_table=name, rays=len(rows), local_flags_pass=sum(row['ray_converged'] == '1' for row in rows),
            time_limit_pass=int(np.sum(time <= 25e-6)), source_vector_limit_pass=int(np.sum(source <= 3e-6)),
            both_limits_pass=int(np.sum((time <= 25e-6) & (source <= 3e-6))),
            max_absolute_time_error_s=float(time.max()), max_source_vector_error_s_per_km=float(source.max()))
    for ax, limit, text in zip(axes, [25, 3e-6], ['25 microseconds', r'$3\times10^{-6}$ s/km']):
        ax.set_xscale('log'); ax.set_ylim(0, 1.04)
        ax.axvline(limit, color='0.3', linestyle='--', linewidth=1)
        ax.text(limit, .32, ' ' + text, rotation=90, va='bottom', ha='right', fontsize=9, color='0.25')
        ax.grid(axis='y', color='0.9'); ax.tick_params(direction='out')
    axes[0].set_xlabel('Absolute travel-time error (microseconds)')
    axes[1].set_xlabel('Source-derivative vector error (s/km)')
    axes[0].set_ylabel('Fraction of 14,262 initial rays')
    figures.legend(*axes[0].get_legend_handles_labels(), loc='upper center', ncol=1, fontsize=9, frameon=False)
    figures.subplots_adjust(left=.08, right=.99, bottom=.19, top=.78, wspace=.14)
    files = []
    for suffix in ['pdf', 'png']:
        path = output / ('hayward_full_initial_accuracy.' + suffix)
        figures.savefig(str(path), dpi=180)
        files.append(path)
    plt.close(figures)
    manifest = dict(scope='Full identical initial Hayward cohort only; no acceptance of sampled refinement, updated 3D models or inversion',
        time_limit_s=25e-6, source_vector_limit_s_per_km=3e-6, identical_native_observations_and_references=True,
        plotted_comparisons=records, source_sha256=sha(Path(__file__).read_bytes()),
        output_sha256={str(path.relative_to(ROOT)):sha(path.read_bytes()) for path in files})
    (output / 'hayward_full_initial_accuracy.json').write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    main()
