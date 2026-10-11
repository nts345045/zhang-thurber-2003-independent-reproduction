#pragma once
// SOURCE DRAFT ONLY. This supplies proposals/history, not a new ray solver.
// The immutable candidate still owns every physical/action/stopping gate.
#include "../../data/development/integrated_face_ray_candidate_001/integrated_ray.hpp"
#include "principal_usable_ray_curvature.hpp"
#include "held_cone_ray_metric.hpp"

namespace face_acceleration {
namespace fr = face_ray;
namespace ec = candidate_cell;
using fr::Path;
using fr::PathState;
using fr::Contact;

// Zero-padded representation of a principal inverse on the SAME held/free
// basis for every application in one two-loop recursion. No box clipping or
// active-set solve is permitted here. The original incident diagonals remain.
struct PrincipalInverse {
  const Vec &weights;
  const std::vector<bool> &held;
  bool operator()(const Vec &rhs, Vec &out) const {
    out.clear();
    if (weights.size() < 2 || rhs.size() != 3 * (weights.size() - 1) ||
        held.size() != rhs.size() || !finite_curvature_vector(rhs)) return false;
    for (double w : weights) if (!(w > 0) || !std::isfinite(w)) return false;
    for (std::size_t k = 0; k < rhs.size(); ++k)
      if (held[k] && rhs[k] != 0) return false;
    const std::size_t n = weights.size() - 1;
    // Validate the frozen solve's exact coefficient/RHS operation order.
    for (int axis = 0; axis < 3; ++axis) {
      Vec diagonal(n), forward(n);
      for (std::size_t i = 0; i < n; ++i) {
        const std::size_t k = 3 * i + axis;
        double d = held[k] ? 1 : weights[i] + weights[i + 1];
        double b = held[k] ? 0 : -rhs[k];
        if (i && !held[k] && !held[k - 3]) {
          const double ratio = -weights[i] / diagonal[i - 1];
          const double dd = ratio * (-weights[i]), db = ratio * forward[i - 1];
          if (!std::isfinite(ratio) || !std::isfinite(dd) || !std::isfinite(db)) return false;
          d -= dd;
          b -= db;
        }
        if (!(d > 0) || !std::isfinite(d) || !std::isfinite(b)) return false;
        diagonal[i] = d;
        forward[i] = b;
      }
    }
    out = solve_free_ray_metric(weights, rhs, held); // This returns NEGATIVE inverse.
    for (std::size_t k = 0; k < out.size(); ++k) {
      out[k] = -out[k];
      if (!std::isfinite(out[k]) || (held[k] && out[k] != 0)) return false;
    }
    return true;
  }
};

struct Basis {
  const ec::GridData *model = nullptr;
  std::size_t nodes = 0, representation_revision = 0;
  P source{}, receiver{};
  std::vector<Contact> contacts;
  std::vector<bool> held, available, physical_active;
  std::vector<int> box_sign; // +1 exact lower face; -1 exact upper; 0 interior.
  bool same_structure(const Basis &b) const {
    return model == b.model && nodes == b.nodes &&
      representation_revision == b.representation_revision && source == b.source &&
      receiver == b.receiver && contacts == b.contacts && held == b.held &&
      available == b.available && box_sign == b.box_sign;
  }
  bool operator==(const Basis &b) const {
    return same_structure(b) && physical_active == b.physical_active;
  }
};

inline Basis basis(const ec::GridData &grid, const PathState &s,
                   const std::vector<Contact> &held, std::size_t revision) {
  ec::need(s.grid_identity == &grid && s.path.size() >= 3 &&
           s.ordinary.size() == s.path.size() && s.available.size() == s.path.size() &&
           !s.multiple_faces, "Invalid smooth-coordinate history state");
  Basis b;
  b.model = &grid;
  b.nodes = s.path.size();
  b.representation_revision = revision;
  b.source = s.path.front();
  b.receiver = s.path.back();
  b.contacts = held;
  std::sort(b.contacts.begin(), b.contacts.end());
  ec::need(std::adjacent_find(b.contacts.begin(), b.contacts.end()) == b.contacts.end(),
           "Duplicate held contact");
  b.held.assign(3 * (b.nodes - 2), false);
  b.physical_active.assign(b.held.size(), false);
  b.available.resize(b.held.size());
  b.box_sign.resize(b.held.size());
  for (const auto &c : b.contacts) {
    ec::need(c.node > 0 && c.node + 1 < b.nodes && c.axis >= 0 && c.axis < 3 &&
             c.plane > 0 && std::size_t(c.plane + 1) < grid.axis[c.axis].size() &&
             ec::exact(s.path[c.node][c.axis]) == grid.axis[c.axis][c.plane],
             "Held equality is not an exact internal-plane contact");
    b.held[3 * (c.node - 1) + c.axis] = true;
  }
  for (std::size_t i = 0; i < b.nodes; ++i)
    for (int axis = 0; axis < 3; ++axis) {
      const ec::Q x = ec::exact(s.path[i][axis]);
      ec::need(grid.axis[axis].front() <= x && x <= grid.axis[axis].back(),
               "History coordinate is outside the true physical box");
      if (!i || i + 1 == b.nodes) continue;
      const std::size_t k = 3 * (i - 1) + axis;
      b.box_sign[k] = x == grid.axis[axis].front() ? 1 :
                      x == grid.axis[axis].back() ? -1 : 0;
      b.available[k] = s.available[i][axis];
      ec::need(b.held[k] || b.available[k], "Unavailable normal cannot enter smooth history");
    }
  return b;
}

inline bool fixed_coordinate(const Basis &b, std::size_t k) {
  // An empty physical mask supports the unchanged full-support geometry carrier.
  return b.held[k] || (!b.physical_active.empty() && b.physical_active[k]);
}
inline std::vector<bool> principal_mask(const Basis &b) {
  std::vector<bool> fixed(b.held.size());
  for (std::size_t k = 0; k < fixed.size(); ++k) fixed[k] = fixed_coordinate(b, k);
  return fixed;
}
inline bool has_unheld_boundary(const Basis &b) {
  for (std::size_t k = 0; k < b.held.size(); ++k)
    if (!b.held[k] && b.box_sign[k]) return true;
  return false;
}
inline Vec ordinary_gradient(const PathState &s, const Basis &b) {
  Vec g(b.held.size(), 0);
  for (std::size_t k = 0; k < g.size(); ++k)
    if (!fixed_coordinate(b, k)) g[k] = fr::finite_double(s.ordinary[k / 3 + 1][k % 3]);
  return g; // Unprojected ordinary/tangent gradient; never a support-fit vector.
}
inline bool feasible(const Vec &d, const Basis &b) {
  if (d.size() != b.held.size() || !finite_curvature_vector(d)) return false;
  for (std::size_t k = 0; k < d.size(); ++k)
    if ((fixed_coordinate(b, k) && d[k] != 0) ||
        (b.box_sign[k] && b.box_sign[k] * d[k] < 0)) return false;
  return true;
}
inline Path path_direction(const Vec &d, const Basis &b) {
  ec::need(feasible(d, b), "Cannot export an infeasible acceleration proposal");
  Path out(b.nodes, P{{0, 0, 0}});
  for (std::size_t k = 0; k < d.size(); ++k) out[k / 3 + 1][k % 3] = d[k];
  return out;
}

struct Proposal {
  bool usable = false;
  std::string mode, reason;
  Path direction;
  Vec rejected_lbfgs_direction, cone_last_iterate;
  std::vector<std::string> history_notes;
  std::size_t history_pairs_used = 0, linear_inverse_calls = 0;
  bool selection_required = false, selection_valid = false, selection_reused = false;
  bool cone_direction_from_selection = false;
  std::size_t cone_calls = 0, cone_solves = 0, selected_physical_equalities = 0;
  double computed_slope = 0, cone_quadratic_objective = 0;
  // Work counts above concern THIS invocation. Cached statistics retain their
  // original solve count as evidence and must not be summed as new work.
  HeldConeStats selection, cone;
};
struct PairReport {
  bool stored = false, reset = false, pending_box_selection = false;
  std::string reason;
  std::size_t pairs_before = 0, pairs_after = 0;
  double computed_curvature = 0, reciprocal = 0;
};
enum class AcceptedMode { ordinary_restricted, release_or_full_support };

class History {
  std::vector<Vec> S_, Y_;
  Vec rho_, anchor_gradient_;
  Basis basis_;
  Path anchor_;
  bool bound_ = false;
  struct Selection {
    bool valid = false;
    Basis structure;
    Path path;
    Vec raw_gradient, weights, direction;
    int maximum_solves = 0;
    HeldConeStats stats;
    bool matches(const Basis &b, const PathState &s, const Vec &g,
                 const Vec &w, int budget) const {
      return valid && structure == b && path == s.path && raw_gradient == g &&
        weights == w && maximum_solves == budget;
    }
  } selection_;
  void anchor(const Basis &b, const PathState &s, const Vec &g) {
    basis_ = b;
    anchor_ = s.path;
    anchor_gradient_ = g;
    bound_ = true;
  }
public:
  std::size_t size() const { return S_.size(); }
  void clear() { S_.clear(); Y_.clear(); rho_.clear(); }
  // Call upon entering release/support mode or after an unusable direction.
  // A single rejected Armijo backtrack does NOT call this method.
  // The exact-key selector may survive this clear for same-state force_cone;
  // accepted() always invalidates it, and ordinary proposals never reuse it.
  void discard_direction_or_enter_nonsmooth_search() { clear(); }

