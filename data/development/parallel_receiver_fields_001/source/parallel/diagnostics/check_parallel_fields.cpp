// Invented geometry only. Raw field access is enabled solely in copied diagnostic headers.
#define main tomography_main
#include "../src/main.cpp"
#undef main
#include <cstdint>
#include <cstring>
#include <omp.h>

void prepare_test(ForwardFields &cache,const Grid &g,const std::vector<P> &receivers,
                  double h,std::size_t *failed=nullptr) {
#ifdef SERIAL_CACHE
  for(std::size_t i=0;i<receivers.size();++i) {
    try { cache.get(g,receivers[i],h); }
    catch(...) { if(failed)*failed=i; throw; }
  }
#else
  cache.prepare(g,receivers,h,failed);
#endif
}
template<class T> void scalar(std::ostream &out,const T &value) {
  out.write(reinterpret_cast<const char *>(&value),sizeof(value));
}
template<class T> void array(std::ostream &out,const std::vector<T> &values) {
  scalar(out,std::uint64_t(values.size()));
  for(const auto &value:values)scalar(out,value);
}
void string_value(std::ostream &out,const std::string &value) {
  scalar(out,std::uint64_t(value.size()));out.write(value.data(),value.size());
}
void snapshot_field(std::ostream &out,const first_arrival::Field &f) {
  scalar(out,f.receiver_);scalar(out,f.spacing_);scalar(out,f.order_);
  scalar(out,f.closed_seed_cells_);scalar(out,f.shape_);
  for(const auto &axis:f.axes_)array(out,axis);
  array(out,f.time_);array(out,f.parent_);scalar(out,f.accepted_nodes);
  scalar(out,f.stats.seed_nodes);scalar(out,f.stats.first_order_direction_evaluations);
  scalar(out,f.stats.second_order_direction_evaluations);scalar(out,f.stats.second_order_ineligible);
  scalar(out,f.stats.causal_fallback_updates);scalar(out,f.stats.root_bisection_updates);
  scalar(out,f.stats.second_neighbor_revisits);
}
void snapshot_candidate(std::ostream &out,const first_arrival::Candidate &c) {
  array(out,c.path);scalar(out,c.success);string_value(out,c.message);
  scalar(out,c.field_time);scalar(out,c.descent_steps);scalar(out,c.fallback_steps);
}
void snapshot_ray(std::ostream &out,const Ray &r) {
  scalar(out,r.time);array(out,r.path);scalar(out,r.source);array(out,r.dv);array(out,r.length);
  scalar(out,r.gradient);scalar(out,r.raw_gradient);scalar(out,r.iterations);
  scalar(out,r.merged_nodes);scalar(out,r.converged);scalar(out,r.initialization_attempted);
  scalar(out,r.initialization_succeeded);scalar(out,r.selected_fmm_seed);
  scalar(out,r.direct_seed_time);scalar(out,r.fmm_seed_time);scalar(out,r.initializer_field_time);
  scalar(out,r.initializer_fallback_steps);string_value(out,r.initializer_message);
}
int main(int argc,char **argv) {
  if(argc!=3)throw std::runtime_error("Usage: check_parallel_fields OUT THREADS");
  std::string dir=argv[1];int threads=std::stoi(argv[2]);omp_set_dynamic(0);omp_set_num_threads(threads);
  auto checks=output(dir+"/checks.csv");checks<<"name,passed\n";int failures=0;
  auto check=[&](std::string name,bool ok){checks<<name<<','<<ok<<std::endl;failures+=!ok;};
  int team=0;
#pragma omp parallel
  {
#pragma omp single
    team=omp_get_num_threads();
  }
  check("requested_team_active",team==threads);
  std::ofstream binary(dir+"/snapshot.bin",std::ios::binary);
  Grid g;g.x={-2,0,2};g.y={-2,2};g.z={-1,0,2};g.v.resize(g.size());
  for(int k=0;k<int(g.z.size());++k)for(int j=0;j<int(g.y.size());++j)for(int i=0;i<int(g.x.size());++i)
    g.v[g.id(i,j,k)]=5+.12*g.x[i]+.08*g.y[j]+.2*g.z[k];
  P b{.9,.7,-.35},c{-1.25,1.1,.65},d{-.5,-1,.75},near=b;near[0]=std::nextafter(near[0],INFINITY);
  std::vector<P> receivers{b,c,b,d,near};
  std::vector<Event> events{{{-.831,-.721,.333},0,{{"fixture_event","a"}}},
                            {{-.7,-.5,.65},0,{{"fixture_event","b"}}},
                            {{.1,-.9,1.1},0,{{"fixture_event","c"}}}};
  std::vector<Event> stations;
  for(std::size_t k=0;k<receivers.size();++k)stations.push_back({receivers[k],0,{{"fixture_receiver",std::to_string(k)}}});
  stations.push_back({{10,0,0},0,{{"fixture_receiver","unused_invalid"}}});
  std::vector<int> used{8,0,13,4,15,6,10};
  output(dir+"/fixture.cfg").close();Config config(dir+"/fixture.cfg");
  config.v={{"ray_spacing",.2},{"ray_iterations",1000},{"ray_initializer",1},{"fmm_spacing",.25}};
  ForwardFields cache;int phase=0;
  auto save_phase=[&](const Grid &model,double h){
    prepare_test(cache,model,receivers,h);
    check("phase_"+std::to_string(phase)+"_exact_unique_receivers",cache.fields.size()==4);
    scalar(binary,phase++);scalar(binary,std::uint64_t(cache.fields.size()));
    for(const auto &entry:cache.fields){
      snapshot_field(binary,*entry.second);
      for(const auto &event:events)snapshot_candidate(binary,entry.second->candidate(event.p));
    }
    Config current=config;current.v["fmm_spacing"]=h;
    auto traced=rays(model,events,stations,current,true,&used,&cache);
    check("phase_"+std::to_string(phase)+"_native_support",traced.size()==events.size()*stations.size()&&
          traced[8].initialization_succeeded&&!traced[5].initialization_attempted);
    for(const auto &ray:traced)snapshot_ray(binary,ray);
  };
  save_phase(g,.25);
  const auto *old=&cache.get(g,b,.25);
  std::reverse(receivers.begin(),receivers.end());save_phase(g,.25);
  check("cache_hit_retains_field",old==&cache.get(g,b,.25));
  check("coincident_native_epochs_share_only_field",&cache.get(g,b,.25)==&cache.get(g,stations[2].p,.25)&&
        stations[0].metadata!=stations[2].metadata);
  check("nextafter_coordinate_stays_distinct",&cache.get(g,b,.25)!=&cache.get(g,near,.25));
  auto add_extra=[&](const Grid &model,double h){cache.get(model,{.4,-.4,.3},h);check("extra_key_present",cache.fields.size()==5);};
  Grid changed=g;add_extra(g,.25);for(auto &v:changed.v)v*=1.01;save_phase(changed,.25);
  add_extra(changed,.25);changed.v[0]=std::nextafter(changed.v[0],INFINITY);save_phase(changed,.25);
  add_extra(changed,.25);changed.x[1]=.15;save_phase(changed,.25);
  add_extra(changed,.25);save_phase(changed,.125);
  binary.close();
#ifndef SERIAL_CACHE
  std::size_t failed=999;std::string message;
  std::size_t before=cache.fields.size();
  try { cache.prepare(changed,{{.2,.3,.4},{10,0,0},{-10,0,0},b},.125,&failed); }
  catch(const std::runtime_error &e){message=e.what();}
  check("worker_exception_first_request",failed==1&&message=="FMM receiver outside domain or model values missing");
  check("failed_batch_publishes_no_new_fields",cache.fields.size()==before&&cache.fields.count(P{.2,.3,.4})==0);
  const auto *retained=&cache.get(changed,b,.125);
  try { cache.prepare(changed,{b,{NAN,0,0},d},.125,&failed); }
  catch(const std::runtime_error &e){message=e.what();}
  check("nonfinite_key_rejected_before_map",failed==1&&message=="Invalid FMM receiver or requested spacing"&&
        &cache.get(changed,b,.125)==retained);
  bool rejected=false;try{cache.get(changed,{NAN,0,0},.125);}catch(const std::runtime_error &){rejected=true;}
  check("serial_get_rejects_nonfinite_key",rejected);
  Grid bad=changed;bad.v[0]=-1;rejected=false;
  try{cache.prepare(bad,{b,c},.125,&failed);}catch(const std::runtime_error &){rejected=true;}
  check("changed_model_invalidates_even_on_failure",rejected&&failed==0&&cache.fields.empty()&&cache.model.v==bad.v);
  prepare_test(cache,g,{b},.25);rejected=false;
  try{cache.prepare(g,{b,c},0,&failed);}catch(const std::runtime_error &){rejected=true;}
  check("bad_spacing_invalidates_and_propagates",rejected&&failed==0&&cache.fields.empty());
  prepare_test(cache,g,{b,c},.25);check("cache_recovers_after_failure",cache.fields.size()==2);
#endif
  std::vector<int> bad_support{5,17};std::string identified;
  try{rays(g,events,stations,config,true,&bad_support);}catch(const std::runtime_error &e){identified=e.what();}
  check("first_native_exception_context",identified.find("event 0; native receiver 5")!=std::string::npos);
  auto identified_file=output(dir+"/identified_error.bin");string_value(identified_file,identified);identified_file.close();
  // Exercise the actual CLI implementations, including ordered identifiers and h/2 refinement.
  write_events(events,dir+"/initial_events.csv");write_events(stations,dir+"/stations.csv");write_grid(g,dir+"/initial_grid.csv");
  auto cfg=output(dir+"/fixture.cfg");for(const auto &entry:config.v)cfg<<entry.first<<' '<<entry.second<<'\n';cfg.close();
  auto obs=output(dir+"/observations.csv");obs<<"i,j,station,type,value,fixture_observation\n";
  for(int n:used)obs<<n/int(stations.size())<<",-1,"<<n%stations.size()<<",0,1,absolute_"<<n<<'\n';obs.close();
  auto samples=output(dir+"/ray_samples.csv");samples<<"event,station\n";
  for(int n:used)samples<<n/int(stations.size())<<','<<n%stations.size()<<'\n';samples.close();
  raycheck(config,dir,"initial");linearize(config,dir,"initial");
  check("all_sample_rows_written",csv_table(dir+"/initial_ray_convergence.csv").rows.size()==used.size());
  return failures?1:0;
}
