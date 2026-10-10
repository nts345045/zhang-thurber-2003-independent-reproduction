// Isolated optimizer observation; original stopping/updates are not modified.
#define main frozen_solver_entry_point
#include "../src/main.cpp"
#undef main
#include "first_arrival_fmm.hpp"
#ifndef AUDIT_PRODUCTION_HYBRID
#include "seeded_bending.hpp"
#endif
#ifdef AUDIT_REDUCED_METRIC
#include "reduced_ray_metric.hpp"
#ifdef AUDIT_CONE_METRIC
#include "cone_ray_metric.hpp"
#endif
#include "control_optimizer.hpp"
#endif

std::ofstream *audit_history=nullptr;
std::string audit_run;
std::string audit_observation;
#if defined(AUDIT_REDUCED_METRIC) || defined(AUDIT_PRODUCTION_HYBRID)
std::ofstream *audit_metric_file=nullptr;
#ifdef AUDIT_REDUCED_METRIC
void audit_metric(const ReducedRayMetricStats &stats) {
  if(audit_metric_file)
    *audit_metric_file<<audit_run<<','<<audit_observation<<','<<stats.initial_fixed<<','
      <<stats.added_fixed<<','<<stats.solves<<','<<stats.free_equation_max_error<<','
      <<stats.slope<<','<<stats.inward_multiplier_violations<<','
      <<stats.most_negative_signed_multiplier<<'\n';
}
#endif
#ifdef AUDIT_CONE_METRIC
void audit_metric(const ConeRayMetricStats &stats) {
  if(audit_metric_file)
    *audit_metric_file<<audit_run<<','<<audit_observation<<','<<stats.success<<','
      <<stats.solves<<','<<stats.releases<<','<<stats.blocks<<','<<stats.initial_fixed<<','
      <<stats.final_fixed<<','<<stats.free_equation_max_error<<','<<stats.primal_violation<<','
      <<stats.dual_violation<<','<<stats.complementarity_max_error<<','<<stats.slope<<','
      <<stats.kkt_roundoff_tolerance<<','<<stats.free_equation_relative_backward_error<<','
      <<stats.maximum_arithmetic_scale<<'\n';
}
#endif
#endif
void audit_step(const char *phase,int iteration,int updates,const Grid &g,
                const std::vector<P> &path,const Vec &gradient,double action,
                double change,double step,double feasible_step,double slope,
                const Vec *direction,int searches,std::size_t memory,
                bool reset,int merged,bool curvature_accepted) {
  if(!audit_history) return;
  double shortest=INFINITY,longest=0,tangential=0,normal=0,maximum_move=0;
  for(std::size_t i=1;i<path.size();++i) {
    double length=norm(path[i]-path[i-1]);
    shortest=std::min(shortest,length);longest=std::max(longest,length);
  }
  std::array<int,6> faces{};
  const Vec *axes[]={&g.x,&g.y,&g.z};
  double closest_internal_plane=INFINITY;
  for(std::size_t i=1;i+1<path.size();++i) {
    P tangent=path[i+1]-path[i-1];
    double length=norm(tangent);
    if(length) tangent=tangent*(1/length);
    P grad{gradient[3*(i-1)],gradient[3*(i-1)+1],gradient[3*(i-1)+2]};
    double parallel=dot(grad,tangent);
    tangential+=parallel*parallel;
    normal+=std::max(0.,dot(grad,grad)-parallel*parallel);
    for(int axis=0;axis<3;++axis) {
      faces[2*axis]+=path[i][axis]<=axes[axis]->front()+1e-10;
      faces[2*axis+1]+=path[i][axis]>=axes[axis]->back()-1e-10;
      for(std::size_t k=1;k+1<axes[axis]->size();++k)
        closest_internal_plane=std::min(closest_internal_plane,std::abs(path[i][axis]-(*axes[axis])[k]));
    }
  }
  if(direction)
    for(std::size_t i=0;i<direction->size()/3;++i)
      maximum_move=std::max(maximum_move,std::abs(step)*norm(P{(*direction)[3*i],(*direction)[3*i+1],(*direction)[3*i+2]}));
  auto &f=*audit_history;
  f<<audit_run<<','<<audit_observation<<','<<phase<<','<<iteration<<','<<updates<<','
   <<action<<','<<projected_ray_gradient(g,path,gradient)<<','<<norm(gradient)<<','
   <<change<<','<<step<<','<<feasible_step<<','<<slope<<','<<searches<<','<<memory<<','
   <<reset<<','<<merged<<','<<curvature_accepted<<','<<maximum_move<<','<<path.size()<<','
   <<shortest<<','<<longest<<','<<std::sqrt(tangential)<<','<<std::sqrt(normal)<<','
   <<closest_internal_plane;
  for(int count:faces)f<<','<<count;
  f<<'\n';
}
#include "curvature_capture.hpp"
#include "observed_optimizer.hpp"

