#!/usr/bin/env python3
"""Plot saved failed-path offsets and model face sections; no ray calculation."""
import csv
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    names = ['normal_sections.csv', 'geometry.pdf', 'geometry.png', 'plot_receipt.json']
    if any((OUT/name).exists() for name in names):
        raise RuntimeError('Preserve existing plot products')
    summary = json.loads((OUT/'summary.json').read_text())
    assert sha(OUT/'near_face_nodes.csv') == summary['output_sha256']['near_face_nodes.csv']
    with (OUT/'near_face_nodes.csv').open() as stream:
        records = list(csv.DictReader(stream))
    sections = []
    fig, axes = plt.subplots(1, 2, figsize=(8.2, 3.2), layout='constrained')
    for event, color in [(981, '#0072B2'), (987, '#D55E00')]:
        rows = [r for r in records if int(r['event']) == event]
        closest = min(rows, key=lambda r: abs(float(r['x'])))
        label = closest['source_event_resource_id'].rsplit('/', 1)[-1]
        v = float(closest['projection_v_km_per_s'])
        vl = v - 3*float(closest['left_dv_dx_per_s'])
        vr = v + 5*float(closest['right_dv_dx_per_s'])
        axes[0].plot([-3, 0, 5], [vl, v, vr], color=color, label=label,
                     linestyle='-' if event == 981 else '--', linewidth=1.5)
        for x, velocity in [(-3, vl), (0, v), (5, vr)]:
            row = dict(closest)
            row.update(section_x_km=x, section_v_km_per_s=format(velocity, '.17g'))
            sections.append(row)
        axes[1].plot([int(r['node']) for r in rows], [float(r['x']) for r in rows],
                     color=color, marker='.', markersize=4, linewidth=.8, label=label)
    axes[0].axvline(0, color='.6', linewidth=.6)
    axes[0].set(xlabel='Normal coordinate x (km)', ylabel='Trial-model velocity (km/s)',
                title='Sections through closest saved nodes')
    axes[1].axhline(0, color='.5', linewidth=.6)
    axes[1].set_yscale('symlog', linthresh=1e-10)
    axes[1].set_ylim(-1e-6, 1e-6)
    axes[1].set(xlabel='Saved path node index', ylabel='Computed x offset (km)',
                title='Preserved nodes within 1 mm of x=0')
    axes[0].legend(title='Event at NC.CMJ..EHZ', fontsize=8, title_fontsize=8, frameon=False)
    for ax in axes:
        ax.tick_params(labelsize=8)
        ax.spines[['top', 'right']].set_visible(False)
    fig.savefig(OUT/'geometry.pdf', metadata={'Title': 'Rejected Hayward trial: normal velocity sections and saved path offsets'})
    fig.savefig(OUT/'geometry.png', dpi=180)
    plt.close(fig)
    with (OUT/'normal_sections.csv').open('x', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(sections[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(sections)
    receipt = {'scope': 'Diagnostic plot of saved failed paths and calculated model sections; not a manuscript reproduction panel or accepted ray/inverse result.',
               'source_sha256': sha(Path(__file__)), 'matplotlib_version': matplotlib.__version__,
               'input_sha256': {n: sha(OUT/n) for n in ['summary.json', 'near_face_nodes.csv']},
               'output_sha256': {n: sha(OUT/n) for n in names[:-1]},
               'normal_sections': 'Three x vertices per event at fixed y,z of the closest recorded node, using the independently reviewed face values/slopes. Adjacent-cell interpolation is linear in x; binary64 display reconstruction only.',
               'limits': 'Offset magnitudes describe numerical coordinates, not observational accuracies. Only nodes within the declared descriptive 1mm interval are displayed; no solver geometry or flag changes.'}
    (OUT/'plot_receipt.json').write_text(json.dumps(receipt, indent=2, sort_keys=True)+'\n')


if __name__ == '__main__':
    main()
