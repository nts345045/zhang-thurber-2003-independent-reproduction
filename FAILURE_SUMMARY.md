# Why the manuscript results remain only partly reproduced

The main causes were different observational inputs, inaccurate forward
calculations, and validation that did not cover the rays used by the inversion.
The completed baseline now supplies independently generated counterparts for
every manuscript panel, but the [panel audit](FIGURE_AUDIT.md) classifies only
the written true-velocity profile as reproduced; the other 61 panels remain partial.

| Underlying failure | Consequence and current evidence |
| --- | --- |
| The original synthetic geometry and observational cohort were not reconstructed. | Generated source/station coordinates changed ray coverage and source–velocity trade-offs. The later authorized authoritative Hayward subset has 1,092 events and 37 stations, compared with the manuscript's 1,489 and 52. The exact historical cohort and starting-model conventions remain unmatched. These differences prevent a controlled comparison of recovered structures even with an accurate solver. See the [selection record](data/authoritative/README.md). |
| Metadata were initially incomplete or ambiguous. | Missing historical channel epochs, conflicting borehole elevations, and treating metadata epochs as distinct physical receivers affected matching and differential links. Authoritative history recovered the missing operation epochs; every selected pick now retains its own native identity and epoch. Unknown study membership is not an exclusion criterion. The remaining elevation/datum assumptions are explicit in the [station investigation](data/authoritative/stations/README.md). |
| Local ray convergence was used without establishing first-arrival accuracy. | A stationary ray can follow a later branch. One initial Hayward ray was locally converged but 2.232 ms late. Separately refining path discretization and the FMM initialization field was necessary. All 14,262 initial Hayward rays now pass the unchanged time/source-derivative limits, but this does not validate later 3D models. See the [full initial comparison](data/development/hayward_first_arrival_004_1d_support/README.md). |
| Arithmetic and path representation obstructed optimization and endpoint derivatives. | Rounded action sums rejected genuinely decreasing trial paths. Improving the outer sum exposed stagnation under an absolute curvature-retention cutoff. An isolated positive-retention replay reaches the existing stop in 145 updates; a safeguarded replay preserves all five numerical tables. The integration branch now adopts that tested safeguard after bounded analytic and inversion-guard checks; full-cohort use remains untested. At bottom-boundary sources, the derivative of a finite straight segment differs from the continuous optimized-path derivative. These are distinct failures; fixing the line search does not repair the endpoint action. See the [safeguarded retention experiment](data/development/loma_usable_curvature_native_001/README.md) and [boundary controls](data/development/loma_boundary_endpoint_mesh_controls_001/README.md). |
| Inversion completion and small samples concealed unresolved forward failures. | The original solver could use rays with false local flags in objectives and Jacobians. Its final 32-ray samples do not certify the full ray set. DD ends with a 2.761 km maximum source-coordinate update; two rays fail the final resolution linearization. Fixed-velocity relocation worsens unweighted catalog-DD RMS from 0.09340 to 0.25423 s. Accepted frozen-weight objectives do not increase: their changing weights differ from that unweighted statistic. See the [completed baseline review](data/development/hayward_completed_baseline_review_001/README.md). |
| The data types and uncertainty calculation were incomplete. | The baseline uses catalog differences without waveform-derived rows. The normalized-correlation workflow now supplies 98 identified `dt.cc` measurements, but they have not entered an inversion. The published resolution diagnostic uses absolute picks only, assumes independent one-sigma pick errors and unconstrained sources, and excludes important sources of uncertainty. It does not quantify full-DD resolution or total model error. See the [CC export](data/development/native_dt_cc_001/README.md) and [resolution manifest](data/hayward/absolute_resolution_manifest.json). |

The waveform clarification removes historical instrument-response calibration
as a prerequisite for normalized cross correlation. It does not remove the
need for authoritative samples, correct timing/channel identities, preprocessing
records, or correlation-quality checks. Missing waveforms or responses do not
justify deleting catalog observations or inferring study exclusions.

The guarded catalog-DD attempt stopped at its first trial model: 181 of 14,262
rays failed local stopping despite successful initialization. No inverse update
was accepted. The [failure archive](data/development/hayward_guarded_failure_001/README.md)
preserves the rejected trial, last accepted state, identified rays and execution
evidence. Passing the initial one-dimensional model did not establish convergence
in that first three-dimensional trial.
A [matched replay](data/development/hayward_trial_cmj_old_D_replay_001/RESULTS.md)
confirms that the adopted optimizer also fails on two of these rays. Their
saved paths cluster near a grid face where velocity has a sharp maximum in
the normal direction. This nonsmooth feature is independently checked, but
its role in stopping and the other 179 failures remain unresolved.
Fixed-path reevaluation localizes more than 99% of both old and revised
squared gradient norms to normal motion near that face. This identifies
where the ordinary gradient remains large; a valid nonsmooth stopping
test is still unresolved.
Invented exact-face controls explain two necessary distinctions: a branch
gradient can be nonzero at a true minimum, and zero in a convexified gradient
set can still hide descent at a slow face. Their coupled endpoint directions
cannot be checked independently. These controls do not project or relabel
the nearby native paths; see the [ridge calculation](data/development/internal_ridge_stationarity_controls_001/README.md).

