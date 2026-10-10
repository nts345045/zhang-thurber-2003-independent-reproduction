# First accepted Hayward update: report checks

This checkpoint documents the first accepted update of the separate catalog-only
Hayward backtracking attempt. The run remains incomplete. The
[saved-state archive](../hayward_accepted_update_delivery_001/README.md) contains
the identified initial and accepted models, observation mappings and plotting
source. Its fresh restore and replot completed successfully.

`compile.py` records two ordinary TeX passes, all 16 source hashes, extracted
text and PDF metadata. `validate.py` checks the compiled report against the
closed archive and receipts, the printed quantities, identifier references,
document paths and unchanged manuscript panel classifications. It performs no
ray, Jacobian, inversion or numerical integration calls.

The first validator execution passed its content checks but failed when it
passed a relative `__file__` to an absolute-path hashing helper. The original
source, partial path inventory and actual failure receipt are retained in
`failed_validation_001/`. Resolving that one path allowed the subsequent
execution to finish; the compiled report was unchanged. See
[RESULTS.md](RESULTS.md) for validation results and scientific limits.
