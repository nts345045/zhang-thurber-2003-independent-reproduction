# Rebuild, replay and report commands

The report combines independently generated results from several source
versions. No single completed command regenerates every current dataset and
figure. The [panel audit](FIGURE_AUDIT.md) records one reproduced panel and 61
partial panels; procedure completion does not change those scientific statuses.
The commands below are alternatives with distinct scopes, not one shell script
to run in sequence. Use a fresh checkout for either historical workflow, since
its script writes standard data, figure and report paths. Use absent output
directories for the portable replays. Runtime requirements are in the linked
package instructions and [README](README.md#build-and-run); keep caches inside
the checkout.

## Historical numerical workflows

| Procedure | Command and source | Recorded outcome and limits |
| --- | --- | --- |
| Synthetic generation, eight inversions, analysis and report | `./rebuild.sh` at commit `976d2590c60fae542e25c37c8b2352ff3765c6a1` | Completed in 9,597 seconds with 48 component checks and a 125-page PDF. Nine plot pairs were regenerated; the report used eight regenerated PDFs and 13 reused committed figures. The invented 120-event/32-receiver experiment is separate from the authoritative layout. |
| Historical Hayward standard, catalog DD and fixed-model relocation | `./rebuild_hayward.sh` at commit `3b674ba` | Completed in 33,712 seconds, including its figures and report. Scientific deficiencies remain: failed local ray flags, poor fixed-model relocation and a conditional absolute-arrival resolution calculation. This is the original unguarded workflow, not the newer guarded attempt. |

The [historical synthetic inventory](data/development/historical_clean_rebuild_001/README.md)
identifies regenerated and reused artifacts and the required runtime. Its new
outputs do not replace the original synthetic figures displayed in the report.
The [field readback](data/development/hayward_completed_baseline_review_001/README.md)
documents all three methods and their limitations. At another checkout revision,
the same script names can select different solver source bytes.

## Saved-input geometry and accepted-state figures

Run these from the repository root with a suitable plotting Python:

```sh
mkdir -p tmp
PYTHONDONTWRITEBYTECODE=1 python3 -B diagnostics/plot_loma_geometry.py --output tmp/FRESH_loma_geometry
PYTHONDONTWRITEBYTECODE=1 python3 -B data/development/native_cc_spatial_support_001/plot_cc_spatial_support.py --output tmp/FRESH_cc_support
PYTHONDONTWRITEBYTECODE=1 python3 -B data/development/hayward_second_accepted_update_figure_001/plot_second_update.py --output tmp/FRESH_second_update
PYTHONDONTWRITEBYTECODE=1 python3 -B data/development/hayward_third_accepted_update_figure_001/plot_third_update.py --output tmp/FRESH_third_update
```

The authoritative Figure 2 and CC-support commands passed a
[committed-input replay](data/development/authoritative_geometry_cc_checkout_replay_001/RESULTS.md).
Figure 2 shows 724 identified sources and 52 receiver epochs. It does not
replace the random geometry underlying historical Figure 3. The CC map displays
98 accepted measurements, not an inverted or resolution-tested CC dataset.
The [second](data/development/hayward_second_accepted_update_figure_001/README.md)
and [third](data/development/hayward_third_accepted_update_figure_001/README.md)
state packages contain completed renders and their scientific bindings.
The [first-state package](data/development/hayward_accepted_update_delivery_001/README.md)
provides the separate archive-restoration and replot commands. These displays
retain full identifiers and compare saved accepted geometries; they do not
repeat an inversion or establish convergence. Fresh plots do not automatically
replace the report's bound figure files.

## Initial-model full-DD resolution

```sh
python -B data/development/hayward_initial_full_dd_resolution_001/replay_resolution.py \
  --output tmp/FRESH_initial_full_dd_resolution
```

The [documented numerical replay](data/development/hayward_initial_full_dd_resolution_001/README.md)
and [separate plot replay](data/development/hayward_initial_full_dd_resolution_001/PLOT.md)
both completed. This command regenerates the matrix calculation from the
packaged operator and native inputs; it does not retrace the rays. It concerns
initial-model, stage-0, catalog-only conditional resolution and shared-pick
noise. It does not replace a final-model full-DD calculation or promote
Figure 11. The package separately documents regeneration of the omitted large
ray-path evidence.

## Corrected guarded DD attempt

Use the [portable procedure](data/development/hayward_corrected_rebuild_sources_001/README.md),
with the compatible preparation interpreter also running the entrypoint:

```sh
/path/to/compatible/python3.6 rebuild_hayward_corrected.py \
  --preparation-python /path/to/compatible/python3.6 \
  --report-python /path/to/python-with-matplotlib \
  --output data/hayward_corrected_rebuild_001 \
  --build tmp/hayward_corrected_rebuild_001
```

This regenerates the authoritative subset from saved selection tables, appends
98 saved normalized CC measurements, builds the package's frozen ten-file
solver snapshot and attempts one DD inversion. It makes no new provider query
or waveform measurement. Python 3.6.8 reproduced the legacy catalog weights;
the documented Python 3.11 rounding difference stops preparation honestly.
The fresh checkout at `1d04838e7ac7` completed preparation and compilation; its
inversion has not yet finished at this checkpoint. The later executable-alias
fix has a successful saved-output reporting check, not a second full numerical
attempt. Failures remain in the output, and its short outcome report does not
replace the comprehensive report.

## Corrected catalog-only comparisons

The [comparison entrypoint](data/development/hayward_catalog_comparisons_001/README.md)
uses the same frozen solver source and the original catalog-only configuration.
Run each mode with its own fresh destinations:

```sh
python3 -B run_hayward_catalog_comparison.py --mode standard \
  --preparation-python /path/to/compatible/python3.6 \
  --output data/FRESH_hayward_standard --build tmp/FRESH_hayward_standard
python3 -B run_hayward_catalog_comparison.py --mode loc1d \
  --preparation-python /path/to/compatible/python3.6 \
  --output data/FRESH_hayward_loc1d --build tmp/FRESH_hayward_loc1d
```

The [actual attempts](data/development/hayward_catalog_comparisons_001/ATTEMPTS.md)
passed preparation and compilation. Standard attempt 001 was interrupted by
SIGTERM before its first update; its closed outcome preserves the interruption
without attributing the signal's origin or inferring a numerical failure.
A separate standard attempt 002 and the original fixed-model comparison are
active at the 11 October 2026, 02:45 UTC checkpoint. Standard
tomography uses absolute rows and estimates velocities and sources. Fixed-model
relocation holds the initial velocity grid and uses the original catalog-DD
stages. These commands append no CC rows and retain all current/trial/final ray
guards. Their closed outcomes will be recorded in `comparison_outcome.json`;
they do not yet supply a corrected standard or relocated-source panel.

## Assemble the comprehensive report from saved artifacts

The dependency order is saved numerical results and identity companions, then
their figures and generated TeX tables, then `report/report.tex`. The committed
checkout includes these report dependencies. `audit.py`, `analyze.py` and the
plotters refresh particular products from available data; they do not run all
upstream experiments. Do not treat their execution as complete regeneration.

Two-pass comprehensive report compilation has completed, as recorded in
[the report validation](report/rebuild_scope_validation.json). To compile the
current source and saved dependencies into a fresh local directory without
replacing the published PDF:

```sh
set -e
mkdir -p tmp
report_output="$PWD/tmp/FRESH_report_assembly"
mkdir "$report_output"
mkdir "$report_output/temp" "$report_output/cache" "$report_output/texmf-var" "$report_output/texmf-config"
export TMPDIR="$report_output/temp" XDG_CACHE_HOME="$report_output/cache"
export TEXMFVAR="$report_output/texmf-var" TEXMFCONFIG="$report_output/texmf-config"
(
  cd report
  pdflatex -interaction=nonstopmode -halt-on-error -output-directory="$report_output" report.tex
  pdflatex -interaction=nonstopmode -halt-on-error -output-directory="$report_output" report.tex
)
```

This writes `tmp/FRESH_report_assembly/report.pdf` and local compilation logs.
It preserves the `pdflatex` invocation name and uses the published TeX package
requirements. It runs no numerical model or plotting command. A new assembly
must retain its actual outcome; earlier successful compilation does not certify
later source changes. Missing dependencies or scientific failures should be
reported explicitly, rather than replaced with older outputs presented as new.
