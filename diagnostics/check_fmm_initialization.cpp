// Isolated first-arrival initialization audit. No production solver is changed.
#include "first_arrival_fmm.hpp"
#include "seeded_bending.hpp"
#include <chrono>

using Clock = std::chrono::steady_clock;
double elapsed(Clock::time_point start) {
  return std::chrono::duration<double>(Clock::now() - start).count();
}

Grid layered(bool flat_top) {
  Grid g;
  g.x = {-25, -20, -2, 0, 2, 20, 25};
  g.y = {-1, 1};
  g.z = {-1, 0, 4, 8, 12, 20};
  g.v.resize(g.size());
  for (int k = 0; k < int(g.z.size()); ++k)
    for (int j = 0; j < int(g.y.size()); ++j)
      for (int i = 0; i < int(g.x.size()); ++i)
        g.v[g.id(i,j,k)] = 4 + 0.2 * (flat_top ? std::max(0., g.z[k]) : g.z[k]);
  return g;
}

struct Reference { double time; P source; std::string branch; };
Reference flat_reference(double distance) {
  constexpr double v0 = 4, slope = .2, height = .5, B = v0/slope;
  Reference exact{distance/v0, {-1/v0, 0, 0}, "direct"};
  const double half = distance/2, disc = half*half - 4*height*B;
  if (disc >= 0)
    for (int sign : {-1, 1}) {
      const double q = (half + sign*std::sqrt(disc))/(2*B);
      const double s = std::sqrt(1+q*q);
      const double t = 2*(height*s/(v0*q) + std::asinh(q)/slope);
      if (t < exact.time) exact = {t, {-1/(v0*s), 0, -q/(v0*s)}, "diving"};
    }
  return exact;
}

struct Comparison {
  Ray direct, bent, best;
  first_arrival::Candidate seed;
  std::string selected;
  double seconds = 0;
};
Comparison compare(const Grid &g, const first_arrival::Field &field, P a, P b,
                   double spacing) {
  auto start = Clock::now();
  Comparison c;
  c.direct = trace(g, a, b, spacing, 1000);
  c.seed = field.candidate(a);
  c.best = c.direct;
  c.selected = "direct_seed";
  if (c.seed.success) {
    c.bent = bend_seed(g, c.seed.path, spacing, 1000);
    if (c.bent.time < c.best.time) {
      c.best = c.bent;
      c.selected = "fmm_seed";
    }
  }
  c.seconds = elapsed(start);
  return c;
}

void write_paths(std::ofstream &f, std::string name, double aux, double spacing,
                 double distance, const Comparison &c) {
  auto save = [&](std::string type, const std::vector<P> &path) {
    for (size_t i=0; i<path.size(); ++i)
      f << name << ',' << aux << ',' << spacing << ',' << distance << ','
        << type << ',' << i << ',' << path[i][0] << ',' << path[i][1] << ','
        << path[i][2] << '\n';
  };
  save("direct_bent", c.direct.path);
  if (c.seed.success) {
    save("fmm_raw", c.seed.path);
    save("fmm_bent", c.bent.path);
  }
}

void row(std::ofstream &f, std::string name, double aux, double spacing,
         double distance, size_t nodes, double field_seconds,
         const Grid &g, P a, P b, const Reference &ref, const Comparison &c) {
  double outside = 0, max_depth = a[2];
  for (auto p : c.best.path) {
    outside += !g.contains(p);
    max_depth = std::max(max_depth, p[2]);
  }
  const bool ok = c.seed.success;
  f << name << ',' << aux << ',' << spacing << ',' << distance << ',' << nodes
    << ',' << field_seconds << ',' << ok << ',' << c.seed.message << ','
    << c.seed.field_time << ',' << (ok ? path_eval(g,c.seed.path) : NAN) << ','
    << c.seed.descent_steps << ',' << c.seed.fallback_steps << ','
    << c.direct.time << ',' << c.direct.converged << ','
    << (ok ? c.bent.time : NAN) << ',' << (ok && c.bent.converged) << ','
    << (ok ? c.bent.gradient : NAN) << ',' << (ok ? c.bent.iterations : 0) << ','
    << c.selected << ',' << c.best.time << ',' << ref.time << ',' << ref.branch
    << ',' << c.best.time-ref.time << ',' << c.best.converged << ','
    << c.best.gradient << ',' << norm(c.best.source-ref.source) << ','
    << c.best.source[0] << ',' << c.best.source[1] << ',' << c.best.source[2]
    << ',' << ref.source[0] << ',' << ref.source[1] << ',' << ref.source[2]
    << ',' << max_depth << ',' << outside << ','
    << norm(c.best.path.front()-a)+norm(c.best.path.back()-b) << ',' << c.seconds
    << std::endl;
}

