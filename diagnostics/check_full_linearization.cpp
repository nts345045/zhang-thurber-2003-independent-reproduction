// Invented assembly arrays test export equality, not ray-tracing accuracy.
#ifdef NDEBUG
#error "Compile the full-linearization checks with assertions enabled"
#endif
#define main dd_program_main
#include "../src/main.cpp"
#undef main
#include <cassert>

double number(const CsvTable &t, const Strings &row, const std::string &key) {
  auto found = std::find(t.header.begin(), t.header.end(), key);
  assert(found != t.header.end());
  return csv_double(row[found - t.header.begin()]);
}
std::string field(const CsvTable &t, const Strings &row, const std::string &key) {
  auto found = std::find(t.header.begin(), t.header.end(), key);
  assert(found != t.header.end());
  return row[found - t.header.begin()];
}

// Frozen pre-refactor assembly: independent of the maintained helper/exporter.
Matrix reference_assembly(const Config &c, const std::string &mode, int stage,
                          const ObservationSet &data, const std::vector<Event> &events,
                          const std::vector<Ray> &rays, const Grid &g, int ns,
                          Vec &w, Vec &residual) {
  const int ne = events.size(), off = 4 * ne;
  const bool locate = mode == "loc1d";
  const auto weights = stage_weights(c, data);
  Matrix a(off + (locate ? 0 : g.size()));
  Vec bytype[3];
  residual.resize(data.size()); w.assign(data.size(), 0);
  for (size_t q = 0; q < data.size(); ++q) {
    const auto &d = data[q];
    double predicted = events[d.i].t + rays[d.i * ns + d.k].time;
    if (d.j >= 0) predicted -= events[d.j].t + rays[d.j * ns + second_station(d)].time;
    residual[q] = d.value - predicted;
    bytype[d.type].push_back(std::abs(residual[q]));
  }
  double cutoff[3];
  for (int t = 0; t < 3; ++t) {
    auto &v = bytype[t];
    if (v.empty()) { cutoff[t] = 1; continue; }
    std::nth_element(v.begin(), v.begin() + v.size() / 2, v.end());
    cutoff[t] = std::max(0.01, 6 * 1.4826 * v[v.size() / 2]);
  }
  for (size_t q = 0; q < data.size(); ++q) {
    const auto &d = data[q];
    if (mode == "standard" && d.type != 0) continue;
    double weight = mode == "standard" ? 1 : weights[stage][d.type];
    weight *= d.a_priori_weight;
    double z = residual[q] / cutoff[d.type];
    weight *= std::pow(std::max(0., 1 - z * z), 2);
    if (d.j >= 0) {
      double distance = norm(events[d.i].p - events[d.j].p);
      weight *= std::pow(std::max(0., 1 - std::pow(distance / c.get("pair_distance"), 2)), 2);
    }
    if (weight < 1e-12) continue;
    w[q] = weight;
    const auto &first = rays[d.i * ns + d.k];
    const Ray *second = d.j >= 0 ? &rays[d.j * ns + second_station(d)] : nullptr;
    Row row;
    for (int axis = 0; axis < 3; ++axis) row.push_back({4 * d.i + axis, first.source[axis]});
    row.push_back({4 * d.i + 3, 1});
    if (second) {
      for (int axis = 0; axis < 3; ++axis) row.push_back({4 * d.j + axis, -second->source[axis]});
      row.push_back({4 * d.j + 3, -1});
    }
    if (!locate) for (int k = 0; k < g.size(); ++k) {
      double value = -first.dv[k] * g.v[k];
      if (second) {
        value += second->dv[k] * g.v[k];
        if (std::abs(first.length[k] - second->length[k]) < 0.005) value = 0;
      }
      if (std::abs(value) > 1e-14) row.push_back({off + k, value});
    }
    a.add(row, residual[q], weight);
  }
  if (!locate) smooth(a, g, off, c.get("smoothing"));
  return a;
}

