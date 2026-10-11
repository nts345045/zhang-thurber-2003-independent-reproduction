#!/usr/bin/env python3
"""Display a closed initial-model full-DD resolution and shared-pick covariance."""
import argparse
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import shutil

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            digest.update(block)
    return digest.hexdigest()


def read_json(path):
    return json.loads(path.read_text())


def basis(points, axes, node_lookup):
    """Full trilinear velocity basis, retaining saved node order."""
    cells, local = [], []
    for coordinate, axis in zip(points.T, axes):
        if np.any(coordinate < axis[0]) or np.any(coordinate > axis[-1]):
            raise ValueError('Display point outside model domain')
        cell = np.minimum(np.searchsorted(axis, coordinate, side='right') - 1, len(axis) - 2)
        cells.append(cell)
        local.append((coordinate - axis[cell]) / (axis[cell+1] - axis[cell]))
    ids, weights = [], []
    for k in (0, 1):
        for j in (0, 1):
            for i in (0, 1):
                ids.append(node_lookup[cells[0]+i, cells[1]+j, cells[2]+k])
                weights.append((local[0] if i else 1-local[0]) *
                               (local[1] if j else 1-local[1]) *
                               (local[2] if k else 1-local[2]))
    return np.stack(ids, axis=1), np.stack(weights, axis=1)


def propagated_variance(covariance, ids, weights):
    """Return w C w, with a declared floating-point cancellation allowance."""
    terms = weights[:, :, None] * covariance[ids[:, :, None], ids[:, None, :]] * weights[:, None, :]
    variance = terms.sum(axis=(1, 2))
    bound = 64 * np.finfo(float).eps * np.abs(terms).sum(axis=(1, 2))
    if np.any(variance < -bound) or not np.all(np.isfinite(variance)):
        raise ValueError('Interpolated covariance has materially negative/nonfinite variance')
    return np.maximum(variance, 0), int(np.count_nonzero(variance < 0))


