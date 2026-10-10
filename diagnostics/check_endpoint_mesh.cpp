// Isolated explicit-mesh experiment. The generated optimizer changes only
// initialization; action, update, stopping, box and merge equations are frozen.
#include "../src/core.hpp"
#include "../src/csv.hpp"
#include "explicit_mesh_trace.hpp"

void require(bool ok, const std::string &message) {
  if (!ok) throw std::runtime_error(message);
}
std::ofstream output(const std::string &name) {
  std::ofstream f(name);
  require(bool(f), "Cannot open " + name);
  f << std::setprecision(17);
  return f;
}
Vec values(const std::string &s) {
  Vec out;
  std::istringstream stream(s);
  std::string value;
  while (std::getline(stream,value,',')) out.push_back(csv_double(value));
  return out;
}
Grid input_grid(const std::string &file) {
  const auto table=csv_table(file,{"x","y","z","v"});
  require(table.header.size()==4 && !table.rows.empty(),"Expected numeric grid");
  Grid g;
  Vec *axes[]={&g.x,&g.y,&g.z};
  for(int k=0;k<3;++k) {
    for(const auto &row:table.rows) axes[k]->push_back(csv_double(row[k]));
    std::sort(axes[k]->begin(),axes[k]->end());
    axes[k]->erase(std::unique(axes[k]->begin(),axes[k]->end()),axes[k]->end());
    require(axes[k]->size()>=2,"Degenerate grid axis");
  }
  require(table.rows.size()==g.x.size()*g.y.size()*g.z.size(),"Incomplete grid");
  g.v.assign(table.rows.size(),NAN);
  for(const auto &row:table.rows) {
    int index[3];
    for(int k=0;k<3;++k)
      index[k]=std::lower_bound(axes[k]->begin(),axes[k]->end(),csv_double(row[k]))-axes[k]->begin();
    const int id=g.id(index[0],index[1],index[2]);
    require(!std::isfinite(g.v[id]),"Duplicate grid node");
    g.v[id]=csv_double(row[3]);
    require(g.v[id]>0,"Nonpositive velocity");
  }
  return g;
}
Ray evaluate(const Grid &g,const std::vector<P> &p) {
  require(p.size()>=2,"Short path");
  Ray r;
  r.path=p;
  Vec gradient;
  r.time=path_eval(g,p,&gradient);
  r.gradient=projected_ray_gradient(g,p,gradient);
  r.raw_gradient=norm(gradient);
  r.dv.assign(g.size(),0);r.length.assign(g.size(),0);
  for(size_t i=1;i<p.size();++i) {
    P a{},b{};
    segment(g,p[i-1],p[i],&a,&b,&r.dv,&r.length);
    if(i==1)r.source=a;
  }
  return r;
}
bool same(const Ray &a,const Ray &b) {
  return a.path==b.path && a.time==b.time && a.source==b.source &&
    a.dv==b.dv && a.length==b.length && a.iterations==b.iterations &&
    a.merged_nodes==b.merged_nodes && a.gradient==b.gradient &&
    a.raw_gradient==b.raw_gradient && a.converged==b.converged;
}

