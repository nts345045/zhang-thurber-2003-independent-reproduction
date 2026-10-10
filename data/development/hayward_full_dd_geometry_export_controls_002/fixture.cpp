// Invented arrays and one tiny physical export; never an inverse solve.
#ifdef NDEBUG
#error "Keep assertions enabled for the bounded fixture"
#endif
#include <string>
std::string fixture_output_suffix;
#define main dd_program_main
#include "main.cpp"
#undef main

int main(int argc, char **argv) {
  try {
    if (argc != 4) throw std::runtime_error("fixture cli|arrays DIRECTORY CASE");
    const std::string action = argv[1], dir = argv[2], test = argv[3];
    if (action == "cli") {
      std::string cfg = dir + "/run.cfg", mode = "dd", stage = "0";
      char program[] = "dd", command[] = "linearize_full";
      char *args[] = {program, command, cfg.data(), argv[2], mode.data(), stage.data()};
      return dd_program_main(6, args);
    }
    if (action != "arrays") throw std::runtime_error("Unknown fixture action");
    const Config config(dir + "/run.cfg");
    const auto events = read_events(dir + "/dd_events.csv");
    const auto stations = read_events(dir + "/stations.csv");
    const auto data = observations(dir + "/observations.csv", events, stations);
    const auto grid = read_grid(dir + "/dd_grid.csv");
    std::vector<Ray> supplied(events.size() * stations.size());
    for (size_t index = 0; index < supplied.size(); ++index) {
      auto &ray = supplied[index];
      const auto source = events[index / stations.size()].p;
      const auto receiver = stations[index % stations.size()].p;
      ray.time = .25 + .031 * index;
      ray.source = {{.12345678901234566 + .01 * index, -.04, .2}};
      ray.path = {source, (source + receiver) * .5, receiver};
      ray.dv.resize(grid.size()); ray.length.resize(grid.size());
      for (int k = 0; k < grid.size(); ++k) {
        ray.dv[k] = -.001 * (k + 1 + index);
        ray.length[k] = .1 * (k + 1) + .01 * index;
      }
      ray.gradient = .125; ray.raw_gradient = .25;
      ray.converged = true; ray.iterations = 3;
      ray.initialization_attempted = true; ray.initialization_succeeded = true;
      ray.direct_seed_time = ray.time; ray.fmm_seed_time = ray.time + .01;
      ray.initializer_field_time = ray.time + .02;
      ray.initializer_message = "invented, supplied \"Ray\" array";
    }
    auto &ray = supplied[0];
    const double nan = std::numeric_limits<double>::quiet_NaN();
    if (test == "local") ray.converged = false;
    else if (test == "initializer_failed") ray.initialization_succeeded = false;
    else if (test == "unattempted" || test == "missing_required") {
      for (auto &r : supplied) {
        r.initialization_attempted = false; r.initialization_succeeded = false;
        r.direct_seed_time = r.fmm_seed_time = r.initializer_field_time = nan;
      }
    } else if (test == "outside") ray.path[1][0] = std::nextafter(grid.x.back(), INFINITY);
    else if (test == "source_endpoint") ray.path.front()[0] = std::nextafter(ray.path.front()[0], INFINITY);
    else if (test == "receiver_endpoint") ray.path.back()[0] = std::nextafter(ray.path.back()[0], INFINITY);
    else if (test == "empty") ray.path.clear();
    else if (test == "nan_path") ray.path[1][0] = nan;
    else if (test == "nan_time") ray.time = nan;
    else if (test == "nan_source") ray.source[0] = nan;
    else if (test == "short_dv") ray.dv.pop_back();
    else if (test == "short_length") ray.length.pop_back();
    else if (test == "wrong_array") supplied.pop_back();
    else if (test == "io_geometry") fixture_output_suffix = "_ray_geometry.csv";
    else if (test == "io_paths") fixture_output_suffix = "_ray_paths.csv";
    else if (test != "valid") throw std::runtime_error("Unknown supplied-array case");
    bool threw = false; std::string error;
    try {
      write_full_linearization(config, dir + "/dd_full_linearization", "dd", 0,
                               "fixture supplied arrays", events, stations, data, grid, supplied);
    } catch (const std::exception &e) { threw = true; error = e.what(); }
    // Use an ordinary stream: the output seam targets only the two new files.
    std::ofstream result(dir + "/writer_outcome.csv");
    result << "threw,error\n" << threw << ',' << csv_quote(error) << '\n';
    finish_output(result, dir + "/writer_outcome.csv");
    return 0;
  } catch (const std::exception &error) {
    std::cerr << error.what() << '\n';
    return 1;
  }
}
