#include "reference_selected_curve.hpp"
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <sys/stat.h>

namespace sc=selected_curve;
using lcr::Real;
using lcr::require;

void quoted(std::ostream &out,const std::string &value) {
  const char *digits="0123456789abcdef";
  out << '"';
  for (unsigned char c:value) {
    if (c=='"' || c=='\\') out << '\\' << char(c);
    else if (c<32) out << "\\u00" << digits[c>>4] << digits[c&15];
    else out << char(c);
  }
  out << '"';
}
void hex(std::ostream &out,Real value) {
  require(lcr::finite(value),"Nonfinite saved scalar");
  std::ostringstream text;text << std::hexfloat << value;quoted(out,text.str());
}
template<class Values> void vector(std::ostream &out,const Values &values) {
  out << '[';bool first=true;
  for (auto v:values) {if (!first) out << ',';first=false;hex(out,v);}
  out << ']';
}
void absent(const std::string &path) {
  struct stat info;
  require(lstat(path.c_str(),&info)!=0 && errno==ENOENT,"Output path is not absent");
}
void sidecar(const std::string &path) {
  std::ifstream input(path+".identifiers.json");
  require(bool(input),"Missing required identity sidecar");
}
double binary64(std::istream &in) {
  std::string token;require(bool(in>>token),"Missing binary64 token");
  char *end=nullptr;errno=0;
  const double value=std::strtod(token.c_str(),&end);
  require(end==token.c_str()+token.size() && end!=token.c_str() &&
          std::isfinite(value) && (errno!=ERANGE || value!=0),"Invalid binary64 token");
  return value;
}
struct Input {lcr::Grid grid;lcr::Point source{},receiver{};std::size_t nodes=0;};
Input read_original(std::istream &in) {
  Input input;std::size_t nx=0,ny=0,nz=0;
  require(bool(in>>nx>>ny>>nz) && nx>=2 && ny>=2 && nz>=2 &&
          nx<=1000 && ny<=1000 && nz<=1000,"Invalid original grid dimensions");
  input.grid.x.resize(nx);input.grid.y.resize(ny);input.grid.z.resize(nz);
  for (auto *axis:{&input.grid.x,&input.grid.y,&input.grid.z})
    for (auto &v:*axis) v=binary64(in);
  require(nx<=1000000/ny && nx*ny<=1000000/nz,"Original grid exceeds diagnostic inventory");
  input.grid.v.resize(nx*ny*nz);
  for (auto &v:input.grid.v) v=binary64(in);
  require(bool(in>>input.nodes) && input.nodes>=2 && input.nodes<=10000,
          "Invalid original path count");
  lcr::Point previous{};
  for (std::size_t j=0;j<input.nodes;++j) {
    lcr::Point point;for (auto &v:point) v=binary64(in);
    if (j==0) input.source=point;
    else require(point!=previous,"Zero original edge");
    previous=point;
  }
  input.receiver=previous;std::string extra;
  require(!(in>>extra),"Unexpected original input tokens");
  return input;
}
void join(std::ostream &out,const sc::Join &j,bool completed=true) {
  out << "{\"kind\":";quoted(out,j.kind);out << ",\"layer\":" << j.layer;
  const std::pair<const char *,Real> fields[]={
    {"nominal_begin_depth",j.nominal_begin},{"nominal_end_depth",j.nominal_end},
    {"velocity_begin",j.velocity_begin},{"velocity_end",j.velocity_end},
    {"slope",j.slope},{"theta",j.theta},{"sweep",j.sweep}};
  for (const auto &field:fields) {out << ',';quoted(out,field.first);out << ':';hex(out,field.second);}
  out << ",\"completed\":" << (completed?"true":"false") << ",\"actual_begin\":";
  if(completed)vector(out,std::array<Real,2>{j.actual_begin.r,j.actual_begin.z});else out << "null";
  out << ",\"actual_end\":";
  if(completed)vector(out,std::array<Real,2>{j.actual_end.r,j.actual_end.z});else out << "null";
  out << ",\"tangent_begin\":";if(completed)vector(out,j.tangent_begin);else out << "null";
  out << ",\"tangent_end\":";if(completed)vector(out,j.tangent_end);else out << "null";out << '}';
}
void curve(std::ostream &out,const sc::Build &b) {
  out << "{\"origin\":";vector(out,b.curve.origin);
  out << ",\"azimuth\":";vector(out,b.curve.azimuth);
  out << ",\"branch\":";quoted(out,b.curve.status.branch);
  out << ",\"completeness\":";quoted(out,b.curve.status.completeness);
  out << ",\"derivatives\":";quoted(out,b.curve.status.derivatives);
  out << ",\"pieces\":[";
  for (std::size_t j=0;j<b.curve.pieces.size();++j) {
    if(j)out << ',';
    const auto &p=b.curve.pieces[j];
    out << "{\"kind\":" << int(p.kind) << ",\"parameters\":";
    vector(out,std::array<Real,8>{p.r0,p.z0,p.r1,p.z1,p.theta0,p.theta1,p.sweep,p.kappa});
    out << '}';
  }
  out << "],\"joins\":[";
  for (std::size_t j=0;j<b.joins.size();++j) {if(j)out << ',';join(out,b.joins[j]);}
  out << "],\"pending_join\":";
  if(b.has_pending_join)join(out,b.pending_join,false);else out << "null";
  out << '}';
}
void result(std::ostream &out,const lcr::Result &r,const lcr::Grid &g) {
  out << "{\"action_s\":";hex(out,r.action);
  out << ",\"arclength_km\":";hex(out,r.arclength);
  out << ",\"dv\":";vector(out,r.dv);
  out << ",\"length\":";vector(out,r.length);
  out << ",\"action_8_16_difference_s\":";hex(out,r.action_difference);
  out << ",\"dv_8_16_max_difference\":";hex(out,r.dv_max_difference);
  out << ",\"length_8_16_max_difference_km\":";hex(out,r.length_max_difference);
  out << ",\"maximum_face_coordinate_residual_km\":";hex(out,r.maximum_face_coordinate_residual);
  out << ",\"maximum_anchor_roundtrip_displacement_km\":";hex(out,r.maximum_anchor_roundtrip_displacement);
  out << ",\"maximum_anchor_midpoint_discrepancy_km\":";hex(out,r.maximum_anchor_midpoint_discrepancy);
  Real sum_length=0,scaling=0;
  for(std::size_t j=0;j<r.dv.size();++j) {sum_length+=r.length[j];scaling-=Real(g.v[j])*r.dv[j];}
  out << ",\"basis_length_sum_residual_km\":";hex(out,sum_length-r.arclength);
  out << ",\"velocity_homogeneity_residual_s\":";hex(out,scaling-r.action);
  out << ",\"pieces\":" << r.pieces << ",\"subpieces\":" << r.subpieces
      << ",\"samples\":" << r.samples << ",\"face_crossings\":" << r.face_crossings
      << ",\"interval_certificate\":false}";
}

