// Invented Candidate files and one homogeneous seeded ray only. Never invoke
// the included driver's renamed native main or construct a receiver field.
#include "fixture_driver.hpp"
#include "extracted_retention.hpp"
#include <cstdint>
#include <cstring>
#include <functional>

namespace fixture {
std::ofstream checks, rejections;
std::size_t check_count=0;
void check(const std::string &name,bool passed) {
  checks<<csv_quote(name)<<','<<passed<<std::endl;
  ++check_count;
  if(!checks||!passed)throw std::runtime_error("Invented control failed: "+name);
}
std::string number(double value) {
  std::ostringstream out;out<<std::setprecision(17)<<value;return out.str();
}
std::string bits(double value) {
  std::uint64_t word;std::memcpy(&word,&value,sizeof word);
  std::ostringstream out;out<<std::hex<<std::setfill('0')<<std::setw(16)<<word;return out.str();
}
void point(std::ostream &out,P p) {for(double value:p)out<<bits(value)<<' ';out<<'\n';}
std::string candidate_bits(const first_arrival::Candidate &candidate) {
  std::ostringstream out;
  out<<candidate.success<<' '<<bits(candidate.field_time)<<' '<<candidate.descent_steps<<' '
     <<candidate.fallback_steps<<' '<<csv_quote(candidate.message)<<'\n'<<candidate.path.size()<<'\n';
  for(P p:candidate.path)point(out,p);
  return out.str();
}
std::string ray_bits(const Ray &ray) {
  std::ostringstream out;
  out<<bits(ray.time)<<' '<<ray.iterations<<' '<<ray.merged_nodes<<' '
     <<bits(ray.gradient)<<' '<<bits(ray.raw_gradient)<<' '<<ray.converged<<' '
     <<ray.initialization_attempted<<' '<<ray.initialization_succeeded<<' '<<ray.selected_fmm_seed<<' '
     <<bits(ray.direct_seed_time)<<' '<<bits(ray.fmm_seed_time)<<' '<<bits(ray.initializer_field_time)<<' '
     <<ray.initializer_fallback_steps<<' '<<csv_quote(ray.initializer_message)<<'\n';
  point(out,ray.source);out<<ray.path.size()<<'\n';for(P p:ray.path)point(out,p);
  for(const Vec *v:{&ray.dv,&ray.length}) {out<<v->size()<<'\n';for(double x:*v)out<<bits(x)<<'\n';}
  return out.str();
}
void write(const std::string &path,const std::string &text) {
  std::ofstream out(path,std::ios::binary);out<<text;out.close();
  if(!out)throw std::runtime_error("Cannot write fixture: "+path);
}
void table(const std::string &path,const CsvTable &data) {
  std::ostringstream out;
  auto row=[&](const Strings &r) {
    for(std::size_t i=0;i<r.size();++i)out<<(i?",":"")<<csv_quote(r[i]);out<<'\n';
  };
  row(data.header);for(const auto &r:data.rows)row(r);write(path,out.str());
}
std::pair<CsvTable,CsvTable> tables(const first_arrival::Candidate &candidate,
    const std::vector<P> &resampled,const std::string &run,const std::string &observation) {
  CsvTable path{{"run_id","observation_index","kind","node","x","y","z"},{}};
  for(bool second:{false,true}) {
    const auto &frame=second?resampled:candidate.path;
    for(std::size_t i=0;i<frame.size();++i)path.rows.push_back({run,observation,
      second?"post_resampling_and_merge":"raw_fmm_seed",std::to_string(i),
      number(frame[i][0]),number(frame[i][1]),number(frame[i][2])});
  }
  CsvTable metadata{{"run_id","observation_index","field_time_s","success",
    "descent_steps","fallback_steps","message"},{{run,observation,number(candidate.field_time),
    candidate.success?"1":"0",std::to_string(candidate.descent_steps),
    std::to_string(candidate.fallback_steps),candidate.message}}};
  return {path,metadata};
}
const std::string &field(const CsvTable &t,std::size_t row,const std::string &name) {
  auto found=std::find(t.header.begin(),t.header.end(),name);
  if(found==t.header.end())throw std::runtime_error("Missing history column: "+name);
  return t.rows.at(row).at(std::size_t(found-t.header.begin()));
}
Grid model() {Grid g;g.x=g.y=g.z={-2,0,2};g.v.assign(g.size(),5);return g;}

void loader_controls(const std::string &out) {
  const Grid g=model();const P a={-1.5,-.7,-.8},b={1.4,1.2,1.3};
  first_arrival::Candidate original;
  original.path={a,{std::nextafter(.125,1.),-0.,std::ldexp(1.,-900)},{1.,.8,.9},b};
  original.success=true;original.field_time=std::nextafter(1.,2.);
  original.descent_steps=7;original.fallback_steps=2;original.message="invented,\"seed\"\nmessage";
  const std::string run="invented,\"frame\"\nrecord",observation="invented,\"17\"\nkey";
  // Deliberately different valid post frame: the loader structurally validates
  // it, but returns raw only. Actual trace resampling is tested separately.
  const std::vector<P> post={a,{.4,.2,.3},b};
  const auto baseline=tables(original,post,run,observation);
  const std::string directory=out+"/loader";std::filesystem::create_directories(directory);
  auto load=[&](const std::string &name,const CsvTable &path,const CsvTable &metadata) {
    const std::string stem=directory+"/"+name;
    table(stem+"_path.csv",path);table(stem+"_metadata.csv",metadata);
    return read_saved_candidate(g,a,b,run,observation,stem+"_path.csv",stem+"_metadata.csv");
  };
  auto loaded=load("roundtrip",baseline.first,baseline.second);
  check("complete_candidate_normal_binary64_and_quoted_string_roundtrip",candidate_bits(loaded)==candidate_bits(original));
  write(out+"/candidate_bits.txt",candidate_bits(loaded));
  auto empty=baseline.second;empty.rows[0][6]="";
  check("empty_message_preserved",load("empty_message",baseline.first,empty).message.empty());
  auto signed_zero=baseline.second;signed_zero.rows[0][2]="-0";
  check("signed_zero_field_time_preserved",bits(load("signed_zero",baseline.first,signed_zero).field_time)==bits(-0.));
  auto post_changed=baseline.first;post_changed.rows[5][4]="0.6";
  check("post_frame_structural_validation_does_not_claim_resampling_equivalence",
    candidate_bits(load("different_valid_post",post_changed,baseline.second))==candidate_bits(original));
  auto reject=[&](const std::string &name,const std::function<void(CsvTable&,CsvTable&)> &change) {
    auto path=baseline.first,metadata=baseline.second;change(path,metadata);
    bool rejected=false;std::string message;
    try {load(name,path,metadata);}catch(const std::exception &e){rejected=true;message=e.what();}
    rejections<<csv_quote(name)<<','<<rejected<<','<<csv_quote(message)<<std::endl;
    check("loader_reject_"+name,rejected);
  };
  reject("reordered_path_header",[](CsvTable &p,CsvTable&){std::swap(p.header[0],p.header[1]);});
  reject("reordered_metadata_header",[](CsvTable&,CsvTable &m){std::swap(m.header[0],m.header[1]);});
  reject("extra_column",[](CsvTable &p,CsvTable&){p.header.push_back("extra");for(auto &r:p.rows)r.push_back("");});
  reject("missing_column",[](CsvTable&,CsvTable &m){m.header.pop_back();m.rows[0].pop_back();});
  reject("duplicate_header",[](CsvTable &p,CsvTable&){p.header[1]=p.header[0];});
  reject("short_row",[](CsvTable &p,CsvTable&){p.rows[1].pop_back();});
  reject("no_metadata",[](CsvTable&,CsvTable &m){m.rows.clear();});
  reject("duplicate_metadata",[](CsvTable&,CsvTable &m){m.rows.push_back(m.rows[0]);});
  for(int column:{0,1}) {
    reject("metadata_identity_"+std::to_string(column),[=](CsvTable&,CsvTable &m){m.rows[0][column]="wrong";});
    reject("path_identity_"+std::to_string(column),[=](CsvTable &p,CsvTable&){p.rows[1][column]="wrong";});
  }
  for(const std::string bad:{"0","true","1.0",""})
    reject("success_"+(bad.empty()?"empty":bad),[=](CsvTable&,CsvTable &m){m.rows[0][3]=bad;});
  for(int column:{4,5})for(const std::string bad:{"-1","0.5","nan","inf","2147483648","2junk",""})
    reject("counter_"+std::to_string(column)+"_"+(bad.empty()?"empty":bad),
      [=](CsvTable&,CsvTable &m){m.rows[0][column]=bad;});
  for(const std::string bad:{"-1","nan","inf","1junk",""})
    reject("field_time_"+(bad.empty()?"empty":bad),[=](CsvTable&,CsvTable &m){m.rows[0][2]=bad;});
  for(const std::string bad:{"-1","0","2","0.5","nan","inf","2147483648","1junk"})
    reject("node_"+bad,[=](CsvTable &p,CsvTable&){p.rows[1][3]=bad;});
  reject("missing_raw",[](CsvTable &p,CsvTable&){p.rows.erase(p.rows.begin(),p.rows.begin()+4);});
  reject("missing_post",[](CsvTable &p,CsvTable&){p.rows.resize(4);});
  reject("raw_after_post",[](CsvTable &p,CsvTable&){p.rows.push_back(p.rows[0]);});
  reject("duplicate_post_frame",[](CsvTable &p,CsvTable&){p.rows.push_back(p.rows[4]);});
  reject("unknown_frame",[](CsvTable &p,CsvTable&){p.rows[1][2]="other";});
  reject("two_point_raw",[](CsvTable &p,CsvTable&){p.rows.erase(p.rows.begin()+1,p.rows.begin()+3);p.rows[1][3]="1";});
  reject("two_point_post",[](CsvTable &p,CsvTable&){p.rows.erase(p.rows.begin()+5);p.rows.back()[3]="1";});
  for(const std::string bad:{"nan","inf","-inf","2.1","1junk"})
    reject("coordinate_"+bad,[=](CsvTable &p,CsvTable&){p.rows[1][4]=bad;});
  for(int row:{0,3,4,6})
    reject("endpoint_"+std::to_string(row),[=](CsvTable &p,CsvTable&){p.rows[row][4]=number(std::nextafter(std::stod(p.rows[row][4]),0.));});

  // std::stod may throw ERANGE on subnormal strings. Report the actual result;
  // do not expand the loader or the normal-finite round-trip claim to hide it.
  auto tiny=baseline.second;tiny.rows[0][2]=number(std::numeric_limits<double>::denorm_min());
  std::string outcome;bool parsed=false;double parsed_value=0;
  try {
    const auto candidate=load("subnormal_parse",baseline.first,tiny);
    parsed=true;parsed_value=candidate.field_time;
    outcome="accepted with exact bits";
  }catch(const std::exception &e){outcome="rejected: "+std::string(e.what());}
  if(parsed)check("accepted_subnormal_parse_keeps_exact_bits",bits(parsed_value)==bits(std::numeric_limits<double>::denorm_min()));
  write(out+"/subnormal_parse_behavior.txt",outcome+"\n");
}

void retention_controls(const std::string &out,bool positive) {
  std::ofstream cases(out+"/retention_cases.csv");
  cases<<"case,computed_sy,sy_bits,expected_old,expected_positive,actual_keep,reciprocal,reciprocal_bits,reciprocal_finite,interpretation\n";
  auto test=[&](const std::string &name,double sy,bool old_expected,bool positive_expected,const std::string &scope) {
    const bool keep=extracted_retention(sy);volatile double denominator=sy;
    const double reciprocal=1./denominator;
    cases<<name<<','<<number(sy)<<','<<bits(sy)<<','<<old_expected<<','<<positive_expected<<','<<keep<<','
      <<number(reciprocal)<<','<<bits(reciprocal)<<','<<std::isfinite(reciprocal)<<','<<csv_quote(scope)<<std::endl;
    check("actual_extracted_predicate_"+name,keep==(positive?positive_expected:old_expected));
    return reciprocal;
  };
  test("negative",-1,false,false,"negative curvature rejected");
  test("negative_zero",-0.,false,false,"zero rejected; reciprocal remains negative infinity");
  test("positive_zero",0,false,false,"zero rejected; reciprocal remains positive infinity");
  test("below_old",std::nextafter(1e-14,0.),false,true,"adjacent binary64 below old cutoff");
  test("at_old",1e-14,false,true,"strict old cutoff");
  test("above_old",std::nextafter(1e-14,INFINITY),true,true,"adjacent binary64 above old cutoff");
  test("unit",1,true,true,"finite positive curvature");
  test("minimum_normal",std::numeric_limits<double>::min(),false,true,"positive normal; reciprocal finite");
  const double unsafe=test("minimum_subnormal",std::numeric_limits<double>::denorm_min(),false,true,
    "failed generalization: positive retention permits reciprocal overflow");
  check("positive_subnormal_reciprocal_overflows",std::isinf(unsafe)&&unsafe>0);
  test("positive_infinity",INFINITY,true,true,"both predicates admit infinity; not a safe retention rule");
  test("negative_infinity",-INFINITY,false,false,"negative infinity rejected");
  test("nan",NAN,false,false,"unordered comparison rejects NaN");
  for(int exponent:{-30,0,30}) {
    const double scale=std::ldexp(1.,exponent);const Vec s={scale},y={scale};
    const double sy=dot(s,y);
    check("exact_power_two_dot_"+std::to_string(exponent),sy==std::ldexp(1.,2*exponent));
    test("scaled_dot_"+std::to_string(exponent),sy,exponent>=0,true,
      "same positive geometry under scaling; absolute cutoff is not scale invariant");
  }
  const double cancellation=dot(Vec{1e16,1,-1e16},Vec{1,1,1});
  check("core_dot_cancellation_loses_exact_positive_integer_sum",cancellation==0);
  test("cancelled_dot",cancellation,false,false,"exact real dot is one; binary64 sequential sum is zero");
  const double reordered=dot(Vec{1e16,-1e16,1},Vec{1,1,1});
  check("reordered_core_dot_retains_same_exact_sum",reordered==1);
  test("reordered_dot",reordered,true,true,"same exact dot; different binary64 addition order");
  const double underflow=dot(Vec{std::ldexp(1.,-600)},Vec{std::ldexp(1.,-600)});
  check("core_dot_underflows_positive_real_product",underflow==0);
  test("underflowed_dot",underflow,false,false,"exact positive 2^-1200 underflows to zero");
  const double overflow=dot(Vec{1e308},Vec{2});
  check("core_dot_overflows_finite_operands",std::isinf(overflow)&&overflow>0);
  test("overflowed_dot",overflow,true,true,"finite operands overflow to accepted infinite dot");
  cases.close();check("retention_cases_written",bool(cases));
}

void trace_controls(const std::string &out) {
  const Grid g=model();const P a={-1.5,-.7,-.8},b={1.4,.8,.9};
  first_arrival::Candidate candidate;candidate.path={a,{-.1,.7,-.3},b};candidate.success=true;
  candidate.field_time=1;candidate.descent_steps=2;candidate.message="invented seed; no FMM field";
  auto input=tables(candidate,{a,(a+b)*.5,b},"invented_trace","invented_only");
  table(out+"/trace_seed_path.csv",input.first);table(out+"/trace_seed_metadata.csv",input.second);
  const auto loaded=read_saved_candidate(g,a,b,"invented_trace","invented_only",out+"/trace_seed_path.csv",out+"/trace_seed_metadata.csv");
  check("trace_seed_loaded_raw_bits_exact",candidate_bits(loaded)==candidate_bits(candidate));
  const Ray original=trace(g,a,b,.5,80,true,&candidate.path);
  const Ray replay=trace(g,a,b,.5,80,true,&loaded.path);
  check("loaded_raw_seed_trace_full_ray_bit_parity",ray_bits(original)==ray_bits(replay));
  std::ofstream history(out+"/history.csv");history<<std::setprecision(17);
  history<<"run_id,observation_index,phase,iteration,updates,time_s,projected_gradient,raw_gradient,action_change_s,accepted_step,feasible_initial_step,directional_slope,line_search_evaluations,memory_pairs,gradient_fallback,merged_nodes,curvature_pair_accepted,max_node_step_km,path_nodes,min_segment_km,max_segment_km,tangential_gradient_norm,normal_gradient_norm,min_internal_grid_plane_distance_km,x_min_active,x_max_active,y_min_active,y_max_active,z_min_active,z_max_active\n";
  audit_run="invented_trace";audit_observation="invented_only";audit_history=&history;audit_metric_file=nullptr;
  const Ray observed=observed_trace(g,a,b,.5,80,true,&loaded.path);audit_history=nullptr;history.close();
  check("history_written",bool(history));
  check("observed_and_actual_trace_full_ray_bit_parity",ray_bits(observed)==ray_bits(original));
  write(out+"/ray_bits.txt",ray_bits(original));
  const auto h=csv_table(out+"/history.csv");int accepted=0,retained=0,failed=0;
  for(std::size_t i=0;i<h.rows.size();++i) {
    if(field(h,i,"phase")=="accepted") {++accepted;retained+=field(h,i,"curvature_pair_accepted")=="1";}
    failed+=field(h,i,"phase")=="line_search_failed";
  }
  // For B, the actual observed retention flag proves its sole computed sy was
  // greater than 1e-14. No newly retained pair is exercised by this parity ray.
  check("homogeneous_one_update_one_retained_pair",accepted==1&&retained==1&&failed==0&&original.iterations==1);
  check("homogeneous_converged_no_merge",original.converged&&original.merged_nodes==0);
  check("homogeneous_time_matches_straight_analytic_limit",std::abs(original.time-norm(b-a)/5)<2e-15);
  check("invented_trace_exact_endpoints_and_domain",original.path.front()==a&&original.path.back()==b&&
    std::all_of(original.path.begin(),original.path.end(),[&](P p){return g.contains(p);}));
  write(out+"/trace_summary.csv","time_s,iterations,converged,gradient,path_nodes,accepted_pairs,retained_pairs\n"+
    number(original.time)+","+std::to_string(original.iterations)+","+std::to_string(original.converged)+","+
    number(original.gradient)+","+std::to_string(original.path.size())+","+std::to_string(accepted)+","+std::to_string(retained)+"\n");
}
}

int main(int argc,char **argv) {
  using namespace fixture;
  if(argc!=3)throw std::runtime_error("Usage: check_seeded_retention FRESH_OUTPUT seed_loaded_B|positive_curvature");
  const std::string out=argv[1],variant=argv[2];
  if(variant!="seed_loaded_B"&&variant!="positive_curvature")throw std::runtime_error("Unknown invented variant");
  if(std::filesystem::exists(out))throw std::runtime_error("Fresh output required");
  std::filesystem::create_directories(out);
  checks.open(out+"/checks.csv");checks<<"check,passed\n";
  rejections.open(out+"/loader_rejections.csv");rejections<<"case,rejected,message\n";
  try {
    loader_controls(out);retention_controls(out,variant=="positive_curvature");trace_controls(out);
    rejections.close();check("rejection_records_written",bool(rejections));
    std::cout<<check_count<<" invented checks passed; no native data or production changes\n";
    return 0;
  }catch(const std::exception &e) {
    audit_history=nullptr;write(out+"/failure.txt",std::string(e.what())+"\n");
    std::cerr<<e.what()<<'\n';return 1;
  }
}
