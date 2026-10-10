# Streaming simulation-audit controls

All 24 checks pass. These controls consume the saved **invented** two-source,
two-receiver launcher fixture; they do not run a simulator, trace rays, or audit
actual Loma observations. The positive case contains four arrivals and eight
observations. The separate terminal CLI smoke check is recorded in
`../../analytic_simulation_launcher_001/independent_stream_review.json`.

Run from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 data/development/analytic_simulation_review_checks/001/check.py
```

`check.py` imports the frozen audit source, copies the existing invented fixture
to project-local temporary directories, and checks terminal/hash rejection,
row ordering, absolute and differential values, native event/channel/epoch
identities, blank ray fields, quantization, and full-precision truth-status
coordinates. Seven explicit rounding cases include positive and negative ties
and the representable values immediately below a tie. Source, fixture manifest
and execution hashes are recorded in `results.json`.

The value bound is the sum of the operand/result half-units at 12 significant
decimal digits, with a floating-point parsing/arithmetic bound proportional to
machine epsilon. It is a serialization check, not an accuracy threshold for
reference or inverse rays. The audit verifies the saved noise algebra; the C++
random-number sequence is tested separately by the consumer-contract fixtures.
