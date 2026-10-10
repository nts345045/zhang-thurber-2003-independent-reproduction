# Independent double-difference tomography

## Scope and provenance

The scientific specification is Zhang and Thurber (2003), BSSA 93,
1875–1889, doi:10.1785/0120020190. The full manuscript text was read through
its author-posted ResearchGate transcription (publication 215754286), after
the publisher returned HTTP 403. No original implementation, simulation output,
plotting scripts, or figure files have been used. The initial attempt excluded
observational inputs. The user subsequently required authoritative observations
and metadata, with SEED codes and resource IDs retained in saved records.
The permitted repository guidance files were retrieved from the two URLs in
`reference/task.md`. Reference pages were accessed on 2026-10-09.

The synthetic experiment in the publication uses actual Loma Prieta source
and receiver coordinates. They were not tabulated in the article or used in
the initial attempt. The existing generated geometry cannot reproduce that
experiment exactly. Historical USGS/EarthScope retrievals now establish data
access, but the exact manuscript subset remains unidentified. The user has
authorized an independently selected authoritative subset with its differences
reported. That resolves the cohort-selection question. At the user's request,
metadata investigation preceded station exclusion. The NCSN master history
supplies the missing CMW1 operation epochs; all 42,236 picks now match uniquely.
No examined written source establishes inclusion or exclusion of the four
investigated borehole stations in the paper. Their membership remains unknown.
The evidence and adopted vertical interpretations are recorded in
`data/authoritative/stations/`; they do not establish independent survey accuracy.

## Authoritative subset and conditional resolution

`data/authoritative/README.md` and the acquisition manifests define the Hayward
time, magnitude, spatial, depth, and pick-quality selection. The current catalog
query selects 1,768 earthquakes; 42,236 NC P picks have identifiable provider
event/origin/arrival/pick IDs, concrete SEED channel codes, and reported symmetric
uncertainty no larger than 0.15 s. Every raw reply is preserved with its query,
retrieval time, hash, and identifier attachment. These are current archive
records, not a reconstruction of the manuscript's exact cohort.

`prepare_hayward.py` joins picks to effective channel epochs before preparing
numerical indices. It refuses incomplete acquisition and nonunique metadata
matches. Its additional selection excludes known nonpositive provider
association weights, receivers outside the model's horizontal bounds, and events
with fewer than eight remaining picks. Catalog pairs share at least eight
channel locations and have separation below 10 km. An explicitly independent
greedy selection processes pairs in ascending separation and caps each event's
undirected degree at ten. It reports disconnected components instead of forcing
connections. Each side retains its native channel epoch and metadata provenance;
an epoch change alone does not move a receiver. Cross-epoch pairs are flagged
because common geometry does not establish unchanged timing calibration. A strict
same-epoch sensitivity subset is retained in `data/development/hayward_epoch_restricted/`.
These choices need not reproduce the original pairing algorithm. In particular,
an undirected degree cap of ten bounds the number of differences by five times
the available absolute-pick count, so this interpretation cannot recover the
paper's reported difference count from its reported absolute-pick pool.

Time observations are pick time minus that event's reference catalog origin.
The source time unknown is a correction to this reference. Differences subtract
those two elapsed times and preserve both events, origins, arrivals, and picks.
The common NSLC and exact reported position identify the receiver; each pick's
epoch remains separate. Numerical event outputs
retain the catalog resource IDs as references; updated numerical coordinates
do not claim to be provider-issued origins. The reproduction selection omits
only documented study exclusions in `study_station_policy.csv`; unknown membership
does not cause exclusion. `--selection additional` restores those stations'
eligibility under identical metadata, quality, and domain checks, in a separate
output directory. No original or acquired record is deleted.

CCH1, CGP1 and CSU1 use StationXML Channel/Elevation values 107, 219 and 375 m
as provider-declared sensor elevations. Burial depth is retained but is not
subtracted again. CMW1 uses historical ELEV=214 m as receiver elevation under
an explicit sensor-elevation interpretation; agreement with later StationXML is
not independent validation. Its historical burial depth remains unknown. The
provider's shared geoid convention for elevations and earthquake depths is
retained without a guessed ellipsoid conversion. Conflicting BSL wellhead tables
and their datum labels are documented alongside USGS terrain checks.

The field grid retains the written horizontal and depth nodes, with
one additional level above the geoid to contain elevated receivers. The starting
profile is a continuous-gradient adaptation of Waldhauser and Ellsworth (2002),
Table 1: depths 0, 1, 3, 6, 14, 25 km and velocities 3.77, 4.64, 5.34, 5.75,
6.22, 7.98 km/s, interpolated onto the inversion grid and constant above zero.
This differs from a discontinuous layered model and is not verified as the exact
target-paper starting model. Current geoid depths are used without inventing a
conversion back to the historical velocity-model depth datum.

