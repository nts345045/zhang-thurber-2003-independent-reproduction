// Invented fields only: exact geometry/action bounds, monotone extraction,
// failure reporting, and one full-domain timing measurement. No ray bending.
#include "first_arrival_fmm.hpp"
#include <chrono>
#include <random>

void require(bool condition, const char *message) {
  if (!condition)
    throw std::runtime_error(message);
}

// Independent long-double bisection of the defining max-operator equation.
long double reference_time(const first_arrival::UpwindAxes &axes, double slowness) {
  long double lo = INFINITY, hi = INFINITY;
  for (auto axis : axes)
    for (auto d : axis)
      if (d.inverse_h > 0) {
        lo = std::min(lo, static_cast<long double>(d.offset));
        hi = std::min(hi, d.offset + slowness / static_cast<long double>(d.inverse_h));
      }
  for (int iteration = 0; iteration < 160; ++iteration) {
    long double midpoint = (lo + hi) / 2, sum = 0;
    for (auto axis : axes) {
      long double derivative = 0;
      for (auto d : axis)
        derivative = std::max(derivative, d.inverse_h * (midpoint - d.offset));
      sum += derivative * derivative;
    }
    if (sum < slowness * static_cast<long double>(slowness)) lo = midpoint;
    else hi = midpoint;
  }
  return (lo + hi) / 2;
}

