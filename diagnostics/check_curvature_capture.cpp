// Invented telemetry and small invented rays only. The included driver is a
// frozen, instrumented copy; no authoritative input file is read by this main.
#include "fixture_driver.hpp"
#include <cstdint>
#include <cstring>
#include <functional>

namespace fixture {
std::vector<std::pair<std::string,bool>> checks;
void check(const std::string &name,bool value) {
  checks.emplace_back(name,value);
  if(!value) throw std::runtime_error("Failed invented control: "+name);
}
bool bits(double a,double b) {
  std::uint64_t x,y;std::memcpy(&x,&a,8);std::memcpy(&y,&b,8);return x==y;
}
bool vector_bits(const Vec &a,const Vec &b) {
  if(a.size()!=b.size())return false;
  for(size_t i=0;i<a.size();++i)if(!bits(a[i],b[i]))return false;
  return true;
}
bool point_bits(P a,P b) {
  for(int i=0;i<3;++i)if(!bits(a[i],b[i]))return false;return true;
}
bool path_bits(const std::vector<P> &a,const std::vector<P> &b) {
  if(a.size()!=b.size())return false;
  for(size_t i=0;i<a.size();++i)if(!point_bits(a[i],b[i]))return false;return true;
}
bool ray_bits(const Ray &a,const Ray &b) {
  return bits(a.time,b.time)&&vector_bits(a.dv,b.dv)&&vector_bits(a.length,b.length)&&
    point_bits(a.source,b.source)&&path_bits(a.path,b.path)&&a.iterations==b.iterations&&
    a.merged_nodes==b.merged_nodes&&bits(a.gradient,b.gradient)&&bits(a.raw_gradient,b.raw_gradient)&&
    a.converged==b.converged&&a.initialization_attempted==b.initialization_attempted&&
    a.initialization_succeeded==b.initialization_succeeded&&a.selected_fmm_seed==b.selected_fmm_seed&&
    bits(a.direct_seed_time,b.direct_seed_time)&&bits(a.fmm_seed_time,b.fmm_seed_time)&&
    bits(a.initializer_field_time,b.initializer_field_time)&&a.initializer_fallback_steps==b.initializer_fallback_steps&&
    a.initializer_message==b.initializer_message;
}
std::string bytes(const std::string &name) {
  std::ifstream f(name,std::ios::binary);return std::string(std::istreambuf_iterator<char>(f),{});
}
const std::string &field(const CsvTable &t,size_t row,const std::string &key) {
  auto p=std::find(t.header.begin(),t.header.end(),key);
  if(p==t.header.end())throw std::runtime_error("Missing column "+key);
  return t.rows.at(row).at(size_t(p-t.header.begin()));
}
double num(const CsvTable &t,size_t row,const std::string &key) {return std::stod(field(t,row,key));}
std::vector<size_t> rows(const CsvTable &t,const std::string &run) {
  std::vector<size_t> result;for(size_t i=0;i<t.rows.size();++i)if(field(t,i,"run_id")==run)result.push_back(i);return result;
}
bool rejects(const std::function<void()> &f) {try{f();}catch(const std::runtime_error &){return true;}return false;}
const std::vector<std::string> names={"curvature_pairs.csv","curvature_components.csv",
  "curvature_selected_geometry.csv","curvature_selected_cuts.csv","curvature_initialization.csv",
  "curvature_seed_metadata.csv","curvature_memory_events.csv"};
Grid model(int kind) {
  Grid g;g.x=g.y=g.z={-2,0,2};g.v.resize(g.size());
  for(int k=0;k<3;++k)for(int j=0;j<3;++j)for(int i=0;i<3;++i)
    g.v[g.id(i,j,k)]=5+(kind==1?.3*g.z[k]+.1*g.x[i]:kind==2?.25*std::max(g.z[k],0.):0);
  return g;
}
}