The [trilinear action controls](data/development/trilinear_action_controls_001/RESULTS.md)
now bound reciprocal-velocity integrals and side-dependent first variations
after exact grid-plane splitting. All 80 checks pass (65 mathematical and
15 hash checks), with 18 independent exact comparisons. Coupled descent and
unresolved bounds remain explicit. The [native CMJ calculation](data/development/hayward_cmj_face_action_001/RESULTS.md)
now shows that placing the selected nodes exactly on the face lowers the
continuous trilinear action by 4.3891e-11 and 8.1650e-11 s. Nevertheless, the
remaining tangent norms are 3.4637e-5 and 4.1306e-5 s/km, with lower bounds
above both existing gradient scales. Face alignment alone does not resolve
these two paths; ordinary tangent descent remains. Both original failed
flags are preserved, and no optimized path or first arrival is claimed.

One subsequent [prescribed tangent step](data/development/hayward_cmj_tangent_step_001/RESULTS.md)
per face candidate lowers the action by another 2.4666e-10 and 4.6728e-10 s,
with maximum node movements of 0.05169 and 0.14095 m. Both complete rounded
displacements have certified negative slopes and pass the fixed Armijo check.
Independent saved readback passes. The separate
[post-step gradient calculation](data/development/hayward_cmj_post_step_tangent_001/RESULTS.md)
gives available tangent norms of 3.1087e-6 and 1.2717e-5 s/km. Both retain
resolved tangent residuals above 1e-7, and the second remains above 1e-5.
Neither preceding accepted change is below 1e-11 s. These measured reductions
do not yet resolve convergence or the source-derivative failures.

The [next full-size tangent trials](data/development/hayward_cmj_tangent_step_002/RESULTS.md)
increase action by 3.0212e-10 and 2.7020e-10 s and are rejected. Their initial
slopes are negative, so the finite step is too large for decrease. This
is resolved by a [half-length trial](data/development/hayward_cmj_tangent_half_step_001/RESULTS.md)
along each same direction: action decreases by 1.9272e-11 and 7.5767e-11 s,
with both conservative Armijo checks passing. This establishes a finite-step
size issue for these prescribed trials. Neither decrease yet meets the
combined stopping scale of 1e-11 s.

The [post-half check](data/development/hayward_cmj_post_half_step_tangent_001/RESULTS.md)
finds available gradient norms of 2.5528e-6 and 6.7473e-6 s/km. Both retain
a resolved residual above the strict 1e-7 scale. Their same-geometry
zero-normal support construction retains ordinary entry and exit terms;
its large full-vector norms do not establish the minimum support residual.
The original failed flags therefore remain unchanged.

On the earlier first-step geometry, [exact face-sign checks](data/development/hayward_cmj_post_step_zero_support_001/RESULTS.md)
permit a shared pointwise mixture with zero normal contributions from aligned
edges. Ordinary entry and exit contributions remain. The resulting full-vector
norms, 4.4155e-5 and 2.4963e-5 s/km, describe one feasible support choice;
their size cannot rule out a smaller support residual. Thus this calculation
does not establish stationarity or justify changing either failed ray flag.

The [fixed-polygon evaluator check](data/development/hayward_cmj_fixed_polygon_kernel_001/RESULTS.md)
finds paired action-difference errors below 4.0e-17 s and reproduces all four
full/half acceptance decisions. Available gradient errors on the four face
and first-step polygons are below 1.057e-15 s/km. Thus integration error does
not explain these resolved increases and decreases; step selection and
the full nonsmooth stationarity condition still require attention.

The subsequent [bounded tangent iteration](data/development/hayward_cmj_tangent_iteration_001/RESULTS.md)
reduces the computed available norms to 8.1821e-8 and 9.6184e-8 s/km after
16 and 38 accepted updates. Independent readback reconstructs all 184 rounded
trials. This resolves the computed tangent residual for these prescribed
face paths, while the full coupled support and continuous action require
separate bounds. It supplies no automatic contact rule, source-derivative
validation or accepted inverse update; both original failed flags remain.

