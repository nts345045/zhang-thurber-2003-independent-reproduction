# Superseded interpolation-gradient attempt

These scientific history and ray-diagnostic CSVs were saved before replacing
signed sums of nodal velocities with paired nodal differences in interpolation
gradients. The formulas are mathematically equivalent, but paired differences
preserve a constant coordinate direction exactly. The previous arithmetic
could introduce tiny gradients in a depth-independent medium. Ray optimization
amplified these into out-of-plane motion; column normalization then amplified
spurious surface-source depth sensitivities into extreme location increments.

The clean rebuild was deliberately terminated after this defect was confirmed.
The DD history is incomplete. None of these files is a final figure input or
an assertion of a successful rebuild. Final output is regenerated with the
corrected source and includes constant-axis and surface-ray regression checks.
