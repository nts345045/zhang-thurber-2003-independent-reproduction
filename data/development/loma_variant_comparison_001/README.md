# LON simulation audit and lossless publication

The independent streaming audit checks all 37,648 arrivals and 15,932,384
observations in the completed LON simulation. All native event, origin,
channel, epoch and source-hash joins pass. The observations are synthetic;
provider identifiers describe the authoritative geometry. `audit_execution.json`
records the exact command, executing reviewer, source hash, logs and resources.
The audit does not establish forward-ray or inverse accuracy.

`compare.py` compares the complete completed LOM and LON file inventories,
requires both independent simulation reviews to pass, and rehashes every
original file before writing `comparison.json`. It also verifies that the
complete original LOM inventory equals the published LOM archive inventory.

The six physical output files are byte-identical: `truth_events.csv`,
`initial_events.csv`, `arrivals.csv`, `observations.csv`,
`simulation_truth_status.csv` and `simulation_truth_mode.txt`. The receiver
table is also identical. In total, 37 files containing 6,992,669,475 bytes are
identical; 11 files containing 87,668 bytes differ. All 48 original LON files
are retained locally, totaling 6,992,757,143 bytes.

All 288 starting-grid rows retain identical coordinates and ordering, while
their velocities differ. Values are in km/s and depths in km:

| Depth | LOM | LON |
| --- | --- | --- |
| -1 | 3 | 2.53 |
| 0 | 3 | 2.53 |
| 3 | 5.160638297872341 | 5.50640625 |
| 7 | 5.9521387283237 | 6.03765625 |
| 11 | 6.113988439306358 | 6.345629139072848 |
| 16 | 6.316300578034682 | 6.478079470198676 |

These are the declared gradient adaptations of USGS Open-File Report 93-578,
Table 4; neither is established as the target manuscript's exact starting
profile. `run.cfg.diff` and `preflight.cfg.diff` show the changed model label
and `initial_model` value from 1 to 2. The frozen source inventories differ
only in `src/main.cpp`; both distinct source archives remain preserved. The
actual output-byte comparison establishes equality of the listed simulation
outputs despite that source difference, without asserting equivalence of
subsequent inversions.

The compact publication is
`data/published/loma_lon_analytic_001`. Its manifest lists the full LON
inventory, pins every file in the verified LOM base package, and stores all
11 LON replacements under `files/`. Native table mappings refer explicitly
to the pinned base and the restored LON member paths. This avoids duplicating
the large identical observation payload. Both publication directories are
required to restore the LON run.

`overlay_create_execution.json` and `overlay_restore_execution.json` record
the exact publication and fresh-restore commands, source hashes, return codes,
logs and resource use. Successful restoration means the complete 48-file LON
inventory and every member hash match the original. The helper rejects stale,
missing, extra or altered base/package files, unsafe paths and an existing
restore directory. The original LOM and LON simulations are preserved.
Independent publication review is stored here as `overlay_review.json`,
outside the package's strict inventory.

Actual creation and fresh restoration both passed. The compact package has
15 files totaling 132,136 bytes. Creation took 101.11 seconds with 19,392 KiB
peak resident memory; restoration took 170.85 seconds with 25,316 KiB peak
resident memory. The restored 48-file inventory contains 6,992,757,143 bytes.
The root review independently rehashes the base/package and the restored
non-observation members, and explicitly relies on the pinned successful
streamed restore for the full observation payload instead of claiming a
second full read.

The helper's 18 invented storage controls are preserved in
`data/development/loma_variant_packaging_checks_001`; they cover additions,
removals, exact restoration, stale bytes, missing/extra files, unsafe paths,
failed comparison and nonfresh destinations. No data-selection or numerical
acceptance threshold is changed by publication.
