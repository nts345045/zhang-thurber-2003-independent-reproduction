#pragma once
// Read-only hooks included after the frozen solver and audit identity globals.
// No returned value or captured arithmetic enters the optimizer.
bool curvature_capture_active = false;
std::ofstream curvature_pairs, curvature_components, curvature_geometry;
std::ofstream curvature_cuts, curvature_initialization, curvature_seed_metadata;
std::ofstream curvature_memory_events;
std::vector<int> curvature_memory_ids;
std::vector<Vec> curvature_memory_s, curvature_memory_y;

const std::vector<int> curvature_selected_iterations = {
    33, 34, 47, 48, 433, 434, 435, 988, 989, 990, 991, 992, 993, 994,
    995, 996, 997, 998, 999};

void curvature_id(std::ostream &file, int iteration) {
  file << csv_quote(audit_run) << ',' << csv_quote(audit_observation) << ',' << iteration;
}

std::string curvature_ids(const std::vector<int> &ids, int iteration, bool ages) {
  std::ostringstream text;
  for (size_t i = 0; i < ids.size(); ++i) {
    if (i) text << ';';
    text << (ages ? iteration - ids[i] : ids[i]);
  }
  return text.str();
}

void curvature_open(const std::string &out) {
  const std::vector<std::pair<std::ofstream *, std::string>> files = {
      {&curvature_pairs, "curvature_pairs.csv"},
      {&curvature_components, "curvature_components.csv"},
      {&curvature_geometry, "curvature_selected_geometry.csv"},
      {&curvature_cuts, "curvature_selected_cuts.csv"},
      {&curvature_initialization, "curvature_initialization.csv"},
      {&curvature_seed_metadata, "curvature_seed_metadata.csv"},
      {&curvature_memory_events, "curvature_memory_events.csv"}};
  for (const auto &item : files)
    if (std::ifstream(out + '/' + item.second).good())
      throw std::runtime_error("Curvature capture refuses to overwrite output");
  for (const auto &item : files) {
    item.first->open(out + '/' + item.second);
    if (!*item.first) throw std::runtime_error("Cannot open curvature capture output");
    *item.first << std::setprecision(17);
  }
  curvature_pairs << "run_id,observation_index,iteration,update,retained,computed_sy,"
                     "threshold,s_squared,y_squared,s_norm,y_norm,normalized_sy,"
                     "step,base_action_s,accepted_action_s,directional_slope,armijo_rhs_s,"
                     "two_loop_metric_scale,memory_before_ids,memory_after_ids,"
                     "memory_before_ages,memory_after_ages,memory_after_size,components\n";
  curvature_components << "run_id,observation_index,iteration,node,s_x,s_y,s_z,y_x,y_y,y_z,"
                          "rounded_displacement_x,rounded_displacement_y,rounded_displacement_z\n";
  curvature_geometry << "run_id,observation_index,iteration,state,node,is_endpoint,x,y,z,"
                        "gradient_x,gradient_y,gradient_z,q_x,q_y,q_z\n";
  curvature_cuts << "run_id,observation_index,iteration,state,selection,selected_node,edge_end_node,"
                    "axis,plane_index,plane_value,axis_delta,axis_test_pass,parameter,parameter_test_pass,used,"
                    "a_x,a_y,a_z,b_x,b_y,b_z\n";
  curvature_initialization << "run_id,observation_index,kind,node,x,y,z\n";
  curvature_seed_metadata << "run_id,observation_index,field_time_s,success,descent_steps,fallback_steps,message\n";
  curvature_memory_events << "run_id,observation_index,iteration,reason,previous_ids,previous_ages\n";
}

void curvature_flush() {
  for (auto file : {&curvature_pairs, &curvature_components, &curvature_geometry,
                    &curvature_cuts, &curvature_initialization, &curvature_seed_metadata,
                    &curvature_memory_events}) {
    file->flush();
    if (!*file) throw std::runtime_error("Incomplete curvature capture output");
  }
}

