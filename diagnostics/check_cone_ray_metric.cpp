// Invented quadratic fixtures; independent exhaustive active-face references.
#include "cone_ray_metric.hpp"
#include <random>

Vec dense_cone_reference(const Vec &weights,const Vec &gradient,const std::vector<int> &sign) {
  const std::size_t size=gradient.size();
  std::vector<std::size_t> bounded;
  for(std::size_t i=0;i<size;++i)if(sign[i])bounded.push_back(i);
  if(bounded.size()>15)throw std::runtime_error("Exhaustive fixture is intentionally small");
  Vec best;
  double objective=INFINITY;
  for(std::size_t mask=0;mask<(std::size_t(1)<<bounded.size());++mask) {
    std::vector<bool> fixed(size,false);
    for(std::size_t i=0;i<bounded.size();++i)if(mask&(std::size_t(1)<<i))fixed[bounded[i]]=true;
    std::vector<std::size_t> free;
    for(std::size_t i=0;i<size;++i)if(!fixed[i])free.push_back(i);
    std::vector<Vec> a(free.size(),Vec(free.size()));Vec b(free.size());
    for(std::size_t row=0;row<free.size();++row) {
      auto k=free[row];auto node=k/3;b[row]=-gradient[k];
      for(std::size_t col=0;col<free.size();++col) {
        auto m=free[col];
        if(m==k)a[row][col]=weights[node]+weights[node+1];
        else if(m==k+3)a[row][col]=-weights[node+1];
        else if(k==m+3)a[row][col]=-weights[node];
      }
    }
    // General dense elimination does not use the tridiagonal implementation.
    for(std::size_t k=0;k<free.size();++k) {
      std::size_t pivot=k;
      for(std::size_t i=k+1;i<free.size();++i)if(std::abs(a[i][k])>std::abs(a[pivot][k]))pivot=i;
      std::swap(a[k],a[pivot]);std::swap(b[k],b[pivot]);
      for(std::size_t i=k+1;i<free.size();++i) {
        double factor=a[i][k]/a[k][k];
        for(std::size_t j=k;j<free.size();++j)a[i][j]-=factor*a[k][j];
        b[i]-=factor*b[k];
      }
    }
    Vec candidate(size);
    for(std::size_t i=free.size();i-->0;) {
      double value=b[i];
      for(std::size_t j=i+1;j<free.size();++j)value-=a[i][j]*candidate[free[j]];
      candidate[free[i]]=value/a[i][i];
    }
    bool feasible=true;
    for(std::size_t k=0;k<size;++k)if(sign[k]&&sign[k]*candidate[k]<-1e-12)feasible=false;
    if(!feasible)continue;
    // Evaluate the quadratic directly as incident edge energies.
    double candidate_objective=dot(gradient,candidate);
    for(int axis=0;axis<3;++axis)for(std::size_t edge=0;edge<weights.size();++edge) {
      double left=edge?candidate[3*(edge-1)+axis]:0;
      double right=edge+1<weights.size()?candidate[3*edge+axis]:0;
      candidate_objective+=.5*weights[edge]*(right-left)*(right-left);
    }
    if(candidate_objective<objective) {objective=candidate_objective;best=std::move(candidate);}
  }
  if(best.empty())throw std::runtime_error("Exhaustive fixture found no feasible face");
  return best;
}

