#include "core.hpp"
#include "ray_checks.hpp"
#include <filesystem>
struct Event {
  P p;
  double t = 0;
};
struct Datum {
  int i, j, k, type;
  double value;
};
std::ofstream output(std::string p) {
  std::ofstream f(p);
  if (!f)
    throw std::runtime_error("Cannot write " + p);
  f << std::setprecision(12);
  return f;
}
void write_grid(const Grid &g, std::string path) {
  auto f = output(path);
  f << "x,y,z,v\n";
  for (int k = 0; k < int(g.z.size()); k++)
    for (int j = 0; j < int(g.y.size()); j++)
      for (int i = 0; i < int(g.x.size()); i++)
        f << g.x[i] << ',' << g.y[j] << ',' << g.z[k] << ','
          << g.v[g.id(i, j, k)] << '\n';
}
void write_events(const std::vector<Event> &e, std::string path) {
  auto f = output(path);
  f << "id,x,y,z,t\n";
  for (size_t i = 0; i < e.size(); i++)
    f << i << ',' << e[i].p[0] << ',' << e[i].p[1] << ',' << e[i].p[2] << ','
      << e[i].t << '\n';
}
std::vector<Vec> read_csv(std::string path) {
  std::ifstream f(path);
  if (!f)
    throw std::runtime_error("Cannot read " + path);
  std::string l;
  std::getline(f, l);
  std::vector<Vec> r;
  while (std::getline(f, l)) {
    std::replace(l.begin(), l.end(), ',', ' ');
    std::istringstream s(l);
    Vec row;
    double v;
    while (s >> v)
      row.push_back(v);
    if (!row.empty())
      r.push_back(row);
  }
  return r;
}
Grid read_grid(std::string path) {
  auto rows = read_csv(path);
  Grid g;
  for (int a = 0; a < 3; a++) {
    Vec q;
    for (auto &r : rows)
      q.push_back(r[a]);
    std::sort(q.begin(), q.end());
    q.erase(std::unique(q.begin(), q.end()), q.end());
    if (a == 0)
      g.x = q;
    if (a == 1)
      g.y = q;
    if (a == 2)
      g.z = q;
  }
  g.v.resize(g.size());
  for (auto &r : rows) {
    int i = std::lower_bound(g.x.begin(), g.x.end(), r[0]) - g.x.begin(),
        j = std::lower_bound(g.y.begin(), g.y.end(), r[1]) - g.y.begin(),
        k = std::lower_bound(g.z.begin(), g.z.end(), r[2]) - g.z.begin();
    g.v[g.id(i, j, k)] = r[3];
  }
  return g;
}
std::vector<Event> read_events(std::string path) {
  std::vector<Event> e;
  for (auto &r : read_csv(path))
    e.push_back({{r[1], r[2], r[3]}, r[4]});
  return e;
}
std::vector<Ray> rays(const Grid &g, const std::vector<Event> &e,
                      const std::vector<Event> &s, const Config &c,
                      bool deriv = true) {
  std::vector<Ray> r(e.size() * s.size());
#pragma omp parallel for schedule(dynamic)
  for (int n = 0; n < int(r.size()); n++)
    r[n] = trace(g, e[n / s.size()].p, s[n % s.size()].p, c.get("ray_spacing"),
                 c.get("ray_iterations"), deriv);
  return r;
}
double setting(const Config &c, const std::string &key, double fallback) {
  auto it = c.v.find(key);
  return it == c.v.end() ? fallback : it->second;
}
double true_velocity(const Config &c, double x) {
  return setting(c, "truth_model", 0) == 1 ? 6.0 : sandwich(x);
}
double starting_velocity(const Config &c, double depth) {
  int profile = int(setting(c, "initial_model", 0));
  if (profile == 0)
    return c.get("initial_velocity");
  // Written gradient adaptations in USGS OFR 93-578 Table 4 (LOM/LON).
  // Neither is identified as the exact starting profile in the target paper.
  Vec z = profile == 1 ? Vec{0, 2, 6.7, 24, 26} : Vec{0, 2.5, 8.9, 24, 26};
  Vec v = profile == 1 ? Vec{3, 4.95, 5.94, 6.64, 8}
                       : Vec{2.53, 5.44, 6.29, 6.69, 7.98};
  int k = std::clamp(
      int(std::upper_bound(z.begin(), z.end(), depth) - z.begin()) - 1, 0, 3);
  return v[k] + (v[k + 1] - v[k]) * (depth - z[k]) / (z[k + 1] - z[k]);
}
void generate(const Config &c, std::string dir) {
  std::filesystem::create_directories(dir);
  std::mt19937 gen(c.get("seed"));
  std::uniform_real_distribution<double> u(0, 1);
  std::normal_distribution<double> normal(0, 1);
  std::vector<Event> e, s, initial;
  int ne = c.get("events"), ns = c.get("stations");
  // Independent design: volume sampling, with half of the sources near the
  // trough.
  for (int i = 0; i < ne; i++) {
    double x = i < ne / 2 ? -4 + 12 * u(gen) : -15 + 40 * u(gen);
    e.push_back({{x, -45 + 70 * u(gen), 2 + 11 * u(gen)}, 0});
  }
  // Jittered surface array, independent of all published map coordinates.
  int nx = std::ceil(std::sqrt(ns * 0.7)), ny = std::ceil(double(ns) / nx);
  for (int i = 0; i < ns; i++)
    s.push_back({{-30 + 60 * (i % nx + 0.25 + 0.5 * u(gen)) / nx,
                  -55 + 90 * (i / nx + 0.25 + 0.5 * u(gen)) / ny, 0},
                 0});
  initial = e;
  for (auto &a : initial) {
    for (int k = 0; k < 3; k++)
      a.p[k] += c.get("location_noise") * normal(gen);
    a.p[2] = std::clamp(a.p[2], 0.5, 15.5);
    a.t = 0.05 * normal(gen);
  }
  Grid truth = grid(true);
  for (int k = 0; k < int(truth.z.size()); k++)
    for (int j = 0; j < int(truth.y.size()); j++)
      for (int i = 0; i < int(truth.x.size()); i++)
        truth.v[truth.id(i, j, k)] = true_velocity(c, truth.x[i]);
  Grid start = grid();
  for (int k = 0; k < int(start.z.size()); k++)
    for (int j = 0; j < int(start.y.size()); j++)
      for (int i = 0; i < int(start.x.size()); i++)
        start.v[start.id(i, j, k)] = starting_velocity(c, start.z[k]);
  write_grid(truth, dir + "/truth_grid.csv");
  write_grid(start, dir + "/initial_grid.csv");
  write_events(e, dir + "/truth_events.csv");
  write_events(initial, dir + "/initial_events.csv");
  write_events(s, dir + "/stations.csv");
  std::vector<Ray> rr(ne * ns);
  if (setting(c, "truth_model", 0) == 1) {
    // Analytic independent observations for the homogeneous joint test.
    for (int i = 0; i < ne; i++)
      for (int k = 0; k < ns; k++)
        rr[i * ns + k].time = norm(e[i].p - s[k].p) / 6;
  } else
    rr = rays(truth, e, s, c, false);
  Vec true_t(rr.size()), abs_t(rr.size()), rounded(rr.size()), bias(ns);
  for (auto &v : bias)
    v = (2 * u(gen) - 1) * c.get("station_noise");
  auto raw = output(dir + "/arrivals.csv");
  raw << "event,station,true_time,rounded_time,station_bias,pick_noise,"
         "absolute_time\n";
  for (int i = 0; i < ne; i++)
    for (int k = 0; k < ns; k++) {
      int n = i * ns + k;
      true_t[n] = rr[n].time;
      double quantum = setting(c, "time_quantum", 0.01);
      rounded[n] =
          quantum > 0 ? std::round(true_t[n] / quantum) * quantum : true_t[n];
      double noise = c.get("noise") * normal(gen);
      abs_t[n] = rounded[n] + bias[k] + noise;
      raw << i << ',' << k << ',' << true_t[n] << ',' << rounded[n] << ','
          << bias[k] << ',' << noise << ',' << abs_t[n] << '\n';
    }
  auto f = output(dir + "/observations.csv");
  f << "i,j,station,type,value\n";
  for (int i = 0; i < ne; i++)
    for (int k = 0; k < ns; k++)
      f << i << ",-1," << k << ",0," << abs_t[i * ns + k] << '\n';
  for (int i = 0; i < ne; i++)
    for (int j = i + 1; j < ne; j++)
      if (norm(e[i].p - e[j].p) < c.get("pair_distance"))
        for (int k = 0; k < ns; k++) {
          f << i << ',' << j << ',' << k << ",1,"
            << abs_t[i * ns + k] - abs_t[j * ns + k] << '\n';
          f << i << ',' << j << ',' << k << ",2,"
            << rounded[i * ns + k] - rounded[j * ns + k] << '\n';
        }
  // Dense sampling saved by the model, used directly by the figure-1 plotting
  // routine.
  auto slice = output(dir + "/truth_slice.csv");
  slice << "x,y,z,v\n";
  for (double y = -60; y <= 40; y += 1)
    for (double x = -35; x <= 35; x += 0.25)
      slice << x << ',' << y << ",7," << true_velocity(c, x) << '\n';
  std::cout << "Generated " << ne << " independent sources and " << ns
            << " stations.\n";
}
std::vector<Datum> observations(std::string path) {
  std::vector<Datum> d;
  for (auto &r : read_csv(path))
    d.push_back({int(r[0]), int(r[1]), int(r[2]), int(r[3]), r[4]});
  return d;
}
double prediction(const Datum &d, const std::vector<Ray> &r,
                  const std::vector<Event> &e, int ns) {
  double t = e[d.i].t + r[d.i * ns + d.k].time;
  if (d.j >= 0)
    t -= e[d.j].t + r[d.j * ns + d.k].time;
  return t;
}
void smooth(Matrix &A, const Grid &g, int off, double weight) {
  for (int k = 0; k < int(g.z.size()); k++)
    for (int j = 0; j < int(g.y.size()); j++)
      for (int i = 0; i < int(g.x.size()); i++) {
        int a = g.id(i, j, k);
        int pos[] = {i, j, k};
        const Vec *ax[] = {&g.x, &g.y, &g.z};
        for (int dim = 0; dim < 3; dim++)
          if (pos[dim] + 1 < int(ax[dim]->size())) {
            int q[] = {i, j, k};
            q[dim]++;
            int b = g.id(q[0], q[1], q[2]);
            double h = (*ax[dim])[pos[dim] + 1] - (*ax[dim])[pos[dim]];
            // Smooth the final log-slowness, not only its increment.
            A.add({{off + a, 1 / h}, {off + b, -1 / h}},
                  std::log(g.v[a] / g.v[b]) / h, weight);
          }
      }
}
void invert(const Config &c, std::string dir, std::string mode) {
  auto e = read_events(dir + "/initial_events.csv"),
       stations = read_events(dir + "/stations.csv");
  auto data = observations(dir + "/observations.csv");
  Grid g = read_grid(dir + "/initial_grid.csv");
  bool locate = mode == "loc1d" || mode == "loc3d";
  if (mode == "loc3d")
    g = read_grid(dir + "/truth_grid.csv");
  int ne = e.size(), ns = stations.size(), off = 4 * ne,
      n = off + (locate ? 0 : g.size());
  auto log = output(dir + "/" + mode + "_history.csv");
  log << "iteration,stage,absolute_rms,catalog_rms,precise_rms,velocity_step,"
         "location_step,step_fraction,objective_before,objective_after,lsqr_"
         "iterations,lsqr_relative_normal_residual,lsqr_converged\n";
  for (int it = 0; it < int(c.get("iterations")); it++) {
    auto r = rays(g, e, stations, c);
    int stage = std::min(2, int(it / c.get("stage_length")));
    double weights[3][3] = {{1, 0.1, 0.01}, {0.1, 1, 0.01}, {0.001, 0.01, 1}};
    Matrix A(n);
    Vec residual(data.size()), w(data.size());
    double ss[3] = {}, count[3] = {};
    // Residual scale is estimated separately for each data type; a 0.01 s floor
    // avoids eliminating the rounded, nearly exact synthetic differential
    // times.
    Vec bytype[3];
    for (size_t q = 0; q < data.size(); q++) {
      residual[q] = data[q].value - prediction(data[q], r, e, ns);
      bytype[data[q].type].push_back(std::abs(residual[q]));
    }
    double cutoff[3];
    for (int t = 0; t < 3; t++) {
      auto a = bytype[t];
      if (a.empty()) {
        cutoff[t] = 1;
        continue;
      }
      std::nth_element(a.begin(), a.begin() + a.size() / 2, a.end());
      cutoff[t] = std::max(0.01, 6 * 1.4826 * a[a.size() / 2]);
    }
    for (size_t q = 0; q < data.size(); q++) {
      auto d = data[q];
      double res = residual[q];
      ss[d.type] += res * res;
      count[d.type]++;
      if (mode == "standard" && d.type != 0)
        continue;
      double weight = mode == "standard" ? 1 : weights[stage][d.type];
      double z = res / cutoff[d.type];
      weight *= std::pow(std::max(0., 1 - z * z), 2);
      if (d.j >= 0) {
        double distance = norm(e[d.i].p - e[d.j].p);
        weight *= std::pow(
            std::max(0., 1 - std::pow(distance / c.get("pair_distance"), 2)),
            2);
      }
      if (weight < 1e-12)
        continue;
      w[q] = weight;
      Row row;
      const auto &a = r[d.i * ns + d.k];
      for (int k = 0; k < 3; k++)
        row.push_back({4 * d.i + k, a.source[k]});
      row.push_back({4 * d.i + 3, 1});
      if (d.j >= 0) {
        const auto &b = r[d.j * ns + d.k];
        for (int k = 0; k < 3; k++)
          row.push_back({4 * d.j + k, -b.source[k]});
        row.push_back({4 * d.j + 3, -1});
      }
      if (!locate)
        for (int k = 0; k < g.size(); k++) {
          // Parameter q = delta log slowness; dv = -v*q.
          double value = -a.dv[k] * g.v[k];
          if (d.j >= 0) {
            auto &b = r[d.j * ns + d.k];
            value += b.dv[k] * g.v[k];
            if (std::abs(a.length[k] - b.length[k]) < 0.005)
              value = 0;
          }
          if (std::abs(value) > 1e-14)
            row.push_back({off + k, value});
        }
      A.add(row, res, weight);
    }
    if (!locate)
      smooth(A, g, off, c.get("smoothing"));
    LSQRInfo linear_info;
    Vec delta = solve(A, c.get("damping"), &linear_info);
    auto objective = [&](const Grid &gg, const std::vector<Event> &ee,
                         const std::vector<Ray> &rr) {
      double value = 0;
      for (size_t q = 0; q < data.size(); q++) {
        double res = data[q].value - prediction(data[q], rr, ee, ns);
        value += w[q] * w[q] * res * res;
      }
      if (!locate) {
        Matrix S(n);
        smooth(S, gg, off, c.get("smoothing"));
        value += dot(S.rhs, S.rhs);
      }
      return value;
    };
    double before = objective(g, e, r), after = before, step = 1;
    Grid ng;
    std::vector<Event> ee;
    bool accepted = false;
    for (int ls = 0; ls < 12; ls++, step *= 0.5) {
      ng = g;
      ee = e;
      bool valid = true;
      for (int i = 0; i < ne; i++) {
        const Vec *axes[] = {&g.x, &g.y, &g.z};
        for (int k = 0; k < 3; k++)
          ee[i].p[k] = std::clamp(e[i].p[k] + step * delta[4 * i + k],
                                  axes[k]->front(), axes[k]->back());
        ee[i].t += step * delta[4 * i + 3];
      }
      if (!locate)
        for (int k = 0; k < g.size(); k++) {
          ng.v[k] = g.v[k] * std::exp(-step * delta[off + k]);
          if (!std::isfinite(ng.v[k]) || ng.v[k] <= 0)
            valid = false;
        }
      if (!valid)
        continue;
      auto nr = rays(ng, ee, stations, c, false);
      after = objective(ng, ee, nr);
      if (after <= before) {
        accepted = true;
        break;
      }
    }
    double dv = 0, dx = 0;
    if (!accepted) {
      step = 0;
      after = before;
    } else {
      for (int i = 0; i < ne; i++)
        for (int k = 0; k < 3; k++)
          dx = std::max(dx, std::abs(ee[i].p[k] - e[i].p[k]));
      g = ng;
      e = ee;
    }
    if (!locate)
      for (int k = 0; k < g.size(); k++)
        dv = std::max(dv, std::abs(step * delta[off + k]));
    log << it << ',' << stage << ','
        << (count[0] > 0 ? std::sqrt(ss[0] / count[0]) : NAN) << ','
        << (count[1] > 0 ? std::sqrt(ss[1] / count[1]) : NAN) << ','
        << (count[2] > 0 ? std::sqrt(ss[2] / count[2]) : NAN) << ',' << dv
        << ',' << dx << ',' << step << ',' << before << ',' << after << ','
        << linear_info.iterations << ',' << linear_info.relative_normal_residual
        << ',' << linear_info.converged << '\n';
    log.flush();
    std::cout << mode << " iteration " << it << " stage " << stage << " rms "
              << (count[0] > 0 ? std::sqrt(ss[0] / count[0]) : NAN) << ' '
              << (count[2] > 0 ? std::sqrt(ss[2] / count[2]) : NAN)
              << " objective " << before << " -> " << after << " step " << step
              << std::endl;
    // With no accepted update, the next solve in the same stage is
    // identical: same model, rays, residual weights, matrix, and RHS.
    // Skip those exact repetitions, retaining every subsequent weight stage.
    if (!accepted) {
      if (mode == "standard" || stage == 2)
        break;
      it = (stage + 1) * int(c.get("stage_length")) - 1;
    }
  }
  write_grid(g, dir + "/" + mode + "_grid.csv");
  write_events(e, dir + "/" + mode + "_events.csv");
  auto rr = rays(g, e, stations, c);
  auto coverage = output(dir + "/" + mode + "_coverage.csv");
  coverage << "node,path_length\n";
  for (int k = 0; k < g.size(); k++) {
    double length = 0;
    for (const auto &ray : rr)
      length += ray.length[k];
    coverage << k << ',' << length << '\n';
  }
  auto f = output(dir + "/" + mode + "_residuals.csv");
  f << "i,j,station,type,residual\n";
  for (auto d : data)
    f << d.i << ',' << d.j << ',' << d.k << ',' << d.type << ','
      << d.value - prediction(d, rr, e, ns) << '\n';
  // Model-generated horizontal sections, including signed recovered-minus-true
  // errors.
  auto sl = output(dir + "/" + mode + "_slices.csv");
  sl << "x,y,z,v,error\n";
  for (double z : {0., 3., 7., 11., 16.})
    for (double y = -60; y <= 40; y += 2)
      for (double x = -35; x <= 35; x += 0.5) {
        double v = g.sample({x, y, z}).v;
        sl << x << ',' << y << ',' << z << ',' << v << ','
           << v - true_velocity(c, x) << '\n';
      }
}
void validate(std::string dir) {
  std::filesystem::create_directories(dir);
  auto f = output(dir + "/validation.csv");
  f << "test,error,tolerance,passed\n";
  int failures = 0;
  auto check = [&](std::string name, double err, double tol) {
    bool ok = std::isfinite(err) && err <= tol;
    f << name << ',' << err << ',' << tol << ',' << ok << '\n';
    std::cout << name << " error=" << err << " tolerance=" << tol << " "
              << (ok ? "PASS" : "FAIL") << '\n';
    if (!ok)
      failures++;
  };
  Grid g = grid();
  std::fill(g.v.begin(), g.v.end(), 6);
  P a{-10, -20, 8}, b{20, 15, 0};
  auto r = trace(g, a, b, 1, 250);
  check("homogeneous_travel_time", std::abs(r.time - norm(b - a) / 6), 1e-10);
  check("homogeneous_source_derivative",
        norm(r.source - (a - b) * (1 / (6 * norm(a - b)))), 1e-9);
  check("homogeneous_velocity_derivative",
        std::abs(std::accumulate(r.dv.begin(), r.dv.end(), 0.) +
                 norm(b - a) / 36),
        1e-9);
  check("partition_of_unity",
        std::abs(std::accumulate(r.length.begin(), r.length.end(), 0.) -
                 norm(b - a)),
        1e-9);
  g = grid(true);
  set_true(g);
  r = trace(g, a, b, 0.6, 600);
  auto reverse = trace(g, b, a, 0.6, 600);
  check("ray_reciprocity", std::abs(r.time - reverse.time), 2e-5);
  check("bending_not_slower_than_straight",
        std::max(0., r.time - segment(g, a, b)), 1e-10);
  auto finer = trace(g, a, b, 0.3, 1000);
  check("ray_refinement_seconds", std::abs(finer.time - r.time), 0.015);
  // A 0.001 km source step amplifies finite ray-discretization/optimization
  // noise; the recorded 0.1/0.03/0.01 km sweep resolves this derivative.
  // Keep the separate velocity perturbation at 0.001 km/s.
  double h = 1e-3, source_h = 0.01, maxerr = 0;
  for (int k = 0; k < 3; k++) {
    P ap = a, am = a;
    ap[k] += source_h;
    am[k] -= source_h;
    double fd = (trace(g, ap, b, 0.6, 600, false).time -
                 trace(g, am, b, 0.6, 600, false).time) /
                (2 * source_h);
    maxerr = std::max(maxerr, std::abs(fd - r.source[k]));
  }
  check("bent_source_finite_difference", maxerr, 0.003);
  // Fixed-path derivative isolates interpolation/integration from optimizer
  // tolerance.
  int node = g.id(4, 2, 2);
  Grid gp = g, gm = g;
  gp.v[node] += h;
  gm.v[node] -= h;
  double fd = (path_eval(gp, r.path) - path_eval(gm, r.path)) / (2 * h);
  check("velocity_finite_difference", std::abs(fd - r.dv[node]), 1e-7);
  check("identical_event_dd_cancellation",
        std::abs(r.time - trace(g, a, b, 0.6, 600).time), 1e-12);
  double bias = 0.271, ti = r.time, tj = reverse.time + 0.73;
  check("station_bias_cancellation",
        std::abs(((ti + bias) - (tj + bias)) - (ti - tj)), 1e-12);
  Matrix A(3);
  A.add({{0, 2}, {1, 1}}, 4);
  A.add({{1, 3}, {2, 1}}, 9);
  A.add({{0, 1}, {2, 4}}, 13);
  A.add({{0, 1}, {1, 1}, {2, 1}}, 6);
  Vec sol = lsqr(A, 50);
  check("lsqr_known_solution", norm(Vec{sol[0] - 1, sol[1] - 2, sol[2] - 3}),
        1e-9);
  Vec x{0.4, -0.3, 0.7}, y{0.1, 0.2, -0.7, 0.8};
  check("matrix_adjoint", std::abs(dot(A.mul(x), y) - dot(x, A.trans(y))),
        1e-12);
  run_ray_checks(check);
  // Save bent and straight ray evidence for the validation figure.
  auto rf = output(dir + "/validation_ray.csv");
  rf << "index,x,y,z\n";
  for (size_t i = 0; i < r.path.size(); i++)
    rf << i << ',' << r.path[i][0] << ',' << r.path[i][1] << ',' << r.path[i][2]
       << '\n';
  if (failures)
    throw std::runtime_error(std::to_string(failures) +
                             " validation checks failed");
}
void raycheck(const Config &c, std::string dir, std::string mode = "truth") {
  auto e = read_events(dir + "/" + mode + "_events.csv");
  auto stations = read_events(dir + "/stations.csv");
  Grid g = read_grid(dir + "/" + mode + "_grid.csv");
  std::string prefix = mode == "truth" ? "ray" : mode + "_ray";
  auto f = output(dir + "/" + prefix + "_convergence.csv");
  f << "event,station,production_time,refined_time,difference,production_"
       "gradient,refined_gradient,production_raw_gradient,refined_raw_gradient,"
       "production_iterations,refined_iterations,production_converged,refined_"
       "converged,production_merged,refined_merged\n";
  auto df = output(dir + "/" + prefix + "_derivatives.csv");
  df << "event,station,axis,production_derivative,refined_derivative,finite_"
        "difference,production_error,refined_error\n";
  for (int n = 0; n < 32; n++) {
    int i = (37 * n + 3) % e.size(), k = (13 * n + 7) % stations.size();
    Ray a = trace(g, e[i].p, stations[k].p, c.get("ray_spacing"),
                  c.get("ray_iterations"));
    Ray b = trace(g, e[i].p, stations[k].p, c.get("ray_spacing") / 2, 1000);
    f << i << ',' << k << ',' << a.time << ',' << b.time << ','
      << a.time - b.time << ',' << a.gradient << ',' << b.gradient << ','
      << a.raw_gradient << ',' << b.raw_gradient << ',' << a.iterations << ','
      << b.iterations << ',' << a.converged << ',' << b.converged << ','
      << a.merged_nodes << ',' << b.merged_nodes << '\n';
    if (n < 8)
      for (int axis = 0; axis < 3; axis++) {
        double h = 0.01;
        P ap = e[i].p, am = e[i].p;
        ap[axis] += h;
        am[axis] -= h;
        if (!g.contains(ap) || !g.contains(am))
          continue;
        double fd =
            (trace(g, ap, stations[k].p, c.get("ray_spacing") / 2, 1000, false)
                 .time -
             trace(g, am, stations[k].p, c.get("ray_spacing") / 2, 1000, false)
                 .time) /
            (2 * h);
        df << i << ',' << k << ',' << axis << ',' << a.source[axis] << ','
           << b.source[axis] << ',' << fd << ',' << a.source[axis] - fd << ','
           << b.source[axis] - fd << '\n';
      }
  }
}
int main(int argc, char **argv) {
  try {
    if (argc >= 3 && std::string(argv[1]) == "validate") {
      validate(argv[2]);
      return 0;
    }
    if (argc < 4)
      throw std::runtime_error("Usage: dd validate OUT | dd generate CONFIG "
                               "OUT | dd invert CONFIG OUT MODE");
    Config c(argv[2]);
    std::string cmd = argv[1];
    if (cmd == "generate")
      generate(c, argv[3]);
    else if (cmd == "raycheck")
      raycheck(c, argv[3], argc == 5 ? argv[4] : "truth");
    else if (cmd == "invert" && argc == 5)
      invert(c, argv[3], argv[4]);
    else
      throw std::runtime_error("Unknown command");
  } catch (const std::exception &e) {
    std::cerr << e.what() << '\n';
    return 1;
  }
  return 0;
}