  Proposal propose(const ec::GridData &grid, const PathState &s,
                   const std::vector<Contact> &held, fr::Counters &counts,
                   std::size_t representation_revision = 0,
                   bool force_cone = false, int maximum_cone_solves = 10000) {
    Proposal out;
    if (!force_cone) selection_ = Selection{};
    Basis b = basis(grid, s, held, representation_revision);
    // No previous physical active coordinate enters this gradient or the QP.
    const Vec raw_gradient = ordinary_gradient(s, b);
    ++counts.metric_calls;
    const Vec weights = ray_metric_weights(grid.g, s.path);
    ec::need(weights.size() + 1 == b.nodes, "Principal metric path dimensions");
    out.selection_required = has_unheld_boundary(b);
    Vec selected_direction;
    if (out.selection_required) {
      const Basis structure = b;
      if (force_cone && selection_.matches(structure, s, raw_gradient, weights,
                                           maximum_cone_solves)) {
        selected_direction = selection_.direction;
        out.selection = selection_.stats;
        out.selection_reused = true;
      } else {
        selection_ = Selection{};
        ++out.cone_calls;
        selected_direction = solve_held_cone_ray_metric(weights, raw_gradient,
          b.box_sign, b.held, out.selection, maximum_cone_solves);
        out.cone_solves += out.selection.solves;
      }
      bool valid = out.selection.success && feasible(selected_direction, b) &&
                   out.selection.active.size() == b.held.size();
      if (valid) for (std::size_t k = 0; k < b.held.size(); ++k) {
        const bool active = out.selection.active[k];
        valid = valid && (!b.held[k] || active) &&
          (!active || b.held[k] || b.box_sign[k] != 0) &&
          (!active || selected_direction[k] == 0);
      }
      if (!valid) {
        clear(); bound_ = false; selection_ = Selection{};
        out.mode = "ordinary_held_true_box_cone";
        out.cone = out.selection;
        out.cone_last_iterate = selected_direction;
        out.reason = "physical_box_selection_unresolved";
        return out; // No partial active set may define H0 or retain history.
      }
      out.selection_valid = true;
      for (std::size_t k = 0; k < b.held.size(); ++k) {
        b.physical_active[k] = out.selection.active[k] && !b.held[k] && b.box_sign[k] != 0;
        out.selected_physical_equalities += b.physical_active[k];
      }
      if (!out.selection_reused) {
        selection_.valid = true; selection_.structure = structure; selection_.path = s.path;
        selection_.raw_gradient = raw_gradient; selection_.weights = weights;
        selection_.maximum_solves = maximum_cone_solves;
        selection_.direction = selected_direction; selection_.stats = out.selection;
      }
    } else selection_ = Selection{}; // No possible physical active mask: no selection solve.
    const Vec g = ordinary_gradient(s, b);
    if (!bound_ || !(basis_ == b) || anchor_ != s.path || anchor_gradient_ != g) {
      out.history_notes.push_back(!bound_ ? "new_history" :
        !(basis_ == b) ? "basis_box_or_representation_changed" : "state_changed_without_accepted_secant");
      clear();
      anchor(b, s, g);
    }
    const std::vector<bool> fixed = principal_mask(b);
    const PrincipalInverse inverse{weights, fixed};
    auto checked_inverse = [&](const Vec &rhs, Vec &value) {
      ++out.linear_inverse_calls;
      return inverse(rhs, value);
    };
    Vec d;
    if (!force_cone) {
      out.history_pairs_used = size();
      const bool recurrence = usable_principal_lbfgs_direction(checked_inverse, g, S_, Y_, rho_, d);
      const double slope = recurrence ? dot(g, d) : 0;
      if (recurrence && feasible(d, b) && std::isfinite(slope) && slope < 0) {
        out.usable = true;
        out.mode = "ordinary_principal_lbfgs";
        out.reason = "proposal_requires_unchanged_true_direction_and_action_gates";
        out.computed_slope = slope;
        out.direction = path_direction(d, b);
        return out;
      }
      out.rejected_lbfgs_direction = d;
      out.history_notes.push_back(!recurrence ? "unusable_lbfgs_arithmetic" :
                                 !feasible(d, b) ? "outward_or_nonfinite_lbfgs" : "nonnegative_lbfgs_dot");
    } else out.history_notes.push_back("explicit_cone_fallback");
    clear();
    out.mode = "ordinary_held_true_box_cone";
    if (out.selection_valid) {
      d = selected_direction;
      out.cone = out.selection;
      out.cone_direction_from_selection = true;
    } else {
      ++out.cone_calls;
      d = solve_held_cone_ray_metric(weights, raw_gradient, b.box_sign, b.held,
                                     out.cone, maximum_cone_solves);
      out.cone_solves += out.cone.solves;
    }
    out.cone_last_iterate = d; // Retained even if the bounded quadratic solve is unresolved.
    if (!out.cone.success || !feasible(d, b)) {
      out.reason = "cone_unresolved_use_existing_projected_gradient_or_unresolved_path";
      return out;
    }
    out.computed_slope = dot(raw_gradient, d);
    const Vec product = ray_metric_product(weights, d);
    out.cone_quadratic_objective = out.computed_slope + 0.5 * dot(d, product);
    if (!std::isfinite(out.computed_slope) || !(out.computed_slope < 0) ||
        !std::isfinite(out.cone_quadratic_objective) || !(out.cone_quadratic_objective < 0)) {
      out.reason = "cone_has_no_usable_negative_quadratic_proposal";
      return out;
    }
    out.usable = true;
    out.reason = "arithmetic_qp_pass_requires_unchanged_true_direction_and_action_gates";
    out.direction = path_direction(d, b);
    return out;
  }

