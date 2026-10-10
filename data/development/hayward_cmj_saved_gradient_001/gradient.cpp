// Reevaluate four fixed selected polygons, never trace or optimize a ray.
#define main archived_application_main
#include "src/main.cpp"
#undef main

std::string decimal17(double value) {
  std::ostringstream out;
  out << std::setprecision(17) << value;
  return out.str();
}

void original_fields(std::ofstream &out, const Strings &row) {
  for (size_t k = 0; k < row.size(); ++k)
    out << (k ? "," : "") << csv_quote(row[k]);
}

int main(int argc, char **argv) {
  try {
    if (argc != 6) throw std::runtime_error("gradient GRID PATHS STATUS OUTPUT old|D");
    const Grid grid = read_grid(argv[1]);
    const auto paths = csv_table(argv[2], {"event", "station", "node", "x", "y", "z"});
    const auto status = csv_table(argv[3], {"event", "station"});
    const std::string out = argv[4], variant = argv[5];
    if (variant != "old" && variant != "D") throw std::runtime_error("Invalid variant");
    if (status.rows.size() != 2) throw std::runtime_error("Expected two saved rays");
    const auto column = [&](const std::string &name) {
      auto found = std::find(status.header.begin(), status.header.end(), name);
      if (found == status.header.end()) throw std::runtime_error("Missing status column: " + name);
      return size_t(found - status.header.begin());
    };
    auto values = output(out + "/node_gradients.csv"), checks = output(out + "/norms.csv");
    values << std::setprecision(17); checks << std::setprecision(17);
    original_fields(values, paths.header);
    values << ",variant,is_free,raw_gx,raw_gy,raw_gz,projected_gx,projected_gy,projected_gz\n";
    original_fields(checks, status.header);
    checks << ",variant,diagnostic_path_action,diagnostic_raw_norm,diagnostic_projected_norm,free_components\n";
    size_t consumed = 0;
    int evaluations = 0;
    for (size_t row_index = 0; row_index < status.rows.size(); ++row_index) {
      const auto &saved = status.rows[row_index];
      const int event = csv_int(saved[0]), station = csv_int(saved[1]);
      if (event != (row_index ? 987 : 981) || station != 160)
        throw std::runtime_error("Unexpected native ray ordering");
      std::vector<P> polygon;
      std::vector<const Strings *> records;
      for (const auto &row : paths.rows) {
        if (csv_int(row[0]) != event || csv_int(row[1]) != station) continue;
        if (csv_int(row[2]) != int(polygon.size())) throw std::runtime_error("Unordered path nodes");
        const P point{csv_double(row[3]), csv_double(row[4]), csv_double(row[5])};
        if (!grid.contains(point)) throw std::runtime_error("Saved point outside grid");
        if (!polygon.empty() && point == polygon.back()) throw std::runtime_error("Zero-length edge");
        for (size_t k = 6; k < paths.header.size(); ++k)
          if (row[k] != saved[column(paths.header[k])]) throw std::runtime_error("Native path/status mismatch");
        polygon.push_back(point); records.push_back(&row);
      }
      consumed += polygon.size();
      if (polygon.size() < 2 || polygon.size() != size_t(csv_int(saved[column("ray_path_points")])))
        throw std::runtime_error("Incomplete saved polygon");
      for (int axis = 0; axis < 3; ++axis) {
        const std::string name(1, "xyz"[axis]);
        if (polygon.front()[axis] != csv_double(saved[column("source_" + name)]) ||
            polygon.back()[axis] != csv_double(saved[column("receiver_" + name)]))
          throw std::runtime_error("Saved endpoint mismatch");
      }
      Vec gradient;
      const double action = path_eval(grid, polygon, &gradient);
      ++evaluations;
      const double raw = norm(gradient), projected = projected_ray_gradient(grid, polygon, gradient);
      if (!std::isfinite(action) || !std::isfinite(raw) || !std::isfinite(projected) ||
          std::any_of(gradient.begin(), gradient.end(), [](double x) { return !std::isfinite(x); }))
        throw std::runtime_error("Nonfinite diagnostic gradient");
      if (decimal17(raw) != saved[column("ray_raw_gradient")] ||
          decimal17(projected) != saved[column("ray_projected_gradient")])
        throw std::runtime_error("Recorded 17-digit gradient norm parity failed");
      Vec projected_components = gradient;
      for (auto &x : projected_components) x = -x;
      project_ray_direction(grid, polygon, projected_components);
      for (auto &x : projected_components) x = -x;
      if (norm(projected_components) != projected) throw std::runtime_error("Projection decomposition mismatch");
      original_fields(checks, saved);
      checks << ',' << variant << ',' << action << ',' << raw << ',' << projected << ',' << gradient.size() << '\n';
      for (size_t node = 0; node < polygon.size(); ++node) {
        original_fields(values, *records[node]);
        const bool free = node > 0 && node + 1 < polygon.size();
        values << ',' << variant << ',' << free;
        for (const auto *array : {&gradient, &projected_components})
          for (int axis = 0; axis < 3; ++axis) {
            values << ',';
            if (free) values << (*array)[3 * (node - 1) + axis];
          }
        values << '\n';
      }
    }
    if (consumed != paths.rows.size() || evaluations != 2) throw std::runtime_error("Unexpected evaluation inventory");
    std::cout << "fixed_path_evaluations=2 trace_calls=0 field_constructions=0 norm_parity=passed\n";
    return 0;
  } catch (const std::exception &error) {
    std::cerr << error.what() << '\n';
    return 1;
  }
}
