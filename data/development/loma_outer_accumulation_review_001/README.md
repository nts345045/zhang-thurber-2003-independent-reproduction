# Saved-result review of the outer-accumulator experiment

`review_saved_result.py` reads the completed, frozen evidence in
`data/development/loma_outer_accumulation_native_001`. It neither evaluates a
segment action nor compiles or runs a ray solver. It requires the completed
native ledger and verifies the source, inputs, native metadata, saved paths,
history arithmetic and continuous-reference comparison.

From the integration repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 data/development/loma_outer_accumulation_review_001/review_saved_result.py
```

The initial execution adds `--write-review` to write the new immutable
`loma_outer_accumulation_native_001/review.json`; later readbacks should omit
that option. The review pins the helper and terminal evidence by SHA256.

The observer's recorded parity means exact numeric equality between observed
and unobserved executions of candidate B. The unchanged C++ comparisons do not
distinguish signed-zero representations. Original A is retained separately;
candidate B need not equal A. The field `original_local_convergence_flag` in
the launcher output means B's unchanged reported flag.

Reconstructing a recorded binary64 Armijo inequality does not certify a
continuous action decrease. Local convergence, reference time error and source
vector error remain separate results. This one-ray experiment cannot establish
general convergence, global branch completeness or inversion readiness.
