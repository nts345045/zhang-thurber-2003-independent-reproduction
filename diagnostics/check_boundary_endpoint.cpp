// A fixed-path subdivision diagnostic; never retrace or change solver flags.
#define main frozen_solver_entry
#include "../src/main.cpp"
#undef main

int main(int argc, char **argv) {
  if (argc != 5)
    throw std::runtime_error("Expected GRID PATHS RUN_ID OUTPUT");
  const Grid g = read_grid(argv[1]);
  const auto table = csv_table(argv[2]);
  std::map<std::string, size_t> column;
  for (size_t k = 0; k < table.header.size(); ++k) column[table.header[k]] = k;
  const std::string run = argv[3];
  std::string observation;
  std::vector<P> original;
  for (const auto &row : table.rows) if (row[column.at("run_id")] == run) {
    if (csv_int(row[column.at("node")]) != int(original.size()))
      throw std::runtime_error("Nonconsecutive path nodes");
    if (!original.empty() && observation != row[column.at("observation_index")])
      throw std::runtime_error("Mixed native ray identities");
    observation = row[column.at("observation_index")];
    original.push_back({csv_double(row[column.at("x")]), csv_double(row[column.at("y")]),
                        csv_double(row[column.at("z")])});
  }
  if (original.size() < 2 || g.z.size() < 2 ||
      original[0][2] != g.z.back() || original[1][2] != g.z.back())
    throw std::runtime_error("Expected a nonempty horizontal leading bottom edge");
  for (const auto &point : original)
    if (!g.contains(point)) throw std::runtime_error("Saved path outside original domain");
  for (size_t k = 0; k < g.z.size(); ++k)
    for (size_t j = 0; j < g.y.size(); ++j)
      for (size_t i = 0; i < g.x.size(); ++i)
        if (g.v[g.id(i,j,k)] != g.v[g.id(0,0,k)])
          throw std::runtime_error("This analytic control requires the unchanged depth-only profile");
  const double speed = g.v[g.id(0,0,g.z.size()-1)];
  const double velocity_slope = (speed-g.v[g.id(0,0,g.z.size()-2)]) /
                                (g.z.back()-g.z[g.z.size()-2]);
  const double slowness_slope = -velocity_slope/(speed*speed);
  const P a = original[0], b = original[1];
  const double original_length = norm(b-a), original_action = path_eval(g,original);
  if (!(original_length > 0)) throw std::runtime_error("Zero leading edge");
  P original_source{};
  segment(g,a,b,&original_source);
  auto result = output(argv[4]);
  result << std::setprecision(17)
    << "run_id,observation_index,leading_subsegments,path_nodes,original_leading_length_km,"
       "new_leading_length_km,action_s,action_minus_original_s,maximum_inserted_collinearity_error_km,"
       "slowness_depth_slope_s_per_km2,analytic_fixed_source_dz_s_per_km,"
       "original_source_dx,original_source_dy,original_source_dz,"
       "fixed_inserted_source_dx,fixed_inserted_source_dy,fixed_inserted_source_dz,"
       "tied_inserted_source_dx,tied_inserted_source_dy,tied_inserted_source_dz,"
       "maximum_tied_minus_original_source_error_s_per_km,projected_path_gradient_s_per_km\n";
  for (int pieces : {1,2,4,8,16}) {
    std::vector<P> path{a};
    double collinearity = 0;
    const P tangent = (b-a)*(1/original_length);
    for (int j = 1; j < pieces; ++j) {
      const P point = a+(b-a)*(double(j)/pieces);
      const P displacement = point-a;
      collinearity = std::max(collinearity, norm(displacement-tangent*dot(displacement,tangent)));
      path.push_back(point);
    }
    path.insert(path.end(),original.begin()+1,original.end());
    Vec gradient;
    const double action = path_eval(g,path,&gradient);
    P fixed{}, tied{};
    segment(g,path[0],path[1],&fixed);
    tied = fixed;
    // If each inserted point follows the original affine edge under endpoint
    // motion, this chain rule recovers the original variation family. Use raw
    // gradients: projecting them onto the box would change that contraction.
    for (int j = 1; j < pieces; ++j)
      for (int axis = 0; axis < 3; ++axis)
        tied[axis] += (1-double(j)/pieces)*gradient[3*(j-1)+axis];
    double error = 0;
    for (int axis = 0; axis < 3; ++axis)
      error = std::max(error,std::abs(tied[axis]-original_source[axis]));
    const double leading_length = norm(path[1]-path[0]);
    result << run << ',' << observation << ',' << pieces << ',' << path.size() << ','
           << original_length << ',' << leading_length << ',' << action << ',' << action-original_action << ','
           << collinearity << ',' << slowness_slope << ',' << leading_length*slowness_slope/2;
    for (const auto &values : {original_source,fixed,tied})
      for (double value : values) result << ',' << value;
    result << ',' << error << ',' << projected_ray_gradient(g,path,gradient) << '\n';
  }
}
