# One fixed half-step on each saved direction

This package is source and preparation only. It has not rounded a native trial
or evaluated an action. Root must review the frozen source and preparation
before executing its single command.

The second full-step trials for events 981 and 987 at receiver 160 had resolved
positive action changes despite negative directional slopes. Their rejected
`alpha = 1` results remain immutable. This separate diagnostic tests exactly
`alpha = 0.5` on those same saved directions, starting from the retained
accepted first-step paths. It does not start from either rejected trial.

## Unchanged numerical operations

The pinned step-002 wrapper supplies its existing standard-library saved-data
loader and process-group cleanup functions. Importing that wrapper does not
call its `main`. The loader joins the original model, native identities,
complete starting action cache and raw post-step component intervals without
integrating or solving anything.

The new wrapper reads the saved metric output and checks its decimal/hex
direction against the recorded full direction. Contraction with every raw
available component must exactly reproduce the saved negative interval slope.
The fixed half-step must lie within the already reviewed geometric bound.
There is no new metric, gradient, direction or bound calculation.

Only the unchanged binary's `round` mode is called, once per case. The frozen
`trial_geometry` checks the actual separately rounded displacement, fixed
endpoints and unavailable normals, box and positive edges. Only a negative
actual-displacement contraction permits the unchanged `trial_actions` call.
It uses the complete cached starting action, exact ordered-edge cancellation
and the existing conservative Armijo comparison with the nominal slope.

The limits are two rounding calls and at most 2058 new action edges, using
8 terms, 1 subdivision and 128-bit dyadic bounds. There is no metric call,
tangent integration, compilation, trace, field, alternate step or loop. Any
failure or unresolved/rejected trial is preserved; no quarter-step follows.
Original flags remain false, source partials remain blank and candidate
convergence remains null. No new post-trial tangent norm is computed.

## Native and terminal records

Every case preserves the complete event/origin, channel/epoch, pick/association
and all nine catalog row/side uses, including both receiver epochs. Current
path coordinates remain distinct from provider catalog coordinates. Each new
numeric file receives its identifier sidecar before numeric input bytes or
helper launch. The chain binds the retained first trial, reviewed post-step
tangents, rejected full-step result and exact saved direction output.

Outputs are `event_EVENT/result.json.gz`, `event_EVENT/round/*`, and terminal
`summary.json`/`execution.json`. The result retains the positive full-step
action difference as provenance alongside the separate half-step outcome.
There is no `metric/` output. The wrapper preserves the previous owned/reaped
child pattern, PID-before-unmask order, signal exit status and refusal to hash
files while writers remain. Root owns and reaps the outer wrapper.

The exact source, reviewed inputs, binary/runtime and command are in
`prepared.json`. Only after independent prelaunch review, from the project root:

```sh
PYTHONDONTWRITEBYTECODE=1 /usr/libexec/platform-python3.6 data/development/hayward_cmj_tangent_half_step_001/run.py
```

Preparation consists of source writing, Python syntax/AST checks, copied
identity metadata and byte hashes. No native loader or numerical module has
been imported or executed during preparation.