int main() {
  std::cout<<std::setprecision(17)<<"check,case,error,tolerance,passed\n";
  int checks=0,failures=0,maximum_solves=0,total_blocks=0,total_releases=0;
  auto check=[&](const char *name,int index,double error,double tolerance) {
    bool ok=std::isfinite(error)&&error<=tolerance;
    ++checks;failures+=!ok;
    std::cout<<name<<','<<index<<','<<error<<','<<tolerance<<','<<ok<<'\n';
  };
  auto exercise=[&](int index,const Vec &weights,const Vec &gradient,const std::vector<int> &sign,bool exhaustive) {
    ConeRayMetricStats stats;
    const Vec result=solve_cone_ray_metric(weights,gradient,sign,stats);
    maximum_solves=std::max(maximum_solves,stats.solves);total_blocks+=stats.blocks;total_releases+=stats.releases;
    check("solver_success",index,stats.success?0:1,0);
    check("free_backward_error_certificate",index,stats.free_equation_relative_backward_error,
          64*std::numeric_limits<double>::epsilon());
    if(!stats.success)std::cerr<<index<<": "<<stats.message<<'\n';
    const Vec product=ray_metric_product(weights,result);
    double scale=0,primal=0,dual=0,free_residual=0,complementarity=0;
    for(std::size_t k=0;k<gradient.size();++k) {
      scale=std::max(scale,std::abs(gradient[k])+std::abs(product[k]));
      if(sign[k]) {
        primal=std::max(primal,-sign[k]*result[k]);
        dual=std::max(dual,-sign[k]*(product[k]+gradient[k]));
        complementarity=std::max(complementarity,std::abs(result[k]*(product[k]+gradient[k])));
      } else free_residual=std::max(free_residual,std::abs(product[k]+gradient[k]));
    }
    const double denom=scale>0?scale:1;
    check("primal_feasibility",index,primal,0);
    check("dual_relative_residual",index,dual/denom,1e-12);
    check("unbounded_relative_residual",index,free_residual/denom,1e-12);
    check("complementarity",index,complementarity/(1+norm(result)*denom),1e-12);
    check("nonpositive_slope",index,std::max(0.,dot(gradient,result)),0);
    check("quadratic_descent_identity",index,std::abs(dot(gradient,result)+dot(result,product))/(1+norm(result)*denom),2e-12);
    if(exhaustive) {
      const Vec reference=dense_cone_reference(weights,gradient,sign);
      double error=0;for(std::size_t k=0;k<result.size();++k)error=std::max(error,std::abs(result[k]-reference[k]));
      check("exhaustive_active_faces",index,error/(1+norm(reference)),2e-11);
    }
  };
  std::mt19937 generator(20261009);
  std::uniform_real_distribution<double> value(-1.,1.),exponent(-2.,2.);
  // All 3^6 combinations of free/lower/upper bounds, including exact zero and
  // sign-symmetric gradients, for two internal nodes and all three axes.
  for(int pattern=0;pattern<729;++pattern) {
    std::vector<int> sign(6);int code=pattern;
    for(int &s:sign) {s=code%3-1;code/=3;}
    Vec weights(3),gradient(6);
    for(auto &v:weights)v=std::pow(10.,exponent(generator));
    for(auto &v:gradient)v=pattern%23==0?0:value(generator);
    exercise(pattern,weights,gradient,sign,true);
  }
  for(int test=0;test<200;++test) {
    Vec weights(4),gradient(9);std::vector<int> sign(9);
    for(auto &v:weights)v=std::pow(10.,exponent(generator));
    for(std::size_t k=0;k<gradient.size();++k) {gradient[k]=value(generator);sign[k]=int(generator()%3)-1;}
    exercise(729+test,weights,gradient,sign,true);
  }
  for(int test=0;test<80;++test) {
    int nodes=4+generator()%64;
    Vec weights(nodes+1),gradient(3*nodes);std::vector<int> sign(3*nodes);
    for(auto &v:weights)v=std::pow(10.,exponent(generator));
    for(std::size_t k=0;k<gradient.size();++k) {gradient[k]=value(generator);sign[k]=int(generator()%3)-1;}
    exercise(929+test,weights,gradient,sign,false);
  }
  // Previously frozen inward multiplier: the full QP must release it.
  ConeRayMetricStats release_stats;
  const Vec released=solve_cone_ray_metric(Vec{1,1,1},Vec{0,0,1,0,0,-4},std::vector<int>{0,0,1,0,0,0},release_stats);
  check("release_counterexample",0,std::abs(released[2]-2./3)+std::abs(released[5]-7./3),1e-13);
  check("release_performed",0,release_stats.releases>0?0:1,0);
  ConeRayMetricStats guard;
  solve_cone_ray_metric(Vec{1,1},Vec{-1,0,0},std::vector<int>{1,0,0},guard,1);
  check("guard_reports_failure",0,!guard.success&&guard.message.find("guard")!=std::string::npos?0:1,0);
  ConeRayMetricStats overflow;
  solve_cone_ray_metric(Vec{1e308,1e308},Vec{1,0,0},std::vector<int>{0,0,0},overflow);
  check("coefficient_overflow_fails_closed",0,!overflow.success&&overflow.message.find("Nonfinite")!=std::string::npos?0:1,0);
  solve_cone_ray_metric(Vec{1e-308,1e-308},Vec{1e308,0,0},std::vector<int>{0,0,0},overflow);
  check("direction_overflow_fails_closed",0,!overflow.success&&overflow.message.find("Nonfinite")!=std::string::npos?0:1,0);
  solve_cone_ray_metric(Vec{1,1e308,1},Vec{1,0,0,1,0,0},std::vector<int>(6),overflow);
  check("lost_positive_pivot_fails_closed",0,!overflow.success&&overflow.message.find("pivot")!=std::string::npos?0:1,0);
  std::cerr<<checks<<" checks, "<<failures<<" failures; max solves "<<maximum_solves
           <<", total blocks "<<total_blocks<<", releases "<<total_releases<<'\n';
  return failures?1:0;
}
