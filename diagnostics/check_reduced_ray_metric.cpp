// Small independent algebra controls for the diagnostic constrained metric.
#include "reduced_ray_metric.hpp"
#include "control_optimizer.hpp"
#include <random>

Vec dense_solve(std::vector<Vec> a,Vec b) {
  const std::size_t n=b.size();
  for(std::size_t k=0;k<n;++k) {
    std::size_t pivot=k;
    for(std::size_t i=k+1;i<n;++i)if(std::abs(a[i][k])>std::abs(a[pivot][k]))pivot=i;
    std::swap(a[k],a[pivot]);std::swap(b[k],b[pivot]);
    if(!(std::abs(a[k][k])>0))throw std::runtime_error("Singular dense reference");
    for(std::size_t i=k+1;i<n;++i) {
      double ratio=a[i][k]/a[k][k];
      for(std::size_t j=k;j<n;++j)a[i][j]-=ratio*a[k][j];
      b[i]-=ratio*b[k];
    }
  }
  Vec answer(n);
  for(std::size_t i=n;i-->0;) {
    double value=b[i];
    for(std::size_t j=i+1;j<n;++j)value-=a[i][j]*answer[j];
    answer[i]=value/a[i][i];
  }
  return answer;
}

int main() {
  std::cout<<std::setprecision(17)<<"check,case,error,tolerance,passed\n";
  int failures=0,count=0;
  auto check=[&](const std::string &name,int index,double error,double tolerance) {
    bool pass=std::isfinite(error)&&error<=tolerance;
    failures+=!pass;++count;
    std::cout<<name<<','<<index<<','<<error<<','<<tolerance<<','<<pass<<'\n';
  };
  std::mt19937 generator(20261009);
  std::uniform_real_distribution<double> positive(.2,2.),signed_value(-1.,1.);
  // Every mask over six coordinates exercises all three axes, adjacent free
  // coordinates, singleton blocks, and the all-fixed case. Dense elimination
  // is independent of the production/diagnostic Thomas implementation.
  for(int repetition=0;repetition<4;++repetition)for(int mask=0;mask<64;++mask) {
    const std::size_t n=2;
    Vec weights(n+1),gradient(3*n);
    for(auto &v:weights)v=positive(generator);
    for(auto &v:gradient)v=signed_value(generator);
    std::vector<bool> fixed(3*n);
    std::vector<std::size_t> free;
    for(std::size_t k=0;k<gradient.size();++k) {fixed[k]=mask&(1<<k);if(!fixed[k])free.push_back(k);}
    std::vector<Vec> matrix(free.size(),Vec(free.size()));Vec rhs(free.size());
    for(std::size_t row=0;row<free.size();++row) {
      const auto k=free[row];const auto i=k/3;rhs[row]=-gradient[k];
      for(std::size_t col=0;col<free.size();++col) {
        const auto m=free[col];
        if(m==k)matrix[row][col]=weights[i]+weights[i+1];
        else if(m==k+3)matrix[row][col]=-weights[i+1];
        else if(k==m+3)matrix[row][col]=-weights[i];
      }
    }
    Vec expected(gradient.size()),actual=solve_free_ray_metric(weights,gradient,fixed);
    if(!free.empty()) {
      const Vec solved=dense_solve(matrix,rhs);
      for(std::size_t i=0;i<free.size();++i)expected[free[i]]=solved[i];
    }
    double error=0;for(std::size_t k=0;k<actual.size();++k)error=std::max(error,std::abs(actual[k]-expected[k]));
    check("dense_principal_matrix",64*repetition+mask,error,2e-13);
  }
  for(int n:{1,2,3,7,19,61}) {
    Vec weights(n+1),gradient(3*n);
    for(auto &v:weights)v=positive(generator);
    for(auto &v:gradient)v=signed_value(generator);
    auto direct=inverse_ray_metric(weights,gradient);
    for(auto &v:direct)v=-v;
    auto reduced=solve_free_ray_metric(weights,gradient,std::vector<bool>(gradient.size(),false));
    double error=0;for(std::size_t k=0;k<direct.size();++k)error=std::max(error,std::abs(direct[k]-reduced[k]));
    check("no_bound_inverse",n,error,2e-11);
  }
  Grid g;g.x={-2,2};g.y={-2,2};g.z={-2,2};g.v.assign(g.size(),4);
  for(int test=0;test<96;++test) {
    std::vector<P> path{P{-1.7,-1.5,-1.3},P{-.8,-.7,-.6},P{-.1,.2,.3},P{.6,.7,.8},P{1.5,1.4,1.3}};
    const int axis=test%3;
    path[1+test%3][axis]=(test%2)?2:-2;
    if(test%4==0)path[2][(axis+1)%3]=-2;
    Vec gradient(9);for(auto &v:gradient)v=signed_value(generator);
    ReducedRayMetricStats stats;
    auto direction=reduced_ray_direction(g,path,gradient,&stats);
    double violation=0;
    for(std::size_t i=0;i<3;++i)for(int a=0;a<3;++a) {
      if(path[i+1][a]==-2)violation=std::max(violation,-direction[3*i+a]);
      if(path[i+1][a]==2)violation=std::max(violation,direction[3*i+a]);
    }
    check("feasible_cone",test,violation,0);
    check("negative_slope",test,stats.slope<0?0:1,0);
    check("free_equation",test,stats.free_equation_max_error,2e-13);
  }
  // The minimal method can leave an initially KKT-active coordinate with an
  // inward (wrong-sign) quadratic multiplier after moving its neighbor.
  Grid release_grid;release_grid.x={-1,1};release_grid.y={-1,1};release_grid.z={0,2};release_grid.v.assign(release_grid.size(),4);
  std::vector<P> release_path{P{-.75,0,0},P{-.25,0,0},P{.25,0,.1},P{.75,0,.2}};
  Vec release_gradient{0,0,1,0,0,-4};ReducedRayMetricStats release_stats;
  auto release_direction=reduced_ray_direction(release_grid,release_path,release_gradient,&release_stats);
  check("no_release_limitation_recorded",0,release_stats.inward_multiplier_violations>0?0:1,0);
  check("no_release_still_descent",0,dot(release_gradient,release_direction)<0?0:1,0);
  // Smooth rays without active bounds: the fallback-only variant should be
  // bitwise unchanged. A pure metric-descent variant instead checks the exact
  // affine-velocity travel time and endpoint derivative at existing tolerances.
  Grid affine;affine.x={-20,20};affine.y={-20,20};affine.z={-20,20};affine.v.resize(affine.size());
  for(int k=0;k<2;++k)for(int j=0;j<2;++j)for(int i=0;i<2;++i)
    affine.v[affine.id(i,j,k)]=6+.05*affine.z[k];
  int index=0;
  for(double spacing:{.5,.25})for(bool reverse:{false,true}) {
    P a{-5,-3,3},b{6,4,5};if(reverse)std::swap(a,b);
    const Ray original=trace(affine,a,b,spacing,1000),variant=control_trace(affine,a,b,spacing,1000);
#ifdef AUDIT_REDUCED_ALL
    const double va=affine.sample(a).v,vb=affine.sample(b).v,G=.05,R=norm(b-a);
    const double u=G*R/(2*std::sqrt(va*vb));
    const double exact=2/G*std::asinh(u);
    const P derivative=((a-b)*(1/(R*R))-P{0,0,G}*(1/(2*va)))*
      (R/(std::sqrt(va*vb)*std::sqrt(1+u*u)));
    check("no_bound_affine_exact_time",index,std::abs(variant.time-exact),2.5e-5);
    check("no_bound_affine_exact_source",index,norm(variant.source-derivative),3e-6);
#else
    bool same=original.path==variant.path&&original.time==variant.time&&original.gradient==variant.gradient&&
      original.source==variant.source&&original.iterations==variant.iterations&&original.converged==variant.converged;
    check("no_bound_affine_unchanged",index,same?0:1,0);
#endif
    check("no_bound_affine_converged",index,original.converged&&variant.converged?0:1,0);
    ++index;
  }
  std::cerr<<count<<" checks, "<<failures<<" failures\n";
  return failures?1:0;
}
