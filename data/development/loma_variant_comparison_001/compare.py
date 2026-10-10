#!/usr/bin/env python3
"""Compare every saved LOM/LON byte after both exhaustive audits have passed."""
import csv
import difflib
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
RUNS = [ROOT / 'data/loma_lom_analytic_001', ROOT / 'data/loma_lon_analytic_001']


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


def inventory(run):
    review = json.loads((run / 'independent_simulation_review.json').read_text())
    ledger = json.loads((run / 'simulation_execution.json').read_text())
    require(review['status'] == 'passed' and ledger['status'] == 'completed' and
            ledger['return_code'] == 0, 'Both terminal simulations must pass their full audit')
    require(all(review[k] is True for k in ('all_native_fields_match',
            'truth_status_all_fields_exact', 'ray_status_fields_blank')), 'Incomplete output audit')
    paths = sorted(run.rglob('*'))
    require(not any(p.is_symlink() for p in paths), 'Unexpected symbolic link')
    require(all(p.is_file() or p.is_dir() for p in paths), 'Unexpected nonregular artifact')
    members = {p.relative_to(run).as_posix(): dict(bytes=p.stat().st_size, sha256=sha(p))
               for p in paths if p.is_file()}
    for name, digest in review['input_sha256'].items():
        require(members[name]['sha256'] == digest, 'Reviewed file changed: ' + name)
    for name, digest in ledger['output_sha256'].items():
        require(review['input_sha256'][name] == digest, 'Unreviewed terminal output: ' + name)
    for name, key in [('simulation_execution.json', 'simulation_execution_sha256'),
                      ('simulation_run_manifest.json', 'simulation_run_manifest_sha256')]:
        require(members[name]['sha256'] == review[key], 'Review linkage differs: ' + name)
    require(review['arrival_count'] == 37648 and review['total_observations'] == 15932384 and
            review['observation_counts_by_type'] == [37648, 7947368, 7947368], 'Cohort support changed')
    return members, review


def table(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def configuration(path):
    return dict(line.split('#', 1)[0].split() for line in path.read_text().splitlines()
                if line.split('#', 1)[0].strip())


def main():
    target = OUT / 'comparison.json'
    require(not target.exists(), 'Preserve the prior comparison')
    (a, ar), (b, br) = [inventory(run) for run in RUNS]
    base = ROOT / 'data/published/loma_lom_analytic_001'
    published = json.loads((base / 'manifest.json').read_text())
    verified = json.loads((base / 'verification.json').read_text())
    require(published['status'] == 'verified' and published['members'] == a and
            verified['status'] == 'passed' and verified['manifest_sha256'] == sha(base / 'manifest.json'),
            'LOM files do not exactly match the verified base package')
    members = {name: dict(lom=a.get(name), lon=b.get(name), byte_identical=a.get(name) == b.get(name))
               for name in sorted(set(a) | set(b))}
    grids = [table(run / 'initial_grid.csv') for run in RUNS]
    require(len(grids[0]) == len(grids[1]) and all(tuple(x[k] for k in 'xyz') ==
            tuple(y[k] for k in 'xyz') for x, y in zip(*grids)), 'Grid coordinates or order differ')
    profiles = []
    for grid in grids:
        profile = {}
        for row in grid:
            profile.setdefault(row['z'], set()).add(row['v'])
        require(all(len(v) == 1 for v in profile.values()), 'Initial grid is not depth-only')
        profiles.append({z: next(iter(v)) for z, v in profile.items()})
    config_differences = {}
    for name in ('run.cfg', 'preflight.cfg'):
        left, right = [configuration(run / name) for run in RUNS]
        config_differences[name] = {k: dict(lom=left.get(k), lon=right.get(k))
                                   for k in sorted(set(left) | set(right)) if left.get(k) != right.get(k)}
        diff = ''.join(difflib.unified_diff((RUNS[0] / name).read_text().splitlines(True),
                       (RUNS[1] / name).read_text().splitlines(True), 'LOM/' + name, 'LON/' + name))
        with (OUT / (name + '.diff')).open('x') as stream:
            stream.write(diff)
    physical = ['truth_events.csv', 'initial_events.csv', 'arrivals.csv', 'observations.csv',
                'simulation_truth_status.csv', 'simulation_truth_mode.txt']
    reusable = [name for name in b if a.get(name) == b[name]]
    separate = [name for name in b if a.get(name) != b[name]]
    manifests = [json.loads((run / 'simulation_run_manifest.json').read_text()) for run in RUNS]
    source_names = sorted(set(manifests[0]['source_sha256']) | set(manifests[1]['source_sha256']))
    result = dict(status='passed', scope='Actual full-file SHA-256 and size comparison after exhaustive native/numerical audits; no inversion-equivalence claim',
        comparison_source_sha256=sha(Path(__file__)), run_directories=[str(p.relative_to(ROOT)) for p in RUNS],
        members=members, physical_simulation_outputs={n: members[n]['byte_identical'] for n in physical},
        all_physical_simulation_outputs_byte_identical=all(members[n]['byte_identical'] for n in physical),
        native_geometry_tables_byte_identical=all(members[n]['byte_identical'] for n in
            ('truth_events.csv', 'initial_events.csv', 'stations.csv')),
        reused_base_members=sorted(reusable), separately_preserved_lon_members=sorted(separate),
        removed_base_members=sorted(set(a) - set(b)), added_lon_members=sorted(set(b) - set(a)),
        reused_bytes=sum(b[n]['bytes'] for n in reusable), separately_preserved_lon_bytes=sum(b[n]['bytes'] for n in separate),
        total_lon_bytes=sum(v['bytes'] for v in b.values()), numeric_config_differences=config_differences,
        initial_grid_coordinate_columns_identical=True, initial_grid_rows=len(grids[0]),
        initial_grid_velocity_rows_differing=sum(x['v'] != y['v'] for x, y in zip(*grids)),
        depth_profiles=[dict(z_km=z, lom_v_km_s=profiles[0][z], lon_v_km_s=profiles[1][z])
                        for z in sorted(profiles[0], key=float)],
        frozen_source_differences={n: dict(lom=manifests[0]['source_sha256'].get(n), lon=manifests[1]['source_sha256'].get(n))
            for n in source_names if manifests[0]['source_sha256'].get(n) != manifests[1]['source_sha256'].get(n)},
        base_package_manifest_sha256=sha(base / 'manifest.json'),
        audit_source_hashes=dict(lom=ar['review_source_sha256'], lon=br['review_source_sha256']))
    for run, expected in zip(RUNS, (a, b)):
        actual, unused_review = inventory(run)
        require(actual == expected, 'Run inventory or bytes changed during comparison')
    require(sha(base / 'manifest.json') == result['base_package_manifest_sha256'] and
            json.loads((base / 'verification.json').read_text()) == verified,
            'Base manifest or verification changed during comparison')
    result['all_original_hashes_and_inventories_reverified_at_end'] = True
    with target.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False); stream.write('\n')
    print(json.dumps({k: result[k] for k in ('status', 'all_physical_simulation_outputs_byte_identical',
          'reused_bytes', 'separately_preserved_lon_bytes', 'total_lon_bytes')}, indent=2))


if __name__ == '__main__':
    main()