int main(int argc, char **argv) {
  const std::string dir = argc > 1 ? argv[1] : "tmp/full_linearization_checks/fixture";
  std::filesystem::create_directories(dir);
  { auto config = output(dir + "/config.cfg");
    config << "smoothing 2\ndamping 0.1\npair_distance 10\nray_spacing 1\nray_iterations 180\n"; }
  Config config(dir + "/config.cfg");
  config.v["stage1_precise_weight"] = 0; // Preserve explicitly omitted stages too.
  Grid g; g.x = {0, 20}; g.y = {0, 2}; g.z = {0, 2}; g.v.assign(g.size(), 6);
  std::vector<Event> events{{{{0, 0, 1}}, .01}, {{{1, 0, 1}}, -.03}, {{{11, 0, 1}}, 0}};
  for (size_t i = 0; i < events.size(); ++i)
    events[i].metadata = {{"event_resource_id", "fixture:event" + std::to_string(i)},
                          {"origin_resource_id", "fixture:origin" + std::to_string(i)}};
  Metadata channel{{"network_code", "XX"}, {"station_code", "FIX"}, {"location_code", ""},
    {"channel_code", "HHZ"}, {"channel_seed_id", "XX.FIX..HHZ"},
    {"channel_fdsn_source_id", "FDSN:XX_FIX__H_H_Z"},
    {"metadata_epoch_start", "1984-01-01"}, {"metadata_epoch_end", "1990-01-01"}};
  std::vector<Event> stations{{{{0, 0, 0}}, 0, channel}, {{{0, 0, 0}}, 0, channel}};
  set_metadata(stations[1].metadata, "metadata_epoch_start", "1990-01-01");
  set_metadata(stations[1].metadata, "metadata_epoch_end", "");
  std::vector<Ray> rays(events.size() * stations.size());
  for (size_t index = 0; index < rays.size(); ++index) {
    auto &r = rays[index];
    r.time = .2 + .031 * index;
    r.source = {{.01 * index, -.02 * index, .04 * index}};
    r.path = {events[index / stations.size()].p, stations[index % stations.size()].p};
    r.dv.resize(g.size()); r.length.resize(g.size()); r.converged = index != 3;
    for (int k = 0; k < g.size(); ++k) {
      r.dv[k] = k == 2 ? 1e-17 * (index + 1) : -.001 * (index + k + 1);
      r.length[k] = .1 + (k == 0 ? .001 : .006) * index;
    }
  }
  ObservationSet data;
  data.rows = {{0, -1, 0, 0, 0}, {1, -1, 1, 0, 0, .25}, {2, -1, 0, 0, 0, 0},
    {1, 0, 0, 1, 0, .8, 1}, {2, 0, 0, 1, 0, 1, 1}, {0, 1, 0, 1, 0, 1, 1},
    {1, 0, 0, 2, 0, 1, 1}, {2, 1, 0, 2, 0, 1, 1}, {1, -1, 0, 0, 0, 1e-12}};
  const Vec errors{.02, .03, .01, .01, .02, 1000, 0, 0, 0};
  for (size_t q = 0; q < data.size(); ++q) {
    auto &d = data[q]; d.value = prediction(d, rays, events, stations.size()) + errors[q];
    Metadata m;
    for (const auto &v : stations[d.k].metadata)
      m.push_back(v);
    m.push_back({"metadata_epoch_j_start", d.j < 0 ? "" : "1990-01-01"});
    m.push_back({"metadata_epoch_j_end", ""});
    m.push_back({"pick_i_resource_id", "fixture:pick" + std::to_string(d.i)});
    m.push_back({"pick_j_resource_id", d.j < 0 ? "" : "fixture:pick" + std::to_string(d.j)});
    m.push_back({"note", q == 0 ? "comma, quote \" and\nnewline" : ""});
    data.native_metadata.push_back(m);
  }
  for (const auto &v : data.native_metadata[0]) data.metadata_header.push_back(v.first);
  size_t cases = 0, entries_checked = 0;
  for (const std::string mode : {"dd", "standard", "loc1d"}) for (int stage = 0; stage < 3; ++stage) {
    const std::string prefix = dir + "/" + mode + std::to_string(stage);
    auto counts = write_full_linearization(config, prefix, mode, stage, "fixture explicit",
                                            events, stations, data, g, rays);
    Vec weights, residual;
    const auto expected = reference_assembly(config, mode, stage, data, events, rays, g,
                                               stations.size(), weights, residual);
    auto rows = csv_table(prefix + "_rows.csv"), matrix = csv_table(prefix + "_matrix.csv"),
         smooth_rows = csv_table(prefix + "_smoothing_rows.csv"),
         smooth_matrix = csv_table(prefix + "_smoothing_matrix.csv"),
         columns = csv_table(prefix + "_columns.csv"), suppressed = csv_table(prefix + "_suppressed.csv");
    assert(rows.rows.size() == data.size() && columns.rows.size() == size_t(expected.n));
    Matrix exported(expected.n);
    for (size_t q = 0; q < rows.rows.size(); ++q) {
      const auto &r = rows.rows[q];
      assert(number(rows, r, "observation_row") == double(q));
      assert(number(rows, r, "residual") == residual[q]);
      assert(number(rows, r, "active") == (weights[q] != 0));
      for (size_t field_index = 0; field_index < data.metadata_header.size(); ++field_index)
        assert(field(rows, r, "observation_" + data.metadata_header[field_index]) ==
               data.native_metadata[q][field_index].second);
      Row row;
      for (const auto &v : matrix.rows) if (number(matrix, v, "observation_row") == double(q)) {
        assert(number(matrix, v, "weighted_value") == number(matrix, v, "value") * weights[q]);
        if (weights[q] != 0) row.push_back({int(number(matrix, v, "column")), number(matrix, v, "weighted_value")});
      }
      if (weights[q] != 0) {
        assert(number(rows, r, "matrix_row") == double(exported.rhs.size()));
        exported.add(row, number(rows, r, "weighted_rhs"));
      } else assert(number(rows, r, "matrix_row") == -1);
    }
    for (size_t q = 0; q < smooth_rows.rows.size(); ++q) {
      Row row;
      for (const auto &v : smooth_matrix.rows) if (number(smooth_matrix, v, "row") == double(q))
        row.push_back({int(number(smooth_matrix, v, "column")), number(smooth_matrix, v, "weighted_value")});
      exported.add(row, number(smooth_rows, smooth_rows.rows[q], "weighted_rhs"));
    }
    assert(exported.offsets == expected.offsets && exported.columns == expected.columns &&
           exported.values == expected.values && exported.rhs == expected.rhs);
    Vec norm2(expected.n, 0);
    for (size_t i = 0; i < expected.values.size(); ++i)
      norm2[expected.columns[i]] += expected.values[i] * expected.values[i];
    for (int k = 0; k < expected.n; ++k) {
      double scale = norm2[k] > 1e-20 ? 1 / std::sqrt(norm2[k]) : 1;
      assert(number(columns, columns.rows[k], "squared_column_norm") == norm2[k]);
      assert(number(columns, columns.rows[k], "column_scale") == scale);
      assert(number(columns, columns.rows[k], "unscaled_damping_coefficient") == config.get("damping") / scale);
    }
    if (mode == "loc1d") assert(suppressed.rows.empty());
    else {
      assert(!suppressed.rows.empty());
      for (const auto &v : suppressed.rows) {
        const int q = number(suppressed, v, "observation_row"), k = number(suppressed, v, "column") - 4 * events.size();
        const auto &d = data[q];
        double expected_value = -rays[d.i * stations.size() + d.k].dv[k] * g.v[k];
        if (d.j >= 0) expected_value += rays[d.j * stations.size() + second_station(d)].dv[k] * g.v[k];
        assert(number(suppressed, v, "unmasked_value") == expected_value);
      }
    }
    assert(counts.active + counts.smoothing == expected.rhs.size());
    ++cases; entries_checked += expected.values.size();
  }
  // Exercise the real CLI dispatcher on a tiny homogeneous physical fixture.
  // The nine exact comparisons above deliberately supplied invented ray arrays.
  write_grid(g, dir + "/initial_grid.csv");
  write_events(events, dir + "/initial_events.csv");
  write_events(stations, dir + "/stations.csv");
  {
    auto stream = output(dir + "/observations.csv");
    stream << "i,j,station,type,value,station_j";
    data.write_header(stream); stream << '\n';
    for (size_t q = 0; q < data.size(); ++q) {
      const auto &d = data[q];
      stream << d.i << ',' << d.j << ',' << d.k << ',' << d.type << ',' << d.value << ',' << d.station_j;
      data.write_metadata(stream, q); stream << '\n';
    }
  }
  char program[] = "dd", command[] = "linearize_full", mode[] = "initial", stage[] = "0";
  std::string config_path = dir + "/config.cfg", input_dir = dir;
  char *arguments[] = {program, command, config_path.data(), input_dir.data(), mode, stage};
  assert(dd_program_main(6, arguments) == 0);
  assert(csv_table(dir + "/initial_full_linearization_rows.csv").rows.size() == data.size());
  assert(dd_program_main(6, arguments) == 1); // Never overwrite a retained export.
  write_grid(g, dir + "/dd_grid.csv");
  write_events(events, dir + "/dd_events.csv");
  { auto stream = output(dir + "/dd_history.csv"); stream << "iteration,stage\n17,2\n"; }
  char final_mode[] = "dd"; arguments[4] = final_mode;
  assert(dd_program_main(5, arguments) == 0);
  const auto final_rows = csv_table(dir + "/dd_full_linearization_rows.csv");
  for (const auto &row : final_rows.rows) assert(number(final_rows, row, "stage") == 2);
  auto result = output(dir + "/checks.json");
  result << "{\"assembly_cases\":" << cases << ",\"ordered_entries_checked\":" << entries_checked
         << ",\"bitwise_matrix_rhs_column_scale_equal\":true,\"all_native_metadata_equal\":true,"
            "\"cli_explicit_and_history_stages\":true,\"existing_export_rejected\":true,"
            "\"scope\":\"invented arrays plus tiny homogeneous CLI fixture; all stages and DD/standard/fixed-model modes\"}\n";
  std::cout << cases << " exact full-assembly/export comparisons passed\n";
}
