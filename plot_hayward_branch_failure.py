#!/usr/bin/env python3
"""Plot the saved, fully identified initial-ray 14099 branch investigation."""
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
import numpy as np


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def table(path):
    with path.open() as stream:
        return list(csv.DictReader(stream))


def main():
    base = ROOT / 'data/development'
    cases = [base / ('initial_ray_first_arrival_003_14099_' + name)
             for name in ('audit001', 'field025001', 'field0125001')]
    hashes, reviews, results = {}, [], []
    for case in cases:
        run = json.loads((case / 'summary.json').read_text())
        if run['status'] != 'completed_with_original_flags_preserved':
            raise ValueError('Ray diagnosis incomplete')
        review_dir = case / 'branch_review'
        review = json.loads((review_dir / 'summary.json').read_text())
        for directory, record in ((case, run), (review_dir, review)):
            for name, expected in record['output_sha256'].items():
                path = directory / name
                if sha(path) != expected:
                    raise ValueError('Frozen artifact changed: ' + str(path))
                hashes[str(path.relative_to(ROOT))] = expected
            hashes[str((directory / 'summary.json').relative_to(ROOT))] = sha(directory / 'summary.json')
        if reviews and (review['native_identity'] != reviews[0]['native_identity'] or
                        review['reference'] != reviews[0]['reference']):
            raise ValueError('Field variants changed the native geometry/reference')
        reviews.append(review)
        rows = table(review_dir / 'identified_branch_comparison.csv')
        if any(r['logged_matches_unobserved_variant'] != '1' for r in rows):
            raise ValueError('Observed and frozen production traces differ')
        results.append([r for r in rows if r['max_updates'] == '1000'])
    reference = reviews[0]['reference']
    if not reference['complete'] or not reference['reference_valid'] or len(reference['near_ties']) != 1:
        raise ValueError('Require the complete unique first-arrival reference')
    identity = reviews[0]['native_identity']
    source = np.asarray(reviews[0]['source_xyz_km'])
    receiver = np.asarray(reviews[0]['receiver_xyz_km'])
    horizontal = receiver[:2] - source[:2]
    distance = np.linalg.norm(horizontal)
    unit = horizontal / distance

    def projection(points):
        points = np.asarray(points)
        if not np.isfinite(points).all():
            raise ValueError('Nonfinite plotted coordinates')
        radial = (points[:, :2] - source[:2]).dot(unit)
        cross = (points[:, 0] - source[0]) * unit[1] - (points[:, 1] - source[1]) * unit[0]
        return radial, points[:, 2], float(np.max(np.abs(cross)))

    selected = []
    for rows in results:
        for spacing in sorted({float(r['path_spacing_km']) for r in rows}, reverse=True):
            group = [r for r in rows if float(r['path_spacing_km']) == spacing]
            if {r['initialization'] for r in group} != {'straight', 'fmm'}:
                raise ValueError('A start is missing from the retained comparison')
            selected.append(min(group, key=lambda r: float(r['time_s'])))
    plt.rcParams.update({'font.size': 9, 'axes.spines.top': False, 'axes.spines.right': False,
                         'pdf.fonttype': 42, 'ps.fonttype': 42})
    fig, axes = plt.subplots(1, 3, figsize=(11.4, 3.65), gridspec_kw={'width_ratios': [1.8, 1, 1]})
    ax, bx, cx = axes
    reference_points = table(cases[0] / 'branch_review/reference_paths.csv')
    first_time = reference['first_arrival']['time_s']
    order = sorted(range(len(reference['candidates'])), key=lambda i: reference['candidates'][i]['time_s'])
    for rank, branch in enumerate(order):
        candidate = reference['candidates'][branch]
        points = [[float(r[k + '_km']) for k in 'xyz'] for r in reference_points if int(r['branch_index']) == branch]
        radial, depth, unused = projection(points)
        ax.plot(radial, depth, color=['#17649b', '#b35b26', '#999999'][rank],
                ls=['-', '--', ':'][rank], lw=1.7 if rank < 2 else 1,
                label=['Exact earliest', 'Exact deep branch', 'Third stationary branch'][rank])
    plotted = []
    for case, field, color, marker in ((cases[0], .5, '#b35b26', 'o'), (cases[2], .125, '#17649b', 's')):
        row = next(r for r in selected if float(r['path_spacing_km']) == .03125 and float(r['field_spacing_km']) == field)
        points = [[float(r[k]) for k in 'xyz'] for r in table(case / 'spacing0_031250/paths.csv') if r['run_id'] == row['run_id']]
        if not np.array_equal(points[0], source) or not np.array_equal(points[-1], receiver):
            raise ValueError('Plotted endpoints differ from the identified coordinates')
        radial, depth, cross = projection(points)
        ax.plot(radial, depth, color=color, ls='none', marker=marker, markersize=3.8,
                markerfacecolor='none', markevery=max(1, len(points) // 18), label='FMM field {} km'.format(field))
        plotted.append(dict(field_spacing_km=field, path_spacing_km=.03125,
                            run_id=row['run_id'], maximum_cross_track_km=cross))
    ax.axhline(12, color='#777777', lw=.7, alpha=.45)
    ax.plot([0, distance], [source[2], receiver[2]], color='black', ls='none', marker='x', markersize=5)
    ax.set(xlabel='Projected source–receiver distance (km)', ylabel='Depth (km)',
           title='(a) Distinct arrival branches', ylim=(15.2, -.8))
    ax.legend(frameon=False, fontsize=7.4, loc='upper left')

    path_series = sorted((r for r in selected if float(r['field_spacing_km']) == .5),
                         key=lambda r: float(r['path_spacing_km']), reverse=True)
    bx.plot([float(r['path_spacing_km']) for r in path_series],
            [float(r['time_minus_first_arrival_s']) * 1e3 for r in path_series], 'o-', color='#b35b26')
    deep_gap = (reference['candidates'][order[1]]['time_s'] - first_time) * 1e3
    bx.axhline(deep_gap, color='#777777', ls='--', lw=1, label='Exact deep-branch gap')
    bx.set(xscale='log', xlim=(.6, .025), ylim=(2.178, 2.242), xlabel='Path spacing (km)',
           ylabel='Time above earliest arrival (ms)', title='(b) Field held at 0.5 km')
    bx.set_xticks([.5, .125, .03125]); bx.set_xticklabels(['0.5', '0.125', '0.03125'])
    bx.minorticks_off(); bx.legend(frameon=False, fontsize=7.2, loc='upper right')

    field_series = sorted((r for r in selected if float(r['path_spacing_km']) == .03125),
                          key=lambda r: float(r['field_spacing_km']), reverse=True)
    cx.plot([float(r['field_spacing_km']) for r in field_series],
            [float(r['time_minus_first_arrival_s']) * 1e6 for r in field_series], 's-', color='#17649b')
    cx.axhline(25., color='#777777', ls='--', lw=1, label='25 µs control limit')
    cx.set(xscale='log', yscale='log', xlim=(.6, .1), ylim=(.1, 5000), xlabel='FMM field spacing (km)',
           ylabel='Time above earliest arrival (µs)', title='(c) Path held at 0.03125 km')
    cx.set_xticks([.5, .25, .125]); cx.set_xticklabels(['0.5', '0.25', '0.125'])
    cx.minorticks_off(); cx.legend(frameon=False, fontsize=7.2, loc='lower left')
    for axis in (bx, cx):
        axis.grid(axis='y', color='#dddddd', lw=.6, zorder=-1)
    fig.suptitle('Identified initial ray 14099: NC/30204761 → NC.JJR..EHZ', fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, .96), w_pad=2.)
    out = ROOT / 'figures/diagnostics'
    out.mkdir(parents=True, exist_ok=True)
    files = [out / ('hayward_branch_failure.' + suffix) for suffix in ('pdf', 'png')]
    for path in files:
        fig.savefig(str(path), dpi=240, bbox_inches='tight')
    plt.close(fig)
    for name, expected in hashes.items():
        if sha(ROOT / name) != expected:
            raise ValueError('Frozen plotting input changed during rendering')
    script = Path(__file__).resolve()
    hashes[str(script.relative_to(ROOT))] = sha(script)
    manifest = dict(scope='Diagnostic figure from independent saved numerical paths; not a manuscript panel reproduction',
                    command='OPENBLAS_NUM_THREADS=1 python3 plot_hayward_branch_failure.py',
                    native_identity=identity, source_xyz_km=list(source), receiver_xyz_km=list(receiver),
                    reference=reference, selected_cases=selected, plotted_paths=plotted,
                    input_sha256=hashes, output_sha256={str(p.relative_to(ROOT)): sha(p) for p in files},
                    limitations=['One initial-profile ray; no full-cohort accuracy claim.',
                                 'Path panel projects saved 3D curves onto the endpoint vertical plane.',
                                 'All displayed selected candidates report local convergence; that alone does not select the first arrival.'])
    (base / 'hayward_branch_figure.json').write_text(json.dumps(manifest, indent=2, allow_nan=False) + '\n')
    print('Wrote diagnostic PDF/PNG and identified input/output manifest')


if __name__ == '__main__':
    main()
