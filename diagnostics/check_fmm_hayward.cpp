// Compare feasible candidate paths in a saved model, without reinversion.
#define main frozen_solver_entry_point
#include "../src/main.cpp"
#undef main
#include "first_arrival_fmm.hpp"
#include "seeded_bending.hpp"
#include "production_entry_checks.hpp"
#include <chrono>

int main(int argc, char **argv) {
  if (argc != 5 && argc != 7 && argc != 8)
    throw std::runtime_error("Usage: check_fmm_hayward GRID.csv RAYS.csv OUTPUT.csv AUX_SPACING [1|2 original|closed [production]]");
  const int order = argc >= 7 ? std::stoi(argv[5]) : 1;
  const std::string rule = argc >= 7 ? argv[6] : "original";
  const bool production_entry = argc == 8;
  if (production_entry && std::string(argv[7]) != "production")
    throw std::runtime_error("Unknown entry point");
  if ((order != 1 && order != 2) || (rule != "original" && rule != "closed"))
    throw std::runtime_error("Invalid FMM order or receiver seed rule");
  const bool closed_seed_cells = rule == "closed";
  const Grid g = read_grid(argv[1]);
  const auto inputs = csv_table(argv[2]);
  const double spacing = csv_double(argv[4]);
  std::map<std::string,size_t> columns;
  for (size_t n=0; n<inputs.header.size(); ++n) columns[inputs.header[n]]=n;
  auto position = [&](const Strings &row, const std::string &prefix) {
    return P{csv_double(row[columns.at(prefix+"x_km")]),
             csv_double(row[columns.at(prefix+"y_km")]),
             csv_double(row[columns.at(prefix+"z_km")])};
  };
  std::map<P,std::vector<size_t>> receivers;
  for (size_t n=0; n<inputs.rows.size(); ++n)
    receivers[position(inputs.rows[n],"receiver_")].push_back(n);
  auto f=output(argv[3]);
  f << std::setprecision(15);
  for (size_t n=0; n<inputs.header.size(); ++n)
    f << (n ? "," : "") << csv_quote(inputs.header[n]);
  f << ",auxiliary_spacing_km,path_spacing_km,field_nodes,field_build_seconds,"
       "extracted,extraction_message,field_time_s,seed_action_s,"
       "baseline_ray_time_s,baseline_ray_converged,baseline_ray_gradient,"
       "fmm_bent_time_s,fmm_bent_converged,fmm_bent_gradient,"
       "selected_action_s,action_reduction_s,selected_converged,"
       "source_derivative_change_s_per_km,selected_max_depth_km,"
       "selected_outside_nodes,selected_endpoint_error_km,order,closed_seed_cells,seed_nodes,"
       "first_order_direction_evaluations,second_order_direction_evaluations,second_order_ineligible,"
       "causal_fallback_updates,root_bisection_updates,second_neighbor_revisits,"
       "baseline_ray_iterations,fmm_bent_iterations,selected_iterations,"
       "production_entry_checked,production_entry_passed\n";
  size_t done=0;
  for (const auto &group:receivers) {
    auto start=std::chrono::steady_clock::now();
    const first_arrival::Field field(g,group.first,spacing,order,closed_seed_cells);
    const double seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
    for (size_t index:group.second) {
      const auto &input=inputs.rows[index];
      const P a=position(input,"dd_source_"), b=group.first;
      const auto original=trace(g,a,b,.5,1000);
      const auto seed=field.candidate(a);
      Ray bent, selected=original;
      if (seed.success) {
        bent=bend_seed(g,seed.path,.5,1000);
        if (bent.time<selected.time) selected=bent;
      }
      bool parity = false;
      if (production_entry) {
        Ray production = trace_first_arrival(g,a,b,.5,1000,true,field);
        auto equal = ProductionEntryChecks::equal(selected, production);
        bool metadata = production.initialization_attempted &&
            production.initialization_succeeded == seed.success &&
            production.selected_fmm_seed == (seed.success && bent.time < original.time) &&
            production.direct_seed_time == original.time &&
            (seed.success ? production.fmm_seed_time == bent.time : std::isnan(production.fmm_seed_time)) &&
            production.initializer_field_time == seed.field_time &&
            production.initializer_fallback_steps == seed.fallback_steps &&
            production.initializer_message == seed.message;
        parity = metadata && std::all_of(equal.begin(), equal.end(), [](bool value) { return value; });
        selected = std::move(production);
      }
      double outside=0,maxdepth=a[2];
      for (auto p:selected.path) {
        outside+=!g.contains(p);
        maxdepth=std::max(maxdepth,p[2]);
      }
      for (size_t n=0; n<input.size(); ++n)
        f << (n ? "," : "") << csv_quote(input[n]);
      f << ',' << spacing << ",0.5," << field.node_count() << ',' << seconds << ','
        << seed.success << ',' << csv_quote(seed.message) << ',' << seed.field_time << ','
        << (seed.success ? path_eval(g,seed.path) : NAN) << ',' << original.time << ','
        << original.converged << ',' << original.gradient << ','
        << (seed.success ? bent.time : NAN) << ',' << (seed.success && bent.converged) << ','
        << (seed.success ? bent.gradient : NAN) << ',' << selected.time << ','
        << original.time-selected.time << ',' << selected.converged << ','
        << norm(selected.source-original.source) << ',' << maxdepth << ',' << outside << ','
        << norm(selected.path.front()-a)+norm(selected.path.back()-b) << ','
        << field.order() << ',' << field.closed_seed_cells() << ',' << field.stats.seed_nodes << ','
        << field.stats.first_order_direction_evaluations << ',' << field.stats.second_order_direction_evaluations << ','
        << field.stats.second_order_ineligible << ',' << field.stats.causal_fallback_updates << ','
        << field.stats.root_bisection_updates << ',' << field.stats.second_neighbor_revisits << ','
        << original.iterations << ',' << (seed.success ? bent.iterations : 0) << ','
        << selected.iterations << ',' << production_entry << ','
        << (production_entry ? (parity ? "1" : "0") : "") << std::endl;
    }
    std::cout << "receiver " << ++done << '/' << receivers.size() << " rays "
              << group.second.size() << " field_seconds " << seconds << std::endl;
  }
}
