# Completed native diagnostic attempts

| Selected ray | Constructed pieces | Integration outcome | Largest intended/stored depth-join difference |
| --- | --- | --- | --- |
| LOM24104 bottom guide | 6 | Quadrature node rounded to a partition endpoint | 8.673617379884035e-19 km |
| LON8670 turn | 5 | Quadrature node rounded to a partition endpoint | 1.3010426069826053e-18 km |

The one compilation succeeded. Each observer completed with nonzero exit and
retained its explicit failure result. Both constructors completed, so neither
failure came from the angular-turn construction guard. Both calls reached the
unchanged integration kernel, which rejected an unrepresentable quadrature
sample. There were two integration attempts, zero completed integrations,
zero display calls and no retry. The full scientific results and constructed
curves are in [results/](results/), with a [compact summary](results/summary.json).

The recorded depth-join differences show working-arithmetic displacement from
intended layer interfaces. Their magnitudes do not by themselves identify the
precise failing partition or prove causation: the observer did not retain an
in-progress partition or sample index when the integrator threw. Any saved-only
localization must distinguish candidate tiny intervals from an observed
failure location. No additional integration was used to repair or localize
these outcomes.

Independent exact arithmetic on the saved endpoints identifies these candidate
slivers (piece indices are zero-based):

| Ray | Piece and intended face | Stored coordinate |
| --- | --- | --- |
| LOM24104 | Piece 3 end, z=3 km | 3 - 2^-61 km |
| LOM24104 | Piece 4 end, z=0 km | -2^-60 km |
| LON8670 | Piece 0 end, z=3 km | 3 + 2^-62 km |
| LON8670 | Piece 4 begin, z=0 km | +2^-61 km |

These stored overshoots create very short face-crossing intervals under the
unchanged full-cut geometry. The linear LON piece's exact parameter to z=0 is
1/1939213970748716544. Depth-span fractions for arcs are not angular-parameter
estimates. [The saved diagnosis](results/saved_geometry_diagnosis.json) retains
every mismatch and explicitly leaves the failed-piece/sample fields null.
It used no trigonometry, root location or integration. Receiver closure was
7.20e-18 km for LOM and 1.32076e-12 km for LON; neither endpoint was repaired.

Exact piece continuity was preserved, and no endpoint, grid coordinate, guide
or velocity was snapped or clamped. The bottom guide used the selected
reference interval's midpoint; the turn used the saved phase-speed rational.
The supplied branch evidence remains separate from this component's explicit
not-assessed completeness status and selected-curve-only derivative status.

The invented homogeneous and affine controls validate the declared component
on their fixtures, but these two failures limit its demonstrated native
applicability. No native action, nodal-kernel accuracy, stationarity, source
derivative or production first-arrival claim follows from these attempts.
