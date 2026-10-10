# Independent double-difference tomography investigation

Independent C++/OpenMP implementation of the ray-based inverse problem in
Zhang and Thurber (2003), *BSSA* 93, 1875–1889,
[doi:10.1785/0120020190](https://doi.org/10.1785/0120020190).

This is a research reproduction attempt, with explicit limits. The report
retains a synthetic baseline using generated source/receiver geometry. The
original task excluded source observations; a later authorized Hayward catalog
workflow has now completed absolute-data tomography, catalog-DD tomography,
and fixed-velocity catalog-DD relocation. Figures 4–11 provide independently
generated partial counterparts. Their saved diagnostics retain unresolved ray
and nonlinear-convergence failures. A separate guarded catalog-only inversion
stopped at its first trial model, before accepting any update. This remains a
partial scientific checkpoint.

A separate catalog-only backtracking attempt has now preserved two accepted
states. The [first-update plot](figures/hayward_accepted_update_001.pdf) shows
changes from the identified starting model; the
[second-update package](data/development/hayward_second_accepted_update_figure_001/RESULTS.md)
and [comparison plot](data/development/hayward_second_accepted_update_figure_001/figure/accepted_update_2_minus_1.pdf)
show the next state's velocity changes and event movements relative to the first.
The run remains incomplete; these accepted states do not establish final
convergence or updated-model ray and source-derivative accuracy.

On 2026-10-09 the user revised that restriction: real station and earthquake
data, including metadata, must now come from authoritative sources, starting
with USGS and EarthScope web services. All saved records must retain SEED
codes and resource identifiers as applicable. The independent-code and
figure-input restrictions still apply. Successful historical catalog, phase,
and station metadata queries are saved in
[the acquisition record](data/authoritative/discovery/README.md).
The user subsequently authorized a documented authoritative subset with its
differences reported. That decision resolves the exact-cohort selection hold.
The independent selection, metadata matching, and exclusions are recorded in
[the subset record](data/authoritative/README.md). The exact paper event/station
lists remain unidentified; a new subset does not establish exact replication.

The completed Hayward retrieval contains 1,768 selected events and 42,236 P
picks. Metadata investigation recovered NC.CMW1's historical channel operation
epochs from the authoritative NCSN station history; all picks now match uniquely.
NC.CCH1, NC.CGP1, and NC.CSU1 use provider-declared sensor elevations without a
second burial subtraction. CMW1's historical elevation is interpreted as sensor
elevation under an explicit assumption. [The metadata record](data/authoritative/stations/README.md)
preserves conflicting historical tables, datum statements, and all identities.
Written study membership remains unknown for all four stations; none is excluded
on a manuscript-membership claim. Separate preparation selections preserve
documented study exclusions for a later additional-data comparison.

Independent ray-kernel corrections now improve quadrature accuracy and
optimizer conditioning. [The numerical audit](data/development/ray_optimizer_audit/README.md)
records 48 passing component checks and remaining failures when retracing
frozen baseline models. The saved synthetic inversions retain their original
kernel; the Hayward runs use the revised kernel. A separate
[first-arrival audit](data/development/first_arrival_audit/README.md) shows that
local ray stationarity can select a late branch. The original first-order FMM
initializer retains near-crossing failures. A [controlled refinement](data/development/fmm_order_comparison.md)
combining switched second-order updates with symmetric receiver seeding passes
all 37 retained analytic checks at 0.0625-km grid/path spacing. This finite suite
does not certify general first arrivals. A separate [oblique 3D affine check](data/development/fmm_rotated_affine_baseline/README.md)
passes all 72 checks; branch completeness in arbitrary 3D media and field
validation remain open.
The corrected initializer and feasible ray directions are integrated and tested
on the `first-arrival-integration` branch. No completed corrected inversion
result is available yet; the completed original workflow retains its frozen solver.
The [fixed-model field comparison](data/development/fmm_hayward_audit/README.md)
finds two faster candidates exceeding 1 ms among 186 selected shallow-endpoint
rays; it does not quantify the resulting inversion bias or certify first arrivals.
A [controlled repeat](data/development/fmm_hayward_order2_closed/README.md)
resolves the extraction failure while preserving one local-stopping failure
and 22 strict endpoint discrepancies at roundoff. An [isolated boundary-ray
audit](data/development/ray_stopping_i775_budget_path/README.md) traces the slow
stopping to repeated loss of the search metric after boundary projection;
longer runs satisfy the unchanged combined stopping rule but do not establish
derivative accuracy.

An [independent 1D reference](data/development/first_arrival_1d_enumeration/README.md)
passes 250 original and 106 added component checks, with discovered failures
and their corrections retained. All 32 saved initial Hayward rays have complete
branch enumeration and valid distance closure. Production travel times exceed
the continuous reference by 3.82--143.95 microseconds; the refined range is
1.32--37.48 microseconds. This checks the initial sample only. Interval root
enumeration does not certify floating-point ordering of nearly tied arrivals.

The [completed third preflight](data/development/hayward_first_arrival_003_review/README.md)
initializes all 14,262 Hayward rays but retains 139 local stopping failures,
despite a passing 32-ray stopping sample. An identified near-interface path
omits a descent variation that appears when its long segment is subdivided;
exact integration rules out quadrature error at the tested scale. Refining
all 139 failed paths to 0.125 km resolves their local stopping flags and
meets the existing 25-microsecond travel-time limit. However, 16 source-vector
errors still exceed the existing 3e-6 s/km analytic limit. Further refinement
to 0.03125 km brings all 139 within both limits; the
[four-variant comparison](data/development/hayward_initial_failure_refinement.md)
preserves every failed result. The complete initial-model reference also
finds a locally converged ray 2.232 ms late, with a source-vector error of
0.033571 s/km, outside the 139-ray subset. The [identified branch
comparison](data/development/initial_ray_first_arrival_003_14099_audit001/README.md)
shows that path refinement approaches a deeper stationary arrival, still
2.185 ms late. At 0.03125 km path spacing, a [0.125 km initialization
field](data/development/initial_ray_first_arrival_003_14099_field0125001/README.md)
recovers the earlier branch with errors of 0.333 microseconds and
5.98e-9 s/km. The [diagnostic figure](figures/diagnostics/hayward_branch_failure.pdf)
shows both controls. The [fourth full initial comparison](data/development/hayward_first_arrival_004_1d_support/README.md)
now passes both unchanged accuracy limits and all local/initializer flags for
all 14,262 rays. Maximum time and source-vector errors are 0.959 microseconds
and 1.782e-6 s/km. The [full-cohort error distributions](figures/diagnostics/hayward_full_initial_accuracy.pdf)
retain the same native observations and references. The separate sampled
refinement also passes [independent accuracy review](data/development/hayward_sampled_accuracy_004_002/README.md).
All 32 travel times and eight source vectors satisfy the same reference limits.
A separately [reviewed guarded DD attempt](data/development/hayward_guarded_dd_launch_plan_001/README.md)
started on 2026-10-10 at 07:37 UTC and stopped after 1 h 53 min when the first
trial model failed the local ray guard. All initializers succeeded, but 181
of 14,262 rays failed local stopping. No inverse update was accepted. The
[failure archive](data/development/hayward_guarded_failure_001/README.md)
preserves the trial and last accepted states separately.
Passing the initial depth-dependent model does not validate subsequent 3D models.
A [matched CMJ replay](data/development/hayward_trial_cmj_old_D_replay_001/RESULTS.md)
exactly reproduces two original failed rays before applying the adopted optimizer.
Both revised rays still fail local stopping after 1,000 updates. Their original
paths contain clusters near an internal velocity ridge; a separate
[saved-geometry calculation](data/development/hayward_cmj_interface_geometry_001/README.md)
and [diagnostic plot](data/development/hayward_cmj_interface_geometry_001/PLOT.md)
identify a normal cusp in reciprocal velocity there. This does not establish
the cause of either failure or certify the paths.
A [fixed-path gradient decomposition](data/development/hayward_cmj_saved_gradient_001/README.md)
reproduces all four saved norms and places 99.29–99.64% of their squared values
in normal components at those near-face nodes. All failed flags remain.
A separate [invented ridge control](data/development/internal_ridge_stationarity_controls_001/README.md)
shows why an ordinary branch gradient can remain nonzero at a true face minimum.
Its slow-face counterexample also shows that zero in the convex hull of branch
gradients can coexist with descent. The 37 exact rational and 62 numerical
checks do not establish stationarity of the nearby CMJ paths or replace their flags.

Within each grid cell, velocity along a straight edge is a polynomial of
degree at most three.
The [completed action controls](data/development/trilinear_action_controls_001/RESULTS.md)
bound reciprocal-velocity integrals and first variations after exact grid-plane
splitting, including changes of incident cell during face-normal motion.
All 80 checks pass: 65 mathematical checks and 15 source/file hash checks.
Independent saved readback verifies 18 exact comparisons. Coupled descent and
deliberately unresolved bounds remain explicit; no production flag changes.
The [completed CMJ calculation](data/development/hayward_cmj_face_action_001/RESULTS.md)
compares two separately identified candidates formed by setting only the
previously selected 31 or 32 node x coordinates to zero. The continuous
trilinear actions decrease by 4.3891e-11 and 8.1650e-11 s. All aligned face
pieces have positive normal slowness jumps, but the available tangent
components still have norms of 3.4637e-5 and 4.1306e-5 s/km. Their lower
bounds exceed both existing gradient scales, even before unavailable face
normals are included. Moving these nodes onto the face therefore does not
resolve the failed paths. Original flags remain false; no optimizer or
displacement step was run, and no source/model derivative or first arrival
is certified. The [independent saved review](data/development/hayward_cmj_face_action_review_001/README.md)
retains exact rational action and tangent-norm bounds with full native identities.

A [single prescribed tangent step](data/development/hayward_cmj_tangent_step_001/RESULTS.md)
from each exact-face candidate decreases the action by a further 2.4666e-10
and 4.6728e-10 s. The maximum node movements are 0.05169 and 0.14095 m.
Both steps satisfy the fixed slope and Armijo checks, with all identifiers
preserved. The saved-output review passes. A separate
[post-step gradient calculation](data/development/hayward_cmj_post_step_tangent_001/RESULTS.md)
reduces the available tangent norms to 3.1087e-6 and 1.2717e-5 s/km, with
unchanged masks. Both remain above the strict 1e-7 scale; the second also
exceeds 1e-5. Neither preceding action change is below the combined stop's
1e-11 s scale. Stationarity, source accuracy and convergence remain unresolved,
and the original failed flags remain unchanged.

A [second full-size tangent trial](data/development/hayward_cmj_tangent_step_002/RESULTS.md)
is rejected for each ray: action increases by 3.0212e-10 and 2.7020e-10 s,
despite negative initial slopes. Exact saved readback confirms both increases
and the rejection decisions. Reusing those directions at
[half length](data/development/hayward_cmj_tangent_half_step_001/RESULTS.md)
decreases action by 1.9272e-11 and 7.5767e-11 s; both trials pass the same
conservative Armijo check. Their maximum movements are 0.04553 and 0.02491 m.
These half-step paths supply the subsequent refinement's starting state. Both action
changes still exceed the combined stopping scale in magnitude.

The [post-half gradient and support check](data/development/hayward_cmj_post_half_step_tangent_001/RESULTS.md)
reduces the available norms to 2.5528e-6 and 6.7473e-6 s/km, with unchanged
masks. Both remain above 1e-7, and the last accepted changes remain above
1e-11 s in magnitude. The exact face-sign checks pass, but the constructed
full supporting vectors do not establish the minimum support residual.
Original failed flags remain unchanged.

A [separate support calculation](data/development/hayward_cmj_post_step_zero_support_001/RESULTS.md)
on the earlier first-step paths proves that zero normal support is feasible
over all 65 aligned face pieces. It retains ordinary entry and exit terms,
giving full-vector norms of 4.4155e-5 and 2.4963e-5 s/km. These are norms of
one feasible vector; they do not establish the minimum support residual or
stationarity. A saved-data checker first failed on equivalent hexadecimal
spellings; its corrected readback passes without changing numerical results.

The [existing C++ evaluator comparison](data/development/hayward_cmj_fixed_polygon_kernel_001/RESULTS.md)
checks all eight saved polygons. Its paired action differences reproduce all
four full-step rejection and half-step acceptance decisions, with errors below
4.0e-17 s. Available gradient-vector errors on the face and first-step paths
are below 1.057e-15 s/km. Each path evaluation takes 1.84–3.42 ms in this
single batch. These results support further bounded iteration with the
existing integration method; they do not certify convergence or source accuracy.
The separate [saved half-gradient comparison](data/development/hayward_cmj_half_gradient_comparison_001/RESULTS.md)
finds available-vector errors below 1.020e-15 s/km on both half-step paths,
using the existing emitted C++ values without rerunning the evaluator.

A [bounded tangent iteration](data/development/hayward_cmj_tangent_iteration_001/RESULTS.md)
starts from those half-step paths and retains the same face-normal search mask.
It accepts 16 and 38 updates after 32 and 152 trials, respectively. The computed
available norms fall to 8.1821e-8 and 9.6184e-8 s/km. Independent readback
reconstructs all 184 rounded trial geometries and decisions. Intermediate
gradient contractions and paired action sums remain recorded evaluator
quantities; the final continuous action and full coupled support require
their separate audit. No original convergence flag changes.

That [final audit](data/development/hayward_cmj_final_tangent_support_001/RESULTS.md)
now bounds feasible full supporting-vector norms below 8.1822e-8 and
9.6185e-8 s/km, including every normal component and ordinary adjacent-edge
term. One common mixture per convex face piece couples its two endpoint
moments. Both bounds satisfy the 1e-7 scale on these prescribed polygons;
their continuous actions decrease by another 3.3921e-11 and 5.8997e-11 s
relative to the half-step paths. The fit proposes feasible coefficients,
without certifying a minimum; the first event reaches its 10,000-sweep cap.
Independent readback passes 90,213 checks. Automatic face-contact discovery,
source/model derivative accuracy and first-arrival selection remain unresolved.

A [saved original-geometry inventory](data/development/hayward_cmj_original_cut_inventory_001/RESULTS.md)
finds all 30 exact grid-plane crossings represented in each original path's
integration partition, with no omitted or spurious cuts. This excludes those
cutoff omissions for the two saved original polygons; it does not establish
quadrature or ordinary-gradient accuracy on arbitrary off-face trials.

A separate [invented contact experiment](data/development/internal_face_contact_controls_001/RESULTS.md)
passes 30 checks: two exact fast-face contacts lower the action, and a slow
face admits normal descent despite zero tangent residual. Temporary contact
retention is a search proposal, with no convergence claim. The same experiment
also measures a 1.1322e-4 s/km endpoint-gradient error when the existing
displacement cutoff omits a tiny crossing, even though its action error is
only 5.2427e-17 s. Accurate action alone therefore does not validate the
derivative. This synthetic omission does not explain the two original CMJ
paths, whose crossing inventories are complete; the production kernel is unchanged.
A [separate exact-partition, explicit-cell diagnostic](data/development/strict_cell_segment_controls_001/RESULTS.md)
reduces that gradient error to 7.4166e-17 s/km and passes 59 structural checks
across nine invented edges. A translated-face example also improves, while
constant-speed and three-dimensional errors remain near 1e-17 s/km. This
combined arithmetic experiment has not been applied to native ray optimization.

An [independent component audit of the unchanged original CMJ paths](data/development/hayward_cmj_original_gradient_bounds_001/RESULTS.md)
finds ordinary gradient norms of 4.9649e-4 and 4.9379e-4 s/km. The saved
C++ vectors differ from the independent bounds by only 1.0564e-15 and
1.0436e-15 s/km. All 6,168 internal components are available, and no exact
physical-box projection is active; 59,290 saved-data checks pass. Thus
component-evaluation error does not explain these large original residuals.
This fixed-geometry comparison leaves automatic contact search, optimized-ray
source sensitivities and first-arrival selection unresolved.

A [bounded backtracking candidate](data/development/hayward_old_kernel_trial_backtracking_candidate_001/README.md)
retains the original, initially validated ray kernel and changes only the
inverse control flow. A pure local-stopping failure at a trial rejects that
fraction; the existing halving, original increment and fixed weights continue.
Current/final, mixed, unexpected and output-write failures remain fatal.
The [invented loop controls](data/development/hayward_old_kernel_trial_backtracking_controls_001/README.md)
preserve 28 all-valid files byte for byte. Separate
[integration checks](data/development/hayward_old_kernel_trial_backtracking_integration_checks_002/README.md)
complete a tiny joint-DD fixture after 20 local rejections, accepting fractions
1/512 and 1/2048. The [190 saved completion checks](data/development/hayward_trial_completion_checks_002/RESULTS.md)
close three preserved bookkeeping gaps, but their launcher test covers only
the child/source prefix; complete final-table integration remains separate.
These controls supply no accepted field update or new scientific stopping criterion.
A [separate launcher](data/development/hayward_old_kernel_backtracking_launcher_001/README.md)
binds the exact source changes to the original initial-model evidence.
Its [62 reviewed checks](data/development/hayward_old_kernel_backtracking_launcher_checks_002/review.json)
include a saved eligibility assessment of all 58,980 observations and 14,262
native rays, plus five process-lifecycle cases with no compiler or numerical
calls. This launcher validation preceded the separate field attempt; successful
execution still requires final scientific diagnostics.
The catalog-only attempt began at 10:52 UTC on 10 October 2026. Its closed
iteration-1 starting-state snapshot now records the first accepted update,
at inverse step fraction 1/8. The fixed-weight inversion objective, including
data residuals and log-slowness smoothing, fell from 1812.15659 to 1409.16490.
The [saved-state figure and reproducible archive](data/development/hayward_accepted_update_delivery_001/README.md)
preserve the accepted grid, all 1,092 event identities and their observation
mappings. This is an intermediate state; the recorded history RMS describes
the preupdate state, and final scientific diagnostics remain pending.
The [lossless evidence archive](data/development/trial_backtracking_evidence_001/README.md)
retains the completed controls, failed attempts and unexecuted drafts.

The revised solver preserves identities in event/residual CSV files and ray
diagnostic mappings, traces observed pairs only, and exports an unweighted
absolute-arrival Jacobian with `dd linearize`. `prepare_hayward.py` prepares the
identified field inputs, `resolution_hayward.py` implements conditional
resolution/noise propagation, and `plot_hayward.py` plots saved field results.
The Hayward input review checks all 58,980 observations and both native epochs
of each differential observation. All 32 sampled initial rays converge at the
configured and refined spacings, but the first full trace converges for only
14,040 of 14,262 rays: 222 fail the configured stopping rule. Later model
convergence must be assessed from the method-specific histories and final
diagnostics. The resolution block algebra
has been checked against a direct joint-matrix calculation, including an unsensed
source column; this component check does not establish field-data resolution.
The prepared full-DD analysis in `resolution_full_hayward.py` propagates shared
catalog-pick errors and distinguishes the masked estimator from unmasked model
derivatives. An [independent algebra check](data/development/catalog_dd_resolution_controls_003/README.md)
passes 35 controls, including repeated picks and ordered-entry column scaling.
Applying it to a corrected saved model still requires that model's full export;
the published field maps remain the conditional absolute-pick calculation.

`dd simulate CONFIG DIR` can generate synthetic observations from supplied
identified catalog geometry and supplied true/initial grids. Its observations
are labeled synthetic and retain geometry identifiers without inventing provider
pick IDs. Invented component fixtures check analytic arrivals, metadata retention,
and unchanged baseline random generation. The [Loma Prieta geometry
archive](data/authoritative/loma_prieta/README.md) now contains 724 selected
earthquakes and 52 historical NC EHZ receiver channels, with preserved candidate
and exclusion records. The initial polygon-truth attempt failed its ray gate;
the explicit continuous-truth simulation described below now completes.
The [completed geometry check](data/development/loma_geometry_preflight/001/README.md)
retains all 104 sampled rays and finds 31 local failures at each spacing.
Three locally converged production paths are slower than explicitly feasible
guide paths, with gaps up to 37.159 ms. A subsequent [continuous layered
reference](data/development/loma_geometry_preflight/layered_reference_001/README.md)
passes completeness and distance closure for all 104 samples and confirms
23 critical guides as first arrivals. Refined production errors still reach
186.569 microseconds. These numerical failures do not justify excluding
any observed geometry.

An [exact-branch seed control](data/development/loma_geometry_preflight/reference_seeds_001/README.md)
finds that supplying the correct earliest guide branch still leaves 39 of 40
optimized paths failing their local stopping rule. The finest paths can have
accurate times and source derivatives while ordinary gradients at the
velocity-gradient interface remain unsuitable for the stopping test. A
subsequent [directional diagnostic](data/development/interface_directional/001/README.md)
also finds a small tangential descent in the retained finest row-5
polygon. Relabeling its local flag would hide that residual optimization error.
A separate [complete continuous layered reference](data/development/loma_layered_full_002/README.md)
now passes all 37,648 pairs and an independent native-identity review. It supplies
an explicit alternative source of synthetic truth. The integration branch provides a
[reviewed-reference exporter](data/development/analytic_truth_preparation_checks_001/README.md)
and a [frozen simulation launcher](data/development/analytic_simulation_launcher_002/README.md).
They retain all native identities, preserve earlier failures, and require
separate output review and inverse forward validation.
The actual LOM-profile run now contains 15,932,384 synthetic observations:
37,648 absolute rows and 7,947,368 rows of each differential type. Its independent
streaming audit passes every row, including identities and timing arithmetic.
The [verified lossless publication](data/published/loma_lom_analytic_001/README.md)
retains the complete run in ten archive parts totaling 504 MB, with readable
geometry, manifests, and reviews. No Loma inversion result is implied.
The second, [LON-profile simulation](data/published/loma_lon_analytic_001/README.md)
also passes its complete audit. Actual
file comparison confirms identical simulated observations and perturbed sources,
while all 288 starting velocity values differ. The complete LOM starting-model
reference passes. The first LON reference attempt preserves one distance-closure
failure with its selected time and derivatives blank. A separately reviewed
[turning-speed arithmetic correction](data/development/loma_lon_initial_reference_002/README.md)
passes all 37,648 LON references without changing the isolated roots or acceptance
limits. The largest candidate-time change is 1.70 nanoseconds; only the previously
invalid pair changes validity. The
[full LOM initial comparison](data/development/loma_lom_initial_accuracy_001/README.md)
now finds all 37,648 travel times within the unchanged limit, but 48 bottom-face
source derivatives fail and one additional ray fails local stopping. The
[observed failures](data/development/loma_initial_failure_review_001/README.md)
separate an exhausted line search from a
[boundary endpoint discretization effect](data/development/loma_boundary_endpoint_001/README.md).
An [exact-action comparison](data/development/loma_failed_trial_exact_001/README.md)
now finds that all 24 actual rounded trials in the failed search satisfy the
original decrease requirement, despite rejection by the binary64 evaluation.
The first exact decrease is 6.76 femtoseconds; its recorded value instead
increases by 12.43 femtoseconds. The independently reviewed
[saved replay](data/development/loma_failed_search_3426_001/README.md) preserves
all original numerical results and flags. This diagnoses an arithmetic failure
for that search; no corrected optimizer or inversion is accepted yet.
A [single-change replay](data/development/loma_outer_accumulation_native_001/README.md)
using an extended outer action sum avoids the early rejection but exhausts
the unchanged 1,000-update budget with a false local flag. Its travel time
and source derivative still pass their reference limits. The
[saved histories](figures/diagnostics/loma_outer_accumulation.pdf) show that
this arithmetic change is insufficient to resolve stationarity; 564 accepted
updates have equal recorded binary64 actions. All original results remain
preserved, and no stopping threshold is relaxed.
A [neutral curvature capture](data/development/loma_curvature_capture_native_001/README.md)
reproduces those tables byte for byte. All 960 discarded pairs have positive
curvature below the fixed retention cutoff, including the final 565 updates.
Exact sums preserve every sign and cutoff classification. This identifies a
retention question for a separate controlled experiment; it supplies no
accepted optimizer correction.
A [static interface calculation](data/development/loma_candidate_support_001/README.md)
then places two nearly aligned vertices exactly on the 7 km interface. The
prescribed candidate has a slightly smaller exact action and admits a
supporting-vector norm of 5.579e-6 s/km. An independent readback checks all
3,396 internal components. The [candidate comparison](figures/diagnostics/loma_interface_candidate.pdf)
also retains the action increase when only vertex 485 is moved. This explains
why the nonsmooth interface needs explicit treatment; it does not provide a
general optimizer correction or change the original false flag.
A [controlled retention replay](data/development/loma_positive_curvature_native_001/README.md)
then changes only the cutoff from `s*y > 1e-14` to `s*y > 0` after a byte-identical
saved-initializer replay. It satisfies the unchanged combined local stop after
145 updates, with time error 0.861 microseconds and source-vector error
3.18e-8 s/km. The [history comparison](figures/diagnostics/loma_retention.pdf)
supports a role for discarded curvature in this case. Positive subnormal and
infinite curvature remain unsafe in invented controls.
A [usable-curvature replay](data/development/loma_usable_curvature_native_001/README.md)
rejects nonfinite or unrepresentable memory operations and preserves the existing
fallback. It reproduces all five native C tables byte for byte after 183 invented
checks per variant. After [bounded integration checks](data/development/usable_curvature_integration_checks_001/README.md),
the `first-arrival-integration` branch [adopts the tested correction](data/development/usable_curvature_adoption_001/README.md).
The finest-grid layered and oblique comparisons pass; a retained coarse layered
source derivative exceeds its accuracy target. Full-cohort validation remains
pending. The running jobs retain their earlier frozen binaries, and the
separate endpoint-action failure remains unresolved.
Historical replays use the [inert sentinel archive](data/development/terminal_lock_archive_001/README.md)
to restore omitted terminal evidence into a fresh scratch checkout; existing
run directories and runtime locks are preserved.
A separate [boundary component calculation](data/development/loma_endpoint_connector_native_001/README.md)
replaces the first straight element by a constrained curved connector in the
saved affine layer. It retains the same local action, removes the demonstrated
source-normal term, and preserves the neighboring vertex's second-element
reaction. The reviewed calculation supplies no general trilinear connector
or model Jacobian and does not produce a new inverse result.
A later [invented scalar contact calculation](data/development/loma_endpoint_scalar_contact_controls_001/README.md)
uses one trilinear action for original-node perturbations. Its correct limiting
source derivative coexists with a 6.066% error in the leading excess action.
The perturbed-family minima and derivative error bounds remain uncertified;
the receiver derivative remains biased. This supplies no native correction.
A [trilinear shooting experiment](data/development/loma_endpoint_shooting_controls_001/README.md)
uses curved candidates and the same action for all original-node perturbations.
All 40 affine reference comparisons pass, while all 24 inward boundary secants
retain finite-step failures and the expected square-root truncation trend.
This supplies an action-consistent local candidate, with no native adoption.
A [saved boundary-limit calculation](data/development/loma_endpoint_shooting_asymptotics_002/README.md)
separates square-root finite-step truncation from the old polygon's nonzero
linear term. All 24 raw failures remain reported; the separate extrapolates
agree with limiting momentum but deteriorate at the finer steps.
Only 37,599 LOM rays pass all full-ray comparison criteria. The [completed LON census](data/development/loma_lon_initial_accuracy_001/README.md)
passes all 37,648 local and time checks but retains 50 source-vector failures:
13 at bottom sources and 37 at interior sources. Both sampled preflights remain
active; neither performs an inverse update. These results use the earlier
frozen optimizer. Repeating the invented endpoint-mesh controls with D preserves
their two false local flags and 32 derivative failures. A [bounded LON replay](data/development/loma_lon_straight_curvature_replay_001/RESULTS.md)
also preserves the worst interior failure and a passing same-event control:
source-vector errors remain 4.8071e-6 and 1.0600e-6 s/km. Their final paths and
model partials are byte-identical with the old and D optimizers. This rules out
the adopted correction as a remedy for that failure, without resolving other
optimization or path-representation effects. A [saved first-edge calculation](data/development/loma_lon_first_edge_decomposition_001/README.md)
matches the recorded source partials within 1.63e-17 s/km. Curving that edge
while fixing its other endpoint slightly worsens both reference discrepancies;
it does not repair the failing ray. Disabling the combined early stop in
[two bounded diagnostics](data/development/loma_lon_strict_straight_replay_001/REPLAY.md)
improves the failing ray's derivative while worsening the control's. Both meet
the derivative limit after 1,000 and 4,000 updates, but both exhaust those
budgets with false strict convergence flags. No production stopping rule changes.
A separate
[one-sided curvature calculation](data/development/native_interface_conditioning/README.md)
assesses a saved interface direction, without changing production optimization
or promoting any failed flag.

A new [inversion forward guard](data/development/inversion_ray_gate_checks/README.md)
on the integration branch rejects locally unconverged or otherwise invalid rays
before Jacobian, trial-objective, or final-output use. It preserves identified
failed paths and model states separately from the last accepted state. Controlled
checks preserve successful inversion outputs byte for byte; this is failure
handling, not a first-arrival or nonlinear-convergence certificate.
The [full-DD resolution reader](data/development/full_dd_resolution_ray_input_checks_001/README.md)
now verifies its complete native ray inventory, metadata, coordinates and
recorded local status before matrix assembly, and preserves existing outputs.
All 56 new input controls pass; the 39 preceding covariance controls retain
identical results. Final-model ray and derivative accuracy still require
separate acceptance. No new field resolution has been calculated.
The [geometry export](data/development/hayward_full_dd_geometry_adoption_002/README.md)
now saves 17-digit paths and status from the same rays used for the full matrix,
retaining native identities and both receiver epochs. Its
[82 invented controls](data/development/hayward_full_dd_geometry_export_controls_002/RESULTS.md)
pass on the frozen old-kernel source, with all eight original export files
byte-identical. The separate reader checks complete support, endpoints,
box membership, configured initialization
and source-matrix joins at the parsed saved 12-digit model. Integration adoption
compiled successfully; the earlier compile failure remains preserved, and
neither adoption attempt evaluated rays. The
[lossless archive](data/development/geometry_export_evidence_001/README.md)
retains both control preparations, terminal results and independent reviews.
These diagnostics supply no field, derivative-accuracy or covariance acceptance.
Run these newer diagnostic and simulation commands from the
[`first-arrival-integration` branch](https://github.com/nts345045/zhang-thurber-2003-independent-reproduction/tree/first-arrival-integration).

The [Figure 2 geometry replacement](data/development/loma_geometry_figure_001/figure02_authoritative_geometry_candidate.pdf)
now shows 724 catalog-derived Loma Prieta sources, 52 identified receivers, and
the manuscript's 48 horizontal grid nodes. The [small input package and replot
command](data/development/loma_geometry_figure_001/README.md) preserve complete
identities and rebuild the plot without the simulation archive. Figure 2 remains
partial because the exact study cohort, projection and layout are unknown.
The historical Figure 3 recovery panels still use the earlier random geometry;
replacement recovery results remain unfinished.

The [authoritative waveform pilot](data/authoritative/waveforms/pilot_001/README.md)
retrieved two five-second records and their historical instrument responses.
The [fixed pair fails the written coherence screen](data/development/waveform_correlation_pilot_001/README.md):
only 2 of 20 frequency bins pass, where 10 are required. No waveform difference
was added. An [offline full-cohort metadata audit](data/authoritative/waveforms/cohort_plan_001/README.md)
preserves every catalog observation and identifies a calibration gap for 117
NC.CMW1 picks from 1995–1998; saved StationXML responses begin in 2000.
The user clarified that normalized waveform cross-correlation should produce
dt.cc inputs without requiring calibration corrections. The
[declared method](data/development/normalized_correlation_specification/README.md)
uses the documented EQcorrscan workflow as a reference; missing response
metadata remain explicit and the rejected pilot remains preserved.
Provider orientation metadata,
rather than channel-name suffixes, distinguish vertical channels from other
orientations. These audit categories establish no study exclusion.

The [completed sample acquisition](data/authoritative/waveforms/cohort_samples_002/README.md)
assesses all 464 windows with reported covering spans: 459 return complete
native samples and five return none. All 14,262 original picks and 44,718
catalog pairs remain identified. The
[audited normalized correlations](data/development/native_waveform_cc_001/README.md)
attempt 1,195 eligible pairs and accept 98 under the declared coherence and
peak checks. They span 103 events and four full SEED channel identities.
The [identified dt.cc export](data/development/native_dt_cc_001/README.md)
preserves both event/pick identities, both metadata epochs, every rejected or
unattempted pair, and explicit event-to-integer mappings. CC squared is a
relative weight, with no formal timing uncertainty inferred. These measurements
have not entered either catalog-only inversion; the original saved results retain
their original inputs and limitations.

The separately [prepared catalog-plus-CC inputs](data/hayward_catalog_cc_001/README.md)
retain all 58,980 catalog rows and append the 98 waveform differences. Both
receiver epochs remain attached, including 38 pairs across metadata epochs;
the combined input uses exactly the same 14,262 native forward pairs.
The [CC spatial-support map](data/development/native_cc_spatial_support_001/render_002/cc_spatial_support.pdf)
places the 98 accepted pairs and their 103 events within the full 1,092-event
catalog geometry, with four identified receiving channels. Its
[saved identifiers and replot instructions](data/development/native_cc_spatial_support_001/REPLAY.md)
retain all 22 used receiver epochs. This is an input-support diagnostic;
the combined dataset remains uninverted, and the map establishes neither
resolution nor inversion accuracy.
The [adopted empirical weighting](data/development/catalog_cc_weight_adoption_001/README.md)
uses literal CC squared as a residual/Jacobian row multiplier, hence CC to the
fourth power in the squared objective before other factors. Timing uncertainty
remains explicitly unestimated. The preparation and independent full-file audit
do not create a configuration or inversion result.

[Read the PDF report](report/report.pdf) or the
[panel-by-panel audit](FIGURE_AUDIT.md).
The [failure summary](FAILURE_SUMMARY.md) connects the input, forward-model,
inversion, and uncertainty deficiencies to the remaining partial reproductions.
An [additional authoritative waveform pilot](data/authoritative/waveforms/eventdata_pilot_001/README.md)
returned no samples for its two exact event/channel requests. The existing
98 waveform measurements and full catalog selection remain unchanged.

## Where to inspect outputs

This integration branch also provides an opt-in FMM initializer in the solver.
Its [configuration, numerical checks, and identity-preserving output tests](diagnostics/FIRST_ARRIVAL.md)
are documented separately. The PDF records the completed audit checkpoint;
the saved full Hayward and synthetic inversions still use their documented
earlier forward operators.

- `data/synthetic/`: existing baseline inversions. `standard_grid.csv` and
  `dd_grid.csv` contain inferred P velocities; method-specific `*_events.csv`,
  `*_history.csv`, and `*_residuals.csv` contain source estimates, convergence
  histories, and observation residuals. These inversions predate the ray fixes.
- [`data/hayward/`](data/hayward/README.md): authoritative inputs and current
  completed baseline. Inspect `standard_*`, `dd_*`, and `loc1d_*` for each
  method's model, events, history, residuals, coverage, and final sampled ray
  checks. `numerical_review.json` and the independent completed-baseline review
  record failures. `absolute_resolution*` is conditional on absolute picks
  at the saved DD model; it is not full-DD resolution.
- `data/hayward_first_arrival_guarded_001/`: failed guarded catalog-DD attempt
  in the integration worktree. `dd_failed_forward_*` records the rejected
  first trial; `dd_last_accepted_*` preserves the initial state. Its history
  contains only a header. The [failure archive](data/development/hayward_guarded_failure_001/README.md)
  preserves identified outputs and execution evidence. There is no accepted final model.
- `data/hayward_old_kernel_backtracking_001/`: separate catalog-DD attempt
  in the integration worktree. Its closed
  `dd_iteration_1_solve_accepted_grid.csv` and
  `dd_iteration_1_solve_accepted_events.csv` contain the first accepted update.
  The [saved snapshot archive](data/development/hayward_accepted_update_delivery_001/README.md)
  includes these files, identified starting inputs, the plotting script and
  [intermediate-state figure](figures/hayward_accepted_update_001.pdf).
  The [second accepted state](data/development/hayward_second_accepted_update_figure_001/RESULTS.md)
  now supplies identified event and grid tables plus a
  [second-minus-first comparison](data/development/hayward_second_accepted_update_figure_001/figure/accepted_update_2_minus_1.pdf).
  Both are intermediate models; the ongoing run has no accepted final model
  or full-DD resolution result.
- `figures/` and `figures/hayward/`: plots generated from the saved numerical
  tables. `report/report.pdf` explains the experiments and reproduction limits.
- `data/development/`: numerical diagnostics and frozen failure evidence.
  `hayward_first_arrival_003_review/` contains the failed third preflight;
  `hayward_first_arrival_004_1d_support/` contains the passing full initial
  reference comparison. `hayward_initial_failure_refinement_*` contains identified follow-up
  ray calculations. These directories contain forward checks, not new inversion
  models. Corrected numerical code is maintained on `first-arrival-integration`.
- `data/development/native_dt_cc_001/`: 98 waveform-derived differential
  inputs in `dt.cc`, with `dt.cc.identifiers.csv.gz`, `event_id_map.csv`, and
  `receiver_epochs.csv.gz`. Keep these identity mappings with the legacy file.
  The full measurement roster and attempted lag/coherence arrays are in
  `data/development/native_waveform_cc_001/`. These directories contain inputs,
  not an additional inversion result.
- [`data/hayward_catalog_cc_001/`](data/hayward_catalog_cc_001/README.md):
  reviewed combined inputs in `observations.csv`, copied original geometry,
  `preparation_manifest.json`, and `independent_review.json`. All original
  catalog rows remain unchanged; no inversion outputs exist in this directory.
- [`data/published/loma_lom_analytic_001/`](data/published/loma_lom_analytic_001/README.md):
  complete, audited synthetic observations and authoritative geometry, with
  verified archive restoration instructions. These are inputs for the corrected
  Loma inversion, whose outputs are still pending.

## Build and run

Requirements: C++17 compiler, CMake >=3.16, OpenMP, Python 3 with NumPy and
Matplotlib, and pdfLaTeX with the `fontenc`, `lmodern`, `geometry`, `amsmath`,
`amssymb`, `graphicx`, `booktabs`, `longtable`, `array`, `hyperref`, `url`,
and `listings` packages. No third-party tomography or optimization library
is required. The formatter used during development is not a runtime dependency.
The delivery environment is recorded in `reference/delivery_environment.json`.
The Hayward plotting and resolution workflow also requires SciPy. Hayward
preparation requires Requests, including when reading the saved archive
without web-service queries.
Run `python3 plot_hayward.py` to plot the completed baseline tables. The optional
`--velocity-only` mode produces Figures 4 and 10 and a separate Figure 10 manifest.

`./rebuild_hayward.sh` reuses the saved authoritative archive, prepares its
identified subset, builds the solver, and runs absolute-data tomography,
catalog DD tomography, and fixed-model relocation. It records source/input
hashes and per-method logs in `data/hayward/`, then generates ray diagnostics,
conditional resolution, figures, and the report. It uses three concurrent
inversions with eight OpenMP threads each by default. This command makes no
new web-service queries.

```sh
./rebuild.sh
```

The script compiles the model from clean object files with CMake's
`--clean-first`, validates it, regenerates the synthetic observations,
performs four main inversions, fixed-model and joint recovery tests, and
two starting-model sensitivity inversions. It checks rays in the true and
final standard/DD models, creates figures and audit tables, and compiles
`report/report.pdf`. The LOM/LON sensitivity profiles are written gradient
adaptations, not confirmed starting models for the target experiment.

The eight inversions run concurrently; `OMP_NUM_THREADS` sets threads per
process (default 8). Generation and final analysis remain sequential, and
every inversion must exit successfully before analysis starts. A successful
invocation overwrites all required numerical and report outputs. Caches and
intermediate files stay inside the project. Standalone panel commands are
in `FIGURE_AUDIT.md`.

Each invocation removes previous rebuild outcome records before starting.
Only completion of every command writes `data/rebuild_result.txt`; a failed
command writes `data/rebuild_failure.txt` with its exit status and elapsed
time. If a rebuild fails, older data or figures may remain, and those files
do not establish that the latest rebuild succeeded.

## Files

- `src/`: independent ray tracing, LSQR, observation generation, and inversion.
- `configs/synthetic.cfg`: reproducible synthetic experiment and solver choices.
- `METHODS.md`: governing problem, assumptions, numerical substitutions, validation.
- `data/`: generated inputs, inversion results, convergence history, metrics, panel audit.
- `plot.py`, `audit.py`, `analyze.py`: plots and report tables from saved output.
- `diagnostics/`: optional source-derivative sweep; commands are in `data/development/README.md`.
- `figures/`: generated PDF and PNG figures.
- `report/report.tex`, `report/report.pdf`: final report source and compiled report.
- `reference/task.md`: original task; subsequent data-sourcing rules are in `AGENTS.md`.

The model uses km, km/s and s. The origin-time convention is a local epoch;
all true synthetic origin times are zero. Stochastic generation uses C++
`mt19937` and standard-library distributions; exact bitwise agreement across
standard-library implementations is not guaranteed. Saved input CSV files
allow inversion without regenerating random inputs.

## Scientific status

Read the report and `FIGURE_AUDIT.md` for the status of each manuscript
panel. Successful numerical unit checks do not establish agreement with
field observations or uniqueness of the inverse solution. No published
reference images are embedded in this repository or report.
