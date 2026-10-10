#!/usr/bin/env python3
"""Absolute-arrival model resolution at the saved DD model, via block elimination."""
import csv
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy import linalg, sparse

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data/hayward"


def damping_penalty(norm_squared, damping):
    # Exact existing C++ column-scaling fallback for zero/tiny columns.
    return damping ** 2 * np.diag(np.where(norm_squared > 1e-20, norm_squared, 1.))


def read(path):
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def block_resolution(G, row_events, ne, L, damping):
    """G is weighted; rows have one source block and the velocity block."""
    nv = L.shape[1]
    B = G[:, 4 * ne:]
    BtB = (B.T @ B).toarray()
    LtL = L.T @ L
    H = BtB + LtL + damping_penalty(np.diag(BtB + LtL), damping)
    Q = BtB.copy()
    N = BtB.copy()
    min_source_eigenvalue = float("inf")
    for event in range(ne):
        subset = np.flatnonzero(row_events == event)
        if not len(subset):
            raise ValueError("Source without absolute observations")
        E = G[subset, 4 * event:4 * event + 4].toarray()
        B_event = B[subset].toarray()
        EtE = E.T @ E
        C = EtE + damping_penalty(np.diag(EtE), damping)
        min_source_eigenvalue = min(min_source_eigenvalue, float(linalg.eigvalsh(C)[0]))
        D = E.T @ B_event
        # Use precisely the column-scaled damping of the C++ solver.
        CinvD = linalg.cho_solve(linalg.cho_factor(C), D)
        reduction = D.T @ CinvD
        H -= reduction
        Q -= reduction
        N += -2 * reduction + CinvD.T @ EtE @ CinvD
    H, Q, N = [(a + a.T) / 2 for a in (H, Q, N)]
    Hinv = linalg.cho_solve(linalg.cho_factor(H), np.eye(nv))
    R = Hinv @ Q
    noise = Hinv @ N @ Hinv.T
    # This covariance is propagation of measurement noise through the estimator,
    # not the inverse regularized normal matrix interpreted as a posterior.
    return R, noise, {"minimum_source_normal_eigenvalue": min_source_eigenvalue,
                       "model_schur_condition_number": float(np.linalg.cond(H)),
                       "inverse_relative_residual": float(np.linalg.norm(H @ Hinv - np.eye(nv)) / np.sqrt(nv))}


def validate():
    gen = np.random.RandomState(2003)
    ne, nv, per_event = 3, 5, 9
    E = linalg.block_diag(*[gen.normal(size=(per_event, 4)) for _ in range(ne)])
    E[:, 2] = 0  # An unsensed depth column exercises the C++ scaling fallback.
    B = gen.normal(size=(ne * per_event, nv))
    G = np.column_stack([E, B])
    L = gen.normal(size=(7, nv))
    damping = 0.2
    R, noise, _ = block_resolution(sparse.csr_matrix(G),
                                    np.repeat(np.arange(ne), per_event), ne, L, damping)
    penalty = np.zeros((7, G.shape[1]))
    penalty[:, 4 * ne:] = L
    F = G.T @ G
    normal = F + penalty.T @ penalty
    normal += damping_penalty(np.diag(normal), damping)
    Hinv = linalg.inv(normal)
    expected_R = (Hinv @ F)[4 * ne:, 4 * ne:]
    expected_noise = (Hinv @ F @ Hinv.T)[4 * ne:, 4 * ne:]
    errors = {"block_vs_full_resolution": float(np.max(np.abs(R - expected_R))),
              "block_vs_full_noise_covariance": float(np.max(np.abs(noise - expected_noise)))}
    if max(errors.values()) > 1e-10:
        raise ValueError("Resolution block algebra failed: " + str(errors))
    return errors


