# Hayward variant postprocessing checks

These checks exercise separate data, figure, configuration, and report paths.
They do not run an inversion. The fixture uses the existing two-event, two-ray
native-epoch integration case identified by the input hashes in `checks.json`.
All three method labels reuse its initial model and events. Their manufactured
histories contain one zero-update row. No physical comparison between methods
is inferred from this fixture.

The three maintained scripts and the prior resolution implementation are frozen
in `source_snapshot.tar.gz`; member hashes, input hashes, and executed CLI
commands are in `checks.json`. Tar member ownership, timestamps, and PAX metadata
are normalized. The gzip container is hashed as saved. Local temporary paths in
the commands are relative to the repository root.

The resolution calculation, all eight figure files, and the numerical/LaTeX
review completed under the explicit temporary variant directories. The new
resolution and noise matrices are exactly equal to those from the prior
implementation on the same model, Jacobian, smoothing, and damping. Native
fixture inputs remained byte-identical. A second fixture removes the newly
introduced initializer and perturbation fields; its analyzer reports those
fields as unavailable, with the same residual statistics. Syntax, CLI help,
and `git diff --check` passed.

The fixture construction is specified in `fixture.json`: every copied file,
manufactured history field, observation residual, and legacy field-removal rule
is recorded. The archived prior resolution script was executed with its `ROOT`
set to the repository root and `DATA` set to the legacy fixture. Its unchanged
hardcoded configuration and the new explicit fixture configuration both use
smoothing 10 and damping 0.1. No source/model calculation was altered. The local
figures were used for directory/format checks; no new scientific visual claim
is made by this test.

For an actual separate run, specify every output directory explicitly:

```sh
python3 resolution_hayward.py --data-dir data/hayward_first_arrival --config configs/hayward_first_arrival.cfg
python3 plot_hayward.py --data-dir data/hayward_first_arrival --figure-dir figures/hayward_first_arrival
python3 analyze.py --hayward-only --data-dir data/hayward_first_arrival --report-dir report/hayward_first_arrival
```

Without options, the existing `data/hayward`, `figures/hayward`,
`configs/hayward.cfg`, and `report` defaults remain in effect. No raw provider
request, production inversion, baseline output, or baseline script changed in
this check.
