#!/usr/bin/env python3
"""Conditional full-DD model resolution and shared-pick noise propagation."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy import linalg, sparse
from scipy.sparse import linalg as sparse_linalg

ROOT = Path(__file__).resolve().parent


def read(path):
    with Path(path).open(newline="") as stream:
        return list(csv.DictReader(stream))


def joint_resolution(A, L, source_columns, damping_coefficients, U,
                     unmasked_model=None):
    """A=W J_masked; U=W P diag(sigma_pick); all row multipliers are frozen.

    L has the full parameter width but acts only on model columns. Damping is
    supplied in unscaled parameter coordinates, lambda / exported_column_scale.
    DD rows couple source blocks, so their normal block is solved jointly.
    """
    A, L, U = [sparse.csr_matrix(x) for x in (A, L, U)]
    ns = int(source_columns)
    if not 0 < ns < A.shape[1] or L.shape[1] != A.shape[1] or U.shape[0] != A.shape[0]:
        raise ValueError("Incompatible joint-resolution dimensions")
    if L[:, :ns].nnz:
        raise ValueError("This elimination requires model-only smoothing")
    damping = np.asarray(damping_coefficients, dtype=float)
    if (damping.shape != (A.shape[1],) or not np.all(np.isfinite(damping)) or
            np.any(damping < 0)):
        raise ValueError("Invalid unscaled damping coefficients")
    for matrix in (A, L, U):
        if not np.all(np.isfinite(matrix.data)):
            raise ValueError("Nonfinite local operator")
    E, B = A[:, :ns], A[:, ns:]
    C = (E.T @ E + sparse.diags(damping[:ns] ** 2)).tocsc()
    D = (E.T @ B).toarray()
    source_factor = sparse_linalg.splu(C)
    Z = source_factor.solve(D)
    BtB = (B.T @ B).toarray()
    Q = BtB - D.T @ Z
    Hq = Q + (L[:, ns:].T @ L[:, ns:]).toarray() + np.diag(damping[ns:] ** 2)
    Q, Hq = [(x + x.T) / 2 for x in (Q, Hq)]
    model_factor = linalg.cho_factor(Hq)
    resolution = linalg.cho_solve(model_factor, Q)
    # U preserves the shared constituent picks. Never form an nobs-by-nobs
    # covariance or add a second 0.05^2 factor to these physical pick sigmas.
    V = (B.T @ U).toarray() - ((E.T @ U).T @ Z).T
    transfer = linalg.cho_solve(model_factor, V)
    covariance = transfer @ transfer.T
    physical_response = None
    if unmasked_model is not None:
        F = sparse.csr_matrix(unmasked_model)
        if F.shape != B.shape or not np.all(np.isfinite(F.data)):
            raise ValueError("Invalid weighted unmasked model derivative")
        cross = (B.T @ F).toarray() - Z.T @ (E.T @ F).toarray()
        physical_response = linalg.cho_solve(model_factor, cross)
    diagnostics = {
        "source_normal_rows": ns,
        "source_solve_relative_residual": float(np.linalg.norm(C @ Z - D) /
                                                  max(np.linalg.norm(D), 1e-300)),
        "model_schur_condition_number": float(np.linalg.cond(Hq)),
        "resolution_equation_relative_residual": float(np.linalg.norm(Hq @ resolution - Q) /
                                                        max(np.linalg.norm(Q), 1e-300)),
        "noise_transfer_relative_residual": float(np.linalg.norm(Hq @ transfer - V) /
                                                  max(np.linalg.norm(V), 1e-300)),
    }
    for result in (resolution, covariance):
        if not np.all(np.isfinite(result)):
            raise ValueError("Nonfinite full-DD result")
    return resolution, covariance, physical_response, diagnostics


def pick_noise(rows):
    """Native pick identities define independent primitive errors, not DD rows."""
    picks, indices, row_index, pick_index, entries = [], {}, [], [], []
    absolute_values, differences = {}, []
    for q, row in enumerate(rows):
        kind = int(row["type"])
        if kind not in (0, 1):
            raise ValueError("Shared catalog-pick covariance is defined only for types 0 and 1")
        ids = []
        for side, sign in (("i", 1), ("j", -1))[:1 if kind == 0 else 2]:
            def obs(key):
                return row["observation_" + key]
            identity = obs("pick_" + side + "_resource_id")
            if not identity:
                raise ValueError("Missing native pick ID at observation " + str(q))
            sigma = float(obs("pick_" + side + "_uncertainty_s"))
            if not np.isfinite(sigma) or sigma <= 0:
                raise ValueError("Missing positive pick uncertainty: " + identity)
            record = {"pick_resource_id": identity, "uncertainty_s": sigma}
            for name in ("event", "origin", "arrival"):
                record[name + "_resource_id"] = obs(name + "_" + side + "_resource_id")
                if not record[name + "_resource_id"]:
                    raise ValueError("Missing native pick association: " + identity)
            for name in ("time_utc", "uncertainty_confidence_level", "source_sha256"):
                record["pick_" + name] = obs("pick_" + side + "_" + name)
            for name in ("network_code", "station_code", "location_code", "channel_code",
                         "channel_seed_id", "channel_fdsn_source_id"):
                record[name] = obs(name)
                if name != "location_code" and not record[name]:
                    raise ValueError("Missing native channel identity: " + identity)
            for edge in ("start", "end"):
                record["metadata_epoch_" + edge] = obs("metadata_epoch_" +
                                                       ("j_" if side == "j" else "") + edge)
            record["channel_source_sha256"] = obs("channel_" + ("j_" if side == "j" else "") + "source_sha256")
            if not record["metadata_epoch_start"] or not record["pick_time_utc"]:
                raise ValueError("Missing native pick time or epoch: " + identity)
            if identity not in indices:
                indices[identity] = len(picks)
                picks.append(record)
            elif picks[indices[identity]] != record:
                raise ValueError("Inconsistent repeated native pick metadata: " + identity)
            index = indices[identity]
            ids.append(identity)
            multiplier = float(row["combined_multiplier"]) if int(row["active"]) else 0.
            row_index.append(q); pick_index.append(index); entries.append(sign * multiplier * sigma)
        if kind == 0:
            value = float(row["observed"])
            if ids[0] in absolute_values and absolute_values[ids[0]] != value:
                raise ValueError("Inconsistent repeated absolute value: " + ids[0])
            absolute_values[ids[0]] = value
        else:
            differences.append((q, ids[0], ids[1], float(row["observed"])))
    for q, first, second, value in differences:
        if first not in absolute_values or second not in absolute_values:
            raise ValueError("DD constituent lacks an absolute observation at row " + str(q))
        # This checks the declared catalog-difference construction, allowing
        # only the existing decimal serialization scale, not a timing fit error.
        if abs(value - (absolute_values[first] - absolute_values[second])) > 1e-10:
            raise ValueError("DD value is not the constituent absolute difference at row " + str(q))
    U = sparse.coo_matrix((entries, (row_index, pick_index)),
                          shape=(len(rows), len(picks))).tocsr()
    return U, picks


def triplet_matrix(path, shape, value_column, return_norm=False):
    with Path(path).open() as stream:
        table = csv.DictReader(stream)
        row_key = "observation_row" if "observation_row" in table.fieldnames else "row"
        row, col, value = [], [], []
        for entry in table:
            row.append(int(entry[row_key])); col.append(int(entry["column"]))
            value.append(float(entry[value_column]))
    if (any(x < 0 or x >= shape[0] for x in row) or
            any(x < 0 or x >= shape[1] for x in col) or not np.all(np.isfinite(value))):
        raise ValueError("Invalid matrix triplets: " + str(path))
    matrix = sparse.coo_matrix((value, (row, col)), shape=shape).tocsr()
    if return_norm:
        return matrix, np.bincount(col, weights=np.asarray(value) ** 2, minlength=shape[1])
    return matrix


def run(data_dir, mode):
    data_dir = Path(data_dir).resolve()
    prefix = data_dir / (mode + "_full_linearization")
    paths = {suffix: Path(str(prefix) + "_" + suffix + ".csv") for suffix in
             ("rows", "matrix", "columns", "suppressed", "smoothing_rows", "smoothing_matrix", "rays", "info")}
    rows, columns = read(paths["rows"]), read(paths["columns"])
    info = {r["key"]: r["value"] for r in read(paths["info"])}
    events_path, grid_path = data_dir / (mode + "_events.csv"), data_dir / (mode + "_grid.csv")
    events, grid = read(events_path), read(grid_path)
    observations_path, stations_path = data_dir / "observations.csv", data_dir / "stations.csv"
    observations, stations = read(observations_path), read(stations_path)
    ns, nv = 4 * len(events), len(grid)
    if len(columns) != ns + nv or len(rows) != int(info["observations"]):
        raise ValueError("Full model linearization dimensions disagree")
    if [int(r["observation_row"]) for r in rows] != list(range(len(rows))):
        raise ValueError("Observation indices are not consecutive")
    if [int(r["column"]) for r in columns] != list(range(len(columns))):
        raise ValueError("Parameter indices are not consecutive")
    if len(observations) != len(rows):
        raise ValueError("Original observation support changed")
    active = 0
    for q, row in enumerate(rows):
        original = observations[q]
        for key, value in original.items():
            if key in ("i", "j", "station", "type"):
                if int(row[key]) != int(value):
                    raise ValueError("Original observation index changed")
            elif key == "value":
                if float(row["observed"]) != float(value):
                    raise ValueError("Original observed value changed")
            elif row["observation_" + key] != value:
                raise ValueError("Original native observation metadata changed: " + key)
        if int(row["active"]):
            if int(row["matrix_row"]) != active or row["omission_reason"]:
                raise ValueError("Active matrix-row ordering changed")
            active += 1
        elif int(row["matrix_row"]) != -1 or not row["omission_reason"]:
            raise ValueError("Omitted observation lacks explicit status")
        if int(row["stage"]) != int(info["stage"]):
            raise ValueError("Mixed weight stages")
    if active != int(info["active_data_rows"]):
        raise ValueError("Active row count changed")
    for k, column in enumerate(columns):
        if k < ns:
            event = events[k // 4]
            if (column["parameter"] != ("x", "y", "z", "t")[k % 4] or
                    int(column["event"]) != k // 4 or
                    column["source_event_resource_id"] != event["event_resource_id"] or
                    column["source_origin_resource_id"] != event["origin_resource_id"]):
                raise ValueError("Source column identities disagree")
        else:
            if column["parameter"] != "q" or int(column["node"]) != k - ns:
                raise ValueError("Model columns disagree")
            if any(float(column[axis]) != float(grid[k - ns][axis]) for axis in ("x", "y", "z")):
                raise ValueError("Model node coordinates disagree")
    for row in rows:
        for side in ("i", "j")[:1 if int(row["type"]) == 0 else 2]:
            event = events[int(row[side])]
            for name in ("event", "origin"):
                if row["observation_" + name + "_" + side + "_resource_id"] != event[name + "_resource_id"]:
                    raise ValueError("Observation source identity mismatch")
            station = stations[int(row["station" if side == "i" else "station_j_index"])]
            for name in ("network_code", "station_code", "location_code", "channel_code",
                         "channel_seed_id", "channel_fdsn_source_id"):
                if row["observation_" + name] != station[name]:
                    raise ValueError("Observation receiver identity mismatch")
            for edge in ("start", "end"):
                key = "metadata_epoch_" + ("j_" if side == "j" else "") + edge
                if row["observation_" + key] != station["metadata_epoch_" + edge]:
                    raise ValueError("Observation native receiver epoch mismatch")
    shape = (len(rows), len(columns))
    A, data_norm = triplet_matrix(paths["matrix"], shape, "weighted_value", True)
    J = triplet_matrix(paths["matrix"], shape, "value")
    suppressed_rows = read(paths["suppressed"])
    correction = sparse.coo_matrix(([float(r["unmasked_value"]) for r in suppressed_rows],
                                    ([int(r["observation_row"]) for r in suppressed_rows],
                                     [int(r["column"]) for r in suppressed_rows])), shape=shape).tocsr()
    weight = np.array([float(r["combined_multiplier"]) if int(r["active"]) else 0. for r in rows])
    mismatch = A - sparse.diags(weight) @ J
    if mismatch.nnz and np.max(np.abs(mismatch.data)) > 1e-14:
        raise ValueError("Exported weighted and unweighted matrices disagree")
    smoothing_rows = read(paths["smoothing_rows"])
    L, smoothing_norm = triplet_matrix(paths["smoothing_matrix"],
                                      (len(smoothing_rows), len(columns)), "weighted_value", True)
    exported_norm = np.array([float(r["squared_column_norm"]) for r in columns])
    if not np.allclose(data_norm + smoothing_norm, exported_norm, rtol=1e-13, atol=1e-25):
        raise ValueError("Ordered-entry column norms disagree")
    damping = np.array([float(r["unscaled_damping_coefficient"]) for r in columns])
    expected_scale = np.where(exported_norm > 1e-20,
                              1 / np.sqrt(np.maximum(exported_norm, 1e-300)), 1.)
    if not np.array_equal(expected_scale, np.array([float(r["column_scale"]) for r in columns])):
        raise ValueError("Column-scaling fallback disagrees")
    if not np.allclose(damping, float(info["damping"]) / expected_scale, rtol=1e-15, atol=0):
        raise ValueError("Unscaled damping disagrees")
    U, picks = pick_noise(rows)
    R, covariance, physical, condition = joint_resolution(A, L, ns, damping, U,
        sparse.diags(weight) @ (J + correction)[:, ns:])
    velocity = np.array([float(r["v"]) for r in grid])
    if not np.all(np.isfinite(velocity)) or np.any(velocity <= 0):
        raise ValueError("Invalid saved velocity")
    sigma = velocity * np.sqrt(np.maximum(0., np.diag(covariance)))
    output_prefix = data_dir / (mode + "_full_resolution")
    with Path(str(output_prefix) + ".csv").open("w", newline="") as stream:
        fields = ["node", "x", "y", "z", "v", "masked_resolution_diagonal",
                  "unmasked_model_response_diagonal", "shared_pick_sigma_velocity_km_s"]
        writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader()
        for k, row in enumerate(grid):
            result = dict(row, node=k, masked_resolution_diagonal=R[k, k],
                          unmasked_model_response_diagonal=physical[k, k],
                          shared_pick_sigma_velocity_km_s=sigma[k])
            writer.writerow(result)
    with Path(str(output_prefix) + "_picks.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["pick_column"] + list(picks[0]))
        writer.writeheader()
        for k, pick in enumerate(picks): writer.writerow(dict(pick, pick_column=k))
    np.savez_compressed(str(output_prefix) + "_matrices.npz",
                        masked_log_slowness_resolution=R,
                        unmasked_log_slowness_model_response=physical,
                        masked_velocity_resolution=velocity[:, None] * R / velocity[None, :],
                        shared_pick_log_slowness_noise_covariance=covariance)
    manifest = {
        "linearization_point": mode + " saved event/model state",
        "observations": len(rows), "active_observations": int(info["active_data_rows"]),
        "independent_primitive_pick_errors": len(picks), "stage": int(info["stage"]),
        "stage_basis": info["stage_basis"], "weights": info["weight_point"],
        "noise_assumption": "Native catalog picks have independent errors; reported symmetric uncertainty is assumed to be one sigma. Catalog differences share these same errors through their +1/-1 pick incidence. Confidence levels are not supplied; calibration is assumed.",
        "estimator": "Frozen weighted/masked local design with coupled source elimination, exported smoothing and column-scaled damping; not an inverse-normal posterior covariance",
        "masked_resolution": "Velocity/model block of H^-1 A^T A for the assembled masked design",
        "unmasked_response": "Velocity/model block of H^-1 A^T W J_unmasked, conditional on the exported ray derivatives",
        "noise_covariance": "Model block of H^-1 A^T W P Sigma_pick P^T W A H^-1; no extra 0.05^2 factor",
        "ray_status_failures": int(info["ray_status_failures"]),
        "limitations": ["Conditional on fixed robust/distance weights, kernel masks, column scales, and computed ray branches.",
                        "Source-domain bounds and their active sets are omitted; this is not the covariance of the constrained nonlinear estimator.",
                        "Reference catalog origin baselines are held fixed; source-coordinate and origin-time parameters remain jointly coupled in the local estimator.",
                        "Excludes correlated station/model errors, selection effects, regularization bias, nonlinear errors, and ray/derivative errors.",
                        "No cross-correlation data or independent differential noise are inferred.",
                        "Unmasked response uses the computed local ray derivatives and is not a first-arrival accuracy certificate."],
        "conditioning": condition,
        "masked_resolution_diagonal_range": [float(np.diag(R).min()), float(np.diag(R).max())],
        "unmasked_response_diagonal_range": [float(np.diag(physical).min()), float(np.diag(physical).max())],
        "velocity_sigma_range_km_s": [float(sigma.min()), float(sigma.max())],
        "input_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in list(paths.values()) + [events_path, grid_path, observations_path, stations_path]},
        "analysis_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    Path(str(output_prefix) + "_manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"observations": len(rows), "primitive_picks": len(picks),
                      "conditioning": condition}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--mode", default="dd")
    options = parser.parse_args()
    run(options.data_dir if options.data_dir.is_absolute() else ROOT / options.data_dir, options.mode)
