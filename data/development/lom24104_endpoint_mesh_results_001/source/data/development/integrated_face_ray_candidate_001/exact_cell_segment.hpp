#pragma once
// Research candidate: exact partition, cached cells, wide piece interpolation.
// Extracted baseline utilities keep the exact arithmetic unchanged; the old
// segment body is excluded. See exact_cell_types_extraction.diff.
#include "exact_cell_types.hpp"

namespace candidate_cell {
using exact_cell::Q;
using exact_cell::QP;
using exact_cell::W;
using exact_cell::WP;
using exact_cell::Event;
using exact_cell::Sample;
using exact_cell::Rounded;
using exact_cell::exact;
using exact_cell::format;
using exact_cell::need;
using exact_cell::nonzero;
using exact_cell::plus;
using exact_cell::power2;
using exact_cell::rounded;
using exact_cell::times;
using exact_cell::wide;
inline void need(bool ok, const std::string &why) {
  if (!ok) throw std::runtime_error(why);
}

// A normalized exact coefficient can be multiplied by wide factors without
// converting its possibly tiny/huge magnitude in isolation.
struct Scale {
  W fraction = 0;
  int exponent = 0;
  explicit Scale(const Q &q = Q(0)) {
    if (q == Q(0)) return;
    const auto r = rounded(q, false);
    fraction = std::ldexp(W(r.mantissa), -64);
    if (r.negative) fraction = -fraction;
    exponent = r.quantum + 64;
  }
  W product(std::initializer_list<W> factors, int shift = 0) const {
    W f = fraction;
    int e = exponent + shift;
    for (W x : factors) {
      need(std::isfinite(x), "Nonfinite product operand");
      if (f == 0 || x == 0) return 0;
      int k = 0;
      f *= std::frexp(x, &k);
      e += k;
      f = std::frexp(f, &k);
      e += k;
    }
    if (f == 0) return 0;
    return nonzero(std::ldexp(f, e), "Nonzero wide product underflow or overflow");
  }
};
inline W product(std::initializer_list<W> values) {
  static const Scale one(Q(1));
  return one.product(values);
}

struct Cell {
  std::array<int, 8> ids{};
  std::array<W, 8> velocity{};
  std::array<Q, 3> width;
  std::array<std::array<Q, 4>, 3> slope_exact;
  std::array<std::array<Scale, 4>, 3> slope;
};
struct GridData : exact_cell::GridData {
  std::array<int, 3> dimensions{};
  std::vector<Cell> cells;
  explicit GridData(const Grid &g) : exact_cell::GridData(g) {
    for (int k = 0; k < 3; ++k) dimensions[k] = int(axis[k].size()) - 1;
    cells.resize(std::size_t(dimensions[0]) * dimensions[1] * dimensions[2]);
    for (int z = 0; z < dimensions[2]; ++z)
      for (int y = 0; y < dimensions[1]; ++y)
        for (int x = 0; x < dimensions[0]; ++x) {
          const std::array<int, 3> p{{x, y, z}};
          Cell &c = cells[index(p)];
          for (int k = 0; k < 3; ++k) c.width[k] = axis[k][p[k] + 1] - axis[k][p[k]];
          int j = 0;
          for (int dz = 0; dz < 2; ++dz)
            for (int dy = 0; dy < 2; ++dy)
              for (int dx = 0; dx < 2; ++dx, ++j) {
                c.ids[j] = g.id(x + dx, y + dy, z + dz);
                c.velocity[j] = W(g.v[c.ids[j]]);
              }
          for (int k = 0; k < 3; ++k) {
            const int u = (k + 1) % 3, v = (k + 2) % 3;
            for (int a = 0; a < 2; ++a)
              for (int b = 0; b < 2; ++b) {
                auto lo = p;
                lo[u] += a;
                lo[v] += b;
                auto hi = lo;
                ++hi[k];
                Q s = (velocity[g.id(hi[0], hi[1], hi[2])] -
                       velocity[g.id(lo[0], lo[1], lo[2])]) / c.width[k];
                c.slope_exact[k][2 * a + b] = s;
                c.slope[k][2 * a + b] = Scale(s);
              }
          }
        }
  }
  std::size_t index(const std::array<int, 3> &p) const {
    for (int k = 0; k < 3; ++k)
      need(p[k] >= 0 && p[k] < dimensions[k], "Invalid explicit cell");
    return (std::size_t(p[2]) * dimensions[1] + p[1]) * dimensions[0] + p[0];
  }
  const Cell &cell(const std::array<int, 3> &p) const { return cells[index(p)]; }
};

using Basis = std::array<std::array<W, 2>, 3>;
using QBasis = std::array<std::array<Q, 2>, 3>;
struct Piece : exact_cell::Piece {
  std::array<QBasis, 2> endpoint_basis;
  std::array<Basis, 2> endpoint_basis_wide;
  std::array<std::array<W, 2>, 2> endpoint_shape_wide;
};
struct NormalPatch {
  Q left, right;
  int axis = -1, plane = -1;
  std::array<int, 3> minus_cell{}, plus_cell{};
  std::array<Q, 3> jump_polynomial;
  std::array<Q, 2> jump_range;
  bool convex = false;
  std::array<W, 2> minus{}, plus{};
};
struct SegmentOptions {
  bool components = true, model = false, records = false;
};
struct Result {
  QP delta;
  W length = 0, action = 0;
  WP unit{}, ga{}, gb{};
  std::array<bool, 3> ordinary{{true, true, true}};
  std::vector<W> dv, node_length;
  std::vector<Event> cuts;
  std::vector<Piece> pieces;
  std::vector<NormalPatch> normal_patches;
  std::size_t piece_count = 0, sample_count = 0;
  bool unsupported_multiple_faces = false;
  bool components_evaluated = false, model_evaluated = false;
};
struct Geometry {
  QP start, delta;
  W scaled_length = 0;
  int exponent = 0;
  Result result;
};
inline Geometry geometry(const GridData &grid, const P &a, const P &b) {
  Geometry q;
  q.exponent = INT_MIN;
  for (int k = 0; k < 3; ++k) {
    q.start[k] = exact(a[k]);
    const Q end = exact(b[k]);
    q.delta[k] = end - q.start[k];
    need(grid.axis[k].front() <= q.start[k] && q.start[k] <= grid.axis[k].back() &&
         grid.axis[k].front() <= end && end <= grid.axis[k].back(), "Endpoint outside physical box");
    if (q.delta[k] != Q(0)) {
      auto r = rounded(q.delta[k], false);
      q.exponent = std::max(q.exponent, r.quantum + 64);
    }
  }
  need(q.exponent != INT_MIN, "Zero edge has no ordinary endpoint derivative");
  WP scaled{};
  for (int k = 0; k < 3; ++k) scaled[k] = wide(q.delta[k] * power2(-q.exponent));
  q.scaled_length = nonzero(std::hypot(scaled[0], scaled[1], scaled[2]), "Invalid scaled length");
  q.result.length = times(Q(1), {q.scaled_length}, q.exponent);
  q.result.delta = q.delta;
  for (int k = 0; k < 3; ++k) q.result.unit[k] = scaled[k] / q.scaled_length;
  std::vector<Event> events{{Q(0), {}}, {Q(1), {}}};
  for (int k = 0; k < 3; ++k)
    for (std::size_t j = 1; j + 1 < grid.axis[k].size(); ++j) {
      const Q &plane = grid.axis[k][j];
      if (q.delta[k] == Q(0)) {
        if (q.start[k] == plane) q.result.ordinary[k] = false;
      } else if (std::min(q.start[k], q.start[k] + q.delta[k]) < plane &&
                 plane < std::max(q.start[k], q.start[k] + q.delta[k])) {
        events.push_back({(plane - q.start[k]) / q.delta[k], {{k, int(j)}}});
      }
    }
  std::sort(events.begin(), events.end(), [](const Event &a, const Event &b) { return a.u < b.u; });
  for (const auto &e : events) {
    if (!q.result.cuts.empty() && e.u == q.result.cuts.back().u)
      q.result.cuts.back().planes.insert(q.result.cuts.back().planes.end(), e.planes.begin(), e.planes.end());
    else q.result.cuts.push_back(e);
  }
  for (auto &e : q.result.cuts) std::sort(e.planes.begin(), e.planes.end());
  q.result.unsupported_multiple_faces = std::count(q.result.ordinary.begin(), q.result.ordinary.end(), false) > 1;
  return q;
}
inline QBasis exact_basis(const GridData &grid, const Geometry &g, const std::array<int, 3> &cell, const Q &u) {
  QBasis b;
  const Cell &c = grid.cell(cell);
  for (int k = 0; k < 3; ++k) {
    const Q z = (g.start[k] + u * g.delta[k] - grid.axis[k][cell[k]]) / c.width[k];
    need(Q(0) <= z && z <= Q(1), "Exact point outside explicit cell");
    b[k] = {{Q(1) - z, z}};
  }
  return b;
}
inline Piece piece(const GridData &grid, const Geometry &g, const Q &left, const Q &right) {
  need(left < right, "Nonpositive exact partition piece");
  Piece p;
  p.left = left;
  p.right = right;
  for (int k = 0; k < 3; ++k) {
    const Q middle = g.start[k] + (left + right) * g.delta[k] / Q(2);
    int c = int(std::upper_bound(grid.axis[k].begin(), grid.axis[k].end(), middle) - grid.axis[k].begin()) - 1;
    c = std::max(0, std::min(c, int(grid.axis[k].size()) - 2));
    if (!g.result.ordinary[k] && c > 0 && grid.axis[k][c] == g.start[k]) --c;
    p.cell[k] = c;
  }
  for (int side = 0; side < 2; ++side) {
    const Q u = side ? right : left;
    p.endpoint_basis[side] = exact_basis(grid, g, p.cell, u);
    for (int k = 0; k < 3; ++k)
      for (int j = 0; j < 2; ++j) p.endpoint_basis_wide[side][k][j] = wide(p.endpoint_basis[side][k][j]);
    p.endpoint_shape_wide[side] = {{wide(Q(1) - u), wide(u)}};
  }
  return p;
}
inline W interpolation(W a, W b, W t) {
  need(t > 0 && t < 1, "Invalid local quadrature parameter");
  W value = plus(product({1 - t, a}), product({t, b}));
  need(value >= 0 && value <= 1, "Wide interpolation escaped explicit cell");
  need(value != 0 || (a == 0 && b == 0), "Positive interpolated basis underflow");
  return value;
}
struct Values { W velocity = 0; WP gradient{}; std::array<W, 8> nodal{}; };
inline Values sample(const Cell &cell, const Basis &basis, bool gradient) {
  Values s;
  int j = 0;
  for (int z = 0; z < 2; ++z)
    for (int y = 0; y < 2; ++y)
      for (int x = 0; x < 2; ++x, ++j) {
        s.nodal[j] = product({basis[0][x], basis[1][y], basis[2][z]});
        s.velocity = plus(s.velocity, product({s.nodal[j], cell.velocity[j]}));
      }
  need(s.velocity > 0 && std::isfinite(s.velocity), "Nonpositive/nonfinite interpolated velocity");
  if (gradient)
    for (int k = 0; k < 3; ++k) {
      const int u = (k + 1) % 3, v = (k + 2) % 3;
      for (int a = 0; a < 2; ++a)
        for (int b = 0; b < 2; ++b)
          s.gradient[k] = plus(s.gradient[k], cell.slope[k][2 * a + b].product({basis[u][a], basis[v][b]}));
    }
  return s;
}
inline Q normal_exact(const Cell &c, int k, const QBasis &basis) {
  const int u = (k + 1) % 3, v = (k + 2) % 3;
  Q value;
  for (int a = 0; a < 2; ++a)
    for (int b = 0; b < 2; ++b) value = value + c.slope_exact[k][2 * a + b] * basis[u][a] * basis[v][b];
  return value;
}
inline NormalPatch patch(const GridData &grid, const Geometry &g, const Piece &p) {
  NormalPatch r;
  r.left = p.left;
  r.right = p.right;
  r.axis = int(std::find(g.result.ordinary.begin(), g.result.ordinary.end(), false) - g.result.ordinary.begin());
  need(r.axis < 3 && !g.result.unsupported_multiple_faces, "Single aligned normal required");
  r.minus_cell = p.cell;
  r.plus_cell = p.cell;
  ++r.plus_cell[r.axis];
  r.plane = r.plus_cell[r.axis];
  const Cell &minus = grid.cell(r.minus_cell), &plus_cell = grid.cell(r.plus_cell);
  std::array<Q, 3> value;
  for (int i = 0; i < 3; ++i) {
    const Q u = p.left + (p.right - p.left) * Q(i) / Q(2);
    const auto basis = exact_basis(grid, g, p.cell, u);
    value[i] = normal_exact(minus, r.axis, basis) - normal_exact(plus_cell, r.axis, basis);
  }
  const Q c0 = value[0], c1 = Q(4) * value[1] - Q(3) * value[0] - value[2];
  const Q c2 = Q(2) * value[2] + Q(2) * value[0] - Q(4) * value[1];
  r.jump_polynomial = {{c0, c1, c2}};
  Q lo = std::min(value[0], value[2]), hi = std::max(value[0], value[2]);
  if (c2 != Q(0)) {
    const Q vertex = -c1 / (Q(2) * c2);
    if (Q(0) < vertex && vertex < Q(1)) {
      const Q v = c0 + vertex * (c1 + vertex * c2);
      lo = std::min(lo, v);
      hi = std::max(hi, v);
    }
  }
  r.jump_range = {{lo, hi}};
  r.convex = Q(0) <= lo;
  return r;
}
static constexpr double nodes[] = {.1834346424956498, .5255324099163290, .7966664774136267, .9602898564975363};
static constexpr double weights[] = {.3626837833783620, .3137066458778873, .2223810344533745, .1012285362903763};

inline Result segment(const GridData &grid, const P &a, const P &b, SegmentOptions options = {}) {
  Geometry g = geometry(grid, a, b);
  Result &out = g.result;
  out.components_evaluated = options.components;
  out.model_evaluated = options.model;
  if (options.model) {
    out.dv.assign(grid.g.v.size(), 0);
    out.node_length.assign(grid.g.v.size(), 0);
  }
  const bool aligned = std::find(out.ordinary.begin(), out.ordinary.end(), false) != out.ordinary.end();
  for (std::size_t part = 1; part < out.cuts.size(); ++part) {
    Piece p = piece(grid, g, out.cuts[part - 1].u, out.cuts[part].u);
    const Q halfwidth = (p.right - p.left) / Q(2);
    const Scale quadrature(halfwidth);
    const Cell &c = grid.cell(p.cell);
    NormalPatch normal;
    if (options.components && aligned && !out.unsupported_multiple_faces) normal = patch(grid, g, p);
    ++out.piece_count;
    for (int j = 0; j < 4; ++j)
      for (int sign : {-1, 1}) {
        const W t = (W(1) + W(sign) * W(nodes[j])) / 2;
        Basis basis;
        for (int k = 0; k < 3; ++k)
          for (int i = 0; i < 2; ++i)
            basis[k][i] = interpolation(p.endpoint_basis_wide[0][k][i], p.endpoint_basis_wide[1][k][i], t);
        const std::array<W, 2> shape{{interpolation(p.endpoint_shape_wide[0][0], p.endpoint_shape_wide[1][0], t),
                                      interpolation(p.endpoint_shape_wide[0][1], p.endpoint_shape_wide[1][1], t)}};
        const Values s = sample(c, basis, options.components);
        const W reciprocal = nonzero(W(1) / s.velocity, "Reciprocal underflow/overflow");
        const W measure = quadrature.product({g.scaled_length, W(weights[j])}, g.exponent);
        need(measure > 0, "Lost positive physical quadrature measure");
        out.action = plus(out.action, quadrature.product({g.scaled_length, W(weights[j]), reciprocal}, g.exponent));
        if (options.components) {
          for (int k = 0; k < 3; ++k)
            if (out.ordinary[k]) {
              const W length_term = quadrature.product({W(weights[j]), out.unit[k], reciprocal});
              out.ga[k] = plus(out.ga[k], plus(-length_term, quadrature.product({g.scaled_length, W(weights[j]), -s.gradient[k], reciprocal, reciprocal, shape[0]}, g.exponent)));
              out.gb[k] = plus(out.gb[k], plus(length_term, quadrature.product({g.scaled_length, W(weights[j]), -s.gradient[k], reciprocal, reciprocal, shape[1]}, g.exponent)));
            }
          if (aligned && !out.unsupported_multiple_faces) {
            Basis other = basis;
            other[normal.axis] = {{1, 0}};
            const Values plus_side = sample(grid.cell(normal.plus_cell), other, true);
            need(s.velocity == plus_side.velocity, "Incident wide face velocities differ");
            for (int side = 0; side < 2; ++side) {
              normal.minus[side] = plus(normal.minus[side], quadrature.product({g.scaled_length, W(weights[j]), -s.gradient[normal.axis], reciprocal, reciprocal, shape[side]}, g.exponent));
              normal.plus[side] = plus(normal.plus[side], quadrature.product({g.scaled_length, W(weights[j]), -plus_side.gradient[normal.axis], reciprocal, reciprocal, shape[side]}, g.exponent));
            }
          }
        }
        if (options.model)
          for (int i = 0; i < 8; ++i) {
            out.dv[c.ids[i]] = plus(out.dv[c.ids[i]], quadrature.product({-g.scaled_length, W(weights[j]), s.nodal[i], reciprocal, reciprocal}, g.exponent));
            out.node_length[c.ids[i]] = plus(out.node_length[c.ids[i]], quadrature.product({g.scaled_length, W(weights[j]), s.nodal[i]}, g.exponent));
          }
        if (options.records) {
          Sample record;
          record.u = p.left + halfwidth * (Q(1) + Q(sign) * exact(nodes[j]));
          record.weight = halfwidth * exact(weights[j]);
          record.shape = {{Q(1) - record.u, record.u}};
          record.basis = exact_basis(grid, g, p.cell, record.u);
          record.shape_wide = shape;
          record.basis_wide = basis;
          record.measure = measure;
          record.velocity = s.velocity;
          record.gradient = s.gradient;
          record.ids = c.ids;
          record.nodal = s.nodal;
          p.samples.push_back(std::move(record));
        }
        ++out.sample_count;
      }
    if (options.components && aligned && !out.unsupported_multiple_faces) out.normal_patches.push_back(std::move(normal));
    if (options.records) out.pieces.push_back(std::move(p));
  }
  need(out.action > 0 && std::isfinite(out.action), "Nonpositive/nonfinite segment action");
  return std::move(out);
}
inline Result segment(const GridData &grid, const P &a, const P &b, bool records) {
  return segment(grid, a, b, SegmentOptions{true, true, records});
}

// True continuous first-variation formula, approximated with the same 8GL
// arithmetic. For an aligned normal, split at the EXACT zero of the interpolated
// displacement and choose the incident cell by that sign. This is not G dot d
// for an arbitrarily selected support vector and is not an interval enclosure.
inline W directional_exact(const GridData &grid, const P &a, const P &b, const QP &da_exact, const QP &db_exact) {
  Geometry g = geometry(grid, a, b);
  need(!g.result.unsupported_multiple_faces, "Multiple aligned faces unsupported for directional variation");
  const int axis = int(std::find(g.result.ordinary.begin(), g.result.ordinary.end(), false) - g.result.ordinary.begin());
  WP da{}, db{};
  for (int k = 0; k < 3; ++k) {
    da[k] = wide(da_exact[k]);
    db[k] = wide(db_exact[k]);
  }
  std::vector<Q> cuts;
  for (const auto &c : g.result.cuts) cuts.push_back(c.u);
  Q na, nb;
  if (axis < 3) {
    na = da_exact[axis];
    nb = db_exact[axis];
    if (na != nb) {
      const Q zero = -na / (nb - na);
      if (Q(0) < zero && zero < Q(1)) cuts.push_back(zero);
    }
  }
  std::sort(cuts.begin(), cuts.end());
  cuts.erase(std::unique(cuts.begin(), cuts.end()), cuts.end());
  W length_slope = 0, result = 0;
  for (int k = 0; k < 3; ++k) length_slope = plus(length_slope, product({g.result.unit[k], db[k] - da[k]}));
  for (std::size_t i = 1; i < cuts.size(); ++i) {
    Piece p = piece(grid, g, cuts[i - 1], cuts[i]);
    auto cell = p.cell;
    if (axis < 3) {
      const Q value = na + (p.left + p.right) * (nb - na) / Q(2);
      if (Q(0) < value) ++cell[axis];
    }
    const Scale quadrature((p.right - p.left) / Q(2));
    for (int j = 0; j < 4; ++j)
      for (int sign : {-1, 1}) {
        const W t = (1 + W(sign) * W(nodes[j])) / 2;
        Basis basis;
        for (int k = 0; k < 3; ++k)
          for (int s = 0; s < 2; ++s)
            basis[k][s] = interpolation(p.endpoint_basis_wide[0][k][s], p.endpoint_basis_wide[1][k][s], t);
        if (axis < 3 && cell[axis] != p.cell[axis]) basis[axis] = {{1, 0}};
        const W h0 = interpolation(p.endpoint_shape_wide[0][0], p.endpoint_shape_wide[1][0], t);
        const W h1 = interpolation(p.endpoint_shape_wide[0][1], p.endpoint_shape_wide[1][1], t);
        const Values v = sample(grid.cell(cell), basis, true);
        const W inv = nonzero(1 / v.velocity, "Directional reciprocal underflow/overflow");
        W velocity_slope = 0;
        for (int k = 0; k < 3; ++k)
          velocity_slope = plus(velocity_slope, product({v.gradient[k], plus(product({h0, da[k]}), product({h1, db[k]}))}));
        result = plus(result, plus(quadrature.product({W(weights[j]), length_slope, inv}),
                    quadrature.product({-g.scaled_length, W(weights[j]), velocity_slope, inv, inv}, g.exponent)));
      }
  }
  return result;
}
} // namespace candidate_cell