int main(int argc,char **argv) {
  using namespace fixture;
  if(argc!=2)throw std::runtime_error("Expected fresh invented output directory");
  const std::string out=argv[1],capture=out+"/capture";
  if(std::filesystem::exists(out))throw std::runtime_error("Control output already exists");
  std::filesystem::create_directories(capture);curvature_open(capture);
  curvature_capture_active=true;
  Grid g=model(0);
  std::vector<P> base={{-1.5,-.7,-.8},{std::nextafter(.125,1.),-0.,.375},
                       {1.,.8,.9},{1.4,1.2,1.3}};
  auto after=base;
  Vec grad={1,2,3,4,5,6},ng={-1,-2,-3,-4,-5,-6},q(6,0),s(6,0),y(6,0);
  std::vector<Vec> S,Y;
  const std::string quoted="invented,\"frame\"\nrecord";
  audit_run=quoted;audit_observation="invented,\"17\"\nkey";
  first_arrival::Candidate seed;seed.path=base;seed.path[1][2]=std::ldexp(1.,-900);
  seed.success=true;seed.field_time=std::nextafter(1.,2.);seed.descent_steps=7;seed.fallback_steps=2;
  seed.message="invented,\"seed\"\nmessage";
  curvature_seed(seed);curvature_begin(base);
  s={1e16,1,-1e16,0,0,0};y={1,1,1,0,0,0};
  const double computed=dot(s,y);
  check("invented_cancellation_differs_from_exact_integer_dot",computed==0);
  curvature_pair(0,1,g,base,after,grad,ng,q,s,y,computed,false,1,2,1.5,-.25,3,S,Y);
  curvature_flush();
  auto init=csv_table(capture+"/"+names[4]),meta=csv_table(capture+"/"+names[5]);
  bool initial=true;
  for(size_t i=0;i<2*base.size();++i) {
    initial&=field(init,i,"run_id")==quoted&&field(init,i,"observation_index")==audit_observation&&
      std::stoul(field(init,i,"node"))==i%base.size()&&field(init,i,"kind")==(i<base.size()?"raw_fmm_seed":"post_resampling_and_merge");
    for(int axis=0;axis<3;++axis)initial&=bits(num(init,i,std::string(1,"xyz"[axis])),(i<base.size()?seed.path:base)[i%base.size()][axis]);
  }
  check("quoted_ids_seed_and_initial_frames_binary64_round_trip",initial&&init.rows.size()==8);
  check("seed_metadata_round_trip",meta.rows.size()==1&&field(meta,0,"message")==seed.message&&
    bits(num(meta,0,"field_time_s"),seed.field_time)&&field(meta,0,"success")=="1"&&
    field(meta,0,"descent_steps")=="7"&&field(meta,0,"fallback_steps")=="2");
  auto pairs=csv_table(capture+"/"+names[0]);
  check("supplied_computed_sy_and_retention_not_replaced",bits(num(pairs,0,"computed_sy"),0)&&field(pairs,0,"retained")=="0");

  audit_run="invented_rounded_displacement";audit_observation="invented_empty_location_";
  curvature_begin(base);s={-0.,std::ldexp(1.,-900),0,std::ldexp(1.,-54),0,0};q=s;y={0,0,0,1,0,0};after=base;
  for(size_t n=1;n+1<base.size();++n)for(int a=0;a<3;++a)after[n][a]+=q[3*(n-1)+a];
  curvature_pair(1,2,g,base,after,grad,ng,q,s,y,0,false,1,2,1.5,-.25,3,S,Y);curvature_flush();
  auto components=csv_table(capture+"/"+names[1]);auto rr=rows(components,audit_run);
  check("signed_zero_and_tiny_component_round_trip",rr.size()==2&&bits(num(components,rr[0],"s_x"),-0.)&&bits(num(components,rr[0],"s_y"),s[1]));
  check("stored_step_direction_separate_from_rounded_displacement",bits(num(components,rr[1],"s_x"),std::ldexp(1.,-54))&&bits(num(components,rr[1],"rounded_displacement_x"),0));

  audit_run="invented_threshold";curvature_begin(base);S.clear();Y.clear();
  Vec thresholds={std::nextafter(1e-14,0.),1e-14,std::nextafter(1e-14,INFINITY)};
  for(size_t i=0;i<thresholds.size();++i) {
    s.assign(6,0);y.assign(6,0);s[0]=1;y[0]=thresholds[i];const bool keep=thresholds[i]>1e-14;
    if(keep){S.push_back(s);Y.push_back(y);}
    curvature_pair(int(i),int(i+1),g,base,base,grad,ng,q,s,y,thresholds[i],keep,1,2,1.5,-.25,1,S,Y);
  }
  curvature_flush();pairs=csv_table(capture+"/"+names[0]);rr=rows(pairs,audit_run);bool threshold_ok=rr.size()==3;
  for(size_t i=0;i<rr.size();++i)threshold_ok&=bits(num(pairs,rr[i],"computed_sy"),thresholds[i])&&
    bits(num(pairs,rr[i],"threshold"),1e-14)&&field(pairs,rr[i],"retained")== (i==2?"1":"0");
  check("strict_threshold_and_adjacent_binary64_values",threshold_ok);

  audit_run="invented_memory";curvature_begin(base);S.clear();Y.clear();
  for(int i=0;i<10;++i) {
    s.assign(6,0);y.assign(6,0);s[0]=i+1;y[0]=2;bool keep=i!=5;
    if(keep){if(S.size()==8){S.erase(S.begin());Y.erase(Y.begin());}S.push_back(s);Y.push_back(y);}
    curvature_pair(10+i,11+i,g,base,base,grad,ng,q,s,y,keep?2*(i+1):0,keep,1,2,1.5,-.25,1,S,Y);
  }
  curvature_memory_clear(25,"invented_reset");curvature_flush();
  pairs=csv_table(capture+"/"+names[0]);rr=rows(pairs,audit_run);
  check("memory_eight_pair_eviction_keeps_original_ids",rr.size()==10&&field(pairs,rr.back(),"memory_before_ids")=="10;11;12;13;14;16;17;18"&&field(pairs,rr.back(),"memory_after_ids")=="11;12;13;14;16;17;18;19");
  check("rejected_pair_keeps_memory",field(pairs,rr[5],"memory_before_ids")==field(pairs,rr[5],"memory_after_ids"));
  check("memory_ages_are_iteration_minus_retained_id",field(pairs,rr.back(),"memory_after_ages")=="8;7;6;5;3;2;1;0");
  auto events=csv_table(capture+"/"+names[6]);
  check("reset_records_old_memory_then_clears",events.rows.size()==1&&field(events,0,"previous_ids")=="11;12;13;14;16;17;18;19"&&
    field(events,0,"previous_ages")=="14;13;12;11;9;8;7;6"&&curvature_memory_ids.empty()&&curvature_memory_s.empty()&&curvature_memory_y.empty());

  audit_run="invented_selected";base={{-1.5,-1.3,-1.1},{.0001,.4,.6},{.8,.9,1.},{1.4,1.2,1.3}};
  after=base;after[1][0]=.0002;grad={1,2,3,9,5,6};ng={2,3,4,10,6,7};q={.1,.2,.3,.4,.5,.6};s=q;y=grad;
  curvature_begin(base);S.clear();Y.clear();
  for(int iteration:{32,33})curvature_pair(iteration,iteration+1,g,base,after,grad,ng,q,s,y,0,false,.5,2,1.5,-.25,1,S,Y);
  curvature_flush();auto geometry=csv_table(capture+"/"+names[2]);rr=rows(geometry,audit_run);bool frames=rr.size()==8;
  for(size_t n=0;n<rr.size();++n) {
    size_t row=rr[n],node=n%4;bool next=n>=4,endpoint=node==0||node==3;
    frames&=field(geometry,row,"iteration")=="33"&&field(geometry,row,"state")==(next?"accepted":"base")&&
      std::stoul(field(geometry,row,"node"))==node&&field(geometry,row,"is_endpoint")== (endpoint?"1":"0");
    for(int a=0;a<3;++a){std::string axis(1,"xyz"[a]);frames&=bits(num(geometry,row,axis),(next?after:base)[node][a]);
      if(endpoint)frames&=field(geometry,row,"gradient_"+axis).empty()&&field(geometry,row,"q_"+axis).empty();
      else frames&=bits(num(geometry,row,"gradient_"+axis),(next?ng:grad)[3*(node-1)+a])&&bits(num(geometry,row,"q_"+axis),q[3*(node-1)+a]);}
  }
  check("selected_iteration_inventory_and_full_base_accepted_frames",frames);
  auto cuts=csv_table(capture+"/"+names[3]);rr=rows(cuts,audit_run);bool edges=rr.size()==72;
  for(size_t row:rr){bool closest=field(cuts,row,"selection")=="closest_internal_plane";int selected=closest?1:2;
    int end=std::stoi(field(cuts,row,"edge_end_node"));edges&=std::stoi(field(cuts,row,"selected_node"))==selected&&(end==selected||end==selected+1)&&field(cuts,row,"iteration")=="33";}
  check("closest_and_largest_gradient_both_adjacent_edge_inventories",edges);

  const Vec deltas={1e-12,std::nextafter(1e-12,INFINITY),1,1,1,1};
  const Vec planes={.5e-12,.5e-12,1e-10,std::nextafter(1e-10,INFINITY),1-1e-10,std::nextafter(1-1e-10,0.)};
  for(size_t i=0;i<deltas.size();++i){audit_run="invented_cut_"+std::to_string(i);Grid cg=g;cg.x={0,planes[i],2};
    std::vector<P> cp={{0,0,0},{deltas[i],0,0}};curvature_edge_cuts(33,"base","predicate",1,1,cg,cp);}
  curvature_flush();cuts=csv_table(capture+"/"+names[3]);bool predicates=true;
  for(size_t i=0;i<deltas.size();++i){auto cr=rows(cuts,"invented_cut_"+std::to_string(i));size_t row=cr.at(1);
    bool used=i==1||i==3||i==5;predicates&=cr.size()==9&&field(cuts,row,"axis_test_pass")== (i==0?"0":"1")&&
      field(cuts,row,"used")== (used?"1":"0")&&field(cuts,row,"parameter_test_pass")==field(cuts,row,"used");
    if(i==0)predicates&=field(cuts,row,"parameter").empty();else predicates&=bits(num(cuts,row,"parameter"),planes[i]/deltas[i]);}
  check("cut_strict_axis_and_parameter_boundaries_nextafter",predicates);

  audit_run="invented_guards";curvature_begin(base);S.clear();Y.clear();
  for(int bad=0;bad<7;++bad) {
    auto b=base,a=after;Vec gg=grad,nn=ng,qq=q,ss=s,yy=y;
    if(bad==0)b.resize(2);if(bad==1)a.pop_back();if(bad==2)gg.pop_back();if(bad==3)nn.pop_back();
    if(bad==4)qq.pop_back();if(bad==5)ss.pop_back();if(bad==6)yy.pop_back();
    check("dimension_rejection_"+std::to_string(bad),rejects([&]{curvature_pair(1,2,g,b,a,gg,nn,qq,ss,yy,0,false,1,2,1,-1,1,S,Y);}));
  }
  check("actual_memory_mismatch_rejected",rejects([&]{curvature_pair(1,2,g,base,after,grad,ng,q,s,y,1,true,1,2,1,-1,1,S,Y);}));
  curvature_begin(base);curvature_flush();std::vector<std::string> saved;for(const auto &name:names)saved.push_back(bytes(capture+"/"+name));
  curvature_capture_active=false;curvature_begin({});curvature_seed(seed);curvature_memory_clear(77,"disabled");
  curvature_pair(77,78,g,{}, {},{}, {},{}, {},{},0,false,1,2,1,-1,1,{},{});curvature_flush();
  bool no_op=curvature_memory_ids.empty();for(size_t i=0;i<names.size();++i)no_op&=bytes(capture+"/"+names[i])==saved[i];
  check("disabled_public_hooks_leave_files_and_memory_unchanged",no_op);
  check("existing_output_rejected",rejects([&]{curvature_open(capture);}));
  bool no_overwrite=true;for(size_t i=0;i<names.size();++i)no_overwrite&=bytes(capture+"/"+names[i])==saved[i];
  check("overwrite_rejection_preserves_all_seven_tables",no_overwrite);

  std::ofstream parity(out+"/invented_ray_parity.csv");parity<<std::setprecision(17);
  parity<<"run_id,model,seeded,time_s,iterations,converged,gradient,path_points,bitwise_equal\n";
  audit_history=nullptr;audit_metric_file=nullptr;
  for(int kind=0;kind<3;++kind)for(bool seeded:{false,true}) {
    const Grid mg=model(kind);P a={-1.5,-.7,-.8},b={1.4,.8,.9};std::vector<P> path={a,{-.1,.7,-.3},b};
    audit_run="invented_ray_"+std::to_string(kind)+(seeded?"_seeded":"_straight");audit_observation="invented_only";
    curvature_capture_active=true;
    Ray observed=observed_trace(mg,a,b,.5,80,true,seeded?&path:nullptr);
    curvature_capture_active=false;Ray original=trace(mg,a,b,.5,80,true,seeded?&path:nullptr);
    const bool same=ray_bits(observed,original);
    check(audit_run+"_logging_bitwise_neutral",same);
    check(audit_run+"_finite_domain_exact_endpoints",std::isfinite(observed.time)&&std::isfinite(observed.gradient)&&
      point_bits(observed.path.front(),a)&&point_bits(observed.path.back(),b)&&
      std::all_of(observed.path.begin(),observed.path.end(),[&](P p){return mg.contains(p);}));
    parity<<audit_run<<','<<kind<<','<<seeded<<','<<observed.time<<','<<observed.iterations<<','<<observed.converged<<','<<observed.gradient<<','<<observed.path.size()<<','<<same<<'\n';
  }
  curvature_flush();pairs=csv_table(capture+"/"+names[0]);size_t ray_records=0;
  for(size_t i=0;i<pairs.rows.size();++i)if(field(pairs,i,"run_id").find("invented_ray_")==0)++ray_records;
  check("actual_invented_trace_hooks_capture_accepted_pairs",ray_records>0);
  std::ofstream report(out+"/checks.csv");report<<"check,passed\n";for(const auto &c:checks)report<<c.first<<','<<c.second<<'\n';
  report.flush();parity.flush();if(!report||!parity)throw std::runtime_error("Incomplete controls output");
  std::cout<<checks.size()<<" invented controls passed; "<<ray_records<<" actual invented accepted-pair records\n";
}
