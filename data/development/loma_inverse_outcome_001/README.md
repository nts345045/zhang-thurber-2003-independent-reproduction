# Authoritative LOM/LON recovery outcome

**Both profiles: inverse not started: initial forward validation failed.**
The completed attempts are initial-model forward/matrix preflights. They made
**zero inverse updates** and did not solve the inverse system. No recovered
velocity model or relocated-source output exists for these corrected
authoritative-geometry experiments. This is a failure to start the inverse
calculation, not a failed nonlinear inverse iteration.

| Retained initial-ray check | LOM | LON |
|---|---:|---:|
| Required rays | 37,648 | 37,648 |
| Valid independent references | 37,648 | 37,648 |
| Travel-time failures, limit 25 microseconds | 0 | 0 |
| Source-vector failures, limit 3e-6 s/km | 48 | 50 |
| Original local-stopping failures | 1 | 0 |
| Distinct rays failing any comparison criterion | 49 | 50 |
| Rays passing all comparison criteria | 37,599 | 37,598 |
| Inverse updates | 0 | 0 |

The LOM local failure is comparison row 3426, event 65, receiver 46,
Event NC10090782 / Origin 2642854, NC.JSJ..EHZ, epoch
1989-05-02T15:00:00 to 1990-09-14T21:50:00. Its time and source-vector checks
pass. The 48 separate LOM derivative failures are bottom-source rays. LON's
50 derivative failures comprise 13 bottom-source and 37 interior-source rays.
Thus the bottom-source explanation does not cover every failed ray.

[LOM failed rows](failures/lom.csv) and [LON failed rows](failures/lon.csv)
preserve **all 152 original columns and field values** for the failed rows of the
completed comparisons. Their [LOM](failures/lom.csv.identifiers.json) and
[LON](failures/lon.csv.identifiers.json) identity sidecars give the source-table
hashes, original row indices/reasons, full native joins, and simulation context.
Blank location codes, event/origin resources,
SEED/FDSN identifiers, distinct station/channel epochs, source-document fields,
original provider coordinates, current perturbed coordinates, and simulated
origin corrections remain intact. CSV serialization is regenerated; numeric
strings are not reformatted and no error is recomputed.

Both simulations contain 724 sources, 52 receivers and 15,932,384 synthetic
observations. Provider identifiers identify their geometry, not newly observed
picks. The shared perturbed locations/origin corrections and observations are
retained; the LOM and LON starting velocity fields differ. The exact published
profile sampling, Gaussian source perturbations and finite-box clamping,
simulated origin-time definition, timing/noise rules, and seed assumptions are
recorded in `outcomes.json` and the sidecars. These are explicit simulation
assumptions, not reconstructed manuscript inputs.

The first unsatisfied gate is step 3 of the existing
[inverse plan](../loma_inverse_plan_001/README.md): initial forward/source-Jacobian
validation. The simulations, independent references, complete matrix censuses,
and prescribed sampled refinement checks finished. The retained stage-0
configurations use `matrix_preflight_only=1`; an `iterations=1` setting therefore
does not mean one inverse update. `preflight/lom_checks.json` and
`preflight/lon_checks.json` are exact copies of the closed scientific checks.
Their historical "awaiting separate full initial-z comparison" fields predate
the completed external comparisons and do not override this outcome.

The [LOM full comparison](../loma_lom_initial_accuracy_001/README.md) and
[LON full comparison](../loma_lon_initial_accuracy_001/README.md), including
their saved readbacks, remain the identified numerical evidence. The six later
[endpoint-mesh calculations](../lom24104_endpoint_mesh_results_001/RESULTS.md)
improve one identified bottom-source study: three final polygons pass their
interval full-witness/time/source checks, while three remain capped. They do
not replace the complete initial Jacobian for either inverse problem.

No tolerance, stopping rule, kernel, observation cohort or model constraint
changes in this closure. It adds no universal global-first-arrival proof
requirement and does not impose the later strict 1e-7 diagnostic on every
original preflight ray. The recorded source-vector failures already violate
the retained initial acceptance criteria.

`outcomes.json` records the two dispositions and explicitly null recovery
outputs. `manifest.json` pins this small scientific package and the consumed
closed evidence. Validation copied saved fields, checked all failed-row/native
joins and existing input hashes, and checked documentation links. It neither
rehashed the multi-gigabyte observation tables nor called a forward evaluator,
reference calculation, matrix solve, optimizer or simulation. Runtime/process
records remain outside this package.

The two published simulation READMEs now link to this outcome. Only their two
documentation entries in the LON overlay manifest are refreshed; its numerical
members and archives are unchanged. The exact prior manifest is preserved in
`historical/lon_manifest_before_status_links.json`, and `outcomes.json` records
both original and updated documentation hashes. Its consumed-manifest hash
identifies that preserved version, not the updated public manifest.
