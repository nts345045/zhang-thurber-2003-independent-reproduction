#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

// Isolated continuous-curve integrator. All working arithmetic, including
// trigonometry and grid-face root locations, is long double. The 8/16-point
// Gauss difference is an error diagnostic, not an outward error certificate.
// No polygon action, optimizer status, or production Ray flag is constructed.
namespace lcr {
using Real = long double;
using Point = std::array<Real, 3>;

inline void require(bool condition, const char *message) {
  if (!condition) throw std::runtime_error(message);
}
inline bool finite(Real value) { return std::isfinite(value); }
inline Real pi() { return std::acos(Real(-1)); }

enum class PieceKind { straight, vertical, plateau_guide, boundary_guide, affine_arc };
struct Meridional { Real r, z; };

struct Piece {
  PieceKind kind = PieceKind::straight;
  Real r0 = 0, z0 = 0, r1 = 0, z1 = 0;
  Real theta0 = 0, theta1 = 0, sweep = 0, kappa = 0;

  static Piece line(Real r0, Real z0, Real r1, Real z1,
                    PieceKind kind = PieceKind::straight) {
    for (Real q : {r0, z0, r1, z1}) require(finite(q), "Nonfinite line coordinate");
    require(kind != PieceKind::affine_arc, "Line cannot have arc kind");
    require(r1 >= r0 && (r1 != r0 || z1 != z0), "Require positive line length and forward range");
    if (kind == PieceKind::vertical) require(r0 == r1, "Vertical piece has transverse motion");
    if (kind == PieceKind::plateau_guide || kind == PieceKind::boundary_guide)
      require(z0 == z1, "Guide is not horizontal");
    Piece p;
    p.kind = kind; p.r0 = r0; p.z0 = z0; p.r1 = r1; p.z1 = z1;
    require(finite(p.arclength()) && p.arclength() > 0, "Unrepresentable line length");
    return p;
  }

  static Piece arc(Real r0, Real z0, Real theta0, Real theta1, Real kappa) {
    require(finite(theta1) && theta1>theta0, "Require ordered arc angles");
    return arc_increment(r0,z0,theta0,theta1-theta0,kappa);
  }
  static Piece arc_increment(Real r0, Real z0, Real theta0, Real sweep, Real kappa) {
    for (Real q : {r0, z0, theta0, sweep, kappa}) require(finite(q), "Nonfinite arc parameter");
    require(kappa>0 && theta0>=0 && theta0<=pi() && sweep>0 && sweep<=pi()-theta0,
            "Require positive arc curvature and sweep within [0,pi]");
    require(theta0>=pi()/2 || sweep<=pi()/2-theta0, "Split arc at its depth turn");
    Piece p;
    p.kind = PieceKind::affine_arc; p.r0 = r0; p.z0 = z0;
    p.theta0 = theta0; p.theta1 = theta0+sweep; p.sweep=sweep; p.kappa = kappa;
    Meridional end = p.at(1);
    p.r1 = end.r; p.z1 = end.z;
    require(finite(end.r) && finite(end.z) && end.r >= r0 && (end.r!=r0 || end.z!=z0),
            "Unrepresentable arc endpoint");
    require(finite(p.arclength()) && p.arclength() > 0, "Unrepresentable arc length");
    return p;
  }

