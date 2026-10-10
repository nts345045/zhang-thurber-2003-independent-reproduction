// Invented serialization/control records only; never calls trace().
#include "../src/core.hpp"
#include "../src/csv.hpp"
#include <cstdint>
#include <cstring>
#include <experimental/filesystem>
#include <functional>
#include <iomanip>
std::string audit_run, audit_observation;
#include "failed_search_capture.hpp"
namespace fs = std::experimental::filesystem;

std::vector<std::pair<std::string,bool>> checks;
void check(const std::string &name, bool value) {
  checks.emplace_back(name,value);
  if (!value) throw std::runtime_error("Failed capture control: "+name);
}
bool same(double a,double b) {
  std::uint64_t x,y;
  std::memcpy(&x,&a,sizeof(x));std::memcpy(&y,&b,sizeof(y));
  return x==y;
}
const std::string &field(const CsvTable &t,size_t row,const std::string &name) {
  auto found=std::find(t.header.begin(),t.header.end(),name);
  if(found==t.header.end())throw std::runtime_error("Missing column "+name);
  return t.rows.at(row).at(size_t(found-t.header.begin()));
}
double number(const CsvTable &t,size_t row,const std::string &name) {
  return std::stod(field(t,row,name));
}
std::string bytes(const std::string &name) {
  std::ifstream f(name,std::ios::binary);
  return std::string(std::istreambuf_iterator<char>(f),{});
}
bool throws(const std::function<void()> &f) {
  try {f();} catch(const std::runtime_error &) {return true;}
  return false;
}
const std::vector<std::string> filenames={"failed_search_directions.csv",
  "failed_search_trials.csv","failed_search_decisions.csv"};

