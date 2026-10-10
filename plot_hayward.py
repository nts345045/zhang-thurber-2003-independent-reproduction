#!/usr/bin/env python3
"""Plot independently inferred Hayward results, retaining identified point tables."""
import argparse
import csv
import hashlib
import json
import os
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / "tmp/matplotlib"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.interpolate import RegularGridInterpolator

from data.authoritative.hayward.acquire import horizontal_coordinates, parse_time

DATA = ROOT / "data/hayward"
FIG = ROOT / "figures/hayward"


def read(name):
    with (DATA / name).open(newline="") as f:
        return list(csv.DictReader(f))


def write(name, rows):
    with (DATA / name).open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def inverse_xy(x, y, lat, lon):
    # Numerically invert the same zero-height ellipsoid/tangent projection.
    # These coordinates are estimates; original provider coordinates remain in
    # separate catalog_* fields and retain the reference origin resource ID.
    for _ in range(8):
        xy = np.array(horizontal_coordinates(lat, lon)[2:])
        error = np.array([x, y]) - xy
        if np.linalg.norm(error) < 1e-8:
            return lat, lon
        h = 1e-5
        jac = np.column_stack([(np.array(horizontal_coordinates(lat + h, lon)[2:]) - xy) / h,
                               (np.array(horizontal_coordinates(lat, lon + h)[2:]) - xy) / h])
        step = np.linalg.solve(jac, error)
        lat += step[0]
        lon += step[1]
    raise ValueError("Projection inverse failed to converge")


def events(mode):
    rows = read(mode + "_events.csv")
    for row in rows:
        lat, lon = inverse_xy(float(row["x"]), float(row["y"]),
                              float(row["catalog_latitude_deg"]), float(row["catalog_longitude_deg"]))
        row["estimated_latitude_deg"] = lat
        row["estimated_longitude_deg"] = lon
        row["estimated_origin_time_utc"] = (parse_time(row["reference_origin_time_utc"]) +
                                             timedelta(seconds=float(row["t"]))).isoformat().replace("+00:00", "Z")
    write(mode + "_geographic_events.csv", rows)
    return rows


def values(rows, field):
    return np.array([float(r[field]) for r in rows])


def save(fig, name):
    fig.savefig(str(FIG / (name + ".pdf")), bbox_inches="tight")
    fig.savefig(str(FIG / (name + ".png")), dpi=160, bbox_inches="tight")
    plt.close(fig)


def setup(ax, x, y):
    ax.set_xlabel(x)
    ax.set_ylabel(y)
    ax.grid(alpha=.18)


