#include "core.hpp"
#include "ray_checks.hpp"
#include "csv.hpp"
#include <filesystem>
struct Event {
  P p;
  double t = 0;
  Metadata metadata{};
};
struct Datum {
  int i, j, k, type;
  double value;
  Metadata metadata{};
  double a_priori_weight = 1;
  int station_j = -1; // Absent in legacy files: both events use station k.
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
std::vector<Ray> rays(const Grid &g, const std::vector<Event> &e,
                      const std::vector<Event> &s, const Config &c,
                      bool deriv = true, const std::vector<int> *used = nullptr) {
  std::vector<Ray> r(e.size() * s.size());
  const int count = used ? int(used->size()) : int(r.size());
#pragma omp parallel for schedule(dynamic)
  for (int q = 0; q < count; q++) {
    int n = used ? (*used)[q] : q;
    r[n] = trace(g, e[n / s.size()].p, s[n % s.size()].p, c.get("ray_spacing"),
                 c.get("ray_iterations"), deriv);
  }
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

// Shared noise generation preserves the original generator's random-number order.
void synthetic_observations(const Config &c, const std::string &dir,
                            const std::vector<Event> &events,
                            const std::vector<Event> &stations,
                            const std::vector<Ray> &rr, std::mt19937 &gen,
                            std::uniform_real_distribution<double> &u,
                            std::normal_distribution<double> &normal,
                            bool identified_geometry = false) {
  const int ne = events.size(), ns = stations.size();
  Vec true_t(rr.size()), abs_t(rr.size()), rounded(rr.size()), bias(ns);
  for (auto &v : bias)
    v = (2 * u(gen) - 1) * c.get("station_noise");
  auto raw = output(dir + "/arrivals.csv");
  raw << "event,station,true_time,rounded_time,station_bias,pick_noise,absolute_time";
  if (identified_geometry)
    csv_metadata_header(raw, simulation_metadata(events, stations, 0, -1, 0, 0));
  raw << '\n';
  for (int i = 0; i < ne; i++)
    for (int k = 0; k < ns; k++) {
      int n = i * ns + k;
      true_t[n] = rr[n].time;
      double quantum = setting(c, "time_quantum", 0.01);
      rounded[n] = quantum > 0 ? std::round(true_t[n] / quantum) * quantum : true_t[n];
      double noise = c.get("noise") * normal(gen);
      abs_t[n] = rounded[n] + bias[k] + noise;
      raw << i << ',' << k << ',' << true_t[n] << ',' << rounded[n] << ','
          << bias[k] << ',' << noise << ',' << abs_t[n];
      if (identified_geometry)
        csv_metadata_values(raw, simulation_metadata(events, stations, i, -1, k, 0));
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
std::vector<Datum> observations(std::string path) {
  std::vector<Datum> d;
  auto table = csv_table(path, {"i", "j", "station", "type", "value"});
  for (const auto &row : table.rows) {
    Datum datum{csv_int(row[0]), csv_int(row[1]), csv_int(row[2]),
                csv_int(row[3]), csv_double(row[4]), csv_metadata(table, row, 5)};
    if (const auto *station = metadata_value(datum.metadata, "station_j")) {
      if (!station->empty())
        datum.station_j = csv_int(*station);
      if (datum.j >= 0 && (station->empty() || datum.station_j < 0))
        throw std::runtime_error("Differential observation requires a nonnegative station_j when that column is present");
      if (datum.j < 0 && datum.station_j != -1)
        throw std::runtime_error("Absolute observation station_j must be empty or -1");
    }
    if (const auto *weight = metadata_value(datum.metadata, "a_priori_weight")) {
      datum.a_priori_weight = csv_double(*weight);
      if (datum.a_priori_weight < 0)
        throw std::runtime_error("Negative a_priori_weight");
    }
    d.push_back(std::move(datum));
  }
  if (d.empty())
    throw std::runtime_error("No observations in " + path);
  return d;
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
void validate_receiver_pair(const Datum &d, const std::vector<Event> &stations) {
  const auto *j_start = metadata_value(d.metadata, "metadata_epoch_j_start");
  const auto *j_end = metadata_value(d.metadata, "metadata_epoch_j_end");
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
    if (required_metadata(d.metadata, key, empty) != required_metadata(a.metadata, key, empty))
      throw std::runtime_error(std::string("Observation/channel identity mismatch: ") + key);
  }
  for (const auto *edge : {"start", "end"}) {
    std::string field = std::string("metadata_epoch_j_") + edge;
    if (required_metadata(d.metadata, field, std::string(edge) == "end") !=
        required_metadata(b.metadata, std::string("metadata_epoch_") + edge, std::string(edge) == "end"))
      throw std::runtime_error("Observation/second receiver epoch mismatch: " + field);
  }
}

std::vector<int> observed_rays(const std::vector<Datum> &data, int ne,
                              const std::vector<Event> &stations) {
  int ns = stations.size();
  if (ne <= 0 || ns <= 0 || size_t(ne) * size_t(ns) > size_t(std::numeric_limits<int>::max()))
    throw std::runtime_error("Invalid event/station dimensions");
  std::vector<int> used;
  for (const auto &d : data) {
    validate_observation_indices(d, ne, ns);
    validate_receiver_pair(d, stations);
    used.push_back(d.i * ns + d.k);
    if (d.j >= 0)
      used.push_back(d.j * ns + second_station(d));
  }
  std::sort(used.begin(), used.end());
  used.erase(std::unique(used.begin(), used.end()), used.end());
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
                         const std::vector<Datum> &data,
                         bool simulated = false) {
  validate_geometry(events, stations);
  for (const auto &d : data) {
    validate_observation_indices(d, events.size(), stations.size());
    validate_receiver_pair(d, stations);
    if (simulated && required_metadata(d.metadata, "synthetic_observation") != "1")
      throw std::runtime_error("Geometry-only identity mode requires explicitly synthetic observations");
    const auto &station = stations[d.k].metadata;
    for (const auto *key : {"channel_seed_id", "channel_fdsn_source_id",
                            "metadata_epoch_start", "metadata_epoch_end"}) {
      bool empty = std::string(key) == "metadata_epoch_end";
      if (required_metadata(d.metadata, key, empty) != required_metadata(station, key, empty))
        throw std::runtime_error(std::string("Observation/channel identity mismatch: ") + key);
    }
    for (const auto &side : {std::make_pair("i", d.i), std::make_pair("j", d.j)}) {
      bool absent = side.second < 0;
      for (const auto *kind : {"event", "origin", "pick", "arrival"}) {
        std::string field = std::string(kind) + "_" + side.first + "_resource_id";
        if (simulated && (std::string(kind) == "pick" || std::string(kind) == "arrival")) {
          const auto *id = metadata_value(d.metadata, field);
          if (id && !id->empty())
            throw std::runtime_error("Synthetic observations must not claim provider pick/arrival IDs");
          continue;
        }
        const auto &id = required_metadata(d.metadata, field, absent);
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

void simulate(const Config &c, const std::string &dir) {
  if (!authoritative_geometry(c, dir) || authoritative_input(c, dir))
    throw std::runtime_error("simulate requires authoritative_geometry, not authoritative_ids_required");
  auto events = read_events(dir + "/truth_events.csv");
  auto stations = read_events(dir + "/stations.csv");
  validate_geometry(events, stations);
  Grid truth = read_grid(dir + "/truth_grid.csv");
  Grid start = read_grid(dir + "/initial_grid.csv");
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
  auto rr = rays(truth, events, stations, c, false);
  write_events(events, dir + "/truth_events.csv");
  write_events(initial, dir + "/initial_events.csv");
  synthetic_observations(c, dir, events, stations, rr, gen, u, normal, true);
  auto marker = output(dir + "/authoritative_geometry");
  marker << "Catalog event/origin and channel epoch IDs describe geometry; all arrivals are synthetic.\n";
  std::cout << "Simulated " << events.size() << " catalog-defined truth sources and "
            << stations.size() << " identified receiver placements.\n";
}

using StageWeights = std::array<std::array<double, 3>, 3>;
StageWeights stage_weights(const Config &c, const std::vector<Datum> &data) {
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
void invert(const Config &c, std::string dir, std::string mode) {
  auto e = read_events(dir + "/initial_events.csv"),
       stations = read_events(dir + "/stations.csv");
  auto data = observations(dir + "/observations.csv");
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
  auto log = output(dir + "/" + mode + "_history.csv");
  log << "iteration,stage,absolute_rms,catalog_rms,precise_rms,velocity_step,"
         "location_step,step_fraction,objective_before,objective_after,lsqr_"
         "iterations,lsqr_relative_normal_residual,lsqr_converged,ray_count,"
         "ray_converged_count,ray_projected_gradient_max,ray_raw_gradient_max\n";
  for (int it = 0; it < int(c.get("iterations")); it++) {
    auto r = rays(g, e, stations, c, true, &used);
    size_t ray_converged = 0;
    double ray_projected_max = 0, ray_raw_max = 0;
    for (int index : used) {
      ray_converged += r[index].converged;
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
      const auto &d = data[q];
      double res = residual[q];
      ss[d.type] += res * res;
      count[d.type]++;
      if (mode == "standard" && d.type != 0)
        continue;
      double weight = mode == "standard" ? 1 : weights[stage][d.type];
      weight *= d.a_priori_weight;
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
      A.add(observation_row(d, r, g, ne, ns, locate), res, weight);
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
      auto nr = rays(ng, ee, stations, c, false, &used);
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
        << ',' << linear_info.converged << ',' << used.size() << ','
        << ray_converged << ',' << ray_projected_max << ',' << ray_raw_max << '\n';
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
  if (authoritative || authoritative_geometry(c, dir))
    for (auto &event : e)
      set_metadata(event.metadata, "coordinate_basis",
                   "independent " + mode + " inversion estimate; provider IDs identify reference catalog records");
  write_events(e, dir + "/" + mode + "_events.csv");
  auto rr = rays(g, e, stations, c, true, &used);
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
  csv_metadata_header(f, data.front().metadata);
  f << '\n';
  for (const auto &d : data) {
    f << d.i << ',' << d.j << ',' << d.k << ',' << d.type << ','
      << d.value - prediction(d, rr, e, ns);
    csv_metadata_values(f, d.metadata);
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
void raycheck(const Config &c, std::string dir, std::string mode = "truth") {
  auto e = read_events(dir + "/" + mode + "_events.csv");
  auto stations = read_events(dir + "/stations.csv");
  auto data = observations(dir + "/observations.csv");
  auto used = observed_rays(data, e.size(), stations);
  const bool authoritative = authoritative_input(c, dir);
  if (authoritative)
    validate_identities(e, stations, data);
  else if (authoritative_geometry(c, dir))
    validate_identities(e, stations, data, true);
  std::vector<int> samples;
  const int ns = stations.size();
  const std::string sample_path = dir + "/ray_samples.csv";
  if (std::filesystem::exists(sample_path)) {
    auto table = csv_table(sample_path, {"event", "station"});
    for (const auto &row : table.rows) {
      int i = csv_int(row[0]), k = csv_int(row[1]);
      if (i < 0 || i >= int(e.size()) || k < 0 || k >= ns ||
          !std::binary_search(used.begin(), used.end(), i * ns + k))
        throw std::runtime_error("Ray sample must identify an observed event/channel pair");
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
  std::string prefix = mode == "truth" ? "ray" : mode + "_ray";
  auto f = output(dir + "/" + prefix + "_convergence.csv");
  f << "event,station,production_time,refined_time,difference,production_"
       "gradient,refined_gradient,production_raw_gradient,refined_raw_gradient,"
       "production_iterations,refined_iterations,production_converged,refined_"
       "converged,production_merged,refined_merged,diagnostic_row\n";
  auto df = output(dir + "/" + prefix + "_derivatives.csv");
  df << "event,station,axis,production_derivative,refined_derivative,finite_"
        "difference,production_error,refined_error,diagnostic_row\n";
  // Both diagnostic tables refer to this zero-based sample key. Each mapping
  // row identifies an original observations.csv row and its i/j event side.
  auto identifiers = output(dir + "/" + prefix + "_identifiers.csv");
  identifiers << "diagnostic_row,event,station,observation_row,observation_event_side";
  csv_metadata_header(identifiers, data.front().metadata, "observation_");
  csv_metadata_header(identifiers, e.front().metadata, "source_");
  csv_metadata_header(identifiers, stations.front().metadata, "receiver_");
  identifiers << '\n';
  for (size_t n = 0; n < samples.size(); n++) {
    int i = samples[n] / ns, k = samples[n] % ns;
    for (size_t q = 0; q < data.size(); q++)
      if ((data[q].i == i && data[q].k == k) ||
          (data[q].j == i && second_station(data[q]) == k)) {
        identifiers << n << ',' << i << ',' << k << ',' << q << ','
                    << (data[q].i == i ? "i" : "j");
        csv_metadata_values(identifiers, data[q].metadata);
        csv_metadata_values(identifiers, e[i].metadata);
        csv_metadata_values(identifiers, stations[k].metadata);
        identifiers << '\n';
      }
    Ray a = trace(g, e[i].p, stations[k].p, c.get("ray_spacing"),
                  c.get("ray_iterations"));
    Ray b = trace(g, e[i].p, stations[k].p, c.get("ray_spacing") / 2, 1000);
    f << i << ',' << k << ',' << a.time << ',' << b.time << ','
      << a.time - b.time << ',' << a.gradient << ',' << b.gradient << ','
      << a.raw_gradient << ',' << b.raw_gradient << ',' << a.iterations << ','
      << b.iterations << ',' << a.converged << ',' << b.converged << ','
      << a.merged_nodes << ',' << b.merged_nodes << ',' << n << '\n';
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
           << b.source[axis] - fd << ',' << n << '\n';
      }
  }
}

// Frozen, unweighted absolute-data Jacobian at the saved event/model estimate.
// Noise, prior, robust, and smoothing weights are deliberately not folded into G.
void linearize(const Config &c, const std::string &dir, const std::string &mode) {
  auto events = read_events(dir + "/" + mode + "_events.csv");
  auto stations = read_events(dir + "/stations.csv");
  auto data = observations(dir + "/observations.csv");
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
  csv_metadata_header(rows, data.front().metadata);
  const bool prior_column = metadata_value(data.front().metadata, "a_priori_weight");
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
    csv_metadata_values(rows, d.metadata);
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

int main(int argc, char **argv) {
  try {
    if (argc >= 3 && std::string(argv[1]) == "validate") {
      validate(argv[2]);
      return 0;
    }
    if (argc < 4)
      throw std::runtime_error("Usage: dd validate OUT | dd generate CONFIG "
                               "OUT | dd simulate CONFIG OUT | dd invert CONFIG OUT MODE | "
                               "dd raycheck CONFIG OUT [MODE] | dd linearize CONFIG OUT MODE");
    Config c(argv[2]);
    std::string cmd = argv[1];
    if (cmd == "generate")
      generate(c, argv[3]);
    else if (cmd == "simulate")
      simulate(c, argv[3]);
    else if (cmd == "raycheck")
      raycheck(c, argv[3], argc == 5 ? argv[4] : "truth");
    else if (cmd == "invert" && argc == 5)
      invert(c, argv[3], argv[4]);
    else if (cmd == "linearize" && argc == 5)
      linearize(c, argv[3], argv[4]);
    else
      throw std::runtime_error("Unknown command");
  } catch (const std::exception &e) {
    std::cerr << e.what() << '\n';
    return 1;
  }
  return 0;
}
