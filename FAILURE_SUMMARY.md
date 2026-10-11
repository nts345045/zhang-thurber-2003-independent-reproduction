# Why the manuscript results remain only partly reproduced

The [panel audit](FIGURE_AUDIT.md) records **one reproduced panel and 61 partial
panels**. Panel 1 reproduces the horizontal true P-wave velocity slice from the
written profile. Independently generated plots do not, by themselves, reproduce the
manuscript's inferred structures or establish numerical convergence.

**The experiments do not yet match the original inputs.** The initial synthetic
inversions used generated geometry and explicit replacements for unspecified
starting conditions. The authorized [Hayward subset](data/authoritative/README.md)
contains 1,092 events and 37 physical stations, versus the manuscript's 1,489 and
52; the original cohort, depth conventions and starting model remain unmatched. The
new [Figure 2 layout](data/development/loma_geometry_figure_001/README.md) uses 724
authoritative catalog sources and 52 identified receiver epochs. It shows input
geometry only. Historical Figure 3 recovery still uses the earlier random layout, so
it cannot demonstrate recovery on this new geometry.

**Metadata gaps and elevation ambiguities affected matching.** The
[station investigation](data/authoritative/stations/README.md) recovered the missing
CMW1 operation epochs and unique pick matches. Provider event, origin, pick and
association IDs, SEED/FDSN channel identifiers, valid blank locations and separate
metadata epochs remain attached. Provider-declared sensor elevations avoid double
subtraction of burial depth. CMW1's historical sensor-elevation interpretation is an
explicit assumption; conflicting elevation records and datum statements are
preserved. Unknown manuscript
station membership, missing waveforms or absent responses are not grounds for
inventing study exclusions.

**Stationarity and first-arrival selection are different tests.** A locally
converged initial Hayward ray was 2.232 ms late; path refinement alone approached
the wrong stationary branch. Refining initialization as well as the path resolved
that example. The [full initial-model
comparison](data/development/hayward_first_arrival_004_1d_support/README.md)
subsequently passed all 14,262 rays against the existing 25-microsecond time and
3e-6 s/km source-vector limits. That evidence applies to the saved depth-dependent
model, not later 3D updates. These are project validation criteria, not recovered
manuscript tolerances. Appropriate reference and refinement evidence is needed; a
small local residual alone supports no global first-arrival claim.

**Evaluator arithmetic and search conditioning caused distinct failures.** Tiny
omitted cell crossings can produce a large derivative error despite an accurate
action; [contact/cutoff
controls](data/development/internal_face_contact_controls_001/RESULTS.md) and
[explicit-cell
controls](data/development/strict_cell_segment_controls_001/RESULTS.md) isolate this
problem. Conversely, the [original CMJ component
audit](data/development/hayward_cmj_original_gradient_bounds_001/RESULTS.md) finds
approximately 5e-4 s/km residuals but only 1e-15 s/km evaluator errors. Those
residuals are not explained by quadrature. Separately, rounded action accumulation
and discarded curvature information obstructed descent; [usable-curvature
evidence](data/development/loma_usable_curvature_native_001/README.md) improves a
particular trajectory without establishing general optimizer convergence.

**Finite path resolution also affects endpoint sensitivities.** At a physical
boundary, a fixed polygon's endpoint partial can differ from the derivative of the
continuously optimized path even when travel time is accurate. The [endpoint-mesh
controls](data/development/loma_boundary_endpoint_mesh_controls_001/README.md)
distinguish fixed, tied and reoptimized nodes, and expose both representation error
and incomplete relaxation. Accurate integration, more nodes or a true local flag
alone did not resolve all value-derivative discrepancies. Zeroing boundary
derivatives would also discard valid nonzero derivatives in other cases.
The separate [continuous-curve component](data/development/layered_curved_components_001/README.md)
now passes 58 affine and 24 independent nodal-integral checks, including a
documented replay. These controls cover limited layered geometry; the component
has not replaced the production forward calculation. Two subsequent catalog-derived
curve constructions succeeded, but both integrations rejected a quadrature node
that rounded to a grid-partition endpoint. Those
[failed native tests](data/development/layered_reference_selected_curves_001/README.md)
are preserved separately; manufactured-case success did not establish native
robustness.
A [local-coordinate formulation](data/development/layered_local_quadrature_001/README.md)
now retains those positive partitions without forming a global Gauss parameter
near one. It passes the unchanged 82 controls and four additional checks of a
known tiny nodal contribution. Both original native integrations then complete,
retaining 15/8 subpieces, 360/192 samples and all 288 nodal entries per case.
This resolves the observed integration failure. It does not supply a general
layered branch selector, native all-node accuracy bounds, optimized-source
derivative validation or an updated three-dimensional forward solver.

