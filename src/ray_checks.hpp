#pragma once
#include "core.hpp"

struct SnellReference {
  double transverse_slowness, time;
  P source;
};
// Independent monotone-x reference for endpoints (-10,-20,8) and (20,15,0).
// In an x-only medium, p is the conserved transverse slowness. For each
// constant/linear velocity segment we integrate exactly:
// R = integral p*v/sqrt(1-p*p*v*v) dx,
// T = integral 1/(v*sqrt(1-p*p*v*v)) dx.
// Bisection matches R to hypot(35,8); Fermat's endpoint derivative then gives
// the source slowness vector. No numerical ray path enters this reference.
SnellReference sandwich_snell_reference() {
  const std::array<double, 3> sections[] = {
      {10, 6, 6}, {1, 6, 4}, {4, 4, 4}, {1, 4, 5}, {14, 5, 5 + 14. / 32}};
  auto integrals = [&](double p) {
    std::array<double, 2> total{};
    for (auto section : sections) {
      double length = section[0], v0 = section[1], v1 = section[2],
             c0 = std::sqrt(1 - p * p * v0 * v0),
             c1 = std::sqrt(1 - p * p * v1 * v1);
      if (v0 == v1) {
        total[0] += length * p * v0 / c0;
        total[1] += length / (v0 * c0);
      } else {
        double slope = (v1 - v0) / length;
        total[0] += (c0 - c1) / (p * slope);
        total[1] += std::log(v1 * (1 + c0) / (v0 * (1 + c1))) / slope;
      }
    }
    return total;
  };
  double distance = std::hypot(35., 8.), lo = 0, hi = (1 - 1e-12) / 6;
  for (int i = 0; i < 90; i++) {
    double p = (lo + hi) / 2;
    if (integrals(p)[0] < distance)
      lo = p;
    else
      hi = p;
  }
  double p = (lo + hi) / 2;
  return {p, integrals(p)[1],
          {-std::sqrt(1. / 36 - p * p), -p * 35 / distance, p * 8 / distance}};
}