int main(int argc,char **argv) {
  if(argc!=2)throw std::runtime_error("Expected fresh invented output directory");
  const std::string out=argv[1];
  if(fs::exists(out))throw std::runtime_error("Control output already exists");
  fs::create_directories(out+"/failed");fs::create_directories(out+"/reset");
  fs::create_directories(out+"/guards");
  Grid g;g.x={-2,2};g.y={-2,2};g.z={-2,2};g.v.assign(8,5);
  std::vector<P> base={{-1,-.5,-.25},{std::nextafter(.125,1.),-0.,.375},
                       {.5,std::nextafter(1./3.,1.),-.125},{1,.75,.5}};
  Vec q={4,-.125,-0.,-2.5,.0625,std::ldexp(1.,-900)};
  Vec gradient=q;for(auto &v:gradient)v=-v;
  const double reevaluated=path_eval(g,base);
  const double cached=std::nextafter(reevaluated,INFINITY),slope=dot(gradient,q);
  capture_output=out+"/failed";
  audit_run="invented_failed_capture";audit_observation="invented_17";
  capture_begin();capture_trial(99,16,base,true,0,-123,-124,true);
  capture_begin(); // The prior accepted iteration must leave no failed record.
  std::vector<std::vector<P>> expected_paths;
  std::vector<bool> expected_valid;
  std::vector<double> expected_action,expected_rhs;
  for(int n=0;n<24;++n) {
    double step=std::ldexp(1.,-n);auto path=base;
    for(size_t i=1;i+1<path.size();++i)
      for(int axis=0;axis<3;++axis)path[i][axis]+=step*q[3*(i-1)+axis];
    bool valid=std::all_of(path.begin(),path.end(),[&](P p){return g.contains(p);});
    const double rhs=cached+1e-4*step*slope;
    // Controlled scalars exercise logging, not a claimed Fermat evaluation.
    const double action=valid?std::nextafter(rhs,INFINITY):NAN;
    expected_paths.push_back(path);expected_valid.push_back(valid);
    expected_action.push_back(action);expected_rhs.push_back(rhs);
    capture_trial(n,step,path,valid,0,action,rhs,false);
    path[1][0]=12345; // Verify capture owns its copy after caller mutation.
  }
  check("records_are_buffered_until_failure",std::all_of(filenames.begin(),filenames.end(),[&](const std::string &n){return !fs::exists(capture_output+"/"+n);}));
  capture_failed(7,g,base,gradient,q,cached,slope,std::ldexp(1.,-24));
  auto directions=csv_table(capture_output+"/"+filenames[0]);
  auto trials=csv_table(capture_output+"/"+filenames[1]);
  auto decisions=csv_table(capture_output+"/"+filenames[2]);
  check("complete_four_node_direction_table",directions.rows.size()==base.size());
  check("exact_twenty_four_trial_inventory",decisions.rows.size()==24&&trials.rows.size()==24*base.size());
  bool ids=true,geometry=true,derivatives=true,endpoints=true;
  for(size_t i=0;i<base.size();++i) {
    const bool endpoint=i==0||i+1==base.size();
    ids&=field(directions,i,"run_id")==audit_run&&field(directions,i,"observation_index")==audit_observation&&
         field(directions,i,"iteration")=="7"&&std::stoul(field(directions,i,"node"))==i;
    endpoints&=(field(directions,i,"is_endpoint")== (endpoint?"1":"0"));
    for(int axis=0;axis<3;++axis) {
      const std::string a(1,"xyz"[axis]);
      geometry&=same(number(directions,i,a),base[i][axis]);
      if(endpoint)endpoints&=number(directions,i,"q"+a)==0&&field(directions,i,"gradient_"+a).empty();
      else derivatives&=same(number(directions,i,"q"+a),q[3*(i-1)+axis])&&same(number(directions,i,"gradient_"+a),gradient[3*(i-1)+axis]);
    }
  }
  check("direction_native_join_keys_and_indices",ids);
  check("binary64_frame_and_signed_zero_round_trip",geometry);
  check("binary64_direction_gradient_and_tiny_value_round_trip",derivatives);
  check("fixed_endpoint_direction_and_blank_gradient",endpoints);
  bool trial_geometry=true,trial_keys=true,decision_fields=true,invalid_nan=true,trial_endpoints=true;
  for(size_t n=0;n<24;++n) {
    const double step=std::ldexp(1.,-int(n));
    decision_fields&=field(decisions,n,"run_id")==audit_run&&field(decisions,n,"observation_index")==audit_observation&&
      field(decisions,n,"iteration")=="7"&&std::stoul(field(decisions,n,"trial_index"))==n&&
      same(number(decisions,n,"step"),step)&&field(decisions,n,"valid")== (expected_valid[n]?"1":"0")&&
      field(decisions,n,"merged_nodes")=="0"&&field(decisions,n,"path_nodes")=="4"&&
      same(number(decisions,n,"cached_base_action_s"),cached)&&same(number(decisions,n,"reevaluated_base_action_s"),reevaluated)&&
      same(number(decisions,n,"directional_slope"),slope)&&same(number(decisions,n,"armijo_rhs_s"),expected_rhs[n])&&
      field(decisions,n,"binary64_accepted")=="0"&&field(decisions,n,"path_identical_to_base")=="0"&&
      same(number(decisions,n,"post_loop_halved_step"),std::ldexp(1.,-24));
    if(expected_valid[n])decision_fields&=same(number(decisions,n,"trial_action_s"),expected_action[n]);
    else invalid_nan&=std::isnan(number(decisions,n,"trial_action_s"));
    for(size_t i=0;i<base.size();++i) {
      size_t row=n*base.size()+i;
      trial_keys&=field(trials,row,"run_id")==audit_run&&field(trials,row,"observation_index")==audit_observation&&
        field(trials,row,"iteration")=="7"&&std::stoul(field(trials,row,"trial_index"))==n&&
        std::stoul(field(trials,row,"node"))==i&&same(number(trials,row,"step"),step);
      for(int axis=0;axis<3;++axis) {
        const double value=number(trials,row,std::string(1,"xyz"[axis]));
        trial_geometry&=same(value,expected_paths[n][i][axis]);
        if(i==0||i+1==base.size())trial_endpoints&=same(value,base[i][axis]);
      }
    }
  }
  check("all_trial_rows_have_complete_join_keys",trial_keys);
  check("caller_mutation_does_not_change_captured_paths",trial_geometry);
  check("every_trial_keeps_exact_endpoints",trial_endpoints);
  check("all_decision_scalars_flags_and_cached_action_preserved",decision_fields);
  check("invalid_trials_preserve_nan_action_without_reevaluation",invalid_nan&&std::count(expected_valid.begin(),expected_valid.end(),false)==2);
  check("last_attempt_step_is_not_post_loop_step",same(number(decisions,23,"step"),std::ldexp(1.,-23))&&same(number(decisions,23,"post_loop_halved_step"),std::ldexp(1.,-24)));
  std::vector<std::string> original_bytes;for(const auto &name:filenames)original_bytes.push_back(bytes(capture_output+"/"+name));
  check("existing_failure_is_not_overwritten",throws([&]{capture_failed(7,g,base,gradient,q,cached,slope,std::ldexp(1.,-24));}));
  bool unchanged=true;for(size_t n=0;n<filenames.size();++n)unchanged&=bytes(capture_output+"/"+filenames[n])==original_bytes[n];
  check("overwrite_rejection_preserves_all_three_files",unchanged);
  capture_output=out+"/reset";capture_begin();audit_run="invented_reset";audit_observation="invented_18";
  auto merged=base;merged.erase(merged.begin()+1);
  capture_trial(0,1,merged,true,1,cached,cached-1,false);
  capture_trial(1,.5,base,true,0,cached,cached-1,false);
  capture_failed(11,g,base,gradient,q,cached,slope,.25);
  auto reset=csv_table(capture_output+"/"+filenames[2]);
  auto reset_paths=csv_table(capture_output+"/"+filenames[1]);
  check("begin_resets_previous_failed_iteration",reset.rows.size()==2&&field(reset,0,"run_id")==audit_run&&field(reset,0,"iteration")=="11");
  check("merged_trial_keeps_its_own_vertex_count",field(reset,0,"merged_nodes")=="1"&&field(reset,0,"path_nodes")=="3"&&reset_paths.rows.size()==7);
  check("unchanged_trial_is_explicitly_identified",field(reset,1,"path_identical_to_base")=="1");
  capture_output=out+"/guards";capture_begin();
  check("empty_failure_buffer_rejected",throws([&]{capture_failed(1,g,base,gradient,q,cached,slope,.5);}));
  capture_trial(0,1,base,true,0,cached,cached,false);
  Vec wrong=q;wrong.pop_back();
  check("wrong_direction_dimension_rejected",throws([&]{capture_failed(1,g,base,gradient,wrong,cached,slope,.5);}));
  check("wrong_gradient_dimension_rejected",throws([&]{capture_failed(1,g,base,wrong,q,cached,slope,.5);}));
  check("rejected_dimensions_write_no_capture_files",std::all_of(filenames.begin(),filenames.end(),[&](const std::string &n){return !fs::exists(capture_output+"/"+n);}));
  std::ofstream report(out+"/checks.csv");report<<"check,passed\n";
  for(const auto &entry:checks)report<<entry.first<<','<<entry.second<<'\n';
  report.flush();if(!report)throw std::runtime_error("Cannot save capture checks");
  std::cout<<checks.size()<<" invented capture checks passed\n";
}
