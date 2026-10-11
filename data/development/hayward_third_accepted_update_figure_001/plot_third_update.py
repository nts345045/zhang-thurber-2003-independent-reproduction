"""Plot preserved states only; read prior scientific tables directly from their published archive."""
import argparse
import collections
import csv
from fractions import Fraction as Q
import gzip
import hashlib
import io
import json
import math
import os
from pathlib import Path
import sys
import tarfile

SOURCE_DIR = Path(__file__).resolve().parent
ROOT = SOURCE_DIR.parents[2]
TITLE = 'Accepted update 3; run incomplete'
HERE = None
OUTPUTS = []


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''): h.update(block)
    return h.hexdigest()


def dump(name, obj, compressed=False):
    data = (json.dumps(obj, indent=2, sort_keys=True, allow_nan=False)+'\n').encode()
    if compressed: data = gzip.compress(data, mtime=0)
    with (HERE/name).open('xb') as stream: stream.write(data)
    OUTPUTS.append(name)


def read_rows(data):
    reader = csv.DictReader(io.StringIO(data.decode(), newline=''))
    assert reader.fieldnames and len(reader.fieldnames) == len(set(reader.fieldnames))
    result = list(reader)
    assert all(None not in r and None not in r.values() for r in result)
    return result


def value(text):
    x = float(text); assert math.isfinite(x)
    return Q(x)


def described(q):
    return {'exact_binary64_rational':str(q), 'display':float(q)}


def extrema(values, unit, keys):
    lo,hi = min(range(len(values)),key=values.__getitem__),max(range(len(values)),key=values.__getitem__)
    return {'unit':unit,'minimum':dict(described(values[lo]),row=keys[lo]),
            'maximum':dict(described(values[hi]),row=keys[hi]),'zero_count':sum(x==0 for x in values)}


def inputs():
    manifest = json.loads((SOURCE_DIR/'scientific_manifest.json').read_text())
    archive = manifest['prior_archive']; path = ROOT/archive['path']
    assert sha(path) == archive['sha256']
    assert sha(ROOT/archive['members_path']) == archive['members_sha256']
    inventory = json.loads((ROOT/archive['members_path']).read_text())['members']
    wanted = {r['member']:key for key,r in archive['members'].items()}; result = {}
    with tarfile.open(str(path),'r:gz') as stream:
        for item in stream:
            if item.name not in wanted: continue
            key = wanted[item.name]; record = archive['members'][key]
            assert key not in result and item.isfile() and item.size == record['bytes']
            assert inventory[item.name]['sha256'] == record['sha256']
            data = stream.extractfile(item).read()
            assert len(data) == item.size and hashlib.sha256(data).hexdigest() == record['sha256']
            result[key] = data
    assert set(result) == set(archive['members'])
    for key,record in manifest['input_files'].items():
        data = (SOURCE_DIR/record['path']).read_bytes()
        assert len(data) == record['bytes'] and hashlib.sha256(data).hexdigest() == record['sha256']
        result[key] = data
    previous = manifest['previous_package']
    assert sha(ROOT/previous['manifest_path']) == previous['manifest_sha256']
    previous_manifest = json.loads((ROOT/previous['manifest_path']).read_text())
    assert previous_manifest['accepted_update_ordinal'] == 2
    for key,record in previous['input_files'].items():
        old_record = previous_manifest['input_files'][key]
        assert record['sha256'] == old_record['sha256'] and record['bytes'] == old_record['bytes']
        data = (ROOT/record['path']).read_bytes()
        assert len(data) == record['bytes'] and hashlib.sha256(data).hexdigest() == record['sha256']
        assert key not in result; result[key] = data
    assert manifest['accepted_update_ordinal'] == 3 and manifest['accepted_iteration'] == 2
    assert manifest['accepted_trial'] == 3 and manifest['accepted_step_fraction'] == '0.125'
    trials = read_rows(result['accepted_trials'])
    assert len(trials) == 4 and [r['trial'] for r in trials] == ['0','1','2','3']
    assert all(r['iteration'] == '2' and r['stage'] == '0' for r in trials)
    assert all(r['status'] == 'local_stopping_rejected' and r['objective_evaluated'] == '0' for r in trials[:-1])
    assert trials[-1] == manifest['accepted_trial_record']
    assert trials[-1]['status'] == 'accepted' and trials[-1]['step_fraction'] == '0.125'
    assert trials[-1]['objective_before'] == manifest['fixed_weight_objective_before'] == '1253.1810003788601'
    assert trials[-1]['objective_after'] == manifest['fixed_weight_objective_after'] == '978.00644322787343'
    solve = read_rows(result['solve_context']); rejection = read_rows(result['rejection_context'])
    assert len(solve) == len(rejection) == 1
    assert solve[0] == manifest['next_solve_context'] and solve[0]['iteration'] == '3'
    assert solve[0]['objective_before'] == manifest['next_iteration_weighted_objective'] == '973.55329487224935'
    assert rejection[0] == manifest['rejection_context'] and rejection[0]['iteration'] == '3'
    assert rejection[0]['message'].startswith('Inverse forward evaluation rejected 394 rays;')
    assert result['third_grid'] == result['third_solve_grid']
    return manifest,result


