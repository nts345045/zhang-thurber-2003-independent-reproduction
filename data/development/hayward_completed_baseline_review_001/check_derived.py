#!/usr/bin/env python3
"""Read back event identities and interpolated resolution display values."""
import bisect
import csv
import hashlib
import json
import math
from pathlib import Path
import sys

sys.dont_write_bytecode = True
from check import ROOT, DATA, sha, table


def main():
    assert __debug__
    output = Path(__file__).with_name('derived_review.json')
    if output.exists():
        raise RuntimeError('Preserve existing review.')
    files = ['initial_events.csv', 'standard_events.csv', 'dd_events.csv', 'loc1d_events.csv',
             'dd_grid.csv', 'absolute_resolution.csv', 'resolution_sections.csv',
             'absolute_resolution_manifest.json', 'dd_linearization_rows.csv',
             'dd_linearization_columns.csv', 'figure_metrics.json']
    files += [m + s for m in ['initial', 'standard', 'dd', 'loc1d']
              for s in ['_geographic_events.csv', '_zoom_events.csv']]
    pins = {'data/hayward/' + f: sha(DATA / f) for f in files}
    for name in ['check.py', 'check_derived.py', 'review.json']:
        f = Path(__file__).with_name(name)
        pins[str(f.resolve().relative_to(ROOT))] = sha(f)
    initial = table('initial_events.csv')
    selected = {r['id'] for r in initial if 37.83 <= float(r['catalog_latitude_deg']) <= 37.91
                and -122.26 <= float(r['catalog_longitude_deg']) <= -122.18}
    assert len(selected) == 159
    modes = {}
    for mode in ['initial', 'standard', 'dd', 'loc1d']:
        original, geographic, zoom = [table(mode + suffix) for suffix in
                                      ['_events.csv', '_geographic_events.csv', '_zoom_events.csv']]
        assert len(original) == len(geographic) == 1092 and len(zoom) == 159
        for a, b in zip(original, geographic):
            assert all(b[k] == v for k, v in a.items())
            assert all(math.isfinite(float(b[k])) for k in ['estimated_latitude_deg', 'estimated_longitude_deg'])
            assert b['event_resource_id'] and b['origin_resource_id'] and b['source_sha256']
        assert zoom == [r for r in geographic if r['id'] in selected]
        modes[mode] = dict(geographic_rows=1092, zoom_rows=159,
                           all_original_fields_and_native_identifiers_exact=True,
                           zoom_exact_catalog_selected_subsequence=True)
    manifest = json.loads((DATA / 'absolute_resolution_manifest.json').read_text())
    for path, digest in manifest['input_sha256'].items():
        assert sha(ROOT / path) == digest
        pins[path] = digest
    assert manifest['source_mappings'] == dict(rows='data/hayward/dd_linearization_rows.csv',
                                               columns='data/hayward/dd_linearization_columns.csv')
    # These native row/column mappings are exhaustively checked in review.json.
    resolution, grid = table('absolute_resolution.csv'), table('dd_grid.csv')
    assert len(resolution) == len(grid) == 462
    axes = [sorted({float(r[k]) for r in grid}) for k in ['x', 'y', 'z']]
    values = {}
    for n, (r, g) in enumerate(zip(resolution, grid)):
        assert int(r['node']) == n and all(float(r[k]) == float(g[k]) for k in ['x', 'y', 'z', 'v'])
        values[tuple(float(r[k]) for k in ['x', 'y', 'z'])] = tuple(float(r[k]) for k in
            ['resolution_diagonal', 'independent_pick_sigma_velocity_km_s'])
    count, max_error = 0, [0.0, 0.0]
    with (DATA / 'resolution_sections.csv').open() as f:
        for r in csv.DictReader(f):
            point = [float(r[k]) for k in ['x', 'y', 'z']]
            weights = []
            for x, axis in zip(point, axes):
                assert axis[0] <= x <= axis[-1]
                j = max(0, min(len(axis) - 2, bisect.bisect_right(axis, x) - 1))
                t = (x - axis[j]) / (axis[j + 1] - axis[j])
                weights.append([(axis[j], 1 - t), (axis[j + 1], t)])
            calculated = [0.0, 0.0]
            for x, wx in weights[0]:
                for y, wy in weights[1]:
                    for z, wz in weights[2]:
                        for k in range(2):
                            calculated[k] += wx * wy * wz * values[x, y, z][k]
            for k, field in enumerate(['resolution_diagonal', 'independent_pick_sigma_velocity_km_s']):
                error = abs(calculated[k] - float(r[field]))
                assert error < 1e-12
                max_error[k] = max(max_error[k], error)
            count += 1
    assert count == 83895
    result = dict(status='passed_derived_identity_and_display_readback', input_sha256=pins,
                  main_review_sha256=sha(Path(__file__).with_name('review.json')),
                  modes=modes, resolution_node_count=462, resolution_section_count=count,
                  maximum_independent_interpolation_difference=max_error,
                  resolution_identity_chain='Model nodes and section interpolation points are derived quantities, not station/event records. The pinned manifest maps the estimator to fully identified absolute-data rows and event/model columns; those native mappings passed the main review.',
                  limits=['No covariance recomputation, optimizer, ray trace or first-arrival reference was run.',
                          'Resolution sections interpolate nodal standard deviations; they are not propagated covariance at interpolated points.',
                          'Geographic additions are finite estimates; this check verifies preservation and selection, not an independent geographic-projection or timestamp calculation.',
                          'No figure, plot source, PDF or Figure 4 manifest is consumed.'])
    for path, digest in pins.items():
        assert sha(ROOT / path) == digest, path
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'status': result['status'], 'review_sha256': sha(output)}))


if __name__ == '__main__':
    main()
