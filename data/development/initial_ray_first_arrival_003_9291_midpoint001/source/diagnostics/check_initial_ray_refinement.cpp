// Insert a free midpoint without changing the saved curve. No knot is snapped
// to an interface and no converged flag is changed. Test a physical depth tent.
#define main unused_solver_main
#include "../src/main.cpp"
#undef main
#include "loma_path_checks.hpp"

int main(int argc,char **argv) {
  if(argc!=5)throw std::runtime_error("Usage: check_initial_ray_refinement GRID PATHS RUN_ID OUTPUT");
  Grid g=read_grid(argv[1]);auto rows=csv_table(argv[2]);std::string run=argv[3],observation;
  std::map<std::string,size_t> cols;
  for(size_t i=0;i<rows.header.size();++i)cols[rows.header[i]]=i;
  std::vector<P> path;
  for(const auto &row:rows.rows)if(row[cols.at("run_id")]==run) {
    observation=row[cols.at("observation_index")];
    if(csv_int(row[cols.at("node")])!=int(path.size()))throw std::runtime_error("Nonconsecutive saved nodes");
    path.push_back({csv_double(row[cols.at("x")]),csv_double(row[cols.at("y")]),csv_double(row[cols.at("z")])});
  }
  if(path.size()<2)throw std::runtime_error("No path selected");
  // Exact integrator takes x-only fields. A coordinate permutation maps the
  // original depth profile to x without changing Euclidean length or action.
  Grid permuted;permuted.x=g.z;permuted.y=g.x;permuted.z=g.y;permuted.v.resize(g.size());
  for(size_t k=0;k<g.z.size();++k)for(size_t j=0;j<g.y.size();++j)for(size_t i=0;i<g.x.size();++i) {
    if(g.v[g.id(i,j,k)]!=g.v[g.id(0,0,k)])throw std::runtime_error("Expected depth-only field");
    permuted.v[permuted.id(k,i,j)]=g.v[g.id(i,j,k)];
  }
  auto exact=[&](const std::vector<P> &points) {
    std::vector<P> transformed;for(P p:points)transformed.push_back({p[2],p[0],p[1]});
    return loma_exact_action(permuted,transformed);
  };
  std::ofstream out(argv[4]);if(!out)throw std::runtime_error("Cannot write refinement control");
  out<<std::setprecision(21)<<"run_id,observation_index,segment,end_a_z_km,end_b_z_km,original_action_s,inserted_action_s,insertion_action_difference_s,midpoint_gradient_z_s_per_km,depth_tent_km,perturbed_action_s,action_difference_s,one_sided_difference_s_per_km,quadrature_minus_exact_s\n";
  const auto initial=exact(path);
  for(size_t i=1;i<path.size();++i) {
    auto refined=path;
    refined.insert(refined.begin()+i,(path[i-1]+path[i])*.5);
    Vec gradient;path_eval(g,refined,&gradient);
    const auto inserted=exact(refined);
    for(double delta:{0.,1e-7,1e-5,1e-3,1e-2}) {
      auto perturbed=refined;perturbed[i][2]+=delta;
      if(!g.contains(perturbed[i]))continue;
      auto changed=exact(perturbed);
      out<<run<<','<<observation<<','<<i-1<<','<<path[i-1][2]<<','<<path[i][2]<<','
         <<initial<<','<<inserted<<','<<inserted-initial<<','<<gradient[3*(i-1)+2]<<','
         <<delta<<','<<changed<<','<<changed-initial<<','<<(delta?(changed-inserted)/delta:0)<<','
         <<(long double)path_eval(g,perturbed)-changed<<'\n';
    }
  }
}
