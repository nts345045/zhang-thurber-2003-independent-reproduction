#pragma once
#include "core.hpp"
#include "first_arrival.hpp"
#include <exception>
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

  void reset_if_changed(const Grid &g, double h) {
    if (spacing != h || model.x != g.x || model.y != g.y ||
        model.z != g.z || model.v != g.v) {
      fields.clear();
      model = g;
      spacing = h;
    }
  }

  // Cache mutation is serial. Only independent constructors run in parallel;
  // they read the same immutable model and write distinct temporary slots.
  // On construction failure no new field is published. Existing fields survive
  // unless the model/spacing changed, which invalidates them before construction.
  // The caller must serialize calls to prepare/get on a particular cache.
  void prepare(const Grid &g, const std::vector<P> &receivers, double h,
               std::size_t *failed_receiver = nullptr) {
    if (failed_receiver) *failed_receiver = receivers.size();
    reset_if_changed(g, h);
    std::map<P, std::size_t> pending;
    std::vector<P> missing;
    std::vector<std::size_t> first_request;
    for (std::size_t i = 0; i < receivers.size(); ++i) {
      const P receiver = receivers[i];
      bool finite = std::all_of(receiver.begin(), receiver.end(),
                                [](double x) { return std::isfinite(x); });
      // Nonfinite coordinates cannot be ordered safely as map keys. Pass them
      // to the unchanged constructor so its exception retains request order.
      if (finite && (fields.find(receiver) != fields.end() ||
                     !pending.emplace(receiver, missing.size()).second))
        continue;
      missing.push_back(receiver);
      first_request.push_back(i);
    }
    std::vector<std::unique_ptr<first_arrival::Field>> built(missing.size());
    std::vector<std::exception_ptr> errors(missing.size());
#pragma omp parallel for schedule(dynamic)
    for (std::size_t i = 0; i < missing.size(); ++i) {
      try {
        built[i] = std::make_unique<first_arrival::Field>(model, missing[i], spacing, 2, true);
      } catch (...) {
        errors[i] = std::current_exception();
      }
    }
    for (std::size_t i = 0; i < missing.size(); ++i)
      if (errors[i]) {
        if (failed_receiver) *failed_receiver = first_request[i];
        std::rethrow_exception(errors[i]);
      }
    for (std::size_t i = 0; i < missing.size(); ++i)
      fields.emplace(missing[i], std::move(built[i]));
  }

  const first_arrival::Field &get(const Grid &g, P receiver, double h) {
    reset_if_changed(g, h);
    if (!std::all_of(receiver.begin(), receiver.end(),
                     [](double x) { return std::isfinite(x); }))
      throw std::runtime_error("Invalid FMM receiver or requested spacing");
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
