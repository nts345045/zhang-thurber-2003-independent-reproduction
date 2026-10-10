#!/usr/bin/env python3
"""Freeze a minimal candidate; no compiler, rays, or inverse execution."""
import difflib, hashlib, json, shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def replace(s,old,new):
    if s.count(old)!=1:raise RuntimeError('Expected exactly one source anchor: '+old[:100])
    return s.replace(old,new,1)

def main():
    for name in ('before','after','prepared.json'):
        if (HERE/name).exists():raise RuntimeError('Fresh candidate preparation required')
    original={}
    files=[ROOT/'CMakeLists.txt']+sorted((ROOT/'src').glob('*'))
    for old in files:
        if not old.is_file():continue
        name=old.relative_to(ROOT);original[str(name)]=sha(old)
        for variant in ('before','after'):
            new=HERE/variant/name;new.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(str(old),str(new))
    path=HERE/'after/src/main.cpp';s=path.read_text()
    s=replace(s,'void write_grid(const Grid &g, std::string path, int precision = 12) {',
'''// Failure evidence must be fully written before a trial can be rejected safely.
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
void write_grid(const Grid &g, std::string path, int precision = 12) {''')
    s=replace(s,"          << g.v[g.id(i, j, k)] << '\\n';\n}","          << g.v[g.id(i, j, k)] << '\\n';\n  finish_output(f, path);\n}")
    s=replace(s,"    csv_metadata_values(f, e[i].metadata);\n    f << '\\n';\n  }\n}","    csv_metadata_values(f, e[i].metadata);\n    f << '\\n';\n  }\n  finish_output(f, path);\n}")
    s=replace(s,'  out.close();\n  return {failures, first};','  finish_output(out, path);\n  return {failures, first};')
    s=replace(s,'void inversion_ray_gate(const std::string &prefix, const Grid &g,',
'''struct InverseRayRejection : std::runtime_error {
  bool only_local_stopping;
  InverseRayRejection(const std::string &message, bool only_local)
      : std::runtime_error(message), only_local_stopping(only_local) {}
};
void inversion_ray_gate(const std::string &prefix, const Grid &g,''')
    s=replace(s,'  out.close();\n  auto paths = output(prefix + "_ray_paths.csv");','  finish_output(out, prefix + "_ray_failures.csv");\n  auto paths = output(prefix + "_ray_paths.csv");')
    s=replace(s,'''  paths.close();
  throw std::runtime_error("Inverse forward evaluation rejected " + std::to_string(failed.size()) +
      " rays; see " + prefix + "_ray_status.csv; first: " +
      ray_identity_context(events, stations, failed.front().first / stations.size(),
                           failed.front().first % stations.size()));''',
'''  finish_output(paths, prefix + "_ray_paths.csv");
  const bool only_local = std::all_of(failed.begin(), failed.end(), [](const auto &failure) {
    return failure.second == "local_stopping_failed";
  });
  throw InverseRayRejection("Inverse forward evaluation rejected " + std::to_string(failed.size()) +
      " rays; see " + prefix + "_ray_status.csv; first: " +
      ray_identity_context(events, stations, failed.front().first / stations.size(),
                           failed.front().first % stations.size()), only_local);''')
    helper=(HERE/'solve_snapshot.inc').read_text()
    s=replace(s,'void invert(const Config &c, std::string dir, std::string mode) {',helper+'\nvoid invert(const Config &c, std::string dir, std::string mode) {')
    s=replace(s,'  int current_iteration = -1;\n  const auto checked_rays',
'''  int current_iteration = -1;
  const auto failure_prefix = [&](const std::string &phase, int trial) {
    return dir + "/" + mode + (phase == "line_search_trial" ?
        "_rejected_trial_it_" + std::to_string(current_iteration) + "_ls_" + std::to_string(trial) :
        "_failed_forward");
  };
  const auto checked_rays''')
    s=replace(s,'    const std::string prefix = dir + "/" + mode + "_failed_forward";','    const std::string prefix = failure_prefix(phase, trial);')
    s=replace(s,'      write_grid(g, dir + "/" + mode + "_last_accepted_grid.csv", 17);',
'''      write_grid(g, dir + "/" + mode + "_last_accepted_grid.csv", 17);
      if (phase == "line_search_trial") {
        write_events(accepted_sources, prefix + "_accepted_events.csv", 17);
        write_grid(g, prefix + "_accepted_grid.csv", 17);
      }''')
    s=replace(s,'              << \',\' << (auxiliary_spacing(c) > 0) << ",17," << csv_quote(error.what()) << \'\\n\';\n      throw;',
'''              << ',' << (auxiliary_spacing(c) > 0) << ",17," << csv_quote(error.what()) << '\\n';
      finish_output(context, prefix + "_context.csv");
      throw;''')
    s=replace(s,'''    bool accepted = false;
    for (int ls = 0; ls < 12; ls++, step *= 0.5) {''',
'''    bool accepted = false;
    int quality_rejections = 0, objective_evaluations = 0;
    const std::string solve_prefix = dir + "/" + mode + "_iteration_" + std::to_string(it) + "_solve";
    const std::string trials_path = dir + "/" + mode + "_iteration_" + std::to_string(it) + "_trials.csv";
    auto trials = output(trials_path);
    trials << std::setprecision(17) << "iteration,stage,trial,step_fraction,status,objective_evaluated,objective_before,objective_after,failure_prefix\\n";
    const auto record_trial = [&](int trial, const char *status, bool evaluated, const std::string &prefix = "") {
      trials << it << ',' << stage << ',' << trial << ',' << step << ',' << status << ',' << evaluated << ',' << before << ',';
      if (evaluated) trials << after;
      trials << ',' << csv_quote(prefix) << '\\n';
      trials.flush();
      if (!trials) throw std::runtime_error("Cannot finish trial record " + trials_path);
    };
    for (int ls = 0; ls < 12; ls++, step *= 0.5) {''')
    s=replace(s,'''      if (!valid)
        continue;
      auto nr = checked_rays(ng, ee, false, "line_search_trial", ls);
      after = objective(ng, ee, nr);
      if (after <= before) {
        accepted = true;
        break;
      }
    }
    double dv = 0, dx = 0;''',
'''      if (!valid) {
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
    double dv = 0, dx = 0;''')
    s=replace(s,'  if (failed.empty()) return;\n  auto identified_events = events;',
'''  if (failed.empty()) return;
  require_new_outputs(prefix, {"_ray_status.csv", "_ray_failures.csv", "_ray_paths.csv"});
  auto identified_events = events;''')
    s=replace(s,'    const std::string prefix = failure_prefix(phase, trial);\n    try {',
'''    const std::string prefix = failure_prefix(phase, trial);
    if (phase == "line_search_trial")
      require_new_outputs(prefix, {"_ray_status.csv", "_ray_failures.csv", "_ray_paths.csv",
          "_events.csv", "_grid.csv", "_context.csv", "_accepted_events.csv", "_accepted_grid.csv"});
    try {''')
    s=replace(s,'    auto trials = output(trials_path);','    require_new_outputs(trials_path, {""});\n    auto trials = output(trials_path);')
    s=replace(s,'    preflight.flush();','    preflight.flush();\n    if (!preflight) throw std::runtime_error("Cannot finish matrix preflight record");')
    s=replace(s,'    log.flush();','    log.flush();\n    if (!log) throw std::runtime_error("Cannot finish inverse history record");')
    path.write_text(s)
    before=(HERE/'before/src/main.cpp').read_text()
    (HERE/'candidate.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True),s.splitlines(True),fromfile='before/src/main.cpp',tofile='after/src/main.cpp')))
    assert all(sha(ROOT/n)==h for n,h in original.items())
    result={'status':'prepared_not_executed','scope':'isolated pure-local trial backtracking candidate; no maintained source or solver run', 'original_sha256':original,'output_sha256':{str(p.relative_to(HERE)):sha(p) for p in sorted(HERE.rglob('*')) if p.is_file()}}
    with (HERE/'prepared.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(sha(HERE/'prepared.json'))
if __name__=='__main__':main()
