#pragma once
Ray trace_mesh(const Grid &g, P a, P b, double spacing = 1, int maxit = 180,
          bool deriv = true, const std::vector<P> *seed = nullptr) {
  if (!(spacing > 0) || !std::isfinite(spacing))
    throw std::runtime_error("Ray spacing must be finite and positive");
  if (!g.contains(a) || !g.contains(b))
    throw std::runtime_error("Ray endpoints must lie inside the model domain");
  if (!seed || seed->size() < 2 || seed->front() != a || seed->back() != b)
    throw std::runtime_error("Explicit mesh requires its original endpoints");
  std::vector<P> p = *seed;
  for (const auto &point : p)
    if (!g.contains(point))
      throw std::runtime_error("Explicit mesh is outside the original box");
  int merged = merge_close_nodes(p), updates = 0;
  Vec grad;
  double T = path_eval(g, p, &grad);
  std::vector<Vec> S, Y;
  Vec rho;
  int iter = 0;
  bool converged = false;
  for (; iter < maxit; iter++) {
    if (projected_ray_gradient(g, p, grad) < 1e-7) {
      converged = true;
      break;
    }
    Vec q = grad, alpha(S.size());
    for (int j = int(S.size()) - 1; j >= 0; j--) {
      alpha[j] = rho[j] * dot(S[j], q);
      for (size_t k = 0; k < q.size(); k++)
        q[k] -= alpha[j] * Y[j][k];
    }
    Vec weights = ray_metric_weights(g, p);
    double scale = S.empty() ? 1 : dot(S.back(), Y.back()) /
                                      dot(Y.back(), inverse_ray_metric(weights, Y.back()));
    q = inverse_ray_metric(weights, std::move(q));
    for (auto &v : q)
      v *= scale;
    for (size_t j = 0; j < S.size(); j++) {
      double beta = rho[j] * dot(Y[j], q);
      for (size_t k = 0; k < q.size(); k++)
        q[k] += S[j][k] * (alpha[j] - beta);
    }
    for (auto &v : q)
      v = -v;
    Vec feasible_direction = q;
    project_ray_direction(g, p, feasible_direction);
    if (feasible_direction != q || !(dot(grad, q) < 0)) {
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
    double step = 1, newT = T;
    // Start with a feasible step even when a point is very close to a face.
    // Otherwise a fixed number of halvings can fail before reaching the box.
    const Vec *axes[] = {&g.x, &g.y, &g.z};
    for (size_t i = 1; i + 1 < p.size(); i++)
      for (int k = 0; k < 3; k++) {
        double d = q[3 * (i - 1) + k];
        if (d > 0)
          step = std::min(step, (axes[k]->back() - p[i][k]) / d);
        if (d < 0)
          step = std::min(step, (axes[k]->front() - p[i][k]) / d);
      }
    std::vector<P> trial;
    bool accepted = false;
    int trial_merged = 0;
    for (int ls = 0; ls < 24; ls++, step *= 0.5) {
      trial = p;
      bool valid = true;
      for (size_t i = 1; i + 1 < p.size(); i++) {
        for (int k = 0; k < 3; k++)
          trial[i][k] += step * q[3 * (i - 1) + k];
        if (!g.contains(trial[i]))
          valid = false;
      }
      if (!valid)
        continue;
      trial_merged = merge_close_nodes(trial);
      newT = path_eval(g, trial);
      if (newT <= T + 1e-4 * step * slope) {
        accepted = true;
        break;
      }
    }
    if (!accepted)
      break;
    Vec ng;
    path_eval(g, trial, &ng);
    if (trial_merged) {
      S.clear();
      Y.clear();
      rho.clear();
      merged += trial_merged;
    } else {
      Vec s(q.size()), y(q.size());
      for (size_t k = 0; k < q.size(); k++) {
        s[k] = step * q[k];
        y[k] = ng[k] - grad[k];
      }
      double sy = dot(s, y);
      if (sy > 1e-14) {
        if (S.size() == 8) {
          S.erase(S.begin());
          Y.erase(Y.begin());
          rho.erase(rho.begin());
        }
        S.push_back(s);
        Y.push_back(y);
        rho.push_back(1 / sy);
      }
    }
    p = std::move(trial);
    grad = std::move(ng);
    double change = T - newT;
    T = newT;
    updates++;
    if (change < 1e-11 && projected_ray_gradient(g, p, grad) < 1e-5) {
      converged = true;
      break;
    }
  }
  Ray r;
  r.time = T;
  r.path = p;
  r.iterations = updates;
  r.merged_nodes = merged;
  r.gradient = projected_ray_gradient(g, p, grad);
  r.raw_gradient = norm(grad);
  r.converged = converged || r.gradient < 1e-7;
  if (deriv) {
    r.dv.assign(g.size(), 0);
    r.length.assign(g.size(), 0);
    for (size_t i = 1; i < p.size(); i++) {
      P sa{}, sb{};
      segment(g, p[i - 1], p[i], &sa, &sb, &r.dv, &r.length);
      if (i == 1)
        r.source = sa;
    }
  }
  const auto nonfinite = [](double value) { return !std::isfinite(value); };
  if (!std::isfinite(r.time) || !std::isfinite(r.gradient) ||
      !std::isfinite(r.raw_gradient) ||
      std::any_of(r.source.begin(), r.source.end(), nonfinite) ||
      std::any_of(r.dv.begin(), r.dv.end(), nonfinite) ||
      std::any_of(r.length.begin(), r.length.end(), nonfinite))
    throw std::runtime_error("Nonfinite ray action, gradient or derivative");
  return r;
}