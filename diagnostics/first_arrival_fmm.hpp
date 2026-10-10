#pragma once
// Diagnostic initializer only. Returned field times are not production actions.
#include "../src/core.hpp"
#include <functional>
#include <limits>
#include <queue>
#include <utility>

namespace first_arrival {

struct Candidate {
  std::vector<P> path;
  bool success = false;
  std::string message;
  double field_time = std::numeric_limits<double>::quiet_NaN();
  int descent_steps = 0;
  int fallback_steps = 0;
};

class Field {
  // The model must outlive the field and remain unchanged.
  const Grid &model_;
  P receiver_, spacing_{};
  std::array<Vec, 3> axes_;
  std::array<int, 3> shape_{};
  Vec time_;
  std::vector<int> parent_;

  static bool finite(P p) {
    return std::all_of(p.begin(), p.end(), [](double x) { return std::isfinite(x); });
  }
  int id(int i, int j, int k) const {
    return (k * shape_[1] + j) * shape_[0] + i;
  }
  std::array<int, 3> indices(int n) const {
    int i = n % shape_[0];
    n /= shape_[0];
    return {i, n % shape_[1], n / shape_[1]};
  }
  P position(int n) const {
    auto q = indices(n);
    return {axes_[0][q[0]], axes_[1][q[1]], axes_[2][q[2]]};
  }
  std::array<int, 3> cell(P p) const {
    std::array<int, 3> q{};
    for (int k = 0; k < 3; ++k)
      q[k] = std::clamp(int(std::upper_bound(axes_[k].begin(), axes_[k].end(), p[k]) -
                            axes_[k].begin()) - 1, 0, shape_[k] - 2);
    return q;
  }
  std::array<int, 8> corners(P p) const {
    auto q = cell(p);
    std::array<int, 8> result{};
    int n = 0;
    for (int k = 0; k < 2; ++k)
      for (int j = 0; j < 2; ++j)
        for (int i = 0; i < 2; ++i)
          result[n++] = id(q[0] + i, q[1] + j, q[2] + k);
    return result;
  }
  struct Sample {
    double time = 0;
    P gradient{};
  };
  Sample sample(P p) const {
    auto q = cell(p);
    P fraction{};
    for (int k = 0; k < 3; ++k)
      fraction[k] = (p[k] - axes_[k][q[k]]) / spacing_[k];
    Sample result;
    for (int k = 0; k < 2; ++k)
      for (int j = 0; j < 2; ++j)
        for (int i = 0; i < 2; ++i) {
          double w = (i ? fraction[0] : 1 - fraction[0]) *
                     (j ? fraction[1] : 1 - fraction[1]) *
                     (k ? fraction[2] : 1 - fraction[2]);
          result.time += w * time_[id(q[0] + i, q[1] + j, q[2] + k)];
        }
    for (int axis = 0; axis < 3; ++axis) {
      int u = (axis + 1) % 3, v = (axis + 2) % 3;
      for (int a = 0; a < 2; ++a)
        for (int b = 0; b < 2; ++b) {
          auto lo = q, hi = q;
          lo[u] += a;
          lo[v] += b;
          hi = lo;
          ++hi[axis];
          result.gradient[axis] +=
              (time_[id(hi[0], hi[1], hi[2])] - time_[id(lo[0], lo[1], lo[2])]) /
              spacing_[axis] * (a ? fraction[u] : 1 - fraction[u]) *
              (b ? fraction[v] : 1 - fraction[v]);
        }
    }
    return result;
  }
  P project(P p) const {
    for (int k = 0; k < 3; ++k)
      p[k] = std::clamp(p[k], axes_[k].front(), axes_[k].back());
    return p;
  }

