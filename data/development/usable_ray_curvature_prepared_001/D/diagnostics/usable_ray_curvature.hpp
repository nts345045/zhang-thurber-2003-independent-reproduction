#pragma once
// Diagnostic copy only. Include after Vec, dot and inverse_ray_metric.
// Keep the original arithmetic on usable states; no magnitude cutoff, floor,
// clipping, new dot product or change to the Fermat action/stopping conditions.
bool finite_curvature_vector(const Vec &values) {
  return std::all_of(values.begin(), values.end(),
                     [](double value) { return std::isfinite(value); });
}

// sy is the caller's unchanged computed dot(s,y), not an exact-sign certificate.
bool usable_ray_curvature(const Vec &s, const Vec &y, double sy,
                          double &reciprocal) {
  if (s.empty() || s.size() != y.size() || !finite_curvature_vector(s) ||
      !finite_curvature_vector(y) || !(sy > 0) || !std::isfinite(sy))
    return false;
  reciprocal = 1 / sy;
  return reciprocal > 0 && std::isfinite(reciprocal);
}

// Validate exactly the coefficient/pivot recurrence used by the existing
// inverse. Positive mathematical weights alone do not ensure representable
// sums/pivots in binary64. This check does not change the inverse arithmetic.
bool usable_curvature_metric(const Vec &weights) {
  if (weights.size() < 2)
    return false;
  for (double value : weights)
    if (!(value > 0) || !std::isfinite(value))
      return false;
  Vec diagonal(weights.size() - 1);
  for (size_t i = 0; i < diagonal.size(); i++) {
    diagonal[i] = weights[i] + weights[i + 1];
    if (!std::isfinite(diagonal[i]))
      return false;
    if (i) {
      double ratio = weights[i] / diagonal[i - 1];
      if (!std::isfinite(ratio))
        return false;
      diagonal[i] -= weights[i] * ratio;
    }
    if (!(diagonal[i] > 0) || !std::isfinite(diagonal[i]))
      return false;
  }
  return true;
}

// A false result means that the caller must use its existing cone-metric
// fallback and clear memory. It does not mean local ray convergence.
// Construct weights at their original point after the first loop. The callback
// also lets invented controls supply a declared positive-definite metric.
template <class MetricWeights>
bool usable_lbfgs_ray_direction(MetricWeights metric_weights, const Vec &gradient,
                               const std::vector<Vec> &S,
                               const std::vector<Vec> &Y, const Vec &rho,
                               Vec &q) {
  q = gradient;
  if (!finite_curvature_vector(gradient) ||
      S.size() != Y.size() || S.size() != rho.size())
    return false;
  for (size_t j = 0; j < S.size(); j++)
    if (S[j].size() != q.size() || Y[j].size() != q.size() ||
        !finite_curvature_vector(S[j]) || !finite_curvature_vector(Y[j]) ||
        !(rho[j] > 0) || !std::isfinite(rho[j]))
      return false;
  Vec alpha(S.size());
  for (int j = int(S.size()) - 1; j >= 0; j--) {
    alpha[j] = rho[j] * dot(S[j], q);
    if (!std::isfinite(alpha[j]))
      return false;
    for (size_t k = 0; k < q.size(); k++)
      q[k] -= alpha[j] * Y[j][k];
    if (!finite_curvature_vector(q))
      return false;
  }
  Vec weights = metric_weights();
  if (!usable_curvature_metric(weights) ||
      gradient.size() != 3 * (weights.size() - 1))
    return false;
  double scale = 1;
  if (!S.empty()) {
    const double numerator = dot(S.back(), Y.back());
    const Vec inverse_y = inverse_ray_metric(weights, Y.back());
    if (!(numerator > 0) || !std::isfinite(numerator) ||
        !finite_curvature_vector(inverse_y))
      return false;
    const double denominator = dot(Y.back(), inverse_y);
    if (!(denominator > 0) || !std::isfinite(denominator))
      return false;
    scale = numerator / denominator;
    if (!(scale > 0) || !std::isfinite(scale))
      return false;
  }
  q = inverse_ray_metric(weights, std::move(q));
  if (!finite_curvature_vector(q))
    return false;
  for (auto &v : q)
    v *= scale;
  if (!finite_curvature_vector(q))
    return false;
  for (size_t j = 0; j < S.size(); j++) {
    double beta = rho[j] * dot(Y[j], q);
    if (!std::isfinite(beta) || !std::isfinite(alpha[j] - beta))
      return false;
    for (size_t k = 0; k < q.size(); k++)
      q[k] += S[j][k] * (alpha[j] - beta);
    if (!finite_curvature_vector(q))
      return false;
  }
  for (auto &v : q)
    v = -v;
  return std::isfinite(dot(gradient, q));
}