int mixed_order_checks(std::ostream &output) {
  const double epsilon = std::numeric_limits<double>::epsilon();
  int all_failures = 0, cases = 0, failures = 0, bisections = 0;
  double maximum_error = 0, maximum_scaled = 0;
  auto compare = [&](double value, double exact) {
    double error = std::abs(value - exact);
    double scaled = error / (epsilon * (1 + std::abs(exact)));
    maximum_error = std::max(maximum_error, error);
    maximum_scaled = std::max(maximum_scaled, scaled);
    // A floating-point arithmetic check, not a path accuracy/convergence gate.
    failures += !std::isfinite(value) || scaled > 128;
    ++cases;
  };
  auto row = [&](const std::string &name, int order, const first_arrival::FieldStats &s) {
    output << name << ',' << order << ',' << cases << ',' << failures << ','
           << maximum_error << ',' << maximum_scaled << ','
           << s.first_order_direction_evaluations << ','
           << s.second_order_direction_evaluations << ',' << s.second_order_ineligible << ','
           << s.causal_fallback_updates << ',' << s.root_bisection_updates + bisections << ','
           << s.second_neighbor_revisits << '\n';
    all_failures += failures;
    cases = failures = bisections = 0;
    maximum_error = maximum_scaled = 0;
  };
  output << std::setprecision(17)
         << "case,fmm_order,cases,failures,max_error_s,max_error_in_epsilon_units,"
            "first_order_direction_evaluations,second_order_direction_evaluations,"
            "second_order_ineligible,causal_fallback_updates,root_bisection_updates,"
            "second_neighbor_revisits\n";
  std::mt19937 random(91273);
  std::uniform_real_distribution<double> uniform(0, 1);
  for (int test = 0; test < 100000; ++test) {
    first_arrival::UpwindAxes axes{};
    for (auto &axis : axes)
      for (auto &d : axis) {
        d.offset = 10 * uniform(random) - 2;
        d.inverse_h = uniform(random) < .2 ? 0 :
            (uniform(random) < .5 ? 1 : 1.5) / (.2 + 2 * uniform(random));
      }
    axes[0][0].inverse_h = 1;
    double slowness = .1 + uniform(random);
    bool bisection = false;
    compare(first_arrival::mixed_order_time(axes, slowness, &bisection),
            reference_time(axes, slowness));
    bisections += bisection;
  }
  row("mixed_root_reference", 2, {});
  // With these opposite directions, the larger raw-neighbor time has the
  // steeper second-order derivative and controls the root T=1.7 s.
  for (int axis = 0; axis < 3; ++axis)
    for (int side = 0; side < 2; ++side) {
      first_arrival::UpwindAxes axes{};
      axes[axis][side] = {1, 1};
      axes[axis][1 - side] = {1.2, 1.5};
      compare(first_arrival::mixed_order_time(axes, .75), 1.7);
    }
  row("opposite_direction_switch", 2, {});
  for (double shift : {0., 1e6, 1e12})
    for (double slowness : {std::nextafter(.6, 0.), .6, std::nextafter(.6, 1.)})
      for (int axis = 0; axis < 3; ++axis)
        for (int side = 0; side < 2; ++side) {
          first_arrival::UpwindAxes axes{};
          axes[axis][side] = {shift + 1, 1};
          axes[axis][1 - side] = {shift + 1.2, 1.5};
          compare(first_arrival::mixed_order_time(axes, slowness),
                  reference_time(axes, slowness));
        }
  row("operator_crossing_and_common_time_shift", 2, {});
  std::array<int, 3> permutation{0, 1, 2};
  P gradient{.17, .11, .07}, spacing{.25, .5, .75};
  do {
    for (int reflection = 0; reflection < 8; ++reflection)
      for (int second_order_axes = 0; second_order_axes < 8; ++second_order_axes) {
        first_arrival::UpwindAxes axes{};
        for (int axis = 0; axis < 3; ++axis) {
          double slope = gradient[permutation[axis]], h = spacing[axis];
          double near = 3 - slope * h, far = 3 - 2 * slope * h;
          int side = (reflection >> axis) & 1;
          axes[axis][side] = (second_order_axes >> axis) & 1 ?
              first_arrival::UpwindDerivative{near + (near - far) / 3, 1.5 / h} :
              first_arrival::UpwindDerivative{near, 1 / h};
        }
        compare(first_arrival::mixed_order_time(axes, norm(gradient)), 3);
      }
  } while (std::next_permutation(permutation.begin(), permutation.end()));
  row("affine_travel_time_permutations_reflections", 2, {});
  Grid g;
  g.x = g.y = g.z = {-2, 0, 2};
  g.v.assign(g.size(), 4);
  // Full field comparisons use reflection-invariant geometry and velocities.
  // Include an on-grid receiver, where exact equal-time acceptance ties occur.
  for (int order : {1, 2}) {
    first_arrival::FieldStats totals;
    for (P receiver : {P{.13, .24, -.35}, P{0, 0, 0}}) {
      P source{-1.8, -1.3, 1.3};
      first_arrival::Field reference(g, receiver, .5, order);
      double exact = reference.interpolated_time(source);
      for (int reflection = 0; reflection < 8; ++reflection) {
        P r = receiver, p = source;
        for (int axis = 0; axis < 3; ++axis)
          if ((reflection >> axis) & 1) { r[axis] = -r[axis]; p[axis] = -p[axis]; }
        first_arrival::Field field(g, r, .5, order);
        auto candidate = field.candidate(p);
        require(candidate.success && candidate.path.front() == p && candidate.path.back() == r,
                "Reflected field path failed to preserve endpoints");
        compare(field.interpolated_time(p), exact);
        std::string geometry = receiver == P{0, 0, 0} ? "on_grid" : "off_grid";
        row("point_source_" + geometry + "_reflection_" + std::to_string(reflection),
            order, field.stats);
        totals.first_order_direction_evaluations += field.stats.first_order_direction_evaluations;
        totals.second_order_direction_evaluations += field.stats.second_order_direction_evaluations;
        totals.second_order_ineligible += field.stats.second_order_ineligible;
        totals.causal_fallback_updates += field.stats.causal_fallback_updates;
        totals.root_bisection_updates += field.stats.root_bisection_updates;
        totals.second_neighbor_revisits += field.stats.second_neighbor_revisits;
      }
    }
    if (order == 2)
      require(totals.second_order_direction_evaluations > 0 && totals.second_order_ineligible > 0,
              "Second-order/reflected fallback stencils were not exercised");
  }
  for (int invalid : {0, 3}) {
    bool rejected = false;
    try { first_arrival::Field field(g, {0, 0, 0}, .5, invalid); }
    catch (const std::runtime_error &) { rejected = true; }
    require(rejected, "Invalid FMM stencil order accepted");
  }
  std::cout << "mixed_order_checks failures=" << all_failures
            << " random_roots=100000 operator_switch_cases=60 affine_cases=384"
               " field_reflections=32 invalid_orders=2\n";
  return all_failures ? 1 : 0;
}