  void build() {
    const double infinity = std::numeric_limits<double>::infinity();
    time_.assign(node_count(), infinity);
    parent_.assign(node_count(), -1);
    Vec slowness(node_count());
    std::vector<unsigned char> accepted(node_count(), 0);
    for (int n = 0; n < int(node_count()); ++n) {
      double velocity = model_.sample(position(n)).v;
      slowness[n] = 1 / velocity;
      if (!(velocity > 0) || !std::isfinite(velocity) ||
          !(slowness[n] > 0) || !std::isfinite(slowness[n]))
        throw std::runtime_error("FMM requires finite positive auxiliary velocity and slowness");
    }
    using Entry = std::pair<double, int>;
    std::priority_queue<Entry, std::vector<Entry>, std::greater<Entry>> trial;
    // The exact off-grid point is connected to its cell vertices by continuous
    // action integrals. These are trial upper bounds, not fixed accepted times.
    for (int n : corners(receiver_)) {
      double value = segment(model_, receiver_, position(n));
      if (!std::isfinite(value) || value < 0)
        throw std::runtime_error("Invalid exact-receiver FMM seed action");
      time_[n] = value;
      trial.push({value, n});
    }
    auto update = [&](int n) {
      auto q = indices(n);
      struct Neighbor { double time, inverse_h2; int id; };
      std::array<Neighbor, 3> used{};
      int count = 0;
      for (int axis = 0; axis < 3; ++axis) {
        int best = -1;
        for (int sign : {-1, 1}) {
          auto next = q;
          next[axis] += sign;
          if (next[axis] < 0 || next[axis] >= shape_[axis])
            continue;
          int other = id(next[0], next[1], next[2]);
          if (accepted[other] && (best < 0 || time_[other] < time_[best]))
            best = other;
        }
        if (best >= 0)
          used[count++] = {time_[best], 1 / (spacing_[axis] * spacing_[axis]), best};
      }
      if (!count)
        return;
      std::sort(used.begin(), used.begin() + count,
                [](const Neighbor &a, const Neighbor &b) { return a.time < b.time; });
      // Shift by the smallest time to avoid subtracting large squared times.
      double aa = 0, bb = 0, cc = -slowness[n] * slowness[n], value = infinity;
      for (int k = 0; k < count; ++k) {
        double offset = used[k].time - used[0].time, weight = used[k].inverse_h2;
        aa += weight;
        bb += weight * offset;
        cc += weight * offset * offset;
        double discriminant = bb * bb - aa * cc;
        // Inclusion of each next axis is causal, so any negative remainder is
        // roundoff in an otherwise nonnegative quadratic discriminant.
        value = used[0].time + (bb + std::sqrt(std::max(0., discriminant))) / aa;
        if (k + 1 == count || value <= used[k + 1].time)
          break;
      }
      if (!std::isfinite(value) || value < used[0].time)
        throw std::runtime_error("Nonfinite or noncausal FMM update");
      if (value < time_[n]) {
        time_[n] = value;
        parent_[n] = used[0].id;
        trial.push({value, n});
      }
    };
    double previous = -infinity;
    while (!trial.empty()) {
      auto entry = trial.top();
      trial.pop();
      int n = entry.second;
      if (accepted[n] || entry.first != time_[n])
        continue;
      if (entry.first < previous)
        throw std::runtime_error("FMM acceptance times are not monotone");
      previous = entry.first;
      accepted[n] = 1;
      ++accepted_nodes;
      auto q = indices(n);
      for (int axis = 0; axis < 3; ++axis)
        for (int sign : {-1, 1}) {
          auto next = q;
          next[axis] += sign;
          if (next[axis] < 0 || next[axis] >= shape_[axis])
            continue;
          int other = id(next[0], next[1], next[2]);
          if (!accepted[other])
            update(other);
        }
    }
    if (accepted_nodes != node_count())
      throw std::runtime_error("FMM did not reach the full positive-speed domain");
  }

public:
  std::size_t accepted_nodes = 0;

  Field(const Grid &model, P receiver, double requested_spacing)
      : model_(model), receiver_(receiver) {
    if (!finite(receiver) || !std::isfinite(requested_spacing) || requested_spacing <= 0)
      throw std::runtime_error("Invalid FMM receiver or requested spacing");
    const Vec *original[] = {&model.x, &model.y, &model.z};
    std::size_t nodes = 1;
    for (int axis = 0; axis < 3; ++axis) {
      const auto &a = *original[axis];
      if (a.size() < 2)
        throw std::runtime_error("FMM requires three nonempty model axes");
      for (std::size_t k = 0; k < a.size(); ++k)
        if (!std::isfinite(a[k]) || (k && a[k] <= a[k - 1]))
          throw std::runtime_error("FMM model axes must be finite and strictly increasing");
      double intervals = std::ceil((a.back() - a.front()) / requested_spacing);
      if (!std::isfinite(intervals) || intervals >= std::numeric_limits<int>::max() - 1)
        throw std::runtime_error("FMM auxiliary axis is too large");
      shape_[axis] = int(intervals) + 1;
      spacing_[axis] = (a.back() - a.front()) / intervals;
      nodes *= std::size_t(shape_[axis]);
      if (nodes > std::size_t(std::numeric_limits<int>::max()))
        throw std::runtime_error("FMM auxiliary grid is too large for its indices");
      axes_[axis].resize(shape_[axis]);
      for (int k = 0; k < shape_[axis]; ++k)
        axes_[axis][k] = a.front() + k * spacing_[axis];
      axes_[axis].back() = a.back();
    }
    if (!model.contains(receiver) || model.v.size() != std::size_t(model.size()))
      throw std::runtime_error("FMM receiver outside domain or model values missing");
    for (double velocity : model.v)
      if (!(velocity > 0) || !std::isfinite(velocity))
        throw std::runtime_error("FMM model velocities must be finite and positive");
    build();
  }