  Meridional at(Real t) const {
    require(finite(t) && t >= 0 && t <= 1, "Piece parameter outside [0,1]");
    if (t == 0) return {r0, z0};
    if (kind != PieceKind::affine_arc) {
      if (t == 1) return {r1, z1};
      return {r0 + (r1-r0)*t, z0 + (z1-z0)*t};
    }
    Real half = sweep*t/2;
    Real chord = 2*std::sin(half)/kappa;
    return {r0 + chord*std::sin(theta0+half),
            z0 + chord*std::cos(theta0+half)};
  }
  Meridional begin() const { return {r0,z0}; }
  Meridional end() const { return at(1); }
  Real arclength() const {
    return kind == PieceKind::affine_arc ? sweep/kappa : std::hypot(r1-r0,z1-z0);
  }
};

struct BranchStatus {
  std::string branch;
  std::string completeness = "not_assessed";
  std::string derivatives = "selected_curve_only";
};
struct Curve {
  std::array<Real,2> origin{}, azimuth{1,0};
  std::vector<Piece> pieces;
  BranchStatus status;
  Point at(std::size_t piece, Real t) const {
    Meridional p = pieces.at(piece).at(t);
    return {origin[0]+azimuth[0]*p.r, origin[1]+azimuth[1]*p.r, p.z};
  }
};
struct Grid {
  std::vector<double> x,y,z,v;
  std::size_t id(std::size_t i,std::size_t j,std::size_t k) const {
    return (k*y.size()+j)*x.size()+i;
  }
};

inline void validate(const Grid &g,const Curve &curve) {
  for (const auto *axis : {&g.x,&g.y,&g.z}) {
    require(axis->size() >= 2, "Grid axis needs at least two nodes");
    for (std::size_t i=0;i<axis->size();++i)
      require(std::isfinite((*axis)[i]) && (!i || (*axis)[i]>(*axis)[i-1]),
              "Require finite strictly increasing grid axes");
  }
  require(g.x.size() <= std::numeric_limits<std::size_t>::max()/g.y.size(), "Grid size overflow");
  const std::size_t xy=g.x.size()*g.y.size();
  require(xy <= std::numeric_limits<std::size_t>::max()/g.z.size(), "Grid size overflow");
  require(g.v.size()==xy*g.z.size(), "Velocity inventory differs from grid dimensions");
  for (std::size_t k=0;k<g.z.size();++k)
    for (std::size_t j=0;j<g.y.size();++j)
      for (std::size_t i=0;i<g.x.size();++i) {
        double q=g.v[g.id(i,j,k)];
        require(std::isfinite(q) && q>0, "Require positive finite nodal velocities");
        require(q==g.v[g.id(0,0,k)], "Grid is not exactly depth only");
      }
  for (Real q : {curve.origin[0],curve.origin[1],curve.azimuth[0],curve.azimuth[1]})
    require(finite(q), "Nonfinite curve embedding");
  const Real azimuth_norm=std::hypot(curve.azimuth[0],curve.azimuth[1]);
  require(std::abs(azimuth_norm-1)<=8*std::numeric_limits<Real>::epsilon(),
          "Curve azimuth is not unit at working precision");
  for (std::size_t j=0;j<curve.pieces.size();++j) {
    const auto &p=curve.pieces[j];
    // Public fields support simple branch construction, but factories are
    // rechecked so a modified/default piece cannot bypass their geometry guards.
    if (p.kind==PieceKind::affine_arc)
      (void)Piece::arc_increment(p.r0,p.z0,p.theta0,p.sweep,p.kappa);
    else
      (void)Piece::line(p.r0,p.z0,p.r1,p.z1,p.kind);
    if (j) {
      Meridional a=curve.pieces[j-1].end(),b=p.begin();
      require(a.r==b.r && a.z==b.z, "Curve pieces are not joined exactly as stored");
    }
    for (Real t : {Real(0),Real(1)}) {
      Point q=curve.at(j,t);
      const std::vector<double> *axes[]{&g.x,&g.y,&g.z};
      for (int k=0;k<3;++k)
        require(finite(q[k]) && q[k]>=axes[k]->front() && q[k]<=axes[k]->back(),
                "Curve endpoint outside physical grid box");
    }
  }
}

struct Partition {
  std::vector<Real> cuts{0,1};
  Real maximum_face_residual=0;
  std::size_t crossings=0;
};
inline Partition partition(const Grid &g,const Curve &curve,std::size_t piece) {
  Partition result;
  const Point a=curve.at(piece,0),b=curve.at(piece,1);
  const std::vector<double> *axes[]{&g.x,&g.y,&g.z};
  for (int k=0;k<3;++k) {
    if (a[k]==b[k]) continue;
    const bool increasing=b[k]>a[k];
    for (double raw_face : *axes[k]) {
      const Real face=raw_face;
      if (!(face>std::min(a[k],b[k]) && face<std::max(a[k],b[k]))) continue;
      Real lo=0,hi=1;
      for (unsigned iteration=0;iteration<256;++iteration) {
        Real mid=lo+(hi-lo)/2;
        if (mid==lo || mid==hi) break;
        Real value=curve.at(piece,mid)[k];
        if (value==face) {lo=mid;hi=mid;break;}
        if ((value<face)==increasing) lo=mid; else hi=mid;
      }
      require(lo==hi || std::nextafter(lo,hi)==hi, "Grid-face root did not resolve at working precision");
      Real t=lo+(hi-lo)/2;
      require(t>0 && t<1 && finite(t), "Interior grid crossing is not representable");
      result.maximum_face_residual=std::max(result.maximum_face_residual,
                                            std::abs(curve.at(piece,t)[k]-face));
      result.cuts.push_back(t);
      ++result.crossings;
    }
  }
  std::sort(result.cuts.begin(),result.cuts.end());
  result.cuts.erase(std::unique(result.cuts.begin(),result.cuts.end()),result.cuts.end());
  for (std::size_t j=1;j<result.cuts.size();++j) {
    Real a0=result.cuts[j-1],b0=result.cuts[j],m=a0+(b0-a0)/2;
    require(a0<m && m<b0, "Grid-partition interval has no working-precision interior");
  }
  return result;
}

struct Accumulator {
  Real action=0;
  std::vector<Real> dv,length;
  explicit Accumulator(std::size_t n):dv(n,0),length(n,0) {}
};
inline void add_sample(const Grid &g,Point point,Real ds,Accumulator &sum) {
  const std::vector<double> *axes[]{&g.x,&g.y,&g.z};
  std::size_t cell[3];
  Real u[3];
  for (int k=0;k<3;++k) {
    const auto &a=*axes[k];
    require(finite(point[k]) && point[k]>=a.front() && point[k]<=a.back(),
            "Curve quadrature sample outside physical box");
    auto found=std::upper_bound(a.begin(),a.end(),point[k]);
    cell[k]=found==a.end()?a.size()-2:std::size_t(found-a.begin()-1);
    const Real width=Real(a[cell[k]+1])-Real(a[cell[k]]);
    u[k]=(point[k]-Real(a[cell[k]]))/width;
    require(finite(width) && width>0 && u[k]>=0 && u[k]<=1, "Unrepresentable local basis");
  }
  // Exact nodal equality was checked globally. This expression preserves the
  // lateral invariance of v while retaining all eight 3D basis weights below.
  Real v0=g.v[g.id(0,0,cell[2])],v1=g.v[g.id(0,0,cell[2]+1)];
  Real velocity=v0+(v1-v0)*u[2];
  require(finite(velocity) && velocity>0 && finite(ds) && ds>0, "Nonpositive sample speed or measure");
  const Real dt=ds/velocity, model_factor=dt/velocity;
  require(finite(dt) && finite(model_factor), "Nonfinite sample integral");
  sum.action+=dt;
  for (std::size_t k=0;k<2;++k)
    for (std::size_t j=0;j<2;++j)
      for (std::size_t i=0;i<2;++i) {
        Real basis=(i?u[0]:1-u[0])*(j?u[1]:1-u[1])*(k?u[2]:1-u[2]);
        std::size_t id=g.id(cell[0]+i,cell[1]+j,cell[2]+k);
        sum.dv[id]-=model_factor*basis;
        sum.length[id]+=ds*basis;
      }
}

struct Result {
  Real action=0,arclength=0;
  std::vector<Real> dv,length;
  Real action_difference=0,dv_max_difference=0,length_max_difference=0;
  Real maximum_face_coordinate_residual=0;
  std::size_t pieces=0,subpieces=0,samples=0,face_crossings=0;
  BranchStatus supplied_status;
};
inline Result integrate(const Grid &g,const Curve &curve) {
  validate(g,curve);
  static const Real x8[]{0.183434642495649804939476142360184L,0.525532409916328985817739049189246L,
    0.796666477413626739591553936475831L,0.960289856497536231683560868569473L};
  static const Real w8[]{0.362683783378361982965150449277196L,0.313706645877887287337962201986601L,
    0.222381034453374470544355994426240L,0.101228536290376259152531354309962L};
  static const Real x16[]{0.095012509837637440185319335424958L,0.281603550779258913230460501460496L,
    0.458016777657227386342419442983578L,0.617876244402643748446671764048791L,
    0.755404408355003033895101194847442L,0.865631202387831743880467897712393L,
    0.944575023073232576077988415534608L,0.989400934991649932596154173450333L};
  static const Real w16[]{0.189450610455068496285396723208283L,0.182603415044923588866763667969220L,
    0.169156519395002538189312079030359L,0.149595988816576732081501730547479L,
    0.124628971255533872052476282192016L,0.095158511682492784809925107602246L,
    0.062253523938647892862843836994378L,0.027152459411754094851780572456018L};
  Accumulator coarse(g.v.size()),fine(g.v.size());
  Result result;
  result.pieces=curve.pieces.size(); result.supplied_status=curve.status;
  for (std::size_t piece=0;piece<curve.pieces.size();++piece) {
    const Real length=curve.pieces[piece].arclength();
    result.arclength+=length;
    Partition p=partition(g,curve,piece);
    result.face_crossings+=p.crossings;
    result.maximum_face_coordinate_residual=std::max(result.maximum_face_coordinate_residual,p.maximum_face_residual);
    for (std::size_t part=1;part<p.cuts.size();++part) {
      Real a=p.cuts[part-1],b=p.cuts[part],half=(b-a)/2,mid=a+half;
      auto rule=[&](const Real *nodes,const Real *weights,std::size_t count,Accumulator &out) {
        for (std::size_t j=0;j<count;++j)
          for (Real sign : {Real(-1),Real(1)}) {
            Real t=mid+sign*half*nodes[j];
            if (!(t>a && t<b)) {
              std::ostringstream message;
              message << "Quadrature node rounded to a partition endpoint"
                      << " [piece_index=" << piece
                      << "; piece_kind=" << int(curve.pieces[piece].kind)
                      << "; partition_index=" << part-1
                      << "; partition_cut_count=" << p.cuts.size()
                      << "; gauss_rule_nodes=" << 2*count
                      << "; positive_node_index=" << j
                      << "; completed_samples=" << result.samples
                      << "; completed_subpieces=" << result.subpieces
                      << "; real_radix=" << std::numeric_limits<Real>::radix
                      << "; real_digits=" << std::numeric_limits<Real>::digits
                      << std::hexfloat
                      << "; a_hex=" << a << "; b_hex=" << b
                      << "; half_hex=" << half << "; mid_hex=" << mid
                      << "; sign_hex=" << sign << "; node_hex=" << nodes[j]
                      << "; weight_hex=" << weights[j] << "; t_hex=" << t
                      << "; piece_arclength_hex=" << length << ']';
              throw std::runtime_error(message.str());
            }
            add_sample(g,curve.at(piece,t),length*half*weights[j],out);
            ++result.samples;
          }
      };
      rule(x8,w8,4,coarse); rule(x16,w16,8,fine);
      ++result.subpieces;
    }
  }
  result.action=fine.action; result.dv=std::move(fine.dv); result.length=std::move(fine.length);
  result.action_difference=std::abs(result.action-coarse.action);
  require(finite(result.action) && finite(result.arclength) && finite(result.action_difference),
          "Nonfinite total curve integral");
  for (std::size_t j=0;j<g.v.size();++j) {
    require(finite(result.dv[j]) && finite(result.length[j]), "Nonfinite nodal curve integral");
    result.dv_max_difference=std::max(result.dv_max_difference,std::abs(result.dv[j]-coarse.dv[j]));
    result.length_max_difference=std::max(result.length_max_difference,std::abs(result.length[j]-coarse.length[j]));
  }
  require(finite(result.dv_max_difference) && finite(result.length_max_difference),
          "Nonfinite quadrature-difference diagnostic");
  return result;
}

inline std::vector<Point> display_samples(const Curve &curve,Real maximum_spacing) {
  require(finite(maximum_spacing) && maximum_spacing>0, "Invalid display spacing");
  std::vector<Point> points;
  for (std::size_t j=0;j<curve.pieces.size();++j) {
    Real count=std::ceil(curve.pieces[j].arclength()/maximum_spacing);
    require(finite(count) && count>=1 && count<std::numeric_limits<std::size_t>::max(), "Display inventory overflow");
    std::size_t n=std::size_t(count);
    if (!j) points.push_back(curve.at(j,0));
    for (std::size_t i=1;i<=n;++i) points.push_back(curve.at(j,Real(i)/Real(n)));
  }
  return points;
}
} // namespace lcr
