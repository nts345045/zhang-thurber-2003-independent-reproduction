#pragma once
// Included after the observation/assembly helpers in main.cpp. This diagnostic
// exports the same rows used by invert, including its DD path-length mask.
struct FullLinearizationCounts {
  size_t observations = 0, active = 0, smoothing = 0, suppressed = 0;
};

FullLinearizationCounts write_full_linearization(
    const Config &c, const std::string &prefix, const std::string &solver_mode,
    int stage, const std::string &stage_basis, const std::vector<Event> &events,
    const std::vector<Event> &stations, const ObservationSet &data, const Grid &g,
    const std::vector<Ray> &traced) {
  if (stage < 0 || stage > 2)
    throw std::runtime_error("Full linearization stage must be 0, 1, or 2");
  const int ne = events.size(), ns = stations.size(), off = 4 * ne;
  const bool locate = solver_mode == "loc1d" || solver_mode == "loc3d";
  const int n = off + (locate ? 0 : g.size());
  const auto used = observed_rays(data, ne, stations);
  if (traced.size() != events.size() * stations.size())
    throw std::runtime_error("Incomplete full-linearization ray array");
  for (int index : used)
    if (!finite_ray(traced[index]) || traced[index].dv.size() != g.v.size() ||
        traced[index].length.size() != g.v.size())
      throw std::runtime_error("Invalid full-linearization ray: " +
          ray_identity_context(events, stations, index / ns, index % ns));
  const auto weights = stage_weights(c, data);
  Vec residual(data.size());
  for (size_t q = 0; q < data.size(); ++q)
    residual[q] = data[q].value - prediction(data[q], traced, events, ns);
  const auto cutoff = residual_cutoffs(data, residual);
  auto exact_output = [](const std::string &path) {
    auto stream = output(path);
    stream << std::setprecision(17);
    return stream;
  };
  auto matrix = exact_output(prefix + "_matrix.csv");
  matrix << "observation_row,matrix_row,entry,column,value,weighted_value\n";
  auto rows = exact_output(prefix + "_rows.csv");
  rows << "observation_row,matrix_row,i,j,station,station_j_index,type,observed,"
          "predicted,residual,stage,stage_multiplier,prior_multiplier,robust_cutoff_s,"
          "robust_multiplier,event_distance_km,distance_multiplier,combined_multiplier,"
          "active,omission_reason,weighted_rhs";
  data.write_header(rows, "observation_");
  rows << '\n';
  auto suppressed = exact_output(prefix + "_suppressed.csv");
  suppressed << "observation_row,column,unmasked_value,i_path_length_km,j_path_length_km,reason\n";
  Vec squared_norm(n, 0);
  FullLinearizationCounts counts;
  counts.observations = data.size();
  for (size_t q = 0; q < data.size(); ++q) {
    const auto &d = data[q];
    const auto weight = observation_weight(c, solver_mode, weights, stage, d,
                                         residual[q], cutoff[d.type], events);
    const auto row = observation_row(d, traced, g, ne, ns, locate);
    const long long matrix_row = weight.active() ? static_cast<long long>(counts.active++) : -1;
    const double multiplier = weight.active() ? weight.combined : 0;
    if (!std::isfinite(weight.combined) || !std::isfinite(residual[q]))
      throw std::runtime_error("Nonfinite full-linearization weight/residual at observation " + std::to_string(q));
    for (size_t entry = 0; entry < row.size(); ++entry) {
      const auto &v = row[entry];
      const double weighted = v.val * multiplier;
      matrix << q << ',' << matrix_row << ',' << entry << ',' << v.col << ','
             << v.val << ',' << weighted << '\n';
      if (weight.active()) squared_norm[v.col] += weighted * weighted;
    }
    rows << q << ',' << matrix_row << ',' << d.i << ',' << d.j << ',' << d.k << ','
         << (d.j < 0 ? -1 : second_station(d)) << ',' << d.type << ',' << d.value << ','
         << prediction(d, traced, events, ns) << ',' << residual[q] << ',' << stage << ','
         << weight.stage << ',' << weight.prior << ',' << cutoff[d.type] << ','
         << weight.robust << ',' << weight.event_distance << ',' << weight.distance << ','
         << weight.combined << ',' << weight.active() << ',' << weight.omission << ','
         << residual[q] * multiplier;
    data.write_metadata(rows, q);
    rows << '\n';
    // Preserve all nonzero model terms suppressed by either assembly rule.
    // Together with matrix.csv this reconstructs the unmasked local derivative.
    if (!locate) {
      const auto &a = traced[d.i * ns + d.k];
      const Ray *b = d.j >= 0 ? &traced[d.j * ns + second_station(d)] : nullptr;
      for (int k = 0; k < g.size(); ++k) {
        double value = -a.dv[k] * g.v[k];
        if (b) value += b->dv[k] * g.v[k];
        const bool masked = b && std::abs(a.length[k] - b->length[k]) < 0.005;
        if (value != 0 && (masked || std::abs(value) <= 1e-14)) {
          suppressed << q << ',' << off + k << ',' << value << ',' << a.length[k] << ',';
          if (b) suppressed << b->length[k];
          suppressed << ',' << (masked ? "dd_length_difference_below_0.005_km" :
                                "coefficient_at_or_below_1e-14") << '\n';
          ++counts.suppressed;
        }
      }
    }
  }
  Matrix smoothing(n);
  if (!locate) smooth(smoothing, g, off, c.get("smoothing"));
  counts.smoothing = smoothing.rhs.size();
  auto smoothing_matrix = exact_output(prefix + "_smoothing_matrix.csv");
  smoothing_matrix << "row,matrix_row,entry,column,weighted_value\n";
  auto smoothing_rows = exact_output(prefix + "_smoothing_rows.csv");
  smoothing_rows << "row,matrix_row,weighted_rhs\n";
  for (size_t row = 0; row < smoothing.rhs.size(); ++row) {
    smoothing_rows << row << ',' << counts.active + row << ',' << smoothing.rhs[row] << '\n';
    for (size_t entry = smoothing.offsets[row]; entry < smoothing.offsets[row + 1]; ++entry) {
      const int column = smoothing.columns[entry];
      const double value = smoothing.values[entry];
      smoothing_matrix << row << ',' << counts.active + row << ','
                       << entry - smoothing.offsets[row] << ',' << column << ',' << value << '\n';
      squared_norm[column] += value * value;
    }
  }
  auto columns = exact_output(prefix + "_columns.csv");
  columns << "column,parameter,event,node,x,y,z,reference_value,parameter_unit,"
             "squared_column_norm,column_scale,unscaled_damping_coefficient";
  csv_metadata_header(columns, events.front().metadata, "source_");
  columns << '\n';
  auto scaling = [&](int column) {
    const double scale = squared_norm[column] > 1e-20 ?
                         1 / std::sqrt(squared_norm[column]) : 1;
    columns << ',' << squared_norm[column] << ',' << scale << ',' << c.get("damping") / scale;
  };
  const char *parameters[] = {"x", "y", "z", "t"};
  for (int event = 0; event < ne; ++event)
    for (int axis = 0; axis < 4; ++axis) {
      const auto &e = events[event];
      const int column = 4 * event + axis;
      columns << column << ',' << parameters[axis] << ',' << event << ",-1,"
              << e.p[0] << ',' << e.p[1] << ',' << e.p[2] << ','
              << (axis == 3 ? e.t : e.p[axis]) << ',' << (axis == 3 ? "s" : "km");
      scaling(column);
      csv_metadata_values(columns, e.metadata);
      columns << '\n';
    }
  if (!locate)
    for (int k = 0; k < int(g.z.size()); ++k)
      for (int j = 0; j < int(g.y.size()); ++j)
        for (int i = 0; i < int(g.x.size()); ++i) {
          const int node = g.id(i, j, k), column = off + node;
          columns << column << ",q,-1," << node << ',' << g.x[i] << ',' << g.y[j]
                  << ',' << g.z[k] << ",0,dimensionless";
          scaling(column);
          for (size_t field = 0; field < events.front().metadata.size(); ++field) columns << ',';
          columns << '\n';
        }
  const auto status = write_ray_status(prefix + "_rays.csv", events, stations, traced, &used);
  auto info = exact_output(prefix + "_info.csv");
  info << "key,value\nsolver_mode," << solver_mode << "\nstage," << stage
       << "\nstage_basis," << csv_quote(stage_basis)
       << "\nweight_point,saved event/model state; residual and distance weights recomputed here"
       << "\nweight_interpretation,row multipliers; their squares enter the least-squares objective"
       << "\nparameterization,source x/y/z/t followed by delta log slowness"
       << "\ncolumn_scaling,ordered squared entries before damping; duplicates are not coalesced"
       << "\ndamping," << c.get("damping")
       << "\nobservations," << counts.observations << "\nactive_data_rows," << counts.active
       << "\nsmoothing_rows," << counts.smoothing << "\ncolumns," << n
       << "\nsuppressed_nonzero_model_entries," << counts.suppressed
       << "\nobserved_rays," << used.size() << "\nray_status_failures," << status.first
       << "\nnoise_covariance,not specified by this export; catalog differences share their constituent picks"
       << "\nconstraints,source-domain bounds and nonlinear active sets are not part of this linear operator"
       << "\nresolution_scope,conditional on these rays and fixed weights/masks; not a convergence certificate\n";
  return counts;
}

