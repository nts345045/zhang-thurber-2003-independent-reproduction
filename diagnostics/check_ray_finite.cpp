// Invented extreme positive velocities test arithmetic failure at zero updates.
#include "../src/core.hpp"

int main() {
  Grid g;
  g.x = g.y = g.z = {0, 1};
  g.v.assign(g.size(), 5);
  P a{.1,.2,.3}, b{.8,.7,.6};
  std::cout << "check,passed\n";
  int failures = 0;
  auto check = [&](const char *name, bool passed) {
    std::cout << name << ',' << passed << '\n';
    failures += !passed;
  };
  auto finite = trace(g,a,b,.1,0);
  check("finite_zero_update_ray", finite.converged &&
        std::abs(finite.time-norm(a-b)/5)<1e-14);
  check("coincident_endpoints", trace(g,a,a,.1,0).time == 0);
  for (bool derivatives : {false,true}) {
    g.v.assign(g.size(),std::numeric_limits<double>::denorm_min()*1024);
    bool rejected = false;
    try { trace(g,a,b,.1,0,derivatives); }
    catch (const std::runtime_error &error) {
      rejected = std::string(error.what()).find("Nonfinite ray") != std::string::npos;
    }
    check(derivatives ? "overflow_with_derivatives" : "overflow_without_derivatives", rejected);
  }
  return failures ? 1 : 0;
}
