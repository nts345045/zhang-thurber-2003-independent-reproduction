// Invented records only. The copied invert loop is unchanged; three explicit
// fixture seams call the actual ray gate/solve or redirect an output stream.
#ifdef NDEBUG
#error "Controls must retain assertions"
#endif
#define main tomography_main
#include "fixture_main.cpp"
#undef main
#include <fstream>
#include <sstream>

namespace fs = std::filesystem;
struct Seen {
  std::string prefix;
  Grid grid;
  std::vector<Event> events;
  std::vector<Ray> rays;
  std::vector<int> used;
  bool derivatives;
};
std::vector<Seen> seen;
Vec prescribed, solved, returned;
LSQRInfo saved_info;
std::string fault, full_output, fixture_dir;
int solves = 0, trial_calls = 0, output_redirects = 0;
std::ofstream checks;
int check_count = 0;

void check(bool condition, const std::string &name) {
  checks << name << ',' << condition << '\n'; checks.flush(); ++check_count;
  if (!condition) throw std::runtime_error("CONTROL FAILED: " + name);
}
const std::string &cell(const CsvTable &t, size_t row, const std::string &name) {
  auto p = std::find(t.header.begin(), t.header.end(), name);
  if (p == t.header.end()) throw std::runtime_error("Missing column " + name);
  return t.rows.at(row).at(size_t(p - t.header.begin()));
}
double number(const CsvTable &t, size_t row, const std::string &name) {
  return csv_double(cell(t, row, name));
}
bool close(double a, double b, double tolerance = 2e-13) {
  return std::isfinite(a) && std::isfinite(b) && std::abs(a-b) <= tolerance;
}
std::string fixture_output(const std::string &path) {
  if (!full_output.empty() && path == full_output) {
    ++output_redirects; return "/dev/full";
  }
  return path;
}
Vec fixture_solve(Matrix matrix, double damping, LSQRInfo *info) {
  ++solves;
  solved = solve(std::move(matrix), damping, info);
  saved_info = *info;
  returned = prescribed.empty() ? solved : prescribed;
  if (returned.size() != solved.size()) throw std::runtime_error("Fixture delta dimension");
  std::ofstream evidence(fixture_dir+"/control_solve_"+std::to_string(solves)+".csv");
  evidence << std::setprecision(17) << "parameter,actual_solve_increment,fixture_returned_increment,lsqr_iterations,lsqr_relative_normal_residual,lsqr_converged\n";
  for(size_t q=0;q<solved.size();++q)evidence<<q<<','<<solved[q]<<','<<returned[q]<<','<<info->iterations<<','<<info->relative_normal_residual<<','<<info->converged<<'\n';
  evidence.close();if(!evidence)throw std::runtime_error("Cannot save fixture solve evidence");
  return returned;
}
void fixture_gate(const std::string &prefix, const Grid &g,
                  const std::vector<Event> &e, const std::vector<Event> &s,
                  const std::vector<Ray> &rr, const std::vector<int> &used,
                  bool required, bool derivatives) {
  seen.push_back({prefix, g, e, rr, used, derivatives});
  auto altered = rr;
  const bool trial = !derivatives;
  int ordinal = trial ? trial_calls++ : -1;
  bool reject = trial && (fault == "all" || fault == "state" || fault == "mixed_invalid" ||
      ((fault == "half" || fault == "worse" || fault == "mixed" || fault == "unexpected") && ordinal == 0) ||
      (fault == "quarter" && ordinal < 2));
  reject |= fault == "current" && derivatives && solves == 0;
  reject |= fault == "final" && derivatives && solves > 0;
  if (trial && fault == "unexpected") throw std::runtime_error("Invented unexpected forward exception");
  if (reject) altered.at(used.back()).converged = false;
  if (trial && fault == "mixed" && ordinal == 0) altered.at(used.front()).time = NAN;
  // These are the actual returned Rays and actual gate; failure classification
  // is never synthesized by throwing a fixture quality exception.
  inversion_ray_gate(prefix, g, e, s, altered, used, required, derivatives);
}
void reset(const std::string &kind = "", const Vec &delta = {}) {
  fault = kind; prescribed = delta; solved.clear(); returned.clear(); seen.clear();
  solves = trial_calls = output_redirects = 0; full_output.clear();
}