  // Call ONLY after the unchanged event/actual-Q/paired-Armijo gates accepted
  // a rounded polygon. Rejected trials never update the anchor or any pair.
  PairReport accepted(const ec::GridData &grid, const PathState &before,
                      const PathState &after, const std::vector<Contact> &held_before,
                      const std::vector<Contact> &held_after, AcceptedMode mode,
                      std::size_t representation_revision = 0) {
    PairReport out;
    out.pairs_before = size();
    selection_ = Selection{}; // Never reuse a pre-acceptance selector.
    if (mode != AcceptedMode::ordinary_restricted) {
      // A released/nonsmooth state need not yet have a valid smooth basis.
      // Discard history without asking for nonexistent ordinary derivatives;
      // the next ordinary proposal validates and anchors its own basis.
      clear();
      bound_ = false;
      anchor_.clear();
      anchor_gradient_.clear();
      out.reset = true;
      out.reason = "accepted_release_or_full_support";
      out.pairs_after = 0;
      return out;
    }
    Basis a = basis(grid, before, held_before, representation_revision);
    Basis b = basis(grid, after, held_after, representation_revision);
    // Tentative secants use exactly the last selected basis. A new ordinary
    // proposal MUST reselect before D; a changed mask then discards all pairs.
    if (bound_ && basis_.same_structure(a)) a.physical_active = basis_.physical_active;
    if (a.same_structure(b)) b.physical_active = a.physical_active;
    const Vec ga = ordinary_gradient(before, a), gb = ordinary_gradient(after, b);
    const bool consistent = bound_ && basis_ == a && anchor_ == before.path && anchor_gradient_ == ga;
    auto reset = [&](const char *why) {
      clear();
      anchor(b, after, gb);
      out.reset = true;
      out.reason = why;
      out.pairs_after = size();
      return out;
    };
    if (!consistent) return reset("accepted_state_does_not_continue_history");
    if (!(a == b)) return reset("accepted_contact_box_availability_or_representation_change");
    Vec s(ga.size(), 0), y(ga.size(), 0);
    for (std::size_t k = 0; k < s.size(); ++k)
      if (fixed_coordinate(a, k) && before.path[k / 3 + 1][k % 3] != after.path[k / 3 + 1][k % 3])
        return reset("principal_fixed_coordinate_changed_on_ordinary_acceptance");
    out.pending_box_selection = has_unheld_boundary(b);
    try {
      for (std::size_t k = 0; k < s.size(); ++k) if (!fixed_coordinate(a, k)) {
        const std::size_t node = k / 3 + 1, axis = k % 3;
        // Exact accepted binary64 displacement, rounded once for D's vectors.
        s[k] = fr::binary64(ec::exact(after.path[node][axis]) - ec::exact(before.path[node][axis]));
        // Same unprojected binary64 gradient handoff at both accepted endpoints.
        y[k] = fr::binary64(ec::exact(gb[k]) - ec::exact(ga[k]));
      }
    } catch (const std::runtime_error &) {
      anchor(b, after, gb);
      out.reason = "secant_handoff_unrepresentable_existing_pairs_retained";
      out.pairs_after = size();
      return out;
    }
    out.computed_curvature = dot(s, y);
    if (usable_ray_curvature(s, y, out.computed_curvature, out.reciprocal)) {
      if (S_.size() == 16) { S_.erase(S_.begin()); Y_.erase(Y_.begin()); rho_.erase(rho_.begin()); }
      S_.push_back(std::move(s));
      Y_.push_back(std::move(y));
      rho_.push_back(out.reciprocal);
      out.stored = true;
      out.reason = "computed_positive_finite_curvature_pair_stored";
    } else out.reason = "unusable_new_curvature_pair_existing_pairs_retained";
    anchor(b, after, gb);
    out.pairs_after = size();
    return out;
  }
};
} // namespace face_acceleration
