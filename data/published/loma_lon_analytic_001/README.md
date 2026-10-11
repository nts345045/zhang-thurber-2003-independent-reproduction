# LON simulation publication

This package retains all LON-specific files under `files/`. The remaining
members are byte-identical to the verified LOM archive. `manifest.json` records
the complete LON inventory, every resource-bearing native table, the exact base
package files, and each replacement hash. `comparison.json` records the actual
model, configuration, source and payload differences. All observations are
synthetic; provider IDs identify the authoritative simulation geometry.

The [corrected recovery outcome](../../development/loma_inverse_outcome_001/README.md)
is **inverse not started: initial forward validation failed**. The completed
LON preflight has 50 source-vector failures among 37,648 rays, despite passing
time and original local-stopping checks. It made zero inverse updates; no
recovered velocity model or relocated-source output is claimed. Full failed-row
identities and simulation assumptions are preserved in the linked package.

Keep the complete LOM package with this package. Restore only into a fresh path:

```sh
python3 diagnostics/package_loma_variant.py verify --package LON_PACKAGE --base LOM_PACKAGE
python3 diagnostics/package_loma_variant.py restore --package LON_PACKAGE --base LOM_PACKAGE --output FRESH_DIRECTORY
```

Paths are relative to the repository. The helper rejects changed base or overlay
files, unsafe paths and existing restore directories. It verifies the base tar
stream, applies the declared replacements, and hashes every restored LON file.
A failed restore retains its partial directory for inspection. Original local
simulations remain unchanged. This publication establishes lossless storage,
not inverse accuracy or equivalence of the distinct starting velocity models.
