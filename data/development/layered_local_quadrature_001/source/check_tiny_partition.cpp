#include "layered_curved_ray.hpp"
#include <iostream>

// One invented vertical line. The lower-plane mass comes from the independent
// antiderivative integral_{-delta}^0 (-z) dz, not a quadrature implementation.
int main() {
  try {
    using namespace lcr;
    const Real delta=std::ldexp(Real(1),-63),velocity=4;
    Grid grid;
    grid.x={0,1};grid.y={0,1};grid.z={-1,0,1};grid.v.assign(12,4);
    Curve curve;curve.origin={Real(0.25),Real(0.25)};curve.azimuth={1,0};
    curve.status={"invented_constant_vertical","not_assessed","selected_curve_only"};
    curve.pieces.push_back(Piece::line(0,1,0,-delta,PieceKind::vertical));
    const Result result=integrate(grid,curve);
    Real lower_mass=0;
    for (std::size_t j=0;j<2;++j)
      for (std::size_t i=0;i<2;++i) lower_mass+=result.length[grid.id(i,j,0)];
    const Real expected_mass=std::ldexp(Real(1),-127),expected_time=(1+delta)/velocity;
    // Finite arithmetic regression allowances, not mathematical error bounds.
    const Real relative_tolerance=512*std::numeric_limits<Real>::epsilon();
    const bool positive=finite(lower_mass) && lower_mass>0;
    const bool mass=finite(lower_mass) && std::abs(lower_mass-expected_mass)<=relative_tolerance*expected_mass;
    const bool time=finite(result.action) && std::abs(result.action-expected_time)<=relative_tolerance*expected_time;
    const bool inventory=result.subpieces==2 && result.samples==48 && result.face_crossings==1;
    const unsigned passed=unsigned(positive)+unsigned(mass)+unsigned(time)+unsigned(inventory);
    std::cout << "{\"status\":\"" << (passed==4?"passed":"failed")
              << "\",\"checks\":4,\"passed\":" << passed << ",\"integrate_calls\":1"
              << ",\"subpieces\":" << result.subpieces << ",\"samples\":" << result.samples
              << ",\"face_crossings\":" << result.face_crossings << std::hexfloat
              << ",\"delta_hex\":\"" << delta << "\",\"expected_lower_mass_hex\":\"" << expected_mass
              << "\",\"lower_mass_hex\":\"" << lower_mass << "\",\"expected_time_hex\":\"" << expected_time
              << "\",\"time_hex\":\"" << result.action << "\",\"relative_tolerance_hex\":\"" << relative_tolerance
              << "\",\"anchor_roundtrip_hex\":\"" << result.maximum_anchor_roundtrip_displacement
              << "\",\"anchor_midpoint_discrepancy_hex\":\"" << result.maximum_anchor_midpoint_discrepancy << "\"}\n";
    return passed==4?0:1;
  } catch(const std::exception &error) {
    std::cerr << error.what() << '\n';return 1;
  }
}