int main(int argc,char **argv) {
  try {
    require(argc==4,"Usage: observe_reference_curve ORIGINAL_INPUT CURVE_SPEC ABSENT_OUTPUT_JSON");
    const std::string numeric=argv[1],spec_path=argv[2],output=argv[3];
    absent(output);sidecar(numeric);sidecar(spec_path);sidecar(output);
    std::ifstream native(numeric),selection(spec_path);
    require(bool(native) && bool(selection),"Cannot open selected inputs");
    const Input input=read_original(native);
    const sc::Spec spec=sc::read_spec(selection);
    sc::Build build;lcr::Result value;std::vector<lcr::Point> display;
    bool constructed=false,integrated=false;unsigned attempted=0,display_calls=0;
    std::string failure,status="construction_failed";
    try {
      sc::construct(input.grid,input.source,input.receiver,spec,build);constructed=true;
      status="integration_failed";++attempted;
      value=lcr::integrate(input.grid,build.curve);integrated=true;
      status="display_failed";++display_calls;
      display=lcr::display_samples(build.curve,Real(1));
      status="completed_reference_selected_curve_diagnostic";
    } catch(const std::exception &error) {failure=error.what();}
    std::ofstream out(output);require(bool(out),"Cannot create diagnostic output");
    out << "{\"status\":";quoted(out,status);out << ",\"case_id\":";quoted(out,spec.case_id);
    out << ",\"supplied_exact\":{\"u\":";quoted(out,spec.u_exact);
    out << ",\"turn_depth\":";quoted(out,spec.turn_exact);
    out << ",\"guide_length\":";quoted(out,spec.guide_exact);out << '}';
    out << ",\"working_conversion\":\"strtold numerator and denominator, then division; not exact rounding\"";
    out << ",\"working_values\":";vector(out,std::array<Real,3>{spec.u,spec.turn,spec.guide});
    out << ",\"original_nodes\":" << input.nodes << ",\"source\":";vector(out,input.source);
    out << ",\"receiver\":";vector(out,input.receiver);
    out << ",\"grid\":{\"x\":";vector(out,input.grid.x);out << ",\"y\":";vector(out,input.grid.y);
    out << ",\"z\":";vector(out,input.grid.z);out << ",\"v\":";vector(out,input.grid.v);out << '}';
    out << ",\"construction_stage\":";quoted(out,build.stage);
    out << ",\"construction_complete\":" << (constructed?"true":"false");
    out << ",\"error\":";if(failure.empty())out << "null";else quoted(out,failure);
    out << ",\"curve\":";curve(out,build);
    out << ",\"maximum_depth_join_error_km\":";hex(out,build.maximum_depth_join_error);
    out << ",\"maximum_tangent_jump\":";hex(out,build.maximum_tangent_jump);
    out << ",\"turn_profile_velocity_minus_u\":";
    if(build.profile_evaluated)hex(out,build.turn_profile_velocity-spec.u);else out << "null";
    out << ",\"endpoint_closure_km\":";if(constructed)hex(out,build.endpoint_closure);else out << "null";
    out << ",\"integrate_attempts\":" << attempted << ",\"successful_integrations\":" << unsigned(integrated)
        << ",\"display_calls\":" << display_calls << ",\"optimizer_calls\":0,\"branch_enumerator_calls\":0";
    out << ",\"result\":";if(integrated)result(out,value,input.grid);else out << "null";
    out << ",\"display_spacing_km\":1,\"display_samples\":[";
    for(std::size_t j=0;j<display.size();++j) {if(j)out << ',';vector(out,display[j]);}
    out << "],\"first_arrival_certified_by_this_component\":false,\"optimized_source_derivative_certified\":false}\n";
    out.close();require(bool(out),"Diagnostic output close failed");
    std::cout << status << '\n';
    return failure.empty()?0:1;
  } catch(const std::exception &error) {std::cerr << error.what() << '\n';return 1;}
}
