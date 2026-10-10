// Exact-family seeds are diagnostic controls, never production replacements.
#define main frozen_solver_main
#include "../src/main.cpp"
#undef main
#include "loma_path_checks.hpp"
#include "preserve_seed_trace.hpp"

bool same_ray(const Ray &a, const Ray &b) {
  return a.time==b.time && a.path==b.path && a.source==b.source &&
    a.dv==b.dv && a.length==b.length && a.gradient==b.gradient &&
    a.raw_gradient==b.raw_gradient && a.converged==b.converged &&
    a.iterations==b.iterations && a.merged_nodes==b.merged_nodes;
}

int main(int argc,char **argv) {
  if(argc!=5) throw std::runtime_error("Usage: check_loma_reference_seeds GRID CASES SEEDS OUT");
  Grid g=read_grid(argv[1]);
  auto cases=csv_table(argv[2]),seeds=csv_table(argv[3]);
  std::map<std::string,size_t> ci,si;
  for(size_t i=0;i<cases.header.size();++i) ci[cases.header[i]]=i;
  for(size_t i=0;i<seeds.header.size();++i) si[seeds.header[i]]=i;
  std::string output=argv[4];
  std::ofstream result(output+"/results.csv"),paths(output+"/paths.csv"),
    finite_difference(output+"/finite_difference.csv"),checks(output+"/checks.csv");
  if(!result||!paths||!finite_difference||!checks) throw std::runtime_error("Cannot create output");
  for(auto stream:{&result,&paths,&finite_difference,&checks}) *stream<<std::setprecision(21);
  result<<"case_id,stage,time_s,exact_polygon_time_s,quadrature_error_s,reference_time_s,time_error_s,path_nodes,updates,converged,projected_gradient,raw_gradient,merged_nodes,source_dx,source_dy,source_dz,source_error_norm,exact_interface_nodes,strict_interface_crossings,min_x,max_x";
  paths<<"case_id,stage,node,x,y,z,gradient_x,gradient_y,gradient_z";
  finite_difference<<"case_id,stage,test,axis,step_km,analytic_gradient,exact_forward,exact_backward,exact_central";
  checks<<"case_id,check,passed\n";
  const Strings ids{"diagnostic_row","event","station","source_event_resource_id","source_origin_resource_id",
    "receiver_channel_seed_id","receiver_channel_fdsn_source_id","receiver_metadata_epoch_start","receiver_metadata_epoch_end"};
  for(auto stream:{&result,&paths,&finite_difference}) {
    for(const auto &name:ids) *stream<<','<<name;
    *stream<<'\n';
  }
  auto check=[&](const std::string &id,const std::string &name,bool passed) {
    checks<<id<<','<<name<<','<<passed<<std::endl;
    if(!passed) throw std::runtime_error(id+": "+name);
  };
  // The copied trace differs only for supplied seed initialization. Exercise
  // the untouched null-seed path and an exactly uniform supplied path.
  Grid flat; flat.x={-2,2};flat.y={-2,2};flat.z={-2,2};flat.v.assign(8,5);
  P fa{-1,0,0},fb{1,0,0};std::vector<P> uniform{{-1,0,0},{-.5,0,0},{0,0,0},{.5,0,0},{1,0,0}};
  for(int budget:{0,10}) {
    check("invented","unseeded_flat_"+std::to_string(budget),same_ray(trace(flat,fa,fb,.5,budget,true),trace_preserve_seed(flat,fa,fb,.5,budget,true)));
    check("invented","uniform_seed_flat_"+std::to_string(budget),same_ray(trace(flat,fa,fb,.5,budget,true,&uniform),trace_preserve_seed(flat,fa,fb,.5,budget,true,&uniform)));
  }
  for(const auto &record:cases.rows) {
    const std::string id=record[ci.at("case_id")];
    std::vector<P> seed;
    for(const auto &row:seeds.rows) if(row[si.at("case_id")]==id) {
      check(id,"seed_order_"+std::to_string(seed.size()),csv_int(row[si.at("node")])==int(seed.size()));
      seed.push_back({csv_double(row[si.at("x")]),csv_double(row[si.at("y")]),csv_double(row[si.at("z")])});
    }
    auto point=[&](const std::string &prefix) {return P{csv_double(record[ci.at(prefix+"x")]),csv_double(record[ci.at(prefix+"y")]),csv_double(record[ci.at(prefix+"z")])};};
    P a=point("source_"),b=point("receiver_");
    const double spacing=csv_double(record[ci.at("spacing_km")]);
    const double reference=csv_double(record[ci.at("reference_time_s")]);
    P source_reference{csv_double(record[ci.at("reference_source_dx")]),csv_double(record[ci.at("reference_source_dy")]),csv_double(record[ci.at("reference_source_dz")])};
    check(id,"exact_endpoints",seed.size()>2 && seed.front()==a && seed.back()==b);
    check(id,"inside_original_box",std::all_of(seed.begin(),seed.end(),[&](P p){return g.contains(p);}));
    if(spacing==.5) check(id,"unseeded_actual_10_updates",same_ray(trace(g,a,b,spacing,10,true),trace_preserve_seed(g,a,b,spacing,10,true)));
    auto append_ids=[&](std::ostream &stream) {for(const auto &name:ids) stream<<','<<csv_quote(record[ci.at(name)]);stream<<'\n';};
    auto emit=[&](const std::string &stage,const Ray &ray) {
      Vec gradient;double time=path_eval(g,ray.path,&gradient);
      check(id,stage+"_action_matches",time==ray.time);
      check(id,stage+"_endpoints",ray.path.front()==a && ray.path.back()==b);
      check(id,stage+"_inside",std::all_of(ray.path.begin(),ray.path.end(),[&](P p){return g.contains(p);}));
      P source{};segment(g,ray.path[0],ray.path[1],&source);
      long double exact=loma_exact_action(g,ray.path);
      size_t aligned=0,crossings=0;double lo=INFINITY,hi=-INFINITY;
      for(size_t i=0;i<ray.path.size();++i) {
        aligned+=ray.path[i][0]==0;lo=std::min(lo,ray.path[i][0]);hi=std::max(hi,ray.path[i][0]);
        if(i) for(double x:g.x) crossings+=(ray.path[i-1][0]<x&&ray.path[i][0]>x)||(ray.path[i-1][0]>x&&ray.path[i][0]<x);
      }
      result<<id<<','<<stage<<','<<time<<','<<exact<<','<<(long double)time-exact<<','<<reference<<','<<time-reference<<','<<ray.path.size()<<','<<ray.iterations<<','<<ray.converged<<','<<projected_ray_gradient(g,ray.path,gradient)<<','<<norm(gradient)<<','<<ray.merged_nodes;
      for(double value:source) result<<','<<value;
      result<<','<<norm(source-source_reference)<<','<<aligned<<','<<crossings<<','<<lo<<','<<hi;append_ids(result);result.flush();
      for(size_t i=0;i<ray.path.size();++i) {
        paths<<id<<','<<stage<<','<<i;
        for(double value:ray.path[i]) paths<<','<<value;
        for(int axis=0;axis<3;++axis) paths<<','<<(i&&i+1<ray.path.size()?gradient[3*(i-1)+axis]:0);
        append_ids(paths);
      }
      for(double h:{1e-4,1e-5,1e-6}) {
        for(int axis=0;axis<3;++axis) {
          auto plus=ray.path,minus=ray.path;plus[0][axis]+=h;minus[0][axis]-=h;
          const long double tp=loma_exact_action(g,plus),tm=loma_exact_action(g,minus);
          finite_difference<<id<<','<<stage<<",fixed_polygon_source,"<<axis<<','<<h<<','<<source[axis]<<','<<(tp-exact)/h<<','<<(exact-tm)/h<<','<<(tp-tm)/(2*h);append_ids(finite_difference);
        }
        if(aligned>2) {
          auto plus=ray.path,minus=ray.path;double directional=0;
          for(size_t i=1;i+1<ray.path.size();++i) if(ray.path[i][0]==0) {
            plus[i][0]+=h;minus[i][0]-=h;directional+=gradient[3*(i-1)];
          }
          const long double tp=loma_exact_action(g,plus),tm=loma_exact_action(g,minus);
          finite_difference<<id<<','<<stage<<",coupled_exact_guide_nodes,0,"<<h<<','<<directional<<','<<(tp-exact)/h<<','<<(exact-tm)/h<<','<<(tp-tm)/(2*h);append_ids(finite_difference);
        }
      }
    };
    Ray raw;raw.path=seed;raw.time=path_eval(g,seed);raw.converged=false;
    emit("analytic_seed_polygon",raw);
    emit("uniform_resampled_zero_updates",trace(g,a,b,spacing,0,true,&seed));
    auto retained=trace_preserve_seed(g,a,b,spacing,0,true,&seed);
    check(id,"no_resampling_initial_path_exact",retained.path==seed);
    emit("retained_seed_zero_updates",retained);
    emit("uniform_resampled_optimized",trace(g,a,b,spacing,1000,true,&seed));
    emit("retained_seed_optimized",trace_preserve_seed(g,a,b,spacing,1000,true,&seed));
    std::cout<<id<<" complete"<<std::endl;
  }
}
