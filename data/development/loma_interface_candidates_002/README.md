# Feasible interface probes of the saved B polygon

This calculation changes no optimizer or saved ray. It evaluates three explicit
candidate polygons from the terminal, unconverged FMM path in
`../loma_outer_accumulation_native_001`. Nodes 484 and 485 straddle the known
7 km velocity-gradient interface at depths 6.9999999999953371 and
7.0000000000023856 km. All other coordinates and both ray endpoints stay fixed.

| Vertices placed at exactly 7 km | Certified action change (s) | Changed edges |
| --- | ---: | ---: |
| 484 | -1.46037531998e-16 | 2 |
| 485 | +4.31711554273e-17 | 2 |
| 484 and 485 | -2.11957953356e-16 | 3 |

The last decrease is smaller than one binary64 unit in the stored total
travel time. These candidates were not original line-search trials. A smaller
action does not establish stationarity or justify an optimizer snapping rule;
in particular, moving vertex 485 alone increases the action.

The calculation reuses the reviewed reciprocal-affine segment and exact
binary64-input arithmetic. Unchanged edges cancel identically. Thirteen
invented homogeneous controls check identity, changed-edge inventory, closed
forms, and reversal. Homogeneous actions cannot independently detect a wrong
depth-axis permutation; the separate native readback must test that mapping.
Separate 80- and 120-digit
Decimal evaluations lie inside each rational enclosure. Only action is used:
the aligned interface edge's supporting vector is not interpreted as an
ordinary derivative. No source or model derivative is changed.

`summary.json` retains the complete context for event
`quakeml:NC.anss.org/Event/NC/10090782`, origin
`quakeml:NC.anss.org/Origin/NC/2642854`, channel `NC.JSJ..EHZ`, FDSN identifier
`FDSN:NC_JSJ__E_H_Z`, and its 1989-05-02T15:00:00–1990-09-14T21:50:00 epoch.
The current initial geometry remains identified as a perturbation of the
authoritative catalog geometry. Input sources, native tables, sidecars and
reviews are copied and hashed under `inputs/`.

Run from the integration worktree into a fresh directory:

```sh
python3 diagnostics/check_loma_interface_candidates.py \
  --output data/development/loma_interface_candidates_REPEAT
```

The earlier `../loma_interface_candidates_001` produced identical numerical
enclosures but included interpreter bytecode in its artifact inventory.
This repeat disables bytecode generation and contains only source and data.
Both local runs are preserved. Independent review passed and is attached as
`review.json`; its reproducible checker is in
`../loma_interface_candidates_review_001`. It verifies the native depth
mapping with separate parameter-split Decimal integration. This diagnostic
was excluded from the preceding accumulator publication.
