# First guarded Hayward DD attempt

This is a prepared launch plan, not an inversion result. `plan.json` pins the
unchanged Hayward004 inputs, the completed preflight records, the reviewed O3
guard-adoption controls, the tested launcher, and a copied source snapshot.
`proposed_run.cfg` is byte-identical to Hayward004, including its documented
duplicate `ray_spacing` assignment: the final value is 0.03125 km. The auxiliary
field spacing is 0.125 km and the ray update budget is 1,000. This source snapshot
is evidence for review; the launcher will create and hash a separate executable,
compiler/build record, runtime library inventory, and source archive.

The proposed fresh output is `data/hayward_first_arrival_guarded_001`, with build
directory `tmp/hayward_guarded_runs/001`. It retains all 1,092 selected events,
372 native receiver epochs, 14,262 absolute picks and 44,718 catalog differences.
The native ray support is 14,262 event/epoch pairs; 37 exact receiver coordinates
share auxiliary fields without merging native identities. The separately
prepared waveform-derived rows are not part of this catalog-only attempt.

The inverse schedule is unchanged: at most 18 iterations in three six-iteration
stages, smoothing 10, damping 0.1 and pair distance 10 km. For absolute/catalog/
precise rows, `catalog_only_dd=1` selects stage multipliers (1, 0.1, 0),
(0.1, 1, 0), and (0.1, 1, 0). These multiply residual and Jacobian rows together
with the existing prior, robust and distance factors. A failed update can end a
stage under the existing algorithm; 18 is a budget, not a promised iteration
count. No observation, uncertainty, row convention or inverse parameter changes.

Full initial support has already passed the independent continuous 1D time and
source-vector controls. The completed sampled diagnostic and exact finite-
difference truncation assessment require independent readback and root's final
hash-bound accuracy review before launch. `ready_for_accuracy_review` alone is
not scientific acceptance. The declared 25 microsecond time and 3e-6 s/km source
vector limits are unchanged. No new finite-difference cutoff is introduced.

The guarded executable checks every current, trial and final forward evaluation
for finite values, exact endpoints, domain, initialization and unchanged local
stopping flags before using it in an objective or Jacobian. A failed evaluation
stops with identified evidence and separate candidate/last-accepted snapshots.
These checks neither prove globally earliest arrival nor transfer the initial
1D accuracy certificate to later 3D models. The proposed attempt uses four
threads and a 128 GiB address-space cap. A durable controller will preserve its
PID, logs, child lifecycle and terminal status; the original baseline and all
preflight evidence remain untouched.

Only DD is proposed for this first guarded attempt. Completion still requires
final-model ray/refinement/source checks, native output readback, and review of
actual accepted steps and LSQR/nonlinear behavior. Other modes and the separate
catalog-plus-CC comparison remain required follow-up work. No automatic cascade
or scientific-success flag follows from an executable exit code.
