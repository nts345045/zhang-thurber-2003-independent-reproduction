#pragma once
// Narrow adaptation of originals/ray_metric.hpp, included after the frozen
// candidate supplies solve_free_ray_metric/ray_metric_product and statistics.
// Held internal contacts are immutable equalities for THIS direction search,
// not physical constraints. Physical box membership is provided separately.
namespace face_acceleration {
struct HeldConeStats : ConeRayMetricStats {
  std::vector<bool> active;
  std::size_t held_equalities=0;
};
// sign[k]=+1 imposes d[k]>=0, -1 imposes d[k]<=0, 0 leaves it free.
// A feasible active-set method, not repeated infeasible equality jumps.
inline Vec solve_held_cone_ray_metric(const Vec &weights,const Vec &gradient,
                          const std::vector<int> &sign,
                          const std::vector<bool> &held,HeldConeStats &stats,
                          int maximum_solves=10000) {
  stats=HeldConeStats{};
  if(weights.size()<2||gradient.size()!=3*(weights.size()-1)||
     sign.size()!=gradient.size()||held.size()!=gradient.size())
    throw std::runtime_error("Held cone ray metric dimensions disagree");
  if(maximum_solves<1||maximum_solves>10000)
    throw std::runtime_error("Held cone solve budget must be in [1,10000]");
  for(double value:weights)if(!(value>0)||!std::isfinite(value))
    throw std::runtime_error("Cone ray metric requires finite positive weights");
  for(double value:gradient)if(!std::isfinite(value))
    throw std::runtime_error("Cone ray metric requires a finite gradient");
  std::vector<bool> fixed(gradient.size());
  Vec direction(gradient.size(),0);
  auto finish=[&]() {
    stats.active=fixed;
    stats.final_fixed=int(std::count(fixed.begin(),fixed.end(),true));
    return direction;
  };
  for(std::size_t k=0;k<sign.size();++k) {
    if(sign[k]<-1||sign[k]>1)throw std::runtime_error("Invalid cone bound sign");
    fixed[k]=held[k]||sign[k]!=0;
    stats.held_equalities+=held[k];
    stats.initial_fixed+=fixed[k];
  }
  for(std::size_t i=1;i<weights.size();++i)
    if(!std::isfinite(weights[i-1]+weights[i])) {
      stats.message="Nonfinite principal coefficient";return finish();
    }
  for(;stats.solves<maximum_solves;) {
    Vec pivots(weights.size()-1);
    for(int axis=0;axis<3;++axis)for(std::size_t i=0;i<pivots.size();++i) {
      const std::size_t k=3*i+axis;
      pivots[i]=fixed[k]?1:weights[i]+weights[i+1];
      if(i&&!fixed[k]&&!fixed[k-3])pivots[i]-=(weights[i]/pivots[i-1])*weights[i];
      if(!(pivots[i]>0)||!std::isfinite(pivots[i])) {
        stats.message="Nonpositive or nonfinite principal pivot";return finish();
      }
    }
    Vec candidate=solve_free_ray_metric(weights,gradient,fixed);
    ++stats.solves;
    double fraction=1;
    std::size_t blocker=gradient.size();
    for(std::size_t k=0;k<gradient.size();++k) {
      if(!std::isfinite(candidate[k])) {stats.message="Nonfinite free minimizer";return finish();}
      if(held[k]&&candidate[k]!=0) {stats.message="Held equality changed";return finish();}
      if(!fixed[k]&&sign[k]&&sign[k]*candidate[k]<0) {
        const double distance=sign[k]*direction[k];
        const double travel=distance-sign[k]*candidate[k];
        if(!(distance>=0)||!(travel>0)||!std::isfinite(travel)) {
          stats.message="Unrepresentable blocking travel";return finish();
        }
        const double crossing=distance/travel;
        if(!(crossing>=0&&crossing<=1)) {stats.message="Invalid blocking fraction";return finish();}
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
      for(double value:direction) {
        if(!std::isfinite(value)) {stats.message="Nonfinite blocking interpolation";return finish();}
        direction_scale=std::max(direction_scale,std::abs(value));
      }
      const double roundoff=64*std::numeric_limits<double>::epsilon()*direction_scale;
      for(std::size_t k=0;k<direction.size();++k)if(sign[k]&&sign[k]*direction[k]<0) {
        if(-sign[k]*direction[k]>roundoff) {stats.message="Blocking step lost feasibility";return finish();}
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
        stats.message="Nonfinite quadratic product, residual or arithmetic scale";return finish();
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
      if(fixed[k]&&!held[k]&&sign[k]*residual[k]<-tolerance[k]&&sign[k]*residual[k]<worst) {
        worst=sign[k]*residual[k];release=k;
      }
    if(release<gradient.size()) {fixed[release]=false;++stats.releases;continue;}
    stats.slope=std::inner_product(gradient.begin(),gradient.end(),direction.begin(),0.0);
    if(!std::isfinite(stats.slope)) {stats.message="Nonfinite quadratic directional slope";return finish();}
    bool certified=true;
    for(std::size_t k=0;k<gradient.size();++k) {
      if(held[k]) {
        // An equality multiplier has no sign restriction, even at a box face.
        certified=certified&&direction[k]==0;
        continue;
      }
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
    return finish();
  }
  stats.message="Quadratic active-set solve guard reached; no solution certificate";
  return finish();
}
} // namespace face_acceleration
