# Independent double-difference tomography investigation

Independent C++/OpenMP implementation of the ray-based inverse problem in
Zhang and Thurber (2003), *BSSA* 93, 1875–1889,
[doi:10.1785/0120020190](https://doi.org/10.1785/0120020190).

This is a research reproduction attempt, with explicit limits. The existing
report records the first attempt: its synthetic inversion panels use generated
source/receiver geometry and are partial reproductions; Hayward field-data
panels were not computed. The original task excluded source observations.

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
picks. Historical channel matching identifies a new unresolved issue: 142 picks
at NC.CMW1 lack matching channel epochs, and borehole elevation conventions are
ambiguous at NC.CCH1, NC.CGP1, and NC.CSU1. These four stations account for 464
picks. [The metadata record](data/authoritative/stations/README.md) documents the
evidence. A clarification request is pending about excluding these stations or
resolving their metadata first. No field inversion has used them.

Independent ray-kernel corrections now improve quadrature accuracy and
optimizer conditioning. [The numerical audit](data/development/ray_optimizer_audit/README.md)
records 48 passing component checks and remaining failures when retracing
frozen baseline models. The saved inversions remain from the initial code;
the complete inversion rebuild has not been rerun with these corrections.

The revised solver preserves identities in event/residual CSV files and ray
diagnostic mappings, traces observed pairs only, and exports an unweighted
absolute-arrival Jacobian with `dd linearize`. `prepare_hayward.py` prepares the
identified field inputs, `resolution_hayward.py` implements conditional
resolution/noise propagation, and `plot_hayward.py` plots saved field results.
Their field-data execution awaits the metadata decision. The block algebra has
been checked against a direct joint-matrix calculation, including an unsensed
source column; this check does not establish field-data resolution.

`dd simulate CONFIG DIR` can generate synthetic observations from supplied
identified catalog geometry and supplied true/initial grids. Its observations
are labeled synthetic and retain geometry identifiers without inventing provider
pick IDs. Invented component fixtures check analytic arrivals, metadata retention,
and unchanged baseline random generation. No Loma Prieta subset has yet been
fetched or inverted with this command.

[Read the PDF report](report/report.pdf) or the
[panel-by-panel audit](FIGURE_AUDIT.md).

## Build and run

Requirements: C++17 compiler, CMake >=3.16, OpenMP, Python 3 with NumPy and
Matplotlib, and pdfLaTeX with the `fontenc`, `lmodern`, `geometry`, `amsmath`,
`amssymb`, `graphicx`, `booktabs`, `longtable`, `array`, `hyperref`, `url`,
and `listings` packages. No third-party tomography or optimization library
is required. The formatter used during development is not a runtime dependency.
The delivery environment is recorded in `reference/delivery_environment.json`.

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
