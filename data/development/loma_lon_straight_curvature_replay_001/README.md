# LON straight-start old/D replay

This bounded diagnostic evaluates the worst interior source-derivative failure, pair8670, and a same-event, straight-selected passing control, pair8674. Both use source166 (NC event10090456, origin2644764), with NC.JHL..EHZ and NC.JRG..EHZ respectively. Complete original native records, valid empty location codes, channel epochs, perturbed initial coordinates and saved FMM metadata are frozen in `inputs/native_context.json` and the selected CSVs.

The source archive belongs to the completed LON initial matrix stage. Its `trace_first_arrival` first evaluates `trace` with a null seed and copies the returned Ray when the straight result is selected. The driver invokes that same public entry using archived readers, spacing0.03125km,1000updates and full derivatives. It does not construct an FMM field or add source.t to travel time. Native files preserve their original precision. The new straight-only initializer fields are distinct from the separately saved original two-start metadata.

`prepare.py` freezes the exact old source and tested/adopted D core/helper. The D snapshot changes outer action accumulation and usable-curvature handling together. Other archived source members remain byte-identical. `run.py` requires an independent passed `prelaunch_review.json` bound to `prepared.json`, compiles with the original compiler and flags, evaluates the two old calls, and demands exact original12-significant-digit scalar/status/native strings (excluding saved-only FMM fields) before compiling/evaluating D. All four final paths and complete model partial arrays are retained at17digits with native IDs on every row. No iteration instrumentation or path history is introduced.

Preparation and execution use fresh files exclusively. From this directory:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 prepare.py
# After the independently reviewed preparation is recorded:
PYTHONDONTWRITEBYTECODE=1 python3 run.py
```

`characterization.json` describes the37 saved interior failures and references their fully identified rows. It does not infer a causal mechanism. The original local flags are preserved separately from the unchanged25microsecond time and3e-6s/km Euclidean source-derivative gates. A true flag with gradient above1e-7 can only arise from the unchanged combined stop, but no detailed termination history is asserted from this uninstrumented replay. Any old/D difference concerns the complete adopted package, not an isolated curvature or summation effect. These two selected straight starts do not establish full-cohort accuracy, a new branch selection, global3D first arrivals, or inversion readiness.
