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
    assert(cell(status, 0, "ray_derivatives_evaluated") == (reason == 7 || reason == 8 ? "0" : "1"));
    assert(cell(status, 0, "source_coordinate_basis").find("failed forward evaluation") != std::string::npos);
    assert(cell(failed, 0, "source_event_resource_id") == "smi:invented/event1");
    assert(cell(failed, 0, "receiver_location_code").empty() && cell(failed, 0, "receiver_metadata_epoch_end").empty());
    assert(cell(failed, 0, "receiver_metadata_epoch_start") == "1990-01-01T00:00:00Z");
    const auto paths = csv_table(prefix + "_ray_paths.csv");
    assert(paths.rows.size() == altered[3].path.size());
    for (size_t node = 0; node < paths.rows.size(); ++node) {
      assert(cell(paths, node, "node") == std::to_string(node));
      assert(cell(paths, node, "source_event_resource_id") == "smi:invented/event1");
      for (int axis = 0; axis < 3; ++axis)
        assert(csv_double(cell(paths, node, std::string(1, "xyz"[axis]))) == altered[3].path[node][axis]);
    }
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
    const auto ray_status = csv_table(target + "/dd_failed_forward_ray_status.csv");
    assert(ray_status.rows.size() == 4);
    for (size_t row = 0; row < ray_status.rows.size(); ++row) {
      assert(cell(ray_status, row, "source_coordinate_basis").find("failed forward evaluation") != std::string::npos);
      assert(cell(ray_status, row, "ray_derivatives_evaluated") == (phase == "line_search_trial" ? "0" : "1"));
      for (const char *axis : {"source_dx", "source_dy", "source_dz"})
        assert(cell(ray_status, row, axis).empty() == (phase == "line_search_trial"));
    }
    assert(!std::filesystem::exists(target + "/dd_grid.csv") && !std::filesystem::exists(target + "/dd_events.csv"));
    assert(csv_table(target + "/dd_history.csv").rows.empty());
    const auto accepted = read_events(target + "/dd_last_accepted_events.csv");
    for (size_t i = 0; i < initial.size(); ++i) assert(accepted[i].p == initial[i].p && accepted[i].t == initial[i].t);
    assert(read_grid(target + "/dd_last_accepted_grid.csv").v == model.v);
    const auto evaluated = read_events(target + "/dd_failed_forward_events.csv");
    const auto evaluated_grid = read_grid(target + "/dd_failed_forward_grid.csv");
    if (phase == "line_search_trial") {
      assert(cell(context, 0, "derivatives_requested") == "0");
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
  // Same original zero-update fixture: trial failure now permits the
  // existing halved steps. Do not impose an unobserved exhaustion outcome.
  int rejected_trial_count = 0, trial_ledger_count = 0;
  bool trial_blocked = false;
  const std::string trial_dir = fixture("trial_backtracking", g, zero);
  std::string trial_error;
  try { invert(zero, trial_dir, "dd"); }
  catch (const std::exception &error) { trial_blocked = true; trial_error = error.what(); }
  const bool trial_exhausted = trial_blocked &&
      trial_error.find("No objective-evaluable trial after local ray rejection") != std::string::npos;
  const bool later_guard_failure = std::filesystem::exists(trial_dir + "/dd_failed_forward_context.csv");
  assert(!trial_blocked || trial_exhausted || later_guard_failure);
  assert(!(trial_exhausted && later_guard_failure));
  std::string trial_outcome = trial_exhausted ? "no_objective_evaluable_trial" : "completed";
  int last_evaluable_count = -1;
  for (int iteration = 0; iteration < int(zero.get("iterations")); ++iteration) {
    const std::string ledger_name = trial_dir + "/dd_iteration_" + std::to_string(iteration) + "_trials.csv";
    if (!std::filesystem::exists(ledger_name)) break;
    const auto ledger = csv_table(ledger_name);
    ++trial_ledger_count;
    assert(!ledger.rows.empty() && ledger.rows.size() <= 12);
    if (iteration == 0) assert(cell(ledger, 0, "status") == "local_stopping_rejected");
    int evaluated_count = 0;
    for (size_t row = 0; row < ledger.rows.size(); ++row) {
      assert(csv_int(cell(ledger, row, "iteration")) == iteration);
      assert(csv_int(cell(ledger, row, "trial")) == int(row));
      assert(csv_double(cell(ledger, row, "step_fraction")) == std::ldexp(1., -int(row)));
      const auto &status = cell(ledger, row, "status");
      if (status == "local_stopping_rejected") {
        ++rejected_trial_count;
        assert(cell(ledger, row, "objective_evaluated") == "0" && cell(ledger, row, "objective_after").empty());
        const std::string prefix = trial_dir + "/dd_rejected_trial_it_" + std::to_string(iteration) + "_ls_" + std::to_string(row);
        assert(cell(ledger, row, "failure_prefix") == prefix);
        const auto context = csv_table(prefix + "_context.csv");
        assert(context.rows.size() == 1 && cell(context, 0, "phase") == "line_search_trial");
        assert(cell(context, 0, "derivatives_requested") == "0");
        const auto ray_status = csv_table(prefix + "_ray_status.csv");
        const auto failures = csv_table(prefix + "_ray_failures.csv");
        assert(ray_status.rows.size() == 4 && !failures.rows.empty());
        for (size_t n = 0; n < failures.rows.size(); ++n)
          assert(cell(failures, n, "reasons") == "local_stopping_failed");
        for (size_t n = 0; n < ray_status.rows.size(); ++n) {
          assert(cell(ray_status, n, "source_coordinate_basis").find("failed forward evaluation") != std::string::npos);
          assert(cell(ray_status, n, "ray_derivatives_evaluated") == "0");
          for (const char *axis : {"source_dx", "source_dy", "source_dz"}) assert(cell(ray_status, n, axis).empty());
          const int event = csv_int(cell(ray_status, n, "event"));
          assert(cell(ray_status, n, "source_event_resource_id") == "smi:invented/event" + std::to_string(event));
          assert(cell(ray_status, n, "receiver_channel_seed_id") == "XX.MOCK..HHZ");
          assert(cell(ray_status, n, "receiver_location_code").empty());
        }
        assert(std::filesystem::exists(prefix + "_ray_paths.csv"));
        const auto accepted = read_events(prefix + "_accepted_events.csv");
        const auto accepted_grid = read_grid(prefix + "_accepted_grid.csv");
        const auto evaluated = read_events(prefix + "_events.csv");
        const auto evaluated_grid = read_grid(prefix + "_grid.csv");
        assert(accepted.size() == initial.size() && evaluated.size() == initial.size());
        bool changed = evaluated_grid.v != accepted_grid.v;
        for (size_t i = 0; i < initial.size(); ++i) {
          changed |= evaluated[i].p != accepted[i].p || evaluated[i].t != accepted[i].t;
          if (iteration == 0) assert(accepted[i].p == initial[i].p && accepted[i].t == initial[i].t);
        }
        assert(changed);
        if (iteration == 0) assert(accepted_grid.v == g.v);
      } else {
        assert(status == "accepted" || status == "objective_rejected");
        ++evaluated_count;
        assert(cell(ledger, row, "objective_evaluated") == "1" && cell(ledger, row, "failure_prefix").empty());
        const double before = csv_double(cell(ledger, row, "objective_before"));
        const double after = csv_double(cell(ledger, row, "objective_after"));
        if (status == "accepted") assert(after <= before && row + 1 == ledger.rows.size());
        else assert(after > before);
      }
    }
    last_evaluable_count = evaluated_count;
  }
  assert(rejected_trial_count > 0 && trial_ledger_count > 0);
  const auto trial_history = csv_table(trial_dir + "/dd_history.csv");
  if (trial_exhausted) {
    assert(last_evaluable_count == 0);
    assert(trial_history.rows.size() + 1 == size_t(trial_ledger_count));
    assert(!std::filesystem::exists(trial_dir + "/dd_grid.csv") && !std::filesystem::exists(trial_dir + "/dd_events.csv"));
  } else if (later_guard_failure) {
    // An accepted action-only trial can fail the next derivative-requesting
    // current/final guard. That fatal state is not trial exhaustion.
    assert(trial_blocked && trial_history.rows.size() == size_t(trial_ledger_count));
    const auto context = csv_table(trial_dir + "/dd_failed_forward_context.csv");
    assert(context.rows.size() == 1 && cell(context, 0, "derivatives_requested") == "1");
    const auto phase = cell(context, 0, "phase");
    assert(phase == "current_model" || phase == "final_model");
    trial_outcome = phase + "_fatal";
    if (phase == "current_model")
      assert(csv_int(cell(context, 0, "iteration")) == trial_ledger_count);
    assert(!trial_history.rows.empty() && csv_double(cell(trial_history, trial_history.rows.size()-1, "step_fraction")) > 0);
    const auto ray_status = csv_table(trial_dir + "/dd_failed_forward_ray_status.csv");
    const auto failures = csv_table(trial_dir + "/dd_failed_forward_ray_failures.csv");
    assert(ray_status.rows.size() == 4 && !failures.rows.empty());
    for (size_t row = 0; row < ray_status.rows.size(); ++row) {
      assert(cell(ray_status, row, "source_coordinate_basis").find("failed forward evaluation") != std::string::npos);
      assert(cell(ray_status, row, "ray_derivatives_evaluated") == "1");
      for (const char *axis : {"source_dx", "source_dy", "source_dz"})
        assert(std::isfinite(csv_double(cell(ray_status, row, axis))));
      const int event = csv_int(cell(ray_status, row, "event"));
      assert(cell(ray_status, row, "source_event_resource_id") == "smi:invented/event" + std::to_string(event));
      assert(cell(ray_status, row, "receiver_channel_seed_id") == "XX.MOCK..HHZ");
      assert(cell(ray_status, row, "receiver_location_code").empty());
    }
    const auto accepted = read_events(trial_dir + "/dd_last_accepted_events.csv");
    const auto evaluated = read_events(trial_dir + "/dd_failed_forward_events.csv");
    assert(accepted.size() == initial.size() && evaluated.size() == initial.size());
    for (size_t i = 0; i < accepted.size(); ++i)
      assert(accepted[i].p == evaluated[i].p && accepted[i].t == evaluated[i].t);
    assert(read_grid(trial_dir + "/dd_last_accepted_grid.csv").v == read_grid(trial_dir + "/dd_failed_forward_grid.csv").v);
    assert(std::filesystem::exists(trial_dir + "/dd_failed_forward_ray_paths.csv"));
    assert(!std::filesystem::exists(trial_dir + "/dd_grid.csv") && !std::filesystem::exists(trial_dir + "/dd_events.csv"));
  } else {
    assert(!trial_blocked);
    assert(trial_history.rows.size() == size_t(trial_ledger_count));
    assert(std::filesystem::exists(trial_dir + "/dd_grid.csv") && std::filesystem::exists(trial_dir + "/dd_events.csv"));
  }
  Config final = zero; final.v["iterations"] = 0;
  failure("final_failure", gradient, final, "final_model");
  const auto exception = fixture("worker_exception", g, c);
  auto outside = initial; outside[1].p[0] = g.x.back() + 1;
  write_events(outside, exception + "/initial_events.csv");
  bool exception_rejected = false;
  try { invert(c, exception, "dd"); } catch (const std::exception &) { exception_rejected = true; }
  assert(exception_rejected);
  const auto exception_status = csv_table(exception + "/dd_failed_forward_ray_status.csv");
  assert(exception_status.rows.size() == 4);
  for (size_t row : {size_t(2), size_t(3)}) {
    assert(cell(exception_status, row, "source_event_resource_id") == "smi:invented/event1");
    assert(cell(exception_status, row, "ray_path_points") == "0");
    assert(cell(exception_status, row, "ray_derivatives_evaluated") == "0");
    for (const char *axis : {"source_dx", "source_dy", "source_dz"}) assert(cell(exception_status, row, axis).empty());
  }
  assert(!std::filesystem::exists(exception + "/dd_grid.csv"));
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
      "\"altered_ray_causes\":9,\"fatal_current_and_final_cases\":2,\"rejected_trial_count\":" << rejected_trial_count
      << ",\"trial_ledger_count\":" << trial_ledger_count << ",\"trial_exhausted\":" << (trial_exhausted ? "true" : "false")
      << ",\"trial_fixture_outcome\":\"" << trial_outcome << "\""
      << ",\"preflight_keeps_failed_local_flags\":true,"
      "\"native_sparse_order_and_epoch_metadata\":true,\"accepted_and_failed_states_separate\":true,"
      "\"failure_states_round_trip_binary64\":true,\"real_inversions_run\":false}\n";
}
