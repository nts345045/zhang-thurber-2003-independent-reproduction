#!/usr/bin/env python3
"""Recheck the 1D formulas using invented geometry and the saved initial grid.

Run: python3 diagnostics/check_1d_reference.py
Requires Python 3.6+ and SciPy. This does not enumerate global first arrivals,
query observations, run production rays, or read event/station records.
"""
import csv
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import scipy
from scipy.integrate import quad

ROOT = Path(__file__).resolve().parents[1]
GRID = ROOT / "data/hayward/initial_grid.csv"
REFERENCE = ROOT / "data/development/first_arrival_1d_reference.md"
OUT = ROOT / "data/development/first_arrival_1d_checks.json"


def profile():
    with GRID.open() as f:
        rows = list(csv.DictReader(f))
    levels = {}
    for row in rows:
        z, v = float(row["z"]), float(row["v"])
        if not math.isfinite(z) or not math.isfinite(v) or v <= 0:
            raise ValueError("Invalid grid coordinate or velocity")
        if z in levels and levels[z] != v:
            raise ValueError("Grid is not horizontally uniform")
        levels[z] = v
    result = sorted(levels.items())
    if any(b[1] < a[1] for a, b in zip(result, result[1:])):
        raise ValueError("Velocity is not monotone")
    if len(result) < 4 or result[1][0] != 0 or result[0][1] != result[1][1]:
        raise ValueError("Examples require the saved flat extension ending at z=0")
    return result


def leg(h, va, vb, p, turning=False):
    """Analytic X, T, and fixed-endpoint dX/dp; the latter diverges at a turn."""
    g = (vb - va) / h
    sa = math.sqrt(1 - (p * va) ** 2)
    if not g:
        return h * p * va / sa, h / (va * sa), h * va / sa ** 3
    if p == 0:
        return 0., math.log(vb / va) / g, h * (va + vb) / 2
    sb = 0. if turning else math.sqrt(1 - (p * vb) ** 2)
    x = p * h * (va + vb) / (sa + sb)
    t = math.log(vb * (1 + sa) / (va * (1 + sb))) / g
    xp = None if turning else (1 / sb - 1 / sa) / (g * p * p)
    return x, t, xp


def quadrature(h, va, vb, p, turning=False):
    g = (vb - va) / h
    if turning:
        # z = z_turn - t^2 removes the integrable endpoint singularity.
        # These are transformed Snell integrands, not their antiderivatives.
        funcs = [lambda t: 2 * (vb - g * t * t) / math.sqrt(g * (2 * vb - g * t * t)),
                 lambda t: 2 * vb / ((vb - g * t * t) * math.sqrt(g * (2 * vb - g * t * t)))]
        end = math.sqrt(h)
    else:
        def v(z):
            return va + g * z
        funcs = [lambda z: p * v(z) / math.sqrt(1 - (p * v(z)) ** 2),
                 lambda z: 1 / (v(z) * math.sqrt(1 - (p * v(z)) ** 2)),
                 lambda z: v(z) / (1 - (p * v(z)) ** 2) ** 1.5]
        end = h
    pairs = [quad(f, 0, end, epsabs=1e-12, epsrel=1e-12) for f in funcs]
    return [a for a, b in pairs], [b for a, b in pairs]


def turning_example(source, receiver, deeper, v0, g):
    r = math.hypot(receiver[0] - source[0], receiver[1] - source[1])
    h = -source[2] - receiver[2]
    a = 2 * v0 / g
    large = (r + math.sqrt(r * r - 4 * a * h)) / (2 * a)
    w = large if deeper else h / (a * large)
    u = v0 * math.sqrt(1 + w * w)
    return {"distance_km": h / w + a * w,
            "time_s": h * math.sqrt(1 + w * w) / (v0 * w) + 2 / g * math.asinh(w),
            "turn_depth_km": (u - v0) / g, "p_s_per_km": 1 / u,
            "w_cotangent": w}