Vec values(const std::string &text) {
  Vec result;
  std::istringstream stream(text);
  std::string item;
  while(std::getline(stream,item,','))result.push_back(std::stod(item));
  return result;
}
int main(int argc,char **argv) {
  if(argc!=7)throw std::runtime_error("Usage: check_ray_stopping GRID.csv IDENTIFIED_RAY.csv OUT BUDGETS SPACINGS FIELD_SPACING");
  Grid g=read_grid(argv[1]);
  auto input=csv_table(argv[2]);
  if(input.rows.size()!=1)throw std::runtime_error("Exactly one identified ray is required");
  std::map<std::string,std::size_t> cols;
  for(std::size_t i=0;i<input.header.size();++i)cols[input.header[i]]=i;
  const auto &record=input.rows[0];
  auto pos=[&](const std::string &prefix) {return P{csv_double(record[cols.at(prefix+"x_km")]),csv_double(record[cols.at(prefix+"y_km")]),csv_double(record[cols.at(prefix+"z_km")])};};
  P a=pos("source_"),b=pos("receiver_");
  audit_observation=record[cols.at("observation_index")];
  std::string out=argv[3];
  curvature_open(out);
  std::ofstream results(out+"/results.csv"),history(out+"/history.csv"),paths(out+"/paths.csv"),fd(out+"/path_gradient_checks.csv");
  if(!results||!history||!paths||!fd)throw std::runtime_error("Cannot open ray-stopping audit files");
  for(auto f:{&results,&history,&paths,&fd})*f<<std::setprecision(17);
#if defined(AUDIT_REDUCED_METRIC) || defined(AUDIT_PRODUCTION_HYBRID)
#ifdef AUDIT_CONE_METRIC
  std::ofstream metric(out+"/cone_metric.csv");
#else
  std::ofstream metric(out+"/reduced_metric.csv");
#endif
  if(!metric)throw std::runtime_error("Cannot open reduced metric audit");
  metric<<std::setprecision(17);
#ifdef AUDIT_CONE_METRIC
  metric<<"run_id,observation_index,success,solves,releases,blocks,initial_fixed,final_fixed,free_equation_max_error,primal_violation,dual_violation,complementarity_max_error,slope,kkt_roundoff_tolerance,free_equation_relative_backward_error,maximum_arithmetic_scale\n";
#else
  metric<<"run_id,observation_index,initial_fixed,added_fixed,solves,free_equation_max_error,slope,inward_multiplier_violations,most_negative_signed_multiplier\n";
#endif
  audit_metric_file=&metric;
  results<<"run_id,observation_index,initialization,path_spacing_km,max_updates,updates,converged,time_s,projected_gradient,raw_gradient,merged_nodes,path_nodes,source_dx,source_dy,source_dz,logged_matches_unobserved_variant\n";
#else
  results<<"run_id,observation_index,initialization,path_spacing_km,max_updates,updates,converged,time_s,projected_gradient,raw_gradient,merged_nodes,path_nodes,source_dx,source_dy,source_dz,logged_matches_unmodified\n";
#endif
  history<<"run_id,observation_index,phase,iteration,updates,time_s,projected_gradient,raw_gradient,action_change_s,accepted_step,feasible_initial_step,directional_slope,line_search_evaluations,memory_pairs,gradient_fallback,merged_nodes,curvature_pair_accepted,max_node_step_km,path_nodes,min_segment_km,max_segment_km,tangential_gradient_norm,normal_gradient_norm,min_internal_grid_plane_distance_km,x_min_active,x_max_active,y_min_active,y_max_active,z_min_active,z_max_active\n";
  paths<<"run_id,observation_index,node,x,y,z,gradient_x,gradient_y,gradient_z\n";
  fd<<"run_id,observation_index,node,axis,step_km,scheme,analytic_gradient,numerical_gradient,error\n";
  first_arrival::Field field(g,b,std::stod(argv[6]),2,true);
  auto seed=field.candidate(a);
  if(!seed.success)throw std::runtime_error(seed.message);
  for(double spacing:values(argv[5]))for(double budget_value:values(argv[4]))for(bool fmm:{false,true}) {
    int budget=int(budget_value);
    if(budget<=0||budget_value!=budget||spacing<=0)throw std::runtime_error("Invalid component budget or spacing");
    audit_run=(fmm?"fmm_":"straight_")+std::to_string(spacing)+"_"+std::to_string(budget);
    curvature_capture_active=fmm;
    if(fmm)curvature_seed(seed);
    audit_history=&history;
#ifdef AUDIT_PRODUCTION_HYBRID
    Ray ray=observed_trace(g,a,b,spacing,budget,true,fmm?&seed.path:nullptr);
#else
    Ray ray=fmm?observed_bend_seed(g,seed.path,spacing,budget):observed_trace(g,a,b,spacing,budget);
#endif
    audit_history=nullptr;
    curvature_capture_active=false;
    // Test observation neutrality against the actual unmodified functions.
#ifdef AUDIT_PRODUCTION_HYBRID
    Ray control=trace(g,a,b,spacing,budget,true,fmm?&seed.path:nullptr);
#elif defined(AUDIT_REDUCED_METRIC)
    Ray control=fmm?control_bend_seed(g,seed.path,spacing,budget):control_trace(g,a,b,spacing,budget);
#else
    Ray control=fmm?bend_seed(g,seed.path,spacing,budget):trace(g,a,b,spacing,budget);
#endif
    bool matches=ray.time==control.time&&ray.path==control.path&&ray.gradient==control.gradient&&
                 ray.raw_gradient==control.raw_gradient&&ray.source==control.source&&
                 ray.iterations==control.iterations&&ray.converged==control.converged&&
                 ray.dv==control.dv&&ray.length==control.length&&ray.merged_nodes==control.merged_nodes;
    results<<audit_run<<','<<audit_observation<<','<<(fmm?"fmm":"straight")<<','<<spacing<<','<<budget
           <<','<<ray.iterations<<','<<ray.converged<<','<<ray.time<<','<<ray.gradient<<','<<ray.raw_gradient
           <<','<<ray.merged_nodes<<','<<ray.path.size();
    for(double value:ray.source)results<<','<<value;
    results<<','<<matches<<std::endl;
    Vec gradient;
    path_eval(g,ray.path,&gradient);
    for(std::size_t i=0;i<ray.path.size();++i) {
      paths<<audit_run<<','<<audit_observation<<','<<i;
      for(double value:ray.path[i])paths<<','<<value;
      for(int axis=0;axis<3;++axis)paths<<','<<(i&&i+1<ray.path.size()?gradient[3*(i-1)+axis]:NAN);
      paths<<'\n';
    }
    Vec projected=gradient;
    for(auto &v:projected)v=-v;
    project_ray_direction(g,ray.path,projected);
    std::size_t worst=std::max_element(projected.begin(),projected.end(),[](double x,double y){return std::abs(x)<std::abs(y);})-projected.begin();
    std::size_t node=worst/3+1;int axis=worst%3;
    for(double h:{1e-4,1e-5,1e-6}) {
      auto plus=ray.path,minus=ray.path;plus[node][axis]+=h;minus[node][axis]-=h;
      bool forward=g.contains(plus[node]),backward=g.contains(minus[node]);
      double derivative=NAN;std::string scheme="unavailable";
      if(forward&&backward) {derivative=(path_eval(g,plus)-path_eval(g,minus))/(2*h);scheme="central";}
      else if(forward) {derivative=(path_eval(g,plus)-ray.time)/h;scheme="forward";}
      else if(backward) {derivative=(ray.time-path_eval(g,minus))/h;scheme="backward";}
      fd<<audit_run<<','<<audit_observation<<','<<node<<','<<axis<<','<<h<<','<<scheme<<','
        <<gradient[worst]<<','<<derivative<<','<<derivative-gradient[worst]<<'\n';
    }
    std::cout<<audit_run<<" converged="<<ray.converged<<" updates="<<ray.iterations
             <<" gradient="<<ray.gradient<<" observed_matches="<<matches<<std::endl;
  }
  curvature_flush();
}
