# Closed standard and fixed-model comparison displays

`plot_hayward_comparison.py` is a saved-output reader and renderer for one
`standard` or `loc1d` attempt. The source passed inspection and syntax parsing, then one
[real interrupted-attempt readback](RESULTS.md). It does not build or run the solver,
trace rays, calculate covariance, or change a numerical acceptance criterion.
Successful-state rendering remains unexecuted until an eligible attempt closes.

The script requires the actual `comparison_outcome.json`, the matching mode,
stable output hashes and the existing recorded child-reaping facts. It reads
only closed saved files. It leaves the runner, its shared helpers, the original
DD renderer and all native inputs/results unchanged. The script imports the
two existing helpers and checks their exact source hashes before readback.
The consumed outcome must also bind the exact reviewed comparison manifest,
entrypoint, shared helper and numerical source mapping. Recorded compiled-source
and prepared-input inventories, when present, must match the reviewed source,
original eight catalog files and `run.cfg`; prepared files must also match the
closed-output map. Complete compiled-source and prepared-input joins are
required before any saved geometry is admitted.
These are direct recorded-hash joins, followed by the existing closed-output
hash checks; no provider files or large observation archives are rescanned.
An early preparation failure can produce a status-only report with unavailable
geometry and null unrecorded source/configuration fields. It is not labeled as
a compiled or scientifically validated comparison. A conflicting recorded hash
is refused.

The copied `accepted_states()` and `geometry()` retain the DD renderer's
complete event/origin/pick/association, receiver SEED/FDSN and both-epoch joins.
Their only mode names are the explicitly requested `standard` or `loc1d`;
files are never renamed or relabeled as DD. Accepted snapshots must join to a
complete history row and a terminal accepted trial, with matching step and
fixed-weight objective values. All event metadata, finite coordinates, physical
box bounds, fixed grid nodes and positive velocities are checked. Fixed-model
relocation additionally requires every accepted velocity to equal its initial
value. Incomplete history tails and unjoined snapshots remain unpromoted.

If an accepted state is verified, the two panels show its velocity change at
the existing 8 km grid depth and source displacement from the initial state.
An unchanged fixed model is labeled with zero change, without an artificial
nonzero color scale. Full event and receiver tables and identity sidecars stay
beside the plots; source-table links retain the complete observation identities.
There is no waveform panel. A closed interruption with no accepted update
produces a candid status report and no recovery plot. Missing or invalid saved
inputs likewise produce no recovery plot. A successful renderer exit means
the disposition was recorded; check `saved_output_validation` separately.
Both panels use common x/y limits enclosing the full saved grid and every
initial and accepted source, with a two-percent margin. Equal coordinate scale
and 1:1 displacement arrows are retained; no fixed window clips admitted points.

From the repository root, after actual closure, use a suitable plotting Python
and an absent immediate child of `tmp/`:

```sh
python3 -B plot_hayward_comparison.py --mode standard \
  --data data/hayward_standard_guarded_001 --output tmp/FRESH_standard_saved_outcome
python3 -B plot_hayward_comparison.py --mode loc1d \
  --data data/hayward_loc1d_guarded_001 --output tmp/FRESH_loc1d_saved_outcome
```

The first command has been executed once against the closed interrupted
attempt; it does not rerun that inversion. Substitute the separately identified `standard_002`
output only after its own closure. The second command must wait for its actual
closed receipt. The fixed-model command and accepted-state plotting remain unexecuted.

Outputs are `render_summary.json` and `report.tex`, plus
`comparison_figure.pdf`/`.png`, `event_points.csv`, `model_nodes.csv`,
`receiver_epochs.csv` and their sidecars only when a state is verified.
The script does not invoke LaTeX; the existing project-local two-pass report
assembly instructions can compile this short TeX file separately. Matplotlib
is imported only for an accepted-state plot. The status-only path uses the
standard library and existing helper utilities.

`source_mapping.json` binds the new script, reused source bytes and exact
function diffs. This reader does not call the old full-completion checker:
that checker excludes standard mode and assumes successful terminal artifacts.
No new ray or finite-difference products are required merely to preserve an
honest partial or failed outcome. History diagnostics remain pre-update;
accepted objective decrease, process completion and numerical convergence are
distinct. The one-reproduced/61-partial manuscript audit is not promoted.