int main(int argc,char **argv) {
  require(argc==9,"Usage: GRID PATH RUN OUTPUT BUDGET EPSILONS LEVELS PARITY");
  const Grid g=input_grid(argv[1]);
  const auto table=csv_table(argv[2]);
  std::map<std::string,size_t> c;
  for(size_t k=0;k<table.header.size();++k)c[table.header[k]]=k;
  std::vector<P> original;
  std::string observation,run=argv[3],out=argv[4];
  const int budget=csv_int(argv[5]);
  require(budget>=0,"Negative budget");
  const Vec epsilons=values(argv[6]),levels=values(argv[7]);
  require(!epsilons.empty()&&epsilons.front()==0,"Require baseline epsilon zero");
  for(const auto &row:table.rows)if(row[c.at("run_id")]==run) {
    require(csv_int(row[c.at("node")])==int(original.size()),"Unordered native nodes");
    if(!original.empty())require(observation==row[c.at("observation_index")],"Mixed identity");
    observation=row[c.at("observation_index")];
    original.push_back({csv_double(row[c.at("x")]),csv_double(row[c.at("y")]),csv_double(row[c.at("z")])});
  }
  require(original.size()>=3,"Require a polygon with movable knots");
  for(const auto &p:original)require(g.contains(p),"Original node outside box");
  require(original.front()[2]==g.z.back(),"Expected source on bottom");
  for(double epsilon:epsilons)
    require(epsilon>=0 && original.front()[2]-epsilon>=g.z.front(),"Invalid inward displacement");

  auto scalar=output(out+"/evaluations.csv"), paths=output(out+"/paths.csv");
  scalar<<"run_id,observation_index,subsegments,epsilon_requested_km,epsilon_actual_km,family,"
    "input_nodes,path_nodes,time_s,source_dx,source_dy,source_dz,tied_source_dx,tied_source_dy,tied_source_dz,"
    "leading_length_km,iterations,merged_nodes,projected_gradient,raw_gradient,converged,error\n";
  paths<<"run_id,observation_index,subsegments,epsilon_requested_km,family,node,x,y,z\n";
  auto write=[&](int level,double epsilon,const char *family,size_t input_nodes,
                 const Ray &r,const P *tied,const std::string &error="") {
    scalar<<run<<','<<observation<<','<<level<<','<<epsilon<<','
      <<original.front()[2]-r.path.front()[2]<<','<<family<<','<<input_nodes<<','<<r.path.size();
    if(error.empty()) {
      scalar<<','<<r.time;
      for(double x:r.source)scalar<<','<<x;
      for(int k=0;k<3;++k){scalar<<',';if(tied)scalar<<(*tied)[k];}
      scalar<<','<<norm(r.path[1]-r.path[0])<<','<<r.iterations<<','<<r.merged_nodes
        <<','<<r.gradient<<','<<r.raw_gradient<<',';
      if(std::string(family)=="optimized")scalar<<r.converged;
    } else scalar<<",,,,,,,,,,,,,";
    scalar<<','<<csv_quote(error)<<'\n';
    for(size_t n=0;n<r.path.size();++n) {
      paths<<run<<','<<observation<<','<<level<<','<<epsilon<<','<<family<<','<<n;
      for(double x:r.path[n])paths<<','<<x;
      paths<<'\n';
    }
    scalar.flush();paths.flush();
    require(bool(scalar)&&bool(paths),"Output write failed");
  };
  // Same initial mesh as ordinary unseeded trace, including identical arithmetic.
  // This exercises optimizer iterations, not just the zero-budget action.
  auto parity=output(out+"/parity.csv");
  parity<<"kind,passed\n";
  if(csv_int(argv[8])) {
    const P a=original.front(),b=original.back();
    const double spacing=.2;
    const int n=std::max(2,int(std::ceil(norm(b-a)/spacing)));
    std::vector<P> initial(n+1);
    for(int i=1;i<n;++i)initial[i]=a+(b-a)*(double(i)/n);
    initial.front()=a;initial.back()=b;
    const Ray control=trace(g,a,b,spacing,20,true);
    const Ray retained=trace_mesh(g,a,b,spacing,20,true,&initial);
    parity<<"ordinary_trace_equal_initial_mesh,"<<same(control,retained)<<'\n';
    require(same(control,retained),"Explicit initialization changed optimizer arithmetic");
  }
  for(double number:levels) {
    const int n=int(number);require(n>0 && n==number,"Invalid subdivision count");
    std::vector<P> base{original[0]};
    for(int j=1;j<n;++j)base.push_back(original[0]+(original[1]-original[0])*(double(j)/n));
    base.insert(base.end(),original.begin()+1,original.end());
    const Ray zero=trace_mesh(g,base.front(),base.back(),1,0,true,&base);
    const Ray direct=evaluate(g,base);
    const bool retained=zero.path==base && zero.time==direct.time &&
      zero.source==direct.source && zero.dv==direct.dv && zero.length==direct.length &&
      zero.merged_nodes==0;
    parity<<"zero_budget_mesh_retention_"<<n<<','<<retained<<'\n';
    require(retained,"Explicit zero-budget initialization changed mesh/action");
    std::vector<P> optimized_base;
    for(double epsilon:epsilons) {
      std::vector<P> fixed=base,tied=base;
      fixed[0][2]-=epsilon;
      tied[0]=fixed[0];
      for(int j=1;j<n;++j)tied[j][2]-=epsilon*(1-double(j)/n);
      const Ray fixed_result=evaluate(g,fixed),tied_result=evaluate(g,tied);
      Vec gradient;path_eval(g,tied,&gradient);
      P tied_source=tied_result.source;
      for(int j=1;j<n;++j)for(int k=0;k<3;++k)
        tied_source[k]+=(1-double(j)/n)*gradient[3*(j-1)+k];
      write(n,epsilon,"fixed",base.size(),fixed_result,nullptr);
      write(n,epsilon,"tied",base.size(),tied_result,&tied_source);
      std::vector<P> seed=epsilon==0?base:optimized_base;
      if(seed.empty()) {
        Ray failed;failed.path=fixed;
        write(n,epsilon,"optimized",base.size(),failed,nullptr,"No optimized baseline after an earlier exception");
        continue;
      }
      seed.front()=fixed.front();
      try {
        const Ray result=trace_mesh(g,seed.front(),seed.back(),1,budget,true,&seed);
        if(epsilon==0)optimized_base=result.path;
        write(n,epsilon,"optimized",seed.size(),result,nullptr);
      } catch(const std::exception &error) {
        Ray failed;failed.path=seed;
        write(n,epsilon,"optimized",seed.size(),failed,nullptr,error.what());
      }
    }
  }
}
