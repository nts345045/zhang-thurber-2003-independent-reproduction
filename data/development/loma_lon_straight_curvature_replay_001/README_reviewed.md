# Reviewed execution preparation

The initial `prepared.json` and `run.py` are preserved as a superseded, unexecuted preparation. Independent source review identified two runner issues: its scope wording incorrectly said no retrace, and interrupted compiler process groups needed complete termination accounting before output hashes could be called stable. No compiler or native call ran under that preparation.

`run_reviewed.py` makes only those lifecycle/wording corrections and reads `prepared_v2.json`. It waits for non-zombie group members after ordinary command completion, catches a disappearing group during termination, reaps the direct child, and preserves unresolved termination without claiming stable output hashes. The driver, numerical source, settings, native input tables and parity gate are unchanged. `prepare_revision.py` rechecks every original prepared file before exclusively writing the new preparation manifest.

The approved execution command, from this directory, is:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 run_reviewed.py
```

It requires a passed `prelaunch_review.json` bound to `prepared_v2.json`. The original README describes the numerical plan; its older run command is superseded by this one.