def run(data_dir=DATA, config_path=ROOT / "configs/hayward.cfg"):
    data_dir, config_path = Path(data_dir), Path(config_path)
    if not data_dir.is_absolute():
        data_dir = ROOT / data_dir
    if not config_path.is_absolute():
        config_path = ROOT / config_path
    data_dir, config_path = data_dir.resolve(), config_path.resolve()
    checks = validate()
    prefix = data_dir / "dd_linearization"
    rows_path = Path(str(prefix) + "_rows.csv")
    matrix_path = Path(str(prefix) + "_matrix.csv")
    columns_path = Path(str(prefix) + "_columns.csv")
    rows, columns = read(rows_path), read(columns_path)
    events = read(data_dir / "dd_events.csv")
    grid = read(data_dir / "dd_grid.csv")
    ne, nv = len(events), len(grid)
    if len(columns) != 4 * ne + nv:
        raise ValueError("Unexpected linearization columns")
    if [int(r["row"]) for r in rows] != list(range(len(rows))):
        raise ValueError("Linearization row identifiers are not consecutive")
    triplets = np.genfromtxt(str(matrix_path), delimiter=",", names=True)
    G = sparse.coo_matrix((triplets["value"], (triplets["row"].astype(int),
                                               triplets["column"].astype(int))),
                          shape=(len(rows), len(columns))).tocsr()
    weight = np.array([float(r["a_priori_weight"]) for r in rows])
    sigma = np.array([float(r["uncertainty_s"]) for r in rows])
    if not np.all(np.isfinite(sigma)) or np.any(sigma <= 0) or not np.allclose(weight * sigma, .05, rtol=1e-10, atol=0):
        raise ValueError("Expected independent-pick weights 0.05s/sigma")
    row_events = np.array([int(r["i"]) for r in rows])
    for r in rows:
        e = events[int(r["i"])]
        if (r["event_i_resource_id"] != e["event_resource_id"] or
                r["origin_i_resource_id"] != e["origin_resource_id"]):
            raise ValueError("Event identities disagree with linearization rows")
    G = sparse.diags(weight) @ G
    settings = {}
    for line in config_path.read_text().splitlines():
        if line.strip() and not line.lstrip().startswith("#"):
            key, value = line.split()
            settings[key] = float(value)
    # Same first differences, coordinates, and ordering as C++ smooth().
    nodes = {(float(r["x"]), float(r["y"]), float(r["z"])): k for k, r in enumerate(grid)}
    axes = [sorted(set(key[d] for key in nodes)) for d in range(3)]
    smooth_rows = []
    for point, node in sorted(nodes.items(), key=lambda item: item[1]):
        for d, axis in enumerate(axes):
            a = axis.index(point[d])
            if a + 1 == len(axis):
                continue
            next_point = list(point)
            next_point[d] = axis[a + 1]
            other = nodes[tuple(next_point)]
            row = np.zeros(nv)
            row[node] = settings["smoothing"] / (axis[a + 1] - point[d])
            row[other] = -row[node]
            smooth_rows.append(row)
    L = np.array(smooth_rows)
    R, noise, condition = block_resolution(G, row_events, ne, L, settings["damping"])
    covariance = .05 ** 2 * noise
    diagonal = np.diag(covariance)
    if np.any(diagonal < -1e-12) or not np.all(np.isfinite(diagonal)):
        raise ValueError("Invalid model covariance")
    vp = np.array([float(r["v"]) for r in grid])
    result = [dict(node=k, x=r["x"], y=r["y"], z=r["z"], v=r["v"],
                   resolution_diagonal=float(R[k, k]),
                   independent_pick_sigma_velocity_km_s=float(vp[k] * np.sqrt(max(0, diagonal[k]))))
              for k, r in enumerate(grid)]
    with (data_dir / "absolute_resolution.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(result[0]))
        writer.writeheader()
        writer.writerows(result)
    np.savez_compressed(str(data_dir / "absolute_resolution_matrices.npz"),
                        log_slowness_resolution=R,
                        velocity_resolution=vp[:, None] * R / vp[None, :],
                        log_slowness_measurement_noise_covariance=covariance)
    manifest = {
        "data_directory": str(data_dir.relative_to(ROOT)),
        "configuration": str(config_path.relative_to(ROOT)),
        "linearization_point": "saved dd_events.csv and dd_grid.csv",
        "observations": "absolute catalog P picks only, independent reported picking errors assumed",
        "uncertainty_interpretation": "reported symmetric uncertainty interpreted as independent 1-sigma picking noise; confidence levels are not supplied, so calibration is an assumption",
        "weights": "0.05s / reported sigma; no residual-biweight factor",
        "parameterization": "source x,y,z,t then q=delta log(slowness); sigma_v=v*sigma_q",
        "regularization": "first-difference log-slowness smoothing plus column-scaled LSQR damping, linearized with fixed weights",
        "column_scaling_fallback": "same as C++: squared column norm<=1e-20 uses scale1, otherwise inverse square root",
        "resolution": "velocity block diagonal of H_joint^-1 G_weighted^T G_weighted; source parameters eliminated analytically",
        "uncertainty": "frequentist propagation through damped estimator, 0.05^2 H_joint^-1 G_weighted^T G_weighted H_joint^-1",
        "source_coordinate_constraints": "This local linear estimator treats source coordinates as unconstrained. Its covariance does not account for active source-domain bounds and is not the covariance of the bound-constrained nonlinear estimator.",
        "section_display": "Figure 11 interpolates nodal resolution diagonals and nodal standard errors. Interpolated standard errors are not covariance propagation to intermediate spatial points.",
        "limitations": ["not a full DD resolution calculation", "not the manuscript's simul2000 parameterization or exact dataset",
                        "excludes correlated station/model errors, nonlinear and ray errors, selection effects, and regularization bias",
                        "excludes active source-domain constraints from the linear covariance",
                        "small propagated noise does not imply small total model error"],
        "validation": checks, "conditioning": condition,
        "resolution_diagonal_min_max": [float(np.diag(R).min()), float(np.diag(R).max())],
        "velocity_sigma_min_max_km_s": [float(min(r["independent_pick_sigma_velocity_km_s"] for r in result)),
                                        float(max(r["independent_pick_sigma_velocity_km_s"] for r in result))],
        "source_mappings": {"rows": str(rows_path.relative_to(ROOT)), "columns": str(columns_path.relative_to(ROOT))},
        "analysis_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "input_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in (rows_path, matrix_path, columns_path, data_dir / "dd_events.csv", data_dir / "dd_grid.csv",
                                   config_path)},
    }
    (data_dir / "absolute_resolution_manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"validation": checks, "conditioning": condition}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DATA,
                        help="Saved field results, relative to the repository root (default: data/hayward)")
    parser.add_argument("--config", type=Path, default=ROOT / "configs/hayward.cfg",
                        help="Configuration used by this inversion (default: configs/hayward.cfg)")
    args = parser.parse_args()
    run(args.data_dir, args.config)
