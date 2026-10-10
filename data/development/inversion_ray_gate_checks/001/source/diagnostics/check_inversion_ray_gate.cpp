// Invented geometry only: test rejection before inverse use, not flag relabeling.
#ifdef NDEBUG
#error "Checks require assertions"
#endif
#define main tomography_main
#include "../src/main.cpp"
#undef main
#include <cassert>

const std::string &cell(const CsvTable &table, size_t row, const std::string &name) {
  auto column = std::find(table.header.begin(), table.header.end(), name);
  assert(column != table.header.end());
  return table.rows.at(row).at(size_t(column - table.header.begin()));
}

int main(int argc, char **argv) {
  if (argc != 2) throw std::runtime_error("Usage: check_inversion_ray_gate NEW_OUTPUT_DIR");
  const std::string dir = argv[1];
  if (std::filesystem::exists(dir)) throw std::runtime_error("Use fresh output");
  std::filesystem::create_directories(dir);
  auto configuration = output(dir + "/fixture.cfg");
  configuration << "authoritative_geometry 1\nray_spacing 0.5\nray_iterations 1000\n"
      "ray_initializer 0\nseed 2003\nnoise 0.04\nstation_noise 0.3\n"
      "time_quantum 0.01\nlocation_noise 0.6\npair_distance 20\n"
      "iterations 2\nstage_length 1\nsmoothing 1\ndamping 0.1\n";
  configuration.close(); Config c(dir + "/fixture.cfg");
  Grid g; g.x = {-2, 4}; g.y = {-2, 2}; g.z = {-1, 5}; g.v.assign(g.size(), 5);
  std::vector<Event> events{
      {{.2, .1, 2}, 0, {{"event_resource_id", "smi:invented/event0"}, {"origin_resource_id", "smi:invented/origin0"}}},
      {{1.2, -.2, 3}, 0, {{"event_resource_id", "smi:invented/event1"}, {"origin_resource_id", "smi:invented/origin1"}}}};
  Metadata metadata{{"network_code", "XX"}, {"station_code", "MOCK"}, {"location_code", ""}, {"channel_code", "HHZ"},
      {"channel_seed_id", "XX.MOCK..HHZ"}, {"channel_fdsn_source_id", "FDSN:XX_MOCK__H_H_Z"},
      {"metadata_epoch_start", "1980-01-01T00:00:00Z"}, {"metadata_epoch_end", "1990-01-01T00:00:00Z"}};
  std::vector<Event> stations{{{0, 0, 0}, 0, metadata}, {{1, 1, 0}, 0, metadata}};
  set_metadata(stations[1].metadata, "metadata_epoch_start", "1990-01-01T00:00:00Z");
  set_metadata(stations[1].metadata, "metadata_epoch_end", "");
  write_events(events, dir + "/truth_events.csv"); write_events(stations, dir + "/stations.csv");
  write_grid(g, dir + "/truth_grid.csv"); write_grid(g, dir + "/initial_grid.csv");
  simulate(c, dir);
  auto initial = read_events(dir + "/initial_events.csv");
  auto successful = rays(g, initial, stations, c, true);
  std::vector<int> sparse{3, 0};
  inversion_ray_gate(dir + "/success", g, initial, stations, successful, sparse, false, true);
  assert(!std::filesystem::exists(dir + "/success_ray_status.csv"));
  for (int reason = 0; reason < 9; ++reason) {
    auto altered = successful;
    if (reason == 0) altered[3].converged = false;
    if (reason == 1) altered[3].time = NAN;
    if (reason == 2) altered[3].path.clear();
    if (reason == 3) altered[3].path[1][0] = g.x.back() + 1;
    if (reason == 4) altered[3].path.front()[0] = std::nextafter(initial[1].p[0], INFINITY);
    if (reason == 5) altered[3].path.back()[0] = std::nextafter(stations[1].p[0], INFINITY);
    if (reason == 6) { altered[3].initialization_attempted = true; altered[3].initialization_succeeded = false; }
    if (reason == 7) altered[3].dv.clear();
    if (reason == 8) altered[3].length.clear();
    const std::string prefix = dir + "/altered_" + std::to_string(reason);
    bool rejected = false;
    try { inversion_ray_gate(prefix, g, initial, stations, altered, sparse, false, true); }
    catch (const std::exception &error) {
      rejected = true;
      const std::string text = error.what();
      for (const char *native : {"smi:invented/event1", "smi:invented/origin1", "XX.MOCK..HHZ", "FDSN:XX_MOCK__H_H_Z"})
        assert(text.find(native) != std::string::npos);
    }
    assert(rejected);
    const auto status = csv_table(prefix + "_ray_status.csv"), failed = csv_table(prefix + "_ray_failures.csv");
    assert(status.rows.size() == 2 && failed.rows.size() == 1);
    assert(cell(status, 0, "event") == "1" && cell(status, 1, "event") == "0");
    assert(cell(failed, 0, "source_event_resource_id") == "smi:invented/event1");
    assert(cell(failed, 0, "receiver_location_code").empty() && cell(failed, 0, "receiver_metadata_epoch_end").empty());
    assert(cell(failed, 0, "receiver_metadata_epoch_start") == "1990-01-01T00:00:00Z");
  }
  bool rejected = false;
  try { inversion_ray_gate(dir + "/missing_initializer", g, initial, stations, successful, sparse, true, true); }
  catch (const std::exception &) { rejected = true; }
  assert(rejected && csv_table(dir + "/missing_initializer_ray_failures.csv").rows.size() == 2);
  auto action_only = rays(g, initial, stations, c, false);
  inversion_ray_gate(dir + "/action_only", g, initial, stations, action_only, sparse, false, false);
  assert(!std::filesystem::exists(dir + "/action_only_ray_status.csv"));
  // Compare this successful nonlinear location run with the parent executable.
  invert(c, dir, "loc1d");
  assert(csv_table(dir + "/loc1d_history.csv").rows.size() == 2);
  assert(!std::filesystem::exists(dir + "/loc1d_failed_forward_context.csv"));
  Grid gradient = g;
  for (int k = 0; k < 2; ++k) for (int j = 0; j < 2; ++j) for (int i = 0; i < 2; ++i)
    gradient.v[gradient.id(i, j, k)] = 5 + .2 * gradient.z[k];
  const auto fixture = [&](const std::string &name, const Grid &model, const Config &cfg) {
    const std::string target = dir + "/" + name; std::filesystem::create_directories(target);
    for (const char *file : {"stations.csv", "observations.csv", "initial_events.csv", "truth_grid.csv"})
      std::filesystem::copy_file(dir + "/" + file, target + "/" + file);
    write_grid(model, target + "/initial_grid.csv");
    auto settings = output(target + "/run.cfg");
    for (const auto &entry : cfg.v) settings << entry.first << ' ' << entry.second << '\n';
    return target;
  };
  const auto failure = [&](const std::string &name, const Grid &model, Config cfg, const std::string &phase) {
    const std::string target = fixture(name, model, cfg);
    bool blocked = false;
    try { invert(cfg, target, "dd"); } catch (const std::exception &) { blocked = true; }
    assert(blocked);
    const auto context = csv_table(target + "/dd_failed_forward_context.csv");
    assert(context.rows.size() == 1 && cell(context, 0, "phase") == phase);
    assert(csv_table(target + "/dd_failed_forward_ray_status.csv").rows.size() == 4);
    assert(!std::filesystem::exists(target + "/dd_grid.csv") && !std::filesystem::exists(target + "/dd_events.csv"));
    assert(csv_table(target + "/dd_history.csv").rows.empty());
    const auto accepted = read_events(target + "/dd_last_accepted_events.csv");
    for (size_t i = 0; i < initial.size(); ++i) assert(accepted[i].p == initial[i].p && accepted[i].t == initial[i].t);
    assert(read_grid(target + "/dd_last_accepted_grid.csv").v == model.v);
    const auto evaluated = read_events(target + "/dd_failed_forward_events.csv");
    const auto evaluated_grid = read_grid(target + "/dd_failed_forward_grid.csv");
    if (phase == "line_search_trial") {
      assert(cell(context, 0, "derivatives_evaluated") == "0");
      bool changed = evaluated_grid.v != model.v;
      for (size_t i = 0; i < initial.size(); ++i) changed |= evaluated[i].p != initial[i].p || evaluated[i].t != initial[i].t;
      assert(changed && csv_table(target + "/dd_matrix_preflight.csv").rows.size() == 1);
    } else {
      assert(evaluated_grid.v == model.v && csv_table(target + "/dd_matrix_preflight.csv").rows.empty());
    }
    return target;
  };
  Config zero = c; zero.v["ray_iterations"] = 0;
  failure("current_failure", gradient, zero, "current_model");
  failure("trial_failure", g, zero, "line_search_trial");
  Config final = zero; final.v["iterations"] = 0;
  failure("final_failure", gradient, final, "final_model");
  // A census still collects failed local flags without an inverse solve.
  Config census = zero; census.v["matrix_preflight_only"] = 1;
  const auto preflight = fixture("preflight", gradient, census);
  invert(census, preflight, "dd");
  assert(csv_table(preflight + "/dd_matrix_preflight.csv").rows.size() == 1);
  assert(csv_table(preflight + "/dd_history.csv").rows.empty());
  assert(!std::filesystem::exists(preflight + "/dd_failed_forward_context.csv"));
  const auto preflight_status = csv_table(preflight + "/dd_preflight_ray_status.csv");
  assert(preflight_status.rows.size() == 4 && cell(preflight_status, 0, "ray_converged") == "0");
  auto exact = initial; exact[0].p[0] = std::nextafter(exact[0].p[0], INFINITY);
  exact[0].t = std::nextafter(exact[0].t, INFINITY);
  write_events(exact, dir + "/precision_events.csv", 17);
  auto loaded = read_events(dir + "/precision_events.csv");
  assert(loaded[0].p == exact[0].p && loaded[0].t == exact[0].t);
  g.v[0] = std::nextafter(g.v[0], INFINITY); write_grid(g, dir + "/precision_grid.csv", 17);
  assert(read_grid(dir + "/precision_grid.csv").v == g.v);
  output(dir + "/summary.json") << "{\"status\":\"passed\",\"scope\":\"invented geometry only\","
      "\"altered_ray_causes\":9,\"current_trial_final_rejections\":3,\"preflight_keeps_failed_local_flags\":true,"
      "\"native_sparse_order_and_epoch_metadata\":true,\"accepted_and_failed_states_separate\":true,"
      "\"failure_states_round_trip_binary64\":true,\"real_inversions_run\":false}\n";
}
