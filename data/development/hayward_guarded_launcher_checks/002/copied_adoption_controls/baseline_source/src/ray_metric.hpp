#pragma once
// Positive-definite fixed-endpoint ray metric on a box tangent cone.
// This numerical search metric does not change the Fermat objective.
#include <algorithm>
#include <cmath>
#include <limits>
#include <numeric>
#include <stdexcept>
#include <string>
#include <vector>
using Vec = std::vector<double>;

// Principal submatrices retain the original diagonal: incident edges to fixed
// coordinates still contribute stiffness. A fixed coordinate separates blocks.
Vec solve_free_ray_metric(const Vec &weights, const Vec &gradient,
                          const std::vector<bool> &fixed) {
  const std::size_t n=weights.size()-1;
  if(gradient.size()!=3*n||fixed.size()!=3*n)
    throw std::runtime_error("Reduced ray metric dimensions disagree");
  Vec direction(3*n),diagonal(n),rhs(n);
  for(int axis=0;axis<3;++axis) {
    for(std::size_t i=0;i<n;++i) {
      const std::size_t k=3*i+axis;
      diagonal[i]=fixed[k]?1:weights[i]+weights[i+1];
      rhs[i]=fixed[k]?0:-gradient[k];
      if(i&&!fixed[k]&&!fixed[k-3]) {
        double ratio=-weights[i]/diagonal[i-1];
        diagonal[i]-=ratio*(-weights[i]);
        rhs[i]-=ratio*rhs[i-1];
      }
    }
    for(std::size_t i=n;i-->0;) {
      const std::size_t k=3*i+axis;
      double value=rhs[i];
      if(i+1<n&&!fixed[k]&&!fixed[k+3])
        value+=weights[i+1]*direction[k+3];
      direction[k]=value/diagonal[i];
    }
  }
  return direction;
}

struct ConeRayMetricStats {
  bool success=false;
  int solves=0,releases=0,blocks=0,initial_fixed=0,final_fixed=0;
  double free_equation_max_error=0,primal_violation=0,dual_violation=0;
  double complementarity_max_error=0,slope=0,kkt_roundoff_tolerance=0;
  double free_equation_relative_backward_error=0;
  double maximum_arithmetic_scale=0;
  std::string message;
};

Vec ray_metric_product(const Vec &weights,const Vec &direction) {
  const std::size_t n=weights.size()-1;
  Vec result(3*n);
  for(std::size_t i=0;i<n;++i)for(int axis=0;axis<3;++axis) {
    const std::size_t k=3*i+axis;
    result[k]=(weights[i]+weights[i+1])*direction[k];
    if(i)result[k]-=weights[i]*direction[k-3];
    if(i+1<n)result[k]-=weights[i+1]*direction[k+3];
  }
  return result;
}