Catalog-only DD uses absolute/catalog row multipliers 1/0.1 initially, then
0.1/1. It does not enter the waveform-dominated stage without waveform data.
The additional prior multiplier is 0.05 s divided by reported pick uncertainty;
the pair uncertainty is the square root of the sum of the two squared values.
Differences reuse picks and are correlated; this objective is not a likelihood
of independent differences. For the conditional noise calculation only,
reported symmetric uncertainty is interpreted as independent one-standard-
deviation error. The provider supplies no confidence levels establishing that
calibration. Source and receiver identities survive event, residual, and ray
diagnostic outputs. Sparse ray calculation uses observed pairs only.

`dd linearize` exports the unweighted absolute-arrival Jacobian at a saved model,
along with identified row and column mappings and ray stationarity diagnostics.
`resolution_hayward.py` partitions its weighted Jacobian into source blocks E
and velocity block B. With the same spatial smoothing L and column-scaled
damping as the solver, it forms source normals C and cross blocks D = E^T B.
The velocity Schur complement is H = B^T B + L^T L + damping - sum(D^T C^-1 D).
Writing Q = B^T B - sum(D^T C^-1 D), its velocity-parameter resolution is
H^-1 Q. Noise propagation uses N = B^T B - 2 sum(D^T C^-1 D) +
sum[(C^-1 D)^T E^T E (C^-1 D)], and covariance 0.05^2 H^-1 N H^-T.
The script preserves the C++ fallback scaling for tiny or zero columns. A direct
small joint-matrix comparison, including an unsensed source-depth column,
agrees within 3e-16 for resolution and 3e-17 for noise covariance.

This diagnostic treats weights and rays as fixed. It is an absolute-data
linearization at the DD model, not full DD resolution or the original simul2000
calculation. Propagated picking noise excludes regularization bias, correlated
station errors, catalog selection, nonlinear effects, and ray errors. Small
propagated uncertainty therefore does not establish accurate velocity.

## Physical problem

Use Cartesian coordinates in km, positive depth downward, velocity in km/s,
and time in s. An isotropic, stationary medium supports geometric P rays.
The predicted arrival is origin time plus the line integral of reciprocal
velocity along a stationary ray between the source and receiver. There are
no wave amplitudes, converted phases, reflections, attenuation, or temporal
velocity variations in this model. Endpoints are fixed during ray tracing.
Paths are confined to the rectangular model domain; no periodic or reflecting
boundary is imposed. No extrapolation outside that domain is permitted.

Joint inversion linearizes arrival residuals in three source coordinates,
origin time, and nodal log slowness. A differential datum subtracts the two
predictions and their complete derivative rows at a common receiver. Absolute
arrivals retain sensitivity outside source clusters. Source origin times and
absolute locations are constrained by absolute arrivals; no cluster centroid
is fixed as extra information.

## Numerical implementation

`src/core.hpp` interpolates nodal **velocity** trilinearly. Each ray segment
is split at model grid planes and its travel time integrated with eight-point
Gauss quadrature. The derivative of this quadrature with respect to each
velocity node is integrated with the same interpolation weights. Converting
to log-slowness increments gives the factor minus the current nodal velocity.
The source derivative is the derivative of the endpoint segment integral.
This converges to the local ray-direction formula for stationary resolved rays.
The initial run used two-point quadrature. A later crossing-segment test found
an objective/gradient discrepancy of 0.000119 s/km because finite quadrature
did not accurately integrate the moving grid cuts. Eight points reduce that
test discrepancy to 5.6e-12 s/km. The variational derivative is still a numerical
integral, not an algebraically exact derivative of arbitrary finite quadrature;
a three-dimensional crossing test also checks its consistency.
Interpolation gradients use paired nodal-velocity differences, preserving an
exactly constant coordinate direction without cancellation roundoff. This is
algebraically the same trilinear derivative; it introduces no extra smoothing.
For the x-only sandwich, an independent monotone-ray Snell reference provides
travel time and the endpoint slowness vector without vertex optimization.
A perturbation sweep is retained in `data/development/`: at the 600-iteration
setting, source finite-difference errors are below 0.000153 s/km at 0.1,
0.03, and 0.01 km, while 0.001 km amplifies ray-discretization/optimization
errors to 0.00350 s/km. More iterations do not ensure finite-difference
convergence. Source checks use 0.01 km with the unchanged
0.003 s/km tolerance; the fixed-path velocity perturbation remains 0.001 km/s.

