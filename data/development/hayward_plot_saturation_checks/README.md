# Fixed-scale Hayward color saturation checks

The Figure 10 velocity limits remain 3.5–7 km/s and the difference limits remain
−0.8–0.8 km/s. Figure 11 retains resolution limits 0–1 and its existing shared
noise scale. Both maintained plotting scripts now derive colorbar extensions
from every plotted array sharing that scale. They save actual extrema, sampled
point counts, and below/above-limit counts for each section and the shared scale
in `figure_metrics.json`. These counts describe sampled interpolation points,
not model nodes or independent observations.

`checks.json` records the original standard/DD interpolation results, input and
script hashes, and fixture verification. Of 83,895 plotted points per method,
20 standard velocities are below 3.5 km/s. The DD-minus-standard extrema are
−1.162139 and 1.375436 km/s, with 1,136 points below −0.8 and 1,265 above 0.8.
The shared velocity colorbar therefore has a lower extension and the difference
colorbar has both extensions. No model or numerical solver result was changed.

The complete eight-figure postprocessing fixture was rerun successfully in the
integration worktree. Exported ranges and counts were independently reconstructed
from its saved section CSVs. The helper rejected empty/nonfinite arrays and
handled all four extension states, including values exactly on a limit. Figure
10 and Figure 11 fixture images and a separate display of the saved real-model
sections were visually inspected. Images remain local test artifacts.

The frozen archive contains both plotting scripts, the exact check script, and
the existing fixture construction record. Tar and gzip metadata are normalized.
The earlier directory-routing fixture is retained unchanged in the integration
branch at `data/development/hayward_variant_checks/` (published in commit
`1456169`). The check script was run from that worktree, with its temporary
fixture already generated; the commands are recorded in `checks.json`.

The complete original field workflow and its final resolution output remain
pending. This display check does not establish inversion convergence, model
accuracy, or any original-publication figure match.
