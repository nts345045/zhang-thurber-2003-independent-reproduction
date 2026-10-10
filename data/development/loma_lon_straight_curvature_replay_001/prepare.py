#!/usr/bin/env python3
"""Freeze only saved inputs/source; no compiler, field construction or ray call."""
import csv
import difflib
import gzip
import hashlib
import json
import math
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import tarfile

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = ROOT / 'data/development/loma_lon_initial_accuracy_001'
PAIRS = (8670, 8674)

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()

def read_csv(path):
    opener = gzip.open if str(path).endswith('.gz') else open
    with opener(str(path), 'rt') as f:
        return list(csv.DictReader(f))

def dump(path, value):
    with Path(path).open('x') as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write('\n')

def table(path, rows):
    with Path(path).open('x', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

def main():
    if (HERE / 'prepared.json').exists() or (HERE / 'inputs').exists():
        raise RuntimeError('Preparation is exclusive; preserve any prior attempt')
    original = {}
    def pin(path):
        path = Path(path)
        original[str(path.relative_to(ROOT))] = sha(path)
        return path
    inputs = HERE / 'inputs'
    inputs.mkdir()
    manifest = json.loads((BASE / 'inputs/preflight/preflight_run_manifest.json').read_text())
    for name in ('initial_grid.csv', 'initial_events.csv', 'stations.csv', 'run.cfg',
                 'preflight_source.tar.gz', 'preflight_run_manifest.json'):
        path = pin(BASE / 'inputs/preflight' / name)
        shutil.copyfile(str(path), str(inputs / name))
    for name in ('summary.json', 'execution.json', 'failure_groups.json'):
        path = pin(BASE / name)
        shutil.copyfile(str(path), str(inputs / ('accuracy_' + name)))
    for name in ('summary.json', 'execution.json', 'review.json', 'independent_review.json'):
        path = pin(BASE / 'inputs/reference' / name)
        shutil.copyfile(str(path), str(inputs / ('reference_' + name)))
    compiler = Path(manifest['compiler'])
    runtime = {str(compiler): sha(compiler)}
    if runtime[str(compiler)] != manifest['compiler_sha256']:
        raise RuntimeError('Compiler changed since frozen preflight')
    for name, expected in manifest['runtime_library_sha256'].items():
        runtime[name] = sha(name)
        if runtime[name] != expected:
            raise RuntimeError('Runtime changed: ' + name)
    flags = pin(ROOT / 'tmp/loma_initial_preflight_runs/lon_001/compiled/CMakeFiles/dd.dir/flags.make')
    shutil.copyfile(str(flags), str(inputs / 'old_flags.make'))
    expected_flags = '-std=gnu++17 -O3 -Wall -Wextra -Wpedantic -fopenmp'
    if 'CXX_FLAGS = ' + expected_flags + '\n' not in flags.read_text():
        raise RuntimeError('Unexpected original compile flags')
    version = subprocess.check_output([str(compiler), '--version'], universal_newlines=True)
    (inputs / 'compiler_version.txt').write_text(version)
    rows = read_csv(pin(BASE / 'comparison.csv.gz'))
    status = read_csv(pin(BASE / 'inputs/preflight/dd_preflight_ray_status.csv.gz'))
    refs = read_csv(pin(BASE / 'inputs/reference/references.csv.gz'))
    samples = read_csv(pin(BASE / 'inputs/reference/inputs/ray_samples.csv'))
    if not (len(rows) == len(status) == len(refs) == 37648):
        raise RuntimeError('Incomplete saved support')
    selected = [rows[p] for p in PAIRS]
    for p, row in zip(PAIRS, selected):
        if int(row['comparison_row']) != p or int(row['reference_pair_index']) != p:
            raise RuntimeError('Pair order mismatch')
        if any(row[k] != v for k, v in status[p].items()):
            raise RuntimeError('Original status join mismatch')
        if row['ray_selected_fmm_seed'] != '0' or row['ray_time'] != row['ray_direct_seed_time']:
            raise RuntimeError('Selected record is not the straight result')
        if refs[p]['pair_index'] != str(p) or refs[p]['candidate_count'] != '1':
            raise RuntimeError('Reference is not the required unique candidate')
    table(inputs / 'selected_comparison.csv', selected)
    table(inputs / 'selected_status.csv', [status[p] for p in PAIRS])
    table(inputs / 'selected_reference.csv', [refs[p] for p in PAIRS])
    events, stations = read_csv(inputs / 'initial_events.csv'), read_csv(inputs / 'stations.csv')
    context = []
    for p, row in zip(PAIRS, selected):
        i, k = divmod(p, len(stations))
        for prefix, native in [('source_', events[i]), ('receiver_', stations[k])]:
            for key, value in native.items():
                if key not in ('id', 'x', 'y', 'z', 't') and row[prefix + key] != value:
                    raise RuntimeError('Full native metadata mismatch')
        context.append({'pair_index': p, 'source_native': events[i], 'receiver_native': stations[k],
                        'saved_comparison_row': row,
                        'initializer_metadata_basis': 'Saved original full two-start preflight only; not a new FMM evaluation'})
    dump(inputs / 'native_context.json', context)
    source = HERE / 'source'
    for variant in ('old', 'D'):
        dest = source / variant
        dest.mkdir(parents=True)
        with tarfile.open(str(inputs / 'preflight_source.tar.gz'), 'r:gz') as archive:
            for member in archive.getmembers():
                if not member.isfile() or member.name.startswith('/') or '..' in Path(member.name).parts:
                    raise RuntimeError('Unsafe source archive member')
                data = archive.extractfile(member).read()
                if hashlib.sha256(data).hexdigest() != manifest['source_sha256'][member.name]:
                    raise RuntimeError('Source archive pin mismatch')
                target = dest / member.name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
    adopted = ROOT / 'data/development/usable_curvature_integration_prepared_001/after'
    for name in ('src/core.hpp', 'src/usable_ray_curvature.hpp'):
        path = pin(adopted / name)
        if pin(ROOT / name).read_bytes() != path.read_bytes():
            raise RuntimeError('Maintained source differs from tested D')
        shutil.copyfile(str(path), str(source / 'D' / name))
    old = (source / 'old/src/core.hpp').read_text()
    new = (source / 'D/src/core.hpp').read_text()
    (HERE / 'core_old_to_D.diff').write_text(''.join(difflib.unified_diff(
        old.splitlines(True), new.splitlines(True), fromfile='old/src/core.hpp', tofile='D/src/core.hpp')))
    source_inventory = {str(p.relative_to(HERE)): sha(p) for p in sorted(source.rglob('*')) if p.is_file()}
    for name, expected in manifest['source_sha256'].items():
        if name != 'src/core.hpp' and sha(source / 'D' / name) != expected:
            raise RuntimeError('D changed an unrelated frozen source')
    grid = read_csv(inputs / 'initial_grid.csv')
    axes = {a: sorted(set(float(r[a]) for r in grid)) for a in 'xyz'}
    face_mismatch = 0
    for row in rows:
        for who in ('source', 'receiver'):
            for axis in 'xyz':
                for side, value in (('lower', axes[axis][0]), ('upper', axes[axis][-1])):
                    face_mismatch += int(int(row['reference_' + who + '_on_' + axis + '_' + side + '_face']) !=
                                         int(float(row['reference_' + who + '_' + axis]) == value))
    failed = [r for r in rows if r['source_vector_limit_pass'] == '0' and not any(
        r['reference_source_on_' + a + '_' + side + '_face'] == '1' for a in 'xyz' for side in ('lower', 'upper'))]
    deep = [r for r in failed if float(r['reference_source_z']) > 2]
    shallow = [r for r in failed if float(r['reference_source_z']) <= 2]
    interface_distances = [min(abs(float(r['reference_source_z']) - z) for z in axes['z'][1:-1]) for r in failed]
    face_distances = [min(min(float(r['reference_source_' + a])-axes[a][0], axes[a][-1]-float(r['reference_source_' + a])) for a in 'xyz') for r in failed]
    def ranges(group, fields):
        return {key: {'min': min(float(r[key]) for r in group),
                      'median': statistics.median(float(r[key]) for r in group),
                      'max': max(float(r[key]) for r in group)} for key in fields}
    sample_hits = [{'sample_row': n, 'comparison_row': int(s['event']) * 52 + int(s['station']),
                    'native': s} for n, s in enumerate(samples)
                   if any(r['event'] == s['event'] and r['station'] == s['station'] for r in failed)]
    table(inputs / 'interior_failure_rows.csv', failed)
    dump(HERE / 'characterization.json', {
        'scope': 'Saved tables only; no ray/reference recomputation', 'full_rows': len(rows),
        'face_flags_checked_per_row': 12, 'face_mismatches': face_mismatch,
        'interior_failure_count': len(failed), 'all_vertical_errors_negative': all(float(r['source_dz_error_s_per_km']) < 0 for r in failed),
        'source_distance_to_nearest_internal_depth_plane_km': {'min': min(interface_distances), 'max': max(interface_distances)},
        'source_distance_to_nearest_box_face_km': {'min': min(face_distances), 'max': max(face_distances)},
        'all_failed_rays_raw_equal_projected_gradient': all(r['ray_raw_gradient'] == r['ray_projected_gradient'] for r in failed),
        'all_failed_rays_above_strict_gradient_threshold': all(float(r['ray_projected_gradient']) >= 1e-7 for r in failed),
        'all_source_and_receiver_faces_false': all(not any(r['reference_' + who + '_on_' + a + '_' + side + '_face'] == '1'
               for who in ('source', 'receiver') for a in 'xyz' for side in ('lower', 'upper')) for r in failed),
        'dominant_group_count': len(deep), 'dominant_group_all_straight_selected': all(r['ray_selected_fmm_seed'] == '0' for r in deep),
        'dominant_group_ranges': ranges(deep, ['reference_source_z', 'reference_turning_depth_km', 'time_error_s',
            'ray_projected_gradient', 'ray_iterations', 'source_error_euclidean_norm_s_per_km', 'source_dz_error_s_per_km']),
        'shallow_group_count': len(shallow), 'shallow_comparison_rows': [int(r['comparison_row']) for r in shallow],
        'sample_hits': sample_hits, 'full_native_failure_rows': 'inputs/interior_failure_rows.csv',
        'interpretation': 'Two descriptive subgroups; no causal attribution. Local flags and source accuracy are distinct. No unfinished sample outputs read.'})
    dump(HERE / 'plan.json', {
        'status': 'prepared_not_executed', 'pairs': list(PAIRS), 'native_context': 'inputs/native_context.json',
        'call': 'trace(g, events[166].p, stations[k].p, 0.03125, 1000, true, nullptr), k=38,42',
        'calls_per_variant': 2, 'variants': ['old', 'D'], 'field_constructions': 0,
        'spacing_km': 0.03125, 'max_updates': 1000, 'source_time': 'retained separately, excluded from pure ray action',
        'old_gate': 'Every saved non-initializer status/native column string must match original C++12-significant-digit serialization before D starts',
        'saved_initializer_fields': 'Original record only; new trace is straight-only and does not reproduce FMM diagnostics',
        'D_difference': 'Extended outer action accumulation plus finite usable-curvature retention/two-loop checks; no single-cause attribution',
        'stopping': 'Unchanged strict1e-7 or action-change<1e-11 plus projected-gradient<1e-5',
        'scientific_limits': {'time_s': 2.5e-5, 'source_vector_norm_s_per_km': 3e-6},
        'outputs': 'Uninstrumented final paths, complete model partial arrays and raw scalar/status records; no history or new direction',
        'limits': 'Two prescribed straight starts only; no new branch selection, complete support, FMM, inversion or general3D acceptance'})
    for path, expected in original.items():
        if sha(ROOT / path) != expected:
            raise RuntimeError('Original changed during preparation: ' + path)
    pins = {str(p.relative_to(HERE)): sha(p) for p in sorted(HERE.rglob('*')) if p.is_file()}
    dump(HERE / 'prepared.json', {'status': 'prepared_not_executed', 'original_sha256': original,
        'runtime_sha256': runtime, 'compiler': str(compiler), 'flags': expected_flags.split(),
        'output_sha256': pins, 'source_sha256': source_inventory,
        'preserved_source_members': len(manifest['source_sha256']), 'native_pairs': list(PAIRS)})
    print(sha(HERE / 'prepared.json'))

if __name__ == '__main__':
    main()
