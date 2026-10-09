// Analytic component problems; no observational or inversion inputs.
#ifndef RAY_CORE_HEADER
#define RAY_CORE_HEADER "../src/core.hpp"
#endif
#include RAY_CORE_HEADER
#include <chrono>

int main() {
  std::cout << std::setprecision(15);
  Grid g = grid(true);
  set_true(g);
  P a{-0.5, 0, 1}, b{1.5, 1, 1}, ga{}, gb{};
  double time = segment(g, a, b, &ga, &gb), h = 1e-5, error = 0;
  for (int end = 0; end < 2; end++)
    for (int axis = 0; axis < 3; axis++) {
      P ap = a, am = a, bp = b, bm = b;
      (end ? bp : ap)[axis] += h;
      (end ? bm : am)[axis] -= h;
      double fd = (segment(g, ap, bp) - segment(g, am, bm)) / (2 * h);
      error = std::max(error, std::abs((end ? gb : ga)[axis] - fd));
    }
  // Here ds = sqrt(5)/2 dx, and velocity is constant/linear in x.
  double exact = std::sqrt(5.) / 2 * (0.5 / 6 + std::log(6. / 4) / 2 + 0.5 / 4);
  std::cerr << std::setprecision(15)
            << "crossing_segment_time_error_s=" << time - exact
            << " endpoint_gradient_fd_error_s_per_km=" << error << '\n';
  std::cout << "velocity_gradient_per_s,distance_km,spacing_km,iteration_limit,"
               "iterations,converged,time_s,reference_time_s,time_error_s,"
               "internal_gradient_s_per_km,source_error_s_per_km,seconds\n";
  for (double slope : {0.05, 0.2}) {
    double v0 = 5, distance = slope == 0.05 ? 20 : 40;
    for (int k = 0; k < int(g.z.size()); k++)
      for (int j = 0; j < int(g.y.size()); j++)
        for (int i = 0; i < int(g.x.size()); i++)
          g.v[g.id(i, j, k)] = v0 + slope * g.z[k];
    double reference = 2 / slope * std::asinh(slope * distance / (2 * v0));
    double radius = std::hypot(v0 / slope, distance / 2);
    P source{-1 / (slope * radius), 0, -distance / (2 * v0 * radius)};
    for (double spacing : {1., 0.5, 0.25})
      for (int limit : {180, 1000}) {
        auto start = std::chrono::steady_clock::now();
        auto ray = trace(g, {-distance / 2, 0, 0}, {distance / 2, 0, 0}, spacing, limit);
        double seconds = std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
        std::cout << slope << ',' << distance << ',' << spacing << ',' << limit
                  << ',' << ray.iterations << ',' << ray.converged << ',' << ray.time
                  << ',' << reference << ',' << ray.time - reference << ','
                  << ray.gradient << ',' << norm(ray.source - source) << ',' << seconds << '\n';
      }
  }
}
