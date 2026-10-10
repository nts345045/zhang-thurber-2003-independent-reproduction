#!/usr/bin/env python3
"""Frozen linear resolution with shared-pick noise; no field-data loader.

G differentiates all unweighted observation predictions. C maps independent
pick errors into those observations: absolute rows select one pick and catalog
difference rows subtract two picks. W is the frozen diagonal row multiplier.
L acts on velocity parameters only; source coordinates remain unconstrained.

For F = G.T W**2 G and H = F + L.T L + column-scaled damping, the velocity
resolution is the velocity block of H**-1 F. Measurement covariance propagates
through H**-1 G.T W**2 C, without inverting the singular shared-pick covariance.
The original pick uncertainties are assumed independent standard deviations.
This is not the derivative or covariance of the full nonlinear robust solver.
"""

import numpy as np
from scipy import linalg, sparse


def calculate(G, weights, C, pick_sigma, L, source_columns, damping):
    """Return velocity resolution/covariance and response to original pick noise.

    The caller must attach observational identities and actual frozen weights.
    No independence is assigned to catalog differences. No noise model for
    waveform correlations is supplied by this function.
    """
    G, C = sparse.csr_matrix(G), sparse.csr_matrix(C)
    weights, sigma, L = (np.asarray(x, dtype=float) for x in (weights, pick_sigma, L))
    ns = source_columns
    if not isinstance(ns, (int, np.integer)) or ns < 0 or ns >= G.shape[1]:
        raise ValueError("Require a nonnegative source count and a velocity block")
    nv = G.shape[1] - ns
    if (weights.shape != (G.shape[0],) or C.shape[0] != G.shape[0] or
            sigma.shape != (C.shape[1],) or L.ndim != 2 or L.shape[1] != nv):
        raise ValueError("Inconsistent observation, pick, or parameter dimensions")
    for values in (G.data, C.data, weights, sigma, L):
        if not np.all(np.isfinite(values)):
            raise ValueError("Nonfinite linear input")
    if (np.any(weights < 0) or np.any(sigma < 0) or
            not np.isfinite(damping) or damping < 0):
        raise ValueError("Negative weight, standard deviation, or damping")

    weighted = sparse.diags(weights) @ G
    F = (weighted.T @ weighted).toarray()
    normal = F.copy()
    normal[ns:, ns:] += L.T @ L
    norm_squared = np.diag(normal).copy()
    # Existing solver convention, not a new physical prior or cutoff.
    norm_squared = np.where(norm_squared > 1e-20, norm_squared, 1.)
    normal[np.diag_indices_from(normal)] += damping ** 2 * norm_squared
    if not np.all(np.isfinite(normal)):
        raise ValueError("Nonfinite regularized normal matrix")

    if ns:
        source_factor = linalg.cho_factor(normal[:ns, :ns])
        elimination = linalg.cho_solve(source_factor, normal[:ns, ns:])
        schur = normal[ns:, ns:] - normal[ns:, :ns] @ elimination
        resolution_rhs = F[ns:, ns:] - elimination.T @ F[:ns, ns:]
    else:
        elimination = np.empty((0, nv))
        schur, resolution_rhs = normal, F
    schur_factor = linalg.cho_factor(schur)
    resolution = linalg.cho_solve(schur_factor, resolution_rhs)

    # W appears twice: once in the residual and once in its weighted Jacobian.
    # Multiplication by C preserves reuse of each original pick's noise.
    rhs_pick_noise = (G.T @ sparse.diags(weights ** 2) @ C).toarray()
    response_rhs = rhs_pick_noise[ns:] - elimination.T @ rhs_pick_noise[:ns]
    pick_response = linalg.cho_solve(schur_factor, response_rhs)
    noise_response = pick_response * sigma[None, :]
    covariance = noise_response @ noise_response.T
    if not all(np.all(np.isfinite(a)) for a in (resolution, covariance, pick_response)):
        raise ValueError("Nonfinite resolution or noise propagation")
    return resolution, covariance, pick_response