struct Fixture {
  std::string dir;
  Config c;
  Grid g;
  std::vector<Event> e, s;
  ObservationSet data;
  Fixture(std::string path, double offset = .1, int iterations = 1) : dir(path), c("/dev/null") {
    fs::create_directories(dir);
    fixture_dir=dir;
    g.x = {-2, 4}; g.y = {-2, 2}; g.z = {-1, 5}; g.v.assign(g.size(), 5);
    e = {{{.2,.1,2},0,{{"event_resource_id","smi:invented/event0"},{"origin_resource_id","smi:invented/origin0"},{"note","invented, \"quoted\"\nline"}}},
         {{1.2,-.2,3},0,{{"event_resource_id","smi:invented/event1"},{"origin_resource_id","smi:invented/origin1"},{"note",""}}}};
    Metadata m{{"network_code","XX"},{"station_code","MOCK"},{"location_code",""},{"channel_code","HHZ"},
      {"channel_seed_id","XX.MOCK..HHZ"},{"channel_fdsn_source_id","FDSN:XX_MOCK__H_H_Z"},
      {"metadata_epoch_start","1980-01-01T00:00:00Z"},{"metadata_epoch_end","1990-01-01T00:00:00Z"}};
    s = {{{0,0,0},0,m},{{0,0,0},0,m}};
    set_metadata(s[1].metadata,"metadata_epoch_start","1990-01-01T00:00:00Z");
    set_metadata(s[1].metadata,"metadata_epoch_end","");
    write_events(e,dir+"/initial_events.csv",17); write_events(s,dir+"/stations.csv",17);
    write_grid(g,dir+"/initial_grid.csv",17);
    c.v = {{"authoritative_ids_required",1},{"ray_spacing",1},{"ray_iterations",1000},
      {"ray_initializer",0},{"pair_distance",20},{"iterations",double(iterations)},
      {"stage_length",1},{"smoothing",1},{"damping",.1},{"catalog_only_dd",1}};
    auto cfg = output(dir+"/run.cfg");
    for (const auto &v:c.v) cfg << v.first << ' ' << v.second << '\n'; cfg.close();
    auto out = output(dir+"/observations.csv"); out << std::setprecision(17);
    out << "i,j,station,type,value,station_j,a_priori_weight,event_i_resource_id,origin_i_resource_id,pick_i_resource_id,arrival_i_resource_id,event_j_resource_id,origin_j_resource_id,pick_j_resource_id,arrival_j_resource_id,channel_seed_id,channel_fdsn_source_id,metadata_epoch_start,metadata_epoch_end,metadata_epoch_j_start,metadata_epoch_j_end,note,observation_index,current_residual\n";
    // Last absolute row has zero prior but adds a native epoch to used-rays.
    const int ii[] = {0,1,0,0}, jj[] = {-1,-1,1,-1}, kk[] = {0,1,0,1};
    const double priors[] = {1,.7,.4,0};
    for (int q=0;q<4;++q) {
      int i=ii[q], j=jj[q], k=kk[q];
      double value=norm(e[i].p)/5+(i+1)*offset;
      if (j>=0) value-=norm(e[j].p)/5+(j+1)*offset;
      out << i << ',' << j << ',' << k << ',' << (j>=0?1:0) << ',' << value << ',' << (j>=0?"1":"") << ',' << priors[q];
      for (int event:{i,j}) for (const char *kind:{"event","origin","pick","arrival"})
        out << ',' << (event<0?"":"smi:invented/"+std::string(kind)+std::to_string(event));
      for (const char *name:{"channel_seed_id","channel_fdsn_source_id","metadata_epoch_start","metadata_epoch_end"})
        out << ',' << csv_quote(required_metadata(s[k].metadata,name,true));
      out << ',' << (j>=0?required_metadata(s[1].metadata,"metadata_epoch_start"):"") << ",," << csv_quote("invented, \"quoted\"\nline") << ",native row " << q << ",not a numeric residual\n";
    }
    out.close(); data=observations(dir+"/observations.csv",e,s,false);
    validate_identities(e,s,data);
  }
};
std::string attempt(Fixture &f, const std::string &mode) {
  try { invert(f.c,f.dir,mode); return ""; }
  catch (const std::exception &error) {
    std::ofstream out(f.dir+"/caught.txt"); out << error.what() << '\n'; return error.what();
  }
}
Vec time_delta(double scale, bool joint=false) {
  Vec d(joint?16:8); d[3]=scale; d[7]=2*scale; return d;
}
std::string trial_prefix(const Fixture &f,int ls,const std::string &mode="loc1d") {
  return f.dir+"/"+mode+"_rejected_trial_it_0_ls_"+std::to_string(ls);
}
void no_final(const Fixture &f,const std::string &mode) {
  check(!fs::exists(f.dir+"/"+mode+"_events.csv")&&!fs::exists(f.dir+"/"+mode+"_grid.csv"),"fatal_has_no_final_state");
}
// Independent fixed weight calculation: sort medians instead of invoking the
// solver weight helper, and retain exact original prior/epoch rows.
Vec fixed_weights(const Fixture &f,const Seen &initial,Vec &residual) {
  Vec w; std::array<Vec,3> bytype;
  for (const auto &d:f.data) {
    double predicted=initial.events[d.i].t+initial.rays[d.i*2+d.k].time;
    if(d.j>=0) predicted-=initial.events[d.j].t+initial.rays[d.j*2+second_station(d)].time;
    residual.push_back(d.value-predicted); bytype[d.type].push_back(std::abs(residual.back()));
  }
  double cut[3];
  for(int t=0;t<3;++t){std::sort(bytype[t].begin(),bytype[t].end());cut[t]=bytype[t].empty()?1:std::max(.01,6*1.4826*bytype[t][bytype[t].size()/2]);}
  for(size_t q=0;q<f.data.size();++q){const auto &d=f.data[q];double z=residual[q]/cut[d.type];
    double v=(d.type==0?1:.1)*d.a_priori_weight*std::pow(std::max(0.,1-z*z),2);
    if(d.j>=0)v*=std::pow(std::max(0.,1-std::pow(norm(f.e[d.i].p-f.e[d.j].p)/20,2)),2);
    w.push_back(v<1e-12?0:v);
  }return w;
}

