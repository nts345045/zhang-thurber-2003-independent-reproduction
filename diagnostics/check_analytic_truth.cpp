// Invented homogeneous geometry; no observed data or production inversion.
#define main solver_entry
#include "../src/main.cpp"
#undef main
#include <functional>
#include <tuple>

void write_table(const std::string &path,const CsvTable &table) {
  auto out=output(path);
  auto row=[&](const Strings &fields) {
    for(size_t i=0;i<fields.size();++i) out<<(i?",":"")<<csv_quote(fields[i]);
    out<<'\n';
  };
  row(table.header);for(const auto &values:table.rows)row(values);
}

std::string number(double value) {
  std::ostringstream out;out<<std::setprecision(17)<<value;return out.str();
}

std::string contents(const std::string &path) {
  std::ifstream file(path,std::ios::binary);
  return std::string(std::istreambuf_iterator<char>(file),std::istreambuf_iterator<char>());
}

int main(int argc,char **argv) {
  if(argc!=2)throw std::runtime_error("Usage: check_analytic_truth OUT");
  std::string out=argv[1],bundle=out+"/bundle";
  std::filesystem::create_directories(bundle+"/inputs");
  std::ofstream checks(out+"/checks.csv");checks<<"check,passed\n";
  auto check=[&](const std::string &name,bool passed) {
    checks<<name<<','<<passed<<std::endl;
    if(!passed)throw std::runtime_error(name);
  };
  auto rejects=[&](const std::string &name,const std::function<void()> &action) {
    bool rejected=false;try{action();}catch(const std::exception &){rejected=true;}
    check(name,rejected);
  };
  Grid truth;truth.x={-2,0,2};truth.y={-2,2};truth.z={-.5,0,2};truth.v.assign(truth.size(),6);
  Grid initial=truth;
  for(size_t k=0;k<initial.z.size();++k)for(size_t j=0;j<initial.y.size();++j)for(size_t i=0;i<initial.x.size();++i)
    initial.v[initial.id(i,j,k)]=5+.1*initial.z[k];
  std::vector<Event> events{{{-.75,.5,.4},0,{{"event_resource_id","invented:event0"},{"origin_resource_id","invented:origin0"},{"note","quoted, fixture"}}},
                             {{.6,-.8,1.1},0,{{"event_resource_id","invented:event1"},{"origin_resource_id","invented:origin1"},{"note","blank end epoch is valid"}}}};
  auto station=[](P p,std::string name,std::string location,std::string end) {
    return Event{p,0,{{"network_code","XX"},{"station_code",name},{"location_code",location},{"channel_code","EHZ"},
      {"channel_seed_id","XX."+name+"."+location+".EHZ"},{"channel_fdsn_source_id","FDSN:XX_"+name+"_"+location+"_E_H_Z"},
      {"metadata_epoch_start","2000-01-01T00:00:00"},{"metadata_epoch_end",end}}};
  };
  std::vector<Event> stations{station({-1,-1,0},"AAA","",""),station({1,1,-.1},"BBB","01","2001-01-01T00:00:00")};
  write_grid(truth,bundle+"/inputs/truth_grid.csv");
  write_events(events,bundle+"/inputs/truth_events.csv");
  write_events(stations,bundle+"/inputs/stations.csv");
  // Read the same serialized geometry the real entry point consumes.
  events=read_events(bundle+"/inputs/truth_events.csv");stations=read_events(bundle+"/inputs/stations.csv");
  auto et=csv_table(bundle+"/inputs/truth_events.csv"),st=csv_table(bundle+"/inputs/stations.csv");
  CsvTable reference;
  reference.header={"pair_index","event","station","reference_complete","reference_valid","candidate_count","near_tie_count","time_s","branch","turning_x_km","source_dx_s_per_km","source_dy_s_per_km","source_dz_s_per_km"};
  for(const auto &name:et.header)reference.header.push_back("source_"+name);
  for(const auto &name:st.header)reference.header.push_back("receiver_"+name);
  for(size_t i=0;i<events.size();++i)for(size_t k=0;k<stations.size();++k) {
    P difference=events[i].p-stations[k].p;double length=norm(difference);
    Strings row{std::to_string(i*stations.size()+k),std::to_string(i),std::to_string(k),"1","1","1","1",number(length/6),"flat_direct",""};
    for(double value:difference)row.push_back(number(value/(6*length)));
    row.insert(row.end(),et.rows[i].begin(),et.rows[i].end());row.insert(row.end(),st.rows[k].begin(),st.rows[k].end());
    reference.rows.push_back(row);
  }
  write_table(bundle+"/references.csv",reference);
  auto load=[&](){return read_analytic_truth(bundle,truth,events,stations);};
  auto accepted=load();check("complete_homogeneous_reference",accepted.times.size()==4);
  check("signed_source_components_accepted",csv_double(reference.rows[0][11])>0&&csv_double(reference.rows[1][10])<0);
  auto mutate=[&](const std::string &name,const std::function<void(CsvTable&)> &change) {
    auto altered=reference;change(altered);write_table(bundle+"/references.csv",altered);rejects(name,[&](){load();});write_table(bundle+"/references.csv",reference);
  };
  mutate("missing_pair",[](CsvTable&t){t.rows.pop_back();});
  mutate("extra_pair",[](CsvTable&t){t.rows.push_back(t.rows.back());});
  mutate("duplicate_pair",[](CsvTable&t){t.rows[1]=t.rows[0];});
  mutate("reordered_pairs",[](CsvTable&t){std::swap(t.rows[0],t.rows[1]);});
  mutate("missing_column",[](CsvTable&t){t.header.pop_back();for(auto&r:t.rows)r.pop_back();});
  mutate("duplicate_column",[](CsvTable&t){t.header.back()=t.header.front();});
  mutate("invented_pick_column_rejected",[](CsvTable&t){t.header.push_back("pick_resource_id");for(auto&r:t.rows)r.push_back("invented:pick");});
  for(const auto &test:std::vector<std::tuple<std::string,size_t,std::string>>{
      {"wrong_pair_index",0,"1"},{"wrong_event",1,"1"},{"wrong_station",2,"1"},
      {"incomplete",3,"0"},{"invalid",4,"0"},{"zero_candidates",5,"0"},
      {"near_tie",6,"2"},{"no_minimum",6,"0"},{"negative_time",7,"-1"},
      {"nan_time",7,"nan"},{"infinite_time",7,"inf"},{"time_below_speed_bound",7,"0"},
      {"time_above_speed_bound",7,"100"},{"unknown_branch",8,"invented_branch"},
      {"direct_turn_inconsistent",9,"0"},{"nan_derivative",10,"nan"},
      {"infinite_derivative",11,"inf"},{"missing_derivative",12,""},
      {"inline_source_index",13,"1"},{"inline_source_position",14,"-0.5"},
      {"inline_source_origin_time",17,"1"},{"inline_event_id",18,"invented:wrong"}}) {
    mutate(std::get<0>(test),[&](CsvTable&t){t.rows[0][std::get<1>(test)]=std::get<2>(test);});
  }
  mutate("outward_missing_turn",[](CsvTable&t){t.rows[0][8]="turning";});
  mutate("outward_turn_outside",[](CsvTable&t){t.rows[0][8]="turning";t.rows[0][9]="3";});
  size_t epoch=std::find(reference.header.begin(),reference.header.end(),"receiver_metadata_epoch_start")-reference.header.begin();
  mutate("native_receiver_epoch",[&](CsvTable&t){t.rows[0][epoch]="changed";});
  auto snapshot=csv_table(bundle+"/inputs/truth_grid.csv");
  auto changed=snapshot;changed.rows.back()=changed.rows.front();write_table(bundle+"/inputs/truth_grid.csv",changed);
  rejects("duplicate_grid_snapshot",[&](){load();});write_table(bundle+"/inputs/truth_grid.csv",snapshot);
  changed=snapshot;changed.rows[0][3]="5";write_table(bundle+"/inputs/truth_grid.csv",changed);
  rejects("different_grid_snapshot_value",[&](){load();});write_table(bundle+"/inputs/truth_grid.csv",snapshot);
  auto changed_event=events;changed_event[0].t=1;
  rejects("nonzero_current_source_time",[&](){read_analytic_truth(bundle,truth,changed_event,stations);});
  auto changed_station=stations;changed_station[0].t=1;
  rejects("nonzero_current_receiver_time",[&](){read_analytic_truth(bundle,truth,events,changed_station);});
  changed_event=events;changed_event[0].metadata.back().second="changed";
  rejects("changed_native_metadata",[&](){read_analytic_truth(bundle,truth,changed_event,stations);});
  Grid bad=truth;bad.v[bad.id(0,1,0)]=5;
  rejects("non_layered_truth",[&](){read_analytic_truth(bundle,bad,events,stations);});
  bad=truth;bad.v.assign(bad.size(),0);
  rejects("nonpositive_truth",[&](){read_analytic_truth(bundle,bad,events,stations);});
  auto config=output(out+"/run.cfg");
  config<<"authoritative_geometry 1\nseed 123\nlocation_noise .15\nstation_noise .03\nnoise .01\npair_distance 10\ntime_quantum .01\nray_initializer 0\nray_spacing .5\nray_iterations 1000\n";config.close();
  Config c(out+"/run.cfg");
  auto prepare=[&](const std::string &name) {
    std::string dir=out+"/"+name;std::filesystem::create_directories(dir);
    for(const auto *file:{"truth_grid.csv","truth_events.csv","stations.csv"})
      std::filesystem::copy_file(bundle+"/inputs/"+file,dir+"/"+file);
    write_grid(initial,dir+"/initial_grid.csv");
    auto marker=output(dir+"/geometry_truth_ray_convergence.csv");marker<<"retained invented prior failure\n";
    return dir;
  };
  std::string ordinary=prepare("ordinary"),analytic=prepare("analytic"),baseline=prepare("baseline"),cli=prepare("cli"),rejected=prepare("rejected");
  simulate(c,ordinary);simulate(c,analytic,bundle);
  check("same_noise_rounding_dd_and_full_identifiers",contents(ordinary+"/observations.csv")==contents(analytic+"/observations.csv"));
  check("same_initial_source_perturbations_depth_varying_start",contents(ordinary+"/initial_events.csv")==contents(analytic+"/initial_events.csv"));
  auto aa=csv_table(ordinary+"/arrivals.csv"),ab=csv_table(analytic+"/arrivals.csv");
  bool same=true,blank=true;
  for(size_t n=0;n<aa.rows.size();++n) {
    for(size_t k=0;k<25;++k)same=same&&aa.rows[n][k]==ab.rows[n][k]; // Seven values plus18native fields.
    for(size_t k=25;k<aa.header.size();++k)blank=blank&&ab.rows[n][k].empty();
  }
  check("same_arrivals_numeric_and_native_fields",same);check("no_fabricated_ray_status",blank);
  check("separate_analytic_truth_status",std::filesystem::exists(analytic+"/simulation_truth_status.csv")&&!std::filesystem::exists(analytic+"/simulation_ray_status.csv"));
  check("prior_geometry_failure_preserved",contents(analytic+"/geometry_truth_ray_convergence.csv")=="retained invented prior failure\n");
  check("explicit_truth_mode",contents(analytic+"/simulation_truth_mode.txt").find("continuous_layered_snell_reference")!=std::string::npos);
  auto obs=observations(analytic+"/observations.csv",read_events(analytic+"/initial_events.csv"),stations,true);
  validate_identities(read_events(analytic+"/initial_events.csv"),stations,obs,true);
  check("unchanged_compact_observation_schema",obs.shared_synthetic&&obs.size()==8);
  rejects("existing_simulation_not_overwritten",[&](){simulate(c,analytic,bundle);});
  auto broken=reference;broken.rows[0][3]="0";write_table(bundle+"/references.csv",broken);
  rejects("invalid_reference_blocks_simulation",[&](){simulate(c,rejected,bundle);});write_table(bundle+"/references.csv",reference);
  check("invalid_reference_no_arrivals_or_initial_output",!std::filesystem::exists(rejected+"/arrivals.csv")&&!std::filesystem::exists(rejected+"/initial_events.csv"));
  std::vector<std::string> args{"dd","simulate",out+"/run.cfg",cli,"--analytic-truth",bundle};
  std::vector<char*> pointers;for(auto &arg:args)pointers.push_back(&arg[0]);
  check("actual_cli_analytic_entry",solver_entry(int(pointers.size()),pointers.data())==0);
  check("actual_cli_matches_direct_call",contents(cli+"/observations.csv")==contents(analytic+"/observations.csv"));
  args[4]="--unknown";pointers.clear();for(auto &arg:args)pointers.push_back(&arg[0]);
  check("unknown_cli_option_rejected",solver_entry(int(pointers.size()),pointers.data())!=0);
  std::cout<<"Analytic truth contract fixtures complete; baseline fixture ready at "<<baseline<<'\n';
}
