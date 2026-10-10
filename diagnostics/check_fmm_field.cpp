// Invented fields only: exact geometry/action bounds, monotone extraction,
// failure reporting, and one full-domain timing measurement. No ray bending.
#include "first_arrival_fmm.hpp"
#include <chrono>

void require(bool condition, const char *message) {
  if (!condition)
    throw std::runtime_error(message);
}

int main(int argc, char **argv) {
  if (argc < 2 || argc > 3)
    throw std::runtime_error("Usage: check_fmm_field OUTPUT.csv [closed-cell]");
  std::ofstream output(argv[1]);
  if (!output)
    throw std::runtime_error("Cannot open field-check output");
  if (argc == 3) {
    require(std::string(argv[2]) == "closed-cell", "Unknown field-check suite");
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
      first_arrival::Field field(g, receiver, 1);
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
            "nondecreasing_field_steps\n";
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
           << candidate.fallback_steps << ',' << endpoint_error << ',' << nondecreasing << '\n';
    ++paths;
  };
  for (P receiver : {P{.13, .24, -.35}, P{2, 2, -1}, P{0, 0, 0}})
    for (double spacing : {1., .5, .25}) {
      auto start = std::chrono::steady_clock::now();
      first_arrival::Field field(homogeneous, receiver, spacing);
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
    try { first_arrival::Field field(homogeneous, {0, 0, 0}, spacing); }
    catch (const std::runtime_error &) { rejected = true; }
    require(rejected, "Invalid spacing was accepted");
    ++invalid_fields;
  }
  for (double velocity : {0., -1., double(NAN)}) {
    Grid bad = homogeneous;
    bad.v[0] = velocity;
    bool rejected = false;
    try { first_arrival::Field field(bad, {0, 0, 0}, .5); }
    catch (const std::runtime_error &) { rejected = true; }
    require(rejected, "Invalid velocity was accepted");
    ++invalid_fields;
  }
  for (P receiver : {P{NAN, 0, 0}, P{9, 0, 0}}) {
    bool rejected = false;
    try { first_arrival::Field field(homogeneous, receiver, .5); }
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
  first_arrival::Field field(full, receiver, .5);
  double seconds = std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
  require(field.accepted_nodes == field.node_count(), "Full-domain field is incomplete");
  for (P source : {P{-30, 20, 5}, P{35, 30, 20}, P{-35, -30, -1}})
    inspect(full, field, source, receiver, .5, seconds, "synthetic_full_domain", NAN);
  std::cout << "PASS paths=" << paths << " invalid_sources=" << invalid_sources
            << " invalid_fields=" << invalid_fields << " full_domain_nodes="
            << field.node_count() << " full_domain_seconds=" << seconds << '\n';
}
