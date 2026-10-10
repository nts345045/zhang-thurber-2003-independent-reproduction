// Evaluate the eight declared saved polygons with the unchanged production
// segment/path_eval functions. No trace, field, resampling or optimizer call.
#include "source/core.hpp"
#include <chrono>
#include <cerrno>
#include <sys/stat.h>

void require(bool ok, const std::string &message) {
  if (!ok) throw std::runtime_error(message);
}
double number(std::istream &in) {
  std::string token; require(bool(in >> token), "Missing binary64 input");
  size_t used = 0; const double value = std::stod(token, &used);
  require(used == token.size() && std::isfinite(value), "Invalid binary64 input");
  return value;
}
void end(std::istream &in) {
  std::string extra; require(!(in >> extra) && in.eof(), "Trailing input");
}
template<class T> std::string hexadecimal(T value) {
  std::ostringstream out; out << std::hexfloat << value; return out.str();
}
template<class T> void value(std::ostream &out, T x) {
  require(std::isfinite(x), "Nonfinite result");
  out << ',' << std::setprecision(std::numeric_limits<T>::max_digits10) << x
      << ',' << hexadecimal(x);
}
bool exists(const std::string &name) {
  struct stat info;
  if (lstat(name.c_str(), &info) == 0) return true;
  require(errno == ENOENT, "Cannot inspect output: " + name); return false;
}
std::ofstream output(const std::string &name) {
  require(!exists(name), "Prior output: " + name);
  std::ofstream out(name); require(bool(out), "Cannot create output: " + name); return out;
}
void close(std::ofstream &out) {
  out.flush(); out.close(); require(bool(out), "Output flush/close failed");
}
Grid model(const std::string &name) {
  std::ifstream in(name); require(bool(in), "Missing model");
  int nx = 0, ny = 0, nz = 0; in >> nx >> ny >> nz;
  require(nx >= 2 && ny >= 2 && nz >= 2 && nx * ny * nz == 462, "Model dimensions");
  Grid g; g.x.resize(nx); g.y.resize(ny); g.z.resize(nz); g.v.resize(g.size());
  for (Vec *axis : {&g.x, &g.y, &g.z}) {
    for (double &x : *axis) x = number(in);
    for (size_t i = 1; i < axis->size(); ++i) require((*axis)[i] > (*axis)[i-1], "Model axis order");
  }
  for (double &v : g.v) { v = number(in); require(v > 0, "Nonpositive model velocity"); }
  end(in); return g;
}
std::vector<P> points(const std::string &name, int event, int stage, const Grid &g) {
  std::ifstream in(name); require(bool(in), "Missing polygon");
  int e = 0, station = 0, s = 0, count = 0; in >> e >> station >> s >> count;
  require(e == event && station == 160 && s == stage && count == (event == 981 ? 1029 : 1031), "Polygon identity/topology");
  std::vector<P> result(count);
  for (size_t i = 0; i < result.size(); ++i) {
    for (double &x : result[i]) x = number(in);
    require(g.contains(result[i]) && (i == 0 || result[i] != result[i-1]), "Invalid saved polygon");
  }
  end(in); return result;
}
Vec direction(const std::string &name, int event, size_t n) {
  std::ifstream in(name); require(bool(in), "Missing saved direction");
  int e = 0, station = 0; size_t count = 0; in >> e >> station >> count;
  require(e == event && station == 160 && count == n, "Direction identity/topology");
  Vec result;
  for (size_t i = 0; i < n; ++i) for (int k = 0; k < 3; ++k) {
    const double x = number(in);
    if (i == 0 || i + 1 == n) require(x == 0, "Fixed endpoint direction");
    else result.push_back(x);
  }
  end(in); return result;
}
struct Result { double action; Vec edges, gradient; std::vector<P> path; };
int main(int argc, char **argv) {
  try {
    require(argc == 4, "Expected GRID INPUT_DIRECTORY OUTPUT_DIRECTORY");
    require(std::numeric_limits<long double>::digits > std::numeric_limits<double>::digits, "Extended accumulator unavailable");
    const Grid g = model(argv[1]); const std::string input = argv[2], out = argv[3];
    for (const auto &name : {"totals.csv", "edges.csv", "gradients.csv", "pairs.csv"})
      require(!exists(out + "/" + name), "Refuse existing output");
    auto totals = output(out + "/totals.csv"), edges = output(out + "/edges.csv"),
         gradients = output(out + "/gradients.csv"), pairs = output(out + "/pairs.csv");
    totals << "event,station,stage,nodes,action,action_hex,ordinary_sum,ordinary_sum_hex,extended_sum,extended_sum_hex,path_eval_microseconds,edge_check_microseconds\n";
    edges << "event,station,stage,edge,action,action_hex\n";
    gradients << "event,station,stage,node,axis,component,component_hex\n";
    pairs << "event,station,base_stage,trial_stage,alpha,paired,paired_hex,outer_change,outer_change_hex,slope,slope_hex,extended_slope,extended_slope_hex,extended_armijo_rhs,extended_armijo_rhs_hex,paired_armijo\n";
    const char *names[] = {"face", "first", "second", "half"};
    size_t path_calls = 0, checked_edges = 0;
    for (int event : {981, 987}) {
      std::vector<Result> all;
      for (int stage = 0; stage < 4; ++stage) {
        Result r; r.path = points(input + "/" + std::to_string(event) + "_" + names[stage] + ".txt", event, stage, g);
        if (stage) require(r.path.front() == all[0].path.front() && r.path.back() == all[0].path.back(), "Changed endpoints");
        const auto start = std::chrono::steady_clock::now();
        r.action = path_eval(g, r.path, &r.gradient); ++path_calls;
        const auto middle = std::chrono::steady_clock::now();
        double ordinary = 0; long double extended = 0;
        for (size_t i = 0; i + 1 < r.path.size(); ++i) {
          const double t = segment(g, r.path[i], r.path[i+1]);
          require(std::isfinite(t) && t > 0, "Nonpositive/nonfinite edge action");
          r.edges.push_back(t); ordinary += t; extended += t; ++checked_edges;
          edges << event << ",160," << stage << ',' << i; value(edges, t); edges << '\n';
        }
        const auto finish = std::chrono::steady_clock::now();
        require(r.action == static_cast<double>(extended), "Actual path_eval/extended edge-sum parity");
        totals << event << ",160," << stage << ',' << r.path.size();
        value(totals, r.action); value(totals, ordinary); value(totals, extended);
        totals << ',' << std::chrono::duration<double, std::micro>(middle-start).count()
               << ',' << std::chrono::duration<double, std::micro>(finish-middle).count() << '\n';
        for (size_t i = 1; i + 1 < r.path.size(); ++i) for (int k = 0; k < 3; ++k) {
          gradients << event << ",160," << stage << ',' << i << ',' << k;
          value(gradients, r.gradient[3*(i-1)+k]); gradients << '\n';
        }
        all.push_back(std::move(r));
      }
      const Vec q = direction(input + "/" + std::to_string(event) + "_direction.txt", event, all[1].path.size());
      const double slope = dot(all[1].gradient, q);
      long double extended_slope = 0;
      for (size_t i = 0; i < q.size(); ++i)
        extended_slope += static_cast<long double>(all[1].gradient[i]) * static_cast<long double>(q[i]);
      for (int stage : {2, 3}) {
        long double paired = 0;
        for (size_t i = 0; i < all[1].edges.size(); ++i)
          paired += static_cast<long double>(all[stage].edges[i]) - static_cast<long double>(all[1].edges[i]);
        const double alpha = stage == 2 ? 1.0 : 0.5;
        const long double rhs = static_cast<long double>(1e-4) * alpha * slope;
        pairs << event << ",160,1," << stage << ',' << alpha;
        value(pairs, paired); value(pairs, all[stage].action - all[1].action);
        value(pairs, slope); value(pairs, extended_slope); value(pairs, rhs);
        pairs << ',' << (slope < 0 && paired <= rhs) << '\n';
      }
    }
    require(path_calls == 8 && checked_edges == 8232, "Fixed evaluation inventory");
    close(totals); close(edges); close(gradients); close(pairs);
    std::cout << "path_eval_calls=8 extra_segment_calls=8232 trace_calls=0 field_calls=0 optimizer_calls=0 double_digits="
              << std::numeric_limits<double>::digits << " long_double_digits=" << std::numeric_limits<long double>::digits << '\n';
    std::cout.flush(); require(bool(std::cout), "Terminal inventory flush failed");
    return 0;
  } catch (const std::exception &error) { std::cerr << error.what() << '\n'; return 1; }
}
