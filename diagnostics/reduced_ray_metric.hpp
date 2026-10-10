#pragma once
// Isolated diagnostic direction; this header is not included by the solver.
#include "../src/core.hpp"

struct ReducedRayMetricStats {
  int initial_fixed=0, added_fixed=0, solves=0, inward_multiplier_violations=0;
  double free_equation_max_error=0, slope=0, most_negative_signed_multiplier=0;
};

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

Vec reduced_ray_direction(const Grid &g,const std::vector<P> &path,
                          const Vec &gradient,ReducedRayMetricStats *record=nullptr) {
  const std::size_t n=path.size()-2;
  const Vec weights=ray_metric_weights(g,path);
  const Vec *axes[]={&g.x,&g.y,&g.z};
  std::vector<bool> lower(3*n),upper(3*n),fixed(3*n);
  ReducedRayMetricStats stats;
  for(std::size_t i=0;i<n;++i)for(int axis=0;axis<3;++axis) {
    const std::size_t k=3*i+axis;
    lower[k]=path[i+1][axis]<=axes[axis]->front()+1e-10;
    upper[k]=path[i+1][axis]>=axes[axis]->back()-1e-10;
    fixed[k]=(lower[k]&&gradient[k]>0)||(upper[k]&&gradient[k]<0);
    stats.initial_fixed+=fixed[k];
  }
  Vec direction;
  for(;;) {
    direction=solve_free_ray_metric(weights,gradient,fixed);
    ++stats.solves;
    bool changed=false;
    for(std::size_t k=0;k<direction.size();++k) {
      if(!std::isfinite(direction[k]))throw std::runtime_error("Nonfinite reduced metric direction");
      if(!fixed[k]&&((lower[k]&&direction[k]<0)||(upper[k]&&direction[k]>0))) {
        fixed[k]=true;
        ++stats.added_fixed;
        changed=true;
      }
    }
    if(!changed)break;
    if(stats.solves>int(gradient.size()))throw std::runtime_error("Reduced metric active-set loop exceeded its finite bound");
  }
  // Report the full tangent-cone KKT residual separately: this minimal method
  // never releases a coordinate within this direction solve. Its free equation
  // and descent can hold even if a fixed-coordinate multiplier has wrong sign.
  for(std::size_t i=0;i<n;++i)for(int axis=0;axis<3;++axis) {
    const std::size_t k=3*i+axis;
    double residual=gradient[k]+(weights[i]+weights[i+1])*direction[k];
    if(i)residual-=weights[i]*direction[k-3];
    if(i+1<n)residual-=weights[i+1]*direction[k+3];
    if(!fixed[k])stats.free_equation_max_error=std::max(stats.free_equation_max_error,std::abs(residual));
    else {
      const double signed_multiplier=lower[k]?residual:-residual;
      stats.inward_multiplier_violations+=signed_multiplier<0;
      stats.most_negative_signed_multiplier=std::min(stats.most_negative_signed_multiplier,signed_multiplier);
    }
  }
  stats.slope=dot(gradient,direction);
  if(record)*record=stats;
  return direction;
}
