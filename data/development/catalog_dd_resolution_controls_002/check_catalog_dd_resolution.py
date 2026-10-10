#!/usr/bin/env python3
"""Invented checks of shared-pick covariance and joint source elimination."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "diagnostics"))

import numpy as np
import scipy
from scipy import linalg, sparse

from catalog_dd_resolution import calculate
from resolution_hayward import block_resolution


def full_joint(G, weights, C, sigma, L, ns, damping, prediction_model=None):
    """Independent dense full-parameter calculation, without block elimination."""
    W = np.diag(weights)
    J = W @ G
    prior = np.zeros((L.shape[0], G.shape[1]))
    prior[:, ns:] = L
    column_norm = np.sum(J * J, axis=0) + np.sum(prior * prior, axis=0)
    scales = np.where(column_norm > 1e-20, 1 / np.sqrt(np.maximum(column_norm, 1e-300)), 1.)
    augmented = np.vstack([J, prior, np.diag(damping / scales)])
    normal = augmented.T @ augmented
    inverse = linalg.inv(normal)
    full_response = inverse @ J.T @ W
    observation_covariance = C @ np.diag(sigma ** 2) @ C.T
    covariance = full_response @ observation_covariance @ full_response.T
    truth_columns = G[:, ns:] if prediction_model is None else prediction_model
    return (full_response @ truth_columns)[ns:], covariance[ns:, ns:]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    checks, saved = [], {}
    tolerance = 1e-10

    def close(name, observed, expected):
        error = float(np.max(np.abs(np.asarray(observed) - np.asarray(expected))))
        checks.append(dict(check=name, maximum_absolute_difference=error,
                           tolerance=tolerance, passed=bool(error <= tolerance)))

    # Two independent original picks are observed absolutely and differenced.
    # Repeating that difference must not create an independent measurement.
    sigma = np.array([0.3, 0.7])
    for copies in (0, 1, 7):
        C = np.vstack([np.eye(2), np.tile([1., -1.], (copies, 1))])
        weights = np.linspace(0.5, 1.5, C.shape[0])
        R, covariance, response = calculate(C, weights, C, sigma, np.empty((0, 2)), 0, 0.)
        close("exact_fit_resolution_%d_differences" % copies, R, np.eye(2))
        close("exact_fit_covariance_%d_differences" % copies, covariance, np.diag(sigma ** 2))
        close("exact_fit_pick_response_%d_differences" % copies, response, np.eye(2))
        saved["exact_fit_C_%d" % copies] = C
        saved["exact_fit_covariance_%d" % copies] = covariance

    # Two repeated representations of one scalar datum retain variance 4.
    G = np.ones((2, 1))
    R, covariance, response = calculate(G, np.ones(2), G, np.array([2.]),
                                         np.empty((0, 1)), 0, 0.)
    close("duplicate_scalar_variance", covariance, [[4.]])
    close("duplicate_scalar_resolution", R, [[1.]])
    close("duplicate_scalar_response", response, [[1.]])
    wrong_independent_variance = float((linalg.inv(G.T @ G) * 4.)[0, 0])
    checks.append(dict(check="independent_duplicate_assumption_is_distinct",
                       shared_pick_variance=float(covariance[0, 0]),
                       wrong_independent_variance=wrong_independent_variance,
                       passed=bool(abs(wrong_independent_variance - 2.) < tolerance)))

    # Coupled source parameters, a cycle of differences, an inactive row, an
    # unsensed source column, and smoothing all appear in one small problem.
    rng = np.random.RandomState(2003)
    npick, ns, nv = 12, 5, 4
    A = rng.normal(size=(npick, ns + nv))
    A[:, 2] = 0.
    pairs = [(0, 1), (1, 2), (2, 0), (3, 8), (6, 10), (0, 1)]
    D = np.zeros((len(pairs), npick))
    for k, (i, j) in enumerate(pairs):
        D[k, i], D[k, j] = 1., -1.
    C = np.vstack([np.eye(npick), D])
    G = C @ A
    weights = np.linspace(0.1, 1.7, len(G))
    weights[13] = 0.
    sigma = np.linspace(0.02, 0.16, npick)
    L = rng.normal(size=(6, nv))
    R, covariance, response = calculate(G, weights, C, sigma, L, ns, .2)
    full_R, full_covariance = full_joint(G, weights, C, sigma, L, ns, .2)
    close("coupled_source_resolution_vs_full_joint", R, full_R)
    close("shared_pick_covariance_vs_full_joint", covariance, full_covariance)
    close("source_eliminated_resolution_from_pick_response", R, response @ A[:, ns:])
    close("covariance_symmetry", covariance, covariance.T)
    observation_covariance = C @ np.diag(sigma ** 2) @ C.T
    rank = int(np.linalg.matrix_rank(observation_covariance))
    checks.append(dict(check="shared_pick_covariance_is_singular", rank=rank,
                       observations=len(G), independent_picks=npick,
                       passed=bool(rank == npick and rank < len(G))))
    eigenvalues = linalg.eigvalsh(covariance)
    checks.append(dict(check="propagated_covariance_positive", minimum_eigenvalue=float(eigenvalues[0]),
                       passed=bool(eigenvalues[0] >= 0)))
    permutation = rng.permutation(len(G))
    reordered = calculate(G[permutation], weights[permutation], C[permutation], sigma, L, ns, .2)
    close("row_permutation_resolution", reordered[0], R)
    close("row_permutation_covariance", reordered[1], covariance)
    signs = np.ones(len(G))
    signs[npick:] = -1.
    reversed_result = calculate(signs[:, None] * G, weights, signs[:, None] * C, sigma, L, ns, .2)
    close("reversing_differences_resolution", reversed_result[0], R)
    close("reversing_differences_covariance", reversed_result[1], covariance)
    saved.update(coupled_G=G, coupled_C=C, coupled_weights=weights, coupled_sigma=sigma,
                 coupled_L=L, coupled_resolution=R, coupled_covariance=covariance,
                 coupled_pick_response=response)

    # The estimator may suppress small DD model coefficients while the
    # prediction still differentiates through them. Distinguish the two maps.
    masked = G.copy()
    masked[npick, ns] = 0.
    masked[npick + 4, ns + 2] = 0.
    physical = calculate(masked, weights, C, sigma, L, ns, .2,
                         prediction_model=G[:, ns:])
    direct_physical = full_joint(masked, weights, C, sigma, L, ns, .2,
                                 prediction_model=G[:, ns:])
    assembled = calculate(masked, weights, C, sigma, L, ns, .2)
    close("unmasked_prediction_resolution_vs_full_joint", physical[0], direct_physical[0])
    close("masked_estimator_noise_vs_full_joint", physical[1], direct_physical[1])
    close("prediction_jacobian_does_not_change_noise_covariance", physical[1], assembled[1])
    close("unmasked_resolution_from_original_pick_response", physical[0], physical[2] @ A[:, ns:])
    distinction = float(np.max(np.abs(physical[0] - assembled[0])))
    checks.append(dict(check="physical_and_assembly_resolution_are_distinct",
                       maximum_absolute_difference=distinction,
                       passed=bool(distinction > tolerance)))
    saved.update(masked_G=masked, unmasked_prediction_model=G[:, ns:],
                 masked_assembly_resolution=assembled[0],
                 masked_estimator_physical_resolution=physical[0],
                 masked_estimator_covariance=physical[1])

    # Reduce to the existing independent absolute-pick calculation, including
    # its unsensed-column damping convention, with W sigma = 0.05 seconds.
    ne, nv, per_event = 3, 5, 9
    E = linalg.block_diag(*[rng.normal(size=(per_event, 4)) for _ in range(ne)])
    E[:, 2] = 0.
    A = np.column_stack([E, rng.normal(size=(ne * per_event, nv))])
    sigma = np.linspace(.025, .12, len(A))
    weights = .05 / sigma
    L = rng.normal(size=(7, nv))
    R, covariance, response = calculate(A, weights, np.eye(len(A)), sigma, L, 4 * ne, .2)
    old_R, old_noise, _ = block_resolution(sparse.diags(weights) @ sparse.csr_matrix(A),
                                          np.repeat(np.arange(ne), per_event), ne, L, .2)
    close("absolute_only_resolution_limit", R, old_R)
    close("absolute_only_covariance_limit", covariance, .05 ** 2 * old_noise)

    # Without damping, the unsensed source makes the requested inverse undefined.
    try:
        calculate(A, weights, np.eye(len(A)), sigma, L, 4 * ne, 0.)
    except linalg.LinAlgError:
        rejected = True
    else:
        rejected = False
    checks.append(dict(check="unidentified_undamped_source_rejected", passed=rejected))
    saved.update(absolute_A=A, absolute_weights=weights, absolute_sigma=sigma,
                 absolute_L=L, absolute_resolution=R, absolute_covariance=covariance)
    np.savez_compressed(str(out / "invented_matrices.npz"), **saved)
    for path in (Path(__file__).resolve(), ROOT / "diagnostics/catalog_dd_resolution.py",
                 ROOT / "resolution_hayward.py"):
        shutil.copyfile(str(path), str(out / path.name))
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    summary = dict(scope="Invented linear-algebra controls only; no native data or inversion",
                   independent_pick_noise_assumption=True,
                   uncertainty_scope="Frozen weights, unconstrained source parameters; no nonlinear/robust-weight derivative, ray error, model error, bias or waveform-noise assumption",
                   numpy_version=np.__version__, scipy_version=scipy.__version__,
                   comparison_tolerance=tolerance, checks=checks,
                   passed=all(c["passed"] for c in checks),
                   files={p.name: sha(p) for p in sorted(out.iterdir()) if p.is_file()})
    (out / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
    print(json.dumps(dict(checks=len(checks), passed=summary["passed"],
                         max_comparison_error=max(c.get("maximum_absolute_difference", 0.)
                                                  for c in checks if "tolerance" in c)), indent=2))
    if not summary["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
