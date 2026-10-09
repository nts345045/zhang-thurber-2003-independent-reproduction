#include "../src/ray_checks.hpp"

// Optional diagnostic, independent of the main rebuild. Compare retraced
// finite differences with the ray endpoint derivative and the analytic Snell
// reference while varying source perturbation and ray iteration limit.
int main(int argc, char **argv) {
  if (argc != 2) {
    std::cerr << "Usage: source_step_sweep OUTPUT.csv\n";
    return 1;
  }
  std::ofstream f(argv[1]);
  if (!f) {
    std::cerr << "Cannot write " << argv[1] << '\n';
    return 1;
  }
  f << std::setprecision(17);
  f << "ray_iteration_limit,base_iterations,base_time_seconds,"
       "base_time_error_seconds,base_projected_gradient,source_dx,source_dy,"
       "source_dz,source_reference_error,source_step_km,fd_dx,fd_dy,fd_dz,"
       "fd_vs_ray_max_error,fd_vs_reference_max_error,"
       "max_perturbed_projected_gradient,reference_time_seconds,"
       "reference_source_dx,reference_source_dy,reference_source_dz,"
       "reference_transverse_slowness\n";
  Grid g = grid(true);
  set_true(g);
  P a{-10, -20, 8}, b{20, 15, 0};
  auto reference = sandwich_snell_reference();
  for (int iterations : {600, 2000, 10000}) {
    Ray base = trace(g, a, b, 0.6, iterations);
    for (double h : {0.1, 0.03, 0.01, 0.001}) {
      P fd{};
      double ray_error = 0, reference_error = 0, maximum_gradient = 0;
      for (int axis = 0; axis < 3; axis++) {
        P plus = a, minus = a;
        plus[axis] += h;
        minus[axis] -= h;
        Ray rp = trace(g, plus, b, 0.6, iterations, false);
        Ray rm = trace(g, minus, b, 0.6, iterations, false);
        fd[axis] = (rp.time - rm.time) / (2 * h);
        ray_error = std::max(ray_error, std::abs(fd[axis] - base.source[axis]));
        reference_error =
            std::max(reference_error, std::abs(fd[axis] - reference.source[axis]));
        maximum_gradient =
            std::max(maximum_gradient, std::max(rp.gradient, rm.gradient));
      }
      f << iterations << ',' << base.iterations << ',' << base.time << ','
        << base.time - reference.time << ',' << base.gradient << ','
        << base.source[0] << ',' << base.source[1] << ',' << base.source[2]
        << ',' << norm(base.source - reference.source) << ',' << h << ','
        << fd[0] << ',' << fd[1] << ',' << fd[2] << ',' << ray_error << ','
        << reference_error << ',' << maximum_gradient << ',' << reference.time
        << ',' << reference.source[0] << ',' << reference.source[1] << ','
        << reference.source[2] << ',' << reference.transverse_slowness << '\n';
    }
    f.flush();
  }
  return f ? 0 : 1;
}