int main(int argc, char **argv) {
  if (argc < 2 || argc > 3 || (argc == 3 && std::string(argv[2]) != "refine"))
    throw std::runtime_error("Usage: check_fmm_initialization OUT_DIR [refine]");
  const bool refine = argc == 3;
  const Vec auxiliary = refine ? Vec{.125,.0625} : Vec{1.,.5,.25};
  const Vec path_spacing = refine ? Vec{.125,.0625} : Vec{.5,.25};
  const std::string out = argv[1];
  std::ofstream f(out+"/results.csv"), paths(out+"/paths.csv"), checks(out+"/consistency.csv");
  if (!f || !paths || !checks) throw std::runtime_error("Cannot open audit files");
  f << std::setprecision(15);
  paths << std::setprecision(15);
  checks << std::setprecision(15);
  f << "case,auxiliary_spacing_km,path_spacing_km,distance_km,field_nodes,field_seconds,"
       "extracted,extraction_message,field_time_s,seed_action_s,descent_steps,fallback_steps,"
       "direct_bent_time_s,direct_converged,fmm_bent_time_s,fmm_converged,fmm_gradient,fmm_updates,"
       "selected,best_time_s,reference_time_s,reference_branch,time_error_s,converged,gradient,"
       "source_error_s_per_km,source_dx,source_dy,source_dz,reference_dx,reference_dy,reference_dz,"
       "maximum_depth_km,outside_nodes,endpoint_error_km,ray_seconds\n";
  paths << "case,auxiliary_spacing_km,path_spacing_km,distance_km,path,node,x,y,z\n";
  checks << "case,auxiliary_spacing_km,path_spacing_km,test,value,tolerance,passed\n";
  auto check = [&](std::string name, double aux, double spacing, std::string test,
                   double value, double tol) {
    checks << name << ',' << aux << ',' << spacing << ',' << test << ','
           << value << ',' << tol << ',' << (std::isfinite(value) && value<=tol) << std::endl;
  };

  for (bool flat : {true, false}) {
    const Grid g = layered(flat);
    const P b{20, .13, flat ? -.5 : 0.};
    const std::string name = flat ? "constant_top_gradient" : "constant_gradient";
    const Vec distances = flat ? Vec{4,12,14,14.64,14.68,15,16,20,40} : Vec{10,40};
    for (double aux : auxiliary) {
      auto start = Clock::now();
      const first_arrival::Field field(g,b,aux);
      const double field_seconds = elapsed(start);
      for (double spacing : path_spacing)
        for (double distance : distances) {
          const P a{b[0]-distance,b[1],b[2]};
          const double B=20, radius=std::sqrt(B*B+distance*distance/4);
          const Reference ref = flat ? flat_reference(distance) :
            Reference{10*std::asinh(distance/40), {-B/(4*radius),0,-distance/(8*radius)}, "diving"};
          const auto c = compare(g,field,a,b,spacing);
          row(f,name,aux,spacing,distance,field.node_count(),field_seconds,g,a,b,ref,c);
          if (aux==auxiliary.back() && spacing==path_spacing.back()) {
            write_paths(paths,name,aux,spacing,distance,c);
            // Existing analytic-ray tolerances retained. Layer-interface cases
            // may expose additional failures; do not weaken these gates.
            const auto label = name+"_"+std::to_string(distance);
            check(label,aux,spacing,"exact_time",std::abs(c.best.time-ref.time),2.5e-5);
            check(label,aux,spacing,"exact_source_derivative",norm(c.best.source-ref.source),3e-6);
            check(label,aux,spacing,"converged",c.best.converged ? 0 : 1,0);
            if (flat && (distance==20 || distance==40)) {
              const first_arrival::Field reverse_field(g,a,aux);
              const auto reversed = compare(g,reverse_field,b,a,spacing);
              check(label,aux,spacing,"reciprocity",std::abs(c.best.time-reversed.best.time),2e-5);
              double fd_error = 0;
              for (int axis=0; axis<3; ++axis) {
                P plus=a,minus=a;
                plus[axis]+=.01; minus[axis]-=.01;
                const auto cp=compare(g,field,plus,b,spacing), cm=compare(g,field,minus,b,spacing);
                const double fd=(cp.best.time-cm.best.time)/.02;
                fd_error=std::max(fd_error,std::abs(fd-c.best.source[axis]));
              }
              check(label,aux,spacing,"source_finite_difference",fd_error,.003);
            }
          }
        }
    }
  }

  if (refine) return 0; // Off-grid homogeneous checks are in the baseline audit.
  Grid homogeneous;
  homogeneous.x={-10,0,10}; homogeneous.y={-8,0,8}; homogeneous.z={-1,0,15};
  homogeneous.v.assign(homogeneous.size(),6);
  const std::vector<std::pair<P,P>> endpoints={
    {{-7.31,3.21,8.17},{8.27,-5.41,-.33}},
    {{-10,7.93,-1},{10,-7.87,14.93}},
    {{-.1,.3,.7},{.7,-.2,1.9}}};
  int n=0;
  for (auto pair:endpoints) {
    const auto a=pair.first,b=pair.second;
    const std::string name="homogeneous_"+std::to_string(n++);
    for (double aux : {.5,.25}) {
      auto start=Clock::now();
      const first_arrival::Field field(homogeneous,b,aux);
      const double field_seconds=elapsed(start),distance=norm(b-a);
      const auto c=compare(homogeneous,field,a,b,.25);
      const Reference ref{distance/6,(a-b)*(1/(6*distance)),"direct"};
      row(f,name,aux,.25,distance,field.node_count(),field_seconds,homogeneous,a,b,ref,c);
      check(name,aux,.25,"exact_time",std::abs(c.best.time-ref.time),1e-10);
      check(name,aux,.25,"exact_source_derivative",norm(c.best.source-ref.source),1e-9);
      check(name,aux,.25,"extracted",c.seed.success ? 0 : 1,0);
      if (c.seed.success)
        check(name,aux,.25,"seed_not_faster_than_exact",std::max(0.,ref.time-path_eval(homogeneous,c.seed.path)),1e-10);
    }
  }
}
