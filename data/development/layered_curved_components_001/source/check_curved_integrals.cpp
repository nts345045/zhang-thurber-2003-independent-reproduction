#include "layered_curved_ray.hpp"
#include <cerrno>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <sys/stat.h>

// Six invented groups. No quadrature implementation, branch enumerator,
// optimizer, or real-data input. Independent polynomial/trigonometric endpoint
// antiderivatives supply every nodal reference. Allowances below are finite
// working-arithmetic regression tolerances, never interval certificates.
namespace {
using lcr::Real;
using lcr::Point;
using lcr::Grid;
using lcr::Curve;
using lcr::Piece;
using lcr::Result;
std::size_t checks=0,groups=0,attempts=0,completed=0,samples=0,subpieces=0,display_calls=0;

void quoted(std::ostream &out,const std::string &s) {
  out << '"';
  for(unsigned char c:s) {
    if(c=='"' || c=='\\')out << '\\' << char(c);
    else if(c=='\n')out << "\\n";
    else if(c<32)throw std::runtime_error("Unserializable control string");
    else out << char(c);
  }
  out << '"';
}
void real(std::ostream &out,Real q) {
  if(!std::isfinite(q))throw std::runtime_error("Nonfinite control output");
  std::ostringstream s;s << std::hexfloat << q;quoted(out,s.str());
}
template<class Values> void vector(std::ostream &out,const Values &a) {
  out << '[';bool first=true;
  for(auto q:a){if(!first)out << ',';first=false;real(out,Real(q));}out << ']';
}
void status(std::ostream &out,const lcr::BranchStatus &s) {
  out << "{\"branch\":";quoted(out,s.branch);
  out << ",\"completeness\":";quoted(out,s.completeness);
  out << ",\"derivatives\":";quoted(out,s.derivatives);out << '}';
}
void flush() {
  std::cout << '\n';std::cout.flush();
  if(!std::cout)throw std::runtime_error("Control stdout write failed");
}
void check(bool condition,const char *name) {
  ++checks;std::cout << "{\"type\":\"assertion\",\"check\":" << checks << ",\"group\":" << groups << ",\"name\":";quoted(std::cout,name);
  std::cout << ",\"passed\":" << (condition?"true":"false") << '}';flush();
  if(!condition)throw std::runtime_error(name);
}
void supplied(const char *name,const Grid &g,const Curve &c) {
  std::cout << "{\"type\":\"supplied\",\"name\":";quoted(std::cout,name);
  std::cout << ",\"x\":";vector(std::cout,g.x);std::cout << ",\"y\":";vector(std::cout,g.y);
  std::cout << ",\"z\":";vector(std::cout,g.z);std::cout << ",\"v\":";vector(std::cout,g.v);
  std::cout << ",\"origin\":";vector(std::cout,c.origin);
  std::cout << ",\"azimuth\":";vector(std::cout,c.azimuth);
  std::cout << ",\"status\":";status(std::cout,c.status);std::cout << ",\"pieces\":[";
  for(std::size_t j=0;j<c.pieces.size();++j) {
    if(j)std::cout << ',';
    const auto &p=c.pieces[j];
    std::cout << "{\"kind\":" << int(p.kind) << ",\"r0\":";real(std::cout,p.r0);
    std::cout << ",\"z0\":";real(std::cout,p.z0);std::cout << ",\"r1\":";real(std::cout,p.r1);
    std::cout << ",\"z1\":";real(std::cout,p.z1);std::cout << ",\"theta0\":";real(std::cout,p.theta0);
    std::cout << ",\"theta1\":";real(std::cout,p.theta1);std::cout << ",\"sweep\":";real(std::cout,p.sweep);
    std::cout << ",\"kappa\":";real(std::cout,p.kappa);std::cout << '}';
  }
  std::cout << "]}";flush();
}
Result evaluated(const char *name,const Grid &g,const Curve &c) {
  supplied(name,g,c);++attempts;Result r=lcr::integrate(g,c);
  ++completed;samples+=r.samples;subpieces+=r.subpieces;
  std::cout << "{\"type\":\"result\",\"name\":";quoted(std::cout,name);
  std::cout << ",\"action\":";real(std::cout,r.action);std::cout << ",\"arclength\":";real(std::cout,r.arclength);
  std::cout << ",\"dv\":";vector(std::cout,r.dv);std::cout << ",\"length\":";vector(std::cout,r.length);
  std::cout << ",\"action_8_16_difference\":";real(std::cout,r.action_difference);
  std::cout << ",\"dv_8_16_max_difference\":";real(std::cout,r.dv_max_difference);
  std::cout << ",\"length_8_16_max_difference\":";real(std::cout,r.length_max_difference);
  std::cout << ",\"maximum_face_coordinate_residual\":";real(std::cout,r.maximum_face_coordinate_residual);
  std::cout << ",\"pieces\":" << r.pieces << ",\"subpieces\":" << r.subpieces
            << ",\"samples\":" << r.samples << ",\"face_crossings\":" << r.face_crossings
            << ",\"supplied_status\":";status(std::cout,r.supplied_status);std::cout << '}';flush();
  return r;
}

struct Reference {
  Real action=0,arclength=0,absolute_accumulation=0,maximum_center_roundoff=0;
  std::vector<Real> dv,length;
  explicit Reference(std::size_t n):dv(n,0),length(n,0) {}
};
using Polynomial=std::array<Real,4>;
Polynomial times_linear(const Polynomial &a,Real b0,Real b1) {
  Polynomial c{};
  for(std::size_t j=0;j<4;++j){c[j]+=a[j]*b0;if(j+1<4)c[j+1]+=a[j]*b1;}
  return c;
}
Real polynomial_integral(const Polynomial &p,Real a,Real b,Real &absolute) {
  Real answer=0,ap=a,bp=b;
  for(std::size_t j=0;j<4;++j) {
    Real term=p[j]*(bp-ap)/Real(j+1);answer+=term;absolute+=std::abs(term);ap*=a;bp*=b;
  }
  return answer;
}
// Integrate cubics in the ORIGINAL line parameter, without kernel partition,
// cell-lookup, sample, or quadrature calls.
Reference polynomial_reference(const Grid &g,const Curve &c,Real speed) {
  const Point a=c.at(0,0),b=c.at(0,1);Point d{};
  for(int k=0;k<3;++k)d[k]=b[k]-a[k];
  const Real length=std::hypot(std::hypot(d[0],d[1]),d[2]);
  Reference r(g.v.size());r.arclength=length;r.action=length/speed;
  const std::vector<double> *axes[]{&g.x,&g.y,&g.z};std::vector<Real> cuts{0,1};
  for(int k=0;k<3;++k)if(d[k]!=0)for(double face:*axes[k]) {
    Real t=(Real(face)-a[k])/d[k];if(t>0 && t<1)cuts.push_back(t);
  }
  std::sort(cuts.begin(),cuts.end());cuts.erase(std::unique(cuts.begin(),cuts.end()),cuts.end());
  for(std::size_t q=1;q<cuts.size();++q) {
    Real lo=cuts[q-1],hi=cuts[q],mid=(lo+hi)/2;
    std::size_t cell[3]{};Real u0[3],u1[3];
    for(int k=0;k<3;++k) {
      const auto &axis=*axes[k];Real coordinate=a[k]+d[k]*mid;
      while(cell[k]+2<axis.size() && coordinate>=axis[cell[k]+1])++cell[k];
      Real width=Real(axis[cell[k]+1])-Real(axis[cell[k]]);
      u0[k]=(a[k]-Real(axis[cell[k]]))/width;u1[k]=d[k]/width;
    }
    for(std::size_t k=0;k<2;++k)for(std::size_t j=0;j<2;++j)for(std::size_t i=0;i<2;++i) {
      Polynomial p{1,0,0,0};const std::size_t corner[]{i,j,k};
      for(int axis=0;axis<3;++axis)
        p=times_linear(p,corner[axis]?u0[axis]:1-u0[axis],corner[axis]?u1[axis]:-u1[axis]);
      Real absolute=0,moment=length*polynomial_integral(p,lo,hi,absolute);
      std::size_t id=((cell[2]+k)*g.y.size()+cell[1]+j)*g.x.size()+cell[0]+i;
      r.length[id]+=moment;r.dv[id]-=moment/(speed*speed);
      r.absolute_accumulation+=length*absolute*(1+1/(speed*speed));
    }
  }
  return r;
}
// v(z)=z, R=2, y=0. An arc's x/z shapes are A+B*cos(theta),
// C+D*sin(theta); both y weights are 1/2. These are elementary
// endpoint antiderivatives, with no sampled-curve integral.
Reference affine_reference(const Grid &g,const Curve &c) {
  Reference r(g.v.size());const Real radius=2,dx=Real(g.x[1])-g.x[0],dz=Real(g.z[1])-g.z[0];
  for(const auto &p:c.pieces) {
    if(p.kind==lcr::PieceKind::affine_arc) {
      Real a=p.theta0,b=p.theta0+p.sweep;
      Real sa=std::sin(a),sb=std::sin(b),ca=std::cos(a),cb=std::cos(b);
      r.maximum_center_roundoff=std::max(r.maximum_center_roundoff,std::abs(p.z0-radius*sa));
      Real xc=c.origin[0]+p.r0+radius*ca;
      Real lm=std::log(std::tan(b/2))-std::log(std::tan(a/2));
      const std::array<Real,4> il{b-a,sb-sa,ca-cb,(sb*sb-sa*sa)/2};
      const std::array<Real,4> iv{ca/sa-cb/sb,1/sa-1/sb,lm,std::log(sb)-std::log(sa)};
      r.action+=lm;r.arclength+=radius*(b-a);
      for(std::size_t k=0;k<2;++k)for(std::size_t j=0;j<2;++j)for(std::size_t i=0;i<2;++i) {
        Real ax=(xc-Real(g.x[0]))/dx,bx=-radius/dx,az=-Real(g.z[0])/dz,bz=radius/dz;
        if(!i){ax=1-ax;bx=-bx;}if(!k){az=1-az;bz=-bz;}
        std::array<Real,4> coefficients{ax*az,bx*az,ax*bz,bx*bz};Real length=0,dv=0;
        for(std::size_t n=0;n<4;++n) {
          Real lt=radius*coefficients[n]*il[n]/2,vt=-coefficients[n]*iv[n]/(2*radius);
          length+=lt;dv+=vt;r.absolute_accumulation+=std::abs(lt)+std::abs(vt);
        }
        std::size_t id=(k*2+j)*2+i;r.length[id]+=length;r.dv[id]+=dv;
      }
    } else {
      Real length=p.r1-p.r0,z=p.z0;r.action+=length/z;r.arclength+=length;
      for(std::size_t k=0;k<2;++k)for(std::size_t j=0;j<2;++j)for(std::size_t i=0;i<2;++i) {
        Real ux=((p.r0+p.r1)/2+c.origin[0]-Real(g.x[0]))/dx,uz=(z-Real(g.z[0]))/dz;
        Real moment=length*(i?ux:1-ux)*(k?uz:1-uz)/2;std::size_t id=(k*2+j)*2+i;
        r.length[id]+=moment;r.dv[id]-=moment/(z*z);
        r.absolute_accumulation+=std::abs(moment)*(1+1/(z*z));
      }
    }
  }
  return r;
}
Real max_difference(const std::vector<Real> &a,const std::vector<Real> &b) {
  if(a.size()!=b.size())throw std::runtime_error("Control vector inventory mismatch");
  Real m=0;for(std::size_t j=0;j<a.size();++j)m=std::max(m,std::abs(a[j]-b[j]));return m;
}
void compare_reference(const char *name,const Result &actual,const Reference &expected) {
  // Declared tolerance only for these well-scaled cases. It includes endpoint,
  // transcendental and polynomial accumulation rounding and is NOT a proved
  // quadrature bound or a tolerance for arbitrary curves.
  Real allowance=4096*std::numeric_limits<Real>::epsilon()*
    std::max(Real(1),expected.absolute_accumulation+expected.arclength+std::abs(expected.action));
  Real ae=std::abs(actual.action-expected.action),le=std::abs(actual.arclength-expected.arclength);
  Real de=max_difference(actual.dv,expected.dv),ne=max_difference(actual.length,expected.length);
  std::cout << "{\"type\":\"analytic_reference\",\"name\":";quoted(std::cout,name);
  std::cout << ",\"action\":";real(std::cout,expected.action);std::cout << ",\"arclength\":";real(std::cout,expected.arclength);
  std::cout << ",\"dv\":";vector(std::cout,expected.dv);std::cout << ",\"length\":";vector(std::cout,expected.length);
  std::cout << ",\"action_error\":";real(std::cout,ae);std::cout << ",\"arclength_error\":";real(std::cout,le);
  std::cout << ",\"maximum_dv_error\":";real(std::cout,de);std::cout << ",\"maximum_length_error\":";real(std::cout,ne);
  std::cout << ",\"working_regression_allowance\":";real(std::cout,allowance);
  std::cout << ",\"manufactured_circle_center_roundoff\":";real(std::cout,expected.maximum_center_roundoff);
  std::cout << ",\"interval_certificate\":false}";flush();
  check(ae<=allowance,"analytic_action");check(le<=allowance,"analytic_arclength");
  check(de<=allowance,"all_analytic_nodal_dv");check(ne<=allowance,"all_analytic_nodal_lengths");
}
void compare_reversal(const Result &a,const Result &b) {
  Real allowance=4096*std::numeric_limits<Real>::epsilon()*std::max(Real(1),a.arclength);
  std::cout << "{\"type\":\"reversal_differences\",\"action\":";real(std::cout,std::abs(a.action-b.action));
  std::cout << ",\"dv\":";real(std::cout,max_difference(a.dv,b.dv));std::cout << ",\"length\":";real(std::cout,max_difference(a.length,b.length));
  std::cout << ",\"working_regression_allowance\":";real(std::cout,allowance);std::cout << '}';flush();
  check(std::abs(a.action-b.action)<=allowance,"reversal_action");
  check(max_difference(a.dv,b.dv)<=allowance,"reversal_all_nodal_dv");
  check(max_difference(a.length,b.length)<=allowance,"reversal_all_nodal_lengths");
}
Grid homogeneous_grid() {
  Grid g;g.x={-1,1,2,4};g.y={-1,1,3,5};g.z={.5,1.75,3};
  g.v.assign(g.x.size()*g.y.size()*g.z.size(),2);return g;
}
Curve homogeneous_curve() {
  Curve c;c.origin={0,0};c.azimuth={Real(3)/5,Real(4)/5};
  c.pieces.push_back(Piece::line(0,1,5,Real(5)/2));
  c.status={"invented_oblique_line","manufactured_geometry","selected_curve_only"};return c;
}
Grid affine_grid() {
  Grid g;g.x={-1,4};g.y={-1,1};g.z={.5,2};g.v.resize(8);
  for(std::size_t k=0;k<2;++k)for(std::size_t j=0;j<2;++j)for(std::size_t i=0;i<2;++i)g.v[g.id(i,j,k)]=g.z[k];
  return g;
}
Curve affine_curve() {
  Curve c;c.origin={0,0};c.azimuth={1,0};const Real a=lcr::pi()/3,b=lcr::pi()/2;
  const Real sweep=b-a,kappa=Real(1)/2;
  // Manufacture the source from the desired exact stored guide depth. This
  // changes no kernel endpoint and applies no clamp; the difference from the
  // ideal zero-centered circle is reported with the analytic reference.
  const Real rise=(2*std::sin(sweep/2)/kappa)*std::cos(a+sweep/2);
  c.pieces.push_back(Piece::arc_increment(0,2-rise,a,sweep,kappa));
  auto p=c.pieces.back().end();
  c.pieces.push_back(Piece::line(p.r,p.z,p.r+Real(1)/2,p.z,lcr::PieceKind::boundary_guide));
  p=c.pieces.back().end();c.pieces.push_back(Piece::arc_increment(p.r,p.z,b,sweep,kappa));
  c.status={"invented_affine_arc_guide","manufactured_geometry","selected_curve_only"};return c;
}
Curve reverse_line(const Curve &c) {
  Curve r;const Point endpoint=c.at(c.pieces.size()-1,1);
  r.origin={endpoint[0],endpoint[1]};r.azimuth={-c.azimuth[0],-c.azimuth[1]};r.status=c.status;
  const auto &p=c.pieces.at(0);r.pieces.push_back(Piece::line(0,p.z1,p.r1-p.r0,p.z0));
  return r;
}
Curve reverse_symmetric_affine(const Curve &c) {
  // Reflection reverses this manufactured symmetric arc/guide curve in exact
  // arithmetic. Keeping its stored pieces also keeps their exact joins; any
  // working-trigonometry asymmetry is covered by the stated comparison scale.
  Curve r=c;Point endpoint=c.at(c.pieces.size()-1,1);
  r.origin={endpoint[0],endpoint[1]};r.azimuth={-c.azimuth[0],-c.azimuth[1]};return r;
}
bool identical(const Result &a,const Result &b) {
  return a.action==b.action && a.arclength==b.arclength && a.dv==b.dv && a.length==b.length &&
    a.action_difference==b.action_difference && a.dv_max_difference==b.dv_max_difference &&
    a.length_max_difference==b.length_max_difference && a.maximum_face_coordinate_residual==b.maximum_face_coordinate_residual &&
    a.pieces==b.pieces && a.subpieces==b.subpieces && a.samples==b.samples && a.face_crossings==b.face_crossings &&
    a.supplied_status.branch==b.supplied_status.branch && a.supplied_status.completeness==b.supplied_status.completeness &&
    a.supplied_status.derivatives==b.supplied_status.derivatives;
}
void run() {
  const Grid hg=homogeneous_grid(),ag=affine_grid();const Curve hc=homogeneous_curve(),ac=affine_curve();
  ++groups;const Result h=evaluated("homogeneous_xyz_crossings",hg,hc);
  compare_reference("homogeneous_global_cubics",h,polynomial_reference(hg,hc,2));
  check(h.face_crossings==5,"all_five_internal_xyz_plane_crossings");
  check(h.subpieces==6 && h.samples==144,"five_distinct_cuts_and_declared_8_plus_16_samples");
  ++groups;const Result a=evaluated("affine_arc_and_positive_guide",ag,ac);
  compare_reference("affine_elementary_antiderivatives",a,affine_reference(ag,ac));
  check(ac.pieces[1].z0==2 && ac.pieces[1].z1==2,"guide_exactly_at_physical_bottom");
  check(a.pieces==3 && a.subpieces==3 && a.samples==72,"two_arcs_and_one_guide_inventory");
  ++groups;compare_reversal(h,evaluated("reversed_homogeneous",hg,reverse_line(hc)));
  compare_reversal(a,evaluated("reversed_symmetric_affine_guide",ag,reverse_symmetric_affine(ac)));
  ++groups;
  const auto coarse=lcr::display_samples(ac,Real(1)),fine=lcr::display_samples(ac,Real(1)/32);display_calls+=2;
  std::cout << "{\"type\":\"display_only\",\"coarse_spacing\":";real(std::cout,1);
  std::cout << ",\"fine_spacing\":";real(std::cout,Real(1)/32);
  std::cout << ",\"coarse_points\":" << coarse.size() << ",\"fine_points\":" << fine.size() << '}';flush();
  check(fine.size()>coarse.size(),"display_resolution_actually_changes_polygon");
  check(identical(a,evaluated("after_display_sampling",ag,ac)),"display_does_not_change_any_integral_or_work_field");
  ++groups;Grid changed=hg;const std::size_t changed_id=changed.id(1,0,0);
  changed.v[changed_id]=std::nextafter(changed.v[changed_id],std::numeric_limits<double>::infinity());
  supplied("one_binary64_ulp_lateral_change",changed,hc);++attempts;bool rejected=false;std::string message;
  try{(void)lcr::integrate(changed,hc);}catch(const std::runtime_error &e){rejected=true;message=e.what();}
  std::cout << "{\"type\":\"expected_rejection\",\"changed_node\":" << changed_id << ",\"message\":";quoted(std::cout,message);std::cout << '}';flush();
  check(rejected && message=="Grid is not exactly depth only","one_node_lateral_perturbation_rejected_before_integration");
  ++groups;Curve tied=hc;tied.status={"supplied_equal_time_branches","incomplete_branch_enumeration","nonunique_nodal_derivatives"};
  Result unresolved=evaluated("supplied_unresolved_status",hg,tied);
  check(unresolved.supplied_status.branch==tied.status.branch && unresolved.supplied_status.completeness==tied.status.completeness &&
        unresolved.supplied_status.derivatives==tied.status.derivatives,"supplied_tie_and_unresolved_status_not_promoted");
  check(unresolved.action==h.action && unresolved.dv==h.dv && unresolved.length==h.length,"status_metadata_does_not_change_selected_curve_integrals");
  check(groups==6 && checks==23 && attempts==7 && completed==6 && display_calls==2 && subpieces==27 && samples==648,"finite_control_roster");
}
} // namespace
int main(int argc,char **argv) {
  try {
    if(argc!=2)throw std::runtime_error("Usage: check_curved_integrals ABSENT_SUMMARY_JSON");
    if(argv[1][0]!='/')throw std::runtime_error("Summary path must be absolute");
    struct stat st{};
    if(lstat(argv[1],&st)==0)throw std::runtime_error("Summary path already exists or is a symlink");
    if(errno!=ENOENT)throw std::runtime_error("Cannot inspect summary path");
    std::cout << "{\"type\":\"scope\",\"groups\":6,\"checks\":24,\"integrate_attempts\":7,\"successful_integrations\":6,\"subpieces\":27,\"samples\":648,"
                 "\"display_calls\":2,\"real_data_calls\":0,\"branch_enumerator_calls\":0,\"optimizer_calls\":0,"
                 "\"arithmetic\":\"long double; finite regression allowance, no interval certificate\",\"epsilon\":";
    real(std::cout,std::numeric_limits<Real>::epsilon());std::cout << '}';flush();
    run();std::ofstream summary(argv[1]);if(!summary)throw std::runtime_error("Cannot create summary");
    summary << "{\"status\":\"passed\",\"groups\":" << groups << ",\"checks\":" << checks
            << ",\"integrate_attempts\":" << attempts << ",\"successful_integrations\":" << completed
            << ",\"rejected_before_samples\":1,\"subpieces\":" << subpieces << ",\"samples\":" << samples
            << ",\"display_calls\":" << display_calls << ",\"real_data_calls\":0,\"branch_enumerator_calls\":0,"
               "\"optimizer_calls\":0,\"interval_certificate\":false}\n";
    summary.close();if(!summary)throw std::runtime_error("Summary close failed");return 0;
  } catch(const std::exception &e){std::cerr << e.what() << '\n';return 1;}
}