int seed_rule_checks(std::ostream &output) {
  Grid g;
  g.x = g.y = g.z = {-2, 0, 2};
  g.v.assign(g.size(), 4);
  const std::array<P, 7> receivers{P{.13, .24, -.35}, P{0, .24, -.35}, P{0, 0, -.35},
                                 P{0, 0, 0}, P{2, .24, -.35}, P{2, 2, -.35}, P{2, 2, 2}};
  const char *names[] = {"off_grid", "interior_face", "interior_edge", "interior_node",
                         "domain_face", "domain_edge", "domain_corner"};
  output << std::setprecision(17)
         << "geometry,fmm_order,closed_seed_cells,reflection,seed_nodes,field_time_s,"
            "unreflected_field_time_s,reflection_error_s,reflection_passed,"
            "off_grid_bitwise_unchanged,path_success,endpoint_error_km,"
            "nondecreasing_field_steps,seed_action_s,exact_homogeneous_time_s,"
            "causal_fallback_updates,second_neighbor_revisits\n";
  int failures = 0, baseline_reflection_failures = 0, cases = 0;
  for (int order : {1, 2})
    for (std::size_t geometry = 0; geometry < receivers.size(); ++geometry)
      for (bool closed : {false, true}) {
        P source{-1.8, -1.3, 1.3}, receiver = receivers[geometry];
        first_arrival::Field reference(g, receiver, .5, order, closed);
        double reference_time = reference.interpolated_time(source);
        for (int reflection = 0; reflection < 8; ++reflection) {
          P p = source, r = receiver;
          for (int axis = 0; axis < 3; ++axis)
            if ((reflection >> axis) & 1) { p[axis] = -p[axis]; r[axis] = -r[axis]; }
          first_arrival::Field field(g, r, .5, order, closed);
          auto candidate = field.candidate(p);
          double time = field.interpolated_time(p), error = std::abs(time - reference_time);
          bool symmetric = error <= 128 * std::numeric_limits<double>::epsilon() *
                                   (1 + std::abs(reference_time));
          if (!closed && !symmetric) ++baseline_reflection_failures;
          bool unchanged = true;
          if (geometry == 0) {
            first_arrival::Field alternative(g, r, .5, order, !closed);
            for (int k = 0; k <= 8; ++k)
              for (int j = 0; j <= 8; ++j)
                for (int i = 0; i <= 8; ++i) {
                  P node{-2 + i * .5, -2 + j * .5, -2 + k * .5};
                  unchanged = unchanged && field.interpolated_time(node) ==
                                             alternative.interpolated_time(node);
                }
            unchanged = unchanged && candidate.path == alternative.candidate(p).path;
          }
          double endpoint_error = norm(candidate.path.front() - p) +
                                  norm(candidate.path.back() - r);
          int nondecreasing = 0;
          for (std::size_t i = 1; i < candidate.path.size(); ++i)
            nondecreasing += !(field.interpolated_time(candidate.path[i]) <
                               field.interpolated_time(candidate.path[i - 1]));
          double action = candidate.success ? path_eval(g, candidate.path) : NAN;
          double exact = norm(p - r) / 4;
          bool passed = candidate.success && endpoint_error == 0 && nondecreasing == 0 &&
                        std::isfinite(action) && action + 1e-12 >= exact && unchanged &&
                        (!closed || symmetric);
          failures += !passed;
          ++cases;
          output << names[geometry] << ',' << order << ',' << closed << ',' << reflection
                 << ',' << field.stats.seed_nodes << ',' << time << ',' << reference_time
                 << ',' << error << ',' << symmetric << ',' << unchanged << ','
                 << candidate.success << ',' << endpoint_error << ',' << nondecreasing
                 << ',' << action << ',' << exact << ',' << field.stats.causal_fallback_updates
                 << ',' << field.stats.second_neighbor_revisits << '\n';
        }
      }
  std::cout << "seed_rule_checks cases=" << cases << " failures=" << failures
            << " preserved_half_open_reflection_failures=" << baseline_reflection_failures << '\n';
  return failures ? 1 : 0;
}

