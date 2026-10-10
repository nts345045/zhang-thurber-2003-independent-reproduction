# Independent double-difference tomography investigation

Independent C++/OpenMP implementation of the ray-based inverse problem in
Zhang and Thurber (2003), *BSSA* 93, 1875–1889,
[doi:10.1785/0120020190](https://doi.org/10.1785/0120020190).

This is a research reproduction attempt, with explicit limits. The report
retains a synthetic baseline using generated source/receiver geometry. The
original task excluded source observations; a later authorized Hayward catalog
DD inversion and absolute-data tomography have written numerical outputs.
A partial Figure 10 counterpart now compares their saved velocity models.
Fixed-model relocation and final ray diagnostics remain pending, and neither
completed method establishes nonlinear convergence. This is a partial scientific
checkpoint, not a completed manuscript reproduction.

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
result is available yet; the original running workflow retains its frozen solver.
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
refinement has not yet completed accuracy review; no corrected inversion has been launched.

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
A separate [boundary component calculation](data/development/loma_endpoint_connector_native_001/README.md)
replaces the first straight element by a constrained curved connector in the
saved affine layer. It retains the same local action, removes the demonstrated
source-normal term, and preserves the neighboring vertex's second-element
reaction. The reviewed calculation supplies no general trilinear connector
or model Jacobian and does not produce a new inverse result.
Only 37,599 rays pass all checks. LOM sampled checks and the LON initial-ray
preflight remain active; neither performs an inverse update. A separate
[one-sided curvature calculation](data/development/native_interface_conditioning/README.md)
assesses a saved interface direction, without changing production optimization
or promoting any failed flag.

A new [inversion forward guard](data/development/inversion_ray_gate_checks/README.md)
on the integration branch rejects locally unconverged or otherwise invalid rays
before Jacobian, trial-objective, or final-output use. It preserves identified
failed paths and model states separately from the last accepted state. Controlled
checks preserve successful inversion outputs byte for byte; this is failure
handling, not a first-arrival or nonlinear-convergence certificate.
Run these newer diagnostic and simulation commands from the
[`first-arrival-integration` branch](https://github.com/nts345045/zhang-thurber-2003-independent-reproduction/tree/first-arrival-integration).

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
have not entered the running catalog-only inversion; its saved results retain
their original inputs and limitations.

The separately [prepared catalog-plus-CC inputs](data/hayward_catalog_cc_001/README.md)
retain all 58,980 catalog rows and append the 98 waveform differences. Both
receiver epochs remain attached, including 38 pairs across metadata epochs;
the combined input uses exactly the same 14,262 native forward pairs.
The [adopted empirical weighting](data/development/catalog_cc_weight_adoption_001/README.md)
uses literal CC squared as a residual/Jacobian row multiplier, hence CC to the
fourth power in the squared objective before other factors. Timing uncertainty
remains explicitly unestimated. The preparation and independent full-file audit
do not create a configuration or inversion result.

[Read the PDF report](report/report.pdf) or the
[panel-by-panel audit](FIGURE_AUDIT.md).

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
  Hayward runs. The file guide distinguishes initial geometry, inversion
  products, and separate ray diagnostics. Missing method files mean that result
  has not been produced. `figure10_velocity_manifest.json` records the separate
  velocity comparison, including its input/output hashes and numerical limitations.
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
The Hayward plotting and resolution workflow also requires SciPy.
To plot the completed standard/DD velocity tables before other methods finish,
run `python3 plot_hayward.py --velocity-only`. This produces Figures 4 and 10
and a separate Figure 10 manifest; it does not complete the full workflow.

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
