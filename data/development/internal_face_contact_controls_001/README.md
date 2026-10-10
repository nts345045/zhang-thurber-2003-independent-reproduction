# Invented internal-face contact controls

This source-only preparation tests a finite contact/release proposal on small invented polygons. It does not run the production ray optimizer, a field solve, an inversion, or a native-data example. No control has been compiled or executed yet.

Coordinates are in km, velocities in km/s, and actions in s. The fixed-endpoint objective is the unchanged piecewise-trilinear Fermat action. The C++ helper exposes the existing segment/path evaluator and positive weighted-Laplacian metric. Exact interval arithmetic independently checks the prescribed small actions and directional derivatives. The trilinear primitive uses series degree eight (nine retained powers), one subdivision and 128 bound bits. A separate split-affine log oracle uses cancellation-free exact-rational atanh series: `J` retains powers n=0 through 16 and `U-V` retains m=1 through 16, with explicit tails and a 192-bit length enclosure.

## Bounded contact and release

The fast-interface fixture uses `v = 6 - |x|` on x planes `[-1, 0, 1]`, with the other box axes spanning y `[-1, 4]` and z `[-1, 1]`. Its endpoints are `(delta, 0, 0)` and `(delta, 3, 0)`, and its two internal nodes are `(delta/2, 1, 0)` and `(delta, 2, 0)`, with `delta = 1/64`. A normal-only principal-metric direction is a declared feasible search subspace, not a physical constraint or a stopping norm. The first exact vertex-plane event is followed by at most one proposal that retains the first contact normal while the adjacent node approaches the face. The isolated-contact normal remains an ordinary component and is tested by its true release direction. At the final formed face, this finite construction control retains the ordinary edge contributions and blocked-normal roster but does not compute a full coupled supporting vector or claim stationarity. That assessment is separate from contact construction and from the completed native support audit.

An event time is the exact rational ratio of a binary64 coordinate distance to its emitted binary64 direction. Exact equal event times are grouped. The trial is formed as exact rational `p + alpha*q` followed by one rounding of each coordinate to binary64; separately rounding the event time and multiplying/adding it is a different construction. Fixed endpoints are copied unchanged. Every actually rounded trial must remain feasible, have nonzero displacement, and pass the stated directional/action checks. The two contact searches and one release search each allow at most 24 declared fractions; a shortened accepted fast step that has not formed the prescribed exact contact ends that bounded experiment rather than adding a hidden continuation.

The slow-interface fixture uses `v = 6 + |x|` with its polygon initially on the face. Its zero tangent residual and zero in the convex hull of branch gradients do not certify a minimum. At this concave slowness kink, that convex-hull zero cannot supply a feasible supporting-vector bound for the true first variation. The two normal-release signs are assessed by the true directional first variation, in a fixed declared order, before any trial action is tested. An inconclusive sign or action remains inconclusive; no tolerance or derivative clipping supplies a result.

## Scope of the evaluator check

The helper retains the existing segment cut rules, including the absolute direction cutoff and exclusion of near-endpoint cut parameters. A separate compact synthetic cut roster records these cases explicitly. The completed native original-cut inventory found no omitted or spurious cuts on its two specific saved CMJ polygons; that result does not certify generic cut handling, rounded sample-cell selection, or off-face derivatives.

The maximum roster is 79 C++ helper calls, 229 combined action/component edge calls, 229 independent affine edge references, and 231 directional edge calls. Actual counts are recorded. There is one compilation; helpers expose only path, principal-metric solve, and edge modes. The control driver saves its closed result under `results/summary.json`; the controller saves its own terminal `execution.json` after child reaping. Outer driver logs must stay outside this package while open. Execution requires a separate hash-bound root prelaunch review. Source preparation consists only of file copies, syntax inspection and hashes. All inputs here are invented; no event or receiver identity is fabricated.

The single-threaded controller records each child PID before unmasking its own termination signals and restores the original signal mask in the child before exec. Control helpers inherit that owned process group. A failure preserves partial artifacts, and unresolved live writers prevent the controller from claiming stable output hashes.

After root prelaunch review, the intended command from the integration checkout is:

```sh
PYTHONDONTWRITEBYTECODE=1 /usr/libexec/platform-python3.6 data/development/internal_face_contact_controls_001/controller.py
```

The root agent will own and reap this one controller. Preparation does not authorize execution.
