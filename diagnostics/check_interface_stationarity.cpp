// Invented interface case; no provider geometry or inversion.
#include "../src/core.hpp"
#include <iomanip>
#include <iostream>

int main() {
  Grid g;
  g.x = {-1, 0, 1}; g.y = {0, 1, 2}; g.z = {-1, 1};
  g.v.resize(g.size());
  for (std::size_t k = 0; k < g.z.size(); ++k)
    for (std::size_t j = 0; j < g.y.size(); ++j)
      for (std::size_t i = 0; i < g.x.size(); ++i)
        g.v[g.id(i, j, k)] = 6 - 2 * std::max(0., g.x[i]);
  auto action = [&](double p) {
    return path_eval(g, {{0, 0, 0}, {p, 1, 0}, {0, 2, 0}});
  };
  auto exact = [](double p) {
    return p <= 0 ? std::sqrt(1 + p*p)/3
                  : std::sqrt(1 + p*p)*(-std::log1p(-p/3))/p;
  };
  std::cout << std::setprecision(17) << "{\"path_cases\":[";
  bool first = true;
  for (double p : {-1e-3, -1e-5, -1e-7, 0., 1e-7, 1e-5, 1e-3}) {
    Vec gradient;
    double time = path_eval(g, {{0, 0, 0}, {p, 1, 0}, {0, 2, 0}}, &gradient);
    std::cout << (first ? "" : ",") << "{\"p_km\":" << p
              << ",\"time_s\":" << time << ",\"exact_time_s\":" << exact(p)
              << ",\"gradient_x_s_per_km\":" << gradient[0] << '}';
    first = false;
  }
  auto ray = trace(g, {0, 0, 0}, {0, 2, 0}, 1., 1000, true);
  std::cout << "],\"ray\":{\"time_s\":" << ray.time
            << ",\"projected_gradient\":" << ray.gradient
            << ",\"raw_gradient\":" << ray.raw_gradient
            << ",\"updates\":" << ray.iterations
            << ",\"converged\":" << (ray.converged ? "true" : "false")
            << ",\"source_derivative_s_per_km\":[" << ray.source[0] << ','
            << ray.source[1] << ',' << ray.source[2] << "]},\"secants\":[";
  first = true;
  for (double h : {1e-3, 1e-5, 1e-7}) {
    std::cout << (first ? "" : ",") << "{\"h_km\":" << h
              << ",\"left_s_per_km\":" << (action(0)-action(-h))/h
              << ",\"right_s_per_km\":" << (action(h)-action(0))/h << '}';
    first = false;
  }
  std::cout << "]}\n";
}
