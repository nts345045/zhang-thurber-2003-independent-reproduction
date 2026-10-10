# Spatial support of accepted waveform differences

This figure uses only closed, independently reviewed inputs: 98 accepted CC
measurements, their 103 events, the full 1,092-event catalog geometry, and four
receiving channels. It changes no measurement, observation, model, gate or
manuscript-panel status. The [connectivity evidence](../native_cc_connectivity_001/README.md)
and [combined-input review](../../hayward_catalog_cc_001/README.md) supply the
closed provenance. No waveform, graph, forward or inverse calculation is repeated.

`plot_cc_spatial_support.py` checks the accepted table against every corresponding
original catalog field and both absolute pick records. Event/origin indices,
pick/association IDs, full SEED/FDSN names, both receiver epochs and metadata
source hashes are joined to the saved tables. All original accepted-row fields
remain unchanged in `render_002/plotted_event_pairs.csv`; appended coordinates are
the original decimal strings in km. `render_002/plot_identifiers.json.gz` retains
all 1,092 native event records, all 22 used receiver-epoch records, all 98 full
measurements, both absolute pick records, and the existing component membership.
Empty strings are preserved. The 38 cross-epoch pairs remain distinct even
where their receiver coordinates coincide.

The PDF and PNG use the saved local rotated x/y coordinates with equal physical
scales on each axis. Panel (a) includes the four receiver positions; panel (b)
shows a northern detail marked by a dashed box in panel (a). Colored segments connect
paired events and are not ray paths. Receiver epochs are displayed by one
channel symbol only after exact equality of their saved coordinates is checked.
The full self-contained caption is saved as `render_002/CAPTION.txt` and in the
figure identifier sidecars. No fault trace, basemap, interpolation, jitter or
displacement amplification is introduced.

The figure describes availability-limited observed support. The 32 CC-only
components do not establish combined-system rank, resolution or recovery.
Unobserved support does not establish historical waveform absence or exclusion
from the original study. The catalog-plus-CC input has not been inverted.

The first render in `result/` passed all joins but its x-axis label overlapped
the legend. Its source, README, logs, figures and execution receipt are retained.
The second render changes only the plot's bottom margin; `layout_correction.patch`
records that one-line source change. The final PDF and PNG are in `render_002/`.

From the integration checkout, the second fresh render uses:

```sh
PYTHONDONTWRITEBYTECODE=1 tmp/waveform_env/bin/python -B data/development/native_cc_spatial_support_001/plot_cc_spatial_support.py --output data/development/native_cc_spatial_support_001/render_002
```

For a repeat, supply `--output tmp/FRESH_CC_MAP`; the destination must be absent.
The existing project-local plotting environment is used. Matplotlib caches stay
under project `tmp/`, outside the evidence package. Every result retains the
executed plotting source, source/input hashes, package versions, all output
hashes and join counts. A separate execution receipt records actual tool
completion. Plotting failures and any earlier renders are retained.
