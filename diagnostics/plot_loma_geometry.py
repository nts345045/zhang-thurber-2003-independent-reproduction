#!/usr/bin/env python3
"""Plot closed, identified Loma Prieta simulation geometry; no solver calls."""
import argparse
import csv
import hashlib
import itertools
import json
import os
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('MPLCONFIGDIR', str(ROOT / 'tmp/matplotlib'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def joined(native, selected, keys):
    lookup = {tuple(row[key] for key in keys): row for row in selected}
    assert len(lookup) == len(selected) == len(native)
    assert {tuple(row[key] for key in keys) for row in native} == set(lookup)
    for index, row in enumerate(native):
        assert int(row['id']) == index
        original = lookup[tuple(row[key] for key in keys)]
        assert all(row[key] == value for key, value in original.items())
        assert row['selected'] == '1' and not row['exclusion_reasons']
    return len(native) * len(selected[0])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path,
                        default=Path('data/development/loma_geometry_figure_001/inputs'))
    parser.add_argument('--output', type=Path,
                        default=Path('tmp/loma_geometry_figure_rebuild_001'))
    args = parser.parse_args()
    out = (ROOT / args.output).resolve()
    out.relative_to(ROOT)  # Keep all outputs inside the project.
    if out.exists():
        raise SystemExit('Output exists; select a fresh --output directory: ' + str(out))
    native = (ROOT / args.input).resolve()
    native.relative_to(ROOT)
    authoritative = ROOT / 'data/authoritative/loma_prieta'
    native_names = ('truth_events.csv', 'stations.csv', 'initial_grid.csv',
                    'simulation_execution.json', 'independent_simulation_review.json', 'preparation_manifest.json')
    paths = [native / name for name in native_names]
    paths += [authoritative / name for name in ('selected_events.csv', 'selected_channels.csv', 'README.md')]
    paths += [ROOT / 'data/development/loma_specification/README.md', Path(__file__).resolve()]
    review = json.loads((native / 'independent_simulation_review.json').read_text())
    execution = json.loads((native / 'simulation_execution.json').read_text())
    preparation = json.loads((native / 'preparation_manifest.json').read_text())
    assert review['status'] == 'passed'
    assert execution['status'] == 'completed' and execution['return_code'] == 0
    for name in ('truth_events.csv', 'stations.csv', 'initial_grid.csv'):
        assert sha(native / name) == review['input_sha256'][name]
    assert sha(native / 'simulation_execution.json') == review['input_sha256']['simulation_execution.json']
    assert sha(native / 'preparation_manifest.json') == review['input_sha256']['preparation_manifest.json']
    for name in ('selected_events.csv', 'selected_channels.csv'):
        path = authoritative / name
        assert sha(path) == preparation['input_sha256'][str(path.relative_to(ROOT))]
    events, receivers, grid = [read(native / name) for name in
                               ('truth_events.csv', 'stations.csv', 'initial_grid.csv')]
    assert (len(events), len(receivers), len(grid)) == (724, 52, 288)
    event_fields = joined(events, read(authoritative / 'selected_events.csv'), ('event_resource_id',))
    receiver_fields = joined(receivers, read(authoritative / 'selected_channels.csv'),
                             ('channel_seed_id', 'metadata_epoch_start', 'metadata_epoch_end'))
    for row in events:
        assert row['event_resource_id'] and row['origin_resource_id'] and row['magnitude_resource_id']
        assert row['coordinate_basis'] == 'catalog-defined simulation truth'
        assert float(row['t']) == 0
        for key, original in (('x', 'x_km'), ('y', 'y_km'), ('z', 'geoid_depth_km')):
            assert row[key] == format(float(row[original]), '.12g')
    for row in receivers:
        assert row['station_seed_id'] == row['network_code'] + '.' + row['station_code']
        assert row['channel_seed_id'] == '.'.join(row[key] for key in
                                                ('network_code', 'station_code', 'location_code', 'channel_code'))
        assert row['station_fdsn_source_id'] and row['channel_fdsn_source_id']
        assert row['metadata_epoch_start'] and row['metadata_epoch_end']
        for key, original in (('x', 'x_km'), ('y', 'y_km'), ('z', 'sensor_z_geoid_km')):
            assert float(row[key]) == float(row[original])
    raw_hashes = {}
    for row in events + receivers:
        path = authoritative / row['source_file']
        if path not in raw_hashes:
            raw_hashes[path] = sha(path)
        assert raw_hashes[path] == row['source_sha256']
    paths += sorted(raw_hashes)
    axes = {key: sorted({float(row[key]) for row in grid}) for key in ('x', 'y', 'z')}
    assert axes == {'x': [-35, -15, 0, 2, 4, 6, 20, 35], 'y': [-60, -40, -20, 0, 20, 40],
                    'z': [-1, 0, 3, 7, 11, 16]}
    assert {tuple(float(row[key]) for key in ('x', 'y', 'z')) for row in grid} == set(
        itertools.product(axes['x'], axes['y'], axes['z']))
    for row in events + receivers:
        assert all(axes[key][0] <= float(row[key]) <= axes[key][-1] for key in axes)
    old_figures = {str(path.relative_to(ROOT)): sha(path) for path in
                   (ROOT / 'figures/figure02.pdf', ROOT / 'figures/figure02.png') if path.exists()}
    input_hashes = {str(path.relative_to(ROOT)): sha(path) for path in paths}
    out.mkdir(parents=True)
    (out / 'inputs').mkdir()
    for name in native_names:
        shutil.copyfile(native / name, out / 'inputs' / name)
        assert sha(out / 'inputs' / name) == sha(native / name)

    plt.rcParams.update({'font.size': 10, 'savefig.dpi': 180, 'pdf.fonttype': 42})
    fig, ax = plt.subplots(figsize=(6.4, 8.6))
    fig.subplots_adjust(left=0.15, right=0.93, top=0.88, bottom=0.21)
    plane = [row for row in grid if float(row['z']) == 0]
    ax.scatter([float(row['x']) for row in plane], [float(row['y']) for row in plane],
               marker='+', s=42, linewidths=0.9, color='0.60', label='Horizontal grid nodes (48)', zorder=1)
    ax.scatter([float(row['x']) for row in events], [float(row['y']) for row in events],
               s=7, color='0.15', linewidths=0, label='Catalog-defined sources (724)', zorder=2)
    ax.scatter([float(row['x']) for row in receivers], [float(row['y']) for row in receivers],
               marker='^', s=39, facecolors='none', edgecolors='#b55216', linewidths=1.1,
               label='NC EHZ receiver epochs (52)', zorder=3)
    ax.set(xlim=(-38, 38), ylim=(-63, 43), xlabel='Rotated X (km)', ylabel='Rotated Y (km)')
    ax.set_aspect('equal', adjustable='box')
    ax.set_xticks([-35, -15, 0, 20, 35])
    ax.set_yticks(axes['y'])
    fig.legend(*ax.get_legend_handles_labels(), loc='lower center',
               bbox_to_anchor=(0.54, 0.075), frameon=False, fontsize=9)
    fig.suptitle('Figure 2 candidate: Loma Prieta input geometry\n'
                 'Documented authoritative subset; partial reproduction', y=0.96, fontsize=12)
    fig.text(0.5, 0.034, 'Equal distance scales; X=(E+N)/√2, Y=(−E+N)/√2.\n'
             'Study cohort and projection are not recovered. Input geometry only.',
             ha='center', va='bottom', fontsize=9)
    stem = 'figure02_authoritative_geometry_candidate'
    fig.savefig(out / (stem + '.pdf'), metadata={'CreationDate': None, 'ModDate': None})
    fig.savefig(out / (stem + '.png'))
    plt.close(fig)
    readme = '''# Loma Prieta geometry candidate for Figure 2

This partial replacement shows the saved horizontal input geometry: 724 catalog-defined
simulation sources, 52 NC EHZ receiver epochs at 52 stations, and the 48 horizontal
grid nodes specified by the manuscript's Figure 2 caption. Black points show sources,
orange open triangles show receivers, and gray crosses show grid nodes. Both axes
are in kilometres with equal distance scales. The plot contains no inferred fault trace.

NCEDC NCSS catalog origins supply the event coordinates. EarthScope discovery routed
the receiver request to authoritative NCEDC StationXML. The event selection spans
1989-10-18 to 1989-11-18 UTC, magnitudes 2.0–5.5, and catalog depths 0–16 km;
the receiver snapshot is 1989-11-01 UTC. Full selection criteria and exclusions remain
in `data/authoritative/loma_prieta/README.md` (repository-relative paths throughout).

The horizontal coordinates use WGS84 tangent east/north directions at 37.0361667° N,
−121.8798333° E, followed by X=(E+N)/sqrt(2), Y=(−E+N)/sqrt(2). That origin is the
saved USGS mainshock geometry: event `quakeml:nc.anss.org/Event/NC/216859`, origin
`quakeml:nc.anss.org/Origin/NC/2642104`. The rotation, windows, magnitude limits,
NC EHZ restriction, and receiver snapshot are independent choices. The exact 2003
study cohort, projection, and map layout have not been recovered. No target cohort
count is asserted, and no map was digitized. These positions define a simulation;
they do not establish historical source–receiver incidence or inversion recovery.

The native grid has X=[−35,−15,0,2,4,6,20,35] and Y=[−60,−40,−20,0,20,40] km.
The documented five depth levels [0,3,7,11,16] km are extended by a −1 km top level
to contain all receivers. Thus the saved grid has 8×6×6 nodes; its horizontal
projection matches the written 8×6 specification. Receiver z ranges from −0.921
to −0.039 km under the saved sensor-elevation convention. Neither depth nor model
velocity is encoded in this horizontal plot. See `data/development/loma_specification/README.md`.

`inputs/truth_events.csv`, `inputs/stations.csv`, and `inputs/initial_grid.csv` are
byte-identical copies of the closed native tables used here, originally under
`data/loma_lom_analytic_001`. Three small completion/preparation/review JSON records
are also copied. A fresh checkout can rebuild this figure from these files and the
tracked authoritative inputs; the multi-gigabyte simulation archive is not required.
Every selected authoritative metadata field is
matched by event resource ID or channel SEED ID plus effective epoch. Event,
origin, magnitude, and available provider resource IDs; station/channel SEED and
derived FDSN identifiers; epochs; raw-response hashes; and valid blank locations
are preserved. Provider station/channel resource-ID fields that were absent remain
explicitly empty. Derived FDSN identifiers are labeled in the native metadata.
Provider `source_file` paths retain their `data/authoritative/loma_prieta` base.

The plotted event x/y values use the saved C++ serialization at 12 significant
digits; the full-precision authoritative x_km/y_km values remain in the same rows.
Their maximum coordinate difference is below 5e−11 km. No coordinate is recomputed,
perturbed, relocated, or omitted. The former random `figures/figure02` files remain intact.

Run from the repository root, choosing a fresh output directory for each run:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B diagnostics/plot_loma_geometry.py --output tmp/loma_geometry_figure_rebuild_001
```

The script uses only Python's standard library and Matplotlib, verifies the closed
source hashes and complete joins, and saves PDF/PNG plus identified sidecars.
`manifest.json` records source/output hashes, counts, checks, command, and versions.
This package does not alter the report, panel audit, solver, or published figures.
'''
    (out / 'README.md').write_text(readme)
    assert old_figures == {name: sha(ROOT / name) for name in old_figures}
    assert input_hashes == {name: sha(ROOT / name) for name in input_hashes}
    manifest = {
        'status': 'passed', 'figure_status': 'partially reproduced',
        'scope': 'Saved authoritative-subset input geometry only; no solver or reference calculation',
        'command': [sys.executable] + sys.argv, 'python_version': sys.version,
        'matplotlib_version': matplotlib.__version__, 'input_sha256': input_hashes,
        'original_native_source_sha256': {'data/loma_lom_analytic_001/' + name: sha(native / name)
                                         for name in native_names},
        'counts': {'events': len(events), 'receiver_epochs': len(receivers),
                   'stations': len({row['station_seed_id'] for row in receivers}),
                   'horizontal_grid_nodes': len(plane), 'saved_grid_nodes': len(grid),
                   'blank_location_codes': sum(not row['location_code'] for row in receivers),
                   'absent_provider_channel_source_ids': sum(not row['provider_channel_source_id'] for row in receivers)},
        'checks': {'exact_event_metadata_field_joins': event_fields,
                   'exact_receiver_metadata_field_joins': receiver_fields,
                   'all_native_ids_contiguous': True, 'complete_one_to_one_identity_joins': True,
                   'all_xyz_within_saved_grid': True, 'sidecars_byte_identical': True,
                   'event_xyz_serialization': 'Exactly format(authoritative value, .12g)',
                   'event_xyz_max_absolute_serialization_difference_km': {
                       key: max(abs(float(row[key]) - float(row[original])) for row in events)
                       for key, original in (('x', 'x_km'), ('y', 'y_km'), ('z', 'geoid_depth_km'))},
                   'receiver_xyz_exact': True, 'all_raw_response_hashes_match': True,
                   'source_inputs_unchanged': True, 'old_figure02_unchanged': True},
        'grid_axes_km': axes, 'plot_axes_limits_km': {'x': [-38, 38], 'y': [-63, 43]},
        'plot_distance_aspect': 1, 'old_figure02_sha256': old_figures,
        'output_sha256': {str(path.relative_to(out)): sha(path)
                          for path in sorted(out.rglob('*')) if path.is_file()}}
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({'output': str(out.relative_to(ROOT)), 'counts': manifest['counts'],
                      'metadata_fields_matched': event_fields + receiver_fields, 'status': 'passed'}, indent=2))


if __name__ == '__main__':
    main()
