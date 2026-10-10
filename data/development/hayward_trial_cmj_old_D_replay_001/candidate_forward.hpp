#pragma once
static int replay_trace_calls = 0;
Ray replay_candidate(const Grid &g, P source, P receiver, double spacing,
                        int maxit, bool deriv, const std::function<first_arrival::Candidate()> &provider, std::array<Ray, 2> &starts) {
  ++replay_trace_calls;
  Ray direct = trace(g, source, receiver, spacing, maxit, deriv);
  starts[0] = direct;
  auto candidate = provider();
  Ray selected = direct;
  double seeded_time = NAN;
  bool used_seed = false;
  if (candidate.success && source != receiver) {
    ++replay_trace_calls;
    Ray seeded = trace(g, source, receiver, spacing, maxit, deriv, &candidate.path);
    starts[1] = seeded;
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
