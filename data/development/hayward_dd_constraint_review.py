#!/usr/bin/env python3
"""Inspect saved DD constraints without tracing rays or changing solver inputs.

Run from the repository root: python3 data/development/hayward_dd_constraint_review.py
Writes only the adjacent event/ray CSVs and review JSON. Geometry SVDs are explicitly
straight-direction proxies, not derivatives of the heterogeneous ray model.
"""
import csv
import datetime
import hashlib
import json
import math
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr


D = Path('data/hayward')
OUT = Path('data/development')
NS = {'q': 'http://quakeml.org/xmlns/bed/1.2'}


def read(path):
    with path.open(newline='') as f:
        return list(csv.DictReader(f))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def component_sizes(neighbors):
    size = [0] * len(neighbors)
    components = []
    for start in range(len(neighbors)):
        if size[start]:
            continue
        seen = {start}
        todo = [start]
        while todo:
            node = todo.pop()
            for other in neighbors[node]:
                if other not in seen:
                    seen.add(other)
                    todo.append(other)
        components.append(len(seen))
        for node in seen:
            size[node] = len(seen)
    return size, sorted(components, reverse=True)


def geometry(position, receiver_positions):
    # Deduplicate physical coordinates only for this geometric description.
    points = np.array(sorted(set(tuple(p) for p in receiver_positions)))
    difference = points - position
    horizontal = np.linalg.norm(difference[:, :2], axis=1)
    distance = np.linalg.norm(difference, axis=1)
    azimuth = np.sort(np.mod(np.arctan2(difference[:, 1], difference[:, 0]), 2 * np.pi))
    gaps = np.diff(np.r_[azimuth, azimuth[0] + 2 * np.pi])
    result = dict(unique_receiver_positions=len(points),
                  azimuthal_gap_deg=float(np.max(gaps) * 180 / np.pi),
                  horizontal_distance_min_km=float(np.min(horizontal)),
                  horizontal_distance_median_km=float(np.median(horizontal)),
                  horizontal_distance_max_km=float(np.max(horizontal)))
    if np.any(distance == 0):
        result.update(direction_z_std=None, direction_time_singular_ratio=None)
        return result
    direction = difference / distance[:, None]
    singular = np.linalg.svd(np.column_stack([direction, np.ones(len(points))]), compute_uv=False)
    result['direction_z_std'] = float(np.std(direction[:, 2]))
    result['direction_time_singular_ratio'] = float(singular[-1] / singular[0]) if len(singular) == 4 else 0.
    return result


