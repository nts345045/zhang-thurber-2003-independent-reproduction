# Closed CC spatial-support figure

The final [PDF](render_002/cc_spatial_support.pdf) and
[PNG](render_002/cc_spatial_support.png) show 98 accepted event pairs, their 103
events, all 1,092 selected catalog events, and four receiving channels. The
northern detail uses the same saved coordinates. Colored links join events;
they are not ray paths. The [caption](render_002/CAPTION.txt) limits the figure
to observed input support, without rank, resolution or inverse-accuracy claims.

All 3,385 recorded checks pass, with 14 source/input pins verified before and
after plotting. The [derived table](render_002/plotted_event_pairs.csv) retains
every original field of all 98 accepted rows, with unchanged saved coordinate
strings appended. The [full identifier sidecar](render_002/plot_identifiers.json.gz)
preserves both event/origin/pick/association identities, SEED/FDSN names, all 22
used receiver epochs, and both sides of 38 cross-epoch pairs. No blank field is
filled or channel epoch substituted. Channel counts are JPR 75, CBR 19, JSB 3
and JSF 1; the existing CC-only graph has 32 components.

The [plotting source](plot_cc_spatial_support.py) completed under owned session
79188, reaped with code 0 in terminal chunk `40136e`; the recorded Python PID
682229 was absent afterward. The [execution receipt](execution_receipt.json)
binds the source, inputs, outputs and [visual review](visual_review.json).
The initial render and its label/legend overlap remain under `result/`;
the exact correction changes only the bottom margin. The derived table is
byte-identical between renders. Both final PNG and separately rendered PDF
were inspected for readability and clipping.

No waveform request, correlation, graph recomputation, forward or inverse call
was made. The report, manuscript-panel audit and publication remain unchanged.
