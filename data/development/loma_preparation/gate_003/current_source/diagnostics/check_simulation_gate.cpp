// Invented, homogeneous component fixtures only; no provider data queries.
#ifdef NDEBUG
#error "Simulation checks require assertions"
#endif
#define main tomography_main
#include "../src/main.cpp"
#undef main
#include <cassert>

int main(int argc,char **argv) {
  if (argc!=2) throw std::runtime_error("Usage: check_simulation_gate NEW_OUTPUT_DIR");
  std::string dir=argv[1];
  if (std::filesystem::exists(dir)) throw std::runtime_error("Use a new evidence directory");
  std::filesystem::create_directories(dir);
  auto config=output(dir+"/fixture.cfg");
  config << "authoritative_geometry 1\nray_spacing 0.5\nray_iterations 1000\n"
            "ray_initializer 0\nseed 2003\nnoise 0.04\nstation_noise 0.3\n"
            "time_quantum 0.01\nlocation_noise 0.6\npair_distance 20\n";
  config.close(); Config c(dir+"/fixture.cfg");
  Grid g;g.x={-2,4};g.y={-2,2};g.z={-1,5};g.v.assign(g.size(),5);
  std::vector<Event> events{{{.2,.1,2},0,{{"event_resource_id","smi:invented/event0"},{"origin_resource_id","smi:invented/origin0"}}},
                            {{1.2,-.2,3},0,{{"event_resource_id","smi:invented/event1"},{"origin_resource_id","smi:invented/origin1"}}}};
  Metadata metadata{{"network_code","XX"},{"station_code","MOCK"},{"location_code",""},{"channel_code","HHZ"},
                    {"channel_seed_id","XX.MOCK..HHZ"},{"channel_fdsn_source_id","FDSN:XX_MOCK__H_H_Z"},
                    {"metadata_epoch_start","1980-01-01T00:00:00Z"},{"metadata_epoch_end","1990-01-01T00:00:00Z"}};
  std::vector<Event> stations{{{0,0,0},0,metadata},{{1,1,0},0,metadata}};
  set_metadata(stations[1].metadata,"metadata_epoch_start","1990-01-01T00:00:00Z");
  set_metadata(stations[1].metadata,"metadata_epoch_end","");
  write_events(events,dir+"/truth_events.csv");write_events(stations,dir+"/stations.csv");
  write_grid(g,dir+"/truth_grid.csv");write_grid(g,dir+"/initial_grid.csv");
  output(dir+"/ray_samples.csv") << "event,station\n0,0\n1,1\n";
  raycheck(c,dir,"truth",true);
  assert(!std::filesystem::exists(dir+"/observations.csv"));
  auto identities=csv_table(dir+"/geometry_truth_ray_identifiers.csv");
  assert(identities.rows.size()==2);
  for (const auto *key:{"source_x","receiver_z","source_event_resource_id","source_origin_resource_id",
                        "receiver_channel_seed_id","receiver_channel_fdsn_source_id","receiver_metadata_epoch_start","receiver_metadata_epoch_end"})
    assert(std::find(identities.header.begin(),identities.header.end(),key)!=identities.header.end());
  auto outside=events;outside[1].p[0]=10;
  std::vector<int> used{3};std::string message;
  try { rays(g,outside,stations,c,true,&used); }
  catch (const std::exception &error) { message=error.what(); }
  assert(message.find("event 1")!=std::string::npos && message.find("native receiver 1")!=std::string::npos);
  for (const auto *value:{"smi:invented/event1","smi:invented/origin1","XX.MOCK..HHZ","FDSN:XX_MOCK__H_H_Z","1990-01-01T00:00:00Z"})
    assert(message.find(value)!=std::string::npos);
  output(dir+"/identified_exception.txt") << message << '\n';
  auto failed=rays(g,outside,stations,c,false,nullptr,nullptr,false);
  assert(failed.size()==4 && !std::isfinite(failed[2].time) && !std::isfinite(failed[3].time));
  std::string rejected=dir+"/rejected";std::filesystem::create_directories(rejected);
  bool blocked=false;
  try { simulation_ray_gate(rejected,outside,stations,failed); }
  catch (const std::exception &) { blocked=true; }
  assert(blocked && csv_table(rejected+"/simulation_ray_status.csv").rows.size()==4);
  assert(!std::filesystem::exists(rejected+"/observations.csv"));
  auto successful=rays(g,events,stations,c,false);
  for (int reason=0;reason<3;++reason) {
    auto altered=successful;
    if(reason==0) altered[1].converged=false;
    if(reason==1) {altered[1].initialization_attempted=true;altered[1].initialization_succeeded=false;}
    if(reason==2) altered[1].path[0][0]=NAN;
    std::string path=dir+"/failure_"+std::to_string(reason);std::filesystem::create_directories(path);
    blocked=false;
    try {simulation_ray_gate(path,events,stations,altered);} catch(const std::exception &){blocked=true;}
    assert(blocked && csv_table(path+"/simulation_ray_status.csv").rows.size()==4);
  }
  simulate(c,dir);
  auto raw=csv_table(dir+"/arrivals.csv");
  assert(raw.rows.size()==4 && csv_table(dir+"/observations.csv").rows.size()==8);
  for (const auto *key:{"ray_converged","ray_finite","ray_projected_gradient","ray_initialization_attempted","channel_seed_id","event_i_resource_id"})
    assert(std::find(raw.header.begin(),raw.header.end(),key)!=raw.header.end());
  auto simulated=observations(dir+"/observations.csv",events,stations,true);
  validate_identities(events,stations,simulated,true);
  auto before=csv_table(dir+"/observations.csv");
  blocked=false;try {simulate(c,dir);}catch(const std::exception &){blocked=true;}
  assert(blocked && csv_table(dir+"/observations.csv").rows==before.rows);
  std::string nonconverged=dir+"/nonconverged_simulation";
  std::filesystem::create_directories(nonconverged);
  write_events(events,nonconverged+"/truth_events.csv");write_events(stations,nonconverged+"/stations.csv");
  Grid gradient=g;
  for (int k=0;k<2;++k) for(int j=0;j<2;++j) for(int i=0;i<2;++i)
    gradient.v[gradient.id(i,j,k)]=5+.2*gradient.z[k];
  write_grid(gradient,nonconverged+"/truth_grid.csv");write_grid(g,nonconverged+"/initial_grid.csv");
  Config unfinished=c;unfinished.v["ray_iterations"]=0;
  blocked=false;try {simulate(unfinished,nonconverged);}catch(const std::exception &){blocked=true;}
  assert(blocked && csv_table(nonconverged+"/simulation_ray_status.csv").rows.size()==4);
  for (const auto *name:{"arrivals.csv","observations.csv","initial_events.csv"})
    assert(!std::filesystem::exists(nonconverged+"/"+name));
  c.v["iterations"]=1;c.v["stage_length"]=1;c.v["smoothing"]=1;c.v["damping"]=.1;
  c.v["matrix_preflight_only"]=1;
  invert(c,dir,"dd");
  assert(csv_table(dir+"/dd_preflight_ray_status.csv").rows.size()==4);
  assert(csv_table(dir+"/dd_matrix_preflight.csv").rows.size()==1);
  assert(csv_table(dir+"/dd_history.csv").rows.empty() && !std::filesystem::exists(dir+"/dd_grid.csv"));
  std::string bad_preflight=dir+"/invalid_preflight";std::filesystem::create_directories(bad_preflight);
  for(const auto *name:{"stations.csv","observations.csv","initial_grid.csv"})
    std::filesystem::copy_file(dir+"/"+name,bad_preflight+"/"+name);
  auto invalid_initial=read_events(dir+"/initial_events.csv");invalid_initial[1].p[0]=10;
  write_events(invalid_initial,bad_preflight+"/initial_events.csv");
  blocked=false;try {invert(c,bad_preflight,"dd");}catch(const std::exception &){blocked=true;}
  assert(blocked && csv_table(bad_preflight+"/dd_preflight_ray_status.csv").rows.size()==4);
  assert(csv_table(bad_preflight+"/dd_matrix_preflight.csv").rows.empty());
  assert(!std::filesystem::exists(bad_preflight+"/dd_grid.csv"));
  output(dir+"/summary.json") << "{\n  \"status\": \"passed\",\n  \"fixture\": \"invented homogeneous geometry, four rays and eight simulated rows\",\n"
      "  \"geometry_only_identity_rows\": 2,\n  \"identified_openmp_exception\": true,\n  \"all_failed_records_preserved\": true,\n"
      "  \"local_initializer_and_nonfinite_rejected\": true,\n  \"successful_arrival_flags\": true,\n  \"existing_output_preserved\": true,\n"
      "  \"preflight_all_native_flags\": true,\n  \"invalid_preflight_rejected_before_matrix\": true,\n"
      "  \"real_rays_or_inversions_run\": false\n}\n";
}
