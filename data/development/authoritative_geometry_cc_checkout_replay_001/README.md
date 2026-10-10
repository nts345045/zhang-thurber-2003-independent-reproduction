# Historical clean-input plot replay receipts

This small package preserves `RESULTS.md` and all ten `logs/` files byte-for-byte
from the completed replay at
`tmp/authoritative_geometry_cc_checkout_replay_001`. That replay exported 65
committed files from main commit
`6a8f79167db4c932a9fa37e6097e7ab3e05b36df`, then ran each documented plot once.
Both commands completed and were reaped with exit 0. The Loma outputs matched
exactly; the CC PDF differed only in CreationDate, while its PNG, coordinates,
identifiers and sidecars matched exactly.

The copied records retain their original paths, commands, timestamps and
working-directory assumptions. In particular, `logs/check_replay.py` is the
historical comparator for that exported tree, not a command to run from this
small receipt package. `export.json` lists the exact committed input inventory;
`comparison.json` and `execution_receipt.json` bind the closed checks and
outputs. The 53 MB exported scientific tree, output figures and runtime caches
are intentionally not duplicated here. `packaging.json` verifies every copied
file and every export member against the recorded Git commit.

For portable plot replay, use the committed
[Loma geometry package](../loma_geometry_figure_001/README.md) and
[CC replay instructions](../native_cc_spatial_support_001/REPLAY.md), choosing
fresh output directories. Their saved native tables, identifier sidecars and
declared tracked scientific dependencies supply the inputs. Python and
Matplotlib remain external dependencies; this historical replay reused the
existing project-local runtime with caches inside its fresh tree.

This evidence covers committed-input replay of two plots. It does not record
a clean software installation, new waveform measurements, solver validation,
inversion or a clean end-to-end project/report rebuild. Published plot packages
and all original replay receipts remain unchanged.
