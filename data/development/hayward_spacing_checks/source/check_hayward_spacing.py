#!/usr/bin/env python3
"""Check preflight spacing declarations without launching any numerical job."""
import ast
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
source = ROOT / "run_hayward_first_arrival.py"
before = ROOT / "tmp/hayward_runs/first_arrival_003/source/run_hayward_first_arrival.py"
out = ROOT / "data/development/hayward_spacing_checks"
if out.exists(): raise ValueError("Preserve previous spacing checks")
out.mkdir(parents=True)
namespace = {"math": math}
tree = ast.parse(source.read_text())
function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "run_configuration")
exec(compile(ast.Module(body=[function]), str(source), "exec"), namespace)
configure = namespace["run_configuration"]


def settings(text):
    result = {}
    for line in text.splitlines():
        fields = line.split()
        if len(fields) >= 2 and not fields[0].startswith("#"):
            result[fields[0]] = float(fields[1])
    return result


checks = []
baseline = (ROOT / "configs/hayward.cfg").read_text()
previous = settings((ROOT / "data/hayward_first_arrival_003/run.cfg").read_text())
for name, path_spacing, field_spacing in (("unchanged_defaults", None, None),
                                         ("independent_path", .125, None),
                                         ("independent_field", None, .25),
                                         ("both_declared", .0625, .5)):
    text, declared = configure(baseline, path_spacing, field_spacing)
    expected = dict(previous)
    if path_spacing is not None: expected["ray_spacing"] = path_spacing
    if field_spacing is not None: expected["fmm_spacing"] = field_spacing
    assert settings(text) == expected
    assert declared == dict(path_spacing_km=expected["ray_spacing"], fmm_spacing_km=expected["fmm_spacing"])
    checks.append({"name": name, "passed": True})
for value in (0., -1., float("nan"), float("inf")):
    for axis in (0, 1):
        values = [None, None]; values[axis] = value
        try: configure(baseline, *values)
        except ValueError: pass
        else: raise AssertionError("Invalid spacing accepted")
        checks.append({"name": "reject_{}_{}".format(axis, value), "passed": True})
for arguments in (("--phase", "preflight", "--path-spacing", "nan"),
                  ("--phase", "preflight", "--fmm-spacing", "0"),
                  ("--phase", "invert", "--path-spacing", "0.125")):
    variant = "spacing_parser_fixture"
    assert not (ROOT / "data" / ("hayward_" + variant)).exists()
    result = subprocess.run([sys.executable, str(source), "--variant", variant] + list(arguments),
                            cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            universal_newlines=True)
    assert result.returncode == 2 and not (ROOT / "data" / ("hayward_" + variant)).exists()
    checks.append({"name": "parser_rejection_" + "_".join(arguments), "passed": True})
old, current = before.read_text(), source.read_text()
start, end = "        absolute = rows(out/", "    except BaseException as error:"
assert old[old.index(start):old.index(end)] == current[current.index(start):current.index(end)]
checks.append({"name": "complete_existing_preflight_validator_unchanged", "passed": True})
old_tree = ast.parse(old)
for name in ("start_execution", "interrupted", "record_failure", "run", "write_execution"):
    previous_node = next(n for n in old_tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    current_node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    assert ast.dump(previous_node) == ast.dump(current_node)
    checks.append({"name": "execution_guard_unchanged_" + name, "passed": True})
snapshot = out / "source"; snapshot.mkdir()
for path, name in ((source, source.name), (before, "runner_before.py"),
                   (Path(__file__), "check_hayward_spacing.py")):
    shutil.copyfile(str(path), str(snapshot / name))
result = {"passed": True, "checks": checks, "numerical_jobs_launched": 0,
          "scope": "Configuration declarations and parser/guard controls only; no accuracy or convergence claim",
          "source_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in snapshot.iterdir()}}
(out / "results.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({"passed": True, "checks": len(checks), "numerical_jobs_launched": 0}))