The independently written ray tracer minimizes Fermat travel time with
limited-memory BFGS (eight secant pairs) and Armijo backtracking. Its initial
inverse-Hessian metric is the inverse fixed-endpoint weighted path Laplacian,
with segment weights equal to midpoint slowness divided by segment length.
This positive definite metric approximates transverse ray stiffness without
adding a smoothing penalty or restricting paths. Secant scaling is
`gamma = (s^T y)/(y^T B y)`, where `B` is the inverse Laplacian. The initial
path is straight with segments no longer than the configured spacing.
This variational discretization replaces the article's specific pseudo-bending
implementation. It finds a local stationary path; global first-arrival
optimality in complicated media is not guaranteed. Active boundary directions
are projected onto feasible tangents, with the first trial step limited by
the nearest model face. Interior nodes separated by less than 1e-8 km are
merged, preserving endpoints and clearing the quasi-Newton history. These
are numerical tolerances far below the ray spacing. Projected and raw
gradients, convergence flags, merge counts, and ray iteration limits are
recorded explicitly. Rays for different source/receiver
pairs are computed with OpenMP.

The numerical correction and analytic isolation experiments are recorded in
`data/development/ray_optimizer_audit/README.md`. All 48 current component
checks pass. Forward retracing of the frozen baseline models improves but does
not eliminate nonconvergence. The saved synthetic inversions have not been
regenerated with this correction. The independent Hayward DD inversion uses
the revised kernel and has complete numerical outputs; the absolute-data and
fixed-model runs and the full comparison workflow remain pending at this
checkpoint. Local stationarity also fails to identify the earliest branch in
the constant-layer/gradient counterexample in
`data/development/first_arrival_audit/`. An experimental FMM initializer improves
some cases but retains near-crossing failures and is not part of these inversions.

The sparse joint system is solved by an independently implemented LSQR
bidiagonalization. Columns are normalized before adding damping equations.
Damping therefore penalizes the scaled increment. Each solve records the
iteration count and the achieved ratio ||A^T(Ax-b)||/||A^T b|| for the scaled,
augmented damped system; the target is 1e-8 with at most 600 LSQR iterations. First differences of the
**final log slowness**, divided by node separation, penalize roughness in all
three directions with equal weight. This is an explicit interpretation of
first-order smoothing; the paper does not fully specify scaling or whether
the final model or only its perturbation is smoothed. Consequently a weight
of 5 need not have the same effective strength as in the publication.

Rows use the paper's staged absolute/catalog/precise weights
(1, 0.1, 0.01), (0.1, 1, 0.01), and (0.001, 0.01, 1). Our explicit choices
for unspecified details are six nonlinear iterations per stage, damping 0.1,
and an event-distance taper [1-(distance/20 km)^2]^2 below 20 km, zero above.
A residual biweight uses [1-(residual/cutoff)^2]^2 below the cutoff, zero
above. The cutoff is six times 1.4826 times the median absolute residual
for each data type, with a 0.01 s minimum. These robust weights multiply
rows directly, rather than being interpreted as inverse variances. Within
a data type, the synthetic baseline uses unit measurement quality weights;
the authoritative Hayward subset uses the uncertainty multipliers stated above.
Shared-station noise
and the correlation among catalog differences are not whitened. Reported
residual RMS values are unweighted for comparability across stages.

When two interpolated path-length coefficients differ by less than 0.005 km,
the corresponding differential model coefficient is zeroed, as described
in the manuscript. This deliberate sparsification is only applied to
inversion derivatives, not to travel-time prediction.

A backtracking joint update must decrease the current weighted data misfit
plus roughness while keeping all velocities positive. Trial source locations
are projected onto the closed rectangular grid domain before evaluating
the objective. This enforces the stated forward-model domain and allows
other sources to update when one reaches a boundary. Weights are held fixed during each line search and recomputed
on the next iteration. No target velocity, event location, or published
result enters this acceptance decision. Physical velocity bounds and ad hoc
maximum source steps are not imposed.

## Synthetic experiment: specified and assumed quantities

The article's written sandwich profile is 6 km/s for x<=0, a linear fall to
4 at x=1, 4 from x=1 to 5, a linear rise to 5 at x=6, and a linear rise to
6 at x=38. It is independent of y and depth. Our forward grid adds the
breakpoints x=1 and 5 to the article's coarser inversion grid so that the
true model is represented exactly. The inversion x nodes are -35,-15,0,2,4,
6,20,35; y nodes -60,-40,-20,0,20,40; and depth nodes 0,3,7,11,16 km.
The domain ends at x=35, before the final profile breakpoint.

