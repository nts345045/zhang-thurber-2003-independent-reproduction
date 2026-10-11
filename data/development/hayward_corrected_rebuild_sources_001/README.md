# Corrected Hayward rebuild sources

This source package prepares the independently selected authoritative Hayward
subset and appends the 98 saved, identified normalized cross-correlation
measurements. It builds one frozen guarded/backtracking C++ snapshot and permits
one DD inversion attempt. A failed preparation, build or inversion is an outcome
to retain. A zero process exit is not a claim of final ray accuracy, convergence,
resolution or manuscript recovery. This draft has not executed preparation,
compilation or inversion. Closed saved outputs then feed a short outcome report.

From the repository root, use fresh destinations:

```sh
python3 rebuild_hayward_corrected.py \
  --preparation-python /path/to/compatible/python3.6 \
  --report-python /path/to/python-with-matplotlib \
  --output data/hayward_corrected_rebuild_001 \
  --build tmp/hayward_corrected_rebuild_001
```

The entrypoint requires Linux process groups and `/proc`, Python 3.6 or later,
CMake 3.16 or later, a C++17 compiler with OpenMP, and its normal build tool.
The preparation interpreter needs NumPy and Requests. Requests is imported by
the published acquisition helper even though this procedure makes no network
request. The reporting interpreter needs Matplotlib; report compilation needs
`pdflatex` and the packages used by the compact report. The compiler can be
selected with `--cxx`. The numerical attempt uses
four OpenMP threads, one BLAS thread and the inherited 128 GiB address-space cap.
All caches, temporary files, build products and command logs remain under the
fresh build directory. Existing output/build directories and symbolic-link
destinations are refused; there is no resume, retry, alternate solver or fallback
dataset.

## Preparation and arithmetic compatibility

`prepare_hayward.py` is copied from the published root helper. Its exact diff
changes only repository-root discovery, explicit fresh output selection and the
CLI. It uses the saved selected-event, selected-pick, channel-epoch and station
policy CSV files. It does not reparse the raw XML, reacquire records, or change
the independent subset selection. The selected events retain their provider
event/origin IDs; every observation retains both pick/arrival identities and
the channel SEED/FDSN identities and separate metadata epochs. Empty location
codes remain valid.

Output is deliberately an immediate child of repository `data/`. The unchanged
`source_file` values, such as `../authoritative/hayward/raw/...`, therefore still
resolve to the saved provider records. The compact scientific input manifest
pins the directly consumed tables and all 20 provider-source files referenced
by the selected event/receiver tables. Those raw records are checked, not parsed
again. The expected selection manifest differs only in its explicit preparer
source hash.

Exact saved catalog weights depend on the preparation runtime. A fresh replay
with Python 3.6.8, NumPy 1.19.5 and Requests 2.20.0 reproduced all nine original
catalog files byte for byte. Python 3.11.9 changed the last bit of `math.hypot`
for some DD uncertainties and their row multipliers. The formula is unchanged.
`--preparation-python` selects the compatible interpreter; it defaults to the
entrypoint interpreter. Eight scientific files must match their saved hashes,
and the remaining selection-manifest fields must match exactly, before any
compile or inversion. A different result is preserved in
`catalog_compatibility.json` and stops the attempt. No rounding normalization or
identity-tolerance relaxation is applied. The combined-table hash also checks
the arithmetic of the entrypoint interpreter used by the unchanged assembler.

`prepare_hayward_cc.py` is an exact published copy. The entrypoint calls its
existing `assemble()` function, not its historical receipt-dependent `run()`.
It validates all 58,980 original catalog rows and joins the complete 44,718-row
catalog-DD sidecar: 98 exported measurements and 44,620 non-accepted records.
It retains every original catalog field and row order, and appends only the 98
already accepted measurements.
It does not correlate new waveforms. The 59,078 combined rows use the same
14,262 event/receiver rays. The saved CC squared value is an empirical residual
and Jacobian row multiplier, so its contribution to the squared objective has
CC to the fourth power. CC timing uncertainty remains blank and unestimated;
no formal CC covariance or instrument-response prerequisite is introduced.

