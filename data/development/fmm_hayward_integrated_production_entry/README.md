# Identified production-entry comparison

```sh
PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/run_fmm_hayward_audit.py --variant NEW_VARIANT --order 2 --closed-seed-cells --allow-solver-change --production-entry
```

The frozen 186-ray cohort and DD-final model are unchanged. Each identified
result row compares `trace_first_arrival` exactly against the current diagnostic
control for time, path, source and nodal velocity derivatives, integrated
lengths, optimizer state, and initializer metadata. All 186 comparisons pass;
the saved selected quantities come from the production entry. The source archive
contains every compilation dependency and the summary records solver changes
relative to the earlier historical audit.

One selected ray, i775/k184 at NC.CMO..EHZ, remains nonconverged under the
unchanged 1000-update budget and local stopping conditions. Its complete
provider IDs and native epoch are retained in the result and summary. There
are no extraction, endpoint, domain, nonfinite, action-increase or parity
failures. The runner intentionally exits 1 because that local failure remains.

Exact parity checks integration consistency. Independent analytic tests provide
separate accuracy evidence; neither establishes globally earliest arrivals in
an arbitrary field. No inversion was rerun and the original active workflow
remains untouched.
