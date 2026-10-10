# Refining the path while retaining the coarse initialization field

This isolated test retains the 0.5 km FMM field for the same identified initial
Hayward observation 9291 and reduces only the initial path spacing to 0.125
and 0.0625 km. Event `quakeml:NC.anss.org/Event/NC/390228`, channel
`NC.CCY..EHZ`, full native resource IDs and epochs are in `identified_ray.csv`.
Every derived path/history row joins this sidecar through `observation_index`.
The original failed calculation and all input files remain unchanged.

All four observed traces match the frozen uninstrumented core exactly and
meet its unchanged combined stopping criterion. Direct and FMM starts are
retained separately. The earlier continuous 1D enumeration supplies the
independent first-arrival time 3.6454799943574034 s and source derivatives.

| Path spacing (km) | Start | Accepted updates | Time error (microseconds) | Maximum source-component error (s/km) |
| --- | --- | --- | --- | --- |
| 0.125 | Straight | 65 | 16.1078 | 3.29718e-6 |
| 0.125 | FMM | 20 | 13.0745 | 2.10691e-6 |
| 0.0625 | Straight | 25 | 4.18938 | 8.13085e-7 |
| 0.0625 | FMM | 19 | 3.26671 | 5.93061e-7 |

The minimum-action FMM result at each spacing meets the previously established
analytic-control limits of 25 microseconds and 3e-6 s/km. The 0.125 km
straight-started result exceeds the source-derivative limit despite local
convergence. This is evidence about one path, not a guarantee for the full
cohort or a replacement full-cohort preflight.

`summary.json` contains the commands, child exits, frozen sources and hashes,
and all four results. There is no 0.5 km path calculation in this particular
experiment, so `selected_initial_ray_matches` is null; exact parity with the
original 0.5 km result was established in the preceding `audit001` experiment.
No numerical stopping rule or iteration limit was loosened.

To repeat into a fresh directory, run from the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/run_initial_ray_diagnosis.py \
  --run first_arrival_003 --observation 9291 --variant NEW_NAME \
  --spacings 0.125,0.0625 --budgets 1000 --field-spacing 0.5
```
