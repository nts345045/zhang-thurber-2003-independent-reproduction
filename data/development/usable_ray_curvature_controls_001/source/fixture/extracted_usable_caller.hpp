// Byte-extracted D caller blocks; no Ray or convergence claim.
Vec fixture_actual_direction(const Grid &g,const std::vector<P> &p,const Vec &grad,
    std::vector<Vec> &S,std::vector<Vec> &Y,Vec &rho) {
    Vec q;
    const bool usable_memory = usable_lbfgs_ray_direction(
        [&] { return ray_metric_weights(g, p); }, grad, S, Y, rho, q);
    Vec feasible_direction = q;
    project_ray_direction(g, p, feasible_direction);
    if (!usable_memory || feasible_direction != q || !(dot(grad, q) < 0)) {
      q = cone_ray_direction(g, p, grad);
      S.clear();
      Y.clear();
      rho.clear();
    }
    double slope = dot(grad, q);
    Vec check_feasible = q;
    project_ray_direction(g, p, check_feasible);
    if (!std::isfinite(slope) ||
        std::any_of(q.begin(), q.end(), [](double value) { return !std::isfinite(value); }) ||
        check_feasible != q || !(slope < 0))
      throw std::runtime_error("Hybrid ray direction is not feasible strict descent");
  return q;
}
void fixture_actual_admission(const Vec &s,const Vec &y,
    std::vector<Vec> &S,std::vector<Vec> &Y,Vec &rho) {
      double sy = dot(s, y);
      double reciprocal = 0;
      if (usable_ray_curvature(s, y, sy, reciprocal)) {
        if (S.size() == 8) {
          S.erase(S.begin());
          Y.erase(Y.begin());
          rho.erase(rho.begin());
        }
        S.push_back(s);
        Y.push_back(y);
        rho.push_back(reciprocal);
      }
}