The [final continuous audit](data/development/hayward_cmj_final_tangent_support_001/RESULTS.md)
now supplies the missing full-vector bound on those prescribed polygons.
Feasible norms are below 8.1822e-8 and 9.6185e-8 s/km, including coupled
face-normal moments and all ordinary adjacent-edge terms. Both actions are
also lower than on the preceding half-step paths. These results meet the
strict first-order residual scale for the prescribed geometry, but do not
provide an automatic way to reach that geometry or establish first arrival
and source/model derivative accuracy. A feasible witness is sufficient for
the bound; no minimum-norm fit is claimed, and one fit exhausts its sweep cap.
The [original-cut inventory](data/development/hayward_cmj_original_cut_inventory_001/RESULTS.md)
also finds zero omitted crossings on the two original paths. Their failure
cannot be attributed to those cut omissions, while general off-face evaluator
accuracy remains a separate question.

The [invented contact and cutoff tests](data/development/internal_face_contact_controls_001/RESULTS.md)
now isolate two further requirements. Exact event construction can place
adjacent nodes on a fast face through two decreasing proposals, but a slow
face still permits normal descent when its tangent residual vanishes.
Separately, the existing displacement cutoff can omit a tiny crossing and
leave a 1.1322e-4 s/km endpoint-gradient error while the action error is only
5.2427e-17 s. Thus an accurate travel time can conceal an inaccurate
variational derivative. These are bounded synthetic results; they neither
attribute the original CMJ failures to omitted cuts nor validate an automatic
contact optimizer. All 30 declared checks passed while preserving the
observed evaluator error and unchanged production source.
A [separate explicit-cell experiment](data/development/strict_cell_segment_controls_001/RESULTS.md)
then reduces the tiny-crossing gradient error to 7.4166e-17 s/km. It preserves
every true partition and keeps the selected cell fixed when a rounded sample
lands on a face. Nine invented cases pass 59 structural checks; all numerical
error intervals remain reported. The experiment changes several arithmetic
steps together and does not yet validate general native segments or provide
an optimizer correction.

The [original-path component audit](data/development/hayward_cmj_original_gradient_bounds_001/RESULTS.md)
then separates evaluator error from the failed rays' actual residuals.
Independent ordinary-gradient norms are 4.9649e-4 and 4.9379e-4 s/km,
whereas the saved C++ component errors are only 1.0564e-15 and 1.0436e-15
s/km. All 6,168 free components are ordinary, with no active physical-box
projection. The large original residuals therefore persist under independent
evaluation. This finding supports testing how the search reaches a cell face;
it does not establish the cause of every ray failure or validate first arrival.

The original guard also stopped before trying a smaller inverse step. A
[separate old-kernel candidate](data/development/hayward_old_kernel_trial_backtracking_candidate_001/README.md)
now distinguishes a pure local-stopping trial rejection from fatal current,
final, mixed and I/O failures. It retains the original solve increment,
fixed weights and halving rule. Invented controls demonstrate smaller
accepted steps and exact all-valid output parity; the
[190 saved completion checks](data/development/hayward_trial_completion_checks_002/RESULTS.md)
verify evidence closure after correcting three preserved bookkeeping gaps.
They do not establish recovery of the failed Hayward trial, later-model
accuracy or a complete final-table launcher test.
The [separate launcher checks](data/development/hayward_old_kernel_backtracking_launcher_checks_002/review.json)
pass all 62 cases, including five process-lifecycle cases, and verify the
exact source changes against the original initial-model evidence. These
saved-evidence and controller checks preceded the separate field attempt.
Final scientific assessment remains necessary after any successful execution.
The catalog-only attempt began at 10:52 UTC on 10 October 2026; the 11:21 UTC
snapshot still showed its initial evaluation, with no accepted update.
The [evidence archive](data/development/trial_backtracking_evidence_001/README.md)
preserves both successful controls and earlier failed or unexecuted variants.

Final-model evidence also needs the paths used by the full-DD matrix. The
[geometry exporter and reader](data/development/hayward_full_dd_geometry_adoption_002/README.md)
now preserve and check identified 17-digit paths, endpoints, box membership,
configured initialization and source-matrix joins. All 82 invented controls
pass on the frozen old-kernel source, and the original eight export files
remain byte-identical. Integration adoption compiled successfully after a
preserved compile-only failure; neither
attempt evaluated rays. The [archive](data/development/geometry_export_evidence_001/README.md)
retains the source, both control preparations and reviews. These checks concern
the parsed saved model and establish no field accuracy or covariance acceptance.

Bounded LON tests also show that early stopping affects source derivatives:
additional optimization improves one failing ray while worsening a passing
control. Both exhaust even a 4,000-update diagnostic budget with false strict
flags. Exact integration of the saved first edge is accurate to roundoff;
curving that edge alone does not repair the original error. These tests isolate
some causes without establishing a general optimizer or endpoint correction.
Boundary-action and optimization controls remain necessary before accepting a
corrected Loma inversion. Inspect the
[output guide](data/hayward/README.md) for the completed baseline files and their
limitations.
