// Invented contact controls only. Reuse the frozen observer's finite checks,
// signed-zero JSON, binary64 parsing and unchanged principal-metric solve.
#define main reviewed_metric_main
#include "tangent_metric_step.cpp"
#undef main

void named_values(const char *name,const Vec &v) {
  for(double x:v)finite(x,"Nonfinite observed value");
  std::cout<<'"'<<name<<"\":";array_json(v);
  std::cout<<",\""<<name<<"_hex\":";hex_json(v);
}

int main(int argc,char **argv) {
  try {
    require_step(argc==3,"Use: observe path|solve|edge INPUT");
    require_step(std::numeric_limits<double>::is_iec559 && std::numeric_limits<double>::digits==53 &&
                 std::fegetround()==FE_TONEAREST,"Require nearest IEEE binary64");
    const std::string mode=argv[1];
    require_step(mode=="path" || mode=="solve" || mode=="edge","Unknown observer mode");
    std::ifstream in(argv[2]);require_step(bool(in),"Cannot open invented input");
    const auto nx=count(in),ny=count(in),nz=count(in),n=count(in);
    require_step(nx==3 && ny==2 && nz==2 && n==(mode=="edge"?2u:4u),"Outside invented roster dimensions");
    Grid g;g.x=values(in,nx);g.y=values(in,ny);g.z=values(in,nz);g.v=values(in,nx*ny*nz);
    require_step(g.x==Vec{-1,0,1} && g.y==Vec{-1,4} && g.z==Vec{-1,1},"Outside invented box");
    const double outer=g.v.front();require_step(outer==5 || outer==7,"Outside fast/slow velocity roster");
    for(int k=0;k<2;++k)for(int j=0;j<2;++j)for(int i=0;i<3;++i)
      require_step(g.v[g.id(i,j,k)]==(i==1?6:outer),"Outside declared depth-independent ridge");
    const auto path=points(in,n);
    for(const auto &p:path)require_step(g.contains(p),"Point outside physical box");
    for(std::size_t i=1;i<n;++i)require_step(norm(path[i]-path[i-1])>0,"Zero or underflowed edge");
    std::vector<bool> fixed;
    if(mode=="solve") {
      fixed.resize(3*(n-2));
      for(std::size_t i=0;i<fixed.size();++i) {
        const auto bit=count(in);require_step(bit<=1,"Invalid search-subspace bit");fixed[i]=bit;
        require_step(i%3==0 || fixed[i],"This fixture uses normal-only metric proposals");
      }
    }
    std::string extra;require_step(!(in>>extra),"Unexpected trailing input");
    std::cout<<std::setprecision(17)<<"{\"invented_only\":true,\"mode\":\""<<mode<<"\",";
    named_values("path",flatten(path));std::cout<<',';
    if(mode=="edge") {
      P a{},b{};const double action=segment(g,path[0],path[1],&a,&b);
      named_values("action",Vec{action});std::cout<<',';
      named_values("endpoint_gradient",Vec{a[0],a[1],a[2],b[0],b[1],b[2]});
      // Read-only repetition of the frozen segment's cut-construction algebra;
      // this does not alter or supply the cuts used by segment itself.
      Vec cuts{0,1};const P delta=path[1]-path[0];const Vec *axes[]={&g.x,&g.y,&g.z};
      for(int k=0;k<3;++k)if(std::abs(delta[k])>1e-12)for(double plane:*axes[k]) {
        const double u=(plane-path[0][k])/delta[k];
        if(u>1e-10 && u<1-1e-10)cuts.push_back(u);
      }
      std::sort(cuts.begin(),cuts.end());std::cout<<',';named_values("reconstructed_core_cuts",cuts);
      std::cout<<",\"path_eval_calls\":0,\"segment_calls\":1";
    } else {
      Vec gradient;const double action=path_eval(g,path,&gradient);
      named_values("action",Vec{action});std::cout<<',';named_values("gradient",gradient);
      std::cout<<",\"path_eval_calls\":1,\"segment_calls\":"<<n-1;
      if(mode=="solve") {
        std::cout<<",\"metric\":";solve_record(ray_metric_weights(g,path),gradient,fixed);
      }
    }
    std::cout<<",\"trace_calls\":0,\"field_calls\":0}\n";
    std::cout.flush();require_step(bool(std::cout),"Observer output write failed");
    return 0;
  } catch(const std::exception &error) {std::cerr<<error.what()<<'\n';return 1;}
}
