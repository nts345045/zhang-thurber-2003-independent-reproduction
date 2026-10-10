# Reference-cache controls

`diagnostics/check_reference_cache.py` passed 17 checks. Small files under `cache/` and `data/` are explicitly invented identity fixtures, not earthquake or station data. They test rejection of stale or incompatible reference inputs and candidate metadata. All fixture mutations are restored after the checks.

The final check uses the separately frozen full Hayward preflight 003 replay: both comparison streams match the original bytes for all 14,262 rays, and the time/source-vector pass counts match the independent review. Euclidean source-vector accuracy is distinct from each coordinate's error and from the solver's local convergence flag.

`summary.json` records the checks and file hashes; `source/` preserves both executed helpers. The helper refuses to replace this directory. Repeating the controls requires a new output name in a copied helper and expanded table archives for the original and replay comparisons. This component validation does not establish accuracy for a changed continuous model or certify any inversion.
