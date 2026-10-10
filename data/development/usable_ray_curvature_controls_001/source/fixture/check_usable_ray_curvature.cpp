// Invented arithmetic and seeded-ray controls. The included native main is
// renamed, never called; no receiver field or authoritative ray is constructed.
#include "fixture_driver.hpp"
#ifndef USABLE_VARIANT_D
#include "usable_ray_curvature.hpp"
#endif
#include "extracted_usable_caller.hpp"
#include <cstdint>
#include <cstring>

namespace fixture {
std::ofstream checks, cases;
std::size_t count=0;
void check(const std::string &name,bool passed) {
  checks<<csv_quote(name)<<','<<passed<<std::endl; ++count;
  if(!checks||!passed) throw std::runtime_error("Invented control failed: "+name);
}
std::string bits(double value) {
  std::uint64_t word; std::memcpy(&word,&value,sizeof word);
  std::ostringstream out; out<<std::hex<<std::setfill('0')<<std::setw(16)<<word;
  return out.str();
}
std::string vector_bits(const Vec &values) {
  std::ostringstream out; for(double value:values) out<<bits(value)<<' '; return out.str();
}
void point(std::ostream &out,P p) { for(double value:p) out<<bits(value)<<' '; out<<'\n'; }
std::string ray_bits(const Ray &ray) {
  std::ostringstream out;
  out<<bits(ray.time)<<' '<<ray.iterations<<' '<<ray.merged_nodes<<' '
     <<bits(ray.gradient)<<' '<<bits(ray.raw_gradient)<<' '<<ray.converged<<' '
     <<ray.initialization_attempted<<' '<<ray.initialization_succeeded<<' '<<ray.selected_fmm_seed<<' '
     <<bits(ray.direct_seed_time)<<' '<<bits(ray.fmm_seed_time)<<' '<<bits(ray.initializer_field_time)<<' '
     <<ray.initializer_fallback_steps<<' '<<csv_quote(ray.initializer_message)<<'\n';
  point(out,ray.source); out<<ray.path.size()<<'\n'; for(P p:ray.path) point(out,p);
  for(const Vec *v:{&ray.dv,&ray.length}) out<<v->size()<<'\n'<<vector_bits(*v)<<'\n';
  return out.str();
}
void write(const std::string &path,const std::string &text) {
  std::ofstream out(path,std::ios::binary); out<<text; out.close();
  if(!out) throw std::runtime_error("Cannot write fixture: "+path);
}
bool same(const Vec &a,const Vec &b) { return a==b; }

void pair_controls() {
  auto pair=[&](const std::string &name,const Vec &s,const Vec &y,double sy,bool expected,
                const std::string &meaning) {
    double reciprocal=0; const bool result=usable_ray_curvature(s,y,sy,reciprocal);
    cases<<csv_quote(name)<<','<<std::setprecision(17)<<sy<<','<<bits(sy)<<','<<result<<','
         <<reciprocal<<','<<bits(reciprocal)<<','<<csv_quote(meaning)<<std::endl;
    check("pair_"+name,result==expected);
    if(result) check("pair_reciprocal_"+name,std::isfinite(reciprocal)&&reciprocal>0&&
                       bits(reciprocal)==bits(1/sy));
  };
  for(const auto &item:std::vector<std::pair<std::string,double>>{
      {"below_old_cutoff",std::nextafter(1e-14,0.)},{"old_cutoff",1e-14},
      {"above_old_cutoff",std::nextafter(1e-14,INFINITY)},{"unit",1.},
      {"minimum_normal",std::numeric_limits<double>::min()},
      {"representable_subnormal",std::ldexp(1.,-1023)}})
    pair(item.first,{item.second,-0.,0},{1,0,0},item.second,true,"positive finite computed dot and reciprocal");
  for(const auto &item:std::vector<std::pair<std::string,double>>{
      {"negative",-1},{"negative_zero",-0.},{"zero",0},
      {"minimum_subnormal",std::numeric_limits<double>::denorm_min()},
      {"positive_infinity",INFINITY},{"negative_infinity",-INFINITY},{"nan",NAN}})
    pair(item.first,{1,0,0},{1,0,0},item.second,false,"supplied computed value is unusable");
  pair("empty",{},{},1,false,"dimension rejection");
  pair("dimension",{1},{1,0},1,false,"dimension rejection");
  pair("nonfinite_s",{INFINITY,0,0},{1,0,0},1,false,"finite supplied dot cannot conceal nonfinite vector");
  pair("nonfinite_y",{1,0,0},{NAN,0,0},1,false,"finite supplied dot cannot conceal nonfinite vector");
  for(int exponent:{-30,0,30}) {
    const double scale=std::ldexp(1.,exponent); Vec s{scale,0,0},y=s;
    check("dyadic_dot_"+std::to_string(exponent),dot(s,y)==std::ldexp(1.,2*exponent));
    pair("dyadic_"+std::to_string(exponent),s,y,dot(s,y),true,"no fixed absolute cutoff");
  }
  Vec s{1e16,1,-1e16},y{1,1,1};
  check("ordered_dot_loses_exact_positive_one",dot(s,y)==0);
  pair("cancelled_positive",s,y,dot(s,y),false,"exact real dot is 1; no cancellation repair claimed");
  s={std::ldexp(1.,-600),0,0}; y=s;
  check("positive_product_underflows",dot(s,y)==0);
  pair("underflowed_positive",s,y,dot(s,y),false,"exact real dot is 2^-1200");
  s={1e308,0,0}; y={2,0,0};
  check("finite_product_overflows",std::isinf(dot(s,y))&&dot(s,y)>0);
  pair("overflowed_dot",s,y,dot(s,y),false,"finite operands do not imply representable dot");
  s={1e16,-1,-1e16,.5}; y={1,1,1,1};
  check("ordered_dot_has_wrong_positive_sign",dot(s,y)==.5);
  pair("exact_negative_computed_positive",s,y,dot(s,y),true,
       "limitation: exact real dot is -1/2; usable arithmetic is not an exact-sign certificate");
}

void direction_controls() {
  auto direction=[&](const std::string &name,const Vec &weights,const Vec &gradient,
                     const std::vector<Vec> &S,const std::vector<Vec> &Y,const Vec &rho,
                     bool expected,const Vec *answer=nullptr,int callback_count=-1) {
    Vec q; int calls=0;
    const bool usable=usable_lbfgs_ray_direction([&]{++calls;return weights;},gradient,S,Y,rho,q);
    check("direction_"+name,usable==expected);
    check("direction_size_"+name,q.size()==gradient.size());
    if(answer) check("closed_form_"+name,same(q,*answer));
    if(callback_count>=0) check("metric_callback_"+name,calls==callback_count);
    return q;
  };
  const Vec answer{-1,2,-4};
  direction("no_memory_one_node",{1,1},{2,-4,8},{},{},{},true,&answer,1);
  const Vec coupled{-2,-1,-3,-1,-2,-3};
  direction("two_node_principal_inverse",{1,1,1},{3,0,3,0,3,3},{},{},{},true,&coupled,1);
  const Vec secant{-2,-4,6};
  direction("one_pair_scaled_identity",{1,1},{1,2,-3},{{2,0,0}},{{1,0,0}},{.5},true,&secant,1);
  // Independent dense BFGS algebra gives H=[[.5,.5,0],[.5,1.5,0],[0,0,.5]].
  const Vec oblique{0,2,-2};
  direction("one_pair_oblique",{1,1},{2,-2,4},{{1,1,0}},{{2,0,0}},{.5},true,&oblique,1);
  const Vec zero{0,0,0};
  direction("zero_slope_is_arithmetic_only",{1,1},zero,{},{},{},true,&zero,1);
  direction("nonfinite_gradient",{1,1},{NAN,0,0},{},{},{},false,nullptr,0);
  direction("memory_count",{1,1},{1,0,0},{{1,0,0}},{},{},false,nullptr,0);
  direction("reciprocal_count",{1,1},{1,0,0},{{1,0,0}},{{1,0,0}},{},false,nullptr,0);
  direction("memory_dimension",{1,1},{1,0,0},{{1}},{{1,0,0}},{1},false,nullptr,0);
  direction("memory_nonfinite",{1,1},{1,0,0},{{INFINITY,0,0}},{{1,0,0}},{1},false,nullptr,0);
  for(const auto &item:std::vector<std::pair<std::string,double>>{
      {"zero",0},{"negative",-1},{"infinite",INFINITY},{"nan",NAN}})
    direction("bad_reciprocal_"+item.first,{1,1},{1,0,0},{{1,0,0}},{{1,0,0}},{item.second},false,nullptr,0);
  direction("metric_dimension",{1,1},{1,0,0,0,0,0},{},{},{},false,nullptr,1);
  for(const auto &item:std::vector<std::pair<std::string,Vec>>{
      {"too_short",{1}},{"zero",{0,1}},{"negative",{-1,1}},
      {"nan",{NAN,1}},{"infinite",{INFINITY,1}},{"overflow_sum",{1e308,1e308}}})
    direction("metric_"+item.first,item.second,{1,0,0},{},{},{},false,nullptr,1);
  direction("rounded_zero_pivot",{std::ldexp(1.,-100),1,std::ldexp(1.,-100)},
            {1,0,0,1,0,0},{},{},{},false,nullptr,1);
  direction("inverse_rhs_overflow",{std::numeric_limits<double>::min(),std::numeric_limits<double>::min()},
            {1e308,0,0},{},{},{},false,nullptr,1);
  direction("finite_direction_nonfinite_slope",{.5,.5},{1e308,0,0},{},{},{},false,nullptr,1);
  direction("alpha_overflow_before_metric",{1,1},{std::ldexp(1.,600),0,0},
            {{std::ldexp(1.,-500),0,0}},{{std::ldexp(1.,-500),1,0}},
            {std::ldexp(1.,1000)},false,nullptr,0);
  direction("first_update_overflow_before_metric",{1,1},{2,0,0},
            {{1,0,0}},{{1,1e308,0}},{1},false,nullptr,0);
  direction("last_pair_zero_computed_numerator",{1,1},{1,0,0},
            {{1e16,1,-1e16}},{{1,1,1}},{1},false,nullptr,1);
  direction("scale_denominator_underflow",{std::ldexp(1.,99),std::ldexp(1.,99)},{1,0,0},
            {{1,0,0}},{{std::ldexp(1.,-500),0,0}},{std::ldexp(1.,500)},false,nullptr,1);
  direction("scale_denominator_overflow",{std::ldexp(1.,-501),std::ldexp(1.,-501)},{1,0,0},
            {{std::ldexp(1.,-300),0,0}},{{std::ldexp(1.,300),0,0}},{1},false,nullptr,1);
  direction("gamma_underflow",{std::ldexp(1.,-601),std::ldexp(1.,-601)},{1,0,0},
            {{std::ldexp(1.,-500),0,0}},{{1,0,0}},{std::ldexp(1.,500)},false,nullptr,1);
  direction("gamma_overflow",{std::ldexp(1.,499),std::ldexp(1.,499)},{1,0,0},
            {{std::ldexp(1.,600),0,0}},{{1,0,0}},{std::ldexp(1.,-600)},false,nullptr,1);
  direction("scaled_q_overflow",{.5,.5},{0,std::ldexp(1.,600),0},
            {{std::ldexp(1.,600),0,0}},{{1,0,0}},{std::ldexp(1.,-600)},false,nullptr,1);
  // A deliberately inconsistent but finite memory reciprocal exercises the
  // use-time guard. This is not claimed reachable through normal admission.
  direction("corrupt_finite_memory_beta_overflow",{1,1},{0,8,0},
            {{1,0,0}},{{1,2,0}},{1e308},false,nullptr,1);
  direction("alpha_minus_beta_overflow",{1,1},{1,0,0},
            {{1,0,0}},{{1e-308,1,0}},{1/1e-308},false,nullptr,1);
  direction("second_update_overflow",{1,1},{1,0,0},
            {{1.7e308,0,0}},{{1,1,0}},{1/1.7e308},false,nullptr,1);
}

Grid model(bool affine=false) {
  Grid g; g.x=g.y=g.z={-2,0,2};
  for(double z:g.z) for(double y:g.y) for(double x:g.x)
    g.v.push_back(affine?5+.1*x+.05*y+.08*z:5);
  return g;
}
void caller_controls() {
  Grid g=model(); const std::vector<P> p{{-1,0,0},{0,0,0},{1,0,0}};
  std::vector<Vec> S{{1,0,0}},Y{{1,0,0}}; Vec rho{INFINITY};
  const Vec q=fixture_actual_direction(g,p,{1,2,0},S,Y,rho);
  check("actual_caller_unusable_memory_uses_cone",q==Vec({-2.5,-5,0}));
  check("actual_caller_fallback_clears_memory",S.empty()&&Y.empty()&&rho.empty());
  auto reject=[&](const std::string &name,const Grid &grid,const std::vector<P> &path,const Vec &grad) {
    std::vector<Vec> a{{1,0,0}},b{{1,0,0}}; Vec r{INFINITY};
    bool threw=false; try {fixture_actual_direction(grid,path,grad,a,b,r);} catch(const std::exception &) {threw=true;}
    check("actual_caller_reject_"+name,threw);
  };
  reject("nonfinite_fallback_gradient",g,p,{NAN,0,0});
  auto degenerate=p; degenerate[1]=degenerate[0];
  reject("zero_edge_metric",g,degenerate,{1,0,0});
  reject("zero_direction_not_success",g,p,{0,0,0});
  S={{1,0,0}};Y=S;rho={1};
  fixture_actual_admission({std::numeric_limits<double>::denorm_min(),0,0},{1,0,0},S,Y,rho);
  check("actual_rejected_new_pair_preserves_old_memory",S==std::vector<Vec>({{1,0,0}})&&S==Y&&rho==Vec({1}));
  const double tiny=std::nextafter(1e-14,0.);
  fixture_actual_admission({tiny,0,0},{1,0,0},S,Y,rho);
  check("actual_subcutoff_pair_retained",S.size()==2&&S.back()==Vec({tiny,0,0})&&rho.back()==1/tiny);
  S.clear();Y.clear();rho.clear();
  for(int i=1;i<=9;++i) fixture_actual_admission({double(i),0,0},{1,0,0},S,Y,rho);
  check("actual_capacity_eight_evicts_oldest",S.size()==8&&S.front()[0]==2&&S.back()[0]==9&&Y.size()==8&&rho.size()==8);
}

const std::string history_header="run_id,observation_index,phase,iteration,updates,time_s,projected_gradient,raw_gradient,action_change_s,accepted_step,feasible_initial_step,directional_slope,line_search_evaluations,memory_pairs,gradient_fallback,merged_nodes,curvature_pair_accepted,max_node_step_km,path_nodes,min_segment_km,max_segment_km,tangential_gradient_norm,normal_gradient_norm,min_internal_grid_plane_distance_km,x_min_active,x_max_active,y_min_active,y_max_active,z_min_active,z_max_active\n";
void ray_controls(const std::string &out) {
  const P a={-1.5,-.7,-.8},b={1.4,.8,.9};
  const std::vector<P> seed{a,{-.1,.7,-.3},b};
  std::ofstream results(out+"/rays.csv");
  results<<std::setprecision(17)<<"case,updates,converged,time_s,gradient,time_error_s,path_nodes\n";
  for(bool affine:{false,true}) for(bool seeded:{false,true}) {
    const std::string name=std::string(affine?"affine":"homogeneous")+(seeded?"_seeded":"_direct");
    Grid g=model(affine); const auto *initial=seeded?&seed:nullptr;
    const Ray original=trace(g,a,b,.25,180,true,initial);
    std::ofstream history(out+"/"+name+"_history.csv"); history<<std::setprecision(17)<<history_header;
    audit_run=name;audit_observation="invented_only";audit_history=&history;audit_metric_file=nullptr;
    const Ray observed=observed_trace(g,a,b,.25,180,true,initial);
    audit_history=nullptr;history.close();
    check(name+"_history_written",bool(history));
    check(name+"_observer_full_ray_bits",ray_bits(observed)==ray_bits(original));
    check(name+"_exact_endpoints_and_domain",original.path.front()==a&&original.path.back()==b&&
      std::all_of(original.path.begin(),original.path.end(),[&](P p){return g.contains(p);}));
    check(name+"_finite_action_and_derivatives",std::isfinite(original.time)&&finite_curvature_vector(original.dv)&&
      finite_curvature_vector(original.length)&&std::all_of(original.source.begin(),original.source.end(),[](double v){return std::isfinite(v);}));
    const double G=norm(P{.1,.05,.08}),distance=norm(b-a);
    const double exact=affine?2/G*std::asinh(G*distance/(2*std::sqrt(g.sample(a).v*g.sample(b).v))):distance/5;
    // The mild affine minimizer is well inside this box. The numerical flag
    // is recorded, not forced; this bound is an independent action control.
    check(name+"_analytic_action",std::abs(original.time-exact)<=2.5e-5);
    if(!affine) check(name+"_homogeneous_converged",original.converged);
    write(out+"/"+name+"_ray_bits.txt",ray_bits(original));
    results<<name<<','<<original.iterations<<','<<original.converged<<','<<original.time<<','
      <<original.gradient<<','<<original.time-exact<<','<<original.path.size()<<'\n';
  }
  results.close();check("ray_results_written",bool(results));
}
}

int main(int argc,char **argv) {
  using namespace fixture;
  if(argc!=2) throw std::runtime_error("Usage: check_usable_ray_curvature FRESH_OUTPUT");
  const std::string out=argv[1];
  if(std::filesystem::exists(out)) throw std::runtime_error("Fresh output required");
  std::filesystem::create_directories(out);
  checks.open(out+"/checks.csv");checks<<"check,passed\n";
  cases.open(out+"/pair_cases.csv");cases<<"case,computed_sy,sy_bits,usable,reciprocal,reciprocal_bits,interpretation\n";
  try {
    pair_controls(); direction_controls(); caller_controls(); ray_controls(out);
    cases.close();check("pair_cases_written",bool(cases));
    std::cout<<count<<" invented controls passed; no native ray or field construction\n";
    return 0;
  } catch(const std::exception &error) {
    audit_history=nullptr;write(out+"/failure.txt",std::string(error.what())+"\n");
    std::cerr<<error.what()<<'\n';return 1;
  }
}
