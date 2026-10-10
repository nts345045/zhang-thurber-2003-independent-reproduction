# Independent scalar-contact readback

The source/math and saved-output review passed without rerunning a segment, minimizer, finite-difference evaluation or model. `check.py` verifies all four input and eleven output pins and reconstructs both precision rosters, original velocity-kernel to negative-log column scaling, candidate central differences, error/budget classifications, y-mirror identities and precision-agreement summary. Its terminal stdout is `readback.json`.

The actual command was:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 data/development/loma_endpoint_scalar_contact_review_001/check.py > data/development/loma_endpoint_scalar_contact_review_001/readback.json
```

Exit code was zero. The final `../loma_endpoint_scalar_contact_controls_001/review.json` adds the separately read final README hash and its bounded interpretation to that saved readback. The only requested prose correction called the receiver's incident contribution its adjacent edge rather than its first edge; executed numerical source/results were unchanged.

All 87 recorded controls pass. Each precision preserves seven scalar cases, 224 model columns and 448 perturbed models. There are zero declared numerical discrepancy-budget failures, but 192 positive-epsilon perturbed-envelope comparisons and all 224 derivative error bounds remain unresolved. The boundary family has nonunique contact representations; its collapsed source link has no assigned ordinary endpoint partial. The finite receiver normal partial remains. These are invented restricted-family calculations, not native/production or general endpoint-envelope validation.
