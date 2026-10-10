#!/usr/bin/env python3
"""Plot saved independent diagnostic paths and retained analytic errors."""
import csv
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ["MPLCONFIGDIR"] = str(ROOT / "tmp/matplotlib")
os.environ["XDG_CACHE_HOME"] = str(ROOT / "tmp/cache")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

base = ROOT / "data/development/fmm_initialization_audit"
refined = ROOT / "data/development/fmm_initialization_refinement"
out = ROOT / "figures/diagnostics"
out.mkdir(parents=True, exist_ok=True)
def read(path):
    with path.open() as f:
        return list(csv.DictReader(f))

fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2), constrained_layout=True)
paths = read(base / "paths.csv")
for name, label, style in (("direct_bent", "Original stationary ray", "--"),
                           ("fmm_raw", "FMM candidate", ":"),
                           ("fmm_bent", "Candidate after bending", "-")):
    rows = [r for r in paths if r["case"] == "constant_top_gradient" and
            float(r["distance_km"]) == 40 and r["path"] == name]
    axes[0].plot([float(r["x"]) for r in rows], [float(r["z"]) for r in rows],
                 style, label=label, linewidth=1.8)
axes[0].axhline(0, color="0.7", linewidth=.7)
axes[0].set(xlabel="Horizontal coordinate (km)", ylabel="Depth (km)",
            title="40 km offset: a faster admissible path", ylim=(9, -1))
axes[0].legend(fontsize=8, loc="upper center", bbox_to_anchor=(.5,.86))
for folder, aux, spacing, label, marker in (
        (base, .25, .25, "Auxiliary/path spacing 0.25 km", "o"),
        (refined, .0625, .0625, "Auxiliary/path spacing 0.0625 km", "s")):
    rows = [r for r in read(folder / "results.csv") if r["case"] == "constant_top_gradient"
            and float(r["auxiliary_spacing_km"]) == aux
            and float(r["path_spacing_km"]) == spacing
            and 14 <= float(r["distance_km"]) <= 20]
    axes[1].plot([float(r["distance_km"]) for r in rows],
                 [1000 * float(r["time_error_s"]) for r in rows],
                 marker + "-", label=label, linewidth=1.3, markersize=4)
axes[1].axvline(14.660446216205, color="0.5", linestyle=":", linewidth=1,
                label="Analytic branch crossover")
axes[1].axhline(.025, color="0.5", linestyle="--", linewidth=1,
                label="Retained analytic time tolerance")
axes[1].set_yscale("symlog", linthresh=.001)
axes[1].set(xlabel="Source–receiver separation (km)",
            ylabel="Selected time minus analytic first arrival (ms)",
            title="Near the crossover: misses remain", xlim=(13.8, 20.3), ylim=(-.00015,30))
axes[1].legend(fontsize=7, loc="upper right")
for ax in axes:
    ax.grid(alpha=.18)
fig.suptitle("Independent constant-layer / velocity-gradient validation; no real observations", fontsize=10)
for suffix in ("pdf", "png"):
    fig.savefig(str(out / ("first_arrival_audit." + suffix)), dpi=180)
plt.close(fig)
inputs = [base / "paths.csv", base / "results.csv", refined / "results.csv", Path(__file__).resolve()]
manifest = {
    "command": "python3 diagnostics/plot_first_arrival_audit.py",
    "purpose": "Independent forward-solver diagnostic; not a reproduced manuscript panel",
    "coordinates": "Isotropic v=4 km/s above z=0; v=4+0.2*z below; depth positive downward",
    "right_axis": "Symmetric logarithmic time error with linear interval within +/-0.001 ms; no clipping",
    "sha256": {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},
}
(out / "first_arrival_audit_manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
