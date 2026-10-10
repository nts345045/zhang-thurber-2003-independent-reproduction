"""Plot closed CC support; no waveform, graph, forward, or inverse calculation."""
import argparse
from collections import Counter
import csv
import datetime
import gzip
import hashlib
import io
import json
import math
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CC = ROOT / 'data/development/native_cc_connectivity_001'
DATA = ROOT / 'data/hayward_catalog_cc_001'
PINS = {}
CHECKS = Counter()
OUTPUTS = []
CHANNELS = ['NC.JPR.02.EHZ', 'NC.CBR.10.EHZ', 'NC.JSB.10.EHZ', 'NC.JSF.10.EHZ']
COLORS = ['#0072B2', '#D55E00', '#009E73', '#CC79A7']
EXPECTED_COUNTS = dict(zip(CHANNELS, [75, 19, 3, 1]))
CAPTION = (
    'Spatial support of 98 accepted normalized waveform-correlation (CC) pairs. '
    '(a) All 1,092 selected catalog events and the four receiving channels. '
    '(b) A northern detail of the same event geometry, marked by the dashed box '
    'in (a). Gray points '
    'show the catalog subset; black points identify the 103 events in accepted '
    'pairs. Colored segments join paired events; triangles locate their receiving '
    'channels. Segments are pair links, not seismic ray paths. Coordinates are '
    'the saved local rotated x and y in km; neither panel moves points. '
    'The accepted CC-only graph has 32 components. Multiple epochs at the same '
    'channel position share a plotted symbol, while all 22 used epochs and both '
    'sides of 38 cross-epoch measurements remain identified in the companion files. '
    'This figure describes observed input availability and support. It does not '
    'establish historical waveform absence, manuscript membership, combined-system '
    'rank, resolution, or inversion accuracy. No CC measurement has entered the '
    'catalog-only inversion shown elsewhere.')


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def check(condition, name):
    if not condition:
        raise ValueError(name)
    CHECKS[name] += 1


def pin(path, expected=None):
    value = sha(path)
    check(expected is None or value == expected, 'input hash')
    PINS[str(path.relative_to(ROOT))] = value
    return value


def read_json(path, expected):
    pin(path, expected)
    return json.loads(path.read_text())


def rows(path):
    opener = gzip.open if path.suffix == '.gz' else open
    with opener(path, 'rt', newline='') as f:
        r = csv.DictReader(f)
        check(len(r.fieldnames) == len(set(r.fieldnames)), 'unique CSV headers')
        result = list(r)
    check(all(None not in r and None not in r.values() for r in result), 'complete CSV rows')
    return result


def save(out, name, content):
    with (out / name).open('xb') as f:
        f.write(content)
    OUTPUTS.append(name)


def dump(out, name, value):
    content = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()
    save(out, name, gzip.compress(content, mtime=0) if name.endswith('.gz') else content)


