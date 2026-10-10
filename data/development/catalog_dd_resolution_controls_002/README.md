# Shared-pick catalog-DD resolution controls

This is an invented linear-algebra experiment. All 31 controls pass; the largest
agreement error is 1.78e-15 against the declared 1e-10 algebra tolerance. It runs
no field calculation or inversion and has no provider identities to attach.
The first 26-control execution is preserved in `../catalog_dd_resolution_controls_001/`.
The second adds a distinction required by the existing DD assembly mask.

Let G contain the unweighted coefficients actually used by a frozen estimator,
W its diagonal row multipliers, and C the map from original pick errors to
absolute and catalog-difference errors. Each difference row of C has one +1 and
one -1. Assuming independent original-pick variances Sigma, the joint observation
covariance is C Sigma C^T. This matrix is singular when differences reuse picks;
we propagate through it without treating differences as independent or inverting
that singular matrix.

With F = G^T W^2 G, H = F + L^T L + column-scaled damping, and P selecting the
velocity parameters, the response to original pick errors is

    K = P H^-1 G^T W^2 C
    covariance = K Sigma K^T.

The source block is eliminated by a general Schur complement, allowing coupling
between source parameters. L acts only on velocity parameters. Damping retains
the existing solver's column normalization and its fallback for zero/tiny norms.
The comparison uses unconstrained sources and fixed weights/linearization;
it does not differentiate robust weights, source bounds, or the nonlinear solve.

The physical local model resolution additionally needs the prediction's model
Jacobian J_model:

    R_model = P H^-1 G^T W^2 J_model.

It need not equal the velocity block of H^-1 F. The existing DD assembly masks
model coefficients when path-length differences are below 0.005 km and drops
coefficients at or below 1e-14. Thus a field caller must preserve the actual
assembled coefficients and reconstruct unmasked model derivatives from the
full export plus its suppressed-coefficient table. Subtracting already-thresholded
absolute rows is insufficient. Calling the helper without J_model returns only
the self-consistent assembly resolution, explicitly labeled as such.

Controls compare the Schur result with a dense full-parameter inverse and the
explicit C Sigma C^T covariance. They include coupled sources, an unsensed source
column, a difference cycle, an inactive row, row permutation, sign reversal,
existing absolute-only resolution, and rejection of an unidentified undamped
source. Hand-solvable controls retain the original pick covariance when catalog
differences are repeated. Two copies of the same scalar datum retain variance4;
assuming independent copies would incorrectly give variance2. A masked-assembly
control distinguishes physical model resolution from assembly resolution while
leaving measurement-noise propagation unchanged.

`invented_matrices.npz` preserves the generated matrices and results. The summary
pins the executed source copies and records NumPy/SciPy versions. Reproduce in a
fresh directory from the integration worktree:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/check_catalog_dd_resolution.py --output data/development/catalog_dd_resolution_controls_NEW
```

No field-data loader, native identity joins, final-model full Jacobian, or CC
noise model has been adopted. A later field calculation must bind its actual
weights, stage, geometry, suppressed derivatives and original-pick identities.
Interpreting reported pick errors as independent one-sigma noise remains an
explicit assumption; correlated station/model error, ray error, regularization
bias, active source bounds and nonlinear effects remain outside this covariance.
