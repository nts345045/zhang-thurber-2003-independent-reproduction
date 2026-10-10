// Two calls total are authorized: this executable evaluates two fixed pairs.
// Keep the archived readers and scalar writer; never construct a receiver field.
#define main archived_application_main
#include "src/main.cpp"
#undef main

int main(int argc, char **argv) {
  try {
    if (argc != 3) throw std::runtime_error("driver INPUT_DIRECTORY OUTPUT_DIRECTORY");
    const std::string input = argv[1], out = argv[2];
    const Grid g = read_grid(input + "/initial_grid.csv");
    const auto events = read_events(input + "/initial_events.csv");
    const auto stations = read_events(input + "/stations.csv");
    if (events.size() != 724 || stations.size() != 52)
      throw std::runtime_error("Unexpected full native geometry inventory");
    const Config config(input + "/run.cfg");
    if (config.get("ray_spacing") != 0.03125 || config.get("ray_iterations") != 4000)
      throw std::runtime_error("Unexpected frozen straight-trace settings");
    const std::vector<int> pairs{8670, 8674};
    std::vector<Ray> result(events.size() * stations.size());
    auto paths = output(out + "/paths.csv");
    auto kernels = output(out + "/model_partials.csv");
    paths << std::setprecision(17);
    kernels << std::setprecision(17);
    paths << "pair_index,event,station,node,x,y,z";
    kernels << "pair_index,event,station,model_index,dT_dv,length";
    for (auto *stream : {&paths, &kernels}) {
      csv_metadata_header(*stream, events.front().metadata, "source_");
      csv_metadata_header(*stream, stations.front().metadata, "receiver_");
      *stream << '\n';
    }
    for (int pair : pairs) {
      const int i = pair / stations.size(), k = pair % stations.size();
      // This is precisely the first call inside archived trace_first_arrival.
      // Null seed uses trace's original straight interpolation, with no resampling helper.
      result[pair] = trace(g, events[i].p, stations[k].p,
                           config.get("ray_spacing"), int(config.get("ray_iterations")),
                           true, nullptr);
      const Ray &r = result[pair];
      if (!finite_ray(r) || !ray_path_in_domain(g, r) ||
          r.path.front() != events[i].p || r.path.back() != stations[k].p ||
          r.dv.size() != g.v.size() || r.length.size() != g.v.size())
        throw std::runtime_error("Invalid returned straight Ray");
      for (size_t n = 0; n < r.path.size(); ++n) {
        if (n && !(norm(r.path[n] - r.path[n-1]) > 0))
          throw std::runtime_error("Nonpositive final edge length");
        paths << pair << ',' << i << ',' << k << ',' << n;
        for (double value : r.path[n]) paths << ',' << value;
        csv_metadata_values(paths, events[i].metadata);
        csv_metadata_values(paths, stations[k].metadata);
        paths << '\n';
      }
      for (size_t n = 0; n < r.dv.size(); ++n) {
        kernels << pair << ',' << i << ',' << k << ',' << n << ',' << r.dv[n]
                << ',' << r.length[n];
        csv_metadata_values(kernels, events[i].metadata);
        csv_metadata_values(kernels, stations[k].metadata);
        kernels << '\n';
      }
    }
    // The initializer fields here describe a fresh straight-only call. Original
    // FMM-selection metadata remains separately saved in inputs/selected_status.csv.
    write_ray_status(out + "/scalars_12.csv", events, stations, result, &pairs, &g, 12);
    write_ray_status(out + "/scalars_17.csv", events, stations, result, &pairs, &g, 17);
    return 0;
  } catch (const std::exception &e) {
    std::cerr << e.what() << '\n';
    return 1;
  }
}
