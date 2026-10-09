// Run from the project root (the fixture and executable stay under tmp):
// TMPDIR="$PWD/tmp" g++ -std=c++17 -O2 -fopenmp diagnostics/check_external_inputs.cpp -lstdc++fs -o tmp/external_input_checks/check
// OMP_NUM_THREADS=2 tmp/external_input_checks/check
#ifdef NDEBUG
#error "External-input component checks require assertions enabled"
#endif
#define main dd_program_main
#include "../src/main.cpp"
#undef main
#include <cassert>

template <class F> void rejects(F f) {
  bool rejected = false;
  try { f(); } catch (const std::exception &) { rejected = true; }
  assert(rejected);
}
int main() {
  const std::string dir = "tmp/external_input_checks/fixture";
  std::filesystem::create_directories(dir);
  std::vector<Event> events{{{{0,0,2}},0,{{"event_resource_id","smi:fixture/event0"},{"origin_resource_id","smi:fixture/origin0"},{"note","comma, quote \" and\nnewline"}}},
                            {{{1,0,2}},0,{{"event_resource_id","smi:fixture/event1"},{"origin_resource_id","smi:fixture/origin1"},{"note",""}}},
                            {{{10000,0,2}},0,{{"event_resource_id","smi:fixture/event2"},{"origin_resource_id","smi:fixture/origin2"},{"note","unused source outside grid"}}}};
  Metadata channel{{"network_code","XX"},{"station_code","TEST"},{"location_code",""},{"channel_code","HHZ"},
                   {"channel_seed_id","XX.TEST..HHZ"},{"channel_fdsn_source_id","FDSN:XX_TEST__H_H_Z"},
                   {"metadata_epoch_start","1984-01-01T00:00:00Z"},{"metadata_epoch_end",""}};
  std::vector<Event> stations{{{{0,0,0}},0,channel},{{{10000,0,0}},0,channel}};
  write_events(events, dir+"/initial_events.csv");
  write_events(events, dir+"/truth_events.csv");
  write_events(stations, dir+"/stations.csv");
  auto reread=read_events(dir+"/initial_events.csv");
  assert(reread[0].metadata==events[0].metadata && reread[1].metadata==events[1].metadata);
  auto moved=reread; moved[0].p[0]+=0.1;
  write_events(moved,dir+"/roundtrip.csv");
  assert(read_events(dir+"/roundtrip.csv")[0].metadata==events[0].metadata);
  std::vector<Datum> data;
  for (int n=0;n<2;n++) {
    int i=n,j=n ? 0:-1;
    Metadata m{{"event_i_resource_id","smi:fixture/event"+std::to_string(i)},
               {"event_j_resource_id",n ? "smi:fixture/event0":""},
               {"origin_i_resource_id","smi:fixture/origin"+std::to_string(i)},
               {"origin_j_resource_id",n ? "smi:fixture/origin0":""},
               {"pick_i_resource_id","smi:fixture/pick"+std::to_string(i)},
               {"pick_j_resource_id",n ? "smi:fixture/pick0":""},
               {"arrival_i_resource_id","smi:fixture/arrival"+std::to_string(i)},
               {"arrival_j_resource_id",n ? "smi:fixture/arrival0":""},
               {"channel_seed_id","XX.TEST..HHZ"},{"channel_fdsn_source_id","FDSN:XX_TEST__H_H_Z"},
               {"metadata_epoch_start","1984-01-01T00:00:00Z"},{"metadata_epoch_end",""},
               {"a_priori_weight","0.25"},{"note","preserve, \"quoted\"\ntext"}};
    data.push_back({i,j,0,n,1,std::move(m)});
  }
  {
    auto f=output(dir+"/observations.csv");
    f << "i,j,station,type,value"; csv_metadata_header(f,data[0].metadata); f << '\n';
    for (const auto &d:data) {
      f << d.i << ',' << d.j << ',' << d.k << ',' << d.type << ',' << d.value;
      csv_metadata_values(f,d.metadata); f << '\n';
    }
  }
  auto loaded=observations(dir+"/observations.csv");
  assert(loaded[0].metadata==data[0].metadata && loaded[0].a_priori_weight==0.25);
  auto used=observed_rays(loaded,events.size(),stations.size());
  assert((used==std::vector<int>{0,2}));
  validate_identities(events,stations,loaded);
  auto bad=loaded; bad[0].metadata[0].second="smi:fixture/wrong-event";
  rejects([&]{validate_identities(events,stations,bad);});
  bad=loaded; bad[1].metadata[7].second="";
  rejects([&]{validate_identities(events,stations,bad);});
  auto no_channel=stations; no_channel[0].metadata.clear();
  rejects([&]{validate_identities(events,no_channel,loaded);});
  bad=loaded; bad[0].j=0;
  rejects([&]{observed_rays(bad,events.size(),stations.size());});
  {
    auto f=output(dir+"/fixture.cfg");
    f << "ray_spacing 1\nray_iterations 180\nauthoritative_ids_required 1\ncatalog_only_dd 1\n";
  }
  Config config(dir+"/fixture.cfg");
  assert(authoritative_input(config,dir));
  auto weights=stage_weights(config,loaded);
  assert(weights[2][0]==0.1 && weights[2][1]==1 && weights[2][2]==0);
  config.v["catalog_only_dd"]=0;
  weights=stage_weights(config,loaded);
  assert(weights[2][0]==0.001 && weights[2][1]==0.01 && weights[2][2]==1);
  config.v["catalog_only_dd"]=1;
  bad=loaded; bad[1].type=2;
  rejects([&]{stage_weights(config,bad);});
  Grid g=grid(); std::fill(g.v.begin(),g.v.end(),6);
  write_grid(g,dir+"/truth_grid.csv");
  auto traced=rays(g,events,stations,config,true,&used);
  assert(traced.size()==6 && traced[1].dv.empty() && traced[4].dv.empty());
  assert(std::abs(traced[0].time-1./3)<1e-12);
  raycheck(config,dir);
  auto mapping=csv_table(dir+"/ray_identifiers.csv");
  assert(mapping.rows.size()==3);
  assert(std::find(mapping.header.begin(),mapping.header.end(),"observation_pick_j_resource_id")!=mapping.header.end());
  assert(std::find(mapping.header.begin(),mapping.header.end(),"receiver_metadata_epoch_end")!=mapping.header.end());
  auto convergence=csv_table(dir+"/ray_convergence.csv");
  assert(convergence.rows.size()==2 && convergence.header.back()=="diagnostic_row");
  char program[]="dd", command[]="linearize", mode[]="truth";
  std::string config_path=dir+"/fixture.cfg", input_dir=dir;
  char *arguments[]={program,command,config_path.data(),input_dir.data(),mode};
  assert(dd_program_main(5,arguments)==0);
  auto linear_rows=csv_table(dir+"/truth_linearization_rows.csv");
  auto linear_columns=csv_table(dir+"/truth_linearization_columns.csv");
  auto linear_matrix=csv_table(dir+"/truth_linearization_matrix.csv");
  assert(linear_rows.rows.size()==1 && linear_columns.rows.size()==4*events.size()+g.size());
  assert(linear_rows.rows[0][1]=="0" && std::abs(csv_double(linear_rows.rows[0][5])-1./3)<1e-11);
  assert(linear_rows.header[7]=="ray_converged" && linear_rows.rows[0][7]=="1");
  assert(csv_double(linear_rows.rows[0][8])<1e-7 && csv_int(linear_rows.rows[0][9])==0);
  assert(std::abs(csv_double(linear_rows.rows[0][10])-1./3)<1e-11);
  assert(std::find(linear_rows.header.begin(),linear_rows.header.end(),"pick_i_resource_id")!=linear_rows.header.end());
  double origin_derivative=0,vertical_derivative=0,log_slowness_sum=0;
  for (const auto &entry:linear_matrix.rows) {
    assert(csv_int(entry[0])==0);
    int column=csv_int(entry[1]); double value=csv_double(entry[2]);
    if (column==3) origin_derivative+=value;
    if (column==2) vertical_derivative+=value;
    if (column>=int(4*events.size())) log_slowness_sum+=value;
  }
  // Prior weight is 0.25, but exported derivatives must remain unweighted.
  assert(origin_derivative==1 && std::abs(vertical_derivative-1./6)<1e-11);
  assert(std::abs(log_slowness_sum-1./3)<1e-11);
  for (size_t column=0;column<linear_columns.rows.size();column++)
    assert(csv_int(linear_columns.rows[column][0])==int(column));
  {
    std::ofstream f(dir+"/bad.csv"); f << "id,x,y,z,t\n0,1,2,3,4,extra\n";
  }
  rejects([&]{read_events(dir+"/bad.csv");});
  {
    std::ofstream f(dir+"/bad.csv"); f << "id,x,y,z,t\n1,1,2,3,4\n";
  }
  rejects([&]{read_events(dir+"/bad.csv");});
  {
    std::istringstream f("a,b\r\n\"text,\"\"quote\"\"\nnext\",\r\n"); Strings row;
    assert(csv_record(f,row) && row==Strings({"a","b"}));
    assert(csv_record(f,row) && row==Strings({"text,\"quote\"\nnext",""}));
    assert(!csv_record(f,row));
  }
  std::filesystem::create_directories("data/development");
  {
    auto result=output("data/development/external_input_checks.json");
    result << "{\n  \"status\": \"passed\",\n"
           << "  \"fixture_kind\": \"invented component fixture; no provider observations\",\n"
           << "  \"checks\": [\"quoted CSV and empty metadata roundtrip\", "
           << "\"missing and mismatched identity rejection\", \"numeric index rejection\", "
           << "\"sparse ray support\", \"explicit catalog-only weights and synthetic defaults\", "
           << "\"ray diagnostic identity mappings\", \"absolute-only unweighted analytic Jacobian\"],\n"
           << "  \"inversions_run\": false\n}\n";
  }
  std::cout << "External-input component checks passed; no inversion was run.\n";
}
