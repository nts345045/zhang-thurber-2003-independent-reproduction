# Full-DD resolution ray-input prerequisite

The analysis previously hashed its exported ray table without reading it. It
now checks that table before matrix assembly and refuses any existing intended
resolution output before reading the inputs. No field calculation was run.

All 56 new invented controls pass. The existing 39 algebra/control records and
their Python, NumPy and SciPy versions are exactly unchanged in the separate
`prior39/` execution. The bodies of `joint_resolution`, `pick_noise` and
`triplet_matrix` are byte-identical to the preserved previous source.

The reader reconstructs unique event/receiver-epoch support from every original
observation, including rows omitted by weights. It preserves the loader's
`station_j` semantics, checks both epochs without collapsing colocated receivers,
and matches every source/receiver metadata string to the native tables. Valid
empty location codes and open epoch ends remain empty. Recorded coordinates
must equal the native coordinates numerically after 12-significant-digit
serialization, as written by this exporter. This is a serialization check,
not a coordinate-accuracy tolerance.

The reader rejects incomplete/duplicate/unexpected support, changed identities
or coordinates, inconsistent aggregate counts, and nonfinite/negative displayed
travel time or gradient norms. Its flag predicate is the existing exporter rule:
`!ray_finite || !ray_converged || (attempted && !succeeded)`. Unattempted
initialization is allowed and counted explicitly; unused seed diagnostics need
not be finite. No magnitude cutoff or altered convergence threshold is added.

The current exporter does not include path-domain, exact-endpoint or
source-partial fields in this table. Those properties cannot be independently
checked here. Passing this prerequisite does not certify first arrivals, final
model accuracy, derivative accuracy or nonlinear convergence. Source constraints,
fixed weights/masks and the original-pick noise assumptions retain their existing
limitations. No CC timing uncertainty is assigned.

`new_checks/` retains every malformed or valid invented CSV and its native input
tables, plus the frozen reader and control source. Its entry-point control
rejects a failed recorded ray before any matrix assembly. Separate controls
verify preservation of all four resolution-output suffixes and a dangling output
symlink. The symlink is removed after its behavior is recorded; it is not a
published runtime artifact. All resource identifiers in these fixtures are
explicitly invented.

`changes.patch` records the maintained-source correction. `source/` preserves
the before and after analysis. `execution_receipt.json` records the two commands
and their observed zero return codes; its pending-review status describes the
time that receipt was created. A later independent review is kept separately in
`review.json`. `prior39_comparison.json` pins the exact old/new result comparison.

Reproduce only the invented controls in fresh project directories:

```sh
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python3 diagnostics/check_full_dd_resolution_rays.py --output data/development/full_dd_ray_input_repeat
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python3 diagnostics/check_full_dd_resolution.py --output data/development/full_dd_algebra_repeat
```

No solver source, frozen exporter artifact, observed input, live run, original
39-control package or Git index was changed by this task.
