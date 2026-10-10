// Invented fixed paths only. No trace, search, field construction or stopping test.
#ifdef NDEBUG
#error "Diagnostic checks require assertions"
#endif
#include "src/core.hpp"
#include <cassert>

int main(int argc, char **argv) {
  if (argc != 2) throw std::runtime_error("Usage: observe FRESH_RESULTS_DIRECTORY");
  const std::string dir = argv[1];
  std::ofstream paths(dir + "/paths.csv"), edges(dir + "/face_segments.csv");
  if (!paths || !edges) throw std::runtime_error("Cannot create observation files");
  paths << std::setprecision(17)
        << "model,midpoint_x_km,path_action_s,midpoint_gx_s_per_km,midpoint_gy_s_per_km,midpoint_gz_s_per_km\n";
  edges << std::setprecision(17)
        << "model,action_s,a_gx_s_per_km,a_gy_s_per_km,a_gz_s_per_km,b_gx_s_per_km,b_gy_s_per_km,b_gz_s_per_km\n";
  int path_calls = 0, segment_calls = 0;
  for (int kind = 0; kind < 2; ++kind) {
    const std::string label = kind == 0 ? "fast_ridge" : "slow_face";
    Grid g; g.x = {-1, 0, 1}; g.y = {-1, 1}; g.z = {-1, 1}; g.v.resize(g.size());
    for (int k = 0; k < 2; ++k) for (int j = 0; j < 2; ++j) for (int i = 0; i < 3; ++i)
      g.v[g.id(i,j,k)] = kind == 0 ? 6 - std::abs(g.x[i]) : 5 + std::abs(g.x[i]);
    std::vector<double> xs{0};
    for (int exponent : {8, 16, 24}) for (double sign : {-1., 1.}) xs.push_back(sign * std::ldexp(1., -exponent));
    for (double x : xs) {
      const std::vector<P> p{{0,-.5,0},{x,0,0},{0,.5,0}};
      Vec gradient;
      const double action = path_eval(g,p,&gradient); ++path_calls;
      assert(gradient.size() == 3 && std::isfinite(action));
      for (double q : gradient) assert(std::isfinite(q));
      paths << label << ',' << x << ',' << action;
      for (double q : gradient) paths << ',' << q;
      paths << '\n';
    }
    P a{}, b{};
    const double action = segment(g, P{0,-.5,0}, P{0,.5,0}, &a, &b); ++segment_calls;
    edges << label << ',' << action;
    for (double q : a) { assert(std::isfinite(q)); edges << ',' << q; }
    for (double q : b) { assert(std::isfinite(q)); edges << ',' << q; }
    edges << '\n';
  }
  paths.close(); edges.close();
  if (!paths || !edges) throw std::runtime_error("Cannot finish observation files");
  assert(path_calls == 14 && segment_calls == 2);
  std::cout << "path_evaluations=14 direct_segment_evaluations=2 trace_calls=0 optimizer_calls=0\n";
}
