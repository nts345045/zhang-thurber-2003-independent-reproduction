#!/usr/bin/env python3
"""Geometry and exact one-sided face slopes of two saved rejected rays."""
import bisect
import csv
import hashlib
import json
from datetime import datetime
from fractions import Fraction as F
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
INPUT = ROOT / 'data/development/hayward_trial_cmj_old_D_replay_001/inputs'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    with path.open() as stream:
        return list(csv.DictReader(stream))


def main():
    if (OUT/'summary.json').exists() or (OUT/'near_face_nodes.csv').exists():
        raise RuntimeError('Use a fresh output package; preserve completed evidence')
    names = ['trial_grid.csv', 'original_paths.csv', 'original_status.csv']
    pins = {str((INPUT/name).relative_to(ROOT)): sha(INPUT/name) for name in names}
    grid, paths, status = [read(INPUT/name) for name in names]
    axes = {a: sorted({F(float(r[a])) for r in grid}) for a in 'xyz'}
    velocity = {tuple(F(float(r[a])) for a in 'xyz'): F(float(r['v'])) for r in grid}
    assert len(grid) == len(velocity) == 462
    assert axes['x'][5:8] == [F(-3), F(0), F(5)]

    def value(x, y, z):
        cells, weights = [], []
        for a, point in [('y', y), ('z', z)]:
            axis = axes[a]
            assert axis[0] <= point <= axis[-1]
            index = min(bisect.bisect_right(axis, point)-1, len(axis)-2)
            cells.append(axis[index:index+2])
            t = (point-axis[index])/(axis[index+1]-axis[index])
            weights.append([1-t, t])
        return sum(velocity[x, cells[0][j], cells[1][k]]*weights[0][j]*weights[1][k]
                   for j in (0, 1) for k in (0, 1))

    selected, results = [], []
    metadata = [k for k in paths[0] if k.startswith(('source_', 'receiver_'))]
    for original in status:
        event, station = int(original['event']), int(original['station'])
        rows = [r for r in paths if (int(r['event']), int(r['station'])) == (event, station)]
        assert station == 160 and event in (981, 987)
        assert len(rows) == int(original['ray_path_points'])
        assert [int(r['node']) for r in rows] == list(range(len(rows)))
        assert all(r[k] == original[k] for r in rows for k in metadata)
        near, distances, normal_pairs = [], [], []
        for r in rows[1:-1]:
            point = {a: F(float(r[a])) for a in 'xyz'}
            for a in 'xyz':
                distance, plane = min((abs(point[a]-plane), plane) for plane in axes[a][1:-1])
                distances.append((distance, int(r['node']), a, plane))
            # Descriptive selection only: one millimetre from the x=0 face.
            # It is neither a snapping operation nor a stationarity tolerance.
            if abs(point['x']) >= F(1, 1000000):
                continue
            vm, v0, vp = [value(F(x), point['y'], point['z']) for x in (-3, 0, 5)]
            left, right = (v0-vm)/3, (vp-v0)/5
            output = dict(r)
            output.update(face_x_km='0', projection_v_km_per_s=format(float(v0), '.17g'),
                          left_dv_dx_per_s=format(float(left), '.17g'),
                          right_dv_dx_per_s=format(float(right), '.17g'),
                          face_strict_velocity_maximum=str(int(left > 0 > right)))
            selected.append(output)
            near.append(r)
            normal_pairs.append((left, right))
        closest = min(distances)
        results.append({'event': event, 'station': station,
                        'native_context': {k: original[k] for k in metadata},
                        'path_points': len(rows), 'original_local_flag': original['ray_converged'],
                        'nearest_internal_plane': {'distance_km': float(closest[0]), 'node': closest[1],
                                                   'axis': closest[2], 'plane_km': float(closest[3])},
                        'node_axis_distances_below_km': {str(t): sum(float(d[0]) < t for d in distances)
                                                       for t in (1e-12, 1e-9, 1e-6, 1e-3)},
                        'nodes_with_abs_x_below_1e_minus6_km': len(near),
                        'selected_node_range': [min(int(r['node']) for r in near), max(int(r['node']) for r in near)],
                        'exact_positive_left_negative_right_count': sum(a > 0 > b for a, b in normal_pairs),
                        'left_dv_dx_range_per_s': [float(min(a for a, b in normal_pairs)), float(max(a for a, b in normal_pairs))],
                        'right_dv_dx_range_per_s': [float(min(b for a, b in normal_pairs)), float(max(b for a, b in normal_pairs))]})
    assert [r['event'] for r in results] == [981, 987]
    fields = list(paths[0]) + ['face_x_km', 'projection_v_km_per_s', 'left_dv_dx_per_s',
                             'right_dv_dx_per_s', 'face_strict_velocity_maximum']
    with (OUT/'near_face_nodes.csv').open('x', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        writer.writerows(selected)
    assert all(sha(ROOT/name) == digest for name, digest in pins.items())
    summary = {'status': 'completed_saved_geometry_calculation',
               'created_utc': datetime.utcnow().isoformat()+'Z',
               'scope': 'Saved failed paths and model only; no trace, field, optimizer, derivatives of ray travel time, inverse, or input mutation.',
               'arithmetic': 'Exact rational bilinear face interpolation and one-sided velocity slopes of the binary64 grid/coordinate values. CSV decimals round these rationals to binary64 for display; reported slope signs are exact for those inputs.',
               'selection': 'All internal nodes with abs(x)<1e-6 km (one millimetre) at the x=0 internal face; descriptive inventory, no path projection or stopping tolerance applied to the solver.',
               'input_sha256': pins, 'source_sha256': sha(Path(__file__)),
               'output_sha256': {'near_face_nodes.csv': sha(OUT/'near_face_nodes.csv')},
               'results': results,
               'interpretation': 'Every selected node projects to a strict local maximum of velocity across x=0: velocity rises from the left and falls on the right. The reciprocal-velocity integrand has a normal cusp minimum there. This identifies a nonsmooth feature adjacent to these two failed paths; it does not prove causation, stationarity, first-arrival accuracy, a common mechanism for181failures, or an optimizer correction.'}
    (OUT/'summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True)+'\n')
    print(json.dumps({'selected_nodes': len(selected), 'summary_sha256': sha(OUT/'summary.json')}))


if __name__ == '__main__':
    main()
