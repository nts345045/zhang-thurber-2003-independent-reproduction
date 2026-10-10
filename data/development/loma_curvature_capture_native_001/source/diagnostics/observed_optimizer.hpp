Ray observed_trace(const Grid &g, P a, P b, double spacing = 1, int maxit = 180,
          bool deriv = true, const std::vector<P> *seed = nullptr) {
  if (!(spacing > 0) || !std::isfinite(spacing))
    throw std::runtime_error("Ray spacing must be finite and positive");
  if (!g.contains(a) || !g.contains(b))
    throw std::runtime_error("Ray endpoints must lie inside the model domain");
  std::vector<P> p;
  if (seed) {
    if (seed->size() < 2 || seed->front() != a || seed->back() != b)
      throw std::runtime_error("Seeded ray must preserve both exact endpoints");
    Vec arc(seed->size(), 0);
    for (size_t i = 0; i < seed->size(); ++i) {
      if (!g.contains((*seed)[i]))
        throw std::runtime_error("Seeded ray must stay inside the model domain");
      if (i) arc[i] = arc[i-1] + norm((*seed)[i] - (*seed)[i-1]);
    }
    if (!(arc.back() > 0) || !std::isfinite(arc.back()))
      throw std::runtime_error("Seeded ray has zero or nonfinite length");
    int n = std::max(2, int(std::ceil(arc.back() / spacing)));
    p.resize(n + 1);
    size_t next = 1;
    for (int i = 1; i < n; ++i) {
      double distance = arc.back() * i / n;
      while (next + 1 < arc.size() && arc[next] <= distance) ++next;
      double fraction = (distance - arc[next-1]) / (arc[next] - arc[next-1]);
      p[i] = (*seed)[next-1] + ((*seed)[next] - (*seed)[next-1]) * fraction;
    }
  } else {
    int n = std::max(2, int(std::ceil(norm(b - a) / spacing)));
    p.resize(n + 1);
    for (int i = 1; i < n; ++i)
      p[i] = a + (b - a) * (double(i) / n);
  }
  p.front() = a;
  p.back() = b;
  int merged = merge_close_nodes(p), updates = 0;
  Vec grad;
  double T = path_eval(g, p, &grad);
  std::vector<Vec> S, Y;
  Vec rho;
  int iter = 0;
  bool converged = false;
  audit_step("initial",0,0,g,p,grad,T,NAN,NAN,NAN,NAN,nullptr,0,S.size(),false,0,false);
  curvature_begin(p);
  for (; iter < maxit; iter++) {
    int audit_searches=0;
    bool audit_reset=false,audit_curvature=false;
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
      ConeRayMetricStats metric_stats;
      q = cone_ray_direction(g, p, grad, &metric_stats);
      audit_reset=true; audit_metric(metric_stats);
      S.clear();
      Y.clear();
      rho.clear();
      curvature_memory_clear(iter,"cone_metric_fallback");
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
    const double audit_feasible_step=step;
    for (int ls = 0; ls < 24; ls++, step *= 0.5) {
      ++audit_searches;
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
    if (!accepted) {
      audit_step("line_search_failed",iter,updates,g,p,grad,T,NAN,step,audit_feasible_step,slope,&q,audit_searches,S.size(),audit_reset,0,false);
      break;
    }
    Vec ng;
    path_eval(g, trial, &ng);
    if (trial_merged) {
      S.clear();
      Y.clear();
      rho.clear();
      curvature_memory_clear(iter,"accepted_node_merge");
      merged += trial_merged;
    } else {
      Vec s(q.size()), y(q.size());
      for (size_t k = 0; k < q.size(); k++) {
        s[k] = step * q[k];
        y[k] = ng[k] - grad[k];
      }
      double sy = dot(s, y);
      if (sy > 1e-14) {
        audit_curvature=true;
        if (S.size() == 8) {
          S.erase(S.begin());
          Y.erase(Y.begin());
          rho.erase(rho.begin());
        }
        S.push_back(s);
        Y.push_back(y);
        rho.push_back(1 / sy);
      }
      curvature_pair(iter,updates+1,g,p,trial,grad,ng,q,s,y,sy,audit_curvature,
                     step,T,newT,slope,scale,S,Y);
    }
    p = std::move(trial);
    grad = std::move(ng);
    double change = T - newT;
    T = newT;
    updates++;
    audit_step("accepted",iter,updates,g,p,grad,T,change,step,audit_feasible_step,slope,&q,audit_searches,S.size(),audit_reset,trial_merged,audit_curvature);
    if (change < 1e-11 && projected_ray_gradient(g, p, grad) < 1e-5) {
      converged = true;
      break;
    }
  }
  audit_step("final",iter,updates,g,p,grad,T,NAN,NAN,NAN,NAN,nullptr,0,S.size(),false,0,false);
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