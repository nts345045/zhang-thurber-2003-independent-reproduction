// Run from the project root (the fixture and executable stay under tmp):
// TMPDIR="$PWD/tmp" g++ -std=c++17 -O2 -fopenmp diagnostics/check_external_inputs.cpp -lstdc++fs -o tmp/external_input_checks/check
// OMP_NUM_THREADS=2 tmp/external_input_checks/check [RESULT_JSON [FIXTURE_DIR]]
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
void write_observations(const std::string &path, const ObservationSet &data) {
  auto f=output(path);
  f << "i,j,station,type,value"; data.write_header(f); f << '\n';
  for (size_t q=0;q<data.size();++q) {
    const auto &d=data[q];
    f << d.i << ',' << d.j << ',' << d.k << ',' << d.type << ',' << d.value;
    data.write_metadata(f,q); f << '\n';
  }
}
int main(int argc, char **argv) {
  const std::string dir = argc > 2 ? argv[2] : "tmp/external_input_checks/fixture";
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
  ObservationSet data;
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
    data.rows.push_back({i,j,0,n,1});
    data.native_metadata.push_back(std::move(m));
  }
  for (const auto &field:data.native_metadata[0]) data.metadata_header.push_back(field.first);
  write_observations(dir+"/observations.csv",data);
  auto loaded=observations(dir+"/observations.csv");
  assert(loaded.native_metadata[0]==data.native_metadata[0] && loaded[0].a_priori_weight==0.25);
  assert(loaded[1].station_j==-1 && second_station(loaded[1])==loaded[1].k);
  auto used=observed_rays(loaded,events.size(),stations);
  assert((used==std::vector<int>{0,2}));
  validate_identities(events,stations,loaded);
  auto bad=loaded; bad.native_metadata[0][0].second="smi:fixture/wrong-event";
  rejects([&]{validate_identities(events,stations,bad);});
  bad=loaded; bad.native_metadata[1][7].second="";
  rejects([&]{validate_identities(events,stations,bad);});
  auto no_channel=stations; no_channel[0].metadata.clear();
  rejects([&]{validate_identities(events,no_channel,loaded);});
  bad=loaded; bad[0].j=0;
  rejects([&]{observed_rays(bad,events.size(),stations);});
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
  assert(convergence.rows.size()==2 &&
         std::find(convergence.header.begin(),convergence.header.end(),"diagnostic_row")!=convergence.header.end());
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

  // Native receiver epochs remain separate rows even when channel/position
  // agree. Invented fixtures exercise the actual DD row builder, not an inversion.
  const std::string cross_dir=dir+"/cross_epoch";
  std::filesystem::create_directories(cross_dir);
  auto cross_stations=stations;
  cross_stations.push_back(stations[0]);
  const std::string boundary="1990-01-01T00:00:00Z";
  set_metadata(cross_stations[0].metadata,"metadata_epoch_end",boundary);
  set_metadata(cross_stations[2].metadata,"metadata_epoch_start",boundary);
  for (size_t k=0;k<cross_stations.size();k++)
    set_metadata(cross_stations[k].metadata,"source_sha256","invented-fixture-source-"+std::to_string(k));
  auto cross=loaded;
  for (size_t q=0;q<cross.size();++q) {
    const auto &d=cross[q];
    auto &metadata=cross.native_metadata[q];
    set_metadata(metadata,"station_j",d.j<0 ? "-1":"2");
    set_metadata(metadata,"metadata_epoch_end",boundary);
    set_metadata(metadata,"metadata_epoch_j_start",d.j<0 ? "":boundary);
    set_metadata(metadata,"metadata_epoch_j_end","");
    set_metadata(metadata,"channel_source_sha256","invented-fixture-source-0");
    set_metadata(metadata,"channel_j_source_sha256",d.j<0 ? "":"invented-fixture-source-2");
    set_metadata(metadata,"cross_metadata_epoch",d.j<0 ? "0":"1");
  }
  cross.metadata_header.clear();
  for (const auto &field:cross.native_metadata[0]) cross.metadata_header.push_back(field.first);
  write_observations(cross_dir+"/observations.csv",cross);
  auto expected_metadata=cross.native_metadata[1];
  cross=observations(cross_dir+"/observations.csv");
  assert(cross[0].station_j==-1 && cross[1].station_j==2);
  assert(cross.native_metadata[1]==expected_metadata);
  validate_identities(events,cross_stations,cross);
  auto differential_only=cross;
  differential_only.rows.erase(differential_only.rows.begin());
  differential_only.native_metadata.erase(differential_only.native_metadata.begin());
  auto cross_used=observed_rays(differential_only,events.size(),cross_stations);
  assert((cross_used==std::vector<int>{2,3}));
  auto cross_rays=rays(g,events,cross_stations,config,true,&cross_used);
  assert(cross_rays[0].dv.empty() && !cross_rays[2].dv.empty() && !cross_rays[3].dv.empty());
  auto timed_events=events; timed_events[0].t=-0.03; timed_events[1].t=0.05;
  const double expected_dd=(std::sqrt(5.)-2)/6+0.08;
  assert(std::abs(prediction(cross[1],cross_rays,timed_events,3)-expected_dd)<1e-12);
  Row differential=observation_row(cross[1],cross_rays,g,events.size(),3,false);
  auto coefficient=[&](int column) {
    double value=0;
    for (const auto &entry:differential) if (entry.col==column) value+=entry.val;
    return value;
  };
  assert(coefficient(3)==-1 && coefficient(7)==1);
  assert(std::abs(coefficient(2)+1./6)<1e-12);
  assert(std::abs(coefficient(4)-1./(6*std::sqrt(5.)))<1e-12);
  assert(std::abs(coefficient(6)-2./(6*std::sqrt(5.)))<1e-12);
  const double h=1e-5;
  for (int i=0;i<2;i++)
    for (int axis=0;axis<3;axis++) {
      auto plus=events,minus=events;
      plus[i].p[axis]+=h; minus[i].p[axis]-=h;
      auto exact=[&](const std::vector<Event> &e) {
        return (norm(e[1].p-cross_stations[0].p)-norm(e[0].p-cross_stations[2].p))/6;
      };
      assert(std::abs((exact(plus)-exact(minus))/(2*h)-coefficient(4*i+axis))<1e-10);
    }
  // Check an included model coefficient against the independent action
  // derivative. The existing 5 m DD exclusion is intentionally retained.
  int node=-1;
  for (const auto &entry:differential)
    if (entry.col>=int(4*events.size()) &&
        (node<0 || std::abs(entry.val)>std::abs(coefficient(4*events.size()+node))))
      node=entry.col-4*events.size();
  assert(node>=0);
  auto gp=g,gm=g; gp.v[node]*=std::exp(-h); gm.v[node]*=std::exp(h);
  auto dd_action=[&](const Grid &grid) {
    return path_eval(grid,cross_rays[3].path)-path_eval(grid,cross_rays[2].path);
  };
  assert(std::abs((dd_action(gp)-dd_action(gm))/(2*h)-coefficient(4*events.size()+node))<1e-9);
  assert(observation_row(cross[1],cross_rays,g,events.size(),3,true).size()==8);

  auto wrong_stations=cross_stations;
  wrong_stations[2].p[2]+=1e-12; // Exact position is required, not a tolerance.
  rejects([&]{observed_rays(cross,events.size(),wrong_stations);});
  wrong_stations=cross_stations;
  set_metadata(wrong_stations[2].metadata,"channel_code","HHN");
  set_metadata(wrong_stations[2].metadata,"channel_seed_id","XX.TEST..HHN");
  set_metadata(wrong_stations[2].metadata,"channel_fdsn_source_id","FDSN:XX_TEST__H_H_N");
  rejects([&]{observed_rays(cross,events.size(),wrong_stations);});
  wrong_stations=cross_stations;
  set_metadata(wrong_stations[2].metadata,"channel_fdsn_source_id","FDSN:XX_OTHER__H_H_Z");
  rejects([&]{validate_identities(events,wrong_stations,cross);});
  for (const auto *field:{"metadata_epoch_start","metadata_epoch_end","metadata_epoch_j_start","metadata_epoch_j_end"}) {
    bad=cross; set_metadata(bad.native_metadata[1],field,"wrong-epoch");
    rejects([&]{validate_identities(events,cross_stations,bad);});
  }
  bad=cross; bad[1].station_j=3;
  rejects([&]{observed_rays(bad,events.size(),cross_stations);});
  rejects([&]{validate_identities(events,cross_stations,bad);});
  bad=cross; set_metadata(bad.native_metadata[0],"metadata_epoch_j_start",boundary);
  rejects([&]{observed_rays(bad,events.size(),cross_stations);});
  for (const auto *value:{"", "-1", "-2", "1.5"}) {
    bad=cross; set_metadata(bad.native_metadata[1],"station_j",value);
    write_observations(cross_dir+"/bad.csv",bad);
    rejects([&]{observations(cross_dir+"/bad.csv");});
  }
  bad=cross; set_metadata(bad.native_metadata[0],"station_j","0");
  write_observations(cross_dir+"/bad.csv",bad);
  rejects([&]{observations(cross_dir+"/bad.csv");});
  bad=cross; set_metadata(bad.native_metadata[0],"station_j","");
  write_observations(cross_dir+"/empty_absolute.csv",bad);
  assert(observations(cross_dir+"/empty_absolute.csv")[0].station_j==-1);

  write_events(events,cross_dir+"/truth_events.csv");
  write_events(cross_stations,cross_dir+"/stations.csv");
  write_grid(g,cross_dir+"/truth_grid.csv");
  raycheck(config,cross_dir);
  auto cross_mapping=csv_table(cross_dir+"/ray_identifiers.csv");
  assert(cross_mapping.rows.size()==3);
  bool saw_native_j=false;
  for (const auto &row:cross_mapping.rows) {
    if (row[4]!="j") continue;
    assert(row[1]=="0" && row[2]=="2" && row[3]=="1");
    auto field=[&](const std::string &key) {
      auto found=std::find(cross_mapping.header.begin(),cross_mapping.header.end(),key);
      assert(found!=cross_mapping.header.end());
      return row[found-cross_mapping.header.begin()];
    };
    assert(field("receiver_metadata_epoch_start")==boundary);
    assert(field("observation_metadata_epoch_start")=="1984-01-01T00:00:00Z");
    assert(field("observation_metadata_epoch_j_start")==boundary);
    assert(field("observation_channel_j_source_sha256")=="invented-fixture-source-2");
    assert(field("observation_station_j")=="2");
    assert(field("observation_pick_j_resource_id")=="smi:fixture/pick0");
    saw_native_j=true;
  }
  assert(saw_native_j);
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
    auto result=output(argc>=2 ? argv[1] : "data/development/external_input_checks.json");
    result << "{\n  \"status\": \"passed\",\n"
           << "  \"fixture_kind\": \"invented component fixture; no provider observations\",\n"
           << "  \"checks\": [\"quoted CSV and empty metadata roundtrip\", "
           << "\"missing and mismatched identity rejection\", \"numeric index rejection\", "
           << "\"sparse ray support\", \"explicit catalog-only weights and synthetic defaults\", "
           << "\"ray diagnostic identity mappings\", \"absolute-only unweighted analytic Jacobian\", "
           << "\"native cross-epoch receiver identities and sparse support\", "
           << "\"cross-epoch analytic DD prediction and source Jacobian\", "
           << "\"DD model Jacobian against finite-difference action\", "
           << "\"cross-epoch channel, coordinate, epoch and index mismatch rejection\"],\n"
           << "  \"inversions_run\": false\n}\n";
  }
  std::cout << "External-input component checks passed; no inversion was run.\n";
}
