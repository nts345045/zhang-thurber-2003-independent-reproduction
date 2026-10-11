#pragma once
#include "layered_curved_ray.hpp"
#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>

// A separate closed-form branch calculation for a homogeneous or increasing
// affine speed on a finite depth interval. No production Ray flags are set.
// Coordinates are km, speed km/s, time s. Horizontal space is unbounded (or a
// convex rectangle containing both endpoints). The finite bottom is a path
// constraint, not an extrapolated high-speed layer.
namespace lcr {

struct AffineProfile {
  Real top, bottom, top_speed, bottom_speed;
};

struct AffineArrival {
  Curve curve;
  Point source_derivative{}, receiver_derivative{};
  Real analytic_time = 0;
  Real endpoint_closure = 0;
  Real horizontal_slowness = 0;
  bool source_derivative_available = true;
};

inline AffineArrival affine_arrival(const AffineProfile &model,
                                    Point source, Point receiver) {
  for (Real q : {model.top, model.bottom, model.top_speed, model.bottom_speed})
    if (!std::isfinite(q)) throw std::invalid_argument("Nonfinite affine profile");
  if (!(model.bottom > model.top && model.top_speed > 0 &&
        model.bottom_speed >= model.top_speed))
    throw std::invalid_argument("Require increasing depth and positive nondecreasing speed");
  for (Point p : {source, receiver}) {
    for (Real q : p)
      if (!std::isfinite(q)) throw std::invalid_argument("Nonfinite endpoint");
    if (p[2] < model.top || p[2] > model.bottom)
      throw std::invalid_argument("Endpoint outside finite depth interval");
  }
  AffineArrival result;
  auto &curve = result.curve;
  curve.origin = {source[0], source[1]};
  Real dx = receiver[0] - source[0], dy = receiver[1] - source[1];
  Real range = std::hypot(dx, dy), dz = receiver[2] - source[2];
  Real distance = std::hypot(range, dz);
  curve.azimuth = range > 0 ? std::array<Real, 2>{dx / range, dy / range}
                            : std::array<Real, 2>{1, 0};
  curve.status.completeness = "closed_form_affine_family_in_finite_depth_domain";
  curve.status.derivatives = "unique_ray_envelope_with_fixed_physical_box";
  if (distance == 0) {
    curve.status.branch = "coincident_endpoints";
    curve.status.derivatives = "source_derivative_unavailable_at_zero_distance";
    result.source_derivative_available = false;
    return result;
  }
  Real gradient = (model.bottom_speed - model.top_speed) / (model.bottom - model.top);
  auto velocity = [&](Real z) {
    if (z == model.top) return model.top_speed;
    if (z == model.bottom) return model.bottom_speed;
    return model.top_speed + gradient * (z - model.top);
  };
  Real vs = velocity(source[2]), vr = velocity(receiver[2]);
  if (gradient == 0) {
    curve.status.branch = "homogeneous_straight";
    curve.pieces.push_back(Piece::line(0, source[2], range, receiver[2]));
    result.analytic_time = distance / vs;
    result.horizontal_slowness = range / (vs * distance);
    for (int k = 0; k < 3; ++k) {
      result.source_derivative[k] = (source[k] - receiver[k]) / (vs * distance);
      result.receiver_derivative[k] = -result.source_derivative[k];
    }
  } else if (range == 0) {
    curve.status.branch = "affine_vertical";
    curve.pieces.push_back(Piece::line(0, source[2], 0, receiver[2], PieceKind::vertical));
    result.analytic_time = std::abs(std::log1p((vr - vs) / vs)) / gradient;
    Real sign = dz > 0 ? 1 : -1;
    result.source_derivative[2] = -sign / vs;
    result.receiver_derivative[2] = sign / vr;
  } else {
    const Real half_pi = std::acos(Real(-1)) / 2;
    Real vb = model.bottom_speed;
    // Rationalized products retain the grazing and shallow-gradient limits.
    Real qs = std::sqrt((vb - vs) * (vb + vs));
    Real qr = std::sqrt((vb - vr) * (vb + vr));
    Real guide_threshold = (qs + qr) / gradient;
    Real theta_s, theta_r, kappa, source_vertical, receiver_vertical;
    auto arc = [&](Real start_angle, Real sweep, Real curvature) {
      if (sweep == 0) return;
      Meridional start = curve.pieces.empty() ? Meridional{0, source[2]}
                                            : curve.pieces.back().end();
      curve.pieces.push_back(Piece::arc_increment(start.r, start.z, start_angle, sweep, curvature));
    };
    if (range >= guide_threshold) {
      curve.status.branch = "affine_bottom_guide";
      theta_s = std::atan2(vs, qs);
      theta_r = std::acos(Real(-1)) - std::atan2(vr, qr);
      kappa = gradient / vb;
      result.horizontal_slowness = 1 / vb;
      source_vertical = -qs / (vb * vs);
      receiver_vertical = -qr / (vb * vr);
      arc(theta_s, half_pi - theta_s, kappa);
      Meridional start = curve.pieces.empty() ? Meridional{0, source[2]}
                                            : curve.pieces.back().end();
      Real guide_length = range - guide_threshold;
      if (guide_length > 0)
        curve.pieces.push_back(Piece::line(start.r, start.z, start.r + guide_length,
                                          start.z, PieceKind::boundary_guide));
      arc(half_pi, theta_r - half_pi, kappa);
      result.analytic_time = (std::log1p((vb - vs + qs) / vs) +
                              std::log1p((vb - vr + qr) / vr)) / gradient +
                             guide_length / vb;
    } else {
      curve.status.branch = "affine_circular_arc";
      // A = gradient * horizontal circle-center coordinate. This avoids
      // constructing the distant center of a nearly straight circle.
      Real a = (gradient * range + dz * (vs + vr) / range) / 2;
      Real turning_speed = std::hypot(a, vs);
      theta_s = std::atan2(vs, a);
      Real delta = std::atan2(gradient * (a * dz + vs * range),
                             a * (a - gradient * range) + vs * vr);
      theta_r = theta_s + delta;
      if (!(delta > 0))
        throw std::runtime_error("Affine arc angle unresolved at working precision");
      kappa = gradient / turning_speed;
      result.horizontal_slowness = 1 / turning_speed;
      source_vertical = -a / (turning_speed * vs);
      receiver_vertical = (a - gradient * range) / (turning_speed * vr);
      if (theta_s < half_pi && theta_r > half_pi) {
        Real first_sweep = half_pi - theta_s;
        arc(theta_s, first_sweep, kappa);
        arc(half_pi, delta - first_sweep, kappa);
      } else {
        arc(theta_s, delta, kappa);
      }
      result.analytic_time = 2 * std::asinh(gradient * distance /
                                           (2 * std::sqrt(vs * vr))) / gradient;
    }
    for (int k = 0; k < 2; ++k) {
      result.source_derivative[k] = -result.horizontal_slowness * curve.azimuth[k];
      result.receiver_derivative[k] = result.horizontal_slowness * curve.azimuth[k];
    }
    result.source_derivative[2] = source_vertical;
    result.receiver_derivative[2] = receiver_vertical;
  }
  Point end = curve.at(curve.pieces.size() - 1, 1);
  result.endpoint_closure = std::hypot(std::hypot(end[0] - receiver[0], end[1] - receiver[1]),
                                      end[2] - receiver[2]);
  if (!std::isfinite(result.analytic_time) || !std::isfinite(result.endpoint_closure))
    throw std::runtime_error("Nonfinite affine branch output");
  return result;
}

} // namespace lcr
