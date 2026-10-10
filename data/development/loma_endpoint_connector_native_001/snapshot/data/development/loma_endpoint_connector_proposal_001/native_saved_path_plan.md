# Proposed saved-path component comparison for pair 24104

**Planning only. Native execution remains held.** The 304 invented controls
test affine connector arithmetic and derivatives, not a production forward
functional or an optimized native ray.

Use only the selected `fmm_0.031250_1000` polygon in
`data/development/loma_initial_failure_24104_001/`. The source record is event
`quakeml:NC.anss.org/Event/NC/20091537`, origin
`quakeml:NC.anss.org/Origin/NC/2658134`, channel `NC.HQR..EHZ`,
`FDSN:NC_HQR__E_H_Z`, epoch `1989-07-11T19:55:00` to
`1990-03-24T19:55:00`. Preserve its complete identified row, original/current
coordinate distinction, input/source hashes, and the original local flag and
separate source-accuracy failure.

## What the comparison could establish

The saved source and first two interior vertices all have z=16 km. Replace
only the first mathematical straight-element action S(a,x₁) by the finite-box
connector G(a,x₁), with every saved vertex and every remaining element fixed:

    Fnew = Fold − S(a,x₁) + G(a,x₁).
    source_new = ∂a G.
    gradient_x₁,new = gradient_x₁,old − ∂x₁ S + ∂x₁ G.

At this unperturbed horizontal edge, G and S have the same mathematical
travel time. The predicted normal partials of G at both ends are zero from
the admissible interior side, whereas S contributes L s′z/2 at each end.
The source tangential partial is −t/vB and the first-vertex tangential partial
is +t/vB. The next straight element still contributes its normal reaction to
x₁: the full vertex gradient is not zeroed. Reporting only the source change
would conceal this required variational change.

Evaluate the component actions and both endpoint partials, separating exact
mathematical equality from floating-point differences. Retain the old total
and report the local difference G−S directly before adding it to the saved
remainder. Compare the source vector with the already reviewed continuous
reference, without promoting its accuracy result or changing any saved flag.
This would test whether the isolated component removes the demonstrated
fixed-family endpoint term in the actual saved geometry.

The source/grid record must be interpreted from its stored binary64 numbers.
Derive the last-layer affine coefficient from those nodal values and depths
as an exact ratio before numerical evaluation; do not silently fit or round
the field into a different model. Verify the relevant cell is depth-only and
that the whole connector stays in that affine layer and the original box.
The baseline guide has positive length. If later finite source or first-vertex
perturbations are included, preserve the actual critical-distance comparison:
Xc can exceed the first-element length, requiring an interior connector even
though the rest of the saved polygon is a guide. Such fixed-remainder values
are not reoptimized whole-ray values. A concrete perturbation roster must be
reviewed before extending this baseline comparison.

## What it could not establish

No polygon optimization is performed. The remaining action error, branch
choice, first-vertex stationarity and whole-path source secants remain
unresolved. A locally exact first element cannot remove errors elsewhere or
prove a differentiable optimized envelope. No model-grid derivative, Jacobian,
resolution estimate, source update or inverse result should be exported.

In particular, a production rule that uses the curved action only when the
initial profile is exactly affine and reverts to the old polygon action after
an arbitrarily small non-affine nodal perturbation is inadmissible. It changes
the forward functional across the inversion parameter space; neither the
affine derivative nor an unchanged old kernel then differentiates the executed
forward values in general.

A production proposal would first need one connector definition for the
actual trilinear velocity field at all model states, consistent endpoint and
interior-vertex derivatives, and every nodal sensitivity integrated through
the original basis functions along the corresponding curve. The affine case
could be a verified evaluation shortcut for that same functional. It cannot
define a separate physical model or fallback functional. The present controls
do not supply this generalization, and success of the proposed saved-path
calculation would not authorize it.