**Small samples and relaxed stopping do not validate the full inverse calculation.**
The [completed legacy baseline
review](data/development/hayward_completed_baseline_review_001/README.md) retains
failed local rays, a final DD source step of 2.761 km, and two failed rays in the
final linearization despite a passing 32-ray sample. Accepted frozen-weight
objectives and unweighted RMS measure different quantities. A local flag may reflect
the combined small-action-change/gradient rule rather than the strict 1e-7 s/km
residual test. At nonsmooth faces, tangent-only residuals omit coupled normal
variations. The [published final CMJ
audit](data/development/hayward_cmj_final_tangent_support_001/RESULTS.md) bounds
complete feasible supporting vectors below 1e-7 s/km on two prescribed polygons.
This is stronger first-order evidence for those geometries, but not a minimum,
first-arrival, derivative-accuracy or inverse-convergence certificate.

**Guarded inversion progress remains intermediate.** The [first guarded
attempt](data/development/hayward_guarded_failure_001/README.md) rejected its first
trial because 181 rays failed local stopping. A separate catalog-only backtracking
attempt now has three preserved accepted states. The [first-state
plot](figures/hayward_accepted_update_001.pdf) shows the fraction-1/8 update from
the initial model; the [second-state
package](data/development/hayward_second_accepted_update_figure_001/RESULTS.md) and
[comparison
figure](data/development/hayward_second_accepted_update_figure_001/figure/accepted_update_2_minus_1.pdf)
show the next fraction-1/16 update. Its fixed-weight objective fell by 11.3999%.
The [third-state comparison](data/development/hayward_third_accepted_update_figure_001/RESULTS.md)
preserves the subsequent fraction-1/8 update, reducing its own fixed-weight
objective by 21.9581%. The two third-state snapshot variants agree numerically;
their distinct coordinate-basis labels remain intact. The 394 failed rays in
the next rejected trial do not describe this accepted state.
Weights are recomputed between iterations, and history RMS/ray diagnostics describe
pre-update states. These acceptances do not establish final convergence, updated-model
accuracy or recovery.

**Catalog differences and normalized waveform differences remain separate
evidence.** The completed inversions used catalog data only. The [identified CC
export](data/development/native_dt_cc_001/README.md) supplies 98 accepted
measurements covering 103 events and four channels. Historical response calibration
is not a prerequisite for normalized correlation; authoritative samples, timing,
identities, preprocessing and quality checks still are. The [59,078-row combined
input](data/hayward_catalog_cc_001/README.md) preserves all 58,980 catalog rows,
both observation endpoints' identities and channel epochs, but has not been
inverted. Its sparse CC connectivity does not determine combined-system rank or
resolution. The squared correlation coefficient is an empirical row multiplier
(fourth power in the objective), not a measured timing variance.

**Final-model uncertainty and complete rebuilding remain unfinished.** The earlier
field diagnostic uses only absolute picks at the legacy DD estimate. The new
[initial-model full-DD calculation](data/development/hayward_initial_full_dd_resolution_001/README.md)
includes catalog differences, source coupling and shared primitive-pick errors.
All 14,262 initial rays passed the saved reference and geometry checks; the
462-node matrices and seven-section display are complete. The display propagates
the full covariance to interpolated velocity. These results remain conditional on
initial sources/model and stage-0 weights, with reported symmetric pick
uncertainties assumed to be one sigma. Active source bounds, model and ray errors,
regularization bias and nonlinear uncertainty remain excluded. They do not supply
final-model covariance or total model uncertainty. The [report
checkpoint](data/development/initial_full_dd_report_001/RESULTS.md)
compiles, and [clean committed-input plot
replay](data/development/authoritative_geometry_cc_checkout_replay_001/RESULTS.md)
passes using the existing runtime. A clean end-to-end rebuild of corrected
inversions, recovery tests, resolution and report remains pending.

The separate [historical clean rebuild](data/development/historical_clean_rebuild_001/README.md)
completed all eight prescribed inversions and 48 component checks in 9,597
seconds at commit `976d2590c60f`. Its sampled truth, standard and DD ray checks
retained only 16/32, 2/32 and 11/32 true production convergence flags. Refinement
did not eliminate every failure. Successful command completion therefore did
not establish numerical acceptance or change the one/61 panel audit. The new
results are preserved separately from the original synthetic figures. In the
120-source experiment, location RMS error increased from 1.112 km initially to
3.061 km for standard tomography and 1.388 km for DD tomography, despite passing
the separate small homogeneous recovery control.
