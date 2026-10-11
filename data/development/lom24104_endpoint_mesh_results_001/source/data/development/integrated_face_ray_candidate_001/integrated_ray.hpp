#pragma once
// Standalone research descent/contact candidate. No trace/FMM, production
// adoption, optimized-source certificate, or first-arrival claim is made here.
#include "exact_cell_segment.hpp"
#include <functional>
#include <set>
#include <tuple>

namespace face_ray {
namespace ec = candidate_cell;
using ec::W;
using ec::WP;
using ec::Q;
using ec::QP;
using ec::need;
using Path = std::vector<P>;
struct Contact {
  std::size_t node = 0;
  int axis = 0, plane = 0;
  bool operator<(const Contact &b) const { return std::tie(node, axis, plane) < std::tie(b.node, b.axis, b.plane); }
  bool operator==(const Contact &b) const { return node == b.node && axis == b.axis && plane == b.plane; }
};
struct Counters {
  std::size_t segment_calls = 0, reused_edges = 0, directional_segment_calls = 0;
  std::size_t metric_calls = 0, support_calls = 0, support_sweeps = 0;
};
struct PathState {
  const ec::GridData *grid_identity = nullptr;
  Path path;
  std::vector<ec::Result> edges;
  std::vector<WP> ordinary;
  std::vector<std::array<bool, 3>> available;
  W action = 0;
  bool multiple_faces = false;
  WP source_partial{}, receiver_partial{};
  std::array<bool, 3> source_ordinary{}, receiver_ordinary{};
};
struct SupportAssessment {
  bool eligible = false;
  std::string reason, termination;
  std::vector<double> theta;
  std::vector<WP> vector, projected;
  W norm = 0;
  std::size_t sweeps = 0;
};
struct Attempt {
  std::size_t update = 0, attempt = 0;
  std::string mode, reason;
  Path before, trial, direction;
  Q alpha;
  std::vector<Contact> event_hits, contacts_before, contacts_after;
  W nominal_slope = 0, actual_slope = 0, paired_change = 0, armijo_rhs = 0, trial_action = 0;
  bool actual_evaluated = false, action_evaluated = false, accepted = false, no_op = false, event_limited = false;
  Counters counters;
};
struct SolveOptions {
  std::size_t maximum_updates = 1000, maximum_halvings = 24, maximum_support_sweeps = 10000;
};
struct SolveResult {
  PathState initial, final;
  SupportAssessment support;
  std::vector<Contact> contacts;
  std::string stop_reason;
  std::size_t updates = 0, attempts = 0;
  Counters counters;
  bool approximate_full_candidate = false;
};

inline W projected(W g, double x, const std::vector<Q> &axis) {
  const Q q = ec::exact(x);
  need(axis.front() <= q && q <= axis.back(), "Coordinate outside true box");
  if (q == axis.front()) return std::min(W(0), g);
  if (q == axis.back()) return std::max(W(0), g);
  return g;
}
inline W vector_norm(const std::vector<WP> &v) {
  W n = 0;
  for (std::size_t i = 1; i + 1 < v.size(); ++i)
    for (W x : v[i]) n = std::hypot(n, x);
  need(std::isfinite(n), "Nonfinite vector norm");
  return n;
}
inline std::vector<Contact> contacts(const ec::GridData &grid, const Path &p) {
  std::vector<Contact> out;
  for (std::size_t i = 1; i + 1 < p.size(); ++i)
    for (int k = 0; k < 3; ++k) {
      const Q x = ec::exact(p[i][k]);
      const auto it = std::lower_bound(grid.axis[k].begin(), grid.axis[k].end(), x);
      if (it != grid.axis[k].end() && it != grid.axis[k].begin() && it != grid.axis[k].end() - 1 && *it == x)
        out.push_back({i, k, int(it - grid.axis[k].begin())});
    }
  return out;
}
inline PathState evaluate_path(const ec::GridData &grid, const Path &p,
                              const PathState *previous = nullptr, bool model = false,
                              Counters *counts = nullptr) {
  need(p.size() >= 3, "At least one free vertex required");
  need(!previous || (previous->grid_identity == &grid && previous->edges.size() + 1 == previous->path.size()),
       "Cached path/model ownership mismatch");
  PathState s;
  s.grid_identity = &grid;
  s.path = p;
  s.ordinary.resize(p.size());
  s.available.assign(p.size(), {{true, true, true}});
  for (std::size_t i = 0; i + 1 < p.size(); ++i) {
    const bool reuse = previous && previous->path.size() == p.size() && previous->path[i] == p[i] &&
                       previous->path[i + 1] == p[i + 1] && (!model || previous->edges[i].model_evaluated);
    if (reuse) {
      s.edges.push_back(previous->edges[i]);
      if (counts) ++counts->reused_edges;
    } else {
      if (counts) ++counts->segment_calls;
      s.edges.push_back(ec::segment(grid, p[i], p[i + 1], ec::SegmentOptions{true, model, false}));
    }
    const auto &edge = s.edges.back();
    s.action = ec::plus(s.action, edge.action);
    s.multiple_faces = s.multiple_faces || edge.unsupported_multiple_faces;
    for (int side = 0; side < 2; ++side) {
      const std::size_t node = i + side;
      for (int k = 0; k < 3; ++k) {
        s.available[node][k] = s.available[node][k] && edge.ordinary[k];
        if (node && node + 1 < p.size() && edge.ordinary[k])
          s.ordinary[node][k] = ec::plus(s.ordinary[node][k], side ? edge.gb[k] : edge.ga[k]);
      }
    }
  }
  s.source_partial = s.edges.front().ga;
  s.receiver_partial = s.edges.back().gb;
  s.source_ordinary = s.edges.front().ordinary;
  s.receiver_ordinary = s.edges.back().ordinary;
  return s;
}

// One-dimensional minimization of the approximate true-box projected norm.
// There are at most two affected free endpoint components per patch. Its
// breakpoints are where a physical-box component enters/leaves its zero half.
// No activity distance, rank tolerance, fit success certificate, or free
// endpoint-normal mixture is introduced.
inline SupportAssessment assess_support(const ec::GridData &grid, const PathState &s,
                                       std::size_t max_sweeps = 10000) {
  need(max_sweeps > 0 && max_sweeps <= 10000, "Invalid declared support sweep budget");
  SupportAssessment out;
  if (s.multiple_faces) { out.reason = "multiple_aligned_faces"; return out; }
  struct Entry { std::size_t node; int axis; W value; };
  std::vector<std::vector<Entry>> columns;
  std::vector<WP> base = s.ordinary;
  for (std::size_t e = 0; e < s.edges.size(); ++e)
    for (const auto &p : s.edges[e].normal_patches) {
      if (!p.convex) { out.reason = "nonconvex_normal_jump"; return out; }
      std::vector<Entry> c;
      for (int side = 0; side < 2; ++side) {
        const std::size_t node = e + side;
        if (!node || node + 1 == s.path.size()) continue;
        base[node][p.axis] = ec::plus(base[node][p.axis], p.minus[side]);
        const W a = p.plus[side] - p.minus[side];
        need(std::isfinite(a), "Nonfinite support column");
        if (a != 0) c.push_back({node, p.axis, a});
      }
      columns.push_back(std::move(c));
    }
  out.theta.assign(columns.size(), 0.5);
  auto residual = [&]() {
    auto r = base;
    for (std::size_t j = 0; j < columns.size(); ++j)
      for (const auto &a : columns[j]) r[a.node][a.axis] = ec::plus(r[a.node][a.axis], ec::product({W(out.theta[j]), a.value}));
    return r;
  };
  auto r = residual();
  out.termination = columns.empty() ? "no_aligned_patches" : "sweep_budget";
  for (std::size_t sweep = 0; sweep < max_sweeps && !columns.empty(); ++sweep) {
    bool changed = false;
    for (std::size_t j = 0; j < columns.size(); ++j) {
      const auto &c = columns[j];
      if (c.empty()) continue;
      std::vector<W> knots{0, 1};
      for (const auto &a : c) {
        const Q x = ec::exact(s.path[a.node][a.axis]);
        if (x == grid.axis[a.axis].front() || x == grid.axis[a.axis].back()) {
          const W z = W(out.theta[j]) - r[a.node][a.axis] / a.value;
          need(std::isfinite(z), "Nonfinite support breakpoint");
          if (z > 0 && z < 1) knots.push_back(z);
        }
      }
      std::sort(knots.begin(), knots.end());
      knots.erase(std::unique(knots.begin(), knots.end()), knots.end());
      auto objective = [&](W t) {
        W value = 0;
        for (const auto &a : c) {
          const W v = ec::plus(r[a.node][a.axis], ec::product({t - W(out.theta[j]), a.value}));
          const W p = projected(v, s.path[a.node][a.axis], grid.axis[a.axis]);
          value = ec::plus(value, ec::product({p, p}));
        }
        return value;
      };
      W best = W(out.theta[j]), best_value = objective(best);
      auto consider = [&](W t) {
        need(std::isfinite(t) && t >= 0 && t <= 1, "Invalid support coefficient proposal");
        // Freeze a feasible binary64 coefficient before assessing its objective.
        const double d = static_cast<double>(t);
        need(std::isfinite(d) && d >= 0 && d <= 1, "Invalid rounded support coefficient");
        const W value = objective(W(d));
        if (value < best_value) { best_value = value; best = W(d); }
      };
      for (W t : knots) consider(t);
      for (std::size_t k = 1; k < knots.size(); ++k) {
        const W mid = (knots[k - 1] + knots[k]) / 2;
        W numerator = 0, denominator = 0;
        for (const auto &a : c) {
          const W b = ec::plus(r[a.node][a.axis], -ec::product({W(out.theta[j]), a.value}));
          const W probe = ec::plus(b, ec::product({mid, a.value}));
          const Q x = ec::exact(s.path[a.node][a.axis]);
          const bool active = (x == grid.axis[a.axis].front()) ? probe < 0 :
                              (x == grid.axis[a.axis].back()) ? probe > 0 : true;
          if (active) {
            numerator = ec::plus(numerator, ec::product({a.value, b}));
            denominator = ec::plus(denominator, ec::product({a.value, a.value}));
          }
        }
        if (denominator == 0) continue;
        need(denominator > 0, "Invalid positive support denominator");
        const W t = -numerator / denominator;
        need(std::isfinite(t), "Nonfinite support coordinate minimizer");
        if (t >= knots[k - 1] && t <= knots[k]) consider(t);
      }
      const double next = static_cast<double>(best);
      if (next != out.theta[j]) {
        const W change = W(next) - W(out.theta[j]);
        for (const auto &a : c) r[a.node][a.axis] = ec::plus(r[a.node][a.axis], ec::product({change, a.value}));
        out.theta[j] = next;
        changed = true;
      }
    }
    out.sweeps = sweep + 1;
    if (!changed) { out.termination = "coefficients_unchanged"; break; }
  }
  out.vector = residual(); // Independent of accumulated coordinate-fit residual.
  out.projected = out.vector;
  for (std::size_t i = 1; i + 1 < s.path.size(); ++i)
    for (int k = 0; k < 3; ++k)
      out.projected[i][k] = projected(out.vector[i][k], s.path[i][k], grid.axis[k]);
  out.norm = vector_norm(out.projected);
  out.eligible = true;
  out.reason = "approximate_feasible_constant_patch_vector_not_interval_certificate";
  return out;
}

inline double finite_double(W x) {
  const double d = static_cast<double>(x);
  need(std::isfinite(d) && (d != 0 || x == 0), "Wide value cannot be handed to binary64 metric");
  return d;
}
inline Path metric_direction(const ec::GridData &grid, const PathState &s, const std::vector<WP> &gradient,
                             const std::vector<Contact> &held, Counters &counts) {
  ++counts.metric_calls;
  const Vec weights = ray_metric_weights(grid.g, s.path);
  const std::size_t n = s.path.size() - 2;
  need(weights.size() == n + 1, "Metric weight dimensions");
  for (double w : weights) need(std::isfinite(w) && w > 0, "Unusable positive metric weight");
  Vec rhs(3 * n);
  std::vector<bool> fixed(3 * n, false);
  for (const auto &c : held) fixed[3 * (c.node - 1) + c.axis] = true;
  for (std::size_t i = 0; i < n; ++i)
    for (int k = 0; k < 3; ++k) rhs[3 * i + k] = finite_double(gradient[i + 1][k]);
  // Validate the same principal elimination before calling the frozen solve.
  for (int k = 0; k < 3; ++k) {
    Vec pivot(n), forward(n);
    for (std::size_t i = 0; i < n; ++i) {
      const std::size_t j = 3 * i + k;
      double d = fixed[j] ? 1 : weights[i] + weights[i + 1];
      double b = fixed[j] ? 0 : -rhs[j];
      if (i && !fixed[j] && !fixed[j - 3]) {
        const double ratio = -weights[i] / pivot[i - 1];
        const double u = ratio * (-weights[i]), v = ratio * forward[i - 1];
        need(std::isfinite(ratio) && std::isfinite(u) && std::isfinite(v), "Nonfinite metric elimination");
        d -= u;
        b -= v;
      }
      need(d > 0 && std::isfinite(d) && std::isfinite(b), "Unusable principal metric pivot");
      pivot[i] = d;
      forward[i] = b;
    }
  }
  const Vec d = solve_free_ray_metric(weights, rhs, fixed);
  Path direction(s.path.size(), P{{0, 0, 0}});
  for (std::size_t i = 1; i + 1 < s.path.size(); ++i)
    for (int k = 0; k < 3; ++k) {
      double v = d[3 * (i - 1) + k];
      need(std::isfinite(v) && (!fixed[3 * (i - 1) + k] || v == 0), "Invalid principal direction");
      const Q x = ec::exact(s.path[i][k]);
      if (x == grid.axis[k].front()) v = std::max(0.0, v);
      if (x == grid.axis[k].back()) v = std::min(0.0, v);
      direction[i][k] = v;
    }
  // This true-box projection need not solve a metric cone problem; the actual
  // directional gate, not a claimed metric optimum, determines usability.
  return direction;
}
inline std::vector<QP> exact_direction(const Path &d) {
  std::vector<QP> out(d.size());
  for (std::size_t i = 0; i < d.size(); ++i)
    for (int k = 0; k < 3; ++k) out[i][k] = ec::exact(d[i][k]);
  return out;
}
inline W directional(const ec::GridData &grid, const PathState &s, const std::vector<QP> &d, Counters &counts) {
  need(d.size() == s.path.size(), "Directional path dimensions");
  W value = 0;
  for (std::size_t e = 0; e < s.edges.size(); ++e) {
    const auto &r = s.edges[e];
    bool moved = false, normal = false;
    for (int k = 0; k < 3; ++k) {
      moved = moved || d[e][k] != Q(0) || d[e + 1][k] != Q(0);
      normal = normal || (!r.ordinary[k] && (d[e][k] != Q(0) || d[e + 1][k] != Q(0)));
    }
    if (!moved) continue;
    if (normal) {
      ++counts.directional_segment_calls;
      value = ec::plus(value, ec::directional_exact(grid, s.path[e], s.path[e + 1], d[e], d[e + 1]));
    } else {
      for (int k = 0; k < 3; ++k) {
        value = ec::plus(value, ec::Scale(d[e][k]).product({r.ga[k]}));
        value = ec::plus(value, ec::Scale(d[e + 1][k]).product({r.gb[k]}));
      }
    }
  }
  return value;
}

// Exact rational -> one nearest-even binary64 rounding for event coordinates.
// Narrowing a pre-rounded long double could double-round, so use quotient/remainder.
inline double binary64(const Q &x) {
  need(std::numeric_limits<unsigned long>::digits >= 53, "Exact binary64 significand export requires wide unsigned long");
  if (x == Q(0)) return 0;
  exact_cell::Z n, d, tmp, m, rem;
  mpz_abs(n.v, mpq_numref(x.v));
  mpz_set(d.v, mpq_denref(x.v));
  int e = int(mpz_sizeinbase(n.v, 2)) - int(mpz_sizeinbase(d.v, 2));
  if (e >= 0) {
    mpz_mul_2exp(tmp.v, d.v, e);
    if (mpz_cmp(n.v, tmp.v) < 0) --e;
  } else {
    mpz_mul_2exp(tmp.v, n.v, -e);
    if (mpz_cmp(tmp.v, d.v) < 0) --e;
  }
  int k = std::max(e - 52, -1074);
  if (k >= 0) mpz_mul_2exp(d.v, d.v, k);
  else mpz_mul_2exp(n.v, n.v, -k);
  mpz_fdiv_qr(m.v, rem.v, n.v, d.v);
  mpz_mul_2exp(rem.v, rem.v, 1);
  const int cmp = mpz_cmp(rem.v, d.v);
  if (cmp > 0 || (cmp == 0 && mpz_odd_p(m.v))) mpz_add_ui(m.v, m.v, 1);
  if (mpz_sizeinbase(m.v, 2) > 53) {
    mpz_fdiv_q_2exp(m.v, m.v, 1);
    ++k;
  }
  const unsigned long bits = mpz_get_ui(m.v);
  double value = std::ldexp(double(bits), k);
  if (mpq_sgn(x.v) < 0) value = -value;
  need(std::isfinite(value), "Nonfinite rounded trial coordinate");
  // A coordinate may correctly round to zero. Positive physical edge length
  // and exact face membership are checked on the completed rounded polygon.
  return value;
}
struct Step {
  Q alpha{1};
  std::vector<Contact> hits;
  bool event_limited = false;
};
inline Step first_step(const ec::GridData &grid, const PathState &s, const Path &direction) {
  Step out;
  for (std::size_t e = 0; e < s.edges.size(); ++e) {
    W length = 0;
    for (int k = 0; k < 3; ++k)
      length = std::hypot(length, ec::wide(ec::exact(direction[e + 1][k]) - ec::exact(direction[e][k])));
    if (length > 0) {
      const W cap = s.edges[e].length / (2 * length);
      need(std::isfinite(cap) && cap > 0, "Unusable geometric step cap");
      if (cap < 1) {
        double c = finite_double(cap);
        if (W(c) > cap) c = std::nextafter(c, 0.0);
        need(c > 0, "Geometric cap cannot be represented positively");
        out.alpha = std::min(out.alpha, ec::exact(c));
      }
    }
  }
  for (std::size_t i = 1; i + 1 < s.path.size(); ++i)
    for (int k = 0; k < 3; ++k) {
      const Q x = ec::exact(s.path[i][k]), d = ec::exact(direction[i][k]);
      if (d == Q(0)) continue;
      // Along one affine coordinate only the nearest plane in its travel
      // direction can be the first event. Comparisons/order remain exact.
      auto it = Q(0) < d ? std::upper_bound(grid.axis[k].begin(), grid.axis[k].end(), x) :
                           std::lower_bound(grid.axis[k].begin(), grid.axis[k].end(), x);
      if (d < Q(0)) {
        if (it == grid.axis[k].begin()) continue;
        --it;
      }
      if (it == grid.axis[k].end()) continue;
      const Q t = (*it - x) / d;
      if (!(Q(0) < t) || out.alpha < t) continue;
      if (t < out.alpha) {
        out.alpha = t;
        out.hits.clear();
      }
      out.hits.push_back({i, k, int(it - grid.axis[k].begin())});
    }
  out.event_limited = !out.hits.empty();
  return out;
}
inline std::string rounded_geometry(const ec::GridData &grid, const Path &before, const Path &trial,
                                    const Path &direction, const Q &alpha, const Step &step) {
  if (before == trial) return "rounded_no_op";
  if (before.front() != trial.front() || before.back() != trial.back()) return "fixed_endpoint_changed";
  for (std::size_t i = 0; i < trial.size(); ++i) {
    if (i && trial[i] == trial[i - 1]) return "collapsed_rounded_edge";
    for (int k = 0; k < 3; ++k) {
      const Q x = ec::exact(before[i][k]), y = ec::exact(trial[i][k]), d = ec::exact(direction[i][k]);
      if (!(grid.axis[k].front() <= y && y <= grid.axis[k].back())) return "rounded_outside_true_box";
      const auto first = std::upper_bound(grid.axis[k].begin(), grid.axis[k].end(), std::min(x, y));
      if (first != grid.axis[k].end() && *first < std::max(x, y)) return "unintended_rounded_crossing";
      const auto at = std::lower_bound(grid.axis[k].begin(), grid.axis[k].end(), y);
      if (at != grid.axis[k].end() && *at == y && y != x)
        if (d == Q(0) || (y - x) / d != alpha) return "unintended_rounded_contact";
    }
  }
  if (alpha == step.alpha)
    for (const auto &c : step.hits)
      if (ec::exact(trial[c.node][c.axis]) != grid.axis[c.axis][c.plane]) return "exact_event_not_attained";
  return "";
}
inline W paired(const PathState &before, const PathState &after) {
  W value = 0;
  for (std::size_t e = 0; e < before.edges.size(); ++e) {
    if (before.path[e] == after.path[e] && before.path[e + 1] == after.path[e + 1]) continue;
    value = ec::plus(value, after.edges[e].action - before.edges[e].action);
  }
  return value;
}

inline SolveResult solve(const ec::GridData &grid, const Path &path, SolveOptions options = {},
                         const std::function<void(const Attempt &)> &emit = {}) {
  need(options.maximum_updates > 0 && options.maximum_updates <= 1000 &&
       options.maximum_halvings > 0 && options.maximum_halvings <= 24 &&
       options.maximum_support_sweeps > 0 && options.maximum_support_sweeps <= 10000,
       "Invalid declared solve budgets");
  SolveResult out;
  out.initial = evaluate_path(grid, path, nullptr, false, &out.counters);
  out.final = out.initial;
  out.contacts = contacts(grid, path);
  const W strict = W(1e-7), armijo = W(1e-4);
  if (out.final.multiple_faces) { out.stop_reason = "unsupported_multiple_faces"; return out; }

  auto try_direction = [&](const Path &d, const std::string &mode) {
    const auto exact_d = exact_direction(d);
    const W slope = directional(grid, out.final, exact_d, out.counters);
    if (!(slope < 0)) {
      Attempt a;
      a.update = out.updates;
      a.mode = mode;
      a.reason = "nonnegative_nominal_direction";
      a.before = out.final.path;
      a.direction = d;
      a.contacts_before = a.contacts_after = out.contacts;
      a.nominal_slope = slope;
      a.counters = out.counters;
      ++out.attempts;
      if (emit) emit(a);
      return false;
    }
    const Step step = first_step(grid, out.final, d);
    Q alpha = step.alpha;
    for (std::size_t attempt = 0; attempt < options.maximum_halvings; ++attempt, alpha = alpha / Q(2)) {
      Attempt a;
      a.update = out.updates;
      a.attempt = attempt;
      a.mode = mode;
      a.before = out.final.path;
      a.trial = a.before;
      a.direction = d;
      a.alpha = alpha;
      a.event_hits = step.hits;
      a.event_limited = step.event_limited && alpha == step.alpha;
      a.contacts_before = out.contacts;
      a.nominal_slope = slope;
      for (std::size_t i = 1; i + 1 < a.trial.size(); ++i)
        for (int k = 0; k < 3; ++k)
          if (d[i][k] != 0) a.trial[i][k] = binary64(ec::exact(a.before[i][k]) + alpha * exact_d[i][k]);
      a.no_op = a.trial == a.before;
      a.reason = rounded_geometry(grid, a.before, a.trial, d, alpha, step);
      std::vector<QP> actual(d.size());
      for (std::size_t i = 0; i < d.size(); ++i)
        for (int k = 0; k < 3; ++k) actual[i][k] = ec::exact(a.trial[i][k]) - ec::exact(a.before[i][k]);
      a.actual_slope = directional(grid, out.final, actual, out.counters);
      a.actual_evaluated = true;
      a.armijo_rhs = ec::Scale(alpha).product({armijo, slope});
      if (a.reason.empty() && !(a.actual_slope < 0)) a.reason = "rounded_non_descent";
      PathState candidate;
      if (a.reason.empty()) {
        candidate = evaluate_path(grid, a.trial, &out.final, false, &out.counters);
        a.action_evaluated = true;
        a.trial_action = candidate.action;
        a.paired_change = paired(out.final, candidate);
        if (candidate.multiple_faces) a.reason = "unsupported_multiple_faces";
        else {
          a.accepted = a.paired_change <= a.armijo_rhs && a.paired_change < 0;
          a.reason = a.accepted ? "approximate_paired_armijo_accepted" : "approximate_paired_armijo_rejected";
        }
      }
      a.contacts_after = a.accepted ? contacts(grid, candidate.path) : out.contacts;
      ++out.attempts;
      a.counters = out.counters;
      if (emit) emit(a);
      if (a.accepted) {
        out.final = std::move(candidate);
        out.contacts = std::move(a.contacts_after);
        out.support = SupportAssessment{};
        out.support.reason = "not_assessed_for_current_geometry";
        ++out.updates;
        return true;
      }
      if (a.reason != "approximate_paired_armijo_rejected" && a.reason != "rounded_non_descent") return false;
    }
    return false;
  };

  while (out.updates < options.maximum_updates) {
    auto restricted = out.final.ordinary;
    for (std::size_t i = 1; i + 1 < path.size(); ++i)
      for (int k = 0; k < 3; ++k) restricted[i][k] = projected(restricted[i][k], out.final.path[i][k], grid.axis[k]);
    for (const auto &c : out.contacts) restricted[c.node][c.axis] = 0;
    if (vector_norm(restricted) >= strict) {
      const Path d = metric_direction(grid, out.final, out.final.ordinary, out.contacts, out.counters);
      if (try_direction(d, "restricted_metric")) continue;
      // Exact-box-activity projected gradient fallback is a direction proposal,
      // not an alteration of the physical feasible set or stopping gradient.
      Path fallback(path.size(), P{{0, 0, 0}});
      for (std::size_t i = 1; i + 1 < path.size(); ++i)
        for (int k = 0; k < 3; ++k) fallback[i][k] = finite_double(-restricted[i][k]);
      if (try_direction(fallback, "restricted_projected_gradient")) continue;
    }
    ++out.counters.support_calls;
    out.support = assess_support(grid, out.final, options.maximum_support_sweeps);
    out.counters.support_sweeps += out.support.sweeps;
    if (out.support.eligible && out.support.norm < strict) {
      out.approximate_full_candidate = true;
      out.stop_reason = "approximate_full_witness_requires_final_interval_audit";
      return out;
    }
    bool released = false;
    for (const auto &c : out.contacts) {
      const bool ordinary = out.final.available[c.node][c.axis];
      const W g = out.final.ordinary[c.node][c.axis];
      for (int sign : {-1, 1}) {
        if (ordinary && !(W(sign) * g < 0)) continue;
        Path d(path.size(), P{{0, 0, 0}});
        d[c.node][c.axis] = sign;
        if (try_direction(d, ordinary ? "isolated_ordinary_release" : "aligned_true_directional_release")) {
          released = true;
          break;
        }
      }
      if (released) break;
    }
    if (released) continue;
    if (out.support.eligible) {
      const Path d = metric_direction(grid, out.final, out.support.vector, {}, out.counters);
      if (try_direction(d, "full_support_proposal_true_directional_gate")) continue;
    }
    out.stop_reason = "unresolved_restricted_search_and_finite_release_set";
    return out;
  }
  out.stop_reason = "update_budget_unresolved";
  return out;
}
} // namespace face_ray