## Selected numerical source and scope

`source/` contains exactly ten checked C++/CMake files. Nine are byte copies of
the published old-kernel guarded/backtracking snapshot. `src/main.cpp` adds
only the already checked accepted-state export, exposed by
`accepted_snapshot_main.patch`. The source is not taken from current root
`src/`, whose numerical lineage differs. `source_mapping.json` records exact
hashes and provenance; it does not require historical process logs or runtime
approval receipts in a fresh checkout.

The fixed `run.cfg` uses 18 iterations in three six-iteration weighting stages,
smoothing 10, damping 0.1, FMM initialization, 0.03125 km ray spacing, 0.125 km
FMM spacing and the unchanged 1,000-update ray cap. The three
absolute/catalog/precise stage factors are `(1, 0.1, 0.01)`,
`(0.1, 1, 0.01)` and `(0.001, 0.01, 1)`. This is a combined data and weighting
experiment, not a CC-only causal comparison. All original fatal current/final
ray guards remain. Only the reviewed trial-local stopping failure can trigger
the existing bounded line search: 12 trials total, including the full step.
No source derivative is zeroed and no tolerance is relaxed.

## Closed outputs

The numerical files and `run.cfg` are directly in the requested output folder.
The raw catalog table remains in `catalog_provenance/observations.csv`; the four
saved CC export/identifier files are copied into `cc_inputs/`. Every accepted
snapshot has its original `dd_accepted_it_N_events.csv` and `..._grid.csv` name.
Failure, trial and current-model exports retain their original names and full
native metadata. History RMS/ray metrics describe the pre-update state.

After actual child reaping and confirmation that its group has no live writer,
`rebuild_outcome.json` records `status`, `return_code`, `failed_stage`, `commands`,
`outputs_stable`, input/output hashes and `accepted_states`. Each accepted entry
has `iteration`, `events_file`, `grid_file`, and `sha256s` keyed by those relative
filenames. An accepted snapshot must join to a completed history row and the
terminal accepted trial row; orphan or incomplete files are retained without
being advertised as accepted states. `scientific_success` remains false.
Process/runtime receipts and logs are local generated state, not scientific
inputs to publish. A subsequent saved-output renderer can consume this closed
outcome. The same command calls the separately pinned
`plot_hayward_corrected.py` once and then runs exactly two `pdflatex` passes in
`OUTPUT/report/` after successful rendering. The PDF is
`OUTPUT/report/report.pdf`. If preparation did not leave complete identified
inputs, or accepted-state validation failed, the renderer produces an explicit
text-only outcome report. It does not substitute an unverified state. Report
commands have a separate `report_execution.json`; they never change
`rebuild_outcome.json`. An original nonzero numerical return code is retained
even if the report succeeds. A report failure also prevents overall success.
No report is attempted while an owned group might still write numerical output.

## Completed source and interface checks

Five process-only controls passed for the unchanged entrypoint: zero and nonzero
child exits, an executable that could not launch, cleanup of an orphaned
descendant, and interruption while a child and descendant were live. Every
launched process was reaped and no writer remained. Six saved-data renderer
controls passed across two source revisions: identified initial and third
accepted states, missing inventory, omitted acceptance, an interrupted history
tail, and a no-child launch failure. The two boundary PDFs compiled in four TeX
passes. Their overwide printed URL prompted the final descriptive-link-only
source correction. The corrected one-page PDF then passed two further TeX
passes and visual inspection, with no layout warnings and unchanged figure
bytes. [validation.json](validation.json) separates the tested source hashes
and the layout-only result. These checks did not run preparation, a C++ compiler, rays or inversion,
and do not establish a successful end-to-end corrected rebuild.
