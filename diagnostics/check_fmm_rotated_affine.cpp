// Invented 3-D affine-velocity fields; no production solver or real observations.
#include "first_arrival_fmm.hpp"
#include "seeded_bending.hpp"
#include "production_entry_checks.hpp"
#include <chrono>

ProductionEntryChecks entry_checks;

constexpr double velocity0 = 6;
using Clock = std::chrono::steady_clock;
double seconds(Clock::time_point start) {
  return std::chrono::duration<double>(Clock::now() - start).count();
}
struct Exact {
  double time;
  P source;
};
Exact exact(P a, P b, P gradient) {
  double slope = norm(gradient), length = norm(b-a);
  double va = velocity0 + dot(gradient,a), vb = velocity0 + dot(gradient,b);
  if (!(slope > 0 && length > 0 && va > 0 && vb > 0))
    throw std::runtime_error("Invalid affine reference geometry");
  double u = slope*length/(2*std::sqrt(va*vb));
  double factor = length/(std::sqrt(va*vb)*std::sqrt(1+u*u));
  return {2*std::asinh(u)/slope,
          ((a-b)*(1/(length*length))-gradient*(1/(2*va)))*factor};
}
struct Arc {
  P a, b, vertical, horizontal, minimum, maximum;
  double height, center, radius, first_angle, last_angle, integrated_time;
  P point(double angle) const {
    return a + horizontal*(center+radius*std::cos(angle)) +
           vertical*(radius*std::sin(angle)-height);
  }
};
Arc exact_arc(P a, P b, P gradient) {
  Arc arc;
  arc.a=a; arc.b=b;
  double slope=norm(gradient);
  arc.vertical=gradient*(1/slope);
  P transverse=b-a-arc.vertical*dot(b-a,arc.vertical);
  double distance=norm(transverse);
  if (!(distance>0)) throw std::runtime_error("Fixture requires an oblique endpoint direction");
  arc.horizontal=transverse*(1/distance);
  arc.height=(velocity0+dot(gradient,a))/slope;
  double other_height=(velocity0+dot(gradient,b))/slope;
  arc.center=(distance*distance+other_height*other_height-arc.height*arc.height)/(2*distance);
  arc.radius=std::hypot(arc.center,arc.height);
  arc.first_angle=std::atan2(arc.height,-arc.center);
  arc.last_angle=std::atan2(other_height,distance-arc.center);
  arc.integrated_time=std::abs(std::log(std::tan(arc.first_angle/2)/
                                       std::tan(arc.last_angle/2)))/slope;
  arc.minimum=arc.maximum=a;
  auto include=[&](P p) {
    for(int axis=0;axis<3;++axis) {
      arc.minimum[axis]=std::min(arc.minimum[axis],p[axis]);
      arc.maximum[axis]=std::max(arc.maximum[axis],p[axis]);
    }
  };
  include(b);
  double low=std::min(arc.first_angle,arc.last_angle);
  double high=std::max(arc.first_angle,arc.last_angle), pi=std::acos(-1.);
  for(int axis=0;axis<3;++axis) {
    double angle=std::atan2(arc.vertical[axis],arc.horizontal[axis]);
    for(int turn=-2;turn<=2;++turn) {
      double critical=angle+turn*pi;
      if(critical>=low && critical<=high) include(arc.point(critical));
    }
  }
  return arc;
}
Grid model(P gradient) {
  Grid g;
  g.x=g.y=g.z={-15,0,15};
  g.v.resize(g.size());
  for(int k=0;k<3;++k) for(int j=0;j<3;++j) for(int i=0;i<3;++i)
    g.v[g.id(i,j,k)]=velocity0+dot(gradient,P{g.x[i],g.y[j],g.z[k]});
  if(*std::min_element(g.v.begin(),g.v.end())<=0)
    throw std::runtime_error("Affine velocity is not positive throughout the box");
  return g;
}
P transform(P p,int mode) {
  if(mode==1) return {-p[0],p[1],p[2]};
  if(mode==2) return {p[2],p[0],p[1]};
  return p;
}
struct Comparison {
  first_arrival::Candidate seed;
  Ray direct, bent, best;
  bool fmm_selected=false;
};
Comparison compare(const Grid &g,const first_arrival::Field &field,P a,P b,double spacing) {
  Comparison c;
  c.direct=trace(g,a,b,spacing,1000);
  c.best=c.direct;
  c.seed=field.candidate(a);
  if(c.seed.success) {
    c.bent=bend_seed(g,c.seed.path,spacing,1000);
    if(c.bent.time<c.best.time) { c.best=c.bent; c.fmm_selected=true; }
  }
  entry_checks.compare(g,field,a,b,spacing,c.seed,c.direct,c.bent,c.best,c.fmm_selected);
  return c;
}
int main(int argc,char **argv) {
  if((argc!=3 && argc!=4) || (argc==4 && std::string(argv[3])!="--production-entry"))
    throw std::runtime_error("Usage: check_fmm_rotated_affine OUTPUT_DIR baseline|field_refine|path_refine [--production-entry]");
  std::string out=argv[1], level=argv[2];
  if(argc==4) entry_checks.open(out+"/entry_parity.csv");
  if(level!="baseline" && level!="field_refine" && level!="path_refine")
    throw std::runtime_error("Unknown refinement level");
  double aux=level=="field_refine"?.25:.5;
  double spacing=level=="path_refine"?.125:.25;
  std::ofstream rows(out+"/results.csv"), checks(out+"/checks.csv"), references(out+"/references.csv"), paths(out+"/paths.csv");
  if(!rows || !checks || !references || !paths) throw std::runtime_error("Cannot open affine audit files");
  for(auto f:{&rows,&checks,&references,&paths}) *f<<std::setprecision(17);
  checks<<"case,direction,test,value,tolerance,passed\n";
  auto check=[&](const std::string &name,const std::string &direction,const std::string &test,double value,double tolerance) {
    checks<<name<<','<<direction<<','<<test<<','<<value<<','<<tolerance<<','
          <<(std::isfinite(value)&&value<=tolerance)<<std::endl;
  };
  references<<"case,velocity0_km_per_s,gradient_x,gradient_y,gradient_z,source_x,source_y,source_z,receiver_x,receiver_y,receiver_z,minimum_box_velocity,maximum_box_velocity,reference_time_s,circular_arc_integral_s,arc_polyline_action_s,arc_min_x,arc_min_y,arc_min_z,arc_max_x,arc_max_y,arc_max_z,arc_boundary_margin_km,exact_source_dx,exact_source_dy,exact_source_dz,exact_formula_finite_difference_error_s_per_km\n";
  rows<<"case,direction,level,auxiliary_spacing_km,path_spacing_km,field_nodes,seed_nodes,field_build_seconds,ray_seconds,extracted,extraction_message,field_time_s,seed_action_s,direct_time_s,direct_converged,direct_gradient,fmm_time_s,fmm_converged,fmm_gradient,fmm_iterations,fmm_source_dx,fmm_source_dy,fmm_source_dz,fmm_time_error_s,fmm_source_error_s_per_km,selected,best_time_s,best_converged,best_gradient,reference_time_s,reference_source_dx,reference_source_dy,reference_source_dz,best_time_error_s,best_source_error_s_per_km,outside_nodes,endpoint_error_km,second_order_direction_evaluations,second_order_ineligible,causal_fallback_updates\n";
  paths<<"case,direction,kind,node,x,y,z\n";
  auto save_path=[&](const std::string &name,const std::string &direction,const std::string &kind,const std::vector<P> &path) {
    for(std::size_t i=0;i<path.size();++i)
      paths<<name<<','<<direction<<','<<kind<<','<<i<<','<<path[i][0]<<','<<path[i][1]<<','<<path[i][2]<<'\n';
  };
  const char *names[]={"oblique_base","reflected_x","cyclic_permutation"};
  for(int mode=0;mode<3;++mode) {
    std::string name=names[mode];
    P gradient=transform(P{1,2,3}*(.12/std::sqrt(14.)),mode);
    P a=transform(P{-10.13,-5.24,7.35},mode),b=transform(P{11.27,7.19,-7.41},mode);
    Grid g=model(gradient);
    Exact reference=exact(a,b,gradient);
    Arc arc=exact_arc(a,b,gradient);
    double margin=INFINITY;
    for(int axis=0;axis<3;++axis)
      margin=std::min(margin,std::min(arc.minimum[axis]+15,15-arc.maximum[axis]));
    std::vector<P> exact_polyline(4097);
    for(std::size_t i=0;i<exact_polyline.size();++i)
      exact_polyline[i]=arc.point(arc.first_angle+(arc.last_angle-arc.first_angle)*i/(exact_polyline.size()-1));
    exact_polyline.front()=a;exact_polyline.back()=b;
    double arc_action=path_eval(g,exact_polyline),fd_error=0;
    for(int axis=0;axis<3;++axis) {
      P plus=a,minus=a;plus[axis]+=1e-4;minus[axis]-=1e-4;
      double derivative=(exact(plus,b,gradient).time-exact(minus,b,gradient).time)/2e-4;
      fd_error=std::max(fd_error,std::abs(derivative-reference.source[axis]));
    }
    references<<name<<','<<velocity0;
    for(P p:{gradient,a,b})for(double value:p)references<<','<<value;
    references<<','<<*std::min_element(g.v.begin(),g.v.end())<<','<<*std::max_element(g.v.begin(),g.v.end())
              <<','<<reference.time<<','<<arc.integrated_time<<','<<arc_action;
    for(P p:{arc.minimum,arc.maximum})for(double value:p)references<<','<<value;
    references<<','<<margin;
    for(double value:reference.source)references<<','<<value;
    references<<','<<fd_error<<std::endl;
    check(name,"reference","arc_inside_box",std::max(0.,-margin),0);
    check(name,"reference","circle_integral_formula",std::abs(arc.integrated_time-reference.time),
          128*std::numeric_limits<double>::epsilon()*(1+reference.time));
    check(name,"reference","arc_polyline_action",std::abs(arc_action-reference.time),2.5e-5);
    check(name,"reference","formula_source_finite_difference",fd_error,3e-6);
    save_path(name,"forward","exact_arc",exact_polyline);
    std::array<Comparison,2> comparisons;
    for(int reverse=0;reverse<2;++reverse) {
      P source=reverse?b:a,receiver=reverse?a:b;
      std::string direction=reverse?"reverse":"forward";
      Exact ref=exact(source,receiver,gradient);
      auto start=Clock::now();
      first_arrival::Field field(g,receiver,aux,2,true);
      double field_seconds=seconds(start);
      start=Clock::now();
      auto c=compare(g,field,source,receiver,spacing);
      double ray_seconds=seconds(start);
      comparisons[reverse]=c;
      int outside=0;
      for(P p:c.best.path) outside+=!g.contains(p);
      double endpoint_error=norm(c.best.path.front()-source)+norm(c.best.path.back()-receiver);
      rows<<name<<','<<direction<<','<<level<<','<<aux<<','<<spacing<<','<<field.node_count()
          <<','<<field.stats.seed_nodes<<','<<field_seconds<<','<<ray_seconds<<','<<c.seed.success
          <<','<<c.seed.message<<','<<c.seed.field_time<<','<<(c.seed.success?path_eval(g,c.seed.path):NAN)
          <<','<<c.direct.time<<','<<c.direct.converged<<','<<c.direct.gradient
          <<','<<(c.seed.success?c.bent.time:NAN)<<','<<(c.seed.success&&c.bent.converged)
          <<','<<(c.seed.success?c.bent.gradient:NAN)<<','<<c.bent.iterations;
      for(double value:c.bent.source) rows<<','<<(c.seed.success?value:NAN);
      rows<<','<<(c.seed.success?c.bent.time-ref.time:NAN)
          <<','<<(c.seed.success?norm(c.bent.source-ref.source):NAN)
          <<','<<(c.fmm_selected?"fmm_seed":"direct_seed")<<','<<c.best.time
          <<','<<c.best.converged<<','<<c.best.gradient<<','<<ref.time;
      for(double value:ref.source) rows<<','<<value;
      rows<<','<<c.best.time-ref.time<<','<<norm(c.best.source-ref.source)<<','<<outside
          <<','<<endpoint_error<<','<<field.stats.second_order_direction_evaluations
          <<','<<field.stats.second_order_ineligible<<','<<field.stats.causal_fallback_updates<<std::endl;
      check(name,direction,"extracted",c.seed.success?0:1,0);
      check(name,direction,"fmm_bent_exact_time",c.seed.success?std::abs(c.bent.time-ref.time):NAN,2.5e-5);
      check(name,direction,"fmm_bent_exact_source",c.seed.success?norm(c.bent.source-ref.source):NAN,3e-6);
      check(name,direction,"fmm_bent_converged",c.seed.success&&c.bent.converged?0:1,0);
      check(name,direction,"selected_exact_time",std::abs(c.best.time-ref.time),2.5e-5);
      check(name,direction,"selected_exact_source",norm(c.best.source-ref.source),3e-6);
      check(name,direction,"selected_converged",c.best.converged?0:1,0);
      check(name,direction,"selected_outside_nodes",outside,0);
      check(name,direction,"selected_endpoint_error",endpoint_error,0);
      save_path(name,direction,"direct_bent",c.direct.path);
      if(c.seed.success) {
        save_path(name,direction,"fmm_raw",c.seed.path);
        save_path(name,direction,"fmm_bent",c.bent.path);
      }
    }
    check(name,"both","selected_reciprocity",std::abs(comparisons[0].best.time-comparisons[1].best.time),2e-5);
    check(name,"both","fmm_bent_reciprocity",comparisons[0].seed.success&&comparisons[1].seed.success?
          std::abs(comparisons[0].bent.time-comparisons[1].bent.time):NAN,2e-5);
  }
  return entry_checks.failures ? 1 : 0;
}
