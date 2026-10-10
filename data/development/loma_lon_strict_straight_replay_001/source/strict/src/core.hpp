#pragma once
#include "ray_metric.hpp"
#include <algorithm>
#include <array>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <numeric>
#include <random>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
using P = std::array<double, 3>;
P operator+(P a, P b) {
  for (int i = 0; i < 3; i++)
    a[i] += b[i];
  return a;
}
P operator-(P a, P b) {
  for (int i = 0; i < 3; i++)
    a[i] -= b[i];
  return a;
}
P operator*(P a, double b) {
  for (auto &x : a)
    x *= b;
  return a;
}
double dot(P a, P b) { return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]; }
double norm(P a) { return std::sqrt(dot(a, a)); }
double dot(const Vec &a, const Vec &b) {
  return std::inner_product(a.begin(), a.end(), b.begin(), 0.0);
}
double norm(const Vec &a) { return std::sqrt(dot(a, a)); }
struct Config {
  std::map<std::string, double> v;
  explicit Config(const std::string &path) {
    std::ifstream f(path);
    if (!f)
      throw std::runtime_error("Cannot open " + path);
    std::string l, k;
    double x;
    while (std::getline(f, l)) {
      std::istringstream s(l);
      if (s >> k >> x)
        v[k] = x;
    }
  }
  double get(std::string k) const { return v.at(k); }
};
struct Grid {
  Vec x, y, z, v;
  int id(int i, int j, int k) const {
    return (k * y.size() + j) * x.size() + i;
  }
  int size() const { return x.size() * y.size() * z.size(); }
  struct Sample {
    double v = 0;
    P grad{};
    std::array<int, 8> ids{};
    std::array<double, 8> w{};
  };
  Sample sample(P p) const {
    const Vec *axes[] = {&x, &y, &z};
    int ii[3];
    double t[3], h[3];
    for (int a = 0; a < 3; a++) {
      const auto &q = *axes[a];
      ii[a] = std::clamp(
          int(std::upper_bound(q.begin(), q.end(), p[a]) - q.begin()) - 1, 0,
          int(q.size()) - 2);
      h[a] = q[ii[a] + 1] - q[ii[a]];
      t[a] = (p[a] - q[ii[a]]) / h[a];
    }
    Sample s;
    int n = 0;
    for (int c = 0; c < 2; c++)
      for (int b = 0; b < 2; b++)
        for (int a = 0; a < 2; a++, n++) {
          int bits[] = {a, b, c};
          double w[3];
          for (int d = 0; d < 3; d++)
            w[d] = bits[d] ? t[d] : 1 - t[d];
          s.ids[n] = id(ii[0] + a, ii[1] + b, ii[2] + c);
          s.w[n] = w[0] * w[1] * w[2];
          double vel = v[s.ids[n]];
          s.v += s.w[n] * vel;
        }
    // Differentiate by paired nodal differences. This is algebraically the
    // same trilinear gradient, but preserves a constant-axis field exactly.
    // Signed sums of eight velocities leave roundoff gradients that L-BFGS
    // and column normalization can amplify in nearly unobservable directions.
    for (int d = 0; d < 3; d++) {
      int u = (d + 1) % 3, vaxis = (d + 2) % 3;
      for (int a = 0; a < 2; a++)
        for (int b = 0; b < 2; b++) {
          int q[3] = {ii[0], ii[1], ii[2]};
          q[u] += a;
          q[vaxis] += b;
          int lo = id(q[0], q[1], q[2]);
          q[d]++;
          int hi = id(q[0], q[1], q[2]);
          s.grad[d] += (v[hi] - v[lo]) / h[d] *
                       (a ? t[u] : 1 - t[u]) *
                       (b ? t[vaxis] : 1 - t[vaxis]);
        }
    }
    return s;
  }
  bool contains(P p, double pad = 0) const {
    return p[0] >= x.front() + pad && p[0] <= x.back() - pad &&
           p[1] >= y.front() + pad && p[1] <= y.back() - pad &&
           p[2] >= z.front() + pad && p[2] <= z.back() - pad;
  }
};
double sandwich(double x) {
  if (x <= 0)
    return 6;
  if (x < 1)
    return 6 - 2 * x;
  if (x <= 5)
    return 4;
  if (x < 6)
    return x - 1;
  if (x < 38)
    return 5 + (x - 6) / 32;
  return 6;
}
Grid grid(bool fine = false) {
  Grid g;
  g.x = fine ? Vec{-35, -15, 0, 1, 2, 4, 5, 6, 20, 35}
             : Vec{-35, -15, 0, 2, 4, 6, 20, 35};
  g.y = {-60, -40, -20, 0, 20, 40};
  g.z = {0, 3, 7, 11, 16};
  g.v.resize(g.size(), 5.5);
  return g;
}
void set_true(Grid &g) {
  for (int k = 0; k < int(g.z.size()); k++)
    for (int j = 0; j < int(g.y.size()); j++)
      for (int i = 0; i < int(g.x.size()); i++)
        g.v[g.id(i, j, k)] = sandwich(g.x[i]);
}
struct Ray {
  double time = 0;
  Vec dv, length;
  P source{};
  std::vector<P> path;
  int iterations = 0;
  int merged_nodes = 0;
  double gradient = 0;
  double raw_gradient = 0;
  bool converged = false;
  bool initialization_attempted = false;
  bool initialization_succeeded = false;
  bool selected_fmm_seed = false;
  double direct_seed_time = NAN;
  double fmm_seed_time = NAN;
  double initializer_field_time = NAN;
  int initializer_fallback_steps = 0;
  std::string initializer_message;
};
// Eight-point Gauss integration on each piece split at grid-plane intersections.
// Both travel time and its continuous variational derivatives must be accurately
// integrated: inaccurate moving-cut quadrature otherwise gives inconsistent
// objective/gradient pairs even when the variational formula is correct.
double segment(const Grid &g, P a, P b, P *ga = nullptr, P *gb = nullptr,
               Vec *dv = nullptr, Vec *length = nullptr) {
  P d = b - a;
  double L = norm(d);
  if (L < 1e-12)
    return 0;
  Vec cuts{0, 1};
  const Vec *axes[] = {&g.x, &g.y, &g.z};
  for (int k = 0; k < 3; k++)
    if (std::abs(d[k]) > 1e-12)
      for (double q : *axes[k]) {
        double t = (q - a[k]) / d[k];
        if (t > 1e-10 && t < 1 - 1e-10)
          cuts.push_back(t);
      }
  std::sort(cuts.begin(), cuts.end());
  double T = 0;
  for (size_t j = 1; j < cuts.size(); j++) {
    double mid = (cuts[j] + cuts[j - 1]) / 2,
           half = (cuts[j] - cuts[j - 1]) / 2;
    static constexpr double nodes[] = {0.1834346424956498, 0.5255324099163290,
                                      0.7966664774136267, 0.9602898564975363};
    static constexpr double weights[] = {0.3626837833783620, 0.3137066458778873,
                                        0.2223810344533745, 0.1012285362903763};
    for (int point = 0; point < 4; point++)
      for (double sign : {-1., 1.}) {
        double t = mid + sign * half * nodes[point];
        auto s = g.sample(a + d * t);
        double u = 1 / s.v, weight = half * weights[point];
        T += L * weight * u;
        P grad = s.grad * (-u * u);
        if (ga)
          *ga = *ga + (d * (-u / L) + grad * (L * (1 - t))) * weight;
        if (gb)
          *gb = *gb + (d * (u / L) + grad * (L * t)) * weight;
        if (dv)
          for (int m = 0; m < 8; m++)
            (*dv)[s.ids[m]] -= L * weight * s.w[m] * u * u;
        if (length)
          for (int m = 0; m < 8; m++)
            (*length)[s.ids[m]] += L * weight * s.w[m];
      }
  }
  return T;
}
double path_eval(const Grid &g, const std::vector<P> &p, Vec *grad = nullptr) {
  if (grad)
    grad->assign(3 * (p.size() - 2), 0);
  long double T = 0;
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
// Remove a redundant internal vertex if its adjacent segment is below 1e-8 km
// (10 micrometres). This purely numerical tolerance is far below the ray spacing.
// Endpoints are never moved or removed. Without merging, the nondifferentiable
// zero-length limit can stall optimization and give spurious endpoint gradients.
int merge_close_nodes(std::vector<P> &p, double tolerance = 1e-8) {
  int removed = 0;
  for (size_t i = 1; i < p.size() && p.size() > 2;) {
    if (norm(p[i] - p[i - 1]) < tolerance) {
      size_t erase = i + 1 < p.size() ? i : i - 1;
      p.erase(p.begin() + erase);
      removed++;
      i = erase > 1 ? erase - 1 : 1;
    } else {
      i++;
    }
  }
  return removed;
}
// At an active domain face, remove only components that point out of the box.
// The 1e-10 km activity tolerance prevents roundoff-sized distances from blocking
// every feasible tangential step. Interior steps still use domain backtracking.
void project_ray_direction(const Grid &g, const std::vector<P> &p, Vec &d) {
  const Vec *axes[] = {&g.x, &g.y, &g.z};
  for (size_t i = 1; i + 1 < p.size(); i++)
    for (int k = 0; k < 3; k++) {
      double &q = d[3 * (i - 1) + k];
      if ((p[i][k] <= axes[k]->front() + 1e-10 && q < 0) ||
          (p[i][k] >= axes[k]->back() - 1e-10 && q > 0))
        q = 0;
    }
}
double projected_ray_gradient(const Grid &g, const std::vector<P> &p,
                              const Vec &grad) {
  Vec d = grad;
  for (auto &q : d)
    q = -q;
  project_ray_direction(g, p, d);
  return norm(d);
}
// Midpoint slowness / segment length approximates the transverse stiffness
// of a straight ray. The corresponding fixed-endpoint weighted Laplacian is
// positive definite. Its inverse is a search metric, not a smoothing penalty:
// it changes neither Fermat travel time nor the set of admissible paths.
Vec ray_metric_weights(const Grid &g, const std::vector<P> &p) {
  Vec weights(p.size() - 1);
  for (size_t i = 0; i < weights.size(); i++)
    weights[i] = 1 / (g.sample((p[i] + p[i + 1]) * 0.5).v *
                      norm(p[i + 1] - p[i]));
  return weights;
}
Vec inverse_ray_metric(const Vec &weights, Vec rhs) {
  size_t n = weights.size() - 1;
  Vec diagonal(n);
  for (size_t i = 0; i < n; i++) {
    diagonal[i] = weights[i] + weights[i + 1];
    if (i) {
      double ratio = weights[i] / diagonal[i - 1];
      diagonal[i] -= weights[i] * ratio;
      for (int axis = 0; axis < 3; axis++)
        rhs[3 * i + axis] += ratio * rhs[3 * (i - 1) + axis];
    }
  }
  for (size_t i = n; i-- > 0;)
    for (int axis = 0; axis < 3; axis++) {
      if (i + 1 < n)
        rhs[3 * i + axis] += weights[i + 1] * rhs[3 * (i + 1) + axis];
      rhs[3 * i + axis] /= diagonal[i];
    }
  return rhs;
}
Vec cone_ray_direction(const Grid &g,const std::vector<P> &path,const Vec &gradient,
                       ConeRayMetricStats *record=nullptr) {
  std::vector<int> sign(gradient.size());
  const Vec *axes[]={&g.x,&g.y,&g.z};
  for(std::size_t i=1;i+1<path.size();++i)for(int axis=0;axis<3;++axis) {
    const std::size_t k=3*(i-1)+axis;
    if(path[i][axis]<=axes[axis]->front()+1e-10)sign[k]=1;
    else if(path[i][axis]>=axes[axis]->back()-1e-10)sign[k]=-1;
  }
  ConeRayMetricStats stats;
  auto direction=solve_cone_ray_metric(ray_metric_weights(g,path),gradient,sign,stats);
  if(record)*record=stats;
  if(!stats.success)throw std::runtime_error(stats.message);
  const bool nonzero=std::any_of(direction.begin(),direction.end(),[](double value){return value!=0;});
  if((nonzero&&!(stats.slope<0))||(!nonzero&&projected_ray_gradient(g,path,gradient)>0))
    throw std::runtime_error("Cone metric lacks a strict descent direction for a nonstationary ray");
  return direction;
}

#include "usable_ray_curvature.hpp"

// Independently implemented limited-memory BFGS minimization of Fermat travel
// time. Retain feasible descent directions; replace clipped or non-descent
// directions with the tangent-cone metric minimizer. Trial paths outside the
// model are rejected, with fixed endpoints and unchanged Armijo/stopping rules.
Ray trace(const Grid &g, P a, P b, double spacing = 1, int maxit = 180,
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
  for (; iter < maxit; iter++) {
    if (projected_ray_gradient(g, p, grad) < 1e-7) {
      converged = true;
      break;
    }
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
    p = std::move(trial);
    grad = std::move(ng);
    double change = T - newT;
    T = newT;
    updates++;
    if (false && change < 1e-11 && projected_ray_gradient(g, p, grad) < 1e-5) {
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
struct Entry {
  int col;
  double val;
};
using Row = std::vector<Entry>;
// Ordered CSR: preserve duplicate entries and their insertion order. In
// particular, solve's per-entry squared column norms must not coalesce them.
struct Matrix {
  int n;
  std::vector<size_t> offsets{0};
  std::vector<int> columns;
  Vec values, rhs;
  explicit Matrix(int n) : n(n) {}
  static size_t storage_bytes(size_t rows, size_t entries) {
    const size_t limit = std::numeric_limits<size_t>::max();
    if (rows == limit || rows + 1 > limit / sizeof(size_t) ||
        rows > limit / sizeof(double) ||
        entries > limit / (sizeof(int) + sizeof(double)))
      throw std::runtime_error("CSR storage size overflow");
    size_t a = (rows + 1) * sizeof(size_t), b = rows * sizeof(double),
           c = entries * (sizeof(int) + sizeof(double));
    if (a > limit - b || a + b > limit - c)
      throw std::runtime_error("CSR storage size overflow");
    return a + b + c;
  }
  void reserve(size_t rows, size_t entries) {
    storage_bytes(rows, entries);
    if (rows >= offsets.max_size() || rows > rhs.max_size() ||
        entries > columns.max_size() || entries > values.max_size())
      throw std::runtime_error("CSR allocation exceeds vector capacity");
    offsets.reserve(rows + 1);
    rhs.reserve(rows);
    columns.reserve(entries);
    values.reserve(entries);
  }
  void add(const Row &row, double b, double w = 1) {
    for (const auto &e : row) {
      columns.push_back(e.col);
      values.push_back(e.val * w);
    }
    offsets.push_back(values.size());
    rhs.push_back(b * w);
  }
  Vec mul(const Vec &x) const {
    Vec y(rhs.size());
    for (size_t i = 0; i < rhs.size(); i++)
      for (size_t q = offsets[i]; q < offsets[i + 1]; ++q)
        y[i] += values[q] * x[columns[q]];
    return y;
  }
  Vec trans(const Vec &y) const {
    Vec x(n);
    for (size_t i = 0; i < rhs.size(); i++)
      for (size_t q = offsets[i]; q < offsets[i + 1]; ++q)
        x[columns[q]] += values[q] * y[i];
    return x;
  }
};

struct LSQRInfo {
  int iterations = 0;
  double relative_normal_residual = 0;
  bool converged = false;
};
// Golub-Kahan bidiagonalization and orthogonal rotations, no normal equations.
// Diagnostics refer to the supplied matrix (including scaled damping rows when
// called by solve), and use ||A^T(Ax-b)|| / ||A^T b|| as the stopping measure.
Vec lsqr(const Matrix &A, int maxit, double tol = 1e-9,
         LSQRInfo *info = nullptr) {
  Vec x(A.n), u = A.rhs;
  double initial = norm(A.trans(A.rhs));
  int iterations = 0;
  auto finish = [&]() {
    if (info) {
      Vec residual = A.mul(x);
      for (size_t i = 0; i < residual.size(); i++)
        residual[i] -= A.rhs[i];
      double normal = norm(A.trans(residual));
      info->iterations = iterations;
      info->relative_normal_residual = initial > 0 ? normal / initial : normal;
      info->converged = std::isfinite(info->relative_normal_residual) &&
                        info->relative_normal_residual <= tol;
    }
    return x;
  };
  double beta = norm(u);
  if (beta == 0)
    return finish();
  for (auto &v : u)
    v /= beta;
  Vec v = A.trans(u);
  double alpha = norm(v);
  if (alpha == 0)
    return finish();
  for (auto &q : v)
    q /= alpha;
  Vec w = v;
  double phibar = beta, rhobar = alpha;
  for (int it = 0; it < maxit; it++) {
    Vec nu = A.mul(v);
    for (size_t i = 0; i < u.size(); i++)
      nu[i] -= alpha * u[i];
    beta = norm(nu);
    u = std::move(nu);
    if (beta > 0)
      for (auto &q : u)
        q /= beta;
    Vec nv = A.trans(u);
    for (size_t i = 0; i < v.size(); i++)
      nv[i] -= beta * v[i];
    alpha = norm(nv);
    v = std::move(nv);
    if (alpha > 0)
      for (auto &q : v)
        q /= alpha;
    double rho = std::hypot(rhobar, beta);
    if (rho == 0)
      break;
    double c = rhobar / rho, s = beta / rho,
           theta = s * alpha;
    rhobar = -c * alpha;
    double phi = c * phibar;
    phibar = s * phibar;
    for (int i = 0; i < A.n; i++) {
      x[i] += (phi / rho) * w[i];
      w[i] = v[i] - (theta / rho) * w[i];
    }
    iterations++;
    if (it % 20 == 19 || alpha == 0) {
      Vec residual = A.mul(x);
      for (size_t i = 0; i < residual.size(); i++)
        residual[i] -= A.rhs[i];
      if (norm(A.trans(residual)) <= tol * initial)
        break;
    }
    if (alpha == 0 && beta == 0)
      break;
  }
  return finish();
}
Vec solve(Matrix A, double damping, LSQRInfo *info = nullptr) {
  Vec scales(A.n, 0);
  for (size_t q = 0; q < A.values.size(); ++q)
    scales[A.columns[q]] += A.values[q] * A.values[q];
  for (auto &s : scales)
    s = s > 1e-20 ? 1 / std::sqrt(s) : 1;
  for (size_t q = 0; q < A.values.size(); ++q)
    A.values[q] *= scales[A.columns[q]];
  if (A.rhs.size() > std::numeric_limits<size_t>::max() - size_t(A.n) ||
      A.values.size() > std::numeric_limits<size_t>::max() - size_t(A.n))
    throw std::runtime_error("Damped CSR dimensions overflow");
  A.reserve(A.rhs.size() + A.n, A.values.size() + A.n);
  for (int i = 0; i < A.n; i++)
    A.add({{i, damping}}, 0);
  Vec x = lsqr(A, 600, 1e-8, info);
  for (int i = 0; i < A.n; i++)
    x[i] *= scales[i];
  return x;
}
