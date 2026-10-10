#pragma once
// Diagnostic-only loader. Grid/candidate/csv types come from the frozen driver.
first_arrival::Candidate read_saved_candidate(
    const Grid &g, P source, P receiver, const std::string &expected_run,
    const std::string &observation, const std::string &path_file,
    const std::string &metadata_file) {
  const auto paths = csv_table(path_file), metadata = csv_table(metadata_file);
  const std::vector<std::string> path_header = {
      "run_id", "observation_index", "kind", "node", "x", "y", "z"};
  const std::vector<std::string> metadata_header = {
      "run_id", "observation_index", "field_time_s", "success",
      "descent_steps", "fallback_steps", "message"};
  auto require = [](bool ok, const char *message) {
    if (!ok) throw std::runtime_error(message);
  };
  require(paths.header == path_header && metadata.header == metadata_header,
          "Saved candidate schema mismatch");
  require(metadata.rows.size() == 1, "Saved candidate metadata must have exactly one row");
  const auto &m = metadata.rows.front();
  require(m.size() == metadata_header.size(), "Incomplete saved candidate metadata");
  require(m[0] == expected_run && m[1] == observation, "Saved candidate metadata identity mismatch");
  require(m[3] == "1", "Saved candidate was not successful");
  auto integer = [&](const std::string &text) {
    std::size_t end = 0;
    const double value = std::stod(text, &end);
    require(end == text.size() && std::isfinite(value) && value >= 0 &&
                value <= std::numeric_limits<int>::max() && std::floor(value) == value,
            "Invalid saved candidate counter/index");
    return int(value);
  };
  first_arrival::Candidate candidate;
  candidate.success = true;
  candidate.field_time = csv_double(m[2]);
  require(std::isfinite(candidate.field_time) && candidate.field_time >= 0,
          "Nonfinite or negative saved candidate field time");
  candidate.descent_steps = integer(m[4]);
  candidate.fallback_steps = integer(m[5]);
  candidate.message = m[6];
  std::vector<P> resampled;
  bool second_frame = false;
  for (const auto &row : paths.rows) {
    require(row.size() == path_header.size(), "Incomplete saved candidate path row");
    require(row[0] == expected_run && row[1] == observation, "Saved candidate path identity mismatch");
    require(row[2] == "raw_fmm_seed" || row[2] == "post_resampling_and_merge",
            "Unknown saved candidate path frame");
    if (row[2] == "post_resampling_and_merge") second_frame = true;
    require(!(second_frame && row[2] == "raw_fmm_seed"), "Saved candidate frame order changed");
    auto &path = second_frame ? resampled : candidate.path;
    require(std::size_t(integer(row[3])) == path.size(), "Saved candidate node inventory changed");
    const P point = {csv_double(row[4]), csv_double(row[5]), csv_double(row[6])};
    require(std::all_of(point.begin(), point.end(), [](double value) { return std::isfinite(value); }) &&
                g.contains(point), "Saved candidate point is nonfinite or outside model");
    path.push_back(point);
  }
  for (const auto *path : {&candidate.path, &resampled})
    require(path->size() >= 3 && path->front() == source && path->back() == receiver,
            "Saved candidate frame/endpoints changed");
  return candidate;
}
