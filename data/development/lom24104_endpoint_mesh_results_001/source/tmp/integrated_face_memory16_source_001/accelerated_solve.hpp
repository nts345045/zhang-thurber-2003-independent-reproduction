#pragma once
// Function-level source draft. The evaluator and scientific gates are reused
// from immutable candidate001; reviewed direction/history and event scheduling
// changes are explicit here.
#include "acceleration.hpp"
#include "stratified_events.hpp"

namespace face_acceleration {
struct AccelerationRecord {
  std::size_t update = 0, attempts_so_far = 0, pairs_before = 0, pairs_after = 0;
  std::size_t held_equalities = 0, history_pairs_used = 0, linear_inverse_calls = 0;
  std::string phase, mode, reason;
  bool usable = false;
  bool selection_required = false, selection_valid = false, selection_reused = false;
  bool cone_direction_from_selection = false;
  std::size_t cone_calls = 0, cone_solves = 0, selected_physical_equalities = 0;
  std::size_t selection_held_equalities = 0, rejected_direction_size = 0;
  double computed_slope = 0, quadratic_objective = 0;
  std::vector<std::string> history_notes;
  std::vector<std::size_t> selected_physical_slots;
  // Sparse feasibility evidence only; this is not the complete rejected D.
  std::vector<std::pair<std::size_t, double>> rejected_nonfinite, rejected_outward, rejected_fixed;
  PairReport pair;
  ConeRayMetricStats selection, cone;
};
struct SolveResult : fr::SolveResult {
  std::vector<AccelerationRecord> acceleration;
};

// Geometric contacts remain full event metadata. Only unavailable normals are
// equalities in the ordinary search/history basis; there is no magnitude test.
inline std::vector<Contact> unavailable_contact_holds(const ec::GridData &grid,
                    const PathState &s, const std::vector<Contact> &geometric_contacts) {
  ec::need(s.grid_identity == &grid && s.path.size() >= 3 &&
           s.available.size() == s.path.size() && s.ordinary.size() == s.path.size(),
           "Invalid contact-hold state/model dimensions");
  ec::need(geometric_contacts == fr::contacts(grid, s.path),
           "Contact holds require the complete current geometric inventory");
  std::vector<Contact> held;
  for (const auto &c : geometric_contacts)
    if (!s.available[c.node][c.axis]) held.push_back(c);
  std::size_t unavailable = 0;
  for (std::size_t i = 1; i + 1 < s.path.size(); ++i)
    for (int k = 0; k < 3; ++k) unavailable += !s.available[i][k];
  ec::need(held.size() == unavailable,
           "Unavailable internal component lacks its geometric contact");
  return held;
}

// A chosen full support vector may propose a cone direction without being an
// ordinary gradient. Do not call smooth basis()/History or form its secants.
// The unchanged true first-variation gate decides whether it is ray descent.
inline Proposal full_support_cone_proposal(const ec::GridData &grid,
                          const PathState &s, const std::vector<ec::WP> &gradient,
                          fr::Counters &counts, int maximum_cone_solves) {
  ec::need(s.grid_identity == &grid && s.path.size() >= 3 &&
           gradient.size() == s.path.size(), "Full support proposal dimensions/model");
  Proposal out;
  out.mode = "full_support_true_box_cone";
  Basis b; // Geometry/sign carrier only: no claim of available ordinary normals.
  b.nodes = s.path.size();
  b.held.assign(3 * (b.nodes - 2), false);
  b.box_sign.resize(b.held.size());
  Vec g(b.held.size());
  for (std::size_t k = 0; k < g.size(); ++k) {
    const std::size_t node = k / 3 + 1, axis = k % 3;
    const ec::Q x = ec::exact(s.path[node][axis]);
    ec::need(grid.axis[axis].front() <= x && x <= grid.axis[axis].back(),
             "Full support proposal outside true box");
    b.box_sign[k] = x == grid.axis[axis].front() ? 1 :
                    x == grid.axis[axis].back() ? -1 : 0;
    g[k] = fr::finite_double(gradient[node][axis]);
  }
  ++counts.metric_calls;
  const Vec weights = ray_metric_weights(grid.g, s.path);
  ++out.cone_calls;
  const Vec d = solve_held_cone_ray_metric(weights, g, b.box_sign, b.held,
                                         out.cone, maximum_cone_solves);
  out.cone_solves += out.cone.solves;
  out.cone_last_iterate = d;
  if (!out.cone.success || !feasible(d, b)) {
    out.reason = "full_support_cone_unresolved";
    return out;
  }
  out.computed_slope = dot(g, d);
  const Vec product = ray_metric_product(weights, d);
  out.cone_quadratic_objective = out.computed_slope + 0.5 * dot(d, product);
  if (!std::isfinite(out.computed_slope) || !(out.computed_slope < 0) ||
      !std::isfinite(out.cone_quadratic_objective) || !(out.cone_quadratic_objective < 0)) {
    out.reason = "full_support_cone_has_no_usable_negative_quadratic_proposal";
    return out;
  }
  out.usable = true;
  out.reason = "full_support_cone_requires_unchanged_true_direction_and_action_gates";
  out.direction = path_direction(d, b);
  return out;
}

inline SolveResult solve(const ec::GridData &grid, const Path &path, fr::SolveOptions options = {},
                         const std::function<void(const fr::Attempt &)> &emit = {},
                         const std::function<void(const AccelerationRecord &)> &emit_acceleration = {},
                         int maximum_cone_solves = 10000) {
  // Reuse all unchanged evaluator, geometry and first-variation functions.
  using namespace face_ray;
  need(maximum_cone_solves > 0 && maximum_cone_solves <= 10000,
       "Invalid declared cone solve budget");
  need(options.maximum_updates > 0 && options.maximum_updates <= 1000 &&
       options.maximum_halvings > 0 && options.maximum_halvings <= 24 &&
       options.maximum_support_sweeps > 0 && options.maximum_support_sweeps <= 10000,
       "Invalid declared solve budgets");
  face_acceleration::SolveResult out;
  History history; // Fresh for this solve and this immutable GridData lifetime.
  const stratified_events::Policy event_policy(grid);
  auto record = [&](AccelerationRecord r) {
    r.update = out.updates;
    r.attempts_so_far = out.attempts;
    out.acceleration.push_back(std::move(r));
    if (emit_acceleration) emit_acceleration(out.acceleration.back());
  };
  auto record_proposal = [&](const Proposal &p, const std::string &phase,
                             std::size_t pairs_before) {
    AccelerationRecord r;
    r.phase = phase;
    r.mode = p.mode;
    r.reason = p.reason;
    r.usable = p.usable;
    r.pairs_before = pairs_before;
    r.pairs_after = history.size();
    r.history_pairs_used = p.history_pairs_used;
    r.linear_inverse_calls = p.linear_inverse_calls;
    r.computed_slope = p.computed_slope;
    r.quadratic_objective = p.cone_quadratic_objective;
    r.history_notes = p.history_notes;
    r.selection_required = p.selection_required;
    r.selection_valid = p.selection_valid;
    r.selection_reused = p.selection_reused;
    r.cone_direction_from_selection = p.cone_direction_from_selection;
    r.cone_calls = p.cone_calls;
    r.cone_solves = p.cone_solves;
    r.selected_physical_equalities = p.selected_physical_equalities;
    r.selection = p.selection;
    r.selection_held_equalities = p.selection.held_equalities;
    r.cone = p.cone; // Scalar base statistics only; no large per-proposal arrays.
    r.held_equalities = p.cone.held_equalities;
    // Exact membership: these are the same binary64 coordinates/axes encoded
    // in GridData's rational axes. No activity band or new slope/norm arithmetic.
    const Vec *axes[] = {&grid.g.x, &grid.g.y, &grid.g.z};
    std::vector<bool> internal_held(3 * (out.final.path.size() - 2), false);
    for (const auto &c : unavailable_contact_holds(grid, out.final, out.contacts))
      internal_held[3 * (c.node - 1) + c.axis] = true;
    auto box_sign = [&](std::size_t k) {
      const double x = out.final.path[k / 3 + 1][k % 3];
      return x == axes[k % 3]->front() ? 1 : x == axes[k % 3]->back() ? -1 : 0;
    };
    if (p.selection_valid)
      for (std::size_t k = 0; k < p.selection.active.size(); ++k)
        if (p.selection.active[k] && !internal_held[k] && box_sign(k))
          r.selected_physical_slots.push_back(k);
    r.rejected_direction_size = p.rejected_lbfgs_direction.size();
    for (std::size_t k = 0; k < p.rejected_lbfgs_direction.size(); ++k) {
      const double value = p.rejected_lbfgs_direction[k];
      if (!std::isfinite(value)) { r.rejected_nonfinite.push_back({k, value}); continue; }
      const int sign = box_sign(k);
      if ((sign == 1 && value < 0) || (sign == -1 && value > 0))
        r.rejected_outward.push_back({k, value});
      if (value != 0 && (internal_held[k] || (p.selection_valid && p.selection.active[k])))
        r.rejected_fixed.push_back({k, value});
    }
    record(std::move(r));
  };
  auto clear_history = [&](const char *reason) {
    AccelerationRecord r;
    r.phase = "history_clear";
    r.reason = reason;
    r.pairs_before = history.size();
    history.discard_direction_or_enter_nonsmooth_search();
    r.pairs_after = history.size();
    record(std::move(r));
  };
  out.initial = evaluate_path(grid, path, nullptr, false, &out.counters);
  out.final = out.initial;
  out.contacts = contacts(grid, path);
  const W strict = W(1e-7), armijo = W(1e-4);
  if (out.final.multiple_faces) { out.stop_reason = "unsupported_multiple_faces"; return out; }

  auto try_direction = [&](const Path &d, const std::string &mode, AcceptedMode accepted_mode) {
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
    const Step step = stratified_events::first_step(event_policy, grid, out.final, d);
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
      a.reason = stratified_events::rounded_geometry(event_policy, grid, a.before, a.trial, d, alpha, step);
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
        // The full old state and fresh complete event-contact set are available
        // before either is moved. This hook cannot substitute for acceptance.
        const PairReport pair = history.accepted(grid, out.final, candidate,
          unavailable_contact_holds(grid, out.final, out.contacts),
          unavailable_contact_holds(grid, candidate, a.contacts_after), accepted_mode);
        AccelerationRecord r;
        r.phase = "accepted_history";
        r.mode = mode;
        r.reason = pair.reason;
        r.pairs_before = pair.pairs_before;
        r.pairs_after = pair.pairs_after;
        r.pair = pair;
        record(std::move(r));
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
    const auto held = unavailable_contact_holds(grid, out.final, out.contacts);
    auto restricted = out.final.ordinary;
    for (std::size_t i = 1; i + 1 < path.size(); ++i)
      for (int k = 0; k < 3; ++k) restricted[i][k] = projected(restricted[i][k], out.final.path[i][k], grid.axis[k]);
    for (const auto &c : held) restricted[c.node][c.axis] = 0;
    if (vector_norm(restricted) >= strict) {
      const std::size_t pairs_before = history.size();
      const Proposal proposal = history.propose(grid, out.final, held,
        out.counters, 0, false, maximum_cone_solves);
      record_proposal(proposal, "ordinary_proposal", pairs_before);
      if (proposal.usable && try_direction(proposal.direction, proposal.mode,
                                          AcceptedMode::ordinary_restricted)) continue;
      clear_history("ordinary_direction_unusable_or_attempts_exhausted");
      // propose() may already have selected the cone after unusable/outward D.
      // Only a tried D proposal may obtain one additional cone proposal here.
      if (proposal.mode == "ordinary_principal_lbfgs") {
        const std::size_t cone_pairs_before = history.size();
        const Proposal cone = history.propose(grid, out.final, held,
          out.counters, 0, true, maximum_cone_solves);
        record_proposal(cone, "ordinary_cone_fallback", cone_pairs_before);
        if (cone.usable && try_direction(cone.direction, cone.mode,
                                         AcceptedMode::ordinary_restricted)) continue;
        clear_history("cone_direction_unusable_or_attempts_exhausted");
      }
      // Exact-box-activity projected gradient fallback is a direction proposal,
      // not an alteration of the physical feasible set or stopping gradient.
      Path fallback(path.size(), P{{0, 0, 0}});
      for (std::size_t i = 1; i + 1 < path.size(); ++i)
        for (int k = 0; k < 3; ++k) fallback[i][k] = finite_double(-restricted[i][k]);
      if (try_direction(fallback, "restricted_projected_gradient",
                        AcceptedMode::ordinary_restricted)) continue;
    }
    clear_history("entering_full_support_or_release_search");
    ++out.counters.support_calls;
    out.support = assess_support(grid, out.final, options.maximum_support_sweeps);
    out.counters.support_sweeps += out.support.sweeps;
    if (out.support.eligible && out.support.norm < strict) {
      out.approximate_full_candidate = true;
      out.stop_reason = "approximate_full_witness_requires_final_interval_audit";
      return out;
    }
    if (out.support.eligible) {
      const std::size_t support_pairs_before = history.size();
      const Proposal cone = full_support_cone_proposal(grid, out.final, out.support.vector,
        out.counters, maximum_cone_solves);
      record_proposal(cone, "full_support_cone_proposal", support_pairs_before);
      if (cone.usable && try_direction(cone.direction, "full_support_proposal_true_directional_gate",
                                       AcceptedMode::release_or_full_support)) continue;
    }
    bool released = false;
    for (const auto &c : out.contacts) {
      const bool ordinary = out.final.available[c.node][c.axis];
      const W g = out.final.ordinary[c.node][c.axis];
      for (int sign : {-1, 1}) {
        if (ordinary && !(W(sign) * g < 0)) continue;
        Path d(path.size(), P{{0, 0, 0}});
        d[c.node][c.axis] = sign;
        if (try_direction(d, ordinary ? "isolated_ordinary_release" : "aligned_true_directional_release",
                          AcceptedMode::release_or_full_support)) {
          released = true;
          break;
        }
      }
      if (released) break;
    }
    if (released) continue;
    out.stop_reason = "unresolved_restricted_search_and_finite_release_set";
    return out;
  }
  out.stop_reason = "update_budget_unresolved";
  return out;
}
} // namespace face_acceleration