void curvature_initial_path(const char *kind, const std::vector<P> &path) {
  if (!curvature_capture_active) return;
  for (size_t node = 0; node < path.size(); ++node) {
    curvature_initialization << csv_quote(audit_run) << ',' << csv_quote(audit_observation)
                             << ',' << kind << ',' << node;
    for (double value : path[node]) curvature_initialization << ',' << value;
    curvature_initialization << '\n';
  }
}

void curvature_seed(const first_arrival::Candidate &seed) {
  if (!curvature_capture_active) return;
  curvature_initial_path("raw_fmm_seed", seed.path);
  curvature_seed_metadata << csv_quote(audit_run) << ',' << csv_quote(audit_observation)
                          << ',' << seed.field_time << ',' << seed.success << ',' << seed.descent_steps
                          << ',' << seed.fallback_steps << ',' << csv_quote(seed.message) << '\n';
}

void curvature_begin(const std::vector<P> &path) {
  if (!curvature_capture_active) return;
  curvature_memory_ids.clear(); curvature_memory_s.clear(); curvature_memory_y.clear();
  curvature_initial_path("post_resampling_and_merge", path);
}

void curvature_memory_clear(int iteration, const char *reason) {
  if (!curvature_capture_active) return;
  curvature_id(curvature_memory_events, iteration);
  curvature_memory_events << ',' << reason << ',' << curvature_ids(curvature_memory_ids, iteration, false)
                          << ',' << curvature_ids(curvature_memory_ids, iteration, true) << '\n';
  curvature_memory_ids.clear(); curvature_memory_s.clear(); curvature_memory_y.clear();
}

// Reproduce only the existing cut predicates for logging. No segment action is
// evaluated here. All grid-plane candidates, including discarded ones, remain.
void curvature_edge_cuts(int iteration, const char *state, const char *selection,
                         size_t selected, size_t end, const Grid &g, const std::vector<P> &path) {
  const P &a = path[end-1], &b = path[end];
  const P d = b - a;
  const Vec *axes[] = {&g.x, &g.y, &g.z};
  for (int axis = 0; axis < 3; ++axis)
    for (size_t plane = 0; plane < axes[axis]->size(); ++plane) {
      const bool axis_ok = std::abs(d[axis]) > 1e-12;
      const double t = axis_ok ? ((*axes[axis])[plane] - a[axis]) / d[axis] : NAN;
      const bool interior = axis_ok && t > 1e-10 && t < 1 - 1e-10;
      curvature_id(curvature_cuts, iteration);
      curvature_cuts << ',' << state << ',' << selection << ',' << selected << ',' << end << ','
                     << axis << ',' << plane << ',' << (*axes[axis])[plane] << ',' << d[axis] << ',' << axis_ok << ',';
      if (axis_ok) curvature_cuts << t;
      curvature_cuts << ',' << interior << ',' << interior;
      for (double value : a) curvature_cuts << ',' << value;
      for (double value : b) curvature_cuts << ',' << value;
      curvature_cuts << '\n';
    }
}