  std::size_t node_count() const {
    return std::size_t(shape_[0]) * shape_[1] * shape_[2];
  }
  P spacing() const { return spacing_; }
  double interpolated_time(P p) const {
    if (!finite(p) || !model_.contains(p))
      throw std::runtime_error("FMM interpolation point outside finite domain");
    return p == receiver_ ? 0 : sample(p).time;
  }

  Candidate candidate(P source) const {
    Candidate result;
    if (!finite(source) || !model_.contains(source)) {
      result.message = "Source is nonfinite or outside the FMM domain";
      return result;
    }
    result.path.push_back(source);
    result.field_time = interpolated_time(source);
    P current = source;
    const double step = *std::min_element(spacing_.begin(), spacing_.end()) / 2;
    const auto receiver_cell = cell(receiver_);
    // A finite numerical guard reports failure; it is not a physical path limit.
    const std::size_t limit = 4 * node_count();
    for (std::size_t iteration = 0; iteration < limit; ++iteration) {
      // Include upper faces: a seeded corner can be a strict field minimum
      // although the half-open interpolation lookup assigns it another cell.
      bool in_receiver_cell = true;
      for (int axis = 0; axis < 3; ++axis)
        in_receiver_cell = in_receiver_cell &&
            current[axis] >= axes_[axis][receiver_cell[axis]] &&
            current[axis] <= axes_[axis][receiver_cell[axis] + 1];
      if (current == receiver_ || in_receiver_cell ||
          norm(current - receiver_) <= step) {
        if (current != receiver_)
          result.path.push_back(receiver_);
        result.success = true;
        result.message = "Exact endpoints connected by a descending FMM seed";
        return result;
      }
      auto s = sample(current);
      if (!std::isfinite(s.time) || !finite(s.gradient)) {
        result.message = "Nonfinite FMM time or gradient during extraction";
        return result;
      }
      bool moved = false;
      P next{};
      double magnitude = norm(s.gradient), trial_step = step;
      if (magnitude > 0 && std::isfinite(magnitude))
        for (int backtrack = 0; backtrack < 12; ++backtrack, trial_step *= 0.5) {
          // Midpoint integration reduces directional staircasing of the seed.
          P midpoint = project(current - s.gradient * (trial_step / (2 * magnitude)));
          auto middle = sample(midpoint);
          double middle_norm = norm(middle.gradient);
          if (!finite(middle.gradient) || !std::isfinite(middle_norm) || middle_norm == 0)
            continue;
          next = project(current - middle.gradient * (trial_step / middle_norm));
          double value = interpolated_time(next);
          if (std::isfinite(value) && value < s.time && next != current) {
            moved = true;
            ++result.descent_steps;
            break;
          }
        }
      if (!moved) {
        // At a shock or interpolation stall, descend to a nearby accepted
        // corner or its causal parent. Never substitute a long direct ray.
        double best = s.time;
        for (int corner : corners(current))
          for (int n : {corner, parent_[corner]}) {
            if (n < 0)
              continue;
            P point = position(n);
            double value = interpolated_time(point);
            if (value < best && point != current) {
              best = value;
              next = point;
              moved = true;
            }
          }
        if (moved)
          ++result.fallback_steps;
      }
      if (!moved) {
        result.message = "No strictly descending FMM extraction step found";
        return result;
      }
      result.path.push_back(next);
      current = next;
    }
    result.message = "FMM extraction exceeded its finite iteration guard";
    return result;
  }
};

} // namespace first_arrival
