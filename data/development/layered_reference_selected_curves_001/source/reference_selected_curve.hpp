#pragma once
#include "layered_curved_ray.hpp"
#include <cerrno>
#include <cstdlib>
#include <istream>

// Working reconstruction of two externally selected branches. No enumeration,
// root adjustment, endpoint repair, optimizer, or production flags.
namespace selected_curve {
using lcr::Real;
using lcr::require;

inline Real decimal(const std::string &token) {
  char *end = nullptr;
  errno = 0;
  const Real value = std::strtold(token.c_str(), &end);
  require(end == token.c_str()+token.size() && end != token.c_str() &&
          errno != ERANGE && lcr::finite(value), "Invalid working scalar");
  return value;
}
inline Real rational(const std::string &token) {
  const auto slash = token.find('/');
  require(slash != std::string::npos && token.find('/',slash+1)==std::string::npos,
          "Require numerator/denominator token");
  const auto integer = [](const std::string &s) {
    require(!s.empty(), "Empty rational integer");
    std::size_t first = s[0]=='-' ? 1 : 0;
    require(first < s.size(), "Empty signed integer");
    for (std::size_t k=first;k<s.size();++k)
      require(s[k]>='0' && s[k]<='9', "Noninteger rational token");
  };
  const auto numerator=token.substr(0,slash), denominator=token.substr(slash+1);
  integer(numerator); integer(denominator);
  const Real n=decimal(numerator),d=decimal(denominator);
  require(d>0, "Nonpositive rational denominator");
  const Real value=n/d;
  require(lcr::finite(value) && (n==0 || value!=0), "Unrepresentable rational value");
  return value; // Two strtold conversions and a division, not exact rounding.
}

struct Spec {
  std::string case_id,branch,u_exact,turn_exact,guide_exact,completeness,derivatives;
  Real u=0,turn=0,guide=0;
};
inline Spec read_spec(std::istream &in) {
  Spec s; std::string magic,extra;
  require(bool(in >> magic >> s.case_id >> s.branch >> s.u_exact >> s.turn_exact
                  >> s.guide_exact >> s.completeness >> s.derivatives),
          "Incomplete selected-curve input");
  require(!(in >> extra) && magic=="reference_selected_curve_v1", "Unexpected spec tokens");
  require((s.case_id=="lom_24104" && s.branch=="bottom_boundary") ||
          (s.case_id=="lon_8670" && s.branch=="turning"), "Outside fixed two-case roster");
  require(s.completeness=="not_assessed_by_this_component" &&
          s.derivatives=="selected_curve_only", "Unexpected diagnostic status");
  s.u=rational(s.u_exact); s.turn=rational(s.turn_exact); s.guide=rational(s.guide_exact);
  require(s.u>0 && s.guide>=0, "Invalid selected phase speed or guide length");
  return s;
}

struct Join {
  Real nominal_begin=0,nominal_end=0,velocity_begin=0,velocity_end=0,slope=0;
  Real theta=0,sweep=0;
  lcr::Meridional actual_begin{},actual_end{};
  std::array<Real,2> tangent_begin{},tangent_end{};
  std::size_t layer=0;
  std::string kind;
};
struct Build {
  lcr::Curve curve;
  std::vector<Join> joins;
  std::string stage="not_started";
  Real horizontal_distance=0,turn_profile_velocity=0;
  bool profile_evaluated=false;
  Real endpoint_closure=0,maximum_depth_join_error=0,maximum_tangent_jump=0;
  Join pending_join;
  bool has_pending_join=false;
};

inline Real velocity(const lcr::Grid &g,Real z) {
  require(z>=g.z.front() && z<=g.z.back(), "Depth outside profile");
  for (std::size_t k=0;k<g.z.size();++k)
    if (z==Real(g.z[k])) return g.v[g.id(0,0,k)];
  auto it=std::upper_bound(g.z.begin(),g.z.end(),z);
  const std::size_t k=std::size_t(it-g.z.begin()-1);
  const Real a=g.v[g.id(0,0,k)],b=g.v[g.id(0,0,k+1)];
  return a+(b-a)*(z-Real(g.z[k]))/(Real(g.z[k+1])-Real(g.z[k]));
}
inline Real qvalue(Real u,Real v) {
  require(v>0 && v<=u, "Velocity exceeds selected phase speed");
  const Real q=std::sqrt((u-v)*(u+v));
  require(lcr::finite(q), "Unrepresentable vertical phase factor");
  return q;
}
inline Real positive_sweep(Real u,Real low,Real high) {
  require(high>low, "Arc has no positive speed increment");
  const Real ql=qvalue(u,low),qh=qvalue(u,high);
  const Real sum=high*ql+low*qh;
  require(sum>0 && lcr::finite(sum), "Unresolved arc numerator divisor");
  const Real numerator=u*u*(high-low)*(high+low)/sum;
  const Real denominator=low*high+ql*qh;
  const Real delta=std::atan2(numerator,denominator);
  require(lcr::finite(delta) && delta>0 && delta<=lcr::pi()/2,
          "Unresolved positive arc sweep");
  return delta;
}

inline void append(Build &b,const lcr::Piece &piece,Join join) {
  join.actual_begin=piece.begin(); join.actual_end=piece.end();
  if (piece.kind==lcr::PieceKind::affine_arc) {
    join.tangent_begin={std::sin(piece.theta0),std::cos(piece.theta0)};
    join.tangent_end={std::sin(piece.theta0+piece.sweep),std::cos(piece.theta0+piece.sweep)};
  } else {
    const Real length=piece.arclength();
    join.tangent_begin={(piece.r1-piece.r0)/length,(piece.z1-piece.z0)/length};
    join.tangent_end=join.tangent_begin;
  }
  if (!b.joins.empty()) {
    const auto &old=b.joins.back().tangent_end;
    b.maximum_tangent_jump=std::max(b.maximum_tangent_jump,
      std::hypot(old[0]-join.tangent_begin[0],old[1]-join.tangent_begin[1]));
  }
  b.maximum_depth_join_error=std::max(b.maximum_depth_join_error,
    std::max(std::abs(join.actual_begin.z-join.nominal_begin),
             std::abs(join.actual_end.z-join.nominal_end)));
  b.curve.pieces.push_back(piece); b.joins.push_back(join);
  b.has_pending_join=false;
}

inline void leg(const lcr::Grid &g,const Spec &s,Real za,Real zb,Build &b) {
  if (za==zb) return;
  const bool deeper=zb>za;
  std::vector<Real> depths{za,zb};
  for (double z:g.z) if (z>std::min(za,zb) && z<std::max(za,zb)) depths.push_back(z);
  std::sort(depths.begin(),depths.end());
  if (!deeper) std::reverse(depths.begin(),depths.end());
  for (std::size_t j=0;j+1<depths.size();++j) {
    const Real a=depths[j],z=depths[j+1],mid=a+(z-a)/2;
    auto it=std::upper_bound(g.z.begin(),g.z.end(),mid);
    require(it!=g.z.begin() && it!=g.z.end(), "Unresolved layer midpoint");
    const std::size_t k=std::size_t(it-g.z.begin()-1);
    const Real gradient=(Real(g.v[g.id(0,0,k+1)])-Real(g.v[g.id(0,0,k)]))/
                        (Real(g.z[k+1])-Real(g.z[k]));
    const Real va=a==s.turn?s.u:velocity(g,a),vz=z==s.turn?s.u:velocity(g,z);
    const lcr::Meridional begin=b.curve.pieces.empty()?lcr::Meridional{0,a}:
                               b.curve.pieces.back().end();
    Join join; join.nominal_begin=a; join.nominal_end=z; join.layer=k;
    join.velocity_begin=va; join.velocity_end=vz; join.slope=gradient;
    b.stage="construct_layer_"+std::to_string(k)+(deeper?"_deeper":"_shallower");
    if (gradient==0) {
      require(va==vz, "Constant layer endpoint speeds differ");
      const Real q=qvalue(s.u,va);
      require(q>0, "Tangent constant-layer ray cannot traverse depth");
      join.kind="constant_layer_line";
      b.pending_join=join;b.has_pending_join=true;
      append(b,lcr::Piece::line(begin.r,begin.z,begin.r+std::abs(z-a)*va/q,
                               begin.z+(z-a)),join);
    } else {
      require(gradient>0, "Selected diagnostic requires nondecreasing profile");
      const Real q=qvalue(s.u,va);
      join.theta=std::atan2(va,deeper?q:-q);
      join.sweep=positive_sweep(s.u,std::min(va,vz),std::max(va,vz));
      join.kind="affine_arc";
      b.pending_join=join;b.has_pending_join=true;
      append(b,lcr::Piece::arc_increment(begin.r,begin.z,join.theta,join.sweep,
                                       gradient/s.u),join);
    }
  }
}

inline void construct(const lcr::Grid &g,const lcr::Point &source,
                      const lcr::Point &receiver,const Spec &s,Build &b) {
  b.stage="validate_input";
  lcr::validate(g,lcr::Curve{});
  for (std::size_t k=1;k<g.z.size();++k)
    require(g.v[g.id(0,0,k)]>=g.v[g.id(0,0,k-1)], "Profile is not nondecreasing");
  const std::vector<double> *axes[]{&g.x,&g.y,&g.z};
  for (int k=0;k<3;++k)
    for (Real value:{source[k],receiver[k]})
      require(lcr::finite(value) && value>=axes[k]->front() && value<=axes[k]->back(),
              "Original endpoint outside grid");
  const Real dx=receiver[0]-source[0],dy=receiver[1]-source[1];
  b.horizontal_distance=std::hypot(dx,dy);
  require(b.horizontal_distance>0 && lcr::finite(b.horizontal_distance),
          "Fixed diagnostic roster requires nonzero horizontal range");
  require(s.turn>=std::max(source[2],receiver[2]) && s.turn<=g.z.back(),
          "Invalid selected turning depth");
  b.turn_profile_velocity=velocity(g,s.turn);
  b.profile_evaluated=true;
  b.curve.origin={source[0],source[1]};
  b.curve.azimuth={dx/b.horizontal_distance,dy/b.horizontal_distance};
  b.curve.status={s.branch=="turning"?"reference_selected_turning":
                  "reference_selected_bottom_guide",s.completeness,s.derivatives};
  if (s.branch=="bottom_boundary") {
    require(s.turn==g.z.back() && source[2]==s.turn &&
            s.u==Real(g.v[g.id(0,0,g.z.size()-1)]) && s.guide>0,
            "Bottom-source guide differs from fixed selected case");
    b.stage="construct_bottom_guide";
    Join join;join.nominal_begin=s.turn;join.nominal_end=s.turn;
    join.layer=g.z.size()-2;
    join.velocity_begin=s.u;join.velocity_end=s.u;join.kind="boundary_guide";
    append(b,lcr::Piece::line(0,s.turn,s.guide,s.turn,lcr::PieceKind::boundary_guide),join);
  } else {
    require(s.guide==0 && s.turn<g.z.back(), "Invalid selected interior turn");
    leg(g,s,source[2],s.turn,b);
  }
  leg(g,s,s.turn,receiver[2],b);
  b.stage="validate_constructed_curve";
  lcr::validate(g,b.curve);
  require(!b.curve.pieces.empty(), "Empty selected curve");
  const auto end=b.curve.at(b.curve.pieces.size()-1,1);
  b.endpoint_closure=std::hypot(std::hypot(end[0]-receiver[0],end[1]-receiver[1]),
                               end[2]-receiver[2]);
  require(lcr::finite(b.endpoint_closure), "Nonfinite receiver closure");
  b.stage="constructed";
}
} // namespace selected_curve
