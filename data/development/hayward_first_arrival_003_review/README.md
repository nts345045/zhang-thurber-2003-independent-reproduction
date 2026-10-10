# Terminal Hayward preflight 003 review

The corrected initial preflight finished both numerical commands with return code 0, then its unchanged validator recorded `failed_checks_preserved` and driver return code 1. No corrected inversion was launched. The 14,262 full-support ray initializations succeeded; 139 rays failed local stopping. In contrast, all 32 sampled production/refined paths and all 24 source finite-difference perturbation pairs passed their local and initializer flags. This is a direct limitation of the sparse validation sample.

The sampled maximum travel-time refinement difference is 8.93255e-5 s and maximum production source-component difference from the refined finite difference is 5.62588e-5 s/km. These differences do not certify first-arrival accuracy or the unsampled rays.

The failed rays span 128 event IDs, 80 native channel epochs and 28 SEED channel names. Of these, 121 reach 1,000 updates and 18 stop earlier. Their maximum projected gradient is 0.00279900 s/km. None of their source or receiver endpoints lies on an outer grid face, including a 1e-8 km proximity check. The saved tables do not establish whether interior path knots contact outer bounds or grid interfaces. Causes and continuous-reference errors require the separate numerical investigations.

`failed_rays.csv` retains each original linearization row, all native observation IDs and complete source/receiver metadata. The three grouped CSVs keep event/origin identities or SEED/FDSN channel identities and native epochs. `review.json` records checks and hashes. All 560,220 sparse entries are finite and lie in the mapped source/model blocks; every absolute row has a unit origin-time derivative. The absolute log-slowness kernel sums agree with saved travel times within 5.01e-11 s, an implementation/serialization identity rather than a ray accuracy test.

`preflight_execution.json`, `preflight.json`, `run_manifest.json`, `run.cfg` and `source_snapshot.tar.gz` are exact copies from the terminal run. `terminal_tables.tar.gz` contains all nine table files listed in the final preflight hash map, including the complete 14,262-row table, parameter map, sparse matrix and diagnostic identity joins. Every member hash was independently checked. The authoritative observations/stations and other preparation inputs are identified by the original run hashes; they were not modified or reselected.

Reproduce the review with a fresh output directory:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/review_hayward_preflight.py --data data/hayward_first_arrival_003 --output data/development/hayward_first_arrival_003_review_repeat
```

The archive records this failed preflight; subsequent independent reference or refinement experiments do not replace its outcomes.