void curvature_selected(int iteration, const Grid &g, const std::vector<P> &before,
                         const std::vector<P> &after, const Vec &gradient,
                         const Vec &next_gradient, const Vec &q) {
  if (std::find(curvature_selected_iterations.begin(), curvature_selected_iterations.end(), iteration) ==
      curvature_selected_iterations.end()) return;
  const Vec *axes[] = {&g.x, &g.y, &g.z};
  for (bool next : {false, true}) {
    const char *state = next ? "accepted" : "base";
    const auto &path = next ? after : before;
    const auto &grad = next ? next_gradient : gradient;
    size_t closest = 0, worst = 1;
    double distance = INFINITY, greatest = -1;
    for (size_t node = 0; node < path.size(); ++node) {
      const bool endpoint = node == 0 || node+1 == path.size();
      curvature_id(curvature_geometry, iteration);
      curvature_geometry << ',' << state << ',' << node << ',' << endpoint;
      for (double value : path[node]) curvature_geometry << ',' << value;
      for (const Vec *values : {&grad, &q})
        for (int axis = 0; axis < 3; ++axis) {
          curvature_geometry << ',';
          if (!endpoint) curvature_geometry << (*values)[3*(node-1)+axis];
        }
      curvature_geometry << '\n';
      if (endpoint) continue;
      for (int axis = 0; axis < 3; ++axis) {
        const double value = std::abs(grad[3*(node-1)+axis]);
        if (value > greatest) { greatest = value; worst = node; }
        for (size_t plane = 1; plane+1 < axes[axis]->size(); ++plane) {
          const double gap = std::abs(path[node][axis] - (*axes[axis])[plane]);
          if (gap < distance) { distance = gap; closest = node; }
        }
      }
    }
    if (closest)
      for (size_t end : {closest, closest+1})
        curvature_edge_cuts(iteration, state, "closest_internal_plane", closest, end, g, path);
    for (size_t end : {worst, worst+1})
      curvature_edge_cuts(iteration, state, "largest_gradient_component", worst, end, g, path);
  }
}

void curvature_pair(int iteration, int update, const Grid &g,
                    const std::vector<P> &before, const std::vector<P> &after,
                    const Vec &gradient, const Vec &next_gradient, const Vec &q,
                    const Vec &s, const Vec &y, double sy, bool retained,
                    double step, double action, double next_action, double slope, double metric_scale,
                    const std::vector<Vec> &actual_s, const std::vector<Vec> &actual_y) {
  if (!curvature_capture_active) return;
  const size_t dimension = 3*(before.size()-2);
  if (before.size() < 3 || after.size() != before.size() || s.size() != dimension || y.size() != dimension ||
      q.size() != dimension || gradient.size() != dimension || next_gradient.size() != dimension)
    throw std::runtime_error("Curvature capture dimension mismatch");
  const auto previous_ids = curvature_memory_ids;
  if (retained) {
    if (curvature_memory_ids.size() == 8) {
      curvature_memory_ids.erase(curvature_memory_ids.begin());
      curvature_memory_s.erase(curvature_memory_s.begin());
      curvature_memory_y.erase(curvature_memory_y.begin());
    }
    curvature_memory_ids.push_back(iteration);
    curvature_memory_s.push_back(s); curvature_memory_y.push_back(y);
  }
  if (curvature_memory_s != actual_s || curvature_memory_y != actual_y)
    throw std::runtime_error("Captured memory does not equal actual optimizer memory");
  const double ss = dot(s,s), yy = dot(y,y), sn = std::sqrt(ss), yn = std::sqrt(yy);
  curvature_id(curvature_pairs, iteration);
  curvature_pairs << ',' << update << ',' << retained << ',' << sy << ',' << 1e-14 << ',' << ss << ',' << yy
                  << ',' << sn << ',' << yn << ',';
  if (sn > 0 && yn > 0) curvature_pairs << sy / (sn*yn);
  curvature_pairs << ',' << step << ',' << action << ',' << next_action << ',' << slope
                  << ',' << action + 1e-4*step*slope << ',' << metric_scale
                  << ',' << curvature_ids(previous_ids, iteration, false)
                  << ',' << curvature_ids(curvature_memory_ids, iteration, false)
                  << ',' << curvature_ids(previous_ids, iteration, true)
                  << ',' << curvature_ids(curvature_memory_ids, iteration, true)
                  << ',' << actual_s.size() << ',' << dimension << '\n';
  for (size_t node = 1; node+1 < before.size(); ++node) {
    curvature_id(curvature_components, iteration);
    curvature_components << ',' << node;
    for (const Vec *values : {&s, &y})
      for (int axis = 0; axis < 3; ++axis) curvature_components << ',' << (*values)[3*(node-1)+axis];
    for (int axis = 0; axis < 3; ++axis) curvature_components << ',' << after[node][axis] - before[node][axis];
    curvature_components << '\n';
  }
  curvature_selected(iteration, g, before, after, gradient, next_gradient, q);
}