Unpublished choices are explicit in `configs/synthetic.cfg`: 120 sources,
32 surface receivers, seed 2003, a homogeneous 5.5 km/s starting model,
and independent 0.6 km Gaussian starting-location errors (depths clipped
to 0.5–15.5 km only during construction). Origin-time starting errors have
standard deviation 0.05 s. The initial model substitutes for the referenced
Dietz–Ellsworth layered model, whose numerical values are not tabulated in
the target paper. This substitution must remain a stated limitation.

Half the sources sample x in [-4,8] km, half [-15,25] km; all sample y in
[-45,25] and depth in [2,13] km independently and uniformly. Stations form
a jittered rectangular surface array across x=[-30,30], y=[-55,35] km.
These are experimental-design assumptions, not reconstructions from plots.
All sources are observed at every station. The published synthetic count
and full observation mask are not specified in the text used here.

Forward times are rounded to 0.01 s. Absolute picks add station-constant
uniform noise in [-0.3,0.3] s and independent Gaussian noise of standard
deviation 0.04 s. Catalog differences subtract these noisy picks. Precise
synthetic differences subtract the rounded times before added pick noise.
All pairs within 20 km in the constructed true geometry are selected once;
the distance taper uses current inferred coordinates during inversion.
The manuscript's wording leaves noise/differencing order ambiguous; the
chosen order makes precise differences more accurate, as its text requires.
The saved arrivals expose each component separately.

## Validation

`dd validate data` checks homogeneous ray times and derivatives, interpolation
partition of unity, reciprocity, bent-ray time reduction, segment refinement,
source and velocity finite differences, cancellation of identical-event and
station-static terms, sparse transpose consistency, and an exact LSQR system.
These checks do not establish global ray optimality or field-data recovery.
Inversion recovery, starting-profile sensitivity, final-model ray refinement,
and finite-difference diagnostics are recorded with the generated panel audit.

## Fixed-model comparisons

The `loc1d` and `loc3d` modes retain absolute arrivals as well as both
kinds of differential data, but omit velocity unknowns. They test the
sensitivity of location estimates to the assumed medium. They are not
reimplementations of every gauge and data-selection convention of hypoDD;
in particular, an absolute-time constraint replaces a centroid-only gauge.
`loc1d` uses the declared homogeneous initial velocity, and `loc3d` uses
the independent true grid. Published Table 1 is a scale reference, not
an exactly matched benchmark for these comparisons.

The small `configs/recovery.cfg` experiment removes station and pick noise,
retains time quantization, and starts 16 events with 0.25 km Gaussian
coordinate perturbations. Its fixed-true-model inversion must reduce median
3D source error; the final error and residual are recorded explicitly.

When no trial step is accepted, the model and residual weights are unchanged.
Further iterations in that same stage would repeat the identical calculation,
so the final implementation advances to the next weight stage (or stops if
there is no different stage remaining). This saves work without altering the
state reached at any weight transition. Histories retain original iteration
indices, so skipped repetitions appear as gaps.

## Starting-profile sensitivity and joint limiting test

`configs/synthetic_lom.cfg` and `synthetic_lon.cfg` retain all main-experiment
geometry, observations, and inverse settings except the initial velocity.
They sample the two written gradient adaptations tabulated in USGS Open-File
Report 93-578 (Table 4) at our inversion-depth nodes. Full values and the
adaptation caveat are in `reference/specification_notes.md`. Both are tested
with joint DD inversion; neither is asserted to be the target's exact start.

`configs/joint_recovery.cfg` uses 16 events and 16 stations, homogeneous true
velocity 6 km/s, initial velocity 5.7 km/s, and source-coordinate perturbations
with standard deviation 0.15 km. Observations are analytic distance/6 with
no rounding or added noise; thus their generation does not use the ray tracer.
Both source and velocity unknowns are enabled. Fixed acceptance conditions
require reduced median 3D source error, reduced illuminated-node median
velocity error, at least tenfold absolute and precise RMS reduction, no
boundary sources, no accepted objective increase, and nonzero updates to
both source and velocity. Results and individual gate outcomes are reported
without relaxing the criteria.

The true and final standard/DD grids each have a 32-ray production-versus-
refined comparison (half spacing, up to 1000 iterations). Eight sampled
rays additionally receive source-coordinate central finite differences with
0.01 km increments where both perturbed points stay in the domain. These
checks measure numerical sensitivity, not global first-arrival uniqueness.
A small travel-time difference is insufficient to infer derivative convergence;
raw and projected gradients and finite-difference discrepancies are retained.

The CSV `error` field in model slices is recovered minus true velocity.
Figure 3c/d plotting explicitly negates it to match the target manuscript's
prose convention, true minus recovered. The five plotted depths are the
independently generated grid-depth slices; their count is not a verified
reconstruction of the original figure layout.