// sign[k]=+1 imposes d[k]>=0, -1 imposes d[k]<=0, 0 leaves it free.
// A feasible active-set method, not repeated infeasible equality jumps.
Vec solve_cone_ray_metric(const Vec &weights,const Vec &gradient,
                          const std::vector<int> &sign,ConeRayMetricStats &stats,
                          int maximum_solves=10000) {
  stats=ConeRayMetricStats{};
  if(weights.size()<2||gradient.size()!=3*(weights.size()-1)||sign.size()!=gradient.size())
    throw std::runtime_error("Cone ray metric dimensions disagree");
  for(double value:weights)if(!(value>0)||!std::isfinite(value))
    throw std::runtime_error("Cone ray metric requires finite positive weights");
  for(double value:gradient)if(!std::isfinite(value))
    throw std::runtime_error("Cone ray metric requires a finite gradient");
  std::vector<bool> fixed(gradient.size());
  Vec direction(gradient.size(),0);
  for(std::size_t i=1;i<weights.size();++i)
    if(!std::isfinite(weights[i-1]+weights[i])) {
      stats.message="Nonfinite principal coefficient";return direction;
    }
  for(std::size_t k=0;k<sign.size();++k) {
    if(sign[k]<-1||sign[k]>1)throw std::runtime_error("Invalid cone bound sign");
    fixed[k]=sign[k]!=0;
    stats.initial_fixed+=fixed[k];
  }
  for(;stats.solves<maximum_solves;) {
    Vec pivots(weights.size()-1);
    for(int axis=0;axis<3;++axis)for(std::size_t i=0;i<pivots.size();++i) {
      const std::size_t k=3*i+axis;
      pivots[i]=fixed[k]?1:weights[i]+weights[i+1];
      if(i&&!fixed[k]&&!fixed[k-3])pivots[i]-=(weights[i]/pivots[i-1])*weights[i];
      if(!(pivots[i]>0)||!std::isfinite(pivots[i])) {
        stats.message="Nonpositive or nonfinite principal pivot";return direction;
      }
    }
    Vec candidate=solve_free_ray_metric(weights,gradient,fixed);
    ++stats.solves;
    double fraction=1;
    std::size_t blocker=gradient.size();
    for(std::size_t k=0;k<gradient.size();++k) {
      if(!std::isfinite(candidate[k])) {stats.message="Nonfinite free minimizer";return direction;}
      if(!fixed[k]&&sign[k]&&sign[k]*candidate[k]<0) {
        const double distance=sign[k]*direction[k];
        const double travel=distance-sign[k]*candidate[k];
        const double crossing=distance/travel;
        if(!(crossing>=0&&crossing<=1)) {stats.message="Invalid blocking fraction";return direction;}
        if(crossing<fraction) {fraction=crossing;blocker=k;}
      }
    }
    if(blocker<gradient.size()) {
      for(std::size_t k=0;k<direction.size();++k)
        direction[k]+=fraction*(candidate[k]-direction[k]);
      direction[blocker]=0;
      fixed[blocker]=true;
      ++stats.blocks;
      // Equal first hits can differ by a rounding bit. The exact feasible
      // interpolation cannot cross another cone face; report a larger defect.
      double direction_scale=0;
      for(double value:direction)direction_scale=std::max(direction_scale,std::abs(value));
      const double roundoff=64*std::numeric_limits<double>::epsilon()*direction_scale;
      for(std::size_t k=0;k<direction.size();++k)if(sign[k]&&sign[k]*direction[k]<0) {
        if(-sign[k]*direction[k]>roundoff) {stats.message="Blocking step lost feasibility";return direction;}
        direction[k]=0;
        if(!fixed[k]) {fixed[k]=true;++stats.blocks;}
      }
      continue;
    }
    direction=std::move(candidate);
    const Vec product=ray_metric_product(weights,direction);
    Vec residual=gradient,arithmetic_scale(gradient.size()),tolerance(gradient.size());
    for(std::size_t k=0;k<gradient.size();++k) {
      const std::size_t node=k/3;
      residual[k]+=product[k];
      arithmetic_scale[k]=std::abs(gradient[k])+
        (weights[node]+weights[node+1])*std::abs(direction[k]);
      if(node)arithmetic_scale[k]+=weights[node]*std::abs(direction[k-3]);
      if(node+2<weights.size())arithmetic_scale[k]+=weights[node+1]*std::abs(direction[k+3]);
      if(!std::isfinite(product[k])||!std::isfinite(residual[k])||!std::isfinite(arithmetic_scale[k])) {
        stats.message="Nonfinite quadratic product, residual or arithmetic scale";return direction;
      }
      tolerance[k]=64*std::numeric_limits<double>::epsilon()*arithmetic_scale[k];
    }
    // This tolerance only resolves roundoff in the quadratic KKT test. The
    // outer ray's action, Armijo and stationarity thresholds are unchanged.
    stats.kkt_roundoff_tolerance=*std::max_element(tolerance.begin(),tolerance.end());
    stats.maximum_arithmetic_scale=*std::max_element(arithmetic_scale.begin(),arithmetic_scale.end());
    std::size_t release=gradient.size();
    double worst=0;
    for(std::size_t k=0;k<gradient.size();++k)
      if(fixed[k]&&sign[k]*residual[k]<-tolerance[k]&&sign[k]*residual[k]<worst) {
        worst=sign[k]*residual[k];release=k;
      }
    if(release<gradient.size()) {fixed[release]=false;++stats.releases;continue;}
    stats.slope=std::inner_product(gradient.begin(),gradient.end(),direction.begin(),0.0);
    if(!std::isfinite(stats.slope)) {stats.message="Nonfinite quadratic directional slope";return direction;}
    bool certified=true;
    for(std::size_t k=0;k<gradient.size();++k) {
      stats.final_fixed+=fixed[k];
      if(!fixed[k]) {
        stats.free_equation_max_error=std::max(stats.free_equation_max_error,std::abs(residual[k]));
        const double relative=arithmetic_scale[k]>0?std::abs(residual[k])/arithmetic_scale[k]:0;
        stats.free_equation_relative_backward_error=std::max(stats.free_equation_relative_backward_error,relative);
        certified=certified&&std::abs(residual[k])<=tolerance[k];
      }
      if(sign[k]) {
        stats.primal_violation=std::max(stats.primal_violation,-sign[k]*direction[k]);
        stats.dual_violation=std::max(stats.dual_violation,-sign[k]*residual[k]);
        stats.complementarity_max_error=std::max(stats.complementarity_max_error,std::abs(direction[k]*residual[k]));
        const double complementarity=std::abs(direction[k]*residual[k]);
        const double complementarity_tolerance=std::abs(direction[k])*tolerance[k];
        certified=certified&&sign[k]*direction[k]>=0&&sign[k]*residual[k]>=-tolerance[k]&&
          std::isfinite(complementarity)&&std::isfinite(complementarity_tolerance)&&
          complementarity<=complementarity_tolerance;
      }
    }
    stats.success=certified;
    stats.message=certified?"Quadratic KKT conditions reached within arithmetic tolerance":
      "Quadratic residual exceeds arithmetic tolerance; no solution certificate";
    return direction;
  }
  stats.message="Quadratic active-set solve guard reached; no solution certificate";
  return direction;
}
