# Face intervals and primary-source citation

The README's trilinear-degree statement applies separately on each parameter
interval obtained by splitting the edge at the other grid planes. On each such
interval the shared face velocity and either adjacent cell's normal velocity
slope are quadratic in the edge parameter. Their coefficients can change at
the next face patch. A multi-cell edge does not in general have one global
quadratic face restriction. The first-variation integrals are summed over
these intervals; no new numerical calculation or native inference is made.

The regularity qualification was checked in Burke, Lewis and Overton (2005),
Section 1 (Introduction), printed page 753, the paragraph immediately before
Section 2. It distinguishes Clarke stationarity at a subdifferentially regular
point from the nonregular example f(x)=-|x|, for which Clarke stationarity does
not imply nonnegative ordinary directional derivatives. This is PDF page 3
(zero-based page index 2) of the
[primary paper](https://cims.nyu.edu/~overton/papers/pdffiles/gradsamp.pdf).
Section 2, printed page 756, also states the support-function/minimum-norm
relation for a compact convex gradient set (Lemma 2.1). The exact ridge and
coupled-segment formulas in this package are derived independently in the
README; those paper results do not certify the production ray algorithm.

The previously consumed README, source, numerical outputs, summary and
completion receipt remain unchanged. This note only makes the interval scope
and cited location explicit.
