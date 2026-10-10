# Uniform station-bias support check

All 25 controls pass with the final streaming-audit source. This variant adds
rejection of a station bias outside the configured uniform support, including
only the documented CSV serialization bound. Normally distributed pick noise
is checked for finiteness; no magnitude cutoff is imposed.

The preceding 24 checks and frozen source remain unchanged in `../001/`.
This variant imports its own frozen source. Reproduce the controls from the
repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 data/development/analytic_simulation_review_checks/002/check.py
```

`terminal_fixture_review.json` is the final maintained helper's complete CLI
check of the existing invented launcher output (four arrivals, eight
observations), including pre/post artifact hashes and terminal status. Its
command and source hash are recorded in that file. No actual Loma simulation
was audited here, and no simulator or ray tracer was run by these checks.
