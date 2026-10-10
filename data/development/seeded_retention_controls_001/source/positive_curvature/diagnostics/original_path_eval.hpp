double original_path_eval(const Grid &g, const std::vector<P> &p, Vec *grad = nullptr) {
  if (grad)
    grad->assign(3 * (p.size() - 2), 0);
  double T = 0;
  for (size_t i = 1; i < p.size(); i++) {
    P a{}, b{};
    T += segment(g, p[i - 1], p[i], grad ? &a : nullptr, grad ? &b : nullptr);
    if (grad)
      for (int k = 0; k < 3; k++) {
        if (i > 1)
          (*grad)[3 * (i - 2) + k] += a[k];
        if (i + 1 < p.size())
          (*grad)[3 * (i - 1) + k] += b[k];
      }
  }
  return T;
}