#ifdef CANDIDATE
void snapshot_checks(const Fixture &f,const std::string &mode) {
  const auto prefix=f.dir+"/"+mode+"_iteration_0_solve";
  auto delta=csv_table(prefix+"_delta.csv"),weights=csv_table(prefix+"_weights.csv"),context=csv_table(prefix+"_context.csv");
  check(delta.rows.size()==returned.size(),"all_unscaled_columns_saved");
  for(size_t q=0;q<returned.size();++q){
    check(number(delta,q,"increment")==returned[q]&&number(delta,q,"parameter_index")==q,"delta_exact_roundtrip");
    if(q<8) check(cell(delta,q,"source_event_resource_id")==required_metadata(f.e[q/4].metadata,"event_resource_id"),"delta_source_identity");
    else check(cell(delta,q,"source_event_resource_id").empty()&&number(delta,q,"reference_v")==5,"model_row_no_event_identity");
  }
  Vec residual;auto w=fixed_weights(f,seen.front(),residual); double before=0;
  for(size_t q=0;q<w.size();++q){
    before+=w[q]*w[q]*residual[q]*residual[q];
    check(close(number(weights,q,"fixed_row_multiplier"),w[q],1e-15)&&number(weights,q,"current_residual")==residual[q],"original_fixed_weight_and_residual");
    for(const auto &field:f.data.native_metadata[q]) check(cell(weights,q,"original_"+field.first)==field.second,"original_metadata_exact");
    check(number(weights,q,"station_j")== (f.data[q].j<0?-1:second_station(f.data[q])),"second_epoch_index");
  }
  check(close(number(context,0,"objective_before"),before,1e-15),"independent_initial_objective");
  check(number(context,0,"lsqr_iterations")==saved_info.iterations&&number(context,0,"lsqr_relative_normal_residual")==saved_info.relative_normal_residual&&number(context,0,"lsqr_converged")==saved_info.converged,"actual_solve_status_snapshot");
  check(number(weights,3,"fixed_row_multiplier")==0&&seen.front().used==std::vector<int>({0,1,3}),"omitted_row_preserves_native_ray_support");
}
void gate_controls(const std::string &root) {
  reset();Fixture f(root+"/gate");auto used=observed_rays(f.data,2,f.s);auto rr=rays(f.g,f.e,f.s,f.c,true,&used);
  for(int reason=0;reason<11;++reason){auto altered=rr;int n=used.back();
    if(reason==0)altered[n].converged=false;
    if(reason==1)altered[n].time=NAN;
    if(reason==2)altered[n].path.clear();
    if(reason==3)altered[n].path[1][0]=5;
    if(reason==4)altered[n].path.front()[0]=std::nextafter(f.e[1].p[0],INFINITY);
    if(reason==5)altered[n].path.back()[0]=std::nextafter(0.,INFINITY);
    if(reason==6){altered[n].initialization_attempted=true;altered[n].initialization_succeeded=false;}
    if(reason==7)altered[n].dv.clear();
    if(reason==8)altered[n].length.clear();
    if(reason==9){altered[n].converged=false;altered[used.front()].time=NAN;}
    std::string prefix=f.dir+"/reason_"+std::to_string(reason);bool caught=false;
    try{inversion_ray_gate(prefix,f.g,f.e,f.s,altered,used,reason==10,true);}
    catch(const InverseRayRejection &e){caught=true;check(e.only_local_stopping==(reason==0),"actual_gate_exact_pure_reason_classification");}
    check(caught,"actual_gate_rejection");auto roster=csv_table(prefix+"_ray_failures.csv");
    check(!roster.rows.empty()&&cell(roster,roster.rows.size()-1,"receiver_location_code").empty(),"gate_native_empty_location");
  }
}
void candidate_controls(const std::string &root) {
  gate_controls(root);
  for(const std::string kind:{"half","quarter"}) {
    reset(kind,time_delta(kind=="half"?.2:.4));Fixture f(root+"/"+kind);
    check(attempt(f,"loc1d").empty(),"quality_then_valid_completion");
    auto ledger=csv_table(f.dir+"/loc1d_iteration_0_trials.csv");int rejections=kind=="half"?1:2;
    check(ledger.rows.size()==size_t(rejections+1)&&solves==1,"single_solve_existing_halving_sequence");
    for(int q=0;q<rejections;++q){check(cell(ledger,q,"status")=="local_stopping_rejected"&&cell(ledger,q,"objective_after").empty(),"rejected_trial_never_objective");
      check(fs::exists(trial_prefix(f,q)+"_ray_paths.csv"),"unique_failure_path_evidence");}
    check(cell(ledger,rejections,"status")=="accepted"&&close(number(ledger,rejections,"objective_after"),0,1e-27),"known_half_or_quarter_objective_zero");
    auto final=read_events(f.dir+"/loc1d_events.csv");
    check(final[0].p==f.e[0].p&&final[1].p==f.e[1].p&&final[0].t==.1&&final[1].t==.2,"known_accepted_time_update");
    snapshot_checks(f,"loc1d");
  }
  for(const std::string kind:{"all","mixed_invalid","state","worse","current","final","mixed","unexpected"}) {
    bool joint=kind=="mixed_invalid"||kind=="state";
    Vec d=time_delta(kind=="worse"?-.2:kind=="final"?.1:.2,joint);
    if(kind=="mixed_invalid")for(int q=8;q<16;++q)d[q]=-1000;
    if(kind=="state") {d[0]=20;d[1]=-8;d[2]=12;d[4]=-20;d[5]=8;d[6]=-12;for(int q=8;q<16;++q)d[q]=.01*(q-7);}
    reset(kind,d);Fixture f(root+"/"+kind);const std::string mode=joint?"dd":"loc1d";
    auto error=attempt(f,mode);
    if(kind=="worse"){
      check(error.empty(),"valid_nonimproving_trials_retain_legacy_no_update");
      auto final=read_events(f.dir+"/loc1d_events.csv");check(final[0].p==f.e[0].p&&final[0].t==0&&final[1].t==0,"no_update_state");
    }else{check(!error.empty(),"fatal_case_terminates");no_final(f,mode);}
    if(kind=="all"||kind=="mixed_invalid"||kind=="state"||kind=="worse"){
      auto ledger=csv_table(f.dir+"/"+mode+"_iteration_0_trials.csv");
      check(ledger.rows.size()==12&&solves==1,"twelve_existing_fractions_one_solve");
      for(size_t q=0;q<12;++q)check(number(ledger,q,"step_fraction")==std::ldexp(1.,-int(q)),"exact_existing_fraction");
      if(kind=="mixed_invalid")check(cell(ledger,0,"status")=="invalid_trial_model"&&trial_calls==11,"invalid_model_skip_then_quality");
      if(kind!="worse")check(error.find("No objective-evaluable trial")!=std::string::npos,"no_evaluable_trial_explicit_fatal");
      snapshot_checks(f,mode);
    }
    if(kind=="current")check(solves==0&&trial_calls==0,"current_failure_before_solve");
    if(kind=="mixed"||kind=="unexpected")check(trial_calls==1&&!fs::exists(f.dir+"/loc1d_iteration_0_solve_delta.csv"),"nonquality_fatal_no_continuation");
    if(kind=="final")check(solves==1&&trial_calls==1&&error.find("Inverse forward")!=std::string::npos,"final_failure_not_retried");
    if(kind=="state"){
      for(const auto &s:seen)if(!s.derivatives){
        int ls=std::stoi(s.prefix.substr(s.prefix.rfind("_ls_")+4));double step=std::ldexp(1.,-ls);
        const Vec *axes[]={&f.g.x,&f.g.y,&f.g.z};
        for(int i=0;i<2;++i){for(int k=0;k<3;++k)check(s.events[i].p[k]==std::clamp(f.e[i].p[k]+step*d[4*i+k],axes[k]->front(),axes[k]->back()),"candidate_clamp_from_original_state");check(s.events[i].t==step*d[4*i+3],"candidate_time_from_original_delta");}
        for(int q=0;q<8;++q)check(s.grid.v[q]==5*std::exp(-step*d[8+q]),"candidate_velocity_from_original_delta");
        auto saved=read_grid(s.prefix+"_grid.csv");check(saved.v==s.grid.v,"trial_model_exact_serialization");
        auto accepted=read_grid(s.prefix+"_accepted_grid.csv");check(accepted.v==f.g.v,"accepted_model_not_rejected_model");
      }
    }
  }
  // Failure after successful open: no symlink or stale path is used. The
  // fixture opener redirects only this requested stream to the kernel's full
  // device. Every other snapshot output uses the real filesystem.
  std::vector<std::string> suffixes={"_ray_status.csv","_ray_failures.csv","_ray_paths.csv","_events.csv","_grid.csv","_accepted_events.csv","_accepted_grid.csv","_context.csv"};
  for(size_t q=0;q<suffixes.size()+6;++q){reset("half",time_delta(.2));Fixture f(root+"/io_"+std::to_string(q));
    if(q<suffixes.size())full_output=trial_prefix(f,0)+suffixes[q];
    else {const char *extra[]={"_iteration_0_solve_delta.csv","_iteration_0_solve_weights.csv","_iteration_0_solve_context.csv","_iteration_0_trials.csv","_matrix_preflight.csv","_history.csv"};full_output=f.dir+"/loc1d"+extra[q-suffixes.size()];}
    auto error=attempt(f,"loc1d");check(output_redirects==1&&error.find("Cannot finish")!=std::string::npos,"deferred_write_failure_is_fatal");
    check(error.find("No objective-evaluable")==std::string::npos,"write_error_not_quality_exhaustion");no_final(f,"loc1d");
    check(trial_calls<=2,"write_error_stops_following_trials");
  }
  reset();Fixture io(root+"/direct_io");
  for(int kind=0;kind<2;++kind){bool caught=false;try{if(kind)write_events(io.e,"/dev/full");else write_grid(io.g,"/dev/full");}catch(const std::exception&e){caught=std::string(e.what()).find("Cannot finish")!=std::string::npos;}check(caught,"writer_flush_close_detects_full_device");}
  for(const std::string kind:{"prior_trial","prior_solve","dangling","prior_ledger"}){
    reset("half",time_delta(.2));Fixture f(root+"/"+kind);
    std::string p=kind=="prior_solve"?f.dir+"/loc1d_iteration_0_solve_delta.csv":kind=="prior_ledger"?f.dir+"/loc1d_iteration_0_trials.csv":trial_prefix(f,0)+"_ray_status.csv";
    if(kind=="dangling")fs::create_symlink("missing_invented_target",p);else{std::ofstream o(p);o<<"preserved\n";}
    auto error=attempt(f,"loc1d");check(error.find("Refusing prior")!=std::string::npos,"fresh_artifact_refusal");
    if(kind=="dangling")check(fs::is_symlink(p),"dangling_symlink_preserved");else{std::ifstream in(p);std::string line;std::getline(in,line);check(line=="preserved","prior_artifact_bytes_preserved");}
    no_final(f,"loc1d");
  }
  // Small actual cache transitions, independently compared with fresh fields.
  // One physical receiver still retains three used native event/epoch pairs.
  reset();Fixture cached(root+"/cache");cached.c.v["ray_initializer"]=1;cached.c.v["fmm_spacing"]=1;
  ForwardFields fields;auto used=observed_rays(cached.data,2,cached.s);
  for(double velocity:{5.,6.,5.}){
    Grid g=cached.g;g.v.assign(g.size(),velocity);
    auto retained=rays(g,cached.e,cached.s,cached.c,true,&used,&fields,false);
    auto fresh=rays(g,cached.e,cached.s,cached.c,true,&used,nullptr,false);
    check(fields.model.v==g.v&&fields.fields.size()==1,"cache_exact_model_transition_shared_physical_receiver");
    for(int n:used){
      check(retained[n].time==fresh[n].time&&retained[n].path==fresh[n].path&&retained[n].source==fresh[n].source&&retained[n].dv==fresh[n].dv&&retained[n].length==fresh[n].length,"cache_matches_fresh_ray_numerics");
      check(retained[n].converged==fresh[n].converged&&retained[n].initialization_attempted==fresh[n].initialization_attempted&&retained[n].initialization_succeeded==fresh[n].initialization_succeeded,"cache_matches_fresh_flags");
      check(close(retained[n].time,norm(cached.e[n/2].p)/velocity,2e-14),"cache_homogeneous_analytic_time");
    }
  }
  reset();Fixture malformed(root+"/malformed_snapshot");auto rr=rays(malformed.g,malformed.e,malformed.s,malformed.c);
  Vec r(4,.1),w(4,1),d(8);LSQRInfo info;
  for(int kind=0;kind<3;++kind){auto a=d,b=r,c=w;if(kind==0)a.pop_back();if(kind==1)b.pop_back();if(kind==2)c.pop_back();bool caught=false;
    const auto prefix=malformed.dir+"/bad_"+std::to_string(kind);
    try{write_trial_solve(prefix,malformed.c,"loc1d",0,0,malformed.g,malformed.e,malformed.data,a,b,c,info,1,true);}catch(const std::exception&e){caught=std::string(e.what()).find("incomplete original solve")!=std::string::npos;}
    check(caught&&!fs::exists(prefix+"_accepted_events.csv"),"incomplete_snapshot_rejected_before_output");
  }
}
#endif