// Regressions for numerical defects found during independent code review.
// The callback has the same (name, error, tolerance) interface as validate().
template <class Check> void run_ray_checks(Check check) {
  Grid invariant = grid(true);
  for (int axis = 0; axis < 3; axis++) {
    int u = (axis + 1) % 3, v = (axis + 2) % 3;
    for (int k = 0; k < int(invariant.z.size()); k++)
      for (int j = 0; j < int(invariant.y.size()); j++)
        for (int i = 0; i < int(invariant.x.size()); i++) {
          P p{invariant.x[i], invariant.y[j], invariant.z[k]};
          invariant.v[invariant.id(i, j, k)] =
              5 + 0.017 * p[u] + 0.009 * p[v] + 0.0001 * p[u] * p[v];
        }
    double symmetry_error = 0;
    for (size_t k = 0; k + 1 < invariant.z.size(); k++)
      for (size_t j = 0; j + 1 < invariant.y.size(); j++)
        for (size_t i = 0; i + 1 < invariant.x.size(); i++) {
          P p{invariant.x[i] + 0.317 * (invariant.x[i + 1] - invariant.x[i]),
              invariant.y[j] + 0.413 * (invariant.y[j + 1] - invariant.y[j]),
              invariant.z[k] + 0.271 * (invariant.z[k + 1] - invariant.z[k])};
          symmetry_error = std::max(symmetry_error,
                                    std::abs(invariant.sample(p).grad[axis]));
        }
    check(std::string("interpolation_constant_") + "xyz"[axis] + "_symmetry",
          symmetry_error, 0);
  }
  // Independent synthetic endpoints exposed out-of-plane drift caused by
  // roundoff gradients. A depth-invariant medium and surface endpoints must
  // preserve z=0; no physical depth constraint is added to the algorithm.
  set_true(invariant);
  Ray planar = trace(invariant, {-9.49217059051, -1.36168655867, 0},
                     {2.56074625155, 16.0645085136, 0}, 1, 180);
  double plane_error = 0;
  for (auto p : planar.path)
    plane_error = std::max(plane_error, std::abs(p[2]));
  check("surface_ray_plane_symmetry", plane_error, 0);
  check("surface_ray_source_symmetry", std::abs(planar.source[2]), 0);
  auto reference = sandwich_snell_reference();
  auto reference_ray = trace(invariant, {-10, -20, 8}, {20, 15, 0}, 0.6, 2000);
  check("snell_reference_travel_time",
        std::abs(reference_ray.time - reference.time), 1e-3);
  check("snell_reference_source_derivative",
        norm(reference_ray.source - reference.source), 1e-4);
  for (int k = 0; k < int(invariant.z.size()); k++)
    for (int j = 0; j < int(invariant.y.size()); j++)
      for (int i = 0; i < int(invariant.x.size()); i++)
        invariant.v[invariant.id(i, j, k)] =
            5 + 0.017 * invariant.x[i] - 0.013 * invariant.y[j] +
            0.019 * invariant.z[k] +
            0.00001 * invariant.x[i] * invariant.y[j] * invariant.z[k];
  P point{3.173, -7.193, 5.171}, fd{};
  double difference_step = 1e-4;
  for (int axis = 0; axis < 3; axis++) {
    P plus = point, minus = point;
    plus[axis] += difference_step;
    minus[axis] -= difference_step;
    fd[axis] = (invariant.sample(plus).v - invariant.sample(minus).v) /
               (2 * difference_step);
  }
  check("trilinear_gradient_finite_difference",
        norm(invariant.sample(point).grad - fd), 2e-10);

  // A segment crossing moving grid cuts exposed inadequate two-point
  // quadrature. Check the integral against its exact piecewise-linear value,
  // and both endpoint gradients against finite differences of that integral.
  auto endpoint_error = [](const Grid &model, P a, P b) {
    P ga{}, gb{};
    segment(model, a, b, &ga, &gb);
    double error = 0, h = 1e-5;
    for (int end = 0; end < 2; end++)
      for (int axis = 0; axis < 3; axis++) {
        P ap = a, am = a, bp = b, bm = b;
        (end ? bp : ap)[axis] += h;
        (end ? bm : am)[axis] -= h;
        double fd = (segment(model, ap, bp) - segment(model, am, bm)) / (2 * h);
        error = std::max(error, std::abs((end ? gb : ga)[axis] - fd));
      }
    return error;
  };
  Grid crossing = grid(true);
  set_true(crossing);
  P ca{-0.5, 0, 1}, cb{1.5, 1, 1};
  double exact_segment = std::sqrt(5.) / 2 *
                         (0.5 / 6 + std::log(6. / 4) / 2 + 0.5 / 4);
  check("crossing_segment_exact_time",
        std::abs(segment(crossing, ca, cb) - exact_segment), 1e-12);
  check("crossing_segment_endpoint_gradients", endpoint_error(crossing, ca, cb),
        2e-10);
  for (int k = 0; k < int(crossing.z.size()); k++)
    for (int j = 0; j < int(crossing.y.size()); j++)
      for (int i = 0; i < int(crossing.x.size()); i++)
        crossing.v[crossing.id(i, j, k)] =
            5 + 0.8 * std::sin(0.25 * crossing.x[i]) +
            0.5 * std::cos(0.11 * crossing.y[j]) + 0.02 * crossing.z[k] +
            0.0001 * crossing.x[i] * crossing.y[j] * crossing.z[k];
  check("three_dimensional_segment_endpoint_gradients",
        endpoint_error(crossing, {-0.5, -2, 2.5}, {6.5, 12, 10.5}), 1e-9);

  Vec metric_weights{0.4, 2, 0.7, 3, 0.9, 1.7}, rhs(15), other(15);
  for (int i = 0; i < 15; i++) {
    rhs[i] = std::cos(i + 0.3);
    other[i] = std::sin(0.7 * i + 0.2);
  }
  Vec metric_solution = inverse_ray_metric(metric_weights, rhs), residual(15);
  for (int i = 0; i < 5; i++)
    for (int axis = 0; axis < 3; axis++) {
      int index = 3 * i + axis;
      residual[index] = (metric_weights[i] + metric_weights[i + 1]) *
                            metric_solution[index] - rhs[index];
      if (i)
        residual[index] -= metric_weights[i] * metric_solution[index - 3];
      if (i < 4)
        residual[index] -= metric_weights[i + 1] * metric_solution[index + 3];
    }
  check("ray_metric_linear_system", norm(residual) / norm(rhs), 1e-12);
  check("ray_metric_symmetry",
        std::abs(dot(other, metric_solution) -
                 dot(rhs, inverse_ray_metric(metric_weights, other))), 1e-12);
  check("ray_metric_positive_definite", dot(rhs, metric_solution) > 0 ? 0. : 1., 0);

  // Independent smooth-gradient reference: the continuous ray is a circular
  // arc in v(z)=5+0.2*z. Test stationarity at fixed spacing separately from
  // second-order convergence of the polygonal approximation as spacing halves.
  Grid affine = grid();
  for (int k = 0; k < int(affine.z.size()); k++)
    for (int j = 0; j < int(affine.y.size()); j++)
      for (int i = 0; i < int(affine.x.size()); i++)
        affine.v[affine.id(i, j, k)] = 5 + 0.2 * affine.z[k];
  double exact_time = 10 * std::asinh(0.8), previous_error = 0;
  double radius = std::hypot(25., 20.);
  P exact_source{-1 / (0.2 * radius), 0, -4 / radius};
  for (double spacing : {1., 0.5, 0.25}) {
    Ray arc = trace(affine, {-20, 0, 0}, {20, 0, 0}, spacing, 180);
    std::string label = "affine_ray_" + std::to_string(spacing);
    check(label + "_converged", arc.converged ? 0. : 1., 0);
    check(label + "_stationarity", arc.gradient, 1e-5);
    double error = std::abs(arc.time - exact_time);
    if (previous_error)
      check(label + "_refinement_ratio", error / previous_error, 0.3);
    previous_error = error;
    if (spacing == 0.25) {
      check(label + "_exact_time", error, 2.5e-5);
      check(label + "_source_derivative", norm(arc.source - exact_source), 3e-6);
    }
  }

  Grid g = grid();
  for (int k = 0; k < int(g.z.size()); k++)
    for (int j = 0; j < int(g.y.size()); j++)
      for (int i = 0; i < int(g.x.size()); i++)
        g.v[g.id(i, j, k)] = 6 + 0.03 * g.y[j] - 0.02 * g.z[k];
  P a{-10, -20, 0}, b{20, 15, 0};
  // Velocity decreases with depth. The optimum stays at the surface but must
  // bend laterally. Rejecting the entire outward direction incorrectly leaves
  // the initial straight ray unchanged; this explicitly feasible step is faster.
  Ray straight = trace(g, a, b, 1, 0);
  auto feasible = straight.path;
  Vec grad;
  path_eval(g, feasible, &grad);
  for (size_t i = 1; i + 1 < feasible.size(); i++) {
    feasible[i][0] -= 100 * grad[3 * (i - 1)];
    feasible[i][1] -= 100 * grad[3 * (i - 1) + 1];
  }
  Ray surface = trace(g, a, b, 1, 600);
  check("boundary_ray_feasible_descent",
        std::max(0., surface.time - path_eval(g, feasible)), 1e-10);
  check("boundary_ray_projected_gradient", surface.gradient, 1e-5);
  double outside = 0;
  for (auto p : surface.path)
    outside += !g.contains(p);
  check("boundary_ray_domain", outside, 0);

  std::vector<P> p{{0, 0, 1}, {1e-10, 0, 1}, {1, 0, 1},
                   {2 - 1e-10, 0, 1}, {2, 0, 1}};
  int removed = merge_close_nodes(p);
  check("collapsed_vertices_preserve_endpoints",
        norm(p.front() - P{0, 0, 1}) + norm(p.back() - P{2, 0, 1}) +
            std::abs(removed - 2) + std::abs(int(p.size()) - 3),
        0);

  // These endpoints are from our independent seed-2003 synthetic geometry.
  // The old optimizer collapsed an internal segment below 1e-12 km, then
  // stopped at a spurious 0.292 s/km gradient. No published coordinates enter.
  g = grid(true);
  set_true(g);
  a = {23.1626581174, 23.6663612979, 11.0369729223};
  b = {-9.7715156299, 2.61303326716, 0};
  Ray merged = trace(g, a, b, 0.5, 1000);
  double minimum = norm(a - b);
  for (size_t i = 1; i < merged.path.size(); i++)
    minimum = std::min(minimum, norm(merged.path[i] - merged.path[i - 1]));
  check("collapsed_ray_minimum_segment", std::max(0., 1e-8 - minimum), 0);
  // This is a regression tolerance, not the ray convergence criterion. The
  // recorded Ray::converged flag remains false if its tighter criterion fails.
  check("collapsed_ray_gradient_regression", merged.gradient, 1e-3);

  Matrix A(2);
  A.add({{0, 1}}, 2);
  A.add({{1, 3}}, -3);
  LSQRInfo info;
  Vec x = solve(A, 0.5, &info);
  // Columns are normalized before damping, so the analytic result is
  // x_j = (b_j / A_jj) / (1 + damping^2).
  check("scaled_damped_lsqr_solution", norm(Vec{x[0] - 1.6, x[1] + 0.8}),
        1e-10);
  check("scaled_damped_lsqr_normal_residual", info.relative_normal_residual,
        1e-8);
  check("scaled_damped_lsqr_converged", info.converged ? 0. : 1., 0);
  A.rhs.assign(2, 0);
  x = lsqr(A, 10, 1e-9, &info);
  check("zero_rhs_lsqr", norm(x) + (info.converged ? 0 : 1) + info.iterations,
        0);
  Matrix B(3);
  B.add({{0, 1}}, 1);
  B.add({{1, 2}}, 1);
  B.add({{2, 4}}, 1);
  lsqr(B, 1, 1e-12, &info);
  check("truncated_lsqr_not_converged",
        (info.converged ? 1 : 0) + std::abs(info.iterations - 1) +
            (info.relative_normal_residual > 1e-12 ? 0 : 1),
        0);
}
