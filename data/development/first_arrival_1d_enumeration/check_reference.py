#!/usr/bin/env python3
"""Rebuild invented-case checks and analytic path samples; no provider records."""
import csv
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import scipy
from scipy.optimize import brentq

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "diagnostics"))
from first_arrival_1d_reference import enumerate_arrivals, sample_path

OUT = Path(__file__).resolve().parent
GRID = ROOT / "data/hayward/initial_grid.csv"


def main():
    with GRID.open() as f:
        rows = list(csv.DictReader(f))
    levels = sorted(set((float(r["z"]), float(r["v"])) for r in rows))
    assert len(levels) == len(set(z for z, v in levels)), "Initial grid is not one dimensional"
    hz, hv = map(list, zip(*levels))
    cases, checks, paths = [], [], []

    def check(name, passed, **details):
        checks.append(dict(name=name, passed=bool(passed), **details))

    def close(name, a, b, tolerance, units):
        check(name, abs(a - b) <= tolerance, value=a, reference=b,
              absolute_error=abs(a - b), tolerance=tolerance, units=units)

    def run(name, z, v, source, receiver, derivatives=False, **settings):
        result = enumerate_arrivals(z, v, source, receiver, **settings)
        case = dict(name=name, depths_km=z, velocities_km_s=v,
                    source_xyz_km=source, receiver_xyz_km=receiver, result=result)
        cases.append(case)
        check(name + "_complete", result["complete"] and result["reference_valid"],
              unresolved=result["unresolved"])
        if not result["reference_valid"]:
            return case
        reverse = enumerate_arrivals(z, v, receiver, source)
        check(name + "_reverse_complete", reverse["reference_valid"])
        close(name + "_reciprocity", result["first_arrival"]["time_s"],
              reverse["first_arrival"]["time_s"], 1e-10, "s")
        if derivatives:
            step = 1e-5
            for axis in range(3):
                steps = [step, step / 2, step / 4] if axis == 2 and source[2] in z[1:-1] else [step]
                differences = []
                for h in steps:
                    plus, minus = list(source), list(source)
                    plus[axis] += h
                    minus[axis] -= h
                    a, b = [enumerate_arrivals(z, v, point, receiver, root_tolerance=1e-14) for point in (plus, minus)]
                    check(name + "_finite_difference_complete_" + str((axis, h)),
                          a["reference_valid"] and b["reference_valid"])
                    differences.append((a["first_arrival"]["time_s"] - b["first_arrival"]["time_s"]) / (2 * h))
                # At a gradient knot T is differentiable but T_zz can jump;
                # centered differences then have O(h), rather than O(h^2), bias.
                fd = differences[0] if len(steps) == 1 else 2 * differences[-1] - differences[-2]
                if len(steps) > 1:
                    case.setdefault("knot_derivative_refinement", []).append(dict(
                        axis=axis, steps_km=steps, centered_derivatives=differences,
                        first_order_richardson=fd))
                close(name + "_source_derivative_" + "xyz"[axis],
                      result["first_arrival"]["source_derivative_s_per_km"][axis], fd, 2e-7, "s/km")
        return case

    constant = run("constant", [-1, 0, 4, 20], [6, 6, 6, 6], [-2, 1, 2], [9, -3, 8], True)
    close("constant_time", constant["result"]["first_arrival"]["time_s"], math.sqrt(173) / 6, 1e-12, "s")
    for name, a, b in [("affine_direct", [0, 0, 2], [1, 0, 6]),
                       ("affine_turn", [-20, 0, 2], [20, 0, 2])]:
        case = run(name, [0, 20], [4, 8], a, b, True)
        g, vs, vr = .2, 4 + .2 * a[2], 4 + .2 * b[2]
        length2 = sum((x - y) ** 2 for x, y in zip(a, b))
        exact = math.acosh(1 + g * g * length2 / (2 * vs * vr)) / g
        close(name + "_hyperbolic_distance_time", case["result"]["first_arrival"]["time_s"], exact, 1e-11, "s")
    plateau = run("plateau_two_turns", [-1, 0, 20], [4, 4, 8], [-10, 0, -.5], [10, 0, -.5], True)
    turns = sorted((c for c in plateau["result"]["candidates"] if c["kind"] == "turning"), key=lambda c:c["turning_depth_km"])
    check("plateau_two_turn_count", len(turns) == 2)
    for sign, candidate in zip([-1, 1], turns):
        # Independently written exact flat-over-affine quadratic and time.
        cotangent = (10 + sign * math.sqrt(100 - 40)) / 40
        exact_time = 2 * (.5 * math.sqrt(1 + cotangent ** 2) / (4 * cotangent) + math.asinh(cotangent) / .2)
        close("plateau_branch_time_" + str(sign), candidate["time_s"], exact_time, 1e-11, "s")
    fold = run("exact_double_root", [-1, 0, 10], [4, 4, 5.25], [-8, 0, -.5], [8, 0, -.5])
    check("exact_double_root_retained", sum(c["certificate"] == "exact_double_root" for c in fold["result"]["candidates"]) == 1)
    below = run("below_turn_minimum", [-1, 0, 10], [4, 4, 5.25], [0, 0, -.5], [15.9, 0, -.5])
    check("below_minimum_has_no_turn", not any(c["kind"] == "turning" for c in below["result"]["candidates"]))
    above = run("above_turn_minimum", [-1, 0, 10], [4, 4, 5.25], [0, 0, -.5], [16.1, 0, -.5])
    check("above_minimum_has_two_turns", sum(c["kind"] == "turning" for c in above["result"]["candidates"]) == 2)
    node = run("turn_at_layer_node", [0, 10, 20], [3, 5, 6], [-20, 0, 0], [20, 0, 0])
    check("node_limiting_branches_retained", sum(c["turning_depth_km"] == 10 for c in node["result"]["candidates"]) == 2)
    interior = run("interior_plateau", [0, 10, 12, 32], [3, 5, 5, 7], [-40, 0, 0], [40, 0, 0])
    deep = [c for c in interior["result"]["candidates"] if c["kind"] == "turning"]
    check("interior_plateau_two_turns_and_guide", len(deep) == 2 and any(c["kind"] == "plateau_grazing" for c in interior["result"]["candidates"]))
    # X(r)=10*sqrt(r^2+16)+10*r+20/r is strictly convex: its second
    # derivative is 160/(r^2+16)^(3/2)+40/r^3 > 0. These disjoint brackets
    # independently contain its two X=80 roots below u=7.
    for interval, candidate in zip([(.1, 1.), (2., 3.)], sorted(deep, key=lambda c:c["turning_depth_km"])):
        rr = brentq(lambda r:10 * math.sqrt(r * r + 16) + 10 * r + 20 / r - 80, *interval)
        exact_depth = 12 + (math.sqrt(25 + rr * rr) - 5) / .1
        close("interior_turn_depth_" + str(interval), candidate["turning_depth_km"], exact_depth, 1e-10, "km")
    guide = run("terminal_plateau", [0, 10, 20], [3, 5, 5], [-30, 0, 0], [30, 0, 0])
    close("terminal_plateau_time", guide["result"]["first_arrival"]["time_s"], 10 * math.log(3) + 4, 1e-11, "s")
    for name, a, b in [("hayward_direct", [0, 0, 8], [20, 0, -.2]),
                       ("hayward_turn", [0, 0, 4], [15, 0, -.5]),
                       ("hayward_equal_depth", [-7.5, 0, 8], [7.5, 0, 8]),
                       ("hayward_deep_turn", [-20, 0, -.5], [20, 0, -.5]),
                       ("hayward_vertical", [0, 0, 8], [0, 0, -.2]),
                       ("hayward_bottom", [-30, -27, 8], [30, 27, -.2])]:
        run(name, hz, hv, a, b, True)
    coincident = run("coincident", hz, hv, [0, 0, 8], [0, 0, 8])
    check("coincident_gradient_undefined", coincident["result"]["first_arrival"]["source_derivative_s_per_km"] is None)
    unresolved = enumerate_arrivals(hz, hv, [-20, 0, -.5], [20, 0, -.5], max_boxes=1)
    check("limited_search_fails_closed", not unresolved["complete"] and not unresolved["reference_valid"] and unresolved.get("first_arrival") is None)
    unsupported = enumerate_arrivals([0, 10, 20], [4, 6, 5], [0, 0, 1], [10, 0, 2])
    check("nonmonotone_profile_explicitly_unsupported", not unsupported["complete"] and bool(unsupported["unresolved"]))

    def path_time(points, z, v):
        time = 0.
        for a, b in zip(points, points[1:]):
            length = math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))
            va, vb = np.interp([a[2], b[2]], z, v)
            difference = vb - va
            time += length * (math.log1p(difference / va) / difference if difference else 1 / va)
        return time

    sample_names = {"constant", "hayward_vertical", "plateau_two_turns", "affine_turn", "interior_plateau", "hayward_turn", "hayward_bottom"}
    for case in cases:
        if case["name"] not in sample_names:
            continue
        for index, candidate in enumerate(case["result"]["candidates"]):
            times = []
            for spacing in [.1, .05]:
                points = sample_path(case["depths_km"], case["velocities_km_s"], case["source_xyz_km"], case["receiver_xyz_km"], candidate, spacing)
                check(case["name"] + "_path_endpoints_" + str((index, spacing)), points[0] == case["source_xyz_km"] and points[-1] == case["receiver_xyz_km"])
                check(case["name"] + "_path_domain_" + str((index, spacing)), all(case["depths_km"][0] <= p[2] <= case["depths_km"][-1] for p in points))
                if candidate["turning_depth_km"] is not None:
                    check(case["name"] + "_turn_point_" + str((index, spacing)), any(p[2] == candidate["turning_depth_km"] for p in points))
                for knot in case["depths_km"]:
                    if min(p[2] for p in points) < knot < max(p[2] for p in points):
                        check(case["name"] + "_path_knot_" + str((index, spacing, knot)), any(p[2] == knot for p in points))
                times.append(path_time(points, case["depths_km"], case["velocities_km_s"]))
                if spacing == .05:
                    paths += [dict(case=case["name"], branch=index, kind=candidate["kind"], point=n,
                                   x_km=p[0], y_km=p[1], z_km=p[2]) for n, p in enumerate(points)]
            coarse, fine = [abs(t - candidate["time_s"]) for t in times]
            check(case["name"] + "_path_refinement_" + str(index), fine <= coarse + 1e-11, coarse_error_s=coarse, fine_error_s=fine)
            close(case["name"] + "_fine_polygon_action_" + str(index), times[-1], candidate["time_s"], 1e-5, "s")
    path_file = OUT / "invented_paths.csv"
    with path_file.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(paths[0]))
        writer.writeheader()
        writer.writerows(paths)
    files = [GRID, ROOT / "diagnostics/first_arrival_1d_reference.py", Path(__file__).resolve(), path_file]
    summary = dict(created_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                   command="PYTHONDONTWRITEBYTECODE=1 python3 data/development/first_arrival_1d_enumeration/check_reference.py",
                   geometry_status="Every endpoint and path is invented numerical geometry, not a provider event/station record",
                   model_input="Only the saved initial_grid.csv profile is read; other profiles are explicitly invented",
                   scope="Independent one-dimensional branch enumeration and sampled paths; no production solver or observational queries",
                   finite_difference_step_km=1e-5,
                   knot_derivative_method="At source z equal to an interior model knot, halve h twice and cancel the centered difference O(h) term by Richardson extrapolation; all intermediate derivatives are retained",
                   finite_difference_root_tolerance=1e-14,
                   versions=dict(python=sys.version.split()[0], numpy=np.__version__, scipy=scipy.__version__),
                   sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
                   cases=cases, deliberately_unresolved=unresolved, unsupported=unsupported,
                   checks=checks, passed=all(c["passed"] for c in checks),
                   check_count=len(checks), failed_checks=[c for c in checks if not c["passed"]])
    (OUT / "checks.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
    print("{} invented cases; {} checks; {} failures".format(len(cases), len(checks), len(summary["failed_checks"])))
    if not summary["passed"]:
        print(json.dumps(summary["failed_checks"], indent=2))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
