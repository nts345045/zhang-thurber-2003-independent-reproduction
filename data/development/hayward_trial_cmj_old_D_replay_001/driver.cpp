// Four configured evaluations across old/D: exactly eight trace subcalls.
#define main archived_application_main
#include "src/main.cpp"
#undef main
#include <array>
#include <cstring>
#include <functional>
#include "candidate_forward.hpp"

static const std::vector<int> replay_events{981, 987};
static constexpr int replay_station = 160;

void same_metadata(const CsvTable &table, const Strings &row, size_t start,
                   const Event &event, const Event &station) {
  size_t n = start;
  for (auto item : {std::make_pair(&event.metadata, "source_"),
                    std::make_pair(&station.metadata, "receiver_")})
    for (const auto &value : *item.first) {
      if (n >= row.size() || table.header[n] != std::string(item.second) + value.first ||
          row[n] != value.second) throw std::runtime_error("Candidate native metadata mismatch");
      ++n;
    }
  if (n != row.size()) throw std::runtime_error("Unexpected candidate metadata columns");
}

first_arrival::Candidate load_candidate(const std::string &dir, int event_index,
                                         const Event &event, const Event &station,
                                         const Grid &g) {
  const auto meta = csv_table(dir + "/candidate_metadata.csv",
      {"event", "station", "success", "field_time", "descent_steps", "fallback_steps", "path_points", "message"});
  const auto paths = csv_table(dir + "/candidate_paths.csv", {"event", "station", "node", "x", "y", "z"});
  if (meta.rows.size() != replay_events.size()) throw std::runtime_error("Incomplete candidate inventory");
  first_arrival::Candidate result;
  int matches = 0, expected_points = 0;
  for (size_t n = 0; n < meta.rows.size(); ++n) {
    const auto &r = meta.rows[n];
    if (csv_int(r[0]) != replay_events[n] || csv_int(r[1]) != replay_station)
      throw std::runtime_error("Candidate native order mismatch");
    if (csv_int(r[0]) != event_index) continue;
    ++matches;
    same_metadata(meta, r, 8, event, station);
    if (csv_int(r[2]) != 1) throw std::runtime_error("Original Candidate did not succeed");
    result.success = true;
    result.field_time = csv_double(r[3]);
    result.descent_steps = csv_int(r[4]);
    result.fallback_steps = csv_int(r[5]);
    expected_points = csv_int(r[6]);
    result.message = r[7];
    if (result.descent_steps < 0 || result.fallback_steps < 0)
      throw std::runtime_error("Invalid Candidate counters");
  }
  if (matches != 1) throw std::runtime_error("Candidate metadata missing or duplicated");
  for (const auto &r : paths.rows) {
    const int i = csv_int(r[0]);
    if (std::find(replay_events.begin(), replay_events.end(), i) == replay_events.end() ||
        csv_int(r[1]) != replay_station) throw std::runtime_error("Unexpected candidate path identity");
    if (i != event_index) continue;
    if (csv_int(r[2]) != int(result.path.size())) throw std::runtime_error("Candidate node ordering mismatch");
    same_metadata(paths, r, 6, event, station);
    P point{csv_double(r[3]), csv_double(r[4]), csv_double(r[5])};
    if (!g.contains(point)) throw std::runtime_error("Candidate outside original box");
    result.path.push_back(point);
  }
  if (int(result.path.size()) != expected_points || result.path.size() < 2 ||
      result.path.front() != event.p || result.path.back() != station.p)
    throw std::runtime_error("Candidate inventory/endpoints mismatch");
  return result;
}

bool same_double(double a, double b) { return std::memcmp(&a, &b, sizeof(double)) == 0; }
void exact_candidate(const first_arrival::Candidate &a, const first_arrival::Candidate &b) {
  if (a.success != b.success || a.message != b.message || a.descent_steps != b.descent_steps ||
      a.fallback_steps != b.fallback_steps || !same_double(a.field_time, b.field_time) || a.path.size() != b.path.size())
    throw std::runtime_error("Candidate serialization changed metadata");
  for (size_t n = 0; n < a.path.size(); ++n)
    for (int axis = 0; axis < 3; ++axis)
      if (!same_double(a.path[n][axis], b.path[n][axis]))
        throw std::runtime_error("Candidate serialization changed binary64 coordinate");
}