def main(geometry_only=False):
    FIG.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})
    cohort = {mode: events(mode) for mode in (("initial",) if geometry_only else ("initial", "standard", "loc1d", "dd"))}
    initial = cohort["initial"]
    station_rows = read("stations.csv")
    station_points = {(float(r["longitude_deg"]), float(r["latitude_deg"])) for r in station_rows}
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.scatter(values(initial, "estimated_longitude_deg"), values(initial, "estimated_latitude_deg"),
               s=4, c="0.25", alpha=.6, label="Selected earthquakes ({})".format(len(initial)))
    sx, sy = zip(*sorted(station_points))
    ax.scatter(sx, sy, marker="^", facecolors="none", edgecolors="#b34723", s=35,
               label="Receiver positions ({})".format(len(station_points)))
    grid = read("initial_grid.csv")
    xy = sorted(set((float(r["x"]), float(r["y"])) for r in grid))
    ll = [inverse_xy(x, y, 37.72, -122.06) for x, y in xy]
    ax.scatter([p[1] for p in ll], [p[0] for p in ll], marker="+", s=20, c="#397aa2", label="Model nodes")
    setup(ax, "Longitude (degrees east)", "Latitude (degrees north)")
    ax.set_aspect(1 / np.cos(np.deg2rad(37.72)))
    ax.legend(fontsize=8)
    ax.set_title("Figure 4 counterpart: authoritative subset and model grid")
    save(fig, "figure04_geometry")
    geometry = dict(events=len(initial), physical_stations=len({r["station_seed_id"] for r in station_rows}),
                    receiver_positions=len(station_points), horizontal_model_nodes=len(xy),
                    status="partially reproduced: independently selected authoritative geometry, not the original manuscript cohort",
                    metadata_interpretation="Provider sensor elevations and the explicit CMW1 historical-ELEV assumption are documented in data/authoritative/stations/README.md",
                    inputs={name: hashlib.sha256((DATA / name).read_bytes()).hexdigest()
                            for name in ("initial_events.csv", "stations.csv", "initial_grid.csv", "selection_manifest.json")},
                    plot_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (DATA / "figure04_geometry_manifest.json").write_text(json.dumps(geometry, indent=2) + "\n")
    if geometry_only:
        print(json.dumps(geometry, indent=2))
        return

    names = {"initial": "Catalog", "standard": "Absolute-data tomography",
             "loc1d": "Fixed 1D model relocation", "dd": "Catalog DD tomography"}
    fig, axes = plt.subplots(2, 2, figsize=(9, 8), sharex=True, sharey=True)
    for label, mode, ax in zip("abcd", cohort, axes.flat):
        rows = cohort[mode]
        ax.scatter(values(rows, "estimated_longitude_deg"), values(rows, "estimated_latitude_deg"), s=3, c="0.2", alpha=.65)
        setup(ax, "Longitude (degrees east)", "Latitude (degrees north)")
        ax.set_title("({}) {}".format(label, names[mode]))
        ax.set_aspect(1 / np.cos(np.deg2rad(37.72)))
    fig.suptitle("Figure 5 counterpart: common selected events; catalog data only")
    fig.tight_layout(rect=(0, 0, 1, .96))
    save(fig, "figure05_locations")

    # Selection is fixed by original catalog coordinates, so movement does not
    # change membership between methods. Section-box endpoints are not given
    # in the written specification; show all selected zoom events in both views.
    zoom_ids = {r["event_resource_id"] for r in initial
                if 37.83 <= float(r["catalog_latitude_deg"]) <= 37.91 and
                -122.26 <= float(r["catalog_longitude_deg"]) <= -122.18}
    zoom = {mode: [r for r in rows if r["event_resource_id"] in zoom_ids]
            for mode, rows in cohort.items()}
    if not zoom_ids:
        raise ValueError("No catalog-selected events in manuscript zoom region")
    zoom_limits = {}
    for field in ["estimated_longitude_deg", "estimated_latitude_deg", "x", "y", "z"]:
        samples = [float(r[field]) for rows in zoom.values() for r in rows]
        lo, hi = min(samples), max(samples)
        padding = .05 * max(hi - lo, 1e-6)
        zoom_limits[field] = [lo - padding, hi + padding]
    for number, mode in zip(range(6, 10), cohort):
        rows = zoom[mode]
        write(mode + "_zoom_events.csv", rows)
        fig, axes = plt.subplots(2, 2, figsize=(9, 7))
        for ax, xfield, yfield, xlabel, ylabel, label in zip(
                axes.flat, ["estimated_longitude_deg", "x", "x", "y"],
                ["estimated_latitude_deg", "y", "z", "z"],
                ["Longitude (degrees east)", "X northeast (km)", "X northeast (km)", "Y northwest (km)"],
                ["Latitude (degrees north)", "Y northwest (km)", "Geoid depth (km)", "Geoid depth (km)"], "abcd"):
            ax.scatter(values(rows, xfield), values(rows, yfield), s=7, c="0.2", alpha=.65)
            setup(ax, xlabel, ylabel)
            ax.set_xlim(*zoom_limits[xfield])
            ax.set_ylim(*zoom_limits[yfield])
            ax.set_title("({})".format(label), loc="left")
            if yfield == "z":
                ax.invert_yaxis()
        axes[0, 0].set_aspect(1 / np.cos(np.deg2rad(37.72)))
        fig.suptitle("Figure {} counterpart: {}; {} common zoom events".format(number, names[mode], len(rows)))
        fig.tight_layout(rect=(0, 0, 1, .95))
        save(fig, "figure{:02d}_{}".format(number, mode))

    def model(mode, field="v", filename=None):
        rows = read(filename or mode + "_grid.csv")
        ax = [np.array(sorted(set(float(r[k]) for r in rows))) for k in ("x", "y", "z")]
        array = np.zeros(tuple(len(a) for a in ax))
        for r in rows:
            index = tuple(int(np.searchsorted(a, float(r[k]))) for a, k in zip(ax, ("x", "y", "z")))
            array[index] = float(r[field])
        return RegularGridInterpolator(tuple(ax), array, bounds_error=True)

    # Include the elevated-receiver layer so source estimates on its upper
    # boundary remain visible. This is the saved computational domain, not a
    # reconstructed manuscript section extent.
    zmin, zmax = min(float(r["z"]) for r in grid), max(float(r["z"]) for r in grid)
    x, z = np.linspace(-35, 35, 141), np.linspace(zmin, zmax, int(round((zmax - zmin) / .25)) + 1)
    xx, zz = np.meshgrid(x, z)
    standard, dd = model("standard"), model("dd")
    sections = []
    fig, axes = plt.subplots(7, 3, figsize=(11, 15), sharex=True, sharey=True)
    for row, y in enumerate(range(-30, 31, 10)):
        points = np.column_stack([xx.ravel(), np.full(xx.size, y), zz.ravel()])
        vs, vd = standard(points).reshape(xx.shape), dd(points).reshape(xx.shape)
        for index, (xv, zv, sv, dv) in enumerate(zip(xx.ravel(), zz.ravel(), vs.ravel(), vd.ravel())):
            sections.append(dict(x=xv, y=y, z=zv, standard_v=sv, dd_v=dv, dd_minus_standard=dv - sv))
        for col, vv, mode in ((0, vd, "dd"), (1, vs, "standard"), (2, vd - vs, "dd")):
            ax = axes[row, col]
            if col < 2:
                im = ax.pcolormesh(xx, zz, vv, cmap="viridis", vmin=3.5, vmax=7, shading="auto")
            else:
                diff = ax.pcolormesh(xx, zz, vv, cmap="RdBu_r", vmin=-.8, vmax=.8, shading="auto")
            near = [r for r in cohort[mode] if abs(float(r["y"]) - y) <= 5]
            ax.scatter(values(near, "x"), values(near, "z"), s=1.5, c="k", alpha=.45, clip_on=False)
            ax.set_ylim(zmax, zmin)
            ax.set_xlim(-35, 35)
            if col == 0:
                ax.set_ylabel("Y={} km\nGeoid depth (km)".format(y))
            if row == 6:
                ax.set_xlabel("X northeast (km)")
    for ax, title in zip(axes[0], ["(a) Catalog DD", "(b) Absolute only", "(c) DD minus absolute"]):
        ax.set_title(title)
    fig.colorbar(im, ax=axes[:, :2].ravel().tolist(), label="P velocity (km/s)", shrink=.7, pad=.02)
    fig.colorbar(diff, ax=axes[:, 2].ravel().tolist(), label="Velocity difference (km/s)", shrink=.7, pad=.02)
    fig.suptitle("Figure 10 counterpart: independent subset; points within 5 km of each section")
    write("vertical_sections.csv", sections)
    save(fig, "figure10_velocity")

    resolution = model("", "resolution_diagonal", "absolute_resolution.csv")
    uncertainty = model("", "independent_pick_sigma_velocity_km_s", "absolute_resolution.csv")
    fig, axes = plt.subplots(7, 2, figsize=(9, 15), sharex=True, sharey=True)
    resolution_sections = []
    for row, y in enumerate(range(-30, 31, 10)):
        points = np.column_stack([xx.ravel(), np.full(xx.size, y), zz.ravel()])
        rr, ss = resolution(points).reshape(xx.shape), uncertainty(points).reshape(xx.shape)
        for xv, zv, rv, sv in zip(xx.ravel(), zz.ravel(), rr.ravel(), ss.ravel()):
            resolution_sections.append(dict(x=xv, y=y, z=zv, resolution_diagonal=rv, independent_pick_sigma_velocity_km_s=sv))
        rim = axes[row, 0].pcolormesh(xx, zz, rr, cmap="viridis", vmin=0, vmax=1, shading="auto")
        sim = axes[row, 1].pcolormesh(xx, zz, ss, cmap="magma", shading="auto")
        for ax in axes[row]:
            ax.set_ylim(zmax, zmin)
            if row == 6:
                ax.set_xlabel("X northeast (km)")
        axes[row, 0].set_ylabel("Y={} km\nGeoid depth (km)".format(y))
    axes[0, 0].set_title("(a) Nodal resolution (interpolated)")
    axes[0, 1].set_title("(b) Nodal pick noise (interpolated)")
    # Share an uncertainty scale across all sections.
    max_sigma = max(r["independent_pick_sigma_velocity_km_s"] for r in resolution_sections)
    for ax in axes[:, 1]:
        ax.collections[0].set_clim(0, max_sigma)
    fig.colorbar(rim, ax=axes[:, 0].tolist(), label="Interpolated nodal resolution diagonal", shrink=.7, pad=.02)
    fig.colorbar(sim, ax=axes[:, 1].tolist(), label="Interpolated nodal velocity noise (km/s)", shrink=.7, pad=.02)
    fig.suptitle("Figure 11 counterpart: absolute-data linearization at the catalog DD solution")
    write("resolution_sections.csv", resolution_sections)
    save(fig, "figure11_resolution")

    metric = {"catalog_zoom_events": len(zoom_ids), "zoom_common_coordinate_limits": zoom_limits,
              "section_geoid_depth_range_km": [zmin, zmax],
              "resolution_section_interpretation": "The resolution_diagonal and independent_pick_sigma_velocity_km_s columns interpolate nodal diagnostics for display; the latter is not sqrt(w^T C_v w) for interpolated velocity.",
              "modes": {}}
    p0 = np.column_stack([values(initial, k) for k in ("x", "y", "z")])
    for mode, rows in cohort.items():
        p = np.column_stack([values(rows, k) for k in ("x", "y", "z")])
        result = {"centroid_xyz_km": p.mean(axis=0).tolist(),
                  "median_displacement_from_catalog_km": float(np.median(np.linalg.norm(p - p0, axis=1))),
                  "depth_min_max_km": [float(p[:, 2].min()), float(p[:, 2].max())],
                  "interpretation": "displacement from catalog is not location error against truth"}
        if mode != "initial":
            residuals = read(mode + "_residuals.csv")
            result["unweighted_rms_s"] = {str(t): float(np.sqrt(np.mean([float(r["residual"]) ** 2 for r in residuals if int(r["type"]) == t]))) for t in (0, 1)}
            history = read(mode + "_history.csv")
            result["accepted_updates"] = sum(float(r["step_fraction"]) > 0 for r in history)
            result["failed_linear_solves"] = sum(int(r["lsqr_converged"]) == 0 for r in history)
        metric["modes"][mode] = result
    metric["figure_deviations"] = ["common independently selected current catalog cohort",
        "no waveform-correlation observations in these runs", "no digitized fault trace or section-box boundaries",
        "zoom cross sections include all catalog-selected zoom events, not undocumented AA/BB boxes",
        "fixed-model relocation retains absolute-data anchoring", "resolution uncertainty assumes reported symmetric uncertainties are independent 1-sigma picking errors; provider confidence levels are absent"]
    metric["figure_deviations"].append("velocity and resolution sections include the full computational depth range, including the elevated-receiver layer")
    metric["input_sha256"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in sorted(DATA.glob("*.csv")) if "geographic" not in p.name and "zoom" not in p.name}
    (DATA / "figure_metrics.json").write_text(json.dumps(metric, indent=2, allow_nan=False) + "\n")
    print(json.dumps(metric["modes"], indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--geometry-only", action="store_true", help="Generate Figure 4 from identified inputs before inversion")
    main(parser.parse_args().geometry_only)
