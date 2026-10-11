#include "affine_arrival.hpp"
#include <iomanip>
#include <iostream>
#include <string>

using namespace lcr;

int main() {
  struct Example { const char *name; AffineProfile model; Point source, receiver; };
  const Example examples[] = {
    {"homogeneous_oblique", {0,10,4,4}, {-3,-2,1}, {4,5,9}},
    {"affine_vertical", {0,10,4,6}, {0,0,2}, {0,0,8}},
    {"affine_direct", {0,10,4,14}, {-3,-2,1}, {-2.4L,-1.2L,6}},
    {"affine_turn", {0,10,4,14}, {-3,-2,2}, {1.8L,4.4L,3}},
    {"affine_turn_reversed", {0,10,4,14}, {1.8L,4.4L,3}, {-3,-2,2}},
    {"affine_bottom_guide", {0,10,4,14}, {-3,-2,2}, {21,30,3}},
    {"affine_bottom_source", {0,10,4,14}, {-3,-2,10}, {9,14,3}},
    {"affine_bottom_both", {0,10,4,14}, {-3,-2,10}, {9,14,10}},
    {"near_homogeneous", {0,10,4,4+std::ldexp(Real(1),-30)}, {-3,-2,2}, {1.8L,4.4L,7}}
  };
  int failed = 0, checks = 0;
  auto check = [&](bool pass) { ++checks; if (!pass) ++failed; return pass; };
  std::cout << std::setprecision(21) << "{\"cases\":[";
  bool first = true;
  for (const auto &ex : examples) {
    if (!first) std::cout << ',';
    first = false;
    std::cout << "\n{\"name\":\"" << ex.name << "\"";
    try {
      auto arrival = affine_arrival(ex.model, ex.source, ex.receiver);
      Grid grid;
      grid.x = {-64,-6,-1,2,9,64};
      grid.y = {-64,-4,0,5,20,64};
      grid.z = {double(ex.model.top), double(ex.model.bottom)};
      grid.v.resize(grid.x.size()*grid.y.size()*grid.z.size());
      for (std::size_t k=0;k<grid.z.size();++k)
        for (std::size_t j=0;j<grid.y.size();++j)
          for (std::size_t i=0;i<grid.x.size();++i)
            grid.v[grid.id(i,j,k)] = double(k ? ex.model.bottom_speed : ex.model.top_speed);
      auto result = integrate(grid, arrival.curve);
      Real scale_sum=0, length_sum=0, min_length=0;
      for (std::size_t k=0;k<grid.v.size();++k) {
        scale_sum += grid.v[k]*result.dv[k];
        length_sum += result.length[k];
        min_length = std::min(min_length,result.length[k]);
      }
      Real time_error = std::abs(result.action-arrival.analytic_time);
      Real scale_error = std::abs(scale_sum+result.action);
      Real length_error = std::abs(length_sum-result.arclength);
      bool passed = true;
      passed &= check(time_error < 1e-11L);
      passed &= check(arrival.endpoint_closure < 1e-10L);
      passed &= check(scale_error < 1e-13L);
      passed &= check(length_error < 1e-12L);
      passed &= check(min_length >= 0);
      Real source_fd_error=0;
      for (int axis=0;axis<3;++axis) {
        Real step=1e-5L;
        if (axis==2 && (ex.source[2]-step<ex.model.top || ex.source[2]+step>ex.model.bottom))
          continue;
        Point plus=ex.source,minus=ex.source;
        plus[axis]+=step;minus[axis]-=step;
        Real fd=(affine_arrival(ex.model,plus,ex.receiver).analytic_time-
                 affine_arrival(ex.model,minus,ex.receiver).analytic_time)/(2*step);
        source_fd_error=std::max(source_fd_error,std::abs(fd-arrival.source_derivative[axis]));
      }
      passed &= check(source_fd_error < 1e-9L);
      std::cout << ",\"passed\":" << (passed?"true":"false")
                << ",\"branch\":\"" << arrival.curve.status.branch << "\""
                << ",\"analytic_time_s\":" << arrival.analytic_time
                << ",\"integrated_time_s\":" << result.action
                << ",\"time_error_s\":" << time_error
                << ",\"endpoint_closure_km\":" << arrival.endpoint_closure
                << ",\"source_fd_error_s_per_km\":" << source_fd_error
                << ",\"velocity_scaling_identity_error_s\":" << scale_error
                << ",\"basis_length_sum_error_km\":" << length_error
                << ",\"pieces\":" << result.pieces
                << ",\"subpieces\":" << result.subpieces
                << ",\"samples\":" << result.samples
                << ",\"action_quadrature_difference_s\":" << result.action_difference;
    } catch (const std::exception &error) {
      check(false);
      std::cout << ",\"passed\":false,\"error\":\"" << error.what() << "\"";
    }
    std::cout << '}';
  }
  auto zero=affine_arrival({0,10,4,6},{0,0,2},{0,0,2});
  check(zero.analytic_time==0 && !zero.source_derivative_available && zero.curve.pieces.empty());
  for (AffineProfile bad : {AffineProfile{0,10,4,3}, AffineProfile{0,0,4,4}, AffineProfile{0,10,0,4}}) {
    bool rejected=false;
    try { affine_arrival(bad,{0,0,2},{1,0,3}); }
    catch(const std::invalid_argument&) { rejected=true; }
    check(rejected);
  }
  std::cout << "\n],\"checks\":" << checks << ",\"failed\":" << failed
            << ",\"status\":\"" << (failed?"failed":"passed")
            << "\",\"scope\":\"invented affine cases; no production or real-data evaluation\"}\n";
  return failed ? 1 : 0;
}