def main():
    global HERE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,help='Fresh output directory inside this checkout')
    args = parser.parse_args(); HERE = Path(args.output).absolute()
    assert not HERE.exists() and not HERE.is_symlink()
    assert ROOT.resolve() in HERE.parent.resolve().parents or HERE.parent.resolve() == ROOT.resolve()
    HERE.mkdir(parents=True)
    for key,subdir in [('MPLCONFIGDIR','cache/matplotlib'),('XDG_CACHE_HOME','cache/xdg'),('TMPDIR','tmp')]:
        path = HERE/subdir; path.mkdir(parents=True); os.environ[key] = str(path)
    os.environ['MPLBACKEND'] = 'Agg'
    assert os.environ.get('PYTHONDONTWRITEBYTECODE') == '1'
    manifest,data = inputs()
    initial = read_rows(data['second_events']); accepted = read_rows(data['third_events'])
    original = read_rows(data['initial_events']); stations = read_rows(data['stations'])
    g0,g1 = read_rows(data['second_grid']),read_rows(data['third_grid'])
    assert len(initial) == len(accepted) == len(original) == 1092 and len(stations) == 372 and len(g0) == len(g1) == 462
    for i,(a,b,c) in enumerate(zip(initial,accepted,original)):
        assert a['id'] == b['id'] == c['id'] == str(i)
        assert all(a[k] == b[k] == c[k] for k in c if k not in ('x','y','z','t'))
        assert a['coordinate_basis'] == 'independent last accepted inversion state, or starting state before the first accepted update'
        assert b['coordinate_basis'] == 'independent last accepted inversion state, or starting state before the first accepted update'
    solve_events = read_rows(data['third_solve_events']); assert len(solve_events) == len(accepted)
    for a,b in zip(accepted,solve_events):
        assert list(a) == list(b) and all(a[k] == b[k] for k in a if k != 'coordinate_basis')
        assert b['coordinate_basis'] == 'independent accepted inversion state at iteration 3; original unscaled solve recorded separately'
    for a,b in zip(g0,g1):
        assert all(value(a[k]) == value(b[k]) for k in 'xyz') and value(a['v']) > 0 and value(b['v']) > 0
    axes = {k:sorted(set(value(r[k]) for r in g0)) for k in 'xyz'}
    assert [tuple(value(r[k]) for k in 'xyz') for r in g0] == [(x,y,z) for z in axes['z'] for y in axes['y'] for x in axes['x']]
    depth = Q(8); layer = [i for i,r in enumerate(g0) if value(r['z']) == depth]; assert len(layer) == 77
    pairs = read_rows(gzip.decompress(data['native_pairs'])); refs = read_rows(gzip.decompress(data['catalog_refs']))
    pair_map = {(int(r['event']),int(r['station'])):r for r in pairs}
    assert len(pair_map) == len(pairs) == 14262 and len(refs) == 103698
    common = ['network_code','station_code','location_code','channel_code','channel_seed_id','channel_fdsn_source_id','metadata_epoch_start','metadata_epoch_end']
    for (e,s),r in pair_map.items():
        assert r['native_flat_index'] == str(e*len(stations)+s) and stations[s]['id'] == str(s)
        assert all(r[k] == initial[e][k] == accepted[e][k] for k in ['event_resource_id','origin_resource_id'])
        assert all(r[k] == stations[s][k] for k in common)
    use_counts,absolute_counts = collections.Counter(),collections.Counter()
    seen = set()
    for r in refs:
        key = (int(r['event']),int(r['station'])); row_side=(int(r['observation_index']),r['side'])
        assert key in pair_map and row_side not in seen and r['type'] in ('0','1') and r['side'] in ('i','j')
        seen.add(row_side); use_counts[key] += 1; absolute_counts[key] += int(r['type']=='0')
    observation_count = len(set(q for q,side in seen)); assert observation_count == 58980
    for key,r in pair_map.items(): assert int(r['catalog_uses']) == use_counts[key] and int(r['absolute_uses']) == absolute_counts[key] == 1
    del refs,seen
    deltas = [{k:value(b[k])-value(a[k]) for k in 'xyzt'} for a,b in zip(initial,accepted)]
    dv = [value(b['v'])-value(a['v']) for a,b in zip(g0,g1)]
    event_records = []
    for e,(a,b,c,d) in enumerate(zip(initial,accepted,original,deltas)):
        assert all(axes[k][0] <= value(b[k]) <= axes[k][-1] for k in 'xyz')
        event_records.append({'event':e,'initial':c,'second_accepted':a,'third_accepted':b,
            'second_binary64_hex':{k:float(a[k]).hex() for k in 'xyzt'},'third_binary64_hex':{k:float(b[k]).hex() for k in 'xyzt'},
            'third_minus_second_exact':{k:str(d[k]) for k in 'xyzt'}})
    grid_records = [{'node':i,'second_accepted':a,'third_accepted':b,'third_minus_second_v_exact':str(dv[i])}
                    for i,(a,b) in enumerate(zip(g0,g1))]
    mapping = {'title':TITLE,'comparison':'third accepted minus second accepted',
        'coordinate_basis':'Saved local x/y/z in km; native geographic coordinates remain identity metadata.',
        'events':event_records,'third_solve_event_snapshot':solve_events,'receiver_epochs':stations,'grid_nodes':grid_records,
        'native_pairs':dict(manifest['prior_archive']['members']['native_pairs'],archive=manifest['prior_archive']['path']),
        'catalog_row_side_refs':dict(manifest['prior_archive']['members']['catalog_refs'],archive=manifest['prior_archive']['path']),
        'authoritative_observations_sha256':manifest['authoritative_observations_sha256'],
        'scientific_manifest_sha256':sha(SOURCE_DIR/'scientific_manifest.json')}
    dump('native_identifiers.json.gz',mapping,compressed=True)
    horizontal2 = [d['x']**2+d['y']**2 for d in deltas]; spatial2=[d['x']**2+d['y']**2+d['z']**2 for d in deltas]
    stats = {'comparison':'third accepted minus second accepted','grid_shape_xyz':[len(axes[k]) for k in 'xyz'],
        'grid_axes_km_exact':{k:list(map(str,axes[k])) for k in 'xyz'},'grid_nodes':462,'plotted_depth_km_exact':str(depth),'plotted_nodes':77,
        'grid_delta_v_all':extrema(dv,'km/s',list(range(462))),'grid_delta_v_layer':extrema([dv[i] for i in layer],'km/s',layer),
        'event_count':1092,'receiver_epochs':372,'channel_seed_ids':len(set(r['channel_seed_id'] for r in stations)),
        'empty_location_epochs':sum(r['location_code']=='' for r in stations),'native_pairs':14262,'catalog_rows':observation_count,'catalog_side_uses':sum(use_counts.values()),
        'event_delta':{k:extrema([d[k] for d in deltas],'s' if k=='t' else 'km',list(range(1092))) for k in 'xyzt'},
        'horizontal_displacement_squared':extrema(horizontal2,'km^2',list(range(1092))),
        'spatial_displacement_squared':extrema(spatial2,'km^2',list(range(1092)))}
    for label,vals in [('horizontal',horizontal2),('spatial',spatial2)]:stats[label+'_displacement_display_km']=[math.sqrt(float(min(vals))),math.sqrt(float(max(vals)))]
    window=(-4,0,20,24)
    zoom=[i for i,r in enumerate(initial) if window[0]<=value(r['x'])<window[1] and window[2]<=value(r['y'])<window[3]]
    stats['detail_window_km']=list(window);stats['detail_event_ids']=zoom
    dump('statistics.json',stats)
    identity={'title':TITLE,'comparison':'third accepted minus second accepted','mapping_file':'native_identifiers.json.gz',
        'mapping_sha256':sha(HERE/'native_identifiers.json.gz'),'scientific_manifest_sha256':sha(SOURCE_DIR/'scientific_manifest.json'),
        'plot_source_sha256':sha(Path(__file__)),'statistics_sha256':sha(HERE/'statistics.json'),
        'event_resource_ids':[r['event_resource_id'] for r in accepted],'origin_resource_ids':[r['origin_resource_id'] for r in accepted],
        'receiver_epoch_identities':[{k:r[k] for k in ['id']+common} for r in stations],
        'vector_scale':'One native kilometre per plotted kilometre; no vector amplification.',
        'limitations':['Saved grid nodes only; no interpolation or solver calls.','No post-update RMS, final convergence, first-arrival or recovery claim.']}
    for ext in ['png','pdf']:dump('accepted_update_3_minus_2.'+ext+'.identifiers.json',dict(identity,expected_output='accepted_update_3_minus_2.'+ext,hash_binding='summary.json after closure'))
    import matplotlib
    import matplotlib.pyplot as plt
    from matplotlib.colors import Normalize
    from matplotlib.patches import Rectangle
    import numpy
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'axes.titlesize': 12,
                         'axes.spines.top': False, 'axes.spines.right': False, 'pdf.fonttype': 42})
    fig = plt.figure(figsize=(14.6, 6.7), facecolor='white')
    gs = fig.add_gridspec(1, 3, width_ratios=[1.35, 0.62, 1.0], left=.058, right=.97, bottom=.19, top=.80, wspace=.30)
    ax0, ax1, ax2 = [fig.add_subplot(gs[0, i]) for i in range(3)]
    lim = max(abs(float(dv[i])) for i in layer)
    colors = ax0.scatter([float(value(g0[i]['x'])) for i in layer], [float(value(g0[i]['y'])) for i in layer],
                         c=[float(dv[i]) for i in layer], s=22, cmap='RdBu_r', norm=Normalize(-lim, lim),
                         linewidths=.25, edgecolors='#ffffff')
    ax0.set(xlim=(-38, 38), ylim=(-33, 33), xlabel='Native x (km)', ylabel='Native y (km)',
            title='Velocity change at saved z = 8 km\n77 grid nodes; no interpolation')
    cb0 = fig.colorbar(colors, ax=ax0, orientation='horizontal', fraction=.07, pad=.13, aspect=28)
    cb0.set_label('Third − second accepted velocity (km/s)')
    xy = [(float(value(r['x'])), float(value(r['y']))) for r in initial]
    uv = [(float(d['x']), float(d['y'])) for d in deltas]
    mag = [math.sqrt(float(q)) for q in horizontal2]
    norm = Normalize(0, max(mag))
    for ax, indices, size in [(ax1, list(range(1092)), 5), (ax2, zoom, 12)]:
        x, y = [xy[i][0] for i in indices], [xy[i][1] for i in indices]
        dx, dy = [uv[i][0] for i in indices], [uv[i][1] for i in indices]
        ax.scatter(x, y, s=size, c='#a7a7a7', alpha=.6, linewidths=0, zorder=1)
        arrows = ax.quiver(x, y, dx, dy, [mag[i] for i in indices], cmap='viridis', norm=norm,
                          angles='xy', scale_units='xy', scale=1, width=.0035, headwidth=3.5,
                          headlength=4, headaxislength=3.5, minlength=0, zorder=3)
        ax.set(xlabel='Native x (km)', ylabel='Native y (km)')
    ax1.set(xlim=(-11.5, 11.5), ylim=(-32, 32), title='All 1,092 events\nHorizontal displacement')
    ax1.add_patch(Rectangle((window[0], window[2]), window[1] - window[0], window[3] - window[2],
                            facecolor='none', edgecolor='#cc4422', linewidth=1.2))
    ax2.set(xlim=(-4.2, .2), ylim=(19.8, 24.2), title='Detail: {} events\nSame native distance scale for arrows'.format(len(zoom)))
    ax2.quiverkey(arrows, .77, -.105, .1, '0.1 km', labelpos='E', coordinates='axes', color='#343434')
    cb2 = fig.colorbar(arrows, ax=ax2, orientation='horizontal', fraction=.07, pad=.23, aspect=28)
    cb2.set_label('Horizontal displacement magnitude (km)')
    for ax in [ax0, ax1, ax2]:
        ax.set_aspect('equal', adjustable='box')
        ax.grid(True, color='#e3e7eb', linewidth=.55, zorder=0)
        ax.set_axisbelow(True)
    fig.suptitle(TITLE, x=.058, y=.952, ha='left', fontsize=21, fontweight='bold', color='#172735')
    fig.text(.058, .887, 'Third accepted state compared with the second; iteration 2, trial 3, step fraction 1/8', fontsize=12, color='#405463')
    fig.text(.058, .039, 'Gray dots: second accepted events. Arrows: third − second, without magnification. Red box: detail window.\n'
                        'Saved grid-node values only. This figure does not report post-update RMS or final convergence.', fontsize=9, color='#52606c')
    for ext in ['png', 'pdf']:
        path = HERE / ('accepted_update_3_minus_2.' + ext)
        assert not path.exists()
        metadata = {'Title': TITLE, 'Author': '', 'Subject': 'Third accepted update minus second; incomplete run'} if ext == 'pdf' else {'Title': TITLE, 'Description': 'Native saved coordinates; no interpolation or solver calls.'}
        fig.savefig(path, dpi=220, facecolor='white', metadata=metadata)
        OUTPUTS.append(path.name)
    plt.close(fig)
    assert sha(ROOT/manifest['prior_archive']['path']) == manifest['prior_archive']['sha256']
    assert sha(SOURCE_DIR/'scientific_manifest.json') == mapping['scientific_manifest_sha256']
    assert sha(Path(__file__)) == identity['plot_source_sha256']
    for record in manifest['input_files'].values(): assert sha(SOURCE_DIR/record['path']) == record['sha256']
    assert sha(ROOT/manifest['previous_package']['manifest_path']) == manifest['previous_package']['manifest_sha256']
    for record in manifest['previous_package']['input_files'].values(): assert sha(ROOT/record['path']) == record['sha256']
    result={'status':'completed_saved_update_visualization','title':TITLE,'comparison':'third accepted minus second accepted',
        'scientific_manifest_sha256':mapping['scientific_manifest_sha256'],'plot_source_sha256':sha(Path(__file__)),
        'readme_sha256':sha(SOURCE_DIR/'README.md'),'statistics':stats,
        'output_sha256':{name:sha(HERE/name) for name in OUTPUTS},
        'runtime_versions':{'python':sys.version.split()[0],'matplotlib':matplotlib.__version__,'numpy':numpy.__version__},
        'accepted_trial_record':manifest['accepted_trial_record'],'objective_scope':manifest['objective_scope'],
        'next_iteration_weighted_objective':manifest['next_iteration_weighted_objective'],
        'rejected_trial_scope':manifest['rejected_trial_scope'],
        'scope':identity['limitations'],'solver_calls':0,'integration_calls':0,'field_calls':0,'jacobian_calls':0,'fit_or_interpolation_calls':0}
    dump('summary.json',result)
    print(json.dumps({'status':result['status'],'summary_sha256':sha(HERE/'summary.json'),
        'png_sha256':sha(HERE/'accepted_update_3_minus_2.png'),'pdf_sha256':sha(HERE/'accepted_update_3_minus_2.pdf')}))


if __name__ == '__main__':
    if not __debug__: raise SystemExit("Refusing optimized Python: required identity and closure assertions are disabled")
    main()
