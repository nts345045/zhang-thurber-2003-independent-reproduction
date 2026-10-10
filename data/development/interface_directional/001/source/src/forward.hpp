#pragma once
#include "core.hpp"
#include "first_arrival.hpp"
#include <memory>

// A cache owns the immutable model referenced by its receiver fields. Reuse
// requires exact equality of every model axis/value and auxiliary spacing.
// Coordinates identify physical propagation problems; provider records remain
// separate in the event/station/observation tables and all solver indices.
struct ForwardFields {
  // Fields refer to this model's address; do not move the owning cache.
  ForwardFields() = default;
  ForwardFields(const ForwardFields &) = delete;
  ForwardFields &operator=(const ForwardFields &) = delete;
  Grid model;
  double spacing = 0;
  std::map<P, std::unique_ptr<first_arrival::Field>> fields;

  const first_arrival::Field &get(const Grid &g, P receiver, double h) {
    if (spacing != h || model.x != g.x || model.y != g.y ||
        model.z != g.z || model.v != g.v) {
      fields.clear();
      model = g;
      spacing = h;
    }
    auto found = fields.find(receiver);
    if (found == fields.end())
      found = fields.emplace(receiver, std::make_unique<first_arrival::Field>(
          model, receiver, spacing, 2, true)).first;
    return *found->second;
  }
};

// Return the smaller continuously integrated, locally bent action. The FMM
// field time is diagnostic only. A selected nonconverged path keeps its failed
// flag, and an extraction failure is explicit even if the direct path exists.
Ray trace_first_arrival(const Grid &g, P source, P receiver, double spacing,
                        int maxit, bool deriv, const first_arrival::Field &field) {
  Ray direct = trace(g, source, receiver, spacing, maxit, deriv);
  auto candidate = field.candidate(source);
  Ray selected = direct;
  double seeded_time = NAN;
  bool used_seed = false;
  if (candidate.success && source != receiver) {
    Ray seeded = trace(g, source, receiver, spacing, maxit, deriv, &candidate.path);
    seeded_time = seeded.time;
    if (seeded.time < selected.time) {
      selected = std::move(seeded);
      used_seed = true;
    }
  }
  selected.initialization_attempted = true;
  selected.initialization_succeeded = candidate.success;
  selected.selected_fmm_seed = used_seed;
  selected.direct_seed_time = direct.time;
  selected.fmm_seed_time = seeded_time;
  selected.initializer_field_time = candidate.field_time;
  selected.initializer_fallback_steps = candidate.fallback_steps;
  selected.initializer_message = candidate.message;
  return selected;
}
