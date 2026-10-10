#pragma once
// Observation-only storage, included after the frozen solver and audit IDs.
// The original line-search branch is unchanged; flush only after its failure.
struct CapturedSearchTrial {
  int index, merged;
  double step, action, rhs;
  bool valid, accepted;
  std::vector<P> path;
};
std::string capture_output;
std::vector<CapturedSearchTrial> capture_trials;

void capture_begin() { capture_trials.clear(); }

void capture_trial(int index, double step, const std::vector<P> &path,
                   bool valid, int merged, double action, double rhs,
                   bool accepted) {
  capture_trials.push_back({index, merged, step, action, rhs, valid, accepted, path});
}

void capture_failed(int iteration, const Grid &g, const std::vector<P> &base,
                    const Vec &gradient, const Vec &direction,
                    double cached_action, double slope, double post_loop_step) {
  if (capture_output.empty() || base.size() < 2 || capture_trials.empty() ||
      gradient.size() != 3*(base.size()-2) || direction.size() != gradient.size())
    throw std::runtime_error("Invalid failed-search capture dimensions/output");
  const std::string directions_name=capture_output+"/failed_search_directions.csv";
  const std::string trials_name=capture_output+"/failed_search_trials.csv";
  const std::string decisions_name=capture_output+"/failed_search_decisions.csv";
  for (const auto &name : {directions_name,trials_name,decisions_name})
    if (std::ifstream(name).good())
      throw std::runtime_error("Failed-search capture refuses to overwrite a prior failure");
  std::ofstream directions(directions_name), trials(trials_name), decisions(decisions_name);
  if (!directions || !trials || !decisions)
    throw std::runtime_error("Cannot open failed-search capture outputs");
  for (auto file : {&directions,&trials,&decisions}) *file << std::setprecision(17);
  directions << "run_id,observation_index,iteration,node,is_endpoint,x,y,z,qx,qy,qz,"
                "gradient_x,gradient_y,gradient_z\n";
  trials << "run_id,observation_index,iteration,trial_index,step,node,x,y,z\n";
  decisions << "run_id,observation_index,iteration,trial_index,step,valid,merged_nodes,path_nodes,"
               "cached_base_action_s,reevaluated_base_action_s,trial_action_s,directional_slope,"
               "armijo_rhs_s,binary64_accepted,path_identical_to_base,post_loop_halved_step\n";
  // Reevaluate only after the original search has failed; no decision uses it.
  const double reevaluated=path_eval(g,base);
  for (size_t node=0; node<base.size(); ++node) {
    const bool endpoint=node==0 || node+1==base.size();
    directions << audit_run << ',' << audit_observation << ',' << iteration << ','
               << node << ',' << endpoint;
    for (double value : base[node]) directions << ',' << value;
    for (int axis=0; axis<3; ++axis)
      directions << ',' << (endpoint ? 0 : direction[3*(node-1)+axis]);
    for (int axis=0; axis<3; ++axis) {
      directions << ',';
      if (!endpoint) directions << gradient[3*(node-1)+axis];
    }
    directions << '\n';
  }
  for (const auto &trial : capture_trials) {
    decisions << audit_run << ',' << audit_observation << ',' << iteration << ','
              << trial.index << ',' << trial.step << ',' << trial.valid << ','
              << trial.merged << ',' << trial.path.size() << ',' << cached_action << ','
              << reevaluated << ',' << trial.action << ',' << slope << ',' << trial.rhs << ','
              << trial.accepted << ',' << (trial.path==base) << ',' << post_loop_step << '\n';
    for (size_t node=0; node<trial.path.size(); ++node) {
      trials << audit_run << ',' << audit_observation << ',' << iteration << ','
             << trial.index << ',' << trial.step << ',' << node;
      for (double value : trial.path[node]) trials << ',' << value;
      trials << '\n';
    }
  }
  directions.flush(); trials.flush(); decisions.flush();
  if (!directions || !trials || !decisions)
    throw std::runtime_error("Incomplete failed-search capture output");
}
