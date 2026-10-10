#!/usr/bin/env python3
"""Prepare an explicit continuous-layered truth bundle for a fresh Loma run.

This does not run the simulator, alter failed polygon-ray evidence, or accept
the inverse forward operator. Only a completed, independently reviewed full
reference with preserved native identities is eligible.
"""
import argparse
import datetime
import gzip
import itertools
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'diagnostics'))
import run_loma_layered_full as batch


def require(condition, message):
    if not condition:
        raise ValueError(message)


def inside(parent, path):
    path = path.resolve()
    path.relative_to(parent.resolve())
    return path


def reviewed_reference(reference, counts=(724, 52)):
    """Verify immutable artifacts, full native joins, certificates and review links."""
    summary = json.loads((reference / 'summary.json').read_text())
    ledger = json.loads((reference / 'execution.json').read_text())
    pairs = counts[0] * counts[1]
    require(summary['status'] == 'complete' and ledger['status'] == 'completed' and
            ledger['result_status'] == 'complete', 'The full reference is not complete and valid')
    require(ledger['summary_sha256'] == batch.sha(reference / 'summary.json'), 'Terminal summary changed')
    require((summary['source_count'], summary['receiver_count']) == counts and
            summary['expected_pairs'] == summary['verified_pairs'] == pairs and
            all(summary['counts'][key] == pairs for key in ('pairs', 'reference_complete', 'reference_valid')),
            'Full reference support is incomplete')
    require(not summary['unresolved_pair_indices'] and not summary['near_tie_pair_indices'],
            'Unresolved or nonunique references cannot define this truth bundle')
    required = {'inputs/truth_events.csv', 'inputs/stations.csv', 'inputs/truth_grid.csv',
                'references.csv.gz', 'certificates.jsonl.gz', 'source/run_loma_layered_full.py',
                'source/first_arrival_layered_reference.py', 'source/first_arrival_1d_reference.py'}
    require(required <= set(summary['output_sha256']), 'Missing frozen geometry/reference/source artifacts')
    hashes = {}
    for name, expected in summary['output_sha256'].items():
        path = inside(reference, reference / name)
        require(batch.sha(path) == expected, 'Reference artifact changed: ' + name)
        hashes[path] = expected
    for name in ('summary.json', 'execution.json', 'review.json', 'independent_review.json'):
        hashes[reference / name] = batch.sha(reference / name)
    review = json.loads((reference / 'review.json').read_text())
    independent = json.loads((reference / 'independent_review.json').read_text())
    for record in (review, independent):
        require(record['summary_sha256'] == hashes[reference / 'summary.json'] and
                record['execution_sha256'] == hashes[reference / 'execution.json'],
                'Review does not describe this terminal reference')
    require(review['counts']['pairs'] == review['counts']['reference_valid'] == pairs and
            independent['verified_pairs'] == pairs and independent['invalid_reference_count'] == 0 and
            independent['native_metadata_fields_all_match'] and independent['ordered_indices_complete'] and
            independent['source_derivative_permutation_matches'] and not independent['material_issue_found'],
            'Independent reference review is incomplete or reports a material issue')
    _, events = batch.table(reference / 'inputs/truth_events.csv')
    _, stations = batch.table(reference / 'inputs/stations.csv')
    _, grid = batch.table(reference / 'inputs/truth_grid.csv')
    profile, box = batch.geometry(events, stations, grid, counts)
    require(profile == [tuple(row) for row in summary['profile_x_velocity_km_km_s']] and
            box == summary['original_box_km'], 'Reference model description differs from its input grid')
    require(batch.verify_outputs(reference, events, stations) == pairs, 'Native certificate joins incomplete')
    with gzip.open(str(reference / 'certificates.jsonl.gz'), 'rt') as stream:
        for index, line in enumerate(stream):
            record = json.loads(line)
            ref = record['reference']
            first = ref.get('first_arrival')
            require(record['pair_index'] == index and ref['complete'] and ref['reference_valid'] and
                    not ref['unresolved'] and len(ref['near_ties']) == 1 and first is not None,
                    'Invalid or nonunique arrival certificate')
            require(ref['distance_tolerance_km'] == 1e-8, 'Reference closure tolerance changed')
            candidates = ref['candidates']
            require(bool(candidates) and first == min(candidates, key=lambda c: c['time_s']),
                    'Selected arrival is not the earliest enumerated candidate')
            for candidate in candidates:
                require(math.isfinite(candidate['time_s']) and candidate['time_s'] >= 0 and
                        math.isfinite(candidate['distance_residual_km']) and
                        abs(candidate['distance_residual_km']) <= ref['distance_tolerance_km'],
                        'Candidate fails the unchanged action/closure requirements')
            gradient = first['source_derivative_s_per_km']
            require(gradient is not None and len(gradient) == 3 and all(math.isfinite(v) for v in gradient),
                    'Selected reference source derivative is undefined')
    return summary, hashes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--profile', choices=('lom', 'lon'), default='lom')
    args = parser.parse_args()
    reference, out = [inside(ROOT, ROOT / p) for p in (args.reference, args.output)]
    require(not out.exists(), 'Choose a fresh simulation directory; prior outputs are preserved')
    summary, hashes = reviewed_reference(reference)
    preparer = ROOT / 'prepare_loma.py'
    sources = [Path(__file__).resolve(), preparer, Path(batch.__file__).resolve()]
    source_hashes = {path: batch.sha(path) for path in sources}
    command = [sys.executable, str(preparer), '--profile', args.profile, '--output', str(out.relative_to(ROOT))]
    subprocess.check_call(command, cwd=str(ROOT), env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1', TMPDIR=str(ROOT / 'tmp')))
    bundle = out / 'analytic_truth'
    (bundle / 'inputs').mkdir(parents=True)
    for name in ('truth_grid.csv', 'truth_events.csv', 'stations.csv'):
        original = reference / 'inputs' / name
        require(batch.sha(out / name) == batch.sha(original), 'Fresh prepared native geometry/model differs: ' + name)
        shutil.copyfile(str(original), str(bundle / 'inputs' / name))
        require(batch.sha(bundle / 'inputs' / name) == hashes[original], 'Truth input changed during copy')
    # Preserve the full CSV, including all provider/native metadata columns.
    with gzip.open(str(reference / 'references.csv.gz'), 'rb') as src, (bundle / 'references.csv').open('xb') as dst:
        shutil.copyfileobj(src, dst, 1024 * 1024)
    provenance = bundle / 'provenance'
    provenance.mkdir()
    for name in ('summary.json', 'execution.json', 'review.json', 'independent_review.json', 'certificates.jsonl.gz'):
        shutil.copyfile(str(reference / name), str(provenance / name))
        require(batch.sha(provenance / name) == hashes[reference / name], 'Provenance changed during copy')
    shutil.copytree(str(reference / 'source'), str(provenance / 'reference_source'))
    for path in (reference / 'source').rglob('*'):
        if path.is_file():
            require(path in hashes and batch.sha(provenance / 'reference_source' / path.relative_to(reference / 'source')) == hashes[path],
                    'Unfrozen or changed reference source copy')
    (provenance / 'preparation_source').mkdir()
    for source in sources:
        shutil.copyfile(str(source), str(provenance / 'preparation_source' / source.name))
        require(batch.sha(provenance / 'preparation_source' / source.name) == source_hashes[source],
                'Preparation source changed during copy')
    for path, expected in itertools.chain(hashes.items(), source_hashes.items()):
        require(batch.sha(path) == expected, 'Reference or preparation source changed during export: ' + str(path))
    manifest = dict(
        status='prepared', truth_mode='continuous_layered_reference',
        created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        scope='Fresh identified Loma simulation inputs with continuous Snell truth; no simulation or inversion run',
        reference_directory=str(reference.relative_to(ROOT)), profile=args.profile.upper(),
        source_count=summary['source_count'], receiver_count=summary['receiver_count'], pairs=summary['verified_pairs'],
        command=' '.join(sys.argv), preparation_command=command,
        simulation_command_template='FROZEN_DD simulate ' + str((out / 'run.cfg').relative_to(ROOT)) + ' ' +
            str(out.relative_to(ROOT)) + ' --analytic-truth ' + str(bundle.relative_to(ROOT)),
        reference_sha256={str(p.relative_to(ROOT)): h for p, h in hashes.items()},
        source_sha256={str(p.relative_to(ROOT)): h for p, h in source_hashes.items()},
        prepared_sha256={str(p.relative_to(out)): batch.sha(p) for p in out.rglob('*') if p.is_file()},
        timing_definition='T is the unique earliest continuous layered reference time; existing C++ rounding/noise/DD order remains unchanged.',
        limitations=[
            'The catalog defines simulation geometry; simulated arrivals are not observed earthquake picks.',
            'Finite-box candidate completeness and distance closure are checked; floating-point time ordering is not an interval minimum-time certificate.',
            'This truth bundle does not certify the polygon ray solver or replace its preserved failed preflight.',
            'Initial and updated inverse forward calculations still require separate numerical validation.',
            'The authoritative geometry subset and documented model adaptations differ from exact manuscript inputs.'])
    (out / 'analytic_truth_manifest.json').write_text(json.dumps(manifest, indent=2, allow_nan=False) + '\n')
    print('Prepared {} identified continuous truth arrivals; simulator not run'.format(summary['verified_pairs']))


if __name__ == '__main__':
    main()
