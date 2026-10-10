// Invented adapter fixture only: load and assemble supplied rows, without rays
// or an inverse solve. The Python harness freezes every included source.
#define main tomography_main
#include "../src/main.cpp"
#undef main

int main(int argc, char **argv) {
  try {
    if (argc != 3) throw std::runtime_error("Expected fixture directory and result JSON");
    const std::string dir = argv[1];
    size_t checks = 0;
    auto check = [&](bool pass, const char *message) {
      if (!pass) throw std::runtime_error(message);
      ++checks;
    };
    auto events = read_events(dir + "/initial_events.csv");
    auto stations = read_events(dir + "/stations.csv");
    auto data = observations(dir + "/observations.csv");
    check(events.size() == 2 && stations.size() == 2 && data.size() == 4,
          "Unexpected invented fixture dimensions");
    validate_identities(events, stations, data);
    check(!data.shared_synthetic, "Real-input metadata route was not used");
    check(data[0].type == 0 && data[1].type == 0 && data[2].type == 1 && data[3].type == 2,
          "Catalog order or appended type differs");
    check(data[3].i == 0 && data[3].j == 1 && data[3].k == 0 && data[3].station_j == 1,
          "Both native receiver epochs must be retained");
    check(required_metadata(stations[0].metadata, "location_code", true).empty(),
          "Empty native location lost");
    check(required_metadata(data.native_metadata[3], "uncertainty_s", true).empty(),
          "Derived CC uncertainty must remain blank");
    check(data[3].a_priori_weight == 0.25, "Literal CC squared prior differs");
    check(data[3].value == 0.3125, "Differential time or origin correction differs");
    auto original = data;
    original.rows.pop_back();
    original.native_metadata.pop_back();
    check(observed_rays(data, events.size(), stations) ==
          observed_rays(original, events.size(), stations), "CC adds a new native ray");

    // Round-trip the actual loader's metadata, including quoted embedded text.
    {
      auto f = output(dir + "/component_roundtrip.csv");
      f << std::setprecision(17) << "i,j,station,type,value";
      data.write_header(f); f << '\n';
      for (size_t q = 0; q < data.size(); ++q) {
        const auto &d = data[q];
        f << d.i << ',' << d.j << ',' << d.k << ',' << d.type << ',' << d.value;
        data.write_metadata(f, q); f << '\n';
      }
    }
    auto roundtrip = observations(dir + "/component_roundtrip.csv");
    check(roundtrip.metadata_header == data.metadata_header &&
          roundtrip.native_metadata == data.native_metadata, "Metadata round-trip differs");

    // Supplied arbitrary ray values distinguish the second native receiver.
    // They are algebra fixtures, not calculated travel times or derivatives.
    std::vector<Ray> rays(4);
    rays[0].time = 1.5; rays[0].source = {1, 2, 3};
    rays[1].time = 900; rays[1].source = {90, 90, 90};
    rays[2].time = 800; rays[2].source = {80, 80, 80};
    rays[3].time = 3; rays[3].source = {4, 5, 6};
    events[0].t = 0.125; events[1].t = -0.25;
    check(prediction(data[3], rays, events, 2) == -1.125,
          "Prediction must be source i minus source j with both epochs");
    Grid unused_grid;
    const auto row = observation_row(data[3], rays, unused_grid, 2, 2, true);
    const std::array<double, 8> expected{{1, 2, 3, 1, -4, -5, -6, -1}};
    check(row.size() == expected.size(), "Wrong differential derivative dimension");
    for (size_t q = 0; q < expected.size(); ++q)
      check(row[q].col == int(q) && row[q].val == expected[q],
            "Differential source/origin derivative sign differs");

    Config config(dir + "/component.cfg");
    auto stages = stage_weights(config, data);
    check(stages[2][2] == 1, "Explicit invented stage factor differs");
    // Coincident invented event coordinates isolate the distance factor; the
    // nonunit residual taper is retained identically in the two actual rows.
    events[1].p = events[0].p;
    const double residual = 0.5, cutoff = 1;
    auto weight = observation_weight(config, "dd", stages, 2, data[3], residual, cutoff, events);
    auto unit = data[3]; unit.a_priori_weight = 1;
    auto unit_weight = observation_weight(config, "dd", stages, 2, unit, residual, cutoff, events);
    check(weight.active() && weight.robust == 0.5625 && weight.distance == 1,
          "Unexpected residual or distance taper");
    check(weight.combined == 0.140625 && unit_weight.combined == 0.5625,
          "Actual row multiplier must include literal CC squared");
    Matrix weighted(8), unweighted_prior(8);
    weighted.add(row, residual, weight.combined);
    unweighted_prior.add(row, residual, unit_weight.combined);
    for (size_t q = 0; q < expected.size(); ++q)
      check(weighted.values[q] == expected[q] * 0.140625,
            "Actual stored weighted Jacobian differs");
    check(weighted.rhs[0] == 0.0703125, "Actual stored weighted residual differs");
    const double objective_ratio = (weighted.rhs[0] * weighted.rhs[0]) /
      (unweighted_prior.rhs[0] * unweighted_prior.rhs[0]);
    check(objective_ratio == 0.0625, "Conditional squared objective must have CC fourth power");
    // A second exactly representable case makes both stage and distance
    // nonunit, so accidentally skipping either factor cannot pass the check.
    config.v["stage3_precise_weight"] = 0.5;
    stages = stage_weights(config, data);
    events[1].p = events[0].p; events[1].p[0] += 5;
    auto nonunit = observation_weight(config, "dd", stages, 2, data[3], residual, cutoff, events);
    check(nonunit.stage == 0.5 && nonunit.distance == 0.5625 &&
          nonunit.robust == 0.5625 && nonunit.combined == 0.03955078125,
          "Nonunit stage/residual/distance multiplication differs");
    Matrix all_factors(8);
    all_factors.add(row, residual, nonunit.combined);
    check(all_factors.rhs[0] == 0.019775390625 &&
          all_factors.values[0] == 0.03955078125 &&
          all_factors.values[7] == -0.03955078125,
          "Nonunit factors are not applied to both Jacobian and residual");
    config.v["catalog_only_dd"] = 1;
    bool rejected = false;
    try { stage_weights(config, data); } catch (const std::exception &) { rejected = true; }
    check(rejected, "Catalog-only configuration must reject CC rows");
    auto f = output(argv[2]);
    f << "{\n  \"status\": \"passed\",\n  \"checks\": " << checks
      << ",\n  \"invented_geometry_only\": true,\n  \"ray_traces\": 0,\n  \"inverse_solves\": 0,\n"
      << "  \"cc\": 0.5,\n  \"prior\": 0.25,\n  \"conditional_objective_ratio\": "
      << objective_ratio << ",\n  \"nonunit_stage\": 0.5,\n  \"nonunit_distance_taper\": 0.5625,\n"
      << "  \"nonunit_combined_multiplier\": 0.03955078125\n}\n";
    return 0;
  } catch (const std::exception &error) {
    std::cerr << error.what() << '\n';
    return 1;
  }
}
