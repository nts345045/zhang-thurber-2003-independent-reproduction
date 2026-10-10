# Old-kernel launcher controls

Preparation only; no controls have run. The proposed harness checks the frozen
launcher and completion helper without compiling or executing a ray, field, or
inverse calculation. Its only new child commands are invented Python process
stubs supervised by the launcher's actual process-control function.

The source checks compare configuration, the common eligibility prefix and
counts, and the completion function by AST with the reviewed predecessor.
The completion helper must match the reviewed file byte for byte. The source
bridge is read from the reviewed 004, guarded, and main-only backtracking
evidence. Missing, changed, or symlink source/review cases modify only a copied
candidate directory. Separate argument mutations check the main/kernel/compiler
links. Compiler-cache cases cover STRING, FILEPATH, missing, empty, malformed,
and duplicate keys.

The eligibility fixture reuses the saved invented preflight and reference
tables from the earlier launcher checks. Only paths and their hash bindings
change. It preserves their initializer/accuracy contract and checks running,
failed, stale, changed-input, and unassessed-review rejection. No fresh numerical
tables are generated or simulated.

The lifecycle cases extract the exact nested `run`, interrupt handler, exception
handler, and output-hash expression from the frozen launcher AST. They omit its
build/inverse main body. Cases include zero and nonzero exit; zero and nonzero
supervisor exit with a live writer descendant; and two SIGTERM signals while a
writer ignores TERM. Every descendant must be gone before saved hashes are
verified. The harness owns fallback cleanup if a tested case fails. Controller
stdout/stderr stay outside the child directory so the child never hashes its
own still-open driver streams.

There is no complete positive controller-final fixture with the required
first-arrival initializer metadata. Existing completion-helper controls and
unchanged `check_inverse` AST preserve that requirement; these isolated process
tests do not fill the gap or establish scientific success.

After independent source review, the bounded command is:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 diagnostics/check_old_kernel_backtracking_launcher.py \
  --output data/development/hayward_old_kernel_backtracking_launcher_checks_001
```

The harness refuses an existing summary or changed prepared source. Any failed
run is retained; source fixes require a separate result variant. No Git changes
or native launch are part of this package.
