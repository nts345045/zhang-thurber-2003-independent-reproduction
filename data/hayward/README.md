# Authoritative Hayward inputs and results

At this partial checkpoint the DD inversion has written all five numerical
output files below, with all 1,092 event identities and 58,980 observation
mappings verified. Absolute-data tomography and fixed-model relocation remain
active. Their incomplete histories do not constitute finished results; final
ray checks, resolution, comparison figures, and the full workflow completion
record are pending. The DD residual decrease does not establish nonlinear
convergence: its final accepted maximum source-coordinate change is 2.7614 km.
The separate [output review](../development/hayward_final_output_review.json)
records checks and limitations without marking the entire workflow complete.

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
panel's inputs. Figures are written to `../../figures/hayward/`. When completed,
the full plot command also writes `METHOD_geographic_events.csv` with estimated
latitude, longitude, and origin times, and `figure_metrics.json`; resolution outputs
come from `dd linearize` and `resolution_hayward.py`. Missing method files mean
that result has not been produced. The synthetic baseline outputs are in
`../synthetic/` and predate the later ray-kernel corrections.

The additional-data station selection writes a separate
`../hayward_additional/` directory if requested. No original record is removed
when a reproduction selection excludes an observation.
