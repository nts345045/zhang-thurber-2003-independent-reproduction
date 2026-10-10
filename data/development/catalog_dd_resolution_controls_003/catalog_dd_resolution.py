#!/usr/bin/env python3
"""Frozen linear resolution with shared-pick noise; no field-data loader.

G contains the unweighted coefficients used by the estimator. C maps independent
pick errors into those observations: absolute rows select one pick and catalog
difference rows subtract two picks. W is the frozen diagonal row multiplier.
L acts on velocity parameters only; source coordinates remain unconstrained.

For F = G.T W**2 G and H = F + L.T L + column-scaled damping, the velocity
resolution is [H**-1 G.T W**2 J_model]_velocity. J_model differentiates the
predictions with respect to true velocity parameters; it can differ from G's
model block because DD assembly suppresses some coefficients. With J_model
omitted, the result is only the self-consistent assembly resolution [H**-1 F]vv.
Measurement covariance propagates
through H**-1 G.T W**2 C, without inverting the singular shared-pick covariance.
The original pick uncertainties are assumed independent standard deviations.
This is not the derivative or covariance of the full nonlinear robust solver.
"""

import numpy as np
from scipy import linalg, sparse


def calculate(G, weights, C, pick_sigma, L, source_columns, damping,
              prediction_model=None, column_norm_squared=None):
    """Return velocity resolution/covariance and response to original pick noise.

    The caller must attach observational identities and actual frozen weights.
    No independence is assigned to catalog differences. No noise model for
    waveform correlations is supplied by this function. For physical local
    velocity resolution, supply the unmasked prediction_model (rows by model
    columns); the default uses G's potentially masked model columns.
    Field callers must also supply the exported column_norm_squared, which
    includes each ordered data/smoothing entry before duplicate coalescing.
    The default instead computes norms from the coalesced operators G and L.
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
    if prediction_model is not None:
        prediction_model = sparse.csr_matrix(prediction_model)
        if (prediction_model.shape != (G.shape[0], nv) or
                not np.all(np.isfinite(prediction_model.data))):
            raise ValueError("Invalid prediction-model Jacobian")
    if column_norm_squared is not None:
        column_norm_squared = np.asarray(column_norm_squared, dtype=float)
        if (column_norm_squared.shape != (G.shape[1],) or
                not np.all(np.isfinite(column_norm_squared)) or
                np.any(column_norm_squared < 0)):
            raise ValueError("Invalid exported squared column norms")
    if (np.any(weights < 0) or np.any(sigma < 0) or
            not np.isfinite(damping) or damping < 0):
        raise ValueError("Negative weight, standard deviation, or damping")

    weighted = sparse.diags(weights) @ G
    F = (weighted.T @ weighted).toarray()
    normal = F.copy()
    normal[ns:, ns:] += L.T @ L
    norm_squared = (np.diag(normal).copy() if column_norm_squared is None
                    else column_norm_squared.copy())
    # Existing solver convention, not a new physical prior or cutoff.
    norm_squared = np.where(norm_squared > 1e-20, norm_squared, 1.)
    normal[np.diag_indices_from(normal)] += damping ** 2 * norm_squared
    if not np.all(np.isfinite(normal)):
        raise ValueError("Nonfinite regularized normal matrix")

    if ns:
        source_factor = linalg.cho_factor(normal[:ns, :ns])
        elimination = linalg.cho_solve(source_factor, normal[:ns, ns:])
        schur = normal[ns:, ns:] - normal[ns:, :ns] @ elimination
    else:
        elimination = np.empty((0, nv))
        schur = normal
    if prediction_model is None:
        model_rhs = F[:, ns:]
    else:
        model_rhs = (G.T @ sparse.diags(weights ** 2) @ prediction_model).toarray()
    resolution_rhs = model_rhs[ns:] - elimination.T @ model_rhs[:ns]
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
