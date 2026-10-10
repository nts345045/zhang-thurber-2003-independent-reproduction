# Completed fixed-path readback

The four authorized fixed-path evaluations completed with code 0. Both old and D compilations and evaluations returned 0 with empty stderr. Every raw and projected norm reproduced its recorded 17-digit value. Reevaluated path actions also equalled the recorded values exactly in binary64. No trace, field, optimizer or inverse was called.

| Event | Version | Free knots | Free knots within 1 mm of x=0 | Raw/projected norm (s/km) | Near-face x share of squared norm |
| --- | --- | ---: | ---: | ---: | ---: |
| 981 | Original | 1027 | 31 | 0.00049649035047086309 | 99.51324731646493% |
| 987 | Original | 1029 | 32 | 0.00049378622676222908 | 99.29490051662863% |
| 981 | D | 1027 | 31 | 0.00049658579025209989 | 99.44619988996208% |
| 987 | D | 1029 | 32 | 0.00055435395870530009 | 99.63837748613252% |

Raw and projected fractions coincide for these polygons. [summary.json](summary.json) preserves the exact rational squared totals and ratios of exported binary64 components; percentages here are rounded displays. Every original path field and native identifier accompanies [old node gradients](results/old/node_gradients.csv) and [D node gradients](results/D/node_gradients.csv), including blank gradient components at fixed endpoints. Separate tables retain the largest 20 components per case and norm basis. Both native events and the full CMJ channel/epoch are specified in [README.md](README.md).

The ordinary free-knot residual is concentrated in x components near the internal face. This is a localization of the recorded numerical gradient. It neither certifies an all-direction nonsmooth derivative nor proves that the face caused the failure. It does not establish a useful descent direction, first-arrival accuracy, or a solver correction. No path, source/model partial, original derivative-disabled status or false convergence flag was changed. The [execution ledger](execution.json) and [command completion receipt](command_completion.json) preserve the exact evaluation inventory and process outcome.
