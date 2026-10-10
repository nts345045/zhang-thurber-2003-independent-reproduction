#!/usr/bin/env python3
"""Independent small dense controls for conditional shared-pick resolution."""
import argparse
import copy
import csv
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import shutil
import sys

import numpy as np
import scipy

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='data/development/full_dd_resolution_checks')
    args = parser.parse_args()
    output = (ROOT / args.output).resolve()
    output.relative_to(ROOT)
    output.mkdir(parents=True)
    source = ROOT / 'resolution_full_hayward.py'
    source_hash = sha(source)
    snapshot = output / 'source'
    snapshot.mkdir()
    for path in (source, Path(__file__).resolve()):
        shutil.copyfile(str(path), str(snapshot / path.name))
    spec = importlib.util.spec_from_file_location('resolution', str(snapshot / source.name))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    checks = []

    def close(name, actual, expected, tolerance=2e-11):
        actual, expected = np.asarray(actual), np.asarray(expected)
        error = float(np.max(np.abs(actual - expected))) if actual.size else 0.
        scale = max(1., float(np.max(np.abs(expected))) if expected.size else 0.)
        passed = actual.shape == expected.shape and np.all(np.isfinite(actual)) and error <= tolerance * scale
        checks.append(dict(name=name, passed=bool(passed), maximum_absolute_error=error,
                           arithmetic_tolerance=tolerance * scale))

    def truth(name, passed):
        checks.append(dict(name=name, passed=bool(passed)))

    # Two absolute picks and their exact redundant difference. The independent
    # primitive errors are the two picks; the third row is not a third error.
    P = np.array([[1., 0.], [0., 1.], [1., -1.]])
    weight = np.array([1., 1., 1. / math.sqrt(2.)])
    G = weight[:, None] * P
    U = .05 * G
    H = G.T @ G
    transfer = np.linalg.solve(H, G.T @ U)
    close('redundant_two_pick_exact_covariance', transfer @ transfer.T, .05 ** 2 * np.eye(2))
    wrong = .05 ** 2 * np.linalg.inv(H)
    close('independent_DD_wrong_result_exhibited', wrong, .05 ** 2 * np.array([[.75, .25], [.25, .75]]))
    # One unobserved, independently anchored dummy source coordinate lets the
    # model-block API represent this exact two-parameter example unchanged.
    A = np.column_stack((np.zeros(3), G))
    R, covariance, physical, diagnostics = module.joint_resolution(
        A, np.zeros((0, 3)), 1, [1., 0., 0.], U, G)
    close('maintained_two_pick_resolution', R, np.eye(2))
    close('maintained_two_pick_covariance', covariance, .05 ** 2 * np.eye(2))
    close('maintained_two_pick_unmasked_response', physical, np.eye(2))

    # Three events, two picks each, source x/y/z/t and three model parameters.
    # This fixture contains source coupling, unequal uncertainties, fixed row
    # weights, one omitted row, two masked DD model coefficients and smoothing.
    rng = np.random.RandomState(1847)
    ns, nv, npick = 12, 3, 6
    pick_J = np.zeros((npick, ns + nv))
    for k in range(npick):
        e = k // 2
        pick_J[k, 4 * e:4 * e + 3] = rng.uniform(-.18, .18, 3)
        pick_J[k, 4 * e + 3] = 1.
        pick_J[k, ns:] = rng.uniform(.2, 1.2, nv)
    incidence = list(np.eye(npick))
    for i, j in ((0, 2), (1, 3), (0, 4), (1, 5), (2, 4), (3, 5)):
        row = np.zeros(npick); row[i], row[j] = 1., -1.
        incidence.append(row)
    incidence = np.array(incidence)
    sigma = np.array([.03, .05, .07, .04, .06, .09])
    observation_sigma = np.sqrt((incidence ** 2) @ (sigma ** 2))
    prior = .05 / observation_sigma
    frozen_robust = np.array([1., .8, .4, .9, .7, 1., .6, .2, .9, .5, .8, .3])
    stage = np.array([.5] * 6 + [1.7] * 6)
    distance = np.array([1.] * 6 + [.85, .75, .65, .95, .9, .8])
    weight = prior * frozen_robust * stage * distance
    weight[9] = 0.
    unmasked = incidence @ pick_J
    masked = unmasked.copy()
    masked[6, ns], masked[10, ns + 1] = 0., 0.
    A = weight[:, None] * masked
    F = weight[:, None] * unmasked[:, ns:]
    U = weight[:, None] * incidence * sigma[None, :]
    L = np.zeros((2, ns + nv)); L[0, ns:ns + 2] = [.7, -.7]; L[1, ns + 1:] = [.4, -.4]

    # The export scales columns from squared entries before duplicates are
    # coalesced. Deliberately split one coefficient: the operator is unchanged,
    # but its exported damping scale must retain the original entry norm.
    entries, norms = [], np.zeros(ns + nv)
    for i in range(A.shape[0]):
        for j in range(A.shape[1]):
            if A[i, j] == 0:
                continue
            values = [.4 * A[i, j], .6 * A[i, j]] if (i, j) == (0, 3) else [A[i, j]]
            for value in values:
                entries.append(dict(observation_row=i, column=j, weighted_value=value))
                norms[j] += value * value
    with (output / 'invented_matrix.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=['observation_row', 'column', 'weighted_value'])
        writer.writeheader(); writer.writerows(entries)
    exported, data_norm = module.triplet_matrix(output / 'invented_matrix.csv', A.shape, 'weighted_value', True)
    close('ordered_duplicate_operator', exported.toarray(), A)
    close('ordered_duplicate_norms', data_norm, norms)
    truth('duplicate_norm_differs_from_coalesced_gram', abs(norms[3] - (A.T @ A)[3, 3]) > .01)
    norms += np.sum(L * L, axis=0)
    scale = np.where(norms > 1e-20, 1. / np.sqrt(norms), 1.)
    damping = .13 / scale
    H = A.T @ A + L.T @ L + np.diag(damping * damping)
    dense_R = np.linalg.solve(H, A.T @ A)
    dense_transfer = np.linalg.solve(H, A.T @ U)
    dense_covariance = dense_transfer @ dense_transfer.T
    dense_physical = np.linalg.solve(H, A.T @ F)
    R, covariance, physical, joint_diagnostics = module.joint_resolution(A, L, ns, damping, U, F)
    close('coupled_Schur_resolution_vs_joint_dense', R, dense_R[ns:, ns:])
    close('coupled_Schur_covariance_vs_joint_dense', covariance, dense_covariance[ns:, ns:])
    close('coupled_Schur_unmasked_response_vs_joint_dense', physical, dense_physical[ns:])
    close('masked_resolution_differs_from_unmasked_response_control', physical - R,
          dense_physical[ns:] - dense_R[ns:, ns:])
    truth('mask_control_changes_response', np.linalg.norm(physical - R) > 1e-4)
    truth('source_blocks_are_coupled', np.linalg.norm((A.T @ A)[:4, 4:8]) > .1)
    truth('origin_and_model_are_coupled', np.linalg.norm((A.T @ A)[[3, 7, 11], ns:]) > .1)
    truth('full_resolution_has_model_response_to_source', np.linalg.norm(dense_R[ns:, :ns]) > 1e-4)
    injections = []
    for pick in range(npick):
        positive = np.linalg.solve(H, A.T @ U[:, pick])
        negative = np.linalg.solve(H, -A.T @ U[:, pick])
        close('single_pick_{}_signed_linearity'.format(pick), positive, -negative)
        injections.append((positive - negative) / 2.)
    injection_covariance = sum(np.outer(v, v) for v in injections)
    close('deterministic_signed_pick_injection_covariance', covariance, injection_covariance[ns:, ns:])
    wrong_independent = np.linalg.solve(H, A.T) @ np.diag(np.sum(U * U, axis=1)) @ np.linalg.solve(H, A.T).T
    truth('independent_DD_noise_is_detectably_wrong', np.linalg.norm(wrong_independent[ns:, ns:] - covariance) > 1e-5)
    origin_shift = np.zeros(ns + nv); origin_shift[[3, 7, 11]] = 1.
    close('DD_annihilates_shared_origin_shift', unmasked[6:] @ origin_shift, np.zeros(6))
    close('absolute_retains_shared_origin_shift', unmasked[:6] @ origin_shift, np.ones(6))
    close('DD_annihilates_shared_pick_shift', incidence[6:] @ np.ones(npick), np.zeros(6))

    # The reader's native metadata fixture is independent of the numeric one.
    # Reused picks keep all identities/epochs; blank location and open end valid.
    native = []
    for k in range(2):
        native.append(dict(event_resource_id='smi:invented/event/{}'.format(k),
            origin_resource_id='smi:invented/origin/{}'.format(k), arrival_resource_id='smi:invented/arrival/{}'.format(k),
            pick_resource_id='smi:invented/pick/{}'.format(k), pick_uncertainty_s=[.03, .07][k],
            pick_time_utc='2001-01-0{}T00:00:00Z'.format(k + 1), pick_uncertainty_confidence_level='',
            pick_source_sha256='invented_pick_document_{}'.format(k), metadata_epoch_start='2000-01-01T00:00:00Z',
            metadata_epoch_end='', channel_source_sha256='invented_channel_document'))
    channel = dict(network_code='XX', station_code='MOCK', location_code='', channel_code='HHZ',
                   channel_seed_id='XX.MOCK..HHZ', channel_fdsn_source_id='FDSN:XX_MOCK__H_H_Z')
    native_rows = []
    for kind, i, j, value, multiplier, active in ((0, 0, None, 2., 1.2, 1), (0, 1, None, 3., .8, 1),
                                               (1, 0, 1, -1., .6, 1), (1, 1, 0, 1., .9, 0)):
        row = dict(type=kind, observed=value, combined_multiplier=multiplier, active=active)
        row.update({'observation_' + k: v for k, v in channel.items()})
        for side, k in [('i', i)] + ([('j', j)] if j is not None else []):
            for key, value in native[k].items():
                if key.startswith('pick_'):
                    field = 'pick_' + side + '_' + key[5:]
                elif key.endswith('_resource_id'):
                    field = key[:-12] + '_' + side + '_resource_id'
                elif key.startswith('metadata_epoch_'):
                    field = 'metadata_epoch_' + ('j_' if side == 'j' else '') + key[15:]
                else:
                    field = 'channel_' + ('j_' if side == 'j' else '') + 'source_sha256'
                row['observation_' + field] = value
        native_rows.append(row)
    noise, picks = module.pick_noise(native_rows)
    close('native_shared_pick_incidence', noise.toarray(), np.array([[1.2*.03, 0], [0, .8*.07], [.6*.03, -.6*.07], [0, 0]]))
    truth('native_pick_IDs_and_blank_fields_preserved', len(picks) == 2 and all(
        p['pick_resource_id'] == native[k]['pick_resource_id'] and p['location_code'] == '' and
        p['metadata_epoch_end'] == '' for k, p in enumerate(picks)))
    for label, key, value in [('sigma', 'observation_pick_i_uncertainty_s', .031),
                              ('epoch', 'observation_metadata_epoch_start', '1999-01-01T00:00:00Z'),
                              ('arrival', 'observation_arrival_i_resource_id', 'smi:invented/different'),
                              ('type2', 'type', 2)]:
        changed = copy.deepcopy(native_rows); changed[2][key] = value
        try:
            module.pick_noise(changed)
        except ValueError:
            rejected = True
        else:
            rejected = False
        truth('reject_inconsistent_native_' + label, rejected)
    truth('maintained_source_unchanged_during_checks', sha(source) == source_hash)
    report = dict(scope='Invented linear algebra and identity controls only; no field inference or solver execution',
        command='PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python3 diagnostics/check_full_dd_resolution.py --output ' + str(output.relative_to(ROOT)),
        passed=all(c['passed'] for c in checks), checks=checks,
        exact_two_pick_covariance=(.05**2*np.eye(2)).tolist(), wrong_independent_DD_covariance=wrong.tolist(),
        coupled_fixture=dict(events=3, source_coordinates_per_event=4, model_parameters=nv, primitive_picks=npick,
                             observation_rows=A.shape[0], sigmas_s=sigma.tolist(), row_multipliers=weight.tolist(),
                             full_normal_condition_number=float(np.linalg.cond(H)), diagnostics=joint_diagnostics),
        source_sha256={p.name: sha(p) for p in snapshot.iterdir()},
        versions=dict(python=sys.version.split()[0], numpy=np.__version__, scipy=scipy.__version__),
        limitations=['Frozen linear design, row weights, masks, smoothing and column scaling.',
                     'Damping uses the exported entry norms, not a recomputed coalesced Gram diagonal.',
                     'Primitive pick sigmas are already in U; no extra 0.05 squared factor is used.',
                     'The algebra tests do not assess ray accuracy, nonlinear convergence or active source bounds.'])
    (output / 'results.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps(dict(passed=report['passed'], checks=len(checks), failures=[c for c in checks if not c['passed']]), indent=2))
    raise SystemExit(0 if report['passed'] else 1)


if __name__ == '__main__':
    main()