def main():
    model = profile()
    checks, examples = [], []

    def compare(name, value, independent, tolerance, units):
        error = abs(value - independent)
        checks.append(dict(name=name, formula=value, independent=independent,
                           absolute_error=error, tolerance=tolerance, units=units,
                           passed=math.isfinite(error) and error <= tolerance))

    for name, a, b, p in [("gradient", model[2], model[3], .12),
                          ("vertical", model[2], model[3], 0.),
                          ("flat", (-.75, model[0][1]), (-.25, model[0][1]), .12)]:
        values = leg(b[0] - a[0], a[1], b[1], p)
        integrated, error = quadrature(b[0] - a[0], a[1], b[1], p)
        examples.append(dict(name=name, depths_km=[a[0], b[0]], p_s_per_km=p,
                             quadrature_reported_absolute_errors=error))
        for i, (key, unit) in enumerate([( "X", "km"), ("T", "s"), ("dX_dp", "km^2/s")]):
            compare(name + "_" + key, values[i], integrated[i], 1e-10, unit)

    source, receiver = [0., 0., -.5], [12., 0., -.5]
    v0 = model[1][1]
    g = (model[2][1] - v0) / (model[2][0] - model[1][0])
    if not model[0][0] <= -.75 < 0 or g <= 0:
        raise ValueError("Invented examples lie outside the required flat/gradient layers")
    step = 1e-5
    for deeper in [False, True]:
        name = "deeper_turn" if deeper else "shallow_turn"
        result = turning_example(source, receiver, deeper, v0, g)
        if not 0 < result["turn_depth_km"] < model[2][0]:
            raise ValueError("Example turn has left the first positive-gradient layer")
        p, zt = result["p_s_per_km"], result["turn_depth_km"]
        flat, flat_error = quadrature(.5, v0, v0, p)
        curve, curve_error = quadrature(zt, v0, 1 / p, p, turning=True)
        compare(name + "_X", result["distance_km"], 2 * (flat[0] + curve[0]), 1e-10, "km")
        compare(name + "_T", result["time_s"], 2 * (flat[1] + curve[1]), 1e-10, "s")
        exact = [-p, 0., -math.sqrt(1 / v0 ** 2 - p * p)]
        for axis in range(3):
            plus, minus = list(source), list(source)
            plus[axis] += step
            minus[axis] -= step
            fd = (turning_example(plus, receiver, deeper, v0, g)["time_s"] -
                  turning_example(minus, receiver, deeper, v0, g)["time_s"]) / (2 * step)
            compare(name + "_source_derivative_" + "xyz"[axis], exact[axis], fd, 5e-9, "s/km")
        result.update(name=name, source_xyz_km=source, receiver_xyz_km=receiver,
                      source_derivative_s_per_km=exact,
                      quadrature_reported_time_error_s=2 * (flat_error[1] + curve_error[1]))
        examples.append(result)

    # Preserve the finite-bottom example without claiming global branch enumeration.
    p = 1 / model[-1][1]
    total, integrated, reported_error = [0., 0.], [0., 0.], [0., 0.]
    for start in [8., -.2]:
        for a, b in zip(model, model[1:]):
            lo, hi = max(start, a[0]), b[0]
            if hi <= lo:
                continue
            g = (b[1] - a[1]) / (b[0] - a[0])
            va = a[1] + g * (lo - a[0])
            turn = hi == model[-1][0]
            values = leg(hi - lo, va, b[1], p, turning=turn)
            numeric, errors = quadrature(hi - lo, va, b[1], p, turning=turn)
            for i in range(2):
                total[i] += values[i]
                integrated[i] += numeric[i]
                reported_error[i] += errors[i]
    compare("bottom_tangent_X", total[0], integrated[0], 1e-10, "km")
    compare("bottom_tangent_T", total[1], integrated[1], 1e-10, "s")
    if total[0] > 90:
        raise ValueError("Invented bottom example has no nonnegative boundary segment")
    examples.append(dict(name="bottom_boundary_candidate", source_depth_km=8.,
                         receiver_depth_km=-.2, horizontal_distance_km=90.,
                         p_s_per_km=p, tangent_distance_km=total[0], tangent_time_s=total[1],
                         boundary_time_s=(90 - total[0]) * p,
                         total_time_s=total[1] + (90 - total[0]) * p,
                         quadrature_reported_absolute_errors=reported_error))
    files = [GRID, REFERENCE, Path(__file__).resolve()]
    report = {
        "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "command": "python3 diagnostics/check_1d_reference.py",
        "scope": "Analytic leg and selected-branch formula checks; no global root enumeration or FMM validation",
        "geometry_status": "All endpoints and leg examples are invented numerical geometry, not station/event records; no provider identities are assigned",
        "model_input": str(GRID.relative_to(ROOT)),
        "profile_depth_velocity_km_km_s": model,
        "flat_direct_example_time_s": 12 / v0,
        "finite_difference_step_km": step,
        "quadrature": "SciPy quad, epsabs=epsrel=1e-12; square-root variable removes turning-endpoint singularity",
        "versions": {"python": sys.version.split()[0], "scipy": scipy.__version__},
        "sha256": {str(f.relative_to(ROOT)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files},
        "examples": examples, "checks": checks,
        "passed": all(item["passed"] for item in checks),
    }
    OUT.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print("1D reference: {} checks, passed={}; {}".format(len(checks), report["passed"], OUT.relative_to(ROOT)))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
