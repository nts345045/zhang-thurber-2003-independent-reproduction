# Independent continuous-curve integral controls

Source-only definitions in check_curved_integrals.cpp; no compilation or
evaluation was performed while authoring this note. The executable uses
layered_curved_ray.hpp directly, without affine_arrival.hpp, reference
enumerators, optimizers, or real-data inputs.

The six groups contain 24 assertions:

1. A homogeneous oblique line crosses five distinct internal x/y/z planes.
   Every nodal length and velocity derivative is compared with an independently
   integrated cubic trilinear basis in the original line parameter. Time and
   arclength use analytic straight-line answers. The internal z plane is 1.75,
   making cut parameters 1/4, 1/3, 1/2, 2/3, 3/4. An initial unexecuted draft
   used 1.5, creating an unintended x/z tie; only that manufactured plane was
   changed. Inseparable rounded face roots remain an explicit kernel
   representability limitation.
2. Two radius-2 circular arcs meet a positive horizontal guide at the true
   bottom z=2 in v(z)=z. All eight nodal integrals use separate elementary
   endpoint antiderivatives, alongside analytic time and length. The ascending
   source depth is manufactured from the desired stored guide depth; no kernel
   endpoint is replaced or clamped. The working circle-center discrepancy is
   reported explicitly.
3. Reverse the line and reflect the symmetric arc/guide construction. Compare
   action and every nodal kernel in the original global node ordering. The
   reflected curve retains exact stored piece joins; reversal symmetry of its
   trigonometric construction is subject to the declared working tolerance.
4. Display spacing 1 versus 1/32 changes the exported point count. Reintegrating
   the unchanged curve must reproduce every result, status, and work field
   exactly.
5. Changing one lateral grid value by one binary64 ULP must reject the global
   depth-only predicate, with its exact diagnostic, before sample integration.
6. Supplied tied/incomplete/nonunique status remains unchanged. Selected-curve
   integrals must match the identical geometry carrying ordinary metadata;
   these values do not certify unique envelope derivatives.

For each affine arc, write a nodal basis as
N=(A+B cos(theta))(C+D sin(theta))/2. Length uses the antiderivatives of 1,
cos(theta), sin(theta), and sin(theta)cos(theta). Since ds=R dtheta and
v=R sin(theta), the velocity derivative uses -1/(2R) times the same coefficient
combination with antiderivatives of csc²(theta), cos(theta)/sin²(theta),
csc(theta), and cot(theta). The guide contribution is a linear-polynomial
endpoint average evaluated in working arithmetic. No reference quadrature
duplicates the kernel.

All observed and reference scalars are hexadecimal long doubles. Each analytic
comparison reports its error and a declared regression allowance
4096*epsilon*max(1, absolute reference accumulation + length + absolute time).
Reversal uses 4096*epsilon*max(1,length). These finite fixture tolerances include
working endpoint/trigonometric rounding; they are not proved error bounds.
The kernel's 8/16-point differences and face-coordinate residual are also saved
without promotion to interval evidence.

The executable takes one absolute, absent summary filename. Existing files and
dangling symlinks are refused. Standard output contains flushed JSONL supplied
grids/curves, full result vectors, reference vectors/errors, and numbered
assertions. A failure preserves preceding output and returns 1. A successful
summary declares six groups, 24 checks, seven integration attempts (six
completed and one rejected before samples), 27 subpieces, 648 quadrature
samples, two display calls, and zero branch-enumerator/optimizer/real-data calls.
The parent owns any authorized compiler and executable invocation and their
actual lifecycle receipts.

Source pins at this handoff:

- check_curved_integrals.cpp:
  f7aefd8f975cd954b2895324a8be8f9b9d47d1e73bbf4bc1e02dc750cb2e0d22
- layered_curved_ray.hpp:
  ede8a8375b4dbba78acf66c32fe79f4135519a647fc17e7a9890d914337dea33
