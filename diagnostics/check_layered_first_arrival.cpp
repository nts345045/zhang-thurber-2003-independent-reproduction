// Independent counterexample: a stationary direct ray need not arrive first.
// A flat upper layer overlies v(z)=v0+gradient*z for z>=0, with continuous v.
#include "../src/core.hpp"
#include <filesystem>

int main(int argc, char **argv) {
  if (argc != 2)
    throw std::runtime_error("Usage: check_layered_first_arrival OUTPUT.csv");
  constexpr double v0 = 4, gradient = 0.2, height = 0.5;
  Grid g;
  g.x = {-25, -20, -2, 0, 2, 20, 25};
  g.y = {-1, 1};
  g.z = {-1, 0, 4, 8, 12, 20};
  g.v.resize(g.size());
  for (int k = 0; k < int(g.z.size()); ++k)
    for (int j = 0; j < int(g.y.size()); ++j)
      for (int i = 0; i < int(g.x.size()); ++i)
        g.v[g.id(i, j, k)] = v0 + gradient * std::max(0., g.z[k]);
  std::ofstream f(argv[1]);
  if (!f)
    throw std::runtime_error("Cannot open audit output");
  f << std::setprecision(15)
    << "distance_km,direct_time_s,returned_time_s,returned_converged,"
       "returned_gradient_s_per_km,returned_updates,diving_time_s,"
       "diving_polyline_time_s,turning_depth_km,first_arrival_time_s,"
       "returned_first_arrival_error_s,returned_source_x_derivative,"
       "first_arrival_source_x_derivative,returned_source_z_derivative,"
       "first_arrival_source_z_derivative\n";
  for (double distance : {4., 20., 40.}) {
    const P a{-distance / 2, 0, -height}, b{distance / 2, 0, -height};
    const auto r = trace(g, a, b, 0.5, 1000);
    const double direct = distance / v0;
    double diving = NAN, polyline = NAN, turning_depth = NAN;
    double first = direct, first_dx = -1 / v0, first_dz = 0;
    // q=cot(i), where i is incidence from vertical at z=0.
    // distance/2 = height/q + (v0/gradient)*q.
    const double half = distance / 2, radius_scale = v0 / gradient;
    const double discriminant = half * half - 4 * height * radius_scale;
    if (discriminant >= 0) {
      for (int sign : {-1, 1}) {
        const double q = (half + sign * std::sqrt(discriminant)) / (2 * radius_scale);
        const double radius = radius_scale * std::sqrt(1 + q * q);
        const double depth = radius - radius_scale;
        const double time = 2 * (height * std::sqrt(1 + q * q) / (v0 * q)
                                 + std::asinh(q) / gradient);
        if (!std::isfinite(diving) || time < diving) {
          diving = time;
          turning_depth = depth;
          std::vector<P> path{a};
          const double entry_x = radius_scale * q;
          for (int n = 0; n <= 1024; ++n) {
            const double x = -entry_x + 2 * entry_x * n / 1024;
            const double z = (n == 0 || n == 1024) ? 0 :
                             std::sqrt(radius * radius - x * x) - radius_scale;
            path.push_back({x, 0, z});
          }
          path.push_back(b);
          polyline = path_eval(g, path);
          if (time < first) {
            first = time;
            first_dx = -1 / (v0 * std::sqrt(1 + q * q));
            first_dz = -q / (v0 * std::sqrt(1 + q * q));
          }
        }
      }
    }
    f << distance << ',' << direct << ',' << r.time << ',' << r.converged << ','
      << r.gradient << ',' << r.iterations << ',' << diving << ',' << polyline << ','
      << turning_depth << ',' << first << ',' << r.time - first << ','
      << r.source[0] << ',' << first_dx << ',' << r.source[2] << ',' << first_dz << '\n';
  }
}