def main(out):
    out.mkdir()  # A fresh result directory is required; failed attempts are retained.
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    pin(Path(__file__).resolve())
    pin(HERE / 'README.md')
    save(out, 'plot_source.py', Path(__file__).read_bytes())
    connectivity = read_json(CC / 'summary.json', '2fb98b78c31ec8902012f2cf0eb96674c9913220bcd77edb22810623c05df48b')
    review = read_json(CC / 'review.json', '9f4f46b13efa79c624db89eb9ecbf855e783a7ad5ad1a00fa1881f35ebc2feb9')
    prepared = read_json(DATA / 'preparation_manifest.json', '63e909d134182a2dc116c73a20c2d204284f77baf5b333ffde54a820f04944a0')
    native_review = read_json(DATA / 'independent_review.json', 'f7991cadfdab0d08efe8321c9595e09820ea092233a48264ea39a36cec0b850d')
    execution = read_json(DATA / 'execution.json', '21d01bbc4898d2ebf933566421ea8852d65dd0232665cf9d25c14ad4cfe8f7ec')
    check(review['status'] == native_review['status'] == 'passed', 'closed independent reviews')
    check(review['connectivity_summary_sha256'] == sha(CC / 'summary.json'), 'connectivity review binding')
    check(execution['status'] == 'completed' and execution['return_code'] == 0, 'closed input preparation')
    check(execution['preparation_manifest_sha256'] == native_review['preparation_manifest_sha256'] == sha(DATA / 'preparation_manifest.json'), 'native preparation binding')
    for name in ['accepted_measurements.csv.gz', 'event_membership.csv']:
        pin(CC / name, connectivity['output_sha256'][name])
    for name in ['initial_events.csv', 'stations.csv', 'catalog_provenance/observations.csv']:
        pin(DATA / name, prepared['output_sha256'][name])
        check(PINS[str((DATA / name).relative_to(ROOT))] == native_review['verified_sha256'][str((DATA / name).relative_to(ROOT))], 'independently reviewed geometry/catalog bytes')
    for name in ['data/development/native_waveform_cc_001/summary.json', 'data/development/native_waveform_cc_001/independent_measurement_review.json']:
        pin(ROOT / name, connectivity['input_source_sha256'][name])
    check(connectivity['accepted_measurements'] == review['accepted_rows'] == 98 and connectivity['component_count'] == 32, 'reviewed CC inventory')
    accepted, members = rows(CC / 'accepted_measurements.csv.gz'), rows(CC / 'event_membership.csv')
    events, stations = rows(DATA / 'initial_events.csv'), rows(DATA / 'stations.csv')
    check(len(events) == 1092 and len(stations) == 372 and len(accepted) == 98, 'complete plotted input counts')
    for table in [events, stations]:
        check([int(r['id']) for r in table] == list(range(len(table))), 'native index order')
        check(all(math.isfinite(float(r[k])) for r in table for k in 'xyz'), 'finite saved coordinates')
    needed = {int(r['original_catalog_original_observation_index']) for r in accepted}
    needed.update(int(r['waveform_' + side + '_original_observation_index']) for r in accepted for side in ('i', 'j'))
    with (DATA / 'catalog_provenance/observations.csv').open(newline='') as f:
        reader = csv.DictReader(f)
        catalog = {i: row for i, row in enumerate(reader) if i in needed}
    check(len(catalog) == len(needed), 'all original pair and absolute-pick references')
    plotted, used_events, used_epochs = [], set(), set()
    identity_rows = []
    for r in accepted:
        check(r['measurement_status'] == 'accepted_discrete_measurement', 'accepted measurement status')
        original = catalog[int(r['original_catalog_original_observation_index'])]
        check(all(r['original_catalog_' + k] == v for k, v in original.items()), 'every original catalog field unchanged')
        derived = dict(r)
        sides = {}
        for side, station_key, suffix in [('i', 'station', ''), ('j', 'station_j', '_j')]:
            ei, si = int(original[side]), int(original[station_key])
            event, station = events[ei], stations[si]
            used_events.add(ei); used_epochs.add(si)
            check(all(original[k + '_' + side + '_resource_id'] == event[k + '_resource_id'] for k in ('event', 'origin')), 'event/origin/index join')
            for k in ['network_code', 'station_code', 'location_code', 'channel_code', 'channel_seed_id', 'channel_fdsn_source_id']:
                check(original[k] == station[k], 'both-side full channel join')
            check(original['metadata_epoch' + suffix + '_start'] == station['metadata_epoch_start'] and original['metadata_epoch' + suffix + '_end'] == station['metadata_epoch_end'], 'both-side epoch join')
            check(original['channel' + suffix + '_source_sha256'] == station['source_sha256'], 'both-side metadata source hash')
            pick = catalog[int(r['waveform_' + side + '_original_observation_index'])]
            check(pick['type'] == '0' and int(pick['i']) == ei and int(pick['station']) == si, 'absolute pick native index join')
            for k in ['event', 'origin', 'pick', 'arrival']:
                check(original[k + '_' + side + '_resource_id'] == pick[k + '_i_resource_id'], 'absolute pick/association identity join')
            check(original['pick_' + side + '_time_utc'] == pick['pick_i_time_utc'] and original['pick_' + side + '_source_sha256'] == pick['pick_i_source_sha256'], 'pick time/source join')
            for k in 'xyz':
                derived['plot_event_' + side + '_' + k + '_km'] = event[k]
                derived['plot_receiver_' + side + '_' + k + '_km'] = station[k]
            sides[side] = dict(event_index=ei, receiver_epoch_index=si, absolute_pick=pick)
        check(original['cross_metadata_epoch'] == str(int(original['station'] != original['station_j'])), 'cross-epoch distinction')
        plotted.append(derived)
        identity_rows.append(dict(measurement=dict(r), native_sides=sides))
    check(len(used_events) == 103 and len(used_epochs) == 22, 'used event/epoch counts')
    check(len({r['measurement_id'] for r in accepted}) == len({tuple(sorted((int(r['original_catalog_i']), int(r['original_catalog_j'])))) for r in accepted}) == 98, 'unique measurements and event pairs')
    check({int(r['original_event_index']) for r in members} == used_events and len(members) == 103, 'reviewed component event set')
    for r in members:
        event = events[int(r['original_event_index'])]
        check(all(r[k] == event[k] for k in ['event_resource_id', 'origin_resource_id']), 'component native identity join')
    counts = Counter(r['original_catalog_channel_seed_id'] for r in accepted)
    cross = sum(r['original_catalog_cross_metadata_epoch'] == '1' for r in accepted)
    check(dict(counts) == EXPECTED_COUNTS and cross == 38, 'channel and cross-epoch totals')
    positions = {}
    for channel in CHANNELS:
        ss = [stations[i] for i in sorted(used_epochs) if stations[i]['channel_seed_id'] == channel]
        xy = {(r['x'], r['y']) for r in ss}
        check(len(xy) == 1, 'epochs share exact saved channel position')
        positions[channel] = list(next(iter(xy)))
    identifiers = dict(scope='Closed observed CC input support only', input_source_sha256=dict(PINS),
        coordinate_basis='Unchanged saved local rotated x/y/z in km; no reprojection or amplification',
        catalog_events=events, receiver_epochs=[stations[i] for i in sorted(used_epochs)],
        accepted_pairs=identity_rows, event_component_membership=members,
        metadata_relative_path_base='Original provider source_file values retain their data/hayward base',
        epoch_plotting='Only exactly coincident coordinates are shown by one channel marker; all epoch records retained')
    dump(out, 'plot_identifiers.json.gz', identifiers)
    buffer = io.StringIO(newline='')
    writer = csv.DictWriter(buffer, fieldnames=list(plotted[0])); writer.writeheader(); writer.writerows(plotted)
    save(out, 'plotted_event_pairs.csv', buffer.getvalue().encode())
    save(out, 'CAPTION.txt', (CAPTION + '\n').encode())

    cache = ROOT / 'tmp' / ('native_cc_spatial_support_render_' + out.name)
    for key, name in [('MPLCONFIGDIR', 'matplotlib'), ('XDG_CACHE_HOME', 'xdg'), ('TMPDIR', 'tmp')]:
        path = cache / name; path.mkdir(parents=True, exist_ok=True); os.environ[key] = str(path)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.patches import Rectangle
    plt.rcParams.update({'font.size': 9, 'axes.spines.top': False, 'axes.spines.right': False, 'pdf.fonttype': 42, 'ps.fonttype': 42})
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 7.6), gridspec_kw={'width_ratios': [1.5, 1]})
    fig.subplots_adjust(left=.08, right=.97, bottom=.23, top=.88, wspace=.24)
    for ax in axes:
        ax.scatter([float(e['x']) for e in events], [float(e['y']) for e in events], s=5, c='.75', alpha=.7, edgecolors='none', zorder=1)
        for channel, color in zip(CHANNELS, COLORS):
            for r in plotted:
                if r['original_catalog_channel_seed_id'] == channel:
                    ax.plot([float(r['plot_event_i_x_km']), float(r['plot_event_j_x_km'])], [float(r['plot_event_i_y_km']), float(r['plot_event_j_y_km'])], color=color, lw=1.1, alpha=.85, zorder=2)
        ax.scatter([float(events[i]['x']) for i in sorted(used_events)], [float(events[i]['y']) for i in sorted(used_events)], s=7, c='.12', edgecolors='none', zorder=3)
        ax.set_aspect('equal'); ax.set_xlabel('Local x (km)'); ax.set_ylabel('Local y (km)'); ax.grid(alpha=.17)
        ax.set_ylim(-33, 34)
    axes[0].set_xlim(-33, 13)
    axes[1].set_xlim(-6, 3); axes[1].set_ylim(17, 31)
    for channel, color in zip(CHANNELS, COLORS):
        x, y = map(float, positions[channel])
        axes[0].scatter([x], [y], marker='^', s=52, color=color, edgecolors='white', linewidths=.6, zorder=4)
        axes[0].annotate(channel, (x, y), xytext=(6 if x < 0 else -6, 7), textcoords='offset points', ha='left' if x < 0 else 'right', va='bottom', fontsize=7.5, color=color)
        if -6 <= x <= 3 and 17 <= y <= 31:
            axes[1].scatter([x], [y], marker='^', s=52, color=color, edgecolors='white', linewidths=.6, zorder=4)
    axes[0].add_patch(Rectangle((-6, 17), 9, 14, fill=False, lw=.7, ls='--', edgecolor='.45', zorder=0))
    axes[0].set_title('(a) Catalog subset and channels', fontsize=10)
    axes[1].set_title('(b) Northern detail', fontsize=10)
    fig.suptitle('Spatial support of normalized waveform differences', fontsize=12, y=.97)
    fig.text(.5, .922, '98 accepted pairs · 103 participating events · 1,092 catalog events', ha='center', fontsize=10)
    handles = [Line2D([], [], marker='o', ls='', color='.75', markersize=4, label='Catalog event'), Line2D([], [], marker='o', ls='', color='.12', markersize=4, label='Event in accepted CC pair'), Line2D([], [], marker='^', ls='', color='.35', markersize=6, label='Receiving channel')]
    fig.legend(handles=handles, loc='lower center', bbox_to_anchor=(.5, .158), ncol=3, frameon=False, fontsize=8.5)
    handles = [Line2D([], [], color=color, lw=1.6, label='{} ({} pairs)'.format(channel, counts[channel])) for channel, color in zip(CHANNELS, COLORS)]
    fig.legend(handles=handles, loc='lower center', bbox_to_anchor=(.5, .093), ncol=2, frameon=False, fontsize=8.5)
    fig.text(.5, .066, 'Colored links join event pairs; they are not ray paths. Dashed extent in (a) marks panel (b).', ha='center', fontsize=8)
    fig.text(.5, .037, 'Input support only: no inference of rank, resolution, or inversion accuracy.', ha='center', fontsize=8)
    for ext, dpi in [('pdf', 300), ('png', 200)]:
        name = 'cc_spatial_support.' + ext
        sidecar = dict(figure=name, caption=CAPTION, full_identifiers='plot_identifiers.json.gz',
            full_identifiers_sha256=sha(out / 'plot_identifiers.json.gz'), plotted_table='plotted_event_pairs.csv',
            plotted_table_sha256=sha(out / 'plotted_event_pairs.csv'), input_source_sha256=dict(PINS))
        dump(out, name + '.identifiers.json', sidecar)
        fig.savefig(out / name, dpi=dpi, metadata={'Title': 'Spatial support of normalized waveform differences'})
        OUTPUTS.append(name)
    plt.close(fig)
    check(all(sha(ROOT / name) == expected for name, expected in PINS.items()), 'consumed inputs unchanged after plotting')
    python = Path(sys.executable).resolve()
    summary = dict(status='completed_saved_input_plot', started_utc=started,
        finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), pid=os.getpid(), pgid=os.getpgid(0),
        source_sha256=sha(Path(__file__).resolve()), input_source_sha256=PINS,
        output_sha256={name: sha(out / name) for name in OUTPUTS}, checks=dict(CHECKS),
        counts=dict(catalog_events=1092, accepted_events=103, accepted_pairs=98, receiving_channels=4, used_receiver_epochs=22, cross_epoch_pairs=cross, cc_only_components=32),
        accepted_channel_counts=dict(counts), channel_saved_positions_km=positions,
        axes=dict(panel_a=dict(x=[-33, 13], y=[-33, 34]), panel_b=dict(x=[-6, 3], y=[17, 31]), aspect='equal'),
        versions=dict(python=sys.version, matplotlib=matplotlib.__version__, python_executable=str(python), python_sha256=sha(python)),
        new_measurements=0, solver_calls=0, waveform_requests=0, graph_recomputations=0,
        caption=CAPTION, limits='Observed input support; no manuscript reproduction, rank, resolution or inverse-accuracy claim')
    dump(out, 'summary.json', summary)
    print(json.dumps(dict(status=summary['status'], counts=summary['counts'], summary_sha256=sha(out / 'summary.json')), sort_keys=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=HERE / 'result')
    args = parser.parse_args()
    check(not args.output.is_symlink(), 'output is not a symlink')
    out = args.output.resolve()
    check(ROOT in out.parents, 'project-local output')
    check(not out.exists(), 'fresh output')
    main(out)
