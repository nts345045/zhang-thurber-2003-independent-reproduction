#pragma once
// Event scheduling only. The immutable evaluator, all integration cuts,
// derivative kernels, contact inventory and history implementation are reused.
#include "../../data/development/integrated_face_ray_candidate_001/integrated_ray.hpp"

namespace stratified_events {
namespace fr = face_ray;
namespace ec = candidate_cell;
using fr::Path;
using fr::PathState;
using fr::Step;
using ec::Q;
using ec::W;
using ec::need;

struct Policy {
  const ec::GridData *grid_identity;
  bool depth_only = true;
  explicit Policy(const ec::GridData &grid) : grid_identity(&grid) {
    // Equality is on every cached exact nodal value, including boundary nodes.
    // GridData and its borrowed Grid must remain immutable for this lifetime.
    for (std::size_t z = 0; z < grid.axis[2].size(); ++z)
      for (std::size_t y = 0; y < grid.axis[1].size(); ++y)
        for (std::size_t x = 0; x < grid.axis[0].size(); ++x)
          if (grid.velocity[grid.g.id(int(x), int(y), int(z))] !=
              grid.velocity[grid.g.id(0, 0, int(z))]) depth_only = false;
  }
  bool inert(int axis, std::size_t plane) const {
    return depth_only && axis < 2 && plane > 0 &&
           plane + 1 < grid_identity->axis[axis].size();
  }
};

inline Step first_step(const Policy &policy, const ec::GridData &grid,
                       const PathState &s, const Path &direction) {
  need(policy.grid_identity == &grid && s.grid_identity == &grid,
       "Event policy/state model ownership mismatch");
  if (!policy.depth_only) return fr::first_step(grid, s, direction);
  Step out;
  // Byte-preserved arithmetic from the original relative half-edge guard.
  for (std::size_t e = 0; e < s.edges.size(); ++e) {
    W length = 0;
    for (int k = 0; k < 3; ++k)
      length = std::hypot(length, ec::wide(ec::exact(direction[e + 1][k]) - ec::exact(direction[e][k])));
    if (length > 0) {
      const W cap = s.edges[e].length / (2 * length);
      need(std::isfinite(cap) && cap > 0, "Unusable geometric step cap");
      if (cap < 1) {
        double c = fr::finite_double(cap);
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
      auto it = Q(0) < d ? std::upper_bound(grid.axis[k].begin(), grid.axis[k].end(), x) :
                           std::lower_bound(grid.axis[k].begin(), grid.axis[k].end(), x);
      if (d < Q(0)) {
        if (it == grid.axis[k].begin()) continue;
        --it;
      }
      if (it == grid.axis[k].end()) continue;
      // Skip only proven-inert internal x/y planes, never the physical end.
      while (policy.inert(k, std::size_t(it - grid.axis[k].begin()))) {
        if (Q(0) < d) ++it;
        else --it;
      }
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

inline std::string rounded_geometry(const Policy &policy, const ec::GridData &grid,
                                    const Path &before, const Path &trial,
                                    const Path &direction, const Q &alpha, const Step &step) {
  need(policy.grid_identity == &grid, "Rounded event policy/model ownership mismatch");
  if (!policy.depth_only) return fr::rounded_geometry(grid, before, trial, direction, alpha, step);
  if (before == trial) return "rounded_no_op";
  if (before.front() != trial.front() || before.back() != trial.back()) return "fixed_endpoint_changed";
  for (std::size_t i = 0; i < trial.size(); ++i) {
    if (i && trial[i] == trial[i - 1]) return "collapsed_rounded_edge";
    for (int k = 0; k < 3; ++k) {
      const Q x = ec::exact(before[i][k]), y = ec::exact(trial[i][k]), d = ec::exact(direction[i][k]);
      if (!(grid.axis[k].front() <= y && y <= grid.axis[k].back())) return "rounded_outside_true_box";
      auto first = std::upper_bound(grid.axis[k].begin(), grid.axis[k].end(), std::min(x, y));
      while (first != grid.axis[k].end() && *first < std::max(x, y)) {
        if (!policy.inert(k, std::size_t(first - grid.axis[k].begin())))
          return "unintended_rounded_crossing";
        ++first;
      }
      const auto at = std::lower_bound(grid.axis[k].begin(), grid.axis[k].end(), y);
      if (at != grid.axis[k].end() && *at == y && y != x &&
          !policy.inert(k, std::size_t(at - grid.axis[k].begin())))
        if (d == Q(0) || (y - x) / d != alpha) return "unintended_rounded_contact";
    }
  }
  if (alpha == step.alpha)
    for (const auto &c : step.hits)
      if (ec::exact(trial[c.node][c.axis]) != grid.axis[c.axis][c.plane]) return "exact_event_not_attained";
  return "";
}
} // namespace stratified_events