def controls():
    ids = np.array([[0, 1]])
    weights = np.array([[.5, .5]])
    # Independent variances 1 and 4 give 1.25 at their midpoint. Perfectly
    # correlated errors of amplitude 1 and 2 instead give variance 2.25.
    assert propagated_variance(np.diag([1., 4.]), ids, weights)[0][0] == 1.25
    assert propagated_variance(np.array([[1., 2.], [2., 4.]]), ids, weights)[0][0] == 2.25
    axes = [np.array([0., 2.]), np.array([0., 4.]), np.array([0., 6.])]
    lookup = np.arange(8).reshape(2, 2, 2)
    node, weight = basis(np.array([[1., 2., 3.], [2., 4., 6.]]), axes, lookup)
    assert sorted(node[0]) == list(range(8)) and np.array_equal(weight[0], np.full(8, .125))
    assert node[1, np.argmax(weight[1])] == 7 and weight[1].max() == 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True,
                        help='Published scientific inventory, with data hashes relative to its parent')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not __debug__:
        raise ValueError('Run with Python assertions enabled')
    controls()
    data, out = args.data_dir, args.output
    receipt = read_json(args.manifest)
    if not (receipt['status'] == 'passed' and
            receipt['record_type'] == 'closed scientific output inventory'):
        raise ValueError('Expected the published closed scientific inventory')
    names = ['initial_full_resolution' + suffix for suffix in
             ('.csv', '_picks.csv', '_matrices.npz', '_manifest.json')]
    names += ['initial_full_dd_identifiers.json.gz', 'initial_full_dd_identifiers_manifest.json']
    pins = {}
    for name in names:
        path = data / name
        key = str(path.resolve().relative_to(args.manifest.parent.resolve()))
        pins[name] = sha(path)
        if receipt['output_sha256'][key] != pins[name]:
            raise ValueError('Closed artifact hash differs: ' + name)
    native = read_json(data / names[3])
    identity_manifest = read_json(data / names[5])
    if identity_manifest['identity_sha256'] != pins[names[4]]:
        raise ValueError('Identity companion changed')
    if (native['linearization_point'] != 'initial saved event/model state' or
            native['stage'] != 0 or native['ray_status_failures'] != 0):
        raise ValueError('Expected eligible initial model at explicit stage zero')
    with gzip.open(data / names[4], 'rt') as stream:
        identities = json.load(stream)
    with (data / names[0]).open(newline='') as stream:
        rows = list(csv.DictReader(stream))
    count = len(rows)
    if len(identities['model_nodes']) != count:
        raise ValueError('Model identity map has different dimensions')
    coordinates = np.array([[float(row[key]) for key in 'xyz'] for row in rows])
    velocity = np.array([float(row['v']) for row in rows])
    for k, (row, node) in enumerate(zip(rows, identities['model_nodes'])):
        if int(row['node']) != k or any(float(row[key]) != float(node[key]) for key in ('x', 'y', 'z', 'v')):
            raise ValueError('Saved node order differs from identity map')
    axes = [np.unique(coordinates[:, k]) for k in range(3)]
    lookup = np.full(tuple(map(len, axes)), -1, dtype=int)
    for k, point in enumerate(coordinates):
        index = tuple(np.searchsorted(axis, value) for axis, value in zip(axes, point))
        if lookup[index] != -1:
            raise ValueError('Duplicate grid node')
        lookup[index] = k
    if np.any(lookup < 0):
        raise ValueError('Incomplete tensor grid')
    with np.load(data / names[2], allow_pickle=False) as matrices:
        resolution = matrices['masked_log_slowness_resolution']
        response = matrices['unmasked_log_slowness_model_response']
        covariance_q = matrices['shared_pick_log_slowness_noise_covariance']
    for matrix in (resolution, response, covariance_q):
        if matrix.shape != (count, count) or not np.all(np.isfinite(matrix)):
            raise ValueError('Invalid model matrix')
    covariance_v = velocity[:, None] * covariance_q * velocity[None, :]
    if not np.array_equal(np.diag(resolution), np.array([float(row['masked_resolution_diagonal']) for row in rows])):
        raise ValueError('Resolution table and matrix disagree')
    x = np.linspace(axes[0][0], axes[0][-1], 141)
    z = np.linspace(axes[2][0], axes[2][-1], int(round((axes[2][-1]-axes[2][0])/.25))+1)
    xx, zz = np.meshgrid(x, z)
    sections, negative_roundoff = [], 0
    for y in range(-30, 31, 10):
        points = np.column_stack([xx.ravel(), np.full(xx.size, y), zz.ravel()])
        ids, weights = basis(points, axes, lookup)
        variance, negatives = propagated_variance(covariance_v, ids, weights)
        negative_roundoff += negatives
        sections.append(dict(y=y, points=points, node=ids, weight=weights,
                             resolution=(np.diag(resolution)[ids]*weights).sum(axis=1),
                             response=(np.diag(response)[ids]*weights).sum(axis=1),
                             sigma=np.sqrt(variance)))
    # No output is created before inventory, identity, and algebra checks.
    out.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(data / names[4], out / names[4])
    shutil.copyfile(data / names[5], out / names[5])
    fields = ['x', 'y', 'z', 'interpolated_nodal_masked_resolution_diagonal',
              'interpolated_nodal_unmasked_response_diagonal', 'interpolated_velocity_shared_pick_sigma_km_s']
    fields += ['node_' + str(k) for k in range(8)] + ['weight_' + str(k) for k in range(8)]
    with (out / 'sections.csv.gz').open('xb') as raw:
        with gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0) as compressed:
            with io.TextIOWrapper(compressed, encoding='utf-8', newline='') as stream:
                writer = csv.writer(stream); writer.writerow(fields)
                for section in sections:
                    for point, r, response, sigma, ids, weights in zip(section['points'], section['resolution'],
                            section['response'], section['sigma'], section['node'], section['weight']):
                        writer.writerow([*point, r, response, sigma, *ids, *weights])
    rmin = min(section['resolution'].min() for section in sections)
    rmax = max(section['resolution'].max() for section in sections)
    sigma_max = max(section['sigma'].max() for section in sections)
    extend = 'both' if rmin < 0 and rmax > 1 else 'min' if rmin < 0 else 'max' if rmax > 1 else 'neither'
    fig, panels = plt.subplots(7, 2, figsize=(10, 15), sharex=True, sharey=True, layout='constrained')
    for row, section in enumerate(sections):
        a = panels[row, 0].pcolormesh(xx, zz, section['resolution'].reshape(xx.shape),
                cmap='viridis', vmin=0, vmax=1, shading='auto', rasterized=True)
        b = panels[row, 1].pcolormesh(xx, zz, section['sigma'].reshape(xx.shape),
                cmap='magma', vmin=0, vmax=sigma_max, shading='auto', rasterized=True)
        for panel in panels[row]:
            panel.set_ylim(z[-1], z[0])
            panel.set_yticks([0, 5, 10, 15, 20])
        panels[row, 0].set_ylabel('Y = {} km\nGeoid depth (km)'.format(section['y']))
    for panel in panels[-1]:
        panel.set_xlabel('X northeast (km)')
    panels[0, 0].set_title('Masked nodal resolution\n(diagonal interpolated for display)')
    panels[0, 1].set_title('Picking-noise standard deviation\n(full covariance propagated to each point)')
    fig.colorbar(a, ax=panels[:, 0].tolist(), shrink=.7, label='Interpolated nodal diagonal', extend=extend)
    fig.colorbar(b, ax=panels[:, 1].tolist(), shrink=.7, label='Velocity standard deviation (km/s)')
    fig.suptitle('Initial-model catalog-DD resolution and shared-pick noise\n'
                 'Stage 0; fixed weights, masks, smoothing and damping', fontsize=14)
    fig.savefig(out / 'initial_full_dd_resolution.pdf', metadata={'CreationDate': None, 'ModDate': None})
    fig.savefig(out / 'initial_full_dd_resolution.png', dpi=150)
    plt.close(fig)
    manifest = dict(scope='INITIAL saved model, stage 0, catalog only; no final-model covariance claim',
        input_sha256=pins, scientific_inventory_sha256=sha(args.manifest), plot_script_sha256=sha(Path(__file__)),
        model_nodes=count, section_points=sum(len(section['points']) for section in sections),
        section_y_km=[section['y'] for section in sections],
        covariance_display='Cv=diag(v) Cq diag(v); sigma(point)=sqrt(w Cv w). Nodal sigmas are not interpolated.',
        resolution_display='The saved nodal resolution diagonal is interpolated for display, not redefined as pointwise resolution.',
        identity_map='Both copied companions retain contributing event/origin/pick/channel/epoch IDs and matrix node order. Each section row saves its eight node indices and basis weights.',
        artifact_identity_maps={
            'sections.csv.gz': 'node_0 through node_7 index model_nodes in initial_full_dd_identifiers.json.gz; weight_0 through weight_7 give the full velocity basis. All contributing native observation identities remain in that companion.',
            'initial_full_dd_resolution.pdf': 'Rendered from sections.csv.gz; all contributor identities are in initial_full_dd_identifiers.json.gz.',
            'initial_full_dd_resolution.png': 'Rendered from sections.csv.gz; all contributor identities are in initial_full_dd_identifiers.json.gz.'},
        noise_assumption=identities['noise_assumption'], limitations=native['limitations'],
        negative_variances_within_roundoff_allowance=negative_roundoff,
        variance_roundoff_allowance='64 binary64 eps times sum of absolute quadratic-form terms; values within this allowance are displayed as zero.',
        resolution_range=[float(rmin), float(rmax)], sigma_max_km_s=float(sigma_max),
        masked_diagonal_color_limits=[0, 1], colorbar_extend=extend,
        controls='Independent two-variable covariance and tensor-basis midpoint/endpoint checks passed before input reads.')
    manifest['output_sha256'] = {path.name: sha(path) for path in out.iterdir() if path.is_file()}
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2, allow_nan=False)+'\n')
    print(json.dumps({key: manifest[key] for key in ('model_nodes', 'section_points', 'resolution_range', 'sigma_max_km_s')}))


if __name__ == '__main__':
    main()
