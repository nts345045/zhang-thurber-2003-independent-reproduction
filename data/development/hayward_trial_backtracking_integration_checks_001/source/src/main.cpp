#include "core.hpp"
#include "forward.hpp"
#include "ray_checks.hpp"
#include "csv.hpp"
#include <filesystem>
#include <optional>
struct Event {
  P p;
  double t = 0;
  Metadata metadata{};
};
struct Datum {
  int i, j, k, type;
  double value;
  double a_priori_weight = 1;
  int station_j = -1; // Absent in legacy files: both events use station k.
};
// Numeric rows never own repeated metadata strings. Ordinary observational
// inputs keep their complete native metadata separately. Only the exact
// identified synthetic schema may share its event/channel/constant strings.
struct ObservationSet {
  std::vector<Datum> rows;
  Strings metadata_header;
  std::vector<Metadata> native_metadata;
  bool shared_synthetic = false;
  std::vector<std::array<std::string, 2>> event_ids;
  std::vector<Strings> channel_ids;
  std::array<Strings, 3> synthetic_values;
  size_t size() const { return rows.size(); }
  bool empty() const { return rows.empty(); }
  const Datum &operator[](size_t q) const { return rows[q]; }
  Datum &operator[](size_t q) { return rows[q]; }
  auto begin() const { return rows.begin(); }
  auto end() const { return rows.end(); }
  auto begin() { return rows.begin(); }
  auto end() { return rows.end(); }
  const std::string &shared_value(const Datum &d, size_t field) const {
    static const std::string empty;
    if (field < 4) {
      int event = field < 2 ? d.i : d.j;
      return event < 0 ? empty : event_ids[event][field % 2];
    }
    if (field < 12)
      return channel_ids[d.k][field - 4];
    return synthetic_values[d.type][field - 12];
  }
  void write_header(std::ostream &out, const std::string &prefix = "") const {
    for (const auto &name : metadata_header)
      out << ',' << csv_quote(prefix + name);
  }
  void write_metadata(std::ostream &out, size_t q) const {
    if (!shared_synthetic) {
      csv_metadata_values(out, native_metadata[q]);
      return;
    }
    for (size_t field = 0; field < metadata_header.size(); ++field)
      out << ',' << csv_quote(shared_value(rows[q], field));
  }
};
std::ofstream output(std::string p) {
  std::ofstream f(p);
  if (!f)
    throw std::runtime_error("Cannot write " + p);
  f << std::setprecision(12);
  return f;
}
// Failure evidence must be fully written before a trial can be rejected safely.
void finish_output(std::ofstream &stream, const std::string &path) {
  stream.flush();
  stream.close();
  if (!stream) throw std::runtime_error("Cannot finish writing " + path);
}
void require_new_outputs(const std::string &prefix, const std::vector<std::string> &suffixes) {
  for (const auto &suffix : suffixes)
    if (std::filesystem::exists(std::filesystem::symlink_status(prefix + suffix)))
      throw std::runtime_error("Refusing prior failure/audit artifact " + prefix + suffix);
}
void write_grid(const Grid &g, std::string path, int precision = 12) {
  auto f = output(path);
  f << std::setprecision(precision);
  f << "x,y,z,v\n";
  for (int k = 0; k < int(g.z.size()); k++)
    for (int j = 0; j < int(g.y.size()); j++)
      for (int i = 0; i < int(g.x.size()); i++)
        f << g.x[i] << ',' << g.y[j] << ',' << g.z[k] << ','
          << g.v[g.id(i, j, k)] << '\n';
  finish_output(f, path);
}
void write_events(const std::vector<Event> &e, std::string path, int precision = 12) {
  auto f = output(path);
  f << std::setprecision(precision);
  f << "id,x,y,z,t";
  if (!e.empty())
    csv_metadata_header(f, e.front().metadata);
  f << '\n';
  for (size_t i = 0; i < e.size(); i++) {
    f << i << ',' << e[i].p[0] << ',' << e[i].p[1] << ',' << e[i].p[2] << ','
      << e[i].t;
    csv_metadata_values(f, e[i].metadata);
    f << '\n';
  }
  finish_output(f, path);
}
std::vector<Vec> read_csv(std::string path) {
  std::vector<Vec> r;
  for (const auto &fields : csv_table(path).rows) {
    Vec row;
    for (const auto &field : fields)
      row.push_back(csv_double(field));
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
  auto table = csv_table(path, {"id", "x", "y", "z", "t"});
  for (const auto &row : table.rows) {
    if (csv_int(row[0]) != int(e.size()))
      throw std::runtime_error("Event/station IDs must be consecutive row indices in " + path);
    e.push_back({{csv_double(row[1]), csv_double(row[2]), csv_double(row[3])},
                 csv_double(row[4]), csv_metadata(table, row, 5)});
  }
  if (e.empty())
    throw std::runtime_error("No events/stations in " + path);
  return e;
}
double setting(const Config &c, const std::string &key, double fallback) {
  auto it = c.v.find(key);
  return it == c.v.end() ? fallback : it->second;
}
double auxiliary_spacing(const Config &c) {
  double mode = setting(c, "ray_initializer", 0);
  if (mode == 0) return 0;
  if (mode != 1)
    throw std::runtime_error("ray_initializer must be 0 (straight) or 1 (FMM)");
  double spacing = c.get("fmm_spacing");
  if (!(spacing > 0) || !std::isfinite(spacing))
    throw std::runtime_error("fmm_spacing must be finite and positive");
  return spacing;
}
Ray configured_trace(const Grid &g, P source, P receiver, const Config &c,
                     ForwardFields &cache, bool deriv = true) {
  double aux = auxiliary_spacing(c);
  if (aux == 0)
    return trace(g, source, receiver, c.get("ray_spacing"), c.get("ray_iterations"), deriv);
  const auto &field = cache.get(g, receiver, aux);
  return trace_first_arrival(g, source, receiver, c.get("ray_spacing"),
                            c.get("ray_iterations"), deriv, field);
}
std::string ray_identity_context(const std::vector<Event> &events,
                                 const std::vector<Event> &stations, int i, int k) {
  std::ostringstream message;
  message << "event " << i;
  for (const auto *name : {"event_resource_id", "origin_resource_id"})
    if (const auto *value = metadata_value(events[i].metadata, name))
      message << ' ' << name << '=' << *value;
  message << "; native receiver " << k;
  for (const auto *name : {"channel_seed_id", "channel_fdsn_source_id",
                          "metadata_epoch_start", "metadata_epoch_end"})
    if (const auto *value = metadata_value(stations[k].metadata, name))
      message << ' ' << name << '=' << *value;
  return message.str();
}
void prepare_receiver_fields(const Grid &g, const std::vector<Event> &events,
                             const std::vector<Event> &stations, double spacing,
                             ForwardFields &cache, const std::vector<int> &support) {
  std::vector<P> receivers;
  receivers.reserve(support.size());
  for (int n : support) receivers.push_back(stations[n % stations.size()].p);
  std::size_t failed_receiver = receivers.size();
  try { cache.prepare(g, receivers, spacing, &failed_receiver); }
  catch (const std::exception &error) {
    if (failed_receiver < support.size()) {
      int n = support[failed_receiver];
      throw std::runtime_error("Receiver-field construction failed for " +
          ray_identity_context(events, stations, n / stations.size(), n % stations.size()) +
          ": " + error.what());
    }
    throw std::runtime_error("Receiver-field preparation failed: " + std::string(error.what()));
  }
}
std::vector<Ray> rays(const Grid &g, const std::vector<Event> &e,
                      const std::vector<Event> &s, const Config &c,
                      bool deriv = true, const std::vector<int> *used = nullptr,
                      ForwardFields *saved_fields = nullptr,
                      bool require_initialization = true) {
  std::vector<Ray> r(e.size() * s.size());
  std::vector<std::string> errors(r.size());
  const int count = used ? int(used->size()) : int(r.size());
  ForwardFields local_fields;
  auto &cache = saved_fields ? *saved_fields : local_fields;
  double aux = auxiliary_spacing(c);
  std::vector<const first_arrival::Field *> fields(s.size(), nullptr);
  // Prepare independent receiver fields in parallel, with serial cache changes.
  // Native station indices are never combined or renumbered.
  if (aux > 0) {
    std::vector<int> first_observations;
    std::vector<bool> requested(s.size(), false);
    for (int q = 0; q < count; ++q) {
      int n = used ? (*used)[q] : q, k = n % s.size();
      if (!requested[k]) {
        requested[k] = true;
        first_observations.push_back(n);
      }
    }
    prepare_receiver_fields(g, e, s, aux, cache, first_observations);
    for (std::size_t k = 0; k < s.size(); ++k)
      if (requested[k]) fields[k] = &cache.get(g, s[k].p, aux);
  }
#pragma omp parallel for schedule(dynamic)
  for (int q = 0; q < count; q++) {
    int n = used ? (*used)[q] : q;
    int i = n / s.size(), k = n % s.size();
    try {
      r[n] = aux > 0 ? trace_first_arrival(g, e[i].p, s[k].p, c.get("ray_spacing"),
                                          c.get("ray_iterations"), deriv, *fields[k]) :
                      trace(g, e[i].p, s[k].p, c.get("ray_spacing"),
                            c.get("ray_iterations"), deriv);
    } catch (const std::exception &error) {
      // Exceptions cannot cross an OpenMP worker boundary. Preserve the native
      // index and message, then report outside the parallel loop.
      errors[n] = error.what();
      r[n].time = r[n].gradient = r[n].raw_gradient = NAN;
      r[n].initializer_message = "Ray evaluation exception: " + errors[n];
    }
  }
  // Simulation deliberately retains every failed record for its full-support
  // status table and gate. Other callers receive an identified exception.
  if (require_initialization)
    for (int q = 0; q < count; ++q) {
      int n = used ? (*used)[q] : q;
      const auto context = [&]() { return ray_identity_context(e, s, n / s.size(), n % s.size()); };
      if (!errors[n].empty())
        throw std::runtime_error("Ray evaluation failed for " + context() + ": " + errors[n]);
      if (aux > 0 && !r[n].initialization_succeeded)
        throw std::runtime_error("FMM extraction failed for " + context() + ": " + r[n].initializer_message);
    }
  return r;
}
void initializer_header(std::ostream &out, const std::string &prefix) {
  for (const char *name : {"initialization_attempted", "initialization_succeeded",
       "selected_fmm_seed", "direct_seed_time", "fmm_seed_time", "field_time",
       "extraction_fallback_steps", "extraction_message"})
    out << ',' << prefix << name;
}
void initializer_values(std::ostream &out, const Ray &r) {
  out << ',' << r.initialization_attempted << ',' << r.initialization_succeeded
      << ',' << r.selected_fmm_seed << ',' << r.direct_seed_time << ','
      << r.fmm_seed_time << ',' << r.initializer_field_time << ','
      << r.initializer_fallback_steps << ',' << csv_quote(r.initializer_message);
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

void set_metadata(Metadata &metadata, const std::string &key, const std::string &value) {
  for (auto &field : metadata)
    if (field.first == key) {
      field.second = value;
      return;
    }
  metadata.push_back({key, value});
}

Metadata simulation_metadata(const std::vector<Event> &events,
                             const std::vector<Event> &stations,
                             int i, int j, int k, int type) {
  Metadata result;
  for (const auto &side : {std::make_pair("i", i), std::make_pair("j", j)})
    for (const auto *kind : {"event", "origin"}) {
      std::string key = std::string(kind) + "_resource_id";
      result.push_back({std::string(kind) + "_" + side.first + "_resource_id",
                        side.second < 0 ? "" : required_metadata(events[side.second].metadata, key)});
    }
  for (const auto *key : {"network_code", "station_code", "location_code", "channel_code",
                          "channel_seed_id", "channel_fdsn_source_id",
                          "metadata_epoch_start", "metadata_epoch_end"})
    result.push_back({key, required_metadata(stations[k].metadata, key,
                      std::string(key) == "location_code" || std::string(key) == "metadata_epoch_end")});
  const char *basis[] = {"synthetic noisy absolute travel time",
                         "synthetic difference of noisy absolute travel times",
                         "synthetic difference of rounded noise-free travel times"};
  result.push_back({"synthetic_observation", "1"});
  result.push_back({"observation_basis", basis[type]});
  result.push_back({"source_position_basis", "catalog-defined simulation truth"});
  result.push_back({"simulation_origin_time_basis", "zero for every truth event; no observed pick times"});
  result.push_back({"event_geometry_table", "truth_events.csv"});
  result.push_back({"receiver_geometry_table", "stations.csv"});
  return result;
}

bool finite_ray(const Ray &ray) {
  if (!std::isfinite(ray.time) || ray.time < 0 || !std::isfinite(ray.gradient) ||
      !std::isfinite(ray.raw_gradient) || ray.path.empty())
    return false;
  for (const auto &point : ray.path)
    for (double value : point)
      if (!std::isfinite(value)) return false;
  for (double value : ray.source)
    if (!std::isfinite(value)) return false;
  for (const auto *values : {&ray.dv, &ray.length})
    for (double value : *values)
      if (!std::isfinite(value)) return false;
  return true;
}
void ray_status_header(std::ostream &out) {
  out << ",ray_converged,ray_finite,ray_projected_gradient,ray_raw_gradient,"
         "ray_iterations,ray_merged_nodes";
  initializer_header(out, "ray_");
}
void ray_status_values(std::ostream &out, const Ray &ray) {
  out << ',' << ray.converged << ',' << finite_ray(ray) << ',' << ray.gradient
      << ',' << ray.raw_gradient << ',' << ray.iterations << ',' << ray.merged_nodes;
  initializer_values(out, ray);
}
bool ray_path_in_domain(const Grid &g, const Ray &ray) {
  return !ray.path.empty() && std::all_of(ray.path.begin(), ray.path.end(),
                                         [&](P point) { return g.contains(point); });
}
// Save native identities and unchanged local status. Optional preflight fields
// expose pure travel time, source partials and path geometry from the same rays
// used for the matrix census. None of these flags certifies a first arrival.
std::pair<size_t, size_t> write_ray_status(const std::string &path,
                         const std::vector<Event> &events, const std::vector<Event> &stations,
                         const std::vector<Ray> &rr, const std::vector<int> *used = nullptr,
                         const Grid *path_grid = nullptr, int precision = 12,
                         std::optional<bool> derivatives_evaluated = {}) {
  if (rr.size() != events.size() * stations.size())
    throw std::runtime_error("Incomplete ray array");
  auto out = output(path);
  out << std::setprecision(precision);
  out << "event,station,source_x,source_y,source_z,receiver_x,receiver_y,receiver_z,ray_time";
  ray_status_header(out);
  if (path_grid)
    out << ",source_t,source_dx,source_dy,source_dz,ray_path_points,ray_path_in_domain,"
           "ray_exact_source_endpoint,ray_exact_receiver_endpoint";
  if (derivatives_evaluated.has_value()) out << ",ray_derivatives_evaluated";
  csv_metadata_header(out, events.front().metadata, "source_");
  csv_metadata_header(out, stations.front().metadata, "receiver_");
  out << '\n';
  size_t failures = 0, first = 0;
  const size_t count = used ? used->size() : rr.size();
  for (size_t q = 0; q < count; ++q) {
    size_t n = used ? (*used)[q] : q;
    size_t i = n / stations.size(), k = n % stations.size();
    const auto &ray = rr[n];
    // A worker exception leaves an empty Ray, even when derivatives were
    // requested. Do not export its default zeros as evaluated partials.
    const bool evaluated = derivatives_evaluated.value_or(true) &&
        (!derivatives_evaluated.has_value() || !path_grid ||
         (ray.dv.size() == path_grid->v.size() && ray.length.size() == path_grid->v.size()));
    out << i << ',' << k;
    for (double value : events[i].p) out << ',' << value;
    for (double value : stations[k].p) out << ',' << value;
    out << ',' << ray.time;
    ray_status_values(out, ray);
    if (path_grid) {
      out << ',' << events[i].t;
      for (double value : ray.source) {
        out << ',';
        if (evaluated) out << value;
      }
      out << ',' << ray.path.size() << ',' << ray_path_in_domain(*path_grid, ray)
          << ',' << (!ray.path.empty() && ray.path.front() == events[i].p)
          << ',' << (!ray.path.empty() && ray.path.back() == stations[k].p);
    }
    if (derivatives_evaluated.has_value()) out << ',' << evaluated;
    csv_metadata_values(out, events[i].metadata);
    csv_metadata_values(out, stations[k].metadata);
    out << '\n';
    if (!finite_ray(ray) || !ray.converged ||
        (path_grid && (!ray_path_in_domain(*path_grid, ray) ||
                       ray.path.front() != events[i].p || ray.path.back() != stations[k].p)) ||
        (ray.initialization_attempted && !ray.initialization_succeeded)) {
      if (failures == 0) first = n;
      ++failures;
    }
  }
  finish_output(out, path);
  return {failures, first};
}
void simulation_ray_gate(const std::string &dir, const std::vector<Event> &events,
                         const std::vector<Event> &stations, const std::vector<Ray> &rr) {
  auto status = write_ray_status(dir + "/simulation_ray_status.csv", events, stations, rr);
  if (status.first)
    throw std::runtime_error("Simulation truth-ray gate rejected " + std::to_string(status.first) +
        " rays before travel-time rounding/observation noise; see simulation_ray_status.csv; first: " +
        ray_identity_context(events, stations, status.second / stations.size(), status.second % stations.size()));
}

// Shared noise generation preserves the original generator's random-number order.
void synthetic_observations(const Config &c, const std::string &dir,
                            const std::vector<Event> &events,
                            const std::vector<Event> &stations,
                            const std::vector<Ray> &rr, std::mt19937 &gen,
                            std::uniform_real_distribution<double> &u,
                            std::normal_distribution<double> &normal,
                            bool identified_geometry = false,
                            const Vec *analytic_times = nullptr) {
  const int ne = events.size(), ns = stations.size();
  const size_t count=analytic_times ? analytic_times->size() : rr.size();
  if (count!=size_t(ne)*ns || (analytic_times && (!identified_geometry || !rr.empty())))
    throw std::runtime_error("Synthetic travel-time inventory or explicit truth mode differs");
  Vec true_t(count), abs_t(count), rounded(count), bias(ns);
  for (auto &v : bias)
    v = (2 * u(gen) - 1) * c.get("station_noise");
  auto raw = output(dir + "/arrivals.csv");
  raw << "event,station,true_time,rounded_time,station_bias,pick_noise,absolute_time";
  if (identified_geometry)
    csv_metadata_header(raw, simulation_metadata(events, stations, 0, -1, 0, 0));
  ray_status_header(raw);
  if (analytic_times)
    raw<<",truth_mode,reference_pair_index,reference_complete,reference_valid,reference_near_tie_count";
  raw << '\n';
  std::ostringstream ray_header;
  ray_status_header(ray_header);
  const std::string ray_fields=ray_header.str();
  const std::string absent_ray_fields(std::count(ray_fields.begin(),ray_fields.end(),','),',');
  for (int i = 0; i < ne; i++)
    for (int k = 0; k < ns; k++) {
      int n = i * ns + k;
      true_t[n] = analytic_times ? (*analytic_times)[n] : rr[n].time;
      double quantum = setting(c, "time_quantum", 0.01);
      rounded[n] = quantum > 0 ? std::round(true_t[n] / quantum) * quantum : true_t[n];
      double noise = c.get("noise") * normal(gen);
      abs_t[n] = rounded[n] + bias[k] + noise;
      raw << i << ',' << k << ',' << true_t[n] << ',' << rounded[n] << ','
          << bias[k] << ',' << noise << ',' << abs_t[n];
      if (identified_geometry)
        csv_metadata_values(raw, simulation_metadata(events, stations, i, -1, k, 0));
      if (analytic_times)
        raw<<absent_ray_fields<<",continuous_layered_snell_reference,"<<n<<",1,1,1";
      else
        ray_status_values(raw, rr[n]);
      raw << '\n';
    }
  auto f = output(dir + "/observations.csv");
  f << "i,j,station,type,value";
  if (identified_geometry)
    csv_metadata_header(f, simulation_metadata(events, stations, 0, -1, 0, 0));
  f << '\n';
  auto observation = [&](int i, int j, int k, int type, double value) {
    f << i << ',' << j << ',' << k << ',' << type << ',' << value;
    if (identified_geometry)
      csv_metadata_values(f, simulation_metadata(events, stations, i, j, k, type));
    f << '\n';
  };
  for (int i = 0; i < ne; i++)
    for (int k = 0; k < ns; k++)
      observation(i, -1, k, 0, abs_t[i * ns + k]);
  for (int i = 0; i < ne; i++)
    for (int j = i + 1; j < ne; j++)
      if (norm(events[i].p - events[j].p) < c.get("pair_distance"))
        for (int k = 0; k < ns; k++) {
          observation(i, j, k, 1, abs_t[i * ns + k] - abs_t[j * ns + k]);
          observation(i, j, k, 2, rounded[i * ns + k] - rounded[j * ns + k]);
        }
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
  synthetic_observations(c, dir, e, s, rr, gen, u, normal);
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
void validate_observation_indices(const Datum &d, int ne, int ns);
void validate_geometry(const std::vector<Event> &events,
                       const std::vector<Event> &stations);

ObservationSet observations(const std::string &path,
                            const std::vector<Event> &events = {},
                            const std::vector<Event> &stations = {},
                            bool shared_synthetic = false) {
  std::ifstream f(path);
  if (!f)
    throw std::runtime_error("Cannot read " + path);
  const auto header = csv_header(f, path, {"i", "j", "station", "type", "value"});
  ObservationSet data;
  data.metadata_header.assign(header.begin() + 5, header.end());
  data.shared_synthetic = shared_synthetic;
  if (shared_synthetic) {
    validate_geometry(events, stations);
    if (events.empty() || stations.empty())
      throw std::runtime_error("Shared synthetic metadata requires identified geometry");
    for (const auto &event : events)
      data.event_ids.push_back({required_metadata(event.metadata, "event_resource_id"),
                               required_metadata(event.metadata, "origin_resource_id")});
    for (size_t k = 0; k < stations.size(); ++k) {
      auto schema = simulation_metadata(events, stations, 0, -1, k, 0);
      Strings channel;
      for (size_t field = 4; field < 12; ++field)
        channel.push_back(schema[field].second);
      data.channel_ids.push_back(std::move(channel));
    }
    for (int type = 0; type < 3; ++type) {
      auto schema = simulation_metadata(events, stations, 0, -1, 0, type);
      if (schema.size() != data.metadata_header.size())
        throw std::runtime_error("Unexpected shared synthetic metadata schema");
      for (size_t field = 0; field < schema.size(); ++field) {
        if (data.metadata_header[field] != schema[field].first)
          throw std::runtime_error("Unexpected shared synthetic metadata column: " + data.metadata_header[field]);
        if (field >= 12)
          data.synthetic_values[type].push_back(schema[field].second);
      }
    }
  }
  // Count complete CSV records first, then allocate the numeric vector once.
  // Neither pass retains CSV strings beyond the current record.
  const auto body = f.tellg();
  Strings row;
  size_t count = 0;
  while (csv_row(f, row, header.size(), path)) {
    if (count == data.rows.max_size())
      throw std::runtime_error("Observation count exceeds numeric storage capacity");
    ++count;
  }
  if (!count)
    throw std::runtime_error("No observations in " + path);
  data.rows.reserve(count);
  if (!shared_synthetic)
    data.native_metadata.reserve(count);
  f.clear();
  f.seekg(body);
  if (!f)
    throw std::runtime_error("Cannot rewind observation CSV: " + path);
  while (csv_row(f, row, header.size(), path)) {
    if (data.size() == count)
      throw std::runtime_error("Observation CSV changed between counting and loading");
    Datum datum{csv_int(row[0]), csv_int(row[1]), csv_int(row[2]),
                csv_int(row[3]), csv_double(row[4])};
    if (shared_synthetic) {
      validate_observation_indices(datum, events.size(), stations.size());
      for (size_t field = 0; field < data.metadata_header.size(); ++field)
        if (row[field + 5] != data.shared_value(datum, field))
          throw std::runtime_error("Synthetic identity/value mismatch at row " +
                                   std::to_string(data.size()) + ": " + data.metadata_header[field]);
    } else {
      auto metadata = csv_metadata(header, row, 5);
      if (const auto *station = metadata_value(metadata, "station_j")) {
        if (!station->empty())
          datum.station_j = csv_int(*station);
        if (datum.j >= 0 && (station->empty() || datum.station_j < 0))
          throw std::runtime_error("Differential observation requires a nonnegative station_j when that column is present");
        if (datum.j < 0 && datum.station_j != -1)
          throw std::runtime_error("Absolute observation station_j must be empty or -1");
      }
      if (const auto *weight = metadata_value(metadata, "a_priori_weight")) {
        datum.a_priori_weight = csv_double(*weight);
        if (datum.a_priori_weight < 0)
          throw std::runtime_error("Negative a_priori_weight");
      }
      data.native_metadata.push_back(std::move(metadata));
    }
    data.rows.push_back(datum);
  }
  if (data.size() != count)
    throw std::runtime_error("Observation CSV changed between counting and loading");
  return data;
}

int second_station(const Datum &d) {
  return d.station_j < 0 ? d.k : d.station_j;
}

void validate_observation_indices(const Datum &d, int ne, int ns) {
  if (d.i < 0 || d.i >= ne || d.k < 0 || d.k >= ns || d.type < 0 || d.type > 2 ||
      (d.type == 0 ? d.j != -1 : (d.j < 0 || d.j >= ne || d.i == d.j)) ||
      d.station_j < -1 || d.station_j >= ns || (d.j < 0 && d.station_j != -1))
    throw std::runtime_error("Invalid observation event/station/type indices");
}

// Separate receiver rows retain native metadata epochs. Cross-epoch DD is only
// defined here for the same identified channel at exactly the same position.
void validate_receiver_pair(const Datum &d, const Metadata &metadata,
                            const std::vector<Event> &stations) {
  const auto *j_start = metadata_value(metadata, "metadata_epoch_j_start");
  const auto *j_end = metadata_value(metadata, "metadata_epoch_j_end");
  if (d.j < 0) {
    if ((j_start && !j_start->empty()) || (j_end && !j_end->empty()))
      throw std::runtime_error("Absolute observation has a second receiver epoch");
    return;
  }
  if (d.station_j < 0 && !j_start && !j_end)
    return; // Legacy DD uses the same receiver row and epoch on both sides.
  const auto &a = stations[d.k], &b = stations[second_station(d)];
  if (a.p != b.p)
    throw std::runtime_error("Differential receiver epochs have different coordinates");
  for (const auto *key : {"network_code", "station_code", "location_code", "channel_code",
                          "channel_seed_id", "channel_fdsn_source_id"}) {
    bool empty = std::string(key) == "location_code";
    if (required_metadata(a.metadata, key, empty) != required_metadata(b.metadata, key, empty))
      throw std::runtime_error(std::string("Differential receiver channel mismatch: ") + key);
  }
  for (const auto *key : {"channel_seed_id", "channel_fdsn_source_id",
                          "metadata_epoch_start", "metadata_epoch_end"}) {
    bool empty = std::string(key) == "metadata_epoch_end";
    if (required_metadata(metadata, key, empty) != required_metadata(a.metadata, key, empty))
      throw std::runtime_error(std::string("Observation/channel identity mismatch: ") + key);
  }
  for (const auto *edge : {"start", "end"}) {
    std::string field = std::string("metadata_epoch_j_") + edge;
    if (required_metadata(metadata, field, std::string(edge) == "end") !=
        required_metadata(b.metadata, std::string("metadata_epoch_") + edge, std::string(edge) == "end"))
      throw std::runtime_error("Observation/second receiver epoch mismatch: " + field);
  }
}

std::vector<int> observed_rays(const ObservationSet &data, int ne,
                              const std::vector<Event> &stations) {
  int ns = stations.size();
  if (ne <= 0 || ns <= 0 || size_t(ne) * size_t(ns) > size_t(std::numeric_limits<int>::max()))
    throw std::runtime_error("Invalid event/station dimensions");
  std::vector<unsigned char> present(size_t(ne) * ns, 0);
  for (size_t q = 0; q < data.size(); ++q) {
    const auto &d = data[q];
    validate_observation_indices(d, ne, ns);
    if (!data.shared_synthetic)
      validate_receiver_pair(d, data.native_metadata[q], stations);
    present[d.i * ns + d.k] = 1;
    if (d.j >= 0)
      present[d.j * ns + second_station(d)] = 1;
  }
  std::vector<int> used;
  for (size_t index = 0; index < present.size(); ++index)
    if (present[index])
      used.push_back(int(index));
  return used;
}

bool authoritative_input(const Config &c, const std::string &dir) {
  return setting(c, "authoritative_ids_required", 0) != 0 ||
         std::filesystem::exists(dir + "/authoritative_ids_required");
}

bool authoritative_geometry(const Config &c, const std::string &dir) {
  return setting(c, "authoritative_geometry", 0) != 0 ||
         std::filesystem::exists(dir + "/authoritative_geometry");
}

void validate_geometry(const std::vector<Event> &events,
                       const std::vector<Event> &stations) {
  for (const auto &event : events)
    for (const auto *key : {"event_resource_id", "origin_resource_id"})
      required_metadata(event.metadata, key);
  for (const auto &station : stations) {
    for (const auto *key : {"network_code", "station_code", "channel_code",
                            "channel_seed_id", "channel_fdsn_source_id",
                            "metadata_epoch_start"})
      required_metadata(station.metadata, key);
    required_metadata(station.metadata, "location_code", true);
    required_metadata(station.metadata, "metadata_epoch_end", true);
  }
}

void validate_identities(const std::vector<Event> &events,
                         const std::vector<Event> &stations,
                         const ObservationSet &data,
                         bool simulated = false) {
  validate_geometry(events, stations);
  if (data.shared_synthetic) {
    if (!simulated || data.event_ids.size() != events.size() ||
        data.channel_ids.size() != stations.size())
      throw std::runtime_error("Shared synthetic metadata/geometry mismatch");
    for (size_t i = 0; i < events.size(); ++i)
      if (data.event_ids[i][0] != required_metadata(events[i].metadata, "event_resource_id") ||
          data.event_ids[i][1] != required_metadata(events[i].metadata, "origin_resource_id"))
        throw std::runtime_error("Shared synthetic event identity mismatch");
    for (size_t k = 0; k < stations.size(); ++k) {
      auto expected = simulation_metadata(events, stations, 0, -1, k, 0);
      for (size_t field = 4; field < 12; ++field)
        if (data.channel_ids[k][field - 4] != expected[field].second)
          throw std::runtime_error("Shared synthetic channel/epoch identity mismatch");
    }
    // Every row's values were checked against this dictionary while loading.
    return;
  }
  for (size_t q = 0; q < data.size(); ++q) {
    const auto &d = data[q];
    const auto &metadata = data.native_metadata[q];
    validate_observation_indices(d, events.size(), stations.size());
    validate_receiver_pair(d, metadata, stations);
    if (simulated && required_metadata(metadata, "synthetic_observation") != "1")
      throw std::runtime_error("Geometry-only identity mode requires explicitly synthetic observations");
    const auto &station = stations[d.k].metadata;
    for (const auto *key : {"channel_seed_id", "channel_fdsn_source_id",
                            "metadata_epoch_start", "metadata_epoch_end"}) {
      bool empty = std::string(key) == "metadata_epoch_end";
      if (required_metadata(metadata, key, empty) != required_metadata(station, key, empty))
        throw std::runtime_error(std::string("Observation/channel identity mismatch: ") + key);
    }
    for (const auto &side : {std::make_pair("i", d.i), std::make_pair("j", d.j)}) {
      bool absent = side.second < 0;
      for (const auto *kind : {"event", "origin", "pick", "arrival"}) {
        std::string field = std::string(kind) + "_" + side.first + "_resource_id";
        if (simulated && (std::string(kind) == "pick" || std::string(kind) == "arrival")) {
          const auto *id = metadata_value(metadata, field);
          if (id && !id->empty())
            throw std::runtime_error("Synthetic observations must not claim provider pick/arrival IDs");
          continue;
        }
        const auto &id = required_metadata(metadata, field, absent);
        if (absent) {
          if (!id.empty())
            throw std::runtime_error("Absolute observation has a second event identity");
        } else if (std::string(kind) == "event" || std::string(kind) == "origin") {
          if (id != required_metadata(events[side.second].metadata, std::string(kind) + "_resource_id"))
            throw std::runtime_error("Observation/event identity mismatch: " + field);
        }
      }
    }
  }
}

#include "analytic_truth.hpp"

void simulate(const Config &c, const std::string &dir, const std::string &analytic_bundle = "") {
  if (!authoritative_geometry(c, dir) || authoritative_input(c, dir))
    throw std::runtime_error("simulate requires authoritative_geometry, not authoritative_ids_required");
  for (const auto *name : {"arrivals.csv", "observations.csv", "initial_events.csv",
                            "simulation_ray_status.csv", "simulation_truth_status.csv",
                            "simulation_truth_mode.txt"})
    if (std::filesystem::exists(dir + "/" + name))
      throw std::runtime_error(std::string("Preserve existing simulation output ") + name +
                               "; prepare a fresh run directory");
  auto events = read_events(dir + "/truth_events.csv");
  auto stations = read_events(dir + "/stations.csv");
  validate_geometry(events, stations);
  Grid truth = read_grid(dir + "/truth_grid.csv");
  Grid start = read_grid(dir + "/initial_grid.csv");
  AnalyticTruth analytic;
  if (!analytic_bundle.empty())
    analytic=read_analytic_truth(analytic_bundle,truth,events,stations);
  for (auto &event : events) {
    if (!truth.contains(event.p) || !start.contains(event.p))
      throw std::runtime_error("Catalog simulation source lies outside supplied grids");
    event.t = 0;
    set_metadata(event.metadata, "coordinate_basis", "catalog-defined simulation truth");
    set_metadata(event.metadata, "origin_resource_id_basis",
                 "provider catalog geometry reference, not a simulated pick/origin identifier");
    set_metadata(event.metadata, "simulation_origin_time_basis", "truth t=0; initial/inverted t is a simulated correction in seconds");
  }
  for (const auto &station : stations)
    if (!truth.contains(station.p) || !start.contains(station.p))
      throw std::runtime_error("Simulation receiver lies outside supplied grids");
  std::mt19937 gen(c.get("seed"));
  std::uniform_real_distribution<double> u(0, 1);
  std::normal_distribution<double> normal(0, 1);
  auto initial = events;
  const Vec *axes[] = {&start.x, &start.y, &start.z};
  for (auto &event : initial) {
    for (int axis = 0; axis < 3; axis++)
      event.p[axis] = std::clamp(event.p[axis] + c.get("location_noise") * normal(gen),
                                 axes[axis]->front(), axes[axis]->back());
    event.t = 0.05 * normal(gen);
    set_metadata(event.metadata, "coordinate_basis", "perturbed catalog-defined simulation truth");
  }
  // Calculate all requested synthetic rays from the supplied truth grid.
  // Stations retain their archived geometry/epoch identities, but these are
  // simulated receiver placements, not claims of an observed pick at each pair.
  std::vector<Ray> rr;
  if (analytic_bundle.empty()) {
    rr=rays(truth, events, stations, c, false, nullptr, nullptr, false);
    simulation_ray_gate(dir, events, stations, rr);
  } else {
    write_analytic_truth_status(dir,analytic);
  }
  write_events(events, dir + "/truth_events.csv");
  write_events(initial, dir + "/initial_events.csv");
  synthetic_observations(c, dir, events, stations, rr, gen, u, normal, true,
                         analytic_bundle.empty()?nullptr:&analytic.times);
  auto marker = output(dir + "/authoritative_geometry");
  marker << "Catalog event/origin and channel epoch IDs describe geometry; all arrivals are synthetic.\n";
  std::cout << "Simulated " << events.size() << " catalog-defined truth sources and "
            << stations.size() << " identified receiver placements.\n";
}

using StageWeights = std::array<std::array<double, 3>, 3>;
StageWeights stage_weights(const Config &c, const ObservationSet &data) {
  StageWeights weights{{{{1, 0.1, 0.01}}, {{0.1, 1, 0.01}}, {{0.001, 0.01, 1}}}};
  if (setting(c, "catalog_only_dd", 0) != 0) {
    for (const auto &d : data)
      if (d.type == 2)
        throw std::runtime_error("catalog_only_dd requires no type-2 observations");
    weights = {{{{1, 0.1, 0}}, {{0.1, 1, 0}}, {{0.1, 1, 0}}}};
  }
  const char *types[] = {"absolute", "catalog", "precise"};
  for (int stage = 0; stage < 3; stage++)
    for (int type = 0; type < 3; type++) {
      std::string key = "stage" + std::to_string(stage + 1) + "_" + types[type] + "_weight";
      weights[stage][type] = setting(c, key, weights[stage][type]);
      if (!std::isfinite(weights[stage][type]) || weights[stage][type] < 0)
        throw std::runtime_error("Invalid data weight: " + key);
    }
  return weights;
}
double prediction(const Datum &d, const std::vector<Ray> &r,
                  const std::vector<Event> &e, int ns) {
  double t = e[d.i].t + r[d.i * ns + d.k].time;
  if (d.j >= 0)
    t -= e[d.j].t + r[d.j * ns + second_station(d)].time;
  return t;
}

std::array<double, 3> residual_cutoffs(const ObservationSet &data,
                                      const Vec &residual) {
  Vec bytype[3];
  for (size_t q = 0; q < data.size(); ++q)
    bytype[data[q].type].push_back(std::abs(residual[q]));
  std::array<double, 3> cutoff;
  for (int type = 0; type < 3; ++type) {
    auto &a = bytype[type];
    if (a.empty()) {
      cutoff[type] = 1;
      continue;
    }
    std::nth_element(a.begin(), a.begin() + a.size() / 2, a.end());
    cutoff[type] = std::max(0.01, 6 * 1.4826 * a[a.size() / 2]);
  }
  return cutoff;
}

struct ObservationWeight {
  double stage, prior, robust, distance, event_distance, combined;
  const char *omission;
  bool active() const { return omission[0] == '\0'; }
};
ObservationWeight observation_weight(const Config &c, const std::string &mode,
                                     const StageWeights &weights, int stage,
                                     const Datum &d, double residual, double cutoff,
                                     const std::vector<Event> &events) {
  ObservationWeight w;
  w.stage = mode == "standard" ? 1 : weights[stage][d.type];
  w.prior = d.a_priori_weight;
  double z = residual / cutoff;
  w.robust = std::pow(std::max(0., 1 - z * z), 2);
  w.event_distance = d.j >= 0 ? norm(events[d.i].p - events[d.j].p) : 0;
  w.distance = d.j >= 0 ? std::pow(std::max(0.,
      1 - std::pow(w.event_distance / c.get("pair_distance"), 2)), 2) : 1;
  // Keep the multiplication order of the inversion's original assembly.
  w.combined = w.stage;
  w.combined *= w.prior;
  w.combined *= w.robust;
  if (d.j >= 0) w.combined *= w.distance;
  w.omission = mode == "standard" && d.type != 0 ? "mode_excludes_differential" :
               w.combined < 1e-12 ? "weight_below_1e-12" : "";
  return w;
}

Row observation_row(const Datum &d, const std::vector<Ray> &r, const Grid &g,
                    int ne, int ns, bool locate) {
  Row row;
  const auto &a = r[d.i * ns + d.k];
  const Ray *b = d.j >= 0 ? &r[d.j * ns + second_station(d)] : nullptr;
  for (int k = 0; k < 3; k++)
    row.push_back({4 * d.i + k, a.source[k]});
  row.push_back({4 * d.i + 3, 1});
  if (b) {
    for (int k = 0; k < 3; k++)
      row.push_back({4 * d.j + k, -b->source[k]});
    row.push_back({4 * d.j + 3, -1});
  }
  if (!locate)
    for (int k = 0; k < g.size(); k++) {
      // Parameter q = delta log slowness; dv = -v*q.
      double value = -a.dv[k] * g.v[k];
      if (b) {
        value += b->dv[k] * g.v[k];
        if (std::abs(a.length[k] - b->length[k]) < 0.005)
          value = 0;
      }
      if (std::abs(value) > 1e-14)
        row.push_back({4 * ne + k, value});
    }
  return row;
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
// An invalid forward evaluation must not enter an inverse Jacobian or objective.
// These are the existing local checks, not a global first-arrival certificate.
struct InverseRayRejection : std::runtime_error {
  bool only_local_stopping;
  InverseRayRejection(const std::string &message, bool only_local)
      : std::runtime_error(message), only_local_stopping(only_local) {}
};
void inversion_ray_gate(const std::string &prefix, const Grid &g,
                        const std::vector<Event> &events, const std::vector<Event> &stations,
                        const std::vector<Ray> &rr, const std::vector<int> &used,
                        bool initialization_required, bool derivatives) {
  if (rr.size() != events.size() * stations.size())
    throw std::runtime_error("Incomplete inverse forward ray array");
  std::vector<std::pair<int, std::string>> failed;
  for (int n : used) {
    const auto &ray = rr[n];
    const size_t i = n / stations.size(), k = n % stations.size();
    std::string reasons;
    const auto check = [&](bool valid, const char *reason) {
      if (!valid) { if (!reasons.empty()) reasons += ";"; reasons += reason; }
    };
    check(finite_ray(ray), "nonfinite_or_empty_ray");
    check(ray.converged, "local_stopping_failed");
    check(ray_path_in_domain(g, ray), "path_outside_domain_or_empty");
    check(!ray.path.empty() && ray.path.front() == events[i].p, "source_endpoint_changed");
    check(!ray.path.empty() && ray.path.back() == stations[k].p, "receiver_endpoint_changed");
    if (initialization_required) check(ray.initialization_attempted, "initializer_not_attempted");
    if (initialization_required || ray.initialization_attempted)
      check(ray.initialization_succeeded, "initializer_failed");
    if (derivatives) {
      check(ray.dv.size() == g.v.size(), "velocity_derivative_dimension");
      check(ray.length.size() == g.v.size(), "path_length_dimension");
    }
    if (!reasons.empty()) failed.emplace_back(n, std::move(reasons));
  }
  if (failed.empty()) return;
  require_new_outputs(prefix, {"_ray_status.csv", "_ray_failures.csv", "_ray_paths.csv"});
  auto identified_events = events;
  for (auto &event : identified_events)
    if (!event.metadata.empty())
      set_metadata(event.metadata, "coordinate_basis",
          "independent failed forward evaluation at recorded coordinates; see companion context for evaluation phase");
  write_ray_status(prefix + "_ray_status.csv", identified_events, stations, rr, &used, &g, 17, derivatives);
  auto out = output(prefix + "_ray_failures.csv");
  out << "event,station,reasons,derivatives_requested,velocity_derivatives,path_lengths,expected_velocity_nodes";
  csv_metadata_header(out, identified_events.front().metadata, "source_");
  csv_metadata_header(out, stations.front().metadata, "receiver_");
  out << '\n';
  for (const auto &failure : failed) {
    const size_t i = failure.first / stations.size(), k = failure.first % stations.size();
    const auto &ray = rr[failure.first];
    out << i << ',' << k << ',' << csv_quote(failure.second) << ',' << derivatives
        << ',' << ray.dv.size() << ',' << ray.length.size() << ',' << g.v.size();
    csv_metadata_values(out, identified_events[i].metadata);
    csv_metadata_values(out, stations[k].metadata);
    out << '\n';
  }
  finish_output(out, prefix + "_ray_failures.csv");
  auto paths = output(prefix + "_ray_paths.csv");
  paths << std::setprecision(17) << "event,station,node,x,y,z";
  csv_metadata_header(paths, identified_events.front().metadata, "source_");
  csv_metadata_header(paths, stations.front().metadata, "receiver_");
  paths << '\n';
  for (const auto &failure : failed) {
    const size_t i = failure.first / stations.size(), k = failure.first % stations.size();
    const auto &path = rr[failure.first].path;
    for (size_t node = 0; node < path.size(); ++node) {
      paths << i << ',' << k << ',' << node;
      for (double value : path[node]) paths << ',' << value;
      csv_metadata_values(paths, identified_events[i].metadata);
      csv_metadata_values(paths, stations[k].metadata);
      paths << '\n';
    }
  }
  finish_output(paths, prefix + "_ray_paths.csv");
  const bool only_local = std::all_of(failed.begin(), failed.end(), [](const auto &failure) {
    return failure.second == "local_stopping_failed";
  });
  throw InverseRayRejection("Inverse forward evaluation rejected " + std::to_string(failed.size()) +
      " rays; see " + prefix + "_ray_status.csv; first: " +
      ray_identity_context(events, stations, failed.front().first / stations.size(),
                           failed.front().first % stations.size()), only_local);
}
// Save the exact original solve and fixed weights once per quality-rejected
// iteration. Trial coordinates may have been clamped, so they do not determine
// the unclamped LSQR increment. No Ray from a rejected trial is used here.
void write_trial_solve(const std::string &prefix, const Config &c, const std::string &mode,
                       int iteration, int stage, const Grid &g, const std::vector<Event> &events,
                       const ObservationSet &data, const Vec &delta, const Vec &residual,
                       const Vec &weights, const LSQRInfo &info, double before, bool locate) {
  const size_t off = 4 * events.size(), n = off + (locate ? 0 : g.v.size());
  if (delta.size() != n || residual.size() != data.size() || weights.size() != data.size())
    throw std::runtime_error("Cannot preserve incomplete original solve");
  require_new_outputs(prefix, {"_accepted_events.csv", "_accepted_grid.csv", "_delta.csv", "_weights.csv", "_context.csv"});
  auto accepted = events;
  for (auto &event : accepted)
    if (!event.metadata.empty())
      set_metadata(event.metadata, "coordinate_basis", "independent accepted inversion state at iteration " + std::to_string(iteration) + "; original unscaled solve recorded separately");
  write_events(accepted, prefix + "_accepted_events.csv", 17);
  write_grid(g, prefix + "_accepted_grid.csv", 17);
  auto increments = output(prefix + "_delta.csv");
  increments << std::setprecision(17) << "parameter_index,parameter_type,event,node,component,increment,reference_x,reference_y,reference_z,reference_t,reference_v";
  csv_metadata_header(increments, accepted.front().metadata, "source_");
  increments << '\n';
  for (size_t index = 0; index < n; ++index) {
    increments << index << ',';
    if (index < off) {
      size_t i = index / 4, component = index % 4;
      increments << "source," << i << ",," << "xyzt"[component] << ',' << delta[index];
      for (double value : events[i].p) increments << ',' << value;
      increments << ',' << events[i].t << ',';
      csv_metadata_values(increments, accepted[i].metadata);
    } else {
      size_t node = index - off, ix = node % g.x.size(), iy = (node / g.x.size()) % g.y.size(), iz = node / (g.x.size() * g.y.size());
      increments << "model,," << node << ",log_slowness," << delta[index] << ','
                 << g.x[ix] << ',' << g.y[iy] << ',' << g.z[iz] << ",," << g.v[node];
      for (size_t field = 0; field < accepted.front().metadata.size(); ++field) increments << ',';
    }
    increments << '\n';
  }
  finish_output(increments, prefix + "_delta.csv");
  auto frozen_weights = output(prefix + "_weights.csv");
  frozen_weights << std::setprecision(17) << "observation_index,i,j,station,station_j,type,value,current_residual,fixed_row_multiplier";
  data.write_header(frozen_weights, "original_");
  frozen_weights << '\n';
  for (size_t q = 0; q < data.size(); ++q) {
    const auto &d = data[q];
    frozen_weights << q << ',' << d.i << ',' << d.j << ',' << d.k << ',' << (d.j < 0 ? -1 : second_station(d))
                   << ',' << d.type << ',' << d.value << ',' << residual[q] << ',' << weights[q];
    data.write_metadata(frozen_weights, q);
    frozen_weights << '\n';
  }
  finish_output(frozen_weights, prefix + "_weights.csv");
  auto info_file = output(prefix + "_context.csv");
  info_file << std::setprecision(17)
      << "mode,iteration,stage,columns,source_columns,model_columns,lsqr_iterations,lsqr_relative_normal_residual,lsqr_converged,objective_before,smoothing_weight,damping_parameter,weight_basis,objective_basis\n"
      << mode << ',' << iteration << ',' << stage << ',' << n << ',' << off << ',' << n - off << ','
      << info.iterations << ',' << info.relative_normal_residual << ',' << info.converged << ',' << before << ','
      << c.get("smoothing") << ',' << c.get("damping")
      << ",stage/robust/distance/prior row multipliers computed at the accepted state and fixed through this line search"
      << ",sum of squared fixed-weight data residuals plus final log-slowness smoothing; damping enters the solve only\n";
  finish_output(info_file, prefix + "_context.csv");
}

void invert(const Config &c, std::string dir, std::string mode) {
  auto e = read_events(dir + "/initial_events.csv"),
       stations = read_events(dir + "/stations.csv");
  auto data = observations(dir + "/observations.csv", e, stations,
                           !authoritative_input(c, dir) && authoritative_geometry(c, dir));
  const auto used = observed_rays(data, e.size(), stations);
  const bool authoritative = authoritative_input(c, dir);
  if (authoritative)
    validate_identities(e, stations, data);
  else if (authoritative_geometry(c, dir))
    validate_identities(e, stations, data, true);
  const auto weights = stage_weights(c, data);
  if (!(c.get("stage_length") > 0))
    throw std::runtime_error("stage_length must be positive");
  Grid g = read_grid(dir + "/initial_grid.csv");
  bool locate = mode == "loc1d" || mode == "loc3d";
  if (mode == "loc3d")
    g = read_grid(dir + "/truth_grid.csv");
  int ne = e.size(), ns = stations.size(), off = 4 * ne,
      n = off + (locate ? 0 : g.size());
  ForwardFields fields;
  int current_iteration = -1;
  const auto failure_prefix = [&](const std::string &phase, int trial) {
    return dir + "/" + mode + (phase == "line_search_trial" ?
        "_rejected_trial_it_" + std::to_string(current_iteration) + "_ls_" + std::to_string(trial) :
        "_failed_forward");
  };
  const auto checked_rays = [&](const Grid &model, const std::vector<Event> &sources,
                                bool derivatives, const std::string &phase, int trial) {
    const std::string prefix = failure_prefix(phase, trial);
    if (phase == "line_search_trial")
      require_new_outputs(prefix, {"_ray_status.csv", "_ray_failures.csv", "_ray_paths.csv",
          "_events.csv", "_grid.csv", "_context.csv", "_accepted_events.csv", "_accepted_grid.csv"});
    try {
      auto result = rays(model, sources, stations, c, derivatives, &used, &fields, false);
      inversion_ray_gate(prefix, model, sources, stations, result, used,
                         auxiliary_spacing(c) > 0, derivatives);
      return result;
    } catch (const std::exception &error) {
      // A failed trial is distinct from the last accepted state. In particular,
      // do not write a candidate to the conventional final inversion filenames.
      auto identified_sources = sources, accepted_sources = e;
      if (authoritative || authoritative_geometry(c, dir)) {
        for (auto &event : identified_sources)
          set_metadata(event.metadata, "coordinate_basis", "independent failed " + phase + " forward evaluation; not a final inversion result");
        for (auto &event : accepted_sources)
          set_metadata(event.metadata, "coordinate_basis", "independent last accepted inversion state, or starting state before the first accepted update");
      }
      write_events(identified_sources, prefix + "_events.csv", 17);
      write_grid(model, prefix + "_grid.csv", 17);
      write_events(accepted_sources, dir + "/" + mode + "_last_accepted_events.csv", 17);
      write_grid(g, dir + "/" + mode + "_last_accepted_grid.csv", 17);
      if (phase == "line_search_trial") {
        write_events(accepted_sources, prefix + "_accepted_events.csv", 17);
        write_grid(g, prefix + "_accepted_grid.csv", 17);
      }
      auto context = output(prefix + "_context.csv");
      context << "mode,iteration,phase,line_search_trial,derivatives_requested,initialization_required,significant_digits,message\n"
              << mode << ',' << current_iteration << ',' << phase << ',' << trial << ',' << derivatives
              << ',' << (auxiliary_spacing(c) > 0) << ",17," << csv_quote(error.what()) << '\n';
      finish_output(context, prefix + "_context.csv");
      throw;
    }
  };
  auto log = output(dir + "/" + mode + "_history.csv");
  log << "iteration,stage,absolute_rms,catalog_rms,precise_rms,velocity_step,"
         "location_step,step_fraction,objective_before,objective_after,lsqr_"
         "iterations,lsqr_relative_normal_residual,lsqr_converged,ray_count,"
         "ray_converged_count,ray_projected_gradient_max,ray_raw_gradient_max,"
         "ray_initialization_attempted_count,ray_initialization_succeeded_count,"
         "ray_selected_fmm_count\n";
  auto preflight = output(dir + "/" + mode + "_matrix_preflight.csv");
  preflight << "iteration,observation_rows,active_data_rows,smoothing_rows,columns,"
               "damped_rows,damped_entries,csr_payload_bytes,numeric_observation_bytes,"
               "residual_weight_bytes,lsqr_row_workspace_bound_bytes\n";
  for (int it = 0; it < int(c.get("iterations")); it++) {
    current_iteration = it;
    const bool preflight_only = setting(c, "matrix_preflight_only", 0) != 0;
    auto r = preflight_only ? rays(g, e, stations, c, true, &used, &fields, false) :
                             checked_rays(g, e, true, "current_model", -1);
    if (preflight_only) {
      write_ray_status(dir + "/" + mode + "_preflight_ray_status.csv", e, stations, r, &used, &g);
      for (int index : used)
        if (!finite_ray(r[index]) ||
            !ray_path_in_domain(g, r[index]) ||
            r[index].path.front() != e[index / ns].p ||
            r[index].path.back() != stations[index % ns].p ||
            (r[index].initialization_attempted && !r[index].initialization_succeeded) ||
            r[index].dv.size() != g.v.size() || r[index].length.size() != g.v.size())
          throw std::runtime_error("Preflight ray evaluation failed; see identified status table; " +
                                   ray_identity_context(e, stations, index / ns, index % ns));
    }
    size_t ray_converged = 0, attempted = 0, succeeded = 0, selected_fmm = 0;
    double ray_projected_max = 0, ray_raw_max = 0;
    for (int index : used) {
      ray_converged += r[index].converged;
      attempted += r[index].initialization_attempted;
      succeeded += r[index].initialization_succeeded;
      selected_fmm += r[index].selected_fmm_seed;
      ray_projected_max = std::max(ray_projected_max, r[index].gradient);
      ray_raw_max = std::max(ray_raw_max, r[index].raw_gradient);
    }
    int stage = std::min(2, int(it / c.get("stage_length")));
    Matrix A(n);
    Vec residual(data.size()), w(data.size());
    double ss[3] = {}, count[3] = {};
    // Residual scale is estimated separately for each data type; a 0.01 s floor
    // avoids eliminating the rounded, nearly exact synthetic differential
    // times.
    for (size_t q = 0; q < data.size(); q++) {
      residual[q] = data[q].value - prediction(data[q], r, e, ns);
    }
    const auto cutoff = residual_cutoffs(data, residual);
    size_t active_rows = 0, entries = 0;
    for (size_t q = 0; q < data.size(); q++) {
      const auto &d = data[q];
      double res = residual[q];
      ss[d.type] += res * res;
      count[d.type]++;
      if (mode == "standard" && d.type != 0)
        continue;
      const auto weight = observation_weight(c, mode, weights, stage, d, res,
                                             cutoff[d.type], e);
      if (!weight.active())
        continue;
      w[q] = weight.combined;
      size_t row_entries = observation_row(d, r, g, ne, ns, locate).size();
      if (row_entries > std::numeric_limits<size_t>::max() - entries)
        throw std::runtime_error("Observation matrix entry count overflow");
      entries += row_entries;
      ++active_rows;
    }
    Matrix smoothing(n);
    if (!locate)
      smooth(smoothing, g, off, c.get("smoothing"));
    const size_t extra_rows = smoothing.rhs.size() + size_t(n),
                 extra_entries = smoothing.values.size() + size_t(n);
    if (active_rows > std::numeric_limits<size_t>::max() - extra_rows ||
        entries > std::numeric_limits<size_t>::max() - extra_entries)
      throw std::runtime_error("Augmented matrix dimensions overflow");
    const size_t total_rows = active_rows + extra_rows,
                 total_entries = entries + extra_entries,
                 bytes = Matrix::storage_bytes(total_rows, total_entries);
    preflight << it << ',' << data.size() << ',' << active_rows << ','
              << smoothing.rhs.size() << ',' << n << ',' << total_rows << ','
              << total_entries << ',' << bytes << ',' << data.size() * sizeof(Datum)
              << ',' << 2.L * data.size() * sizeof(double) << ','
              << 3.L * total_rows * sizeof(double) << '\n';
    preflight.flush();
    if (!preflight) throw std::runtime_error("Cannot finish matrix preflight record");
    std::cout << "Matrix preflight: " << total_rows << " rows, " << total_entries
              << " ordered entries, " << bytes << " CSR payload bytes" << std::endl;
    if (preflight_only)
      return; // Report actual current rows; do not allocate or solve the matrix.
    A.reserve(total_rows, total_entries);
    for (size_t q = 0; q < data.size(); ++q)
      if (w[q] != 0)
        A.add(observation_row(data[q], r, g, ne, ns, locate), residual[q], w[q]);
    if (!locate)
      smooth(A, g, off, c.get("smoothing"));
    if (A.rhs.size() + size_t(n) != total_rows ||
        A.values.size() + size_t(n) != total_entries)
      throw std::runtime_error("Matrix assembly differs from preflight count");
    LSQRInfo linear_info;
    Vec delta = solve(std::move(A), c.get("damping"), &linear_info);
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
    int quality_rejections = 0, objective_evaluations = 0;
    const std::string solve_prefix = dir + "/" + mode + "_iteration_" + std::to_string(it) + "_solve";
    const std::string trials_path = dir + "/" + mode + "_iteration_" + std::to_string(it) + "_trials.csv";
    require_new_outputs(trials_path, {""});
    auto trials = output(trials_path);
    trials << std::setprecision(17) << "iteration,stage,trial,step_fraction,status,objective_evaluated,objective_before,objective_after,failure_prefix\n";
    const auto record_trial = [&](int trial, const char *status, bool evaluated, const std::string &prefix = "") {
      trials << it << ',' << stage << ',' << trial << ',' << step << ',' << status << ',' << evaluated << ',' << before << ',';
      if (evaluated) trials << after;
      trials << ',' << csv_quote(prefix) << '\n';
      trials.flush();
      if (!trials) throw std::runtime_error("Cannot finish trial record " + trials_path);
    };
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
      if (!valid) {
        record_trial(ls, "invalid_trial_model", false);
        continue;
      }
      std::vector<Ray> nr;
      try {
        nr = checked_rays(ng, ee, false, "line_search_trial", ls);
      } catch (const InverseRayRejection &failure) {
        if (!failure.only_local_stopping) throw;
        if (quality_rejections == 0)
          write_trial_solve(solve_prefix, c, mode, it, stage, g, e, data, delta,
                            residual, w, linear_info, before, locate);
        ++quality_rejections;
        record_trial(ls, "local_stopping_rejected", false, failure_prefix("line_search_trial", ls));
        continue; // Never evaluate or accept an unsupported forward objective.
      }
      ++objective_evaluations;
      after = objective(ng, ee, nr);
      record_trial(ls, after <= before ? "accepted" : "objective_rejected", true);
      if (after <= before) {
        accepted = true;
        break;
      }
    }
    finish_output(trials, trials_path);
    if (quality_rejections > 0 && objective_evaluations == 0)
      throw std::runtime_error("No objective-evaluable trial after local ray rejection; see " + trials_path);
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
        << ',' << linear_info.converged << ',' << used.size() << ','
        << ray_converged << ',' << ray_projected_max << ',' << ray_raw_max << ','
        << attempted << ',' << succeeded << ',' << selected_fmm << '\n';
    log.flush();
    if (!log) throw std::runtime_error("Cannot finish inverse history record");
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
  auto rr = checked_rays(g, e, true, "final_model", -1);
  write_grid(g, dir + "/" + mode + "_grid.csv");
  if (authoritative || authoritative_geometry(c, dir))
    for (auto &event : e)
      set_metadata(event.metadata, "coordinate_basis",
                   "independent " + mode + " inversion estimate; provider IDs identify reference catalog records");
  write_events(e, dir + "/" + mode + "_events.csv");
  auto coverage = output(dir + "/" + mode + "_coverage.csv");
  coverage << "node,path_length\n";
  for (int k = 0; k < g.size(); k++) {
    double length = 0;
    for (int index : used)
      length += rr[index].length[k];
    coverage << k << ',' << length << '\n';
  }
  auto f = output(dir + "/" + mode + "_residuals.csv");
  f << "i,j,station,type,residual";
  data.write_header(f);
  initializer_header(f, "i_");
  initializer_header(f, "j_");
  f << '\n';
  for (size_t q = 0; q < data.size(); ++q) {
    const auto &d = data[q];
    f << d.i << ',' << d.j << ',' << d.k << ',' << d.type << ','
      << d.value - prediction(d, rr, e, ns);
    data.write_metadata(f, q);
    initializer_values(f, rr[d.i * ns + d.k]);
    if (d.j >= 0)
      initializer_values(f, rr[d.j * ns + second_station(d)]);
    else
      for (int k = 0; k < 8; ++k) f << ',';
    f << '\n';
  }
  // Real data have no synthetic sandwich truth; plot their saved grid separately.
  if (authoritative)
    return;
  // Model-generated horizontal sections, including signed recovered-minus-true
  // errors.
  auto sl = output(dir + "/" + mode + "_slices.csv");
  sl << "x,y,z,v,error\n";
  const bool supplied_geometry = authoritative_geometry(c, dir);
  Grid truth;
  if (supplied_geometry)
    truth = read_grid(dir + "/truth_grid.csv");
  Vec depths = supplied_geometry ? g.z : Vec{0., 3., 7., 11., 16.};
  for (double z : depths)
    for (double y = supplied_geometry ? g.y.front() : -60; y <= (supplied_geometry ? g.y.back() : 40); y += 2)
      for (double x = supplied_geometry ? g.x.front() : -35; x <= (supplied_geometry ? g.x.back() : 35); x += 0.5) {
        if (supplied_geometry && !truth.contains({x, y, z}))
          throw std::runtime_error("Synthetic error slice lies outside supplied truth grid");
        double v = g.sample({x, y, z}).v;
        sl << x << ',' << y << ',' << z << ',' << v << ','
           << v - (supplied_geometry ? truth.sample({x, y, z}).v : true_velocity(c, x)) << '\n';
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
size_t checked_raycheck_receiver_batch(double requested_batch) {
  if (!std::isfinite(requested_batch) || requested_batch < 0 ||
      std::floor(requested_batch) != requested_batch ||
      requested_batch > std::numeric_limits<int>::max())
    throw std::runtime_error("raycheck_receiver_batch must be an integer in [0, INT_MAX]");
  return static_cast<size_t>(requested_batch);
}
// Config's legacy numeric extraction ignores malformed tokens. Validate this
// new optional setting explicitly, including every occurrence before a later
// duplicate can hide an invalid value. Other configuration parsing is unchanged.
void read_raycheck_receiver_batch(Config &c, const std::string &path) {
  std::ifstream file(path);
  std::string line;
  while (std::getline(file, line)) {
    line = line.substr(0, line.find('#'));
    std::istringstream fields(line);
    std::string name, token, extra;
    if (!(fields >> name) || name != "raycheck_receiver_batch")
      continue;
    if (!(fields >> token) || fields >> extra)
      throw std::runtime_error("raycheck_receiver_batch requires one numeric value");
    size_t consumed = 0;
    double value;
    try { value = std::stod(token, &consumed); }
    catch (const std::exception &) {
      throw std::runtime_error("Invalid raycheck_receiver_batch numeric token");
    }
    if (consumed != token.size())
      throw std::runtime_error("Invalid raycheck_receiver_batch numeric token");
    checked_raycheck_receiver_batch(value);
    c.v[name] = value;
  }
}
void raycheck(const Config &c, std::string dir, std::string mode = "truth",
              bool geometry_only = false) {
  const size_t receiver_batch = checked_raycheck_receiver_batch(
      setting(c, "raycheck_receiver_batch", 0));
  auto e = read_events(dir + "/" + mode + "_events.csv");
  auto stations = read_events(dir + "/stations.csv");
  ObservationSet data;
  std::vector<int> used;
  const bool authoritative = authoritative_input(c, dir);
  if (geometry_only) {
    validate_geometry(e, stations);
    if (e.size() * stations.size() > size_t(std::numeric_limits<int>::max()))
      throw std::runtime_error("Too many geometry ray indices");
    used.resize(e.size() * stations.size());
    std::iota(used.begin(), used.end(), 0);
  } else {
    data = observations(dir + "/observations.csv", e, stations,
                        !authoritative && authoritative_geometry(c, dir));
    used = observed_rays(data, e.size(), stations);
    if (authoritative)
      validate_identities(e, stations, data);
    else if (authoritative_geometry(c, dir))
      validate_identities(e, stations, data, true);
  }
  std::vector<int> samples;
  const int ns = stations.size();
  const std::string sample_path = dir + "/ray_samples.csv";
  if (std::filesystem::exists(sample_path)) {
    auto table = csv_table(sample_path, {"event", "station"});
    for (const auto &row : table.rows) {
      int i = csv_int(row[0]), k = csv_int(row[1]);
      if (i < 0 || i >= int(e.size()) || k < 0 || k >= ns ||
          !std::binary_search(used.begin(), used.end(), i * ns + k))
        throw std::runtime_error("Ray sample must identify an available event/channel pair");
      if (std::find(samples.begin(), samples.end(), i * ns + k) != samples.end())
        throw std::runtime_error("Duplicate ray sample");
      samples.push_back(i * ns + k);
    }
    if (samples.empty())
      throw std::runtime_error("Empty ray_samples.csv");
  } else if (!authoritative && used.size() == e.size() * stations.size()) {
    // Preserve the original synthetic diagnostic sample.
    for (int n = 0; n < 32; n++)
      samples.push_back(((37 * n + 3) % e.size()) * ns + (13 * n + 7) % ns);
  } else {
    // Deterministic samples of the actual sparse observation support.
    size_t count = std::min(size_t(32), used.size());
    for (size_t n = 0; n < count; n++)
      samples.push_back(used[count == 1 ? 0 : n * (used.size() - 1) / (count - 1)]);
  }
  Grid g = read_grid(dir + "/" + mode + "_grid.csv");
  Config refined = c;
  refined.v["ray_spacing"] = c.get("ray_spacing") / 2;
  refined.v["ray_iterations"] = std::max(1000., c.get("ray_iterations"));
  const double aux = auxiliary_spacing(c);
  if (aux > 0) refined.v["fmm_spacing"] = aux / 2;
  ForwardFields production_fields, refined_fields;
  if (aux > 0) {
    prepare_receiver_fields(g, e, stations, aux, production_fields, samples);
    if (!receiver_batch)
      prepare_receiver_fields(g, e, stations, aux / 2, refined_fields, samples);
  }
  std::string prefix = geometry_only ? "geometry_" + mode + "_ray" :
                                      (mode == "truth" ? "ray" : mode + "_ray");
  auto f = output(dir + "/" + prefix + "_convergence.csv");
  f << "event,station,production_time,refined_time,difference,production_"
       "gradient,refined_gradient,production_raw_gradient,refined_raw_gradient,"
       "production_iterations,refined_iterations,production_converged,refined_"
       "converged,production_merged,refined_merged,diagnostic_row,"
       "production_path_spacing,refined_path_spacing,production_requested_fmm_spacing,"
       "refined_requested_fmm_spacing";
  initializer_header(f, "production_");
  initializer_header(f, "refined_");
  f << '\n';
  auto df = output(dir + "/" + prefix + "_derivatives.csv");
  df << "event,station,axis,production_derivative,refined_derivative,finite_"
        "difference,production_error,refined_error,diagnostic_row,"
        "plus_converged,minus_converged";
  initializer_header(df, "plus_");
  initializer_header(df, "minus_");
  df << '\n';
  // Both diagnostic tables refer to this zero-based sample key. Each mapping
  // row identifies an original observations.csv row and its i/j event side.
  auto identifiers = output(dir + "/" + prefix + "_identifiers.csv");
  identifiers << "diagnostic_row,event,station";
  if (geometry_only)
    identifiers << ",source_x,source_y,source_z,receiver_x,receiver_y,receiver_z";
  else {
    identifiers << ",observation_row,observation_event_side";
    data.write_header(identifiers, "observation_");
  }
  csv_metadata_header(identifiers, e.front().metadata, "source_");
  csv_metadata_header(identifiers, stations.front().metadata, "receiver_");
  identifiers << '\n';
  size_t batch_end = 0;
  for (size_t n = 0; n < samples.size(); n++) {
    if (aux > 0 && receiver_batch && n == batch_end) {
      // Partition contiguous sample rows by exact physical receiver coordinates.
      // Native indices and output order remain unchanged. Completed Ray values
      // own their data; no field reference survives the preceding loop body.
      std::map<P, bool> receivers;
      std::vector<int> batch;
      while (batch_end < samples.size()) {
        const P receiver = stations[samples[batch_end] % ns].p;
        if (!receivers.count(receiver) && receivers.size() == receiver_batch)
          break;
        receivers.emplace(receiver, true);
        batch.push_back(samples[batch_end++]);
      }
      refined_fields.fields.clear();
      prepare_receiver_fields(g, e, stations, aux / 2, refined_fields, batch);
    }
    int i = samples[n] / ns, k = samples[n] % ns;
    if (geometry_only) {
      identifiers << n << ',' << i << ',' << k;
      for (double value : e[i].p) identifiers << ',' << value;
      for (double value : stations[k].p) identifiers << ',' << value;
      csv_metadata_values(identifiers, e[i].metadata);
      csv_metadata_values(identifiers, stations[k].metadata);
      identifiers << '\n';
    }
    for (size_t q = 0; q < data.size(); q++)
      if ((data[q].i == i && data[q].k == k) ||
          (data[q].j == i && second_station(data[q]) == k)) {
        identifiers << n << ',' << i << ',' << k << ',' << q << ','
                    << (data[q].i == i ? "i" : "j");
        data.write_metadata(identifiers, q);
        csv_metadata_values(identifiers, e[i].metadata);
        csv_metadata_values(identifiers, stations[k].metadata);
        identifiers << '\n';
      }
    Ray a = configured_trace(g, e[i].p, stations[k].p, c, production_fields);
    Ray b = configured_trace(g, e[i].p, stations[k].p, refined, refined_fields);
    f << i << ',' << k << ',' << a.time << ',' << b.time << ','
      << a.time - b.time << ',' << a.gradient << ',' << b.gradient << ','
      << a.raw_gradient << ',' << b.raw_gradient << ',' << a.iterations << ','
      << b.iterations << ',' << a.converged << ',' << b.converged << ','
      << a.merged_nodes << ',' << b.merged_nodes << ',' << n << ','
      << c.get("ray_spacing") << ',' << refined.get("ray_spacing") << ','
      << aux << ',' << auxiliary_spacing(refined);
    initializer_values(f, a);
    initializer_values(f, b);
    f << '\n';
    if (n < 8)
      for (int axis = 0; axis < 3; axis++) {
        double h = 0.01;
        P ap = e[i].p, am = e[i].p;
        ap[axis] += h;
        am[axis] -= h;
        if (!g.contains(ap) || !g.contains(am))
          continue;
        Ray plus = configured_trace(g, ap, stations[k].p, refined, refined_fields, false);
        Ray minus = configured_trace(g, am, stations[k].p, refined, refined_fields, false);
        double fd = (plus.time - minus.time) / (2 * h);
        df << i << ',' << k << ',' << axis << ',' << a.source[axis] << ','
           << b.source[axis] << ',' << fd << ',' << a.source[axis] - fd << ','
           << b.source[axis] - fd << ',' << n << ',' << plus.converged << ','
           << minus.converged;
        initializer_values(df, plus);
        initializer_values(df, minus);
        df << '\n';
      }
  }
}

// Frozen, unweighted absolute-data Jacobian at the saved event/model estimate.
// Noise, prior, robust, and smoothing weights are deliberately not folded into G.
void linearize(const Config &c, const std::string &dir, const std::string &mode) {
  auto events = read_events(dir + "/" + mode + "_events.csv");
  auto stations = read_events(dir + "/stations.csv");
  auto data = observations(dir + "/observations.csv", events, stations,
                           !authoritative_input(c, dir) && authoritative_geometry(c, dir));
  observed_rays(data, events.size(), stations);
  if (authoritative_input(c, dir))
    validate_identities(events, stations, data);
  else if (authoritative_geometry(c, dir))
    validate_identities(events, stations, data, true);
  Grid g = read_grid(dir + "/" + mode + "_grid.csv");
  const int ns = stations.size(), off = 4 * events.size();
  std::vector<int> used;
  for (const auto &d : data)
    if (d.type == 0)
      used.push_back(d.i * ns + d.k);
  std::sort(used.begin(), used.end());
  used.erase(std::unique(used.begin(), used.end()), used.end());
  if (used.empty())
    throw std::runtime_error("Absolute-data linearization requires absolute observations");
  auto traced = rays(g, events, stations, c, true, &used);
  auto matrix = output(dir + "/" + mode + "_linearization_matrix.csv");
  matrix << "row,column,value\n";
  auto rows = output(dir + "/" + mode + "_linearization_rows.csv");
  rows << "row,observation_row,i,station,observed,predicted,residual,"
          "ray_converged,ray_projected_gradient,ray_iterations,ray_time,ray_raw_gradient";
  initializer_header(rows, "ray_");
  data.write_header(rows);
  const bool prior_column = std::find(data.metadata_header.begin(), data.metadata_header.end(),
                                      "a_priori_weight") != data.metadata_header.end();
  if (!prior_column)
    rows << ",a_priori_weight";
  rows << '\n';
  size_t row = 0;
  for (size_t q = 0; q < data.size(); q++) {
    const auto &d = data[q];
    if (d.type != 0)
      continue;
    const auto &ray = traced[d.i * ns + d.k];
    for (int axis = 0; axis < 3; axis++)
      if (ray.source[axis] != 0)
        matrix << row << ',' << 4 * d.i + axis << ',' << ray.source[axis] << '\n';
    matrix << row << ',' << 4 * d.i + 3 << ",1\n";
    for (int node = 0; node < g.size(); node++) {
      double value = -g.v[node] * ray.dv[node];
      if (value != 0)
        matrix << row << ',' << off + node << ',' << value << '\n';
    }
    double predicted = prediction(d, traced, events, ns);
    rows << row << ',' << q << ',' << d.i << ',' << d.k << ',' << d.value << ','
         << predicted << ',' << d.value - predicted << ',' << ray.converged << ','
         << ray.gradient << ',' << ray.iterations << ',' << ray.time << ',' << ray.raw_gradient;
    initializer_values(rows, ray);
    data.write_metadata(rows, q);
    if (!prior_column)
      rows << ',' << d.a_priori_weight;
    rows << '\n';
    row++;
  }
  auto columns = output(dir + "/" + mode + "_linearization_columns.csv");
  columns << "column,parameter,event,node,x,y,z,reference_value,parameter_unit";
  csv_metadata_header(columns, events.front().metadata, "source_");
  columns << '\n';
  const char *parameters[] = {"x", "y", "z", "t"};
  for (size_t event = 0; event < events.size(); event++)
    for (int axis = 0; axis < 4; axis++) {
      const auto &e = events[event];
      columns << 4 * event + axis << ',' << parameters[axis] << ',' << event
              << ",-1," << e.p[0] << ',' << e.p[1] << ',' << e.p[2] << ','
              << (axis == 3 ? e.t : e.p[axis]) << ',' << (axis == 3 ? "s" : "km");
      csv_metadata_values(columns, e.metadata);
      columns << '\n';
    }
  for (int k = 0; k < int(g.z.size()); k++)
    for (int j = 0; j < int(g.y.size()); j++)
      for (int i = 0; i < int(g.x.size()); i++) {
        int node = g.id(i, j, k);
        columns << off + node << ",q,-1," << node << ',' << g.x[i] << ',' << g.y[j]
                << ',' << g.z[k] << ",0,dimensionless";
        for (size_t field = 0; field < events.front().metadata.size(); field++)
          columns << ',';
        columns << '\n';
      }
  std::cout << "Exported " << row << " absolute rows, " << off + g.size()
            << " columns, " << used.size() << " observed rays at " << mode << '\n';
}

#include "full_linearization.hpp"

int main(int argc, char **argv) {
  try {
    if (argc >= 3 && std::string(argv[1]) == "validate") {
      validate(argv[2]);
      return 0;
    }
    if (argc < 4)
      throw std::runtime_error("Usage: dd validate OUT | dd generate CONFIG "
                               "OUT | dd simulate CONFIG OUT [--analytic-truth BUNDLE] | dd invert CONFIG OUT MODE | "
                               "dd raycheck CONFIG OUT [MODE] | dd geometrycheck CONFIG OUT [MODE] | "
                               "dd linearize CONFIG OUT MODE | "
                               "dd linearize_full CONFIG OUT MODE [STAGE]");
    Config c(argv[2]);
    std::string cmd = argv[1];
    if (cmd == "raycheck" || cmd == "geometrycheck")
      read_raycheck_receiver_batch(c, argv[2]);
    if (cmd == "generate")
      generate(c, argv[3]);
    else if (cmd == "simulate" && (argc==4 || (argc==6 && std::string(argv[4])=="--analytic-truth")))
      simulate(c, argv[3],argc==6?argv[5]:"");
    else if (cmd == "raycheck")
      raycheck(c, argv[3], argc == 5 ? argv[4] : "truth");
    else if (cmd == "geometrycheck")
      raycheck(c, argv[3], argc == 5 ? argv[4] : "truth", true);
    else if (cmd == "invert" && argc == 5)
      invert(c, argv[3], argv[4]);
    else if (cmd == "linearize" && argc == 5)
      linearize(c, argv[3], argv[4]);
    else if (cmd == "linearize_full" && (argc == 5 || argc == 6))
      linearize_full(c, argv[3], argv[4], argc == 6 ? csv_int(argv[5]) : -1);
    else
      throw std::runtime_error("Unknown command");
  } catch (const std::exception &e) {
    std::cerr << e.what() << '\n';
    return 1;
  }
  return 0;
}