int main(int argc, char **argv) {
  if (argc < 2 || argc > 4)
    throw std::runtime_error("Usage: check_fmm_field OUTPUT.csv [1|2] [full|closed-cell|mixed-order|seed-rules]");
  std::ofstream output(argv[1]);
  if (!output)
    throw std::runtime_error("Cannot open field-check output");
  int order = 1, argument = 2;
  if (argument < argc && (std::string(argv[argument]) == "1" ||
                          std::string(argv[argument]) == "2"))
    order = std::stoi(argv[argument++]);
  std::string suite = argument < argc ? argv[argument++] : "full";
  require(argument == argc && (suite == "full" || suite == "closed-cell" ||
                              (suite == "mixed-order" || suite == "seed-rules")), "Unknown field-check suite");
  if (suite == "mixed-order") return mixed_order_checks(output);
  if (suite == "seed-rules") return seed_rule_checks(output);
  if (suite == "closed-cell") {
    // Invented receiver near a seed-cell diagonal midpoint. Its closest
    // corner is more than h/2 away; seven reflections lie on upper cell faces.
    Grid g;
    g.x = g.y = g.z = {0, 1, 2};
    g.v.assign(g.size(), 4);
    output << std::setprecision(17)
           << "reflection,success,message,source_x,source_y,source_z,receiver_x,"
              "receiver_y,receiver_z,field_time_s,exact_time_s,seed_action_s,"
              "endpoint_error_km,path_nodes\n";
    int failures = 0;
    for (int reflection = 0; reflection < 8; ++reflection) {
      P receiver{}, source{};
      for (int axis = 0; axis < 3; ++axis) {
        source[axis] = (reflection >> axis) & 1;
        receiver[axis] = source[axis] ? .51 : .49;
      }
      first_arrival::Field field(g, receiver, 1, order);
      auto candidate = field.candidate(source);
      double exact = norm(source - receiver) / 4;
      double action = candidate.success ? path_eval(g, candidate.path) : NAN;
      double endpoint_error = norm(candidate.path.front() - source) +
                              norm(candidate.path.back() - receiver);
      bool passed = candidate.success && endpoint_error == 0 &&
                    candidate.path.size() == 2 && std::abs(action - exact) <= 1e-12;
      failures += !passed;
      output << reflection << ',' << passed << ',' << candidate.message;
      for (double x : source) output << ',' << x;
      for (double x : receiver) output << ',' << x;
      output << ',' << candidate.field_time << ',' << exact << ',' << action
             << ',' << endpoint_error << ',' << candidate.path.size() << '\n';
    }
    std::cout << "closed_receiver_cell cases=8 failures=" << failures << '\n';
    return failures ? 1 : 0;
  }
  output << std::setprecision(15)
         << "case,spacing_km,nodes,build_seconds,source_x,source_y,source_z,"
            "receiver_x,receiver_y,receiver_z,field_time_s,seed_action_s,"
            "exact_time_s,path_nodes,descent_steps,fallback_steps,endpoint_error_km,"
            "nondecreasing_field_steps,fmm_order,first_order_direction_evaluations,"
            "second_order_direction_evaluations,second_order_ineligible,"
            "causal_fallback_updates,root_bisection_updates,second_neighbor_revisits\n";
  Grid homogeneous;
  homogeneous.x = {-2, 0, 2};
  homogeneous.y = {-2, 2};
  homogeneous.z = {-1, 0, 3};
  homogeneous.v.assign(homogeneous.size(), 4);
  int paths = 0, invalid_sources = 0;
  auto inspect = [&](const Grid &g, const first_arrival::Field &field,
                     P source, P receiver, double spacing, double seconds,
                     const std::string &name, double exact) {
    auto candidate = field.candidate(source);
    require(candidate.success, candidate.message.c_str());
    require(candidate.path.front() == source && candidate.path.back() == receiver,
            "FMM extraction changed an exact endpoint");
    int nondecreasing = 0;
    for (std::size_t i = 1; i < candidate.path.size(); ++i)
      nondecreasing += !(field.interpolated_time(candidate.path[i]) <
                         field.interpolated_time(candidate.path[i - 1]));
    require(nondecreasing == 0, "FMM path does not strictly descend its field");
    double action = path_eval(g, candidate.path);
    require(std::isfinite(action) && action >= 0, "Nonfinite/negative seed action");
    // In a homogeneous medium every feasible polyline is at least as long as
    // the exact straight path; this tests a physical bound, not an FMM stencil.
    if (std::isfinite(exact))
      require(action + 1e-12 >= exact, "Homogeneous seed beats the exact action");
    double endpoint_error = norm(candidate.path.front() - source) +
                            norm(candidate.path.back() - receiver);
    output << name << ',' << spacing << ',' << field.node_count() << ',' << seconds;
    for (double x : source) output << ',' << x;
    for (double x : receiver) output << ',' << x;
    output << ',' << candidate.field_time << ',' << action << ',' << exact << ','
           << candidate.path.size() << ',' << candidate.descent_steps << ','
           << candidate.fallback_steps << ',' << endpoint_error << ',' << nondecreasing
           << ',' << field.order() << ',' << field.stats.first_order_direction_evaluations
           << ',' << field.stats.second_order_direction_evaluations
           << ',' << field.stats.second_order_ineligible
           << ',' << field.stats.causal_fallback_updates
           << ',' << field.stats.root_bisection_updates
           << ',' << field.stats.second_neighbor_revisits << '\n';
    ++paths;
  };
  for (P receiver : {P{.13, .24, -.35}, P{2, 2, -1}, P{0, 0, 0}})
    for (double spacing : {1., .5, .25}) {
      auto start = std::chrono::steady_clock::now();
      first_arrival::Field field(homogeneous, receiver, spacing, order);
      double seconds = std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
      require(field.accepted_nodes == field.node_count(), "Positive-speed field is incomplete");
      for (P source : {P{-1.8, -1.3, 2.3}, P{1.5, -2., -1}, P{-.2, .3, .1}, receiver})
        inspect(homogeneous, field, source, receiver, spacing, seconds,
                "homogeneous", norm(source - receiver) / 4);
      for (P source : {P{NAN, 0, 0}, P{9, 0, 0}}) {
        require(!field.candidate(source).success, "Invalid source was accepted");
        ++invalid_sources;
      }
    }
  int invalid_fields = 0;
  for (double spacing : {0., -1., double(NAN)}) {
    bool rejected = false;
    try { first_arrival::Field field(homogeneous, {0, 0, 0}, spacing, order); }
    catch (const std::runtime_error &) { rejected = true; }
    require(rejected, "Invalid spacing was accepted");
    ++invalid_fields;
  }
  for (double velocity : {0., -1., double(NAN)}) {
    Grid bad = homogeneous;
    bad.v[0] = velocity;
    bool rejected = false;
    try { first_arrival::Field field(bad, {0, 0, 0}, .5, order); }
    catch (const std::runtime_error &) { rejected = true; }
    require(rejected, "Invalid velocity was accepted");
    ++invalid_fields;
  }
  for (P receiver : {P{NAN, 0, 0}, P{9, 0, 0}}) {
    bool rejected = false;
    try { first_arrival::Field field(homogeneous, receiver, .5, order); }
    catch (const std::runtime_error &) { rejected = true; }
    require(rejected, "Invalid receiver was accepted");
    ++invalid_fields;
  }
  Grid full;
  full.x = {-35, -20, 0, 20, 35};
  full.y = {-30, 0, 30};
  full.z = {-1, 0, 4, 8, 12, 20};
  full.v.resize(full.size());
  for (int k = 0; k < int(full.z.size()); ++k)
    for (int j = 0; j < int(full.y.size()); ++j)
      for (int i = 0; i < int(full.x.size()); ++i)
        full.v[full.id(i, j, k)] = 4 + .2 * std::max(0., full.z[k]);
  P receiver{12.13, -5.24, -.35};
  auto start = std::chrono::steady_clock::now();
  first_arrival::Field field(full, receiver, .5, order);
  double seconds = std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
  require(field.accepted_nodes == field.node_count(), "Full-domain field is incomplete");
  for (P source : {P{-30, 20, 5}, P{35, 30, 20}, P{-35, -30, -1}})
    inspect(full, field, source, receiver, .5, seconds, "synthetic_full_domain", NAN);
  std::cout << "PASS paths=" << paths << " invalid_sources=" << invalid_sources
            << " invalid_fields=" << invalid_fields << " full_domain_nodes="
            << field.node_count() << " full_domain_seconds=" << seconds << '\n';
}
