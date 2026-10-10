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