int main(int argc, char **argv) {
  try {
    if (argc != 5) throw std::runtime_error("driver INPUT OUTPUT old|D OLD_CANDIDATE_DIRECTORY");
    const std::string input = argv[1], out = argv[2], mode = argv[3], seeds = argv[4];
    if (mode != "old" && mode != "D") throw std::runtime_error("Unknown replay variant");
    const Grid g = read_grid(input + "/trial_grid.csv");
    auto events = read_events(input + "/trial_events.csv");
    const auto stations = read_events(input + "/stations.csv");
    const Config config(input + "/run.cfg");
    if (events.size() != 1092 || stations.size() != 372 || g.size() != 462 ||
        config.get("ray_spacing") != .03125 || config.get("ray_iterations") != 1000 ||
        auxiliary_spacing(config) != .125) throw std::runtime_error("Unexpected frozen replay settings");
    for (auto &event : events)
      set_metadata(event.metadata, "coordinate_basis",
          "independent failed forward evaluation at recorded coordinates; see companion context for evaluation phase");
    std::unique_ptr<first_arrival::Field> field;
    if (mode == "old") {
      std::cout << "Constructing one original receiver field" << std::endl;
      field = std::make_unique<first_arrival::Field>(g, stations[replay_station].p, .125, 2, true);
      if (field->node_count() != 45603129 || field->accepted_nodes != field->node_count())
        throw std::runtime_error("Unexpected full receiver-field inventory");
      std::cout << "Completed one receiver field: " << field->node_count() << " nodes" << std::endl;
    }
    std::vector<Ray> results(events.size() * stations.size());
    std::vector<int> used;
    std::vector<first_arrival::Candidate> candidates;
    auto path = output(out + "/paths.csv"), cp = output(out + "/candidate_paths.csv"),
         cm = output(out + "/candidate_metadata.csv"), starts = output(out + "/starts.csv");
    path << "event,station,node,x,y,z";
    cp << "event,station,node,x,y,z";
    cm << "event,station,success,field_time,descent_steps,fallback_steps,path_points,message";
    starts << "event,station,start,time,converged,projected_gradient,raw_gradient,iterations,merged_nodes,path_points";
    for (auto *stream : {&path, &cp, &cm, &starts}) {
      *stream << std::setprecision(17);
      csv_metadata_header(*stream, events.front().metadata, "source_");
      csv_metadata_header(*stream, stations.front().metadata, "receiver_");
      *stream << '\n';
    }
    for (int i : replay_events) {
      const Event &event = events[i], &station = stations[replay_station];
      first_arrival::Candidate captured;
      std::array<Ray, 2> starts_returned;
      const auto provider = [&]() {
        captured = mode == "old" ? field->candidate(event.p) : load_candidate(seeds, i, event, station, g);
        return captured;
      };
      const int index = i * stations.size() + replay_station;
      results[index] = replay_candidate(g, event.p, station.p, config.get("ray_spacing"),
          int(config.get("ray_iterations")), false, provider, starts_returned);
      const Ray &ray = results[index];
      if (!captured.success || !finite_ray(ray) || !ray_path_in_domain(g, ray) ||
          ray.path.front() != event.p || ray.path.back() != station.p ||
          !ray.dv.empty() || !ray.length.empty()) throw std::runtime_error("Invalid action-only replay Ray");
      used.push_back(index);
      candidates.push_back(captured);
      const std::array<std::pair<std::ofstream *, const std::vector<P> *>, 2> exports{{
          {&path, &ray.path}, {&cp, &captured.path}}};
      for (auto item : exports) {
        for (size_t n = 0; n < item.second->size(); ++n) {
          *item.first << i << ',' << replay_station << ',' << n;
          for (double value : (*item.second)[n]) *item.first << ',' << value;
          csv_metadata_values(*item.first, event.metadata);
          csv_metadata_values(*item.first, station.metadata);
          *item.first << '\n';
        }
      }
      cm << i << ',' << replay_station << ',' << captured.success << ',' << captured.field_time << ','
         << captured.descent_steps << ',' << captured.fallback_steps << ',' << captured.path.size() << ','
         << csv_quote(captured.message);
      csv_metadata_values(cm, event.metadata); csv_metadata_values(cm, station.metadata); cm << '\n';
      for (int branch = 0; branch < 2; ++branch) {
        const auto &r = starts_returned[branch];
        starts << i << ',' << replay_station << ',' << (branch ? "fmm" : "straight") << ',' << r.time << ','
               << r.converged << ',' << r.gradient << ',' << r.raw_gradient << ',' << r.iterations << ','
               << r.merged_nodes << ',' << r.path.size();
        csv_metadata_values(starts, event.metadata); csv_metadata_values(starts, station.metadata); starts << '\n';
      }
    }
    path.close(); cp.close(); cm.close(); starts.close();
    for (size_t n = 0; n < replay_events.size(); ++n)
      exact_candidate(candidates[n], load_candidate(out, replay_events[n], events[replay_events[n]], stations[replay_station], g));
    write_ray_status(out + "/status.csv", events, stations, results, &used, &g, 17, false);
    if (replay_trace_calls != 4) throw std::runtime_error("Unexpected trace-call inventory");
    std::cout << "configured_evaluations=2 trace_subcalls=" << replay_trace_calls
              << " field_constructions=" << (mode == "old" ? 1 : 0) << " exact_candidate_roundtrips=2" << std::endl;
    return 0;
  } catch (const std::exception &error) {
    std::cerr << error.what() << '\n';
    return 1;
  }
}
