// Invented geometry and native-style identifiers only; no provider records.
#define main tomography_main
#include "../src/main.cpp"
#undef main
#include <omp.h>

int main(int argc, char **argv) {
  if (argc > 1 && std::string(argv[1]) == "--solver")
    return tomography_main(argc - 1, argv + 1);
  if (argc != 4) return 2;
  const std::string dir = argv[1];
  const int batch = std::stoi(argv[2]), threads = std::stoi(argv[3]);
  omp_set_dynamic(0); omp_set_num_threads(threads);
  auto checks = output(dir + "/checks.csv");
  checks << "name,passed\n";
  int failures = 0;
  auto check = [&](const std::string &name, bool value) {
    checks << name << ',' << value << std::endl; failures += !value;
  };
  Grid g; g.x = {-2, 0, 2}; g.y = {-2, 2}; g.z = {-1, 0, 2};
  g.v.resize(g.size());
  for (int k = 0; k < int(g.z.size()); ++k)
    for (int j = 0; j < int(g.y.size()); ++j)
      for (int i = 0; i < int(g.x.size()); ++i)
        g.v[g.id(i,j,k)] = 5 + .12*g.x[i] + .08*g.y[j] + .2*g.z[k];
  std::vector<P> sources{{-.831,-.721,.333}, {-2,-.5,.65}, {.1,-.9,1.1}, {0,.3,-1}};
  P a{.9,.7,-.35};
  std::vector<P> receivers{a, {-1.25,1.1,.65}, a, {-.5,-1,.75}, {.4,-.4,.3}, {1.1,-.2,.1}};
  std::vector<Event> events, stations;
  for (size_t i=0; i<sources.size(); ++i)
    events.push_back({sources[i], 0, {{"event_resource_id", "smi:local/invented/event/"+std::to_string(i)},
      {"origin_resource_id", "smi:local/invented/origin/"+std::to_string(i)},
      {"scope", "Invented fixture, no provider observations"}}});
  for (size_t k=0; k<receivers.size(); ++k) {
    const auto code = std::to_string(k);
    stations.push_back({receivers[k], 0, {{"network_code", "XX"}, {"station_code", "TEST"+code},
      {"location_code", ""}, {"channel_code", "EHZ"}, {"channel_seed_id", "XX.TEST"+code+"..EHZ"},
      {"channel_fdsn_source_id", "FDSN:XX_TEST"+code+"__E_H_Z"},
      {"metadata_epoch_start", "2000-01-01T00:00:00Z"}, {"metadata_epoch_end", ""}}});
  }
  const std::vector<std::pair<int,int>> samples{{0,0},{1,1},{2,2},{3,3},{0,4},{1,0},
    {2,1},{3,2},{0,3},{1,4},{2,4},{3,1},{0,5},{1,5},{2,3},{3,0}};
  write_events(events, dir+"/initial_events.csv");
  write_events(stations, dir+"/stations.csv");
  write_grid(g, dir+"/initial_grid.csv");
  auto cfg = output(dir+"/fixture.cfg");
  cfg << "ray_initializer 1\nfmm_spacing 0.25\nray_spacing 0.2\nray_iterations 1000\n";
  if (batch >= 0) cfg << "raycheck_receiver_batch " << batch << '\n';
  cfg.close();
  Config config(dir+"/fixture.cfg");
  auto obs = output(dir+"/observations.csv");
  obs << "i,j,station,type,value,fixture_observation\n";
  auto sample = output(dir+"/ray_samples.csv"); sample << "event,station\n";
  for (size_t n=0; n<samples.size(); ++n) {
    const auto s = samples[n];
    obs << s.first << ",-1," << s.second << ",0,1,invented_" << n << '\n';
    sample << s.first << ',' << s.second << '\n';
  }
  obs.close(); sample.close();
  raycheck(config, dir, "initial");
  const auto times = csv_table(dir+"/initial_ray_convergence.csv");
  const auto derivatives = csv_table(dir+"/initial_ray_derivatives.csv");
  check("all_ordered_samples_written", times.rows.size()==samples.size());
  check("first_eight_FD_support_omits_only_domain_crossings", derivatives.rows.size()==20);
#ifndef BASELINE
  const Vec invalid{-1,.5,NAN,INFINITY,-INFINITY,double(std::numeric_limits<int>::max())+1};
  for (size_t i=0; i<invalid.size(); ++i) {
    Config bad = config; bad.v["raycheck_receiver_batch"] = invalid[i]; bool rejected=false;
    try { raycheck(bad, dir+"/absent", "initial"); }
    catch (const std::runtime_error &error) {
      rejected=std::string(error.what()).find("raycheck_receiver_batch")!=std::string::npos;
    }
    check("direct_invalid_value_"+std::to_string(i)+"_before_input_access",rejected);
  }
  check("INT_MAX_checked_before_size_cast",checked_raycheck_receiver_batch(std::numeric_limits<int>::max())==size_t(std::numeric_limits<int>::max()));
#endif
  // A bad native receiver must retain its original event/channel context.
  stations[1].p = {10,0,0}; write_events(stations, dir+"/stations.csv");
  std::string message;
  try { raycheck(config,dir,"initial"); }
  catch (const std::runtime_error &error) { message=error.what(); }
  output(dir+"/identified_failure.txt") << message << '\n';
  check("native_field_failure_identified",message.find("event 1 event_resource_id=smi:local/invented/event/1")!=std::string::npos &&
    message.find("native receiver 1 channel_seed_id=XX.TEST1..EHZ")!=std::string::npos);
  stations[1].p = receivers[1]; write_events(stations,dir+"/stations.csv");
  return failures ? 1 : 0;
}
