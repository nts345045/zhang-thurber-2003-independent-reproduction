# First-arrival initialization plan

This is a proposed numerical change, not an implemented or validated solver.
The active production executable, inputs, and configuration remain unchanged.

For the current positive, isotropic velocity field, the first arrival minimizes
the path action `T = integral ds/v(x)` within the declared model domain. Its
travel-time field satisfies `|grad T| = 1/v`, with zero time at the receiver.
A monotone fast-marching discretization supplies a spatially consistent way to
search that field, including refracted branches which straight-path local
bending can miss. Sethian's primary account describes the causal upwind update
and first-arrival viscosity solution; the seismology application gives the
three-dimensional formulation. [Sethian's method overview](https://math.berkeley.edu/~sethian/2006/History/hold.chart.overview.fastmarching.html),
[Sethian and Popovici's seismology account](https://math.berkeley.edu/~sethian/2006/History/chart.applications.seismology.html).

## Minimal numerical scope

1. Sample `s(x)=1/Grid::sample(x).v` on a uniform auxiliary grid. The existing
   model interpolates velocity, so interpolating nodal slowness instead would
   change the physical model. Retain the same rectangular domain. Do not assign
   zero time to its outer faces; only the receiver initializes the wavefront.

2. Implement the first-order, positive-speed Godunov update. For each axis let
   `a_k` be the smaller available accepted-neighbor time. The trial value solves
   `sum_k [max(T-a_k,0)/h]^2 = s(x)^2`. Sort the available values and add axes
   until the positive quadratic root is causal with respect to the included
   neighbors. A minimum heap accepts the smallest trial time. Missing neighbors
   outside the model are unavailable, rather than assigned fictitious times.

3. Preserve the exact off-grid receiver coordinate. Seed the surrounding cell
   vertices with the continuous action from that coordinate, initially as trial
   candidates that may be improved before acceptance. This introduces a local
   approximation whose size shrinks with the auxiliary spacing; it must be
   tested for off-grid sources and boundaries. Snapping receivers to a grid
   node would introduce an avoidable coordinate and timing error. Point-source
   initialization is a known accuracy issue in Cartesian fast marching.
   [Stanford Exploration Project's primary derivation](https://sepwww.stanford.edu/sep/sergey/sepsergey/fmpolar/paper_html/node3.html).

4. Backtrace from each exact event coordinate down the receiver travel-time
   field. In smooth regions the spatial path follows
   `dx/dl = -grad(T)/|grad(T)|`. Use a step controlled by the auxiliary spacing
   and check travel-time descent. Near shocks or an interpolation stall, an
   accepted-neighbor/simplex descent provides a causal fallback; a zero or
   ambiguous gradient is not a reason to silently substitute the original
   straight ray. Finish at the exact receiver through its source cell. Record
   extraction failures and branch provenance.

5. Resample that polyline for the existing variational bending, preserve exact
   endpoints, and evaluate its final action and derivatives in the original
   trilinear-velocity model with the existing split-cell quadrature. Bend the
   direct seed as well and retain the lowest action found. Preserve the selected
   path's convergence flag and the time difference between candidates. A lower
   but nonstationary candidate remains evidence that the forward/derivative
   calculation is unfinished; selecting a slower converged candidate does not
   establish a first arrival.

Bending removes the auxiliary finite-difference time formula from the reported
travel time. It does not automatically remove auxiliary-grid branch-selection
error or prove that the local optimizer found the best path in that branch.
Every feasible path gives an upper bound on the continuum minimum, apart from
quadrature error. A raw first-order FMM value is not asserted to be a rigorous
lower bound. Agreement of finite candidates and grids is convergence evidence,
not a global-optimum certificate.

## Reuse, identities, and cost

The prepared data contain 372 native receiver epochs and 62 NSLCs at exactly
37 distinct xyz coordinates. Isotropic reciprocity allows one receiver field
per distinct coordinate and velocity model. Numerical reuse must map back to
each original row; it must not merge provider identities or manufacture union
epochs. Every output ray retains its event/origin, pick/arrival, channel, native
epoch, and source-hash associations.

The full domain at 0.5 km spacing has 141 by 121 by 43 = 733,623 auxiliary
nodes. Thirty-seven double-precision time arrays occupy about 217 MB before
heap, status, and path storage. At 0.25 km, each field has 5,756,285 nodes;
initial refinement checks can use selected receivers and analytic cases.
Auxiliary speed samples are shared among stations for one velocity model.

Cache keys must include velocity-grid values, geometry, auxiliary spacing, and
the exact receiver coordinate. A fixed-velocity location run can reuse fields
throughout all event updates. Velocity inversion produces a new field problem
for every distinct trial velocity model. Reusing old fields as seeds is possible,
but it supplies no fresh first-arrival search in the new model and must be
labeled and separately tested. This cost should be measured in isolated
components before adding it to every line-search trial.

## Discriminating validation

- Check homogeneous media against Euclidean travel time for off-grid sources,
  multiple orientations, and receivers near domain faces. Test reciprocity,
  exact endpoint preservation, and source/model derivatives after bending.
- Use the constant-top-layer over increasing-velocity counterexample. Sweep
  offsets on both sides of the independently calculated direct/diving crossover;
  compare with the full first-arrival envelope from one-dimensional Snell-law
  travel-time integrals, not one selected stationary branch. Retain the existing
  constant-gradient analytic cases as additional checks.
- Separate auxiliary-grid refinement from bent-path refinement. Compare 1,
  0.5, and 0.25 km auxiliary grids while holding bending settings fixed, then
  refine path spacing separately. Report candidate branch, final action, path
  stationarity, and derivative error. Keep existing component tolerances; a
  failure calls for resolving the error rather than relaxing its threshold.
- Test a smooth lateral fast region with more than one plausible route to
  expose grid-direction or backtrace bias. For this case use refinement and
  independently converged reference calculations, and label the lack of a
  closed-form global certificate.
- Apply the isolated comparison to the 186 identified final-DD shallow-endpoint
  rays and a representative set of other rays. Preserve both candidate times
  and all native associations. The DD top layer is only approximately constant,
  so the analytic counterexample alone does not determine these answers.
- Check finite-difference derivatives away from branch crossings. At a crossing
  the minimum travel-time envelope may be nondifferentiable; report one-sided
  behavior and competing branch times instead of interpreting every centered
  difference mismatch as quadrature error.

## Alternative initializers

A Dijkstra solve is exact for its chosen graph. A graph whose vertices are only
the coarse velocity-model nodes restricts turning locations and directions,
which can miss a shallow refraction branch. Even a uniformly refined graph with
only a fixed set of edge directions retains directional bias; the continuous
upwind quadratic update is what distinguishes the isotropic eikonal method.
Such graph paths can be useful extra candidates, but their graph optimum alone
does not identify the continuum first arrival.

A small collection of imposed dive depths may recover the present analytic
example. It does not provide a convergent spatial search, and can miss a narrow
branch near the critical offset or a laterally diverted route. It is useful as
an adversarial check on FMM/bending, not as the completeness argument for the
forward solver. Neither approach justifies adding geographical source bounds
or changing damping to conceal a forward-model branch error.