def main():
    initial = read(D / 'initial_events.csv')
    final = read(D / 'dd_events.csv')
    stations = read(D / 'stations.csv')
    observations = read(D / 'observations.csv')
    residuals = read(D / 'dd_residuals.csv')
    assert len(initial) == len(final)
    assert len(observations) == len(residuals)
    assert all(a['event_resource_id'] == b['event_resource_id'] and
               a['origin_resource_id'] == b['origin_resource_id'] for a, b in zip(initial, final))
    for a, b in zip(observations, residuals):
        assert all(a[k] == b[k] for k in a if k != 'value')
    config = {}
    for line in Path('configs/hayward.cfg').read_text().splitlines():
        words = line.split('#')[0].split()
        if words:
            config[words[0]] = float(words[1])
    assert config['catalog_only_dd'] == 1
    assert not any(int(row['type']) == 2 for row in observations)
    stage = [config.get('stage3_absolute_weight', .1),
             config.get('stage3_catalog_weight', 1.)]
    cutoff = {}
    for kind in [0, 1]:
        values = sorted(abs(float(r['residual'])) for r in residuals if int(r['type']) == kind)
        cutoff[kind] = max(.01, 6 * 1.4826 * values[len(values) // 2])
    ne = len(initial)
    source = np.array([[float(r[k]) for k in ['x', 'y', 'z']] for r in final])
    origin = np.array([[float(r[k]) for k in ['x', 'y', 'z']] for r in initial])
    receiver = np.array([[float(r[k]) for k in ['x', 'y', 'z']] for r in stations])
    top_layer_rows = []
    top_layer_count = [0] * ne
    initial_top_layer_count = 0
    for index, observation in enumerate(observations):
        if int(observation['type']) != 0:
            continue
        i, station = int(observation['i']), int(observation['station'])
        receiver_in_layer = -1 <= receiver[station, 2] <= 0
        initial_top_layer_count += int(receiver_in_layer and -1 <= origin[i, 2] <= 0)
        if receiver_in_layer and -1 <= source[i, 2] <= 0:
            row = dict(observation)
            row['observation_index'] = index
            for axis, name in enumerate(['x', 'y', 'z']):
                row['dd_source_' + name + '_km'] = float(source[i, axis])
                row['receiver_' + name + '_km'] = float(receiver[station, axis])
            row['dd_residual_s'] = residuals[index]['residual']
            top_layer_rows.append(row)
            top_layer_count[i] += 1
    top_layer_csv = OUT / 'hayward_dd_top_layer_rays.csv'
    with top_layer_csv.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(top_layer_rows[0]))
        writer.writeheader()
        writer.writerows(top_layer_rows)
    top_layer_grids = {}
    for name in ['initial', 'dd']:
        grid_rows = read(D / (name + '_grid.csv'))
        lower = {(r['x'], r['y']): float(r['v']) for r in grid_rows if float(r['z']) == -1}
        upper = {(r['x'], r['y']): float(r['v']) for r in grid_rows if float(r['z']) == 0}
        differences = [upper[key] - value for key, value in lower.items()]
        top_layer_grids[name] = dict(vertical_node_pairs=len(differences),
                                    exactly_equal_velocity_pairs=sum(v == 0 for v in differences),
                                    v_at_zero_minus_v_at_minus1_min_max_km_s=[min(differences), max(differences)])
    input_neighbors = [set() for _ in final]
    active_neighbors = [set() for _ in final]
    absolute = [[] for _ in final]
    differential = [[] for _ in final]
    weights = []
    reason_counts = dict(absolute_residual_cutoff_zero=0, catalog_residual_cutoff_zero=0,
                         catalog_distance_cutoff_zero=0, absolute_active=0, catalog_active=0)
    for index, (observation, residual) in enumerate(zip(observations, residuals)):
        i, j, kind = [int(observation[k]) for k in ['i', 'j', 'type']]
        value = float(residual['residual'])
        assert math.isfinite(value)
        robust = max(0., 1 - (value / cutoff[kind]) ** 2) ** 2
        distance_weight = 1.
        if j >= 0:
            distance_weight = max(0., 1 - (np.linalg.norm(source[i] - source[j]) /
                                         config['pair_distance']) ** 2) ** 2
        weight = stage[kind] * float(observation['a_priori_weight']) * robust * distance_weight
        active = weight >= 1e-12  # Exactly the solver's row-inclusion rule.
        weights.append(weight)
        if kind == 0:
            absolute[i].append((index, weight))
            reason_counts['absolute_residual_cutoff_zero'] += robust == 0
            reason_counts['absolute_active'] += active
        else:
            differential[i].append((index, weight))
            differential[j].append((index, weight))
            input_neighbors[i].add(j)
            input_neighbors[j].add(i)
            if active:
                active_neighbors[i].add(j)
                active_neighbors[j].add(i)
            reason_counts['catalog_residual_cutoff_zero'] += robust == 0
            reason_counts['catalog_distance_cutoff_zero'] += distance_weight == 0
            reason_counts['catalog_active'] += active
    input_component, input_sizes = component_sizes(input_neighbors)
    active_component, active_sizes = component_sizes(active_neighbors)

    quality_paths = {
        'provider_depth_uncertainty_m': 'depth/uncertainty',
        'provider_origin_time_uncertainty_s': 'time/uncertainty',
        'provider_horizontal_uncertainty_m': 'originUncertainty/horizontalUncertainty',
        'provider_origin_confidence_level_percent': 'originUncertainty/confidenceLevel',
        'provider_ellipsoid_major_axis_m': 'originUncertainty/confidenceEllipsoid/semiMajorAxisLength',
        'provider_ellipsoid_minor_axis_m': 'originUncertainty/confidenceEllipsoid/semiMinorAxisLength',
        'provider_ellipsoid_intermediate_axis_m': 'originUncertainty/confidenceEllipsoid/semiIntermediateAxisLength',
        'provider_ellipsoid_major_axis_plunge_deg': 'originUncertainty/confidenceEllipsoid/majorAxisPlunge',
        'provider_standard_error_s': 'quality/standardError',
        'provider_azimuthal_gap_deg': 'quality/azimuthalGap',
        'provider_used_phase_count': 'quality/usedPhaseCount',
        'provider_used_station_count': 'quality/usedStationCount',
        'provider_location_method_id': 'methodID'}
    archived = {}
    quality = {}
    by_file = defaultdict(list)
    for row in initial:
        by_file[row['source_file']].append(row)
    for name, events in by_file.items():
        path = D / name
        archived[str(path)] = sha(path)
        assert all(archived[str(path)] == e['source_sha256'] for e in events)
        tree = ET.parse(str(path))
        origins = {o.attrib['publicID']: o for o in tree.findall('.//q:origin', NS)}
        for event in events:
            node = origins[event['origin_resource_id']]
            fields = {}
            for name, relative in quality_paths.items():
                value = node.find('/'.join('q:' + segment for segment in relative.split('/')), NS)
                fields[name] = value.text if value is not None and value.text else ''
            quality[event['origin_resource_id']] = fields
    grid = read(D / 'initial_grid.csv')
    bounds = {k: [min(float(r[k]) for r in grid), max(float(r[k]) for r in grid)] for k in ['x', 'y', 'z']}
    displacement = np.linalg.norm(source - origin, axis=1)
    records = []
    for i, event in enumerate(final):
        row = dict(event)
        row.update(quality[event['origin_resource_id']])
        row['catalog_displacement_3d_km'] = float(displacement[i])
        for k, axis in enumerate(['x', 'y', 'z']):
            row['catalog_displacement_' + axis + '_km'] = float(source[i, k] - origin[i, k])
            row[axis + '_lower_boundary'] = int(source[i, k] <= bounds[axis][0] + 1e-6)
            row[axis + '_upper_boundary'] = int(source[i, k] >= bounds[axis][1] - 1e-6)
        row['negative_geoid_depth'] = int(source[i, 2] < 0)
        row['both_endpoints_top_layer_absolute_rays'] = top_layer_count[i]
        row['input_pair_degree'] = len(input_neighbors[i])
        row['final_active_pair_degree'] = len(active_neighbors[i])
        row['input_component_size'] = input_component[i]
        row['final_active_component_size'] = active_component[i]
        for name, entries in [('absolute', absolute[i]), ('catalog', differential[i])]:
            row[name + '_row_count'] = len(entries)
            row[name + '_final_active_row_count'] = sum(weight >= 1e-12 for _, weight in entries)
            row[name + '_final_sum_squared_weights'] = sum(weight * weight for _, weight in entries)
            row[name + '_final_residual_rms_s'] = (math.sqrt(sum(float(residuals[n]['residual']) ** 2 for n, _ in entries) / len(entries)) if entries else '')
        station_indices = sorted(set(int(observations[n]['station']) for n, _ in absolute[i]))
        for label, position in [('initial', origin[i]), ('final', source[i])]:
            for key, value in geometry(position, receiver[station_indices]).items():
                row[label + '_' + key] = value
        row['absolute_receiver_epochs_json'] = json.dumps([
            {k: stations[s][k] for k in ['id', 'channel_seed_id', 'channel_fdsn_source_id',
                                         'metadata_epoch_start', 'metadata_epoch_end', 'source_sha256']}
            for s in station_indices], separators=(',', ':'))
        records.append(row)
    output_csv = OUT / 'hayward_dd_event_constraints.csv'
    with output_csv.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)

    def group(indices):
        return dict(events=len(indices),
                    displacement_median_km=float(np.median(displacement[indices])) if indices else None,
                    displacement_maximum_km=float(np.max(displacement[indices])) if indices else None,
                    negative_geoid_depths=sum(records[i]['negative_geoid_depth'] for i in indices),
                    top_boundary_sources=sum(records[i]['z_lower_boundary'] for i in indices),
                    input_unlinked=sum(not input_neighbors[i] for i in indices),
                    final_active_unlinked=sum(not active_neighbors[i] for i in indices))
    groups = {'all': group(list(range(ne))),
              'input_unlinked': group([i for i in range(ne) if not input_neighbors[i]]),
              'input_linked': group([i for i in range(ne) if input_neighbors[i]]),
              'negative_geoid_depth': group([i for i in range(ne) if source[i, 2] < 0]),
              'top_boundary': group([i for i in range(ne) if records[i]['z_lower_boundary']]),
              'upper_y_boundary': group([i for i in range(ne) if records[i]['y_upper_boundary']])}
    correlations = {}
    for name in ['input_pair_degree', 'final_active_pair_degree', 'absolute_row_count',
                 'absolute_final_active_row_count', 'initial_azimuthal_gap_deg',
                 'initial_horizontal_distance_min_km', 'initial_direction_z_std',
                 'initial_direction_time_singular_ratio', 'provider_depth_uncertainty_m',
                 'provider_horizontal_uncertainty_m', 'provider_ellipsoid_major_axis_m']:
        indices = [i for i in range(ne) if records[i][name] not in ['', None]]
        values = [float(records[i][name]) for i in indices]
        rho = float(spearmanr(values, displacement[indices])[0]) if len(set(values)) > 1 else None
        correlations[name] = {'available_events': len(indices), 'spearman_rho_with_displacement': rho}
    inputs = ['initial_events.csv', 'initial_grid.csv', 'stations.csv', 'observations.csv',
              'dd_events.csv', 'dd_grid.csv', 'dd_residuals.csv', 'dd_history.csv',
              'selection_manifest.json', 'run_manifest.json']
    files = {str(D / name): sha(D / name) for name in inputs}
    files.update({name: sha(Path(name)) for name in ['src/main.cpp', 'src/core.hpp',
                  'src/ray_checks.hpp', 'configs/hayward.cfg', str(Path(__file__)),
                  str(output_csv), str(top_layer_csv)]})
    files.update(archived)
    result = dict(reviewed_utc=datetime.datetime.utcnow().isoformat() + 'Z',
                  command='python3 data/development/hayward_dd_constraint_review.py',
                  event_rows=ne, final_stage_row_multipliers=stage,
                  reconstructed_final_residual_cutoff_s=cutoff,
                  reconstructed_final_weight_counts={k: int(v) for k, v in reason_counts.items()},
                  input_component_sizes=input_sizes, final_active_component_sizes=active_sizes,
                  groups=groups, descriptive_correlations=correlations,
                  per_event_csv=str(output_csv), sha256=files,
                  top_layer=dict(initial_both_endpoints_absolute_rays=initial_top_layer_count,
                                 dd_final_both_endpoints_absolute_rays=len(top_layer_rows),
                                 dd_final_events=sum(n > 0 for n in top_layer_count),
                                 dd_final_native_receiver_epochs=len(set(r['station'] for r in top_layer_rows)),
                                 grids=top_layer_grids, identified_ray_csv=str(top_layer_csv)),
                  largest_displacement_event_indices=[int(i) for i in np.argsort(displacement)[::-1][:10]],
                  limitations=[
                      'Final weights are reconstructed at the saved final model; they are the weights a further final-stage solve would form, not the unavailable pre-update weights of the last accepted step.',
                      'Active uses the existing solver threshold weight >= 1e-12. Boundary counts use the existing 1e-6 km reporting tolerance; no new selection or physical constraint is applied.',
                      'Straight source-to-receiver direction SVDs are dimensionless geometric proxies using unique receiver coordinates. They are not heterogeneous ray derivatives, covariance, or a rank certification of the coupled DD matrix.',
                      'The 186 final-DD top-layer endpoint geometries identify candidates for a first-arrival branch comparison. The DD top layer is not exactly constant, so the flat-layer counterexample alone does not prove their traced arrivals are wrong.',
                      'Spearman coefficients and group summaries describe associations and establish no causal explanation for displacement.',
                      'Catalog displacement is not location error against truth. Negative geoid depth does not establish height relative to local terrain.',
                      'Archived provider uncertainties and their stated confidence fields are preserved without assuming Gaussian calibration or comparable confidence levels.',
                      'No intermediate event checkpoints were saved, so individual events responsible for each history maximum coordinate step cannot be identified from final outputs alone.',
                      'No solver run, ray tracing, observational query, production analysis, or active source/input/configuration mutation was performed.'])
    (OUT / 'hayward_dd_constraint_review.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ['sha256', 'limitations']}, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
