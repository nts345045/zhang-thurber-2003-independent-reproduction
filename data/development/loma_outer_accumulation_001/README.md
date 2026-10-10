# Isolated path-accumulator controls

These controls test one declaration in the frozen `path_eval` function: its
outer total changes from `double T` to `long double T`. The function still
returns `double`. Segment calculations, internal gradients, the optimizer,
seeds, constraints, line search, stopping rules, and update budget are unchanged.
`single_change.diff` records the complete source change.

Both frozen builds pass 91 checks, for 182 checks in total. Four invented
homogeneous paths test the expected action and bitwise unchanged gradients.
The remaining checks use the original base polygon and all 24 actual rounded
trial polygons from the neutral replay of Loma initial pair 3426. The original
build reproduces every saved action. The modified build equals the binary64
cast of the extended-precision sum of the original binary64 segment values.
All 25 internal gradient arrays remain bitwise identical.

The native records retain event `quakeml:NC.anss.org/Event/NC/10090782`, origin
`quakeml:NC.anss.org/Origin/NC/2642854`, channel `NC.JSJ..EHZ`, FDSN identifier
`FDSN:NC_JSJ__E_H_Z`, and the original metadata epoch. Full identifiers and
geometry are in `inputs/identified_ray.csv` and the table sidecars.

`controls_summary.json` pins both source trees, the compiler, input files,
binaries, commands, and outputs. `controls_review.json` is the independent
read-only review. Neither the controls nor that review runs a new ray.

The separate native replay is prepared in
`../loma_outer_accumulation_native_001`. Its result must determine whether the
single change avoids the observed failure. These controls establish neither
convergence nor general action accuracy. Binary64 segment errors and the final
binary64 return remain; the original failed ray and neutral replay are retained.

From the integration worktree:

```sh
python3 diagnostics/prepare_outer_accumulation.py \
  --output data/development/loma_outer_accumulation_001 \
  --build tmp/loma_outer_accumulation_001
```

Output and build paths must be fresh; use new names for a repeat.
