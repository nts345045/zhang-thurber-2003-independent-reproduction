#!/usr/bin/env python3
"""Bind the completed initial-model accuracy evidence to one guarded DD attempt."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def load(path):
    return json.loads(path.read_text())


def check():
    sample, review = load(OUT / 'summary.json'), load(OUT / 'review.json')
    assert sha(OUT / 'summary.json') == '66d48c6df173068fc0cf404414387a02e6d08a34ab02ebb5a0dbdfd880aedaca'
    assert sha(OUT / 'review.json') == '376f88cec5f59498ec4629ee98320744a6df8b1c30c71e19e9c61055a16dff0c'
    assert review['status'] == 'passed' and not review['material_issue_found']
    assert review['summary_sha256'] == sha(OUT / 'summary.json')
    assert review['all_native_fields_match'] and review['all_210_observation_side_joins_verified']
    assert review['all_selected_reference_dictionaries_match_reviewed_full_cache']
    assert review['all_48_saved_references_complete_valid_unique_and_finite']
    for name, digest in sample['input_sha256'].items():
        assert sha(ROOT / name) == digest, name
    for name, digest in sample['output_sha256'].items():
        assert sha(OUT / name) == digest, name
    full_dir = ROOT / 'data/development/hayward_first_arrival_004_1d_support'
    full, full_review = load(full_dir / 'summary.json'), load(full_dir / 'independent_review.json')
    assert full_review['status'] == 'passed' and not full_review['material_issue_found']
    assert full_review['summary_sha256'] == sha(full_dir / 'summary.json')
    assert full_review['both_limits_pass'] == full_review['verified_pairs'] == 14262
    assert full_review['saved_local_convergence_pass'] == full_review['saved_initialization_pass'] == 14262
    limits = dict(absolute_time_s=2.5e-5, source_euclidean_norm_s_per_km=3e-6)
    assert sample['accuracy_control_limits'] == limits
    assert all(full['accuracy_control_limits'][key] == value for key, value in limits.items())
    for variant in ('production', 'refined'):
        assert sample['times'][variant]['passing'] == 32
        assert sample['times'][variant]['maximum_absolute_error_s'] < limits['absolute_time_s']
        assert sample['source_vectors'][variant]['passing'] == 8
        assert sample['source_vectors'][variant]['maximum_error_norm_s_per_km'] < limits['source_euclidean_norm_s_per_km']
    data = ROOT / 'data/hayward_first_arrival_004'
    ledger, preflight = load(data / 'preflight_execution.json'), load(data / 'preflight.json')
    assert ledger['status'] == preflight['status'] == 'ready_for_accuracy_review'
    assert ledger['return_code'] == 0 and not preflight['failures']
    pins = dict(preflight_manifest=data / 'run_manifest.json', preflight_ledger=data / 'preflight_execution.json',
                preflight_checks=data / 'preflight.json', full_reference_summary=full_dir / 'summary.json',
                full_reference_review=full_dir / 'independent_review.json', sampled_summary=OUT / 'summary.json',
                sampled_independent_review=OUT / 'review.json')
    return dict(status='passed', decision='eligible_for_guarded_dd_attempt',
        preflight_directory=str(data.relative_to(ROOT)),
        checks=dict(full_reference_controls_pass=True, sample_local_flags_pass=True,
                    sample_accuracy_assessed=True, finite_difference_truncation_assessed=True),
        sha256={name: sha(path) for name, path in pins.items()},
        sampled_tables_sha256={name: sha(data / name) for name in
            ('initial_ray_convergence.csv', 'initial_ray_derivatives.csv', 'initial_ray_identifiers.csv')},
        accuracy_control_limits=limits, full_initial_pairs=14262, sampled_pairs=32, sampled_source_vectors=8,
        times=sample['times'], source_vectors=sample['source_vectors'],
        interpretation=[
            'All original initial-model forward pairs pass local/initialization flags and the unchanged continuous-reference time and source-vector limits.',
            'The production and refined sampled times and source vectors independently pass these same limits.',
            'The largest exact-reference central-difference truncation is 3.127681378637878e-6 s/km; saved finite differences differ from reference finite differences by at most 3.2654175557977894e-8 s/km.',
            'The finite-difference truncation is assessed separately from source-vector accuracy; no new finite-difference threshold or relaxed local flag is introduced.',
            'This supports one isolated catalog-only DD attempt using the reviewed per-evaluation guard and unchanged004 input/configuration.'
        ],
        limitations=[
            'This is initial depth-only-model evidence; it is not an accuracy or global first-arrival certificate for later three-dimensional models.',
            'The guard must stop on any invalid current/trial/final forward evaluation and preserve its identified evidence.',
            'A completed inversion still requires final-model refinement/source checks, native output review and nonlinear/LSQR interpretation.',
            'Ordinary floating reference ordering and saved 12-significant-digit candidate serialization retain the documented limitations.',
            'No catalog-plus-CC inversion or additional modes are authorized by this evidence file alone.'
        ], checker_sha256=sha(Path(__file__)))


if __name__ == '__main__':
    print(json.dumps(check(), indent=2, allow_nan=False))