int main(int argc,char **argv) {
  if(argc!=2)throw std::runtime_error("Use fresh invented output directory");
  std::string root=argv[1];if(fs::exists(root))throw std::runtime_error("Existing control output");fs::create_directories(root);
  checks.open(root+"/checks.csv");checks<<"check,passed\n";
  try{
    for(const std::string mode:{"loc1d","dd"}){
      reset();Fixture f(root+"/valid_"+mode,mode=="dd"?0:.001,2);
      check(attempt(f,mode).empty(),"unmodified_all_valid_actual_inverse");
      check(solves>0&&trial_calls>0,"actual_solve_and_trial_exercised");
      auto status=output(f.dir+"/observed_status.csv");status<<"call,index,derivatives,finite,converged,initializer_attempted,initializer_success,time,gradient,raw_gradient\n"<<std::setprecision(17);
      for(size_t c=0;c<seen.size();++c)for(int i:seen[c].used){const auto &r=seen[c].rays[i];status<<c<<','<<i<<','<<seen[c].derivatives<<','<<finite_ray(r)<<','<<r.converged<<','<<r.initialization_attempted<<','<<r.initialization_succeeded<<','<<r.time<<','<<r.gradient<<','<<r.raw_gradient<<'\n';}
    }
#ifdef CANDIDATE
    candidate_controls(root);
#endif
    checks.close();std::ofstream done(root+"/completed.txt");done<<check_count<<" checks passed; invented geometry only\n";
  }catch(const std::exception &e){checks.flush();std::ofstream failure(root+"/failure.txt");failure<<e.what()<<'\n';return 1;}
  return 0;
}
