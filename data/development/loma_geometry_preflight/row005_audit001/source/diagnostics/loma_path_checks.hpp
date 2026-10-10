#pragma once

// Independent exact straight-segment action for a continuous x-only linear
// profile. Long-double arithmetic resolves small directional action changes.
long double loma_exact_action(const Grid &g, const std::vector<P> &path) {
  auto velocity = [&](long double x) {
    size_t i=0;
    while(i+2<g.x.size() && x>=g.x[i+1])++i;
    const long double a=g.v[g.id(i,0,0)], b=g.v[g.id(i+1,0,0)];
    return a+(b-a)*(x-g.x[i])/(g.x[i+1]-g.x[i]);
  };
  long double total=0;
  for(size_t n=1;n<path.size();++n) {
    const P &a=path[n-1], &b=path[n];
    long double d[3], square=0;
    for(int axis=0;axis<3;++axis) {d[axis]=(long double)b[axis]-a[axis];square+=d[axis]*d[axis];}
    const long double length=std::sqrt(square);
    std::vector<long double> cuts{0,1};
    if(d[0]!=0)for(double x:g.x) {
      long double t=((long double)x-a[0])/d[0];
      if(t>0 && t<1)cuts.push_back(t);
    }
    std::sort(cuts.begin(),cuts.end());
    for(size_t j=1;j<cuts.size();++j) {
      const long double va=velocity(a[0]+d[0]*cuts[j-1]);
      const long double vb=velocity(a[0]+d[0]*cuts[j]);
      const long double dv=vb-va, span=cuts[j]-cuts[j-1];
      total+=length*span*(dv==0 ? 1/va : std::log1p(dv/va)/dv);
    }
  }
  return total;
}

void loma_path_checks(std::ostream &out, const Grid &g, const Ray &ray,
                      const Vec &gradient, const std::string &run,
                      const std::string &diagnostic_row) {
  for(size_t k=0;k<g.z.size();++k)for(size_t j=0;j<g.y.size();++j)for(size_t i=0;i<g.x.size();++i)
    if(g.v[g.id(i,j,k)]!=g.v[g.id(i,0,0)])throw std::runtime_error("Exact-action check requires x-only velocity");
  Vec kinks;
  for(size_t i=1;i+1<g.x.size();++i) {
    double left=(g.v[g.id(i,0,0)]-g.v[g.id(i-1,0,0)])/(g.x[i]-g.x[i-1]);
    double right=(g.v[g.id(i+1,0,0)]-g.v[g.id(i,0,0)])/(g.x[i+1]-g.x[i]);
    if(left!=right)kinks.push_back(g.x[i]);
  }
  size_t crossings=0,aligned=0,near_aligned=0;
  for(size_t i=1;i<ray.path.size();++i)for(double x:kinks) {
    const double a=ray.path[i-1][0]-x,b=ray.path[i][0]-x;
    crossings+=(a<0 && b>0)||(a>0 && b<0);
    aligned+=a==0 && b==0;
    near_aligned+=std::abs(a)<=1e-8 && std::abs(b)<=1e-8;
  }
  Vec projected=gradient;
  for(double &value:projected)value=-value;
  project_ray_direction(g,ray.path,projected);
  size_t worst=std::max_element(projected.begin(),projected.end(),[](double a,double b){return std::abs(a)<std::abs(b);})-projected.begin();
  size_t worst_x=0;
  for(size_t i=0;i<projected.size();i+=3)if(std::abs(projected[i])>std::abs(projected[worst_x]))worst_x=i;
  std::vector<size_t> components{worst};
  if(worst_x!=worst)components.push_back(worst_x);
  const long double exact=loma_exact_action(g,ray.path);
  for(size_t component:components) {
    size_t node=component/3+1;int axis=component%3;
    double closest=NAN,distance=INFINITY;
    for(double x:kinks)if(std::abs(ray.path[node][0]-x)<distance) {
      closest=x;distance=std::abs(ray.path[node][0]-x);
    }
    for(double h:{1e-3,1e-4,1e-5,1e-6,1e-7,1e-8,1e-9}) {
      auto plus=ray.path,minus=ray.path;
      plus[node][axis]+=h;minus[node][axis]-=h;
      bool fp=g.contains(plus[node]),fm=g.contains(minus[node]);
      double qp=fp?path_eval(g,plus):NAN,qm=fm?path_eval(g,minus):NAN;
      long double ep=fp?loma_exact_action(g,plus):NAN,em=fm?loma_exact_action(g,minus):NAN;
      out<<run<<','<<diagnostic_row<<','<<node<<','<<axis<<','<<h<<','<<gradient[component]
         <<','<<ray.path[node][0]<<','<<closest<<','<<distance<<','<<ray.path[node-1][0]
         <<','<<ray.path[node+1][0]<<','<<crossings<<','<<aligned<<','<<near_aligned
         <<','<<ray.time<<','<<exact<<','<<(long double)ray.time-exact
         <<','<<(fp?(qp-ray.time)/h:NAN)<<','<<(fm?(ray.time-qm)/h:NAN)
         <<','<<(fp&&fm?(qp-qm)/(2*h):NAN)
         <<','<<(fp?(ep-exact)/h:NAN)<<','<<(fm?(exact-em)/h:NAN)
         <<','<<(fp&&fm?(ep-em)/(2*h):NAN)<<'\n';
    }
  }
}
