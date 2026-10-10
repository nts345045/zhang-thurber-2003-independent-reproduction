// Invented CSV fixtures plus an optional saved authoritative input roundtrip.
// No travel times, observations from providers, or inversions are generated.
#ifdef NDEBUG
#error "Streaming checks require assertions"
#endif
#define main tomography_main
#include "../src/main.cpp"
#undef main
#include <cassert>
#include <sys/resource.h>

template <class F> void expect_rejection(F f) {
  bool failed = false;
  try { f(); } catch (const std::exception &) { failed = true; }
  assert(failed);
}
void save_observations(const std::string &path, const ObservationSet &data) {
  auto f = output(path);
  f << std::setprecision(17) << "i,j,station,type,value";
  data.write_header(f); f << '\n';
  for (size_t q=0; q<data.size(); ++q) {
    const auto &d=data[q];
    f << d.i << ',' << d.j << ',' << d.k << ',' << d.type << ',' << d.value;
    data.write_metadata(f,q); f << '\n';
  }
}
int main(int argc, char **argv) {
  if (argc != 2 && argc != 3)
    throw std::runtime_error("Usage: check_streaming_observations OUT_DIR [SAVED_INPUT_DIR]");
  std::string dir=argv[1];
  std::filesystem::create_directories(dir);
  std::vector<Event> events;
  for (int i=0;i<3;++i)
    events.push_back({{double(i),0,2},0,{{"event_resource_id","smi:invented/event"+std::to_string(i)},
                                      {"origin_resource_id","smi:invented/origin"+std::to_string(i)}}});
  Metadata station{{"network_code","XX"},{"station_code","INVENTED"},{"location_code",""},
                   {"channel_code","HHZ"},{"channel_seed_id","XX.INVENTED..HHZ"},
                   {"channel_fdsn_source_id","FDSN:XX_INVENTED__H_H_Z"},
                   {"metadata_epoch_start","1980-01-01T00:00:00Z"},{"metadata_epoch_end",""}};
  std::vector<Event> stations{{{0,0,0},0,station},{{1,0,0},0,station}};
  set_metadata(stations[1].metadata,"metadata_epoch_start","1990-01-01T00:00:00Z");
  set_metadata(stations[0].metadata,"metadata_epoch_end","1990-01-01T00:00:00Z");
  ObservationSet native;
  for (int type=0;type<3;++type)
    for (int i=0;i<3;++i)
      for (int k=0;k<2;++k) {
        int j=type ? (i+1)%3 : -1;
        native.rows.push_back({i,j,k,type,(i+1.)/(k+3.)+type/7.});
        native.native_metadata.push_back(simulation_metadata(events,stations,i,j,k,type));
      }
  for (const auto &field:native.native_metadata[0]) native.metadata_header.push_back(field.first);
  save_observations(dir+"/invented.csv",native);
  // This small identified fixture also supports an independent legacy/current
  // one-step solver comparison. Its times above are explicitly invented.
  save_observations(dir+"/observations.csv",native);
  write_events(events,dir+"/initial_events.csv");
  write_events(events,dir+"/truth_events.csv");
  write_events(stations,dir+"/stations.csv");
  Grid g; g.x={-2,4}; g.y={-2,2}; g.z={-1,4}; g.v.assign(g.size(),5);
  write_grid(g,dir+"/initial_grid.csv");
  write_grid(g,dir+"/truth_grid.csv");
  {
    auto c=output(dir+"/fixture.cfg");
    c << "authoritative_geometry 1\nray_spacing 1\nray_iterations 180\n"
         "ray_initializer 0\niterations 1\nstage_length 1\nsmoothing 1\n"
         "damping 0.1\npair_distance 20\n";
  }
  auto compact=observations(dir+"/invented.csv",events,stations,true);
  auto generic=observations(dir+"/invented.csv");
  assert(sizeof(Datum)==40);
  assert(compact.size()==18 && compact.rows.capacity()==18 && compact.native_metadata.empty());
  validate_identities(events,stations,compact,true);
  validate_identities(events,stations,generic,true);
  assert(observed_rays(compact,3,stations)==observed_rays(generic,3,stations));
  for (size_t q=0;q<compact.size();++q) {
    const auto &a=compact[q], &b=generic[q];
    assert(a.i==b.i && a.j==b.j && a.k==b.k && a.type==b.type && a.value==b.value &&
           a.a_priori_weight==b.a_priori_weight && a.station_j==b.station_j);
  }
  save_observations(dir+"/compact_roundtrip.csv",compact);
  auto expanded=csv_table(dir+"/compact_roundtrip.csv"), original=csv_table(dir+"/invented.csv");
  assert(expanded.header==original.header && expanded.rows==original.rows);
  // Reject each mismatched field, including valid-empty location and end epoch.
  for (size_t field=0;field<native.metadata_header.size();++field) {
    auto bad=native;
    bad.native_metadata[1][field].second+="wrong";
    save_observations(dir+"/bad.csv",bad);
    expect_rejection([&]{observations(dir+"/bad.csv",events,stations,true);});
  }
  auto bad=native;
  bad.metadata_header.push_back("pick_i_resource_id");
  for (auto &m:bad.native_metadata) m.push_back({"pick_i_resource_id","smi:invented/pick"});
  save_observations(dir+"/bad.csv",bad);
  expect_rejection([&]{observations(dir+"/bad.csv",events,stations,true);});
  bad=native; bad[0].i=3; save_observations(dir+"/bad.csv",bad);
  expect_rejection([&]{observations(dir+"/bad.csv",events,stations,true);});
  auto changed=stations; set_metadata(changed[0].metadata,"metadata_epoch_start","wrong");
  expect_rejection([&]{validate_identities(events,changed,compact,true);});
  expect_rejection([&]{validate_identities(events,stations,compact,false);});
  // A large repeated invented fixture exercises the actual streaming parser,
  // not a specialized layout. Values are declared arbitrary numbers, not rays.
  const size_t stress_rows=100000;
  {
    auto f=output(dir+"/invented_stress.csv");
    f << "i,j,station,type,value"; native.write_header(f); f << '\n';
    for (size_t q=0;q<stress_rows;++q) {
      size_t r=q%native.size(); const auto &d=native[r];
      f << d.i << ',' << d.j << ',' << d.k << ',' << d.type << ',' << d.value;
      native.write_metadata(f,r); f << '\n';
    }
  }
  auto stress=observations(dir+"/invented_stress.csv",events,stations,true);
  assert(stress.size()==stress_rows && stress.rows.capacity()==stress_rows && stress.native_metadata.empty());
  validate_identities(events,stations,stress,true);
  rusage usage{}; getrusage(RUSAGE_SELF,&usage);
  auto summary=output(dir+"/summary.json");
  summary << "{\n  \"invented_rows\": 18,\n  \"rejected_metadata_fields\": 18,\n"
          << "  \"stress_rows\": " << stress.size() << ",\n  \"numeric_datum_bytes\": " << sizeof(Datum)
          << ",\n  \"stress_numeric_capacity_bytes\": " << stress.rows.capacity()*sizeof(Datum)
          << ",\n  \"synthetic_peak_rss_kib\": " << usage.ru_maxrss;
  if (argc==3) {
    std::string source=argv[2];
    auto real_events=read_events(source+"/initial_events.csv"), real_stations=read_events(source+"/stations.csv");
    auto real=observations(source+"/observations.csv");
    validate_identities(real_events,real_stations,real);
    auto support=observed_rays(real,real_events.size(),real_stations);
    save_observations(dir+"/real_roundtrip.csv",real);
    summary << ",\n  \"saved_real_rows\": " << real.size() << ",\n  \"saved_real_unique_rays\": " << support.size();
  }
  summary << ",\n  \"status\": \"passed\",\n  \"inversions_run\": false\n}\n";
}
