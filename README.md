# Independent double-difference tomography investigation

Independent C++/OpenMP implementation of the ray-based inverse problem in
Zhang and Thurber (2003), *BSSA* 93, 1875–1889,
[doi:10.1785/0120020190](https://doi.org/10.1785/0120020190).

This is a research reproduction attempt, with explicit limits. The report
retains a synthetic baseline using generated source/receiver geometry. The
original task excluded source observations; a later authorized Hayward catalog
DD inversion has now produced complete numerical outputs. Absolute-data
tomography and fixed-model relocation remain active, so the field comparison
figures and the full workflow are pending. This is a partial scientific
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
The prototype has not been integrated into the production inversions.
The [fixed-model field comparison](data/development/fmm_hayward_audit/README.md)
finds two faster candidates exceeding 1 ms among 186 selected shallow-endpoint
rays; it does not quantify the resulting inversion bias or certify first arrivals.

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
and exclusion records. It has not yet been simulated or inverted with this command.

[Read the PDF report](report/report.pdf) or the
[panel-by-panel audit](FIGURE_AUDIT.md).

## Where to inspect outputs

- `data/synthetic/`: existing baseline inversions. `standard_grid.csv` and
  `dd_grid.csv` contain inferred P velocities; method-specific `*_events.csv`,
  `*_history.csv`, and `*_residuals.csv` contain source estimates, convergence
  histories, and observation residuals. These inversions predate the ray fixes.
- [`data/hayward/`](data/hayward/README.md): authoritative inputs and current
  Hayward runs. The file guide distinguishes initial geometry, inversion
  products, and separate ray diagnostics. Missing method files mean that result
  has not been produced.
- `figures/` and `figures/hayward/`: plots generated from the saved numerical
  tables. `report/report.pdf` explains the experiments and reproduction limits.

## Build and run

Requirements: C++17 compiler, CMake >=3.16, OpenMP, Python 3 with NumPy and
Matplotlib, and pdfLaTeX with the `fontenc`, `lmodern`, `geometry`, `amsmath`,
`amssymb`, `graphicx`, `booktabs`, `longtable`, `array`, `hyperref`, `url`,
and `listings` packages. No third-party tomography or optimization library
is required. The formatter used during development is not a runtime dependency.
The delivery environment is recorded in `reference/delivery_environment.json`.
The Hayward plotting and resolution workflow also requires SciPy.

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
