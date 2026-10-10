// Component controls only: never calls trace(). Compile with each frozen core.
#define main frozen_solver_main
#include "../src/main.cpp"
#undef main
#include "original_path_eval.hpp"
#include <cstring>
#ifndef OUTER_EXTENDED
#define OUTER_EXTENDED 0
#endif

bool same_double(double a,double b) {return std::memcmp(&a,&b,sizeof(double))==0;}
std::size_t checks=0;
void check(bool ok,const std::string &name,std::ofstream &out) {
  out<<name<<','<<ok<<'\n';++checks;
  if(!ok)throw std::runtime_error("Outer accumulation control failed: "+name);
}
double outer_sum(const Grid &g,const std::vector<P> &p,bool extended) {
  double ordinary=0;long double wide=0;
  for(std::size_t n=1;n<p.size();++n) {
    const double value=segment(g,p[n-1],p[n]);ordinary+=value;wide+=value;
  }
  return extended?static_cast<double>(wide):ordinary;
}
bool same_vector(const Vec &a,const Vec &b) {
  if(a.size()!=b.size())return false;
  for(std::size_t n=0;n<a.size();++n)if(!same_double(a[n],b[n]))return false;
  return true;
}
std::size_t column(const CsvTable &t,const std::string &name) {
  auto at=std::find(t.header.begin(),t.header.end(),name);
  if(at==t.header.end())throw std::runtime_error("Missing column "+name);
  return std::size_t(at-t.header.begin());
}

int main(int argc,char **argv) {
  if(argc!=6)throw std::runtime_error("GRID BASE_PATH TRIAL_PATHS DECISIONS OUTPUT_DIR required");
  const std::string out=argv[5];
  if(std::ifstream(out+"/checks.csv").good())throw std::runtime_error("Fresh control outputs required");
  std::ofstream log(out+"/checks.csv"),native(out+"/native_actions.csv");
  if(!log||!native)throw std::runtime_error("Cannot open control outputs");
  log<<"check,passed\n";native<<std::setprecision(17)
    <<"run_id,observation_index,trial_index,original_action_s,variant_action_s,long_double_sum_cast_s,gradient_bitwise_equal,variant_extended\n";
  Grid uniform;uniform.x={-2,2};uniform.y={-2,2};uniform.z={-2,2};uniform.v.assign(8,3);
  std::vector<std::vector<P>> invented={{{-1,0,0},{1,0,0}},{{-1,0,0},{0,0,0},{1,0,0}},
    {{-1,-1,0},{0,0,0},{1,1,0}}};
  std::vector<P> many;for(int n=0;n<=2048;++n)many.push_back(P{double(n%2),0,0});invented.push_back(many);
  const long double exact[]={2.L/3,2.L/3,2*std::sqrt(2.L)/3,2048.L/3};
  for(std::size_t i=0;i<invented.size();++i) {
    Vec a,b;const double old=original_path_eval(uniform,invented[i],&a),now=path_eval(uniform,invented[i],&b);
    check(same_double(old,outer_sum(uniform,invented[i],false)),"invented_original_sum_"+std::to_string(i),log);
    check(same_double(now,outer_sum(uniform,invented[i],OUTER_EXTENDED)),"invented_variant_sum_"+std::to_string(i),log);
    check(same_vector(a,b),"invented_gradient_unchanged_"+std::to_string(i),log);
    // Forward-error allowance grows with additions; no ray accuracy gate is altered.
    const long double tolerance=16*std::numeric_limits<double>::epsilon()*invented[i].size()*exact[i];
    check(std::abs(static_cast<long double>(now)-exact[i])<=tolerance,"invented_closed_form_"+std::to_string(i),log);
  }
  Grid g=read_grid(argv[1]);auto bases=csv_table(argv[2]),trials=csv_table(argv[3]),decisions=csv_table(argv[4]);
  if(bases.rows.size()!=1134||trials.rows.size()!=24*1134||decisions.rows.size()!=24)
    throw std::runtime_error("Wrong native support");
  auto coordinates=[&](const CsvTable &t,std::size_t start) {
    std::vector<P> p;
    for(std::size_t n=0;n<1134;++n) {
      const auto &r=t.rows.at(start+n);
      if(r[column(t,"run_id")]!="fmm_0.031250_1000"||r[column(t,"observation_index")]!="3426"||
         std::stoul(r[column(t,"node")])!=n)throw std::runtime_error("Native path identity/order differs");
      p.push_back(P{std::stod(r[column(t,"x")]),std::stod(r[column(t,"y")]),std::stod(r[column(t,"z")])});
    }
    return p;
  };
  for(int trial=-1;trial<24;++trial) {
    auto p=coordinates(trial<0?bases:trials,trial<0?0:std::size_t(trial)*1134);
    Vec a,b;const double old=original_path_eval(g,p,&a),now=path_eval(g,p,&b),wide=outer_sum(g,p,true);
    const double saved=std::stod(decisions.rows[trial<0?0:trial][column(decisions,trial<0?"cached_base_action_s":"trial_action_s")]);
    check(same_double(old,saved),"native_original_archived_parity_"+std::to_string(trial),log);
    check(same_double(now,OUTER_EXTENDED?wide:old),"native_variant_outer_sum_"+std::to_string(trial),log);
    check(same_vector(a,b),"native_gradient_unchanged_"+std::to_string(trial),log);
    native<<"fmm_0.031250_1000,3426,"<<trial<<','<<old<<','<<now<<','<<wide<<','<<same_vector(a,b)<<','<<OUTER_EXTENDED<<'\n';
  }
  log.flush();native.flush();if(!log||!native)throw std::runtime_error("Incomplete control output");
  std::cout<<checks<<" outer accumulation controls passed; no ray tracing\n";
}
