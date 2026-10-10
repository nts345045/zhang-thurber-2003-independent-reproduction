# Two rejected full-size tangent trials

Both second diagnostic trials were rejected. The retained geometry is the
first accepted trial in `hayward_cmj_tangent_step_001`; the rejected paths are
preserved here. The complete nominal and actual rounded displacement slopes
are negative, but each alpha-one trial gives a strictly positive action change.
This is a resolved finite-step increase, not an interval-sign ambiguity.

| Native event | Nominal slope (s) | Trial minus retained action (s) | Bound width (s) | Maximum node move (m) |
|---|---:|---:|---:|---:|
| 981 | -3.7906052057e-10 | +3.0212363580e-10 | 5.9915e-32 | 0.0910676 |
| 987 | -5.5922279434e-10 | +2.7019930635e-10 | 5.9047e-32 | 0.0498256 |

The fixed conservative Armijo test uses the same coefficient, exact slope
contraction, actual rounded displacement, degree-eight action enclosure,
one subdivision and 128-bit arithmetic as the first trial. No acceptance
threshold or arithmetic budget changed. Both alpha-one candidates are feasible
under the geometric bound. Negative first variation describes sufficiently
small displacements; it does not guarantee decrease at dimensionless step one.
A separately bounded shorter trial along the same direction is warranted.
No shorter step ran in this package.

The run completed from 12:45:21.471844 to 12:47:53.095765 UTC. Root reaped session
33309 with code zero, and all four helper calls were reaped. There were two
metric solves, two rounded trials and 2,058 new edge-action evaluations.
No gradient evaluation, trace, field, optimizer loop or source/model derivative
was performed. Original convergence flags remain false and candidate
convergence remains null. The post-first-step gradient remains the current
accepted-path evidence; no gradient of these rejected paths is used.

Independent saved-output review checked 169203 assertions in 117 categories,
including complete first-trial action-cache reconstruction, raw gradient
joins, both DD endpoints, dyadic directions/rounding, full slopes, exact action
sums, rejection classification and terminal hashes. It did not reintegrate
the primitive action. Review SHA-256: `f59286eaa252f06235d826c3572adbd3e0a35820697b99322b1b57283516a8fe`.

## Native identities

Both cases use station 160, `NC.CMJ..EHZ`, `FDSN:NC_CMJ__E_H_Z`, station
`NC.CMJ` / `FDSN:NC_CMJ`, valid empty location, and the authoritative channel
epoch 1996-11-12T23:45:00 through 1998-06-09T19:30:00.

- Native 981: event `quakeml:NC.anss.org/Event/NC/518943`,
  origin `quakeml:NC.anss.org/Origin/NC/4251144`,
  pick `quakeml:NC.anss.org/Arrival/NC/49639104`,
  association `quakeml:NC.anss.org/AssocArO/NC/49639104`.
- Native 987: event `quakeml:NC.anss.org/Event/NC/519264`,
  origin `quakeml:NC.anss.org/Origin/NC/4252064`,
  pick `quakeml:NC.anss.org/Arrival/NC/49654119`,
  association `quakeml:NC.anss.org/AssocArO/NC/49654119`.

All nine catalog row/side uses per case, both differential endpoints, epochs,
raw provider source hashes and original failed statuses are attached in
`native_contexts.json`, every result, and numeric-file identifier sidecars.
The frozen `README.md` describes preparation; terminal results are recorded here.
