# Invented failed-search capture controls

All 22 controls passed. This checks the recording interface, not a ray optimizer:
the program never calls `trace()`. Trial actions and decisions are deliberately
invented scalar inputs. The capture helper only reevaluates the invented base
polygon after the recorded failure.

The controls preserve binary64 coordinates, directions, signed zero and small
values through 17-digit CSV output; verify all 24 attempted steps separately
from the final halved step; and exercise invalid trials, endpoint preservation,
deep copies, buffer reset, changed vertex counts, unchanged paths, dimension
rejection and refusal to overwrite previous evidence. Internal run labels are
delimiter-free. Native provider metadata belong in the replay's identifier
sidecars and are outside these invented fixtures.

From the repository root, the executed command was:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/run_failed_search_capture_checks.py \
  --output data/development/failed_search_capture_controls_001 \
  --build tmp/failed_search_capture_controls_001
```

Use fresh output and build directories to repeat it. `summary.json` records the
compiler command, binary hash, six frozen source hashes, 17 artifact hashes and
all checks. `source/` preserves the compiled source. `review.json` records the
independent source and saved-result review.

These controls establish no numerical neutrality or failure cause for a native
replay. Those require its own observed/unobserved comparison, unchanged old
output hashes and complete native identifier joins. No production source,
stopping threshold or ray flag changed here.
