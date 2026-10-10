// Save the exact original solve and fixed weights once per quality-rejected
// iteration. Trial coordinates may have been clamped, so they do not determine
// the unclamped LSQR increment. No Ray from a rejected trial is used here.
void write_trial_solve(const std::string &prefix, const Config &c, const std::string &mode,
                       int iteration, int stage, const Grid &g, const std::vector<Event> &events,
                       const ObservationSet &data, const Vec &delta, const Vec &residual,
                       const Vec &weights, const LSQRInfo &info, double before, bool locate) {
  const size_t off = 4 * events.size(), n = off + (locate ? 0 : g.v.size());
  if (delta.size() != n || residual.size() != data.size() || weights.size() != data.size())
    throw std::runtime_error("Cannot preserve incomplete original solve");
  require_new_outputs(prefix, {"_accepted_events.csv", "_accepted_grid.csv", "_delta.csv", "_weights.csv", "_context.csv"});
  auto accepted = events;
  for (auto &event : accepted)
    if (!event.metadata.empty())
      set_metadata(event.metadata, "coordinate_basis", "independent accepted inversion state at iteration " + std::to_string(iteration) + "; original unscaled solve recorded separately");
  write_events(accepted, prefix + "_accepted_events.csv", 17);
  write_grid(g, prefix + "_accepted_grid.csv", 17);
  auto increments = output(prefix + "_delta.csv");
  increments << std::setprecision(17) << "parameter_index,parameter_type,event,node,component,increment,reference_x,reference_y,reference_z,reference_t,reference_v";
  csv_metadata_header(increments, accepted.front().metadata, "source_");
  increments << '\n';
  for (size_t index = 0; index < n; ++index) {
    increments << index << ',';
    if (index < off) {
      size_t i = index / 4, component = index % 4;
      increments << "source," << i << ",," << "xyzt"[component] << ',' << delta[index];
      for (double value : events[i].p) increments << ',' << value;
      increments << ',' << events[i].t << ',';
      csv_metadata_values(increments, accepted[i].metadata);
    } else {
      size_t node = index - off, ix = node % g.x.size(), iy = (node / g.x.size()) % g.y.size(), iz = node / (g.x.size() * g.y.size());
      increments << "model,," << node << ",log_slowness," << delta[index] << ','
                 << g.x[ix] << ',' << g.y[iy] << ',' << g.z[iz] << ",," << g.v[node];
      for (size_t field = 0; field < accepted.front().metadata.size(); ++field) increments << ',';
    }
    increments << '\n';
  }
  finish_output(increments, prefix + "_delta.csv");
  auto frozen_weights = output(prefix + "_weights.csv");
  frozen_weights << std::setprecision(17) << "observation_index,i,j,station,station_j,type,value,current_residual,fixed_row_multiplier";
  data.write_header(frozen_weights, "original_");
  frozen_weights << '\n';
  for (size_t q = 0; q < data.size(); ++q) {
    const auto &d = data[q];
    frozen_weights << q << ',' << d.i << ',' << d.j << ',' << d.k << ',' << (d.j < 0 ? -1 : second_station(d))
                   << ',' << d.type << ',' << d.value << ',' << residual[q] << ',' << weights[q];
    data.write_metadata(frozen_weights, q);
    frozen_weights << '\n';
  }
  finish_output(frozen_weights, prefix + "_weights.csv");
  auto info_file = output(prefix + "_context.csv");
  info_file << std::setprecision(17)
      << "mode,iteration,stage,columns,source_columns,model_columns,lsqr_iterations,lsqr_relative_normal_residual,lsqr_converged,objective_before,smoothing_weight,damping_parameter,weight_basis,objective_basis\n"
      << mode << ',' << iteration << ',' << stage << ',' << n << ',' << off << ',' << n - off << ','
      << info.iterations << ',' << info.relative_normal_residual << ',' << info.converged << ',' << before << ','
      << c.get("smoothing") << ',' << c.get("damping")
      << ",stage/robust/distance/prior row multipliers computed at the accepted state and fixed through this line search"
      << ",sum of squared fixed-weight data residuals plus final log-slowness smoothing; damping enters the solve only\n";
  finish_output(info_file, prefix + "_context.csv");
}
