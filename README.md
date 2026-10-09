# Independent double-difference tomography investigation

Independent C++/OpenMP implementation of the ray-based inverse problem in
Zhang and Thurber (2003), *BSSA* 93, 1875–1889,
[doi:10.1785/0120020190](https://doi.org/10.1785/0120020190).

This is a research reproduction attempt, with explicit limits. The true
synthetic velocity profile is reconstructed from prose. Synthetic inversion
panels use independently generated source/receiver geometry and are partial
reproductions. The Hayward field-data panels require observations excluded
by the task and are not reproduced. No original model code, observations,
simulation outputs, plotting scripts, or figure files were used.

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
- `reference/task.md`: project scope and exclusions.

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
