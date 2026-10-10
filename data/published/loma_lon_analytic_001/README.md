# LON simulation publication

This package retains all LON-specific files under `files/`. The remaining
members are byte-identical to the verified LOM archive. `manifest.json` records
the complete LON inventory, every resource-bearing native table, the exact base
package files, and each replacement hash. `comparison.json` records the actual
model, configuration, source and payload differences. All observations are
synthetic; provider IDs identify the authoritative simulation geometry.

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
