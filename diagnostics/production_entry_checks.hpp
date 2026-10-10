#pragma once
#include "../src/forward.hpp"

// Exact parity for the new entry points against the generated prototype.
// No tolerance is used. Initializer metadata are checked separately because
// the prototype Ray does not contain that metadata.
struct ProductionEntryChecks {
  std::ofstream output;
  int calls = 0, failures = 0;

  void open(const std::string &path) {
    output.open(path);
    if (!output) throw std::runtime_error("Cannot open production entry checks");
    output << std::setprecision(17)
           << "call,source_x,source_y,source_z,receiver_x,receiver_y,receiver_z,path_spacing_km,"
              "seeded_entry_checked,seeded_time_equal,seeded_path_equal,seeded_source_derivative_equal,"
              "seeded_velocity_derivatives_equal,seeded_lengths_equal,seeded_optimizer_state_equal,"
              "selected_time_equal,selected_path_equal,selected_source_derivative_equal,"
              "selected_velocity_derivatives_equal,selected_lengths_equal,selected_optimizer_state_equal,"
              "initializer_metadata_equal,prototype_selected_time_s,production_selected_time_s,passed\n";
  }

  bool enabled() const { return output.is_open(); }

  static std::array<bool, 6> equal(const Ray &a, const Ray &b) {
    return {a.time == b.time, a.path == b.path, a.source == b.source,
            a.dv == b.dv, a.length == b.length,
            a.iterations == b.iterations && a.merged_nodes == b.merged_nodes &&
            a.gradient == b.gradient && a.raw_gradient == b.raw_gradient &&
            a.converged == b.converged};
  }

  // Replace the returned rays with the production results, so all downstream
  // analytic gates test that entry. The prototype remains the exact control.
  void compare(const Grid &g, const first_arrival::Field &field, P a, P b,
               double spacing, const first_arrival::Candidate &seed,
               const Ray &direct, Ray &bent, Ray &best, bool selected_seed) {
    if (!enabled()) return;
    bool seeded = seed.success && a != b;
    Ray production_bent;
    std::array<bool, 6> seed_equal{true, true, true, true, true, true};
    if (seeded) {
      production_bent = trace(g, a, b, spacing, 1000, true, &seed.path);
      seed_equal = equal(bent, production_bent);
    }
    Ray selected = trace_first_arrival(g, a, b, spacing, 1000, true, field);
    auto selected_equal = equal(best, selected);
    bool metadata = selected.initialization_attempted &&
        selected.initialization_succeeded == seed.success &&
        selected.selected_fmm_seed == selected_seed &&
        selected.direct_seed_time == direct.time &&
        (seeded ? selected.fmm_seed_time == bent.time : std::isnan(selected.fmm_seed_time)) &&
        selected.initializer_field_time == seed.field_time &&
        selected.initializer_fallback_steps == seed.fallback_steps &&
        selected.initializer_message == seed.message;
    bool passed = metadata && std::all_of(seed_equal.begin(), seed_equal.end(), [](bool x) { return x; }) &&
        std::all_of(selected_equal.begin(), selected_equal.end(), [](bool x) { return x; });
    output << calls++;
    for (P p : {a, b}) for (double x : p) output << ',' << x;
    output << ',' << spacing << ',' << seeded;
    for (bool x : seed_equal) output << ',' << x;
    for (bool x : selected_equal) output << ',' << x;
    output << ',' << metadata << ',' << best.time << ',' << selected.time << ',' << passed << std::endl;
    failures += !passed;
    if (seeded) bent = std::move(production_bent);
    best = std::move(selected);
  }
};
