#include "source/src/core.hpp"
#include "source/diagnostics/loma_path_checks.hpp"
int main() {
  Grid g;g.x={-2,0,1,3};g.y={-2,2};g.z={-2,2};g.v.resize(g.size());
  for(int k=0;k<2;++k)for(int j=0;j<2;++j)for(int i=0;i<4;++i)g.v[g.id(i,j,k)]=i<2?6:4;
  std::cout<<std::setprecision(21)<<"case,action,closed_form,absolute_error,passed\n";
  bool passed=true;
  auto check=[&](const char *name,std::vector<P> path,long double exact) {
    long double value=loma_exact_action(g,path),error=std::abs(value-exact);
    bool ok=error<1e-15L;passed=passed&&ok;
    std::cout<<name<<','<<value<<','<<exact<<','<<error<<','<<ok<<'\n';
  };
  check("constant",{{-1.5,-1,0},{-.5,1,0}},std::sqrt(5.L)/6);
  check("crossing",{{-1,-1,0},{2,1,0}},std::sqrt(13.L)/3*(1.L/6+std::log(1.5L)/2+1.L/4));
  check("crossing_reverse",{{2,1,0},{-1,-1,0}},std::sqrt(13.L)/3*(1.L/6+std::log(1.5L)/2+1.L/4));
  check("interface",{{0,-1,0},{0,0,0},{0,1,0}},1.L/3);
  double hd=1e-4;long double h=hd;
  check("interface_left",{{0,-1,0},{-hd,0,0},{0,1,0}},std::sqrt(1+h*h)/3);
  check("interface_right",{{0,-1,0},{hd,0,0},{0,1,0}},std::sqrt(1+h*h)*std::log1p(h/(3-h))/h);
  return !passed;
}
