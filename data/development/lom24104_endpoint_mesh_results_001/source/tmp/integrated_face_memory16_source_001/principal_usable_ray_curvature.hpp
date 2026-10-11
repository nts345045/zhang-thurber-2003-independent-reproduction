#pragma once
// Source-only adaptation of validated D. Include after Vec/dot and the
// candidate types. The callback is a FIXED linear principal SPD inverse,
// never a cone solve. Its arithmetic and representability checks are external.
namespace face_acceleration {
inline bool finite_curvature_vector(const Vec &values) {
  return std::all_of(values.begin(), values.end(),
                     [](double value) { return std::isfinite(value); });
}

inline bool usable_ray_curvature(const Vec &s, const Vec &y, double sy,
                                 double &reciprocal) {
  if (s.empty() || s.size() != y.size() || !finite_curvature_vector(s) ||
      !finite_curvature_vector(y) || !(sy > 0) || !std::isfinite(sy))
    return false;
  reciprocal = 1 / sy;
  return reciprocal > 0 && std::isfinite(reciprocal);
}

// The two loops, scale formula, dot products and finite checks follow D.
// A false return invalidates the proposed direction; the caller clears memory.
// A true return is not a descent, feasibility or ray-stopping certificate.
template <class PrincipalInverse>
bool usable_principal_lbfgs_direction(PrincipalInverse inverse,
                                     const Vec &gradient,
                                     const std::vector<Vec> &S,
                                     const std::vector<Vec> &Y, const Vec &rho,
                                     Vec &q) {
  q = gradient;
  if (gradient.empty() || !finite_curvature_vector(gradient) || S.size() > 16 ||
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
  double scale = 1;
  if (!S.empty()) {
    const double numerator = dot(S.back(), Y.back());
    Vec inverse_y;
    if (!(numerator > 0) || !std::isfinite(numerator) ||
        !inverse(Y.back(), inverse_y) || inverse_y.size() != q.size() ||
        !finite_curvature_vector(inverse_y))
      return false;
    const double denominator = dot(Y.back(), inverse_y);
    if (!(denominator > 0) || !std::isfinite(denominator))
      return false;
    scale = numerator / denominator;
    if (!(scale > 0) || !std::isfinite(scale))
      return false;
  }
  Vec inverse_q;
  if (!inverse(q, inverse_q) || inverse_q.size() != q.size())
    return false;
  q = std::move(inverse_q);
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
} // namespace face_acceleration