void linearize_full(const Config &c, const std::string &dir, const std::string &mode,
                    int explicit_stage = -1) {
  const std::string prefix = dir + "/" + mode + "_full_linearization";
  for (const char *suffix : {"_matrix.csv", "_rows.csv", "_suppressed.csv", "_columns.csv",
                            "_smoothing_matrix.csv", "_smoothing_rows.csv", "_rays.csv", "_info.csv"})
    if (std::filesystem::exists(prefix + suffix))
      throw std::runtime_error("Preserve existing full-linearization export: " + prefix + suffix);
  int stage = explicit_stage;
  std::string stage_basis = "explicit command argument (zero based)";
  if (stage == -1) {
    const auto history = csv_table(dir + "/" + mode + "_history.csv");
    auto column = std::find(history.header.begin(), history.header.end(), "stage");
    if (history.rows.empty() || column == history.header.end())
      throw std::runtime_error("Full linearization requires a history stage or an explicit stage");
    stage = csv_int(history.rows.back()[column - history.header.begin()]);
    stage_basis = "last recorded history stage; weights recomputed at saved final state";
  }
  if (stage < 0 || stage > 2)
    throw std::runtime_error("Full linearization stage must be 0, 1, or 2");
  const std::string solver_mode = mode == "standard" || mode == "loc1d" || mode == "loc3d" ? mode : "dd";
  auto events = read_events(dir + "/" + mode + "_events.csv");
  auto stations = read_events(dir + "/stations.csv");
  auto data = observations(dir + "/observations.csv", events, stations,
                           !authoritative_input(c, dir) && authoritative_geometry(c, dir));
  const auto used = observed_rays(data, events.size(), stations);
  if (authoritative_input(c, dir)) validate_identities(events, stations, data);
  else if (authoritative_geometry(c, dir)) validate_identities(events, stations, data, true);
  const auto g = read_grid(dir + "/" + mode + "_grid.csv");
  // Retain failed local/initializer flags in the identified ray table. Finite
  // derivatives are required; an exported operator is not declared accurate.
  const auto traced = rays(g, events, stations, c, true, &used, nullptr, false);
  const auto counts = write_full_linearization(c, prefix, solver_mode, stage, stage_basis,
                                               events, stations, data, g, traced);
  std::cout << "Exported " << counts.observations << " identified full rows ("
            << counts.active << " active), " << counts.smoothing
            << " smoothing rows at " << mode << " stage " << stage << '\n';
}
