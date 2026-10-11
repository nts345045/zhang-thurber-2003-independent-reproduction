# Closed diagnostic and local-coordinate results

The exception-only variant reproduced both original integration failures.
Every original structured field except the enriched exception was unchanged,
and both full identifier companions were identical. The first failed stored
partitions were `[1-2^-63,1]` for LOM24104 (piece 3, partition 1), and
`[1-2^-58,1]` for LON8670 (piece 0, partition 1), using zero-based indices.
Their widths are two and 64 working spacings immediately below one. Exact
arithmetic on the saved operands places the failed nodes 0.47447 and 0.33917
spacings above the lower endpoint; each rounded to that endpoint. These match
the prior z=3 km sliver candidates. Later z=0 candidates were not reached.
The failures retained 266/46 completed samples and 11/1 completed subpieces;
neither failure produced an integral or display.

The separate local-q version passed the unchanged **58+24 checks** and all
four new tiny-partition checks. For a constant-speed vertical ray ending at
`z=-2^-63 km`, the exact lower-plane length mass is `2^-127 km`.
Its returned value is `0x8.000000000000001p-130`, one working ulp above
`0x8p-130`. The positive mass, action and two-subpiece/48-sample inventory
pass the unchanged relative allowance `512 epsilon`. This is an independent
analytic retention check, not an error certificate.

Exactly one local-q observer call per original case then completed:

| Case | Pieces / subpieces / samples | Travel time (s) | Existing-reference comparison (s) | 8/16 action difference (s) |
| --- | --- | --- | --- | --- |
| LOM24104, bottom guide | 6 / 15 / 360 | 13.315127513112486 | Above the saved interval by about 8.15e-20 | 3.49e-13 |
| LON8670, turn | 5 / 8 / 192 | 3.6600250681424327 | −2.98e-16 from the saved binary64 scalar | 1.50e-9 |

LOM uses the existing exact time enclosure. LON has no saved time enclosure;
its scalar discrepancy gives no interval minimum-time ordering. The comparisons
include construction and working arithmetic, not quadrature alone. No new
reference calculation or retry was made.

Both cases retain all 288 nodal length and velocity-kernel entries. Exact
saved arithmetic reproduces the observer's rounded length-sum and velocity
scaling identities. Length residuals are −2.08e-17 and −1.73e-18 km; velocity
scaling residuals are zero and 4.34e-19 s. The largest 8/16 velocity-kernel
differences are 1.61e-12 and 6.87e-9 s²/km. These are diagnostics, not
independent all-node error bounds.

Backward-at-start discrepancies are 3.47e-18/8.13e-20 km; forward/backward
midpoint discrepancies are 6.99e-18/8.67e-19 km. Reanchoring can change rounded
point/cell placement near a face. These observations do not bound agreement
with every original face root. All 21 inherited fields, including the supplied
curve construction, remain exact matches to the failed records.

LOM24104 binds event `quakeml:NC.anss.org/Event/NC/20091537`, origin
`quakeml:NC.anss.org/Origin/NC/2658134`, and `NC.HQR..EHZ`
(`FDSN:NC_HQR__E_H_Z`), channel epoch 1989-07-11T19:55:00 to
1990-03-24T19:55:00. LON8670 binds event
`quakeml:NC.anss.org/Event/NC/10090456`, origin
`quakeml:NC.anss.org/Origin/NC/2644764`, and `NC.JHL..EHZ`
(`FDSN:NC_JHL__E_H_Z`), epoch 1989-10-19T20:40:00 to
1990-08-21T18:35:00. Full coordinate, native-row, reference and intersected
metadata-epoch records remain in [identifiers/](identifiers/).

This resolves the observed failure for these two prescribed curves. It does
not supply general branch selection, native all-node certification,
optimized-source derivative validation, a new inversion, or a panel-status
promotion. Original published failures remain unchanged.
