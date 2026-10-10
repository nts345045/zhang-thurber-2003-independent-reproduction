// Invented homogeneous geometry tests production dispatch/cache/index behavior.
// No catalog records or claimed real station identifiers are invented here.
#define main tomography_main
#include "../src/main.cpp"
#undef main

int main(int argc, char **argv) {
  if (argc > 2 && std::string(argv[1]) == "--solver")
    return tomography_main(argc-1, argv+1);
  if (argc != 2) throw std::runtime_error("Usage: check_forward_integration OUT_DIR");
  std::string dir = argv[1];
  auto checks = output(dir + "/checks.csv");
  checks << "test,value,tolerance,passed\n";
  int failed = 0;
  auto check = [&](const std::string &name, double value, double tolerance) {
    bool pass = std::isfinite(value) && value <= tolerance;
    checks << name << ',' << value << ',' << tolerance << ',' << pass << std::endl;
    failed += !pass;
  };
  Grid g;
  g.x = g.y = g.z = {-2, 2};
  g.v.assign(g.size(), 5);
  P a{-.831, -.721, .333}, b{1.123, .423, -.212};
  output(dir + "/fixture.cfg").close();
  Config c(dir + "/fixture.cfg");
  c.v = {{"ray_spacing", .2}, {"ray_iterations", 1000},
         {"ray_initializer", 1}, {"fmm_spacing", .5},
         {"iterations", 1}, {"stage_length", 1}, {"smoothing", 1},
         {"damping", .1}, {"pair_distance", 10}};
  auto config_file = output(dir + "/fixture.cfg");
  for (const auto &entry : c.v) config_file << entry.first << ' ' << entry.second << '\n';
  config_file.close();
  ForwardFields cache;
  auto first = configured_trace(g, a, b, c, cache);
  check("homogeneous_time", std::abs(first.time - norm(b-a)/5), 1e-12);
  check("homogeneous_source", norm(first.source - (a-b)*(1/(5*norm(a-b)))), 1e-10);
  check("exact_endpoints", first.path.front() == a && first.path.back() == b ? 0 : 1, 0);
  check("successful_initialization", first.initialization_attempted && first.initialization_succeeded ? 0 : 1, 0);
  check("continuous_action_selection", std::abs(first.time-std::min(first.direct_seed_time, first.fmm_seed_time)), 0);
  const auto *field = &cache.get(g, b, .5);
  P changed_source = a; changed_source[0] += .1;
  configured_trace(g, changed_source, b, c, cache);
  check("reuse_for_changed_source", &cache.get(g,b,.5) == field ? 0 : 1, 0);

  // Coincident placements have distinct indices/metadata in the solver. A
  // single receiver field can serve both without combining their records.
  std::vector<Event> events{{a,0,{{"fixture_event", "invented_a"}}},
                            {changed_source,0,{{"fixture_event", "invented_b"}}}};
  std::vector<Event> stations{{b,0,{{"fixture_receiver", "invented_epoch_a"}}},
                              {b,0,{{"fixture_receiver", "invented_epoch_b"}}}};
  std::vector<int> used{0,1,3};
  auto traced = rays(g, events, stations, c, true, &used, &cache);
  check("coincident_receiver_reuse", cache.fields.size() == 1 ? 0 : 1, 0);
  check("native_indices_remain_distinct", traced.size() == 4 &&
        traced[0].initialization_succeeded && traced[1].initialization_succeeded &&
        traced[3].initialization_succeeded && !traced[2].initialization_attempted ? 0 : 1, 0);
  check("native_metadata_unchanged", stations[0].metadata[0].second == "invented_epoch_a" &&
        stations[1].metadata[0].second == "invented_epoch_b" ? 0 : 1, 0);
  check("coincident_predictions_equal", std::abs(traced[0].time-traced[1].time), 0);
  Grid changed = g;
  for (auto &v : changed.v) v *= 2;
  auto faster = configured_trace(changed,a,b,c,cache);
  check("velocity_change_invalidates_field", std::abs(2*faster.initializer_field_time-first.initializer_field_time), 1e-12);
  check("velocity_change_updates_action", std::abs(2*faster.time-first.time), 1e-12);
  size_t old_nodes = cache.get(changed,b,.5).node_count();
  changed.x.back() += .5;
  check("axis_change_invalidates_field", cache.get(changed,b,.5).node_count() != old_nodes ? 0 : 1, 0);
  old_nodes = cache.get(changed,b,.5).node_count();
  check("spacing_change_invalidates_field", cache.get(changed,b,.25).node_count() != old_nodes ? 0 : 1, 0);
  P other_receiver = b; other_receiver[0] = std::nextafter(b[0], INFINITY);
  cache.get(changed,other_receiver,.25);
  check("receiver_coordinates_not_rounded", cache.fields.size() == 2 ? 0 : 1, 0);
  Config direct = c; direct.v.erase("ray_initializer");
  auto legacy = configured_trace(g,a,b,direct,cache);
  check("explicit_legacy_dispatch", !legacy.initialization_attempted ? 0 : 1, 0);
  Config no_updates = c; no_updates.v["ray_iterations"] = 0;
  Grid gradient_model = g;
  for (int k=0; k<2; ++k)
    for (int j=0; j<2; ++j)
      for (int i=0; i<2; ++i)
        gradient_model.v[g.id(i,j,k)] = 5+2*g.z[k];
  auto unfinished = configured_trace(gradient_model,a,b,no_updates,cache);
  check("nonconverged_flag_preserved", !unfinished.converged && unfinished.gradient > 1e-7 ? 0 : 1, 0);
  auto coincident = configured_trace(g,b,b,c,cache);
  check("coincident_endpoints", std::abs(coincident.time), 0);
  bool rejected = false;
  std::vector<P> bad_seed{changed_source,b};
  try { trace(g,a,b,.2,1000,true,&bad_seed); }
  catch (const std::runtime_error &) { rejected = true; }
  check("mismatched_seed_rejected", rejected ? 0 : 1, 0);

  // Exercise full CSV output from a one-step manufactured inversion and its
  // configured diagnostics. These fixtures are not manuscript results.
  write_grid(g,dir+"/initial_grid.csv");
  write_grid(g,dir+"/truth_grid.csv");
  write_events(events,dir+"/initial_events.csv");
  write_events(events,dir+"/truth_events.csv");
  write_events(stations,dir+"/stations.csv");
  auto obs = output(dir+"/observations.csv");
  obs << "i,j,station,type,value,fixture_observation\n";
  for (int i=0; i<2; ++i)
    for (int k=0; k<2; ++k)
      obs << i << ",-1," << k << ",0," << norm(stations[k].p-events[i].p)/5+.01
          << ",invented_absolute_" << i << '_' << k << '\n';
  obs << "0,1,0,1," << (norm(b-a)-norm(b-changed_source))/5 << ",invented_difference\n";
  obs.close();
  invert(c,dir,"standard");
  raycheck(c,dir,"initial");
  linearize(c,dir,"standard");
  auto history = csv_table(dir+"/standard_history.csv");
  check("one_inversion_step_saved", history.rows.size() == 1 ? 0 : 1, 0);
  auto residuals = csv_table(dir+"/standard_residuals.csv");
  check("all_observation_residuals_saved", residuals.rows.size() == 5 ? 0 : 1, 0);
  // csv_table validates unique headers and every row's width, including an
  // empty j-side initializer record on absolute observations.
  for (const auto &name : {"initial_ray_convergence.csv", "initial_ray_derivatives.csv",
                           "initial_ray_identifiers.csv", "standard_linearization_rows.csv",
                           "standard_linearization_columns.csv"})
    check(std::string("valid_csv_")+name, csv_table(dir+"/"+name).rows.empty() ? 1 : 0, 0);
  return failed ? 1 : 0;
}
