// Compact source-bound history for the standalone research candidate.
// Numerical files require native or invented identity sidecars before launch.
#include "accelerated_solve.hpp"
#include <cerrno>
#include <chrono>
#include <cstdlib>
#include <filesystem>
#include <iomanip>

namespace ec = candidate_cell;
namespace fr = face_ray;
namespace fa = face_acceleration;
namespace fs = std::filesystem;

void quoted(std::ostream &out, const std::string &value) {
  static const char digits[] = "0123456789abcdef";
  out << '"';
  for (unsigned char c : value) {
    if (c == '"' || c == '\\') out << '\\' << char(c);
    else if (c < 32) out << "\\u00" << digits[c >> 4] << digits[c & 15];
    else out << char(c);
  }
  out << '"';
}
template<class T> void hexadecimal(std::ostream &out, T value) {
  ec::need(std::isfinite(value), "Nonfinite recorded scalar");
  std::ostringstream text;
  text << std::hexfloat << value;
  quoted(out, text.str());
}
// Failure diagnostics may legitimately contain rejected nonfinite arithmetic.
// Never serialize JSON NaN/Infinity or silently replace them with numeric zero.
void diagnostic_scalar(std::ostream &out, double value) {
  out << "{\"classification\":";
  quoted(out, std::isfinite(value) ? "finite" : std::isnan(value) ? "nan" :
         std::signbit(value) ? "negative_infinity" : "positive_infinity");
  out << ",\"hex\":";
  if (std::isfinite(value)) hexadecimal(out, value);
  else out << "null";
  out << '}';
}
void pair_report(std::ostream &out, const fa::PairReport &r) {
  const bool curvature = r.reason == "computed_positive_finite_curvature_pair_stored" ||
    r.reason == "unusable_new_curvature_pair_existing_pairs_retained";
  const bool reciprocal = curvature && r.computed_curvature > 0 && std::isfinite(r.computed_curvature);
  out << "{\"stored\":" << (r.stored ? "true" : "false")
      << ",\"reset\":" << (r.reset ? "true" : "false")
      << ",\"pending_box_selection\":" << (r.pending_box_selection ? "true" : "false")
      << ",\"reason\":";
  quoted(out, r.reason);
  out << ",\"pairs_before\":" << r.pairs_before << ",\"pairs_after\":" << r.pairs_after
      << ",\"curvature_evaluated\":" << (curvature ? "true" : "false")
      << ",\"computed_curvature\":";
  if (curvature) diagnostic_scalar(out, r.computed_curvature);
  else out << "null";
  out << ",\"reciprocal_evaluated\":" << (reciprocal ? "true" : "false") << ",\"reciprocal\":";
  if (reciprocal) diagnostic_scalar(out, r.reciprocal);
  else out << "null";
  out << '}';
}
void cone_statistics(std::ostream &out, const ConeRayMetricStats &s) {
  out << "{\"success\":" << (s.success ? "true" : "false")
      << ",\"solves\":" << s.solves << ",\"releases\":" << s.releases
      << ",\"blocks\":" << s.blocks << ",\"initial_fixed\":" << s.initial_fixed
      << ",\"final_fixed\":" << s.final_fixed << ",\"message\":";
  quoted(out, s.message);
  const std::pair<const char *, double> values[] = {
    {"free_equation_max_error", s.free_equation_max_error},
    {"primal_violation", s.primal_violation}, {"dual_violation", s.dual_violation},
    {"complementarity_max_error", s.complementarity_max_error}, {"slope", s.slope},
    {"kkt_roundoff_tolerance", s.kkt_roundoff_tolerance},
    {"free_equation_relative_backward_error", s.free_equation_relative_backward_error},
    {"maximum_arithmetic_scale", s.maximum_arithmetic_scale}};
  for (const auto &v : values) {
    out << ',';
    quoted(out, v.first);
    out << ':';
    diagnostic_scalar(out, v.second);
  }
  out << '}';
}
void acceleration_record(std::ostream &out, const std::string &case_id,
                          const fa::AccelerationRecord &r) {
  const bool proposal = r.phase == "ordinary_proposal" ||
    r.phase == "ordinary_cone_fallback" || r.phase == "full_support_cone_proposal";
  const bool cone = proposal && r.mode != "ordinary_principal_lbfgs";
  // A successful cone solve can still fail the caller's feasibility check
  // before these costs are formed. Bind availability to the later branches.
  const bool cone_cost = cone && (r.usable ||
    r.reason == "cone_has_no_usable_negative_quadratic_proposal" ||
    r.reason == "full_support_cone_has_no_usable_negative_quadratic_proposal");
  out << "{\"case_id\":";
  quoted(out, case_id);
  out << ",\"update\":" << r.update << ",\"attempts_so_far\":" << r.attempts_so_far
      << ",\"phase\":";
  quoted(out, r.phase);
  out << ",\"mode\":";
  quoted(out, r.mode);
  out << ",\"reason\":";
  quoted(out, r.reason);
  out << ",\"pairs_before\":" << r.pairs_before << ",\"pairs_after\":" << r.pairs_after
      << ",\"history_pairs_used\":" << r.history_pairs_used
      << ",\"linear_inverse_callback_invocations\":" << r.linear_inverse_calls
      << ",\"proposal_evaluated\":" << (proposal ? "true" : "false")
      << ",\"usable\":";
  if (proposal) out << (r.usable ? "true" : "false");
  else out << "null";
  out << ",\"computed_slope\":";
  if (proposal && (cone ? cone_cost : r.usable)) diagnostic_scalar(out, r.computed_slope);
  else out << "null";
  out << ",\"quadratic_objective\":";
  if (cone_cost) diagnostic_scalar(out, r.quadratic_objective);
  else out << "null";
  out << ",\"history_notes\":[";
  for (std::size_t j = 0; j < r.history_notes.size(); ++j) {
    if (j) out << ',';
    quoted(out, r.history_notes[j]);
  }
  out << "],\"cone_held_equalities\":";
  if (cone) out << r.held_equalities;
  else out << "null";
  out << ",\"cone\":";
  if (cone) cone_statistics(out, r.cone);
  else out << "null";
  out << ",\"actual_cone_calls\":";
  if (proposal) out << r.cone_calls; else out << "null";
  out << ",\"actual_cone_principal_solves\":";
  if (proposal) out << r.cone_solves; else out << "null";
  out << ",\"cone_direction_from_selection\":";
  if (proposal) out << (r.cone_direction_from_selection ? "true" : "false"); else out << "null";
  out << ",\"physical_box_selection\":";
  if (proposal) {
    out << "{\"required\":" << (r.selection_required ? "true" : "false")
        << ",\"valid\":" << (r.selection_valid ? "true" : "false")
        << ",\"reused\":" << (r.selection_reused ? "true" : "false")
        << ",\"selected_physical_equalities\":";
    if (r.selection_valid) out << r.selected_physical_equalities; else out << "null";
    out << ",\"active_physical_slots\":";
    if (r.selection_valid) {
      out << '[';
      for (std::size_t k = 0; k < r.selected_physical_slots.size(); ++k) {
        if (k) out << ',';
        out << r.selected_physical_slots[k];
      }
      out << ']';
    } else out << "null";
    out << ",\"held_equalities\":";
    if (r.selection_required) out << r.selection_held_equalities; else out << "null";
    out << ",\"statistics\":";
    if (r.selection_required) cone_statistics(out, r.selection); else out << "null";
    out << '}';
  } else out << "null";
  out << ",\"rejected_D\":";
  if (proposal) {
    out << "{\"dimension\":" << r.rejected_direction_size
        << ",\"complete_direction_recorded\":false,\"scope\":\"sparse_violating_entries_only\"";
    auto violations = [&](const char *name, const std::vector<std::pair<std::size_t, double>> &entries) {
      out << ','; quoted(out, name); out << ":[";
      for (std::size_t j = 0; j < entries.size(); ++j) {
        if (j) out << ',';
        out << "{\"slot\":" << entries[j].first << ",\"value\":";
        diagnostic_scalar(out, entries[j].second); out << '}';
      }
      out << ']';
    };
    violations("nonfinite", r.rejected_nonfinite);
    violations("outward", r.rejected_outward);
    violations("fixed_coordinate", r.rejected_fixed);
    out << '}';
  } else out << "null";
  out << ",\"pair\":";
  if (r.phase == "accepted_history") pair_report(out, r.pair);
  else out << "null";
  out << '}';
}
template<class Values, class Emit>
void array(std::ostream &out, const Values &values, Emit emit) {
  out << '[';
  bool first = true;
  for (const auto &value : values) {
    if (!first) out << ',';
    first = false;
    emit(value);
  }
  out << ']';
}
template<class Values> void hexes(std::ostream &out, const Values &values) {
  array(out, values, [&](auto value) { hexadecimal(out, value); });
}
void finish(std::ofstream &out, const fs::path &path) {
  out.flush();
  out.close();
  ec::need(bool(out), "Output close failed: " + path.string());
}
void flush(std::ofstream &out, const fs::path &path) {
  out.flush();
  ec::need(bool(out), "Output flush failed: " + path.string());
}
double number(std::istream &in) {
  std::string token;
  ec::need(bool(in >> token), "Missing input number");
  char *end = nullptr;
  errno = 0;
  const double value = std::strtod(token.c_str(), &end);
  ec::need(end != token.c_str() && end == token.c_str() + token.size() &&
           std::isfinite(value) && (errno != ERANGE || value != 0),
           "Invalid, overflowing or lost nonzero binary64 token");
  return value;
}
std::size_t count(std::istream &in, std::size_t low, std::size_t high) {
  std::size_t value = 0;
  ec::need(bool(in >> value) && value >= low && value <= high, "Invalid bounded input count");
  return value;
}
std::size_t option(const char *text, std::size_t high) {
  std::istringstream in(text);
  const auto value = count(in, 1, high);
  std::string extra;
  ec::need(!(in >> extra), "Unexpected option suffix");
  return value;
}
void counters(std::ostream &out, const fr::Counters &c) {
  out << "{\"segment_calls\":" << c.segment_calls
      << ",\"reused_edges\":" << c.reused_edges
      << ",\"directional_segment_calls\":" << c.directional_segment_calls
      << ",\"metric_calls\":" << c.metric_calls
      << ",\"support_calls\":" << c.support_calls
      << ",\"support_sweeps\":" << c.support_sweeps << '}';
}
void contacts(std::ostream &out, const std::vector<fr::Contact> &values) {
  array(out, values, [&](const fr::Contact &v) {
    out << "{\"node\":" << v.node << ",\"axis\":" << v.axis
        << ",\"plane\":" << v.plane << '}';
  });
}
void nullable_vector(std::ostream &out, const ec::WP &v,
                     const std::array<bool, 3> &available) {
  out << '[';
  for (int k = 0; k < 3; ++k) {
    if (k) out << ',';
    if (available[k]) hexadecimal(out, v[k]);
    else out << "null";
  }
  out << ']';
}
void state_summary(std::ostream &out, const fr::PathState &state) {
  out << "{\"nodes\":" << state.path.size() << ",\"action_hex\":";
  hexadecimal(out, state.action);
  out << ",\"multiple_faces\":" << (state.multiple_faces ? "true" : "false")
      << ",\"fixed_polygon_source_partial_hex\":";
  nullable_vector(out, state.source_partial, state.source_ordinary);
  out << ",\"fixed_polygon_receiver_partial_hex\":";
  nullable_vector(out, state.receiver_partial, state.receiver_ordinary);
  out << '}';
}
void write_path(const fs::path &path, const fr::PathState &state) {
  std::ofstream out(path);
  ec::need(bool(out), "Cannot create path output");
  out << "node,x_hex,y_hex,z_hex,ordinary_x_hex,ordinary_y_hex,ordinary_z_hex\n";
  for (std::size_t i = 0; i < state.path.size(); ++i) {
    out << i;
    for (double x : state.path[i]) out << ',' << std::hexfloat << x;
    for (int k = 0; k < 3; ++k) {
      out << ',';
      if (i != 0 && i + 1 != state.path.size() && state.available[i][k])
        out << std::hexfloat << state.ordinary[i][k];
    }
    out << '\n';
  }
  finish(out, path);
}
void write_support(std::ostream &out, const fr::SupportAssessment &s, const fr::PathState &state) {
  out << "{\"eligible\":" << (s.eligible ? "true" : "false") << ",\"reason\":";
  quoted(out, s.reason);
  out << ",\"termination\":";
  quoted(out, s.termination);
  out << ",\"sweeps\":" << s.sweeps << ",\"theta_hex\":";
  hexes(out, s.theta);
  out << ",\"norm_hex\":";
  if (s.eligible) hexadecimal(out, s.norm);
  else out << "null";
  out << ",\"vector_hex\":";
  array(out, s.vector, [&](const ec::WP &v) { hexes(out, v); });
  out << ",\"projected_hex\":";
  array(out, s.projected, [&](const ec::WP &v) { hexes(out, v); });
  out << ",\"ordered_final_patches\":[";
  std::size_t index = 0;
  for (std::size_t edge = 0; edge < state.edges.size(); ++edge) {
    for (const auto &patch : state.edges[edge].normal_patches) {
      if (index) out << ',';
      out << "{\"index\":" << index++ << ",\"edge\":" << edge
          << ",\"axis\":" << patch.axis << ",\"plane\":" << patch.plane << ",\"left_exact\":";
      quoted(out, patch.left.str());
      out << ",\"right_exact\":";
      quoted(out, patch.right.str());
      out << ",\"minus_cell\":";
      array(out, patch.minus_cell, [&](int v) { out << v; });
      out << ",\"plus_cell\":";
      array(out, patch.plus_cell, [&](int v) { out << v; });
      out << ",\"convex\":" << (patch.convex ? "true" : "false") << '}';
    }
  }
  out << "]}";
}
int main(int argc, char **argv) {
  try {
    ec::need(argc == 7, "Use: observe_solve INPUT OUTPUT_PREFIX CASE_ID UPDATES HALVINGS SUPPORT_SWEEPS");
    ec::format();
    const fs::path prefix(argv[2]);
    const std::string case_id(argv[3]);
    const std::array<std::string, 6> suffixes{{"initial.csv", "final.csv", "attempts.jsonl", "accepted_paths.csv", "summary.json", "acceleration.jsonl"}};
    std::array<fs::path, 6> outputs;
    for (std::size_t i = 0; i < outputs.size(); ++i) {
      outputs[i] = prefix.string() + "_" + suffixes[i];
      ec::need(!fs::exists(outputs[i]) && !fs::is_symlink(outputs[i]), "Preserve existing output: " + outputs[i].string());
      ec::need(fs::is_regular_file(outputs[i].string() + ".identifiers.json"), "Missing prelaunch output identity sidecar");
    }
    std::ifstream input(argv[1]);
    ec::need(bool(input), "Cannot read saved polygon input");
    const std::array<std::size_t, 3> sizes{{count(input, 2, 256), count(input, 2, 256), count(input, 2, 256)}};
    ec::need(sizes[0] * sizes[1] * sizes[2] <= 1000000, "Grid exceeds bounded observer capacity");
    Grid model;
    Vec *axes[] = {&model.x, &model.y, &model.z};
    for (int k = 0; k < 3; ++k)
      for (std::size_t i = 0; i < sizes[k]; ++i) axes[k]->push_back(number(input));
    for (std::size_t i = 0; i < sizes[0] * sizes[1] * sizes[2]; ++i) model.v.push_back(number(input));
    fr::Path path(count(input, 3, 10000));
    for (auto &point : path)
      for (double &x : point) x = number(input);
    std::string extra;
    ec::need(!(input >> extra), "Unexpected saved polygon suffix");
    fr::SolveOptions options;
    options.maximum_updates = option(argv[4], 1000);
    options.maximum_halvings = option(argv[5], 24);
    options.maximum_support_sweeps = option(argv[6], 10000);
    std::ofstream attempts(outputs[2]), accepted(outputs[3]), acceleration(outputs[5]);
    ec::need(bool(attempts) && bool(accepted) && bool(acceleration), "Cannot create streaming histories");
    accepted << "update,node,x_hex,y_hex,z_hex\n";
    std::size_t callback_count = 0, accepted_count = 0, acceleration_count = 0;
    std::size_t inverse_calls = 0, cone_solves = 0, cone_proposals = 0, cone_calls = 0;
    std::size_t selection_requests = 0, fresh_selection_calls = 0, selection_reuses = 0, pending_pairs = 0;
    const auto started = std::chrono::steady_clock::now();
    const ec::GridData grid(model);
    const auto decoded = std::chrono::steady_clock::now();
    auto record = [&](const fr::Attempt &a) {
      ++callback_count;
      attempts << "{\"case_id\":";
      quoted(attempts, case_id);
      attempts << ",\"update\":" << a.update << ",\"attempt\":" << a.attempt << ",\"mode\":";
      quoted(attempts, a.mode);
      attempts << ",\"reason\":";
      quoted(attempts, a.reason);
      attempts << ",\"alpha_exact\":";
      quoted(attempts, a.alpha.str());
      attempts << ",\"nominal_slope_hex\":";
      hexadecimal(attempts, a.nominal_slope);
      attempts << ",\"actual_slope_hex\":";
      if (a.actual_evaluated) hexadecimal(attempts, a.actual_slope);
      else attempts << "null";
      attempts << ",\"paired_change_hex\":";
      if (a.action_evaluated) hexadecimal(attempts, a.paired_change);
      else attempts << "null";
      attempts << ",\"armijo_rhs_hex\":";
      hexadecimal(attempts, a.armijo_rhs);
      attempts << ",\"trial_action_hex\":";
      if (a.action_evaluated) hexadecimal(attempts, a.trial_action);
      else attempts << "null";
      attempts << ",\"actual_evaluated\":" << (a.actual_evaluated ? "true" : "false")
               << ",\"action_evaluated\":" << (a.action_evaluated ? "true" : "false")
               << ",\"accepted\":" << (a.accepted ? "true" : "false")
               << ",\"no_op\":" << (a.no_op ? "true" : "false")
               << ",\"event_limited\":" << (a.event_limited ? "true" : "false")
               << ",\"event_hits\":";
      contacts(attempts, a.event_hits);
      attempts << ",\"contacts_before\":";
      contacts(attempts, a.contacts_before);
      attempts << ",\"contacts_after\":";
      contacts(attempts, a.contacts_after);
      attempts << ",\"counters\":";
      counters(attempts, a.counters);
      attempts << "}\n";
      flush(attempts, outputs[2]);
      if (a.accepted) {
        ++accepted_count;
        for (std::size_t i = 0; i < a.trial.size(); ++i) {
          accepted << a.update << ',' << i;
          for (double x : a.trial[i]) accepted << ',' << std::hexfloat << x;
          accepted << '\n';
        }
        flush(accepted, outputs[3]);
      }
    };
    auto record_acceleration = [&](const fa::AccelerationRecord &r) {
      ++acceleration_count;
      inverse_calls += r.linear_inverse_calls;
      cone_solves += r.cone_solves; // Actual work, never a cached statistic's historical count.
      cone_calls += r.cone_calls;
      selection_requests += r.selection_required;
      fresh_selection_calls += r.selection_required && !r.selection_reused && r.cone_calls > 0;
      selection_reuses += r.selection_reused;
      pending_pairs += r.phase == "accepted_history" && r.pair.pending_box_selection;
      const bool cone = r.phase == "ordinary_cone_fallback" || r.phase == "full_support_cone_proposal" ||
        (r.phase == "ordinary_proposal" && r.mode == "ordinary_held_true_box_cone");
      cone_proposals += cone;
      acceleration_record(acceleration, case_id, r);
      acceleration << '\n';
      flush(acceleration, outputs[5]);
    };
    const fa::SolveResult result = fa::solve(grid, path, options, record, record_acceleration);
    const auto finished = std::chrono::steady_clock::now();
    ec::need(callback_count == result.attempts && accepted_count == result.updates &&
             acceleration_count == result.acceleration.size(), "History count mismatch");
    finish(attempts, outputs[2]);
    finish(accepted, outputs[3]);
    finish(acceleration, outputs[5]);
    write_path(outputs[0], result.initial);
    write_path(outputs[1], result.final);
    std::ofstream summary(outputs[4]);
    ec::need(bool(summary), "Cannot create solve summary");
    summary << "{\"status\":\"completed_bounded_saved_polygon_reoptimization\",\"case_id\":";
    quoted(summary, case_id);
    summary << ",\"stop_reason\":";
    quoted(summary, result.stop_reason);
    summary << ",\"approximate_full_candidate\":" << (result.approximate_full_candidate ? "true" : "false")
            << ",\"candidate_convergence_status\":null,\"original_flags_modified\":false"
               ",\"trace_calls\":0,\"field_calls\":0,\"resampling_calls\":0,\"merge_calls\":0"
               ",\"updates\":" << result.updates << ",\"attempts\":" << result.attempts
            << ",\"limits\":{\"updates\":" << options.maximum_updates
            << ",\"halvings\":" << options.maximum_halvings
            << ",\"support_sweeps\":" << options.maximum_support_sweeps << '}'
            << ",\"initial\":";
    state_summary(summary, result.initial);
    summary << ",\"final\":";
    state_summary(summary, result.final);
    summary << ",\"contacts\":";
    contacts(summary, result.contacts);
    summary << ",\"support\":";
    write_support(summary, result.support, result.final);
    summary << ",\"counters\":";
    counters(summary, result.counters);
    summary << ",\"acceleration\":{\"records\":" << acceleration_count
            << ",\"linear_inverse_callback_invocations\":" << inverse_calls
            << ",\"cone_proposals\":" << cone_proposals << ",\"performed_cone_principal_solves\":" << cone_solves
            << ",\"actual_cone_calls\":" << cone_calls
            << ",\"selection_requests\":" << selection_requests
            << ",\"fresh_selection_calls\":" << fresh_selection_calls
            << ",\"selection_reuses\":" << selection_reuses
            << ",\"pending_box_pair_records\":" << pending_pairs
            << ",\"maximum_cone_solves_per_proposal\":10000,\"history_pair_limit\":16}"
            << ",\"grid_setup_seconds_hex\":";
    hexadecimal(summary, std::chrono::duration<double>(decoded - started).count());
    summary << ",\"solve_seconds_hex\":";
    hexadecimal(summary, std::chrono::duration<double>(finished - decoded).count());
    summary << ",\"history_scope\":\"Every completed attempt scalar and accepted polygon; intermediate slopes and paired sums are source-bound, not independent exact-action certificates.\""
               ",\"endpoint_scope\":\"Fixed-polygon endpoint partials only; optimized-ray source accuracy and first arrival require separate evidence.\"}\n";
    finish(summary, outputs[4]);
    std::cout << "completed " << case_id << " updates=" << result.updates << " attempts=" << result.attempts << '\n';
    std::cout.flush();
    ec::need(bool(std::cout), "stdout write failed");
    return 0;
  } catch (const std::exception &error) {
    std::cerr << "preserved candidate failure: " << error.what() << '\n';
    return 1;
  }
}
