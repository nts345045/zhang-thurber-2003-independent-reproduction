# Authoritative Hayward inputs and results

The original baseline workflow completed with exit code 0 after 33,712 seconds.
All three methods have written the numerical files below, final sampled ray
checks, conditional resolution, and Figures 4–11. Each retains all 1,092 event
identities and 58,980 observations: 14,262 absolute picks and 44,718 catalog
differences. These outputs preserve the original straight-initialized solver;
the separate guarded attempt is in `../hayward_first_arrival_guarded_001/` in
the integration worktree. Process completion does not establish convergence.

| Method | Accepted updates | Final absolute RMS (s) | Final catalog-DD RMS (s) |
| --- | ---: | ---: | ---: |
| `standard`: absolute-data tomography | 12 | 0.07869 | 0.07162 |
| `dd`: catalog-DD tomography | 18 | 0.16064 | 0.06160 |
| `loc1d`: fixed-velocity catalog-DD relocation | 10 | 0.29188 | 0.25423 |

Standard tomography stopped at iteration 12 after 12 accepted updates because
its next line search accepted no step. Its final absolute and catalog-difference
RMS residuals are 0.07869 and 0.07162 s. The last pre-update ray calculation
met the stopping rule for 13,690 of 14,262 rays; 572 failed. This termination
does not establish nonlinear convergence. Neither does the DD residual
decrease: its final accepted maximum source-coordinate change is 2.7614 km.
Fixed-velocity relocation uses staged catalog-DD weights with absolute
anchoring. Its catalog-DD RMS worsens from the initial 0.09340 s to 0.25423 s;
three attempted updates accept no step. The final deterministic 32-ray samples
have 31 passing flags for `standard` and 32 for `dd` and `loc1d`, at each spacing.
Passing that sample does not validate every ray: two of 14,262 rays fail the
final DD linearization, and 277 fail the last pre-update `loc1d` trace.
The [completed independent audit](../development/hayward_completed_baseline_review_001/README.md)
checks native identities, finite values, domain membership, termination,
geographic/zoom joins, resolution interpolation, and original run hashes.
`numerical_review.json` retains the workflow's detailed numerical diagnostics.
The earlier [standard](../development/hayward_standard_output_review.json) and
[DD](../development/hayward_final_output_review.json) reviews remain preserved.

`selection_manifest.json` defines the independently selected cohort and records
input hashes, station policy, differences from the manuscript, and graph
connectivity. `initial_events.csv`, `stations.csv`, `initial_grid.csv`, and
`observations.csv` are the solver inputs. Event, station, and observation tables
preserve provider resource IDs, SEED channel names, native epochs, and source
provenance; the grid table contains model coordinates and velocities. For a differential
observation, `station` and `station_j` index the two native receiver records;
the records share an NSLC and exact position, but may have different epochs.

`event_pairs.csv` lists links with both event/origin identities.
`event_selection.csv` records selection, pair degree, and component size.
`excluded_picks.csv` preserves omitted picks and reasons: `selected` refers to
the initial archive selection, whereas `solver_selected=0` denotes exclusion
from this solver dataset. Original records remain in `../authoritative/`.

Inversion commands write these files for each method (`standard`, `dd`, `loc1d`):

| File pattern | Quantity |
| --- | --- |
| `METHOD_grid.csv` | P velocity in km/s at model nodes; fixed input velocities for `loc1d` |
| `METHOD_events.csv` | Source coordinates in km and origin-time corrections in s |
| `METHOD_history.csv` | Residuals, accepted steps, linear solves, and ray convergence by iteration |
| `METHOD_residuals.csv` | Observation residuals in seconds, retaining identities |
| `METHOD_coverage.csv` | Summed observed-ray path lengths at model nodes |

The separate `dd raycheck CONFIG DIR METHOD` command writes:

| File pattern | Quantity |
| --- | --- |
| `METHOD_ray_convergence.csv` | Sampled production/refined travel-time and convergence comparison |
| `METHOD_ray_derivatives.csv` | Sampled source-derivative consistency checks |
| `METHOD_ray_identifiers.csv` | Mapping from each diagnostic row to observations and native metadata |

Files prefixed `initial_` describe input geometry or forward checks, not an
inferred model. A process exit status does not by itself establish ray or
inverse-problem convergence; inspect the numerical diagnostic columns.

`figure04_geometry_manifest.json` records the independently generated geometry
panel's inputs. Figures are written to `../../figures/hayward/`. The full plot
command writes `METHOD_geographic_events.csv` with estimated latitude, longitude,
and origin times, `METHOD_zoom_events.csv` with the common catalog-selected
subset, and `figure_metrics.json`. Resolution outputs come from `dd linearize`
and `resolution_hayward.py`: inspect `dd_linearization_{rows,columns,matrix}.csv`,
`absolute_resolution.csv`, `absolute_resolution_manifest.json`,
`absolute_resolution_matrices.npz`, and `resolution_sections.csv` together.
This is an absolute-pick linear calculation at the DD model, with independent
one-sigma pick noise assumed, unconstrained source elimination, and fixed
regularization. It is not full-DD resolution and excludes ray error, model
error, bias, and active source bounds. The synthetic baseline outputs are in
`../synthetic/` and predate the later ray-kernel corrections.

The additional-data station selection writes a separate
`../hayward_additional/` directory if requested. No original record is removed
when a reproduction selection excludes an observation.
