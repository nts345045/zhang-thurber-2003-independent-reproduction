// One diagnostic principal-metric solve, or one binary64 trial construction.
// Includes frozen core arithmetic, but calls no trace, field or optimizer.
#include "core.hpp"
#include <cfenv>
#include <cstdlib>

void require_step(bool ok, const char *message) {
  if (!ok) throw std::runtime_error(message);
}
double scalar(std::istream &in) {
  std::string token; in >> token;
  char *end=nullptr;
  double value=std::strtod(token.c_str(), &end);
  require_step(in && !token.empty() && end==token.c_str()+token.size() &&
               std::isfinite(value), "Invalid finite binary64 token");
  return value;
}
std::size_t count(std::istream &in) {
  std::string token; in >> token;
  require_step(in && !token.empty() && token.find_first_not_of("0123456789")==std::string::npos,
               "Invalid count");
  return std::stoull(token);
}
Vec values(std::istream &in, std::size_t n) {
  Vec result(n); for (double &x:result) x=scalar(in); return result;
}
std::vector<P> points(std::istream &in, std::size_t n) {
  std::vector<P> result(n);
  for (P &p:result) for (double &x:p) x=scalar(in);
  return result;
}
void finite(double value, const char *message) {
  require_step(std::isfinite(value),message);
}
void array_json(const Vec &v) {
  std::cout << '[';
  for (std::size_t i=0;i<v.size();++i) {
    if(i)std::cout<<',';
    if(v[i]==0)std::cout<<(std::signbit(v[i])?"-0.0":"0.0");
    else std::cout<<v[i];
  }
  std::cout << ']';
}
void hex_json(const Vec &v) {
  std::cout << '[';
  for(std::size_t i=0;i<v.size();++i) {
    if(i)std::cout<<',';
    std::cout << '"' << std::hexfloat << v[i] << std::defaultfloat << '"';
  }
  std::cout << ']';
}
Vec flatten(const std::vector<P> &p) {
  Vec result;for(const P &q:p)for(double x:q)result.push_back(x);return result;
}

void solve_record(const Vec &weights, const Vec &gradient, const std::vector<bool> &fixed) {
  require_step(weights.size()>=2 && gradient.size()==3*(weights.size()-1) &&
               fixed.size()==gradient.size(),"Invalid metric dimensions");
  for(double w:weights)require_step(w>0 && std::isfinite(w),"Invalid positive metric weight");
  for(double g:gradient)finite(g,"Nonfinite metric RHS");
  const std::size_t n=weights.size()-1;
  Vec pivots(3*n),forward_rhs(3*n);
  // Audit the exact original forward-elimination expressions before calling
  // the unchanged solve. Fixed slots retain their incident-edge stiffness in
  // neighboring free diagonals; they do not remove those edges.
  for(int axis=0;axis<3;++axis)for(std::size_t i=0;i<n;++i) {
    const std::size_t k=3*i+axis;
    double diagonal=fixed[k]?1:weights[i]+weights[i+1];
    double rhs=fixed[k]?0:-gradient[k];
    finite(diagonal,"Nonfinite principal diagonal");
    if(i && !fixed[k] && !fixed[k-3]) {
      double ratio=-weights[i]/pivots[k-3];
      double pivot_term=ratio*(-weights[i]),rhs_term=ratio*forward_rhs[k-3];
      finite(ratio,"Nonfinite elimination ratio");
      finite(pivot_term,"Nonfinite pivot product");finite(rhs_term,"Nonfinite RHS product");
      diagonal-=pivot_term;rhs-=rhs_term;
    }
    require_step(diagonal>0 && std::isfinite(diagonal),"Nonpositive or nonfinite principal pivot");
    finite(rhs,"Nonfinite eliminated RHS");
    pivots[k]=diagonal;forward_rhs[k]=rhs;
  }
  const Vec direction=solve_free_ray_metric(weights,gradient,fixed);
  for(std::size_t k=0;k<direction.size();++k) {
    finite(direction[k],"Nonfinite principal solution");
    require_step(!fixed[k] || direction[k]==0,"Fixed slot moved");
  }
  Vec residual(3*n),product(3*n);double slope=0,quadratic=0;
  for(std::size_t i=0;i<n;++i)for(int axis=0;axis<3;++axis) {
    const std::size_t k=3*i+axis;
    double v=(weights[i]+weights[i+1])*direction[k];finite(v,"Nonfinite metric product");
    if(i) {double a=weights[i]*direction[k-3];finite(a,"Nonfinite left product");v-=a;finite(v,"Nonfinite partial product");}
    if(i+1<n) {double a=weights[i+1]*direction[k+3];finite(a,"Nonfinite right product");v-=a;finite(v,"Nonfinite product");}
    product[k]=v;residual[k]=v+gradient[k];finite(residual[k],"Nonfinite residual");
    double term=gradient[k]*direction[k];finite(term,"Nonfinite slope term");slope+=term;finite(slope,"Nonfinite slope sum");
  }
  for(std::size_t edge=0;edge<weights.size();++edge)for(int axis=0;axis<3;++axis) {
    double left=edge?direction[3*(edge-1)+axis]:0;
    double right=edge<n?direction[3*edge+axis]:0;
    double delta=right-left;finite(delta,"Nonfinite edge direction");
    double term=weights[edge]*delta;finite(term,"Nonfinite weighted edge direction");
    term*=delta;finite(term,"Nonfinite quadratic term");quadratic+=term;finite(quadratic,"Nonfinite quadratic sum");
  }
  std::cout << "{\"weights\":";array_json(weights);
  std::cout << ",\"pivots\":";array_json(pivots);
  std::cout << ",\"forward_rhs\":";array_json(forward_rhs);
  std::cout << ",\"direction\":";array_json(direction);
  std::cout << ",\"direction_hex\":";hex_json(direction);
  std::cout << ",\"product\":";array_json(product);
  std::cout << ",\"residual_all_slots\":";array_json(residual);
  std::cout << ",\"slope_binary64\":" << slope << ",\"quadratic_binary64\":" << quadratic
            << ",\"interpretation\":\"Numerical metric only; residuals do not certify a Fermat slope.\"}\n";
}

int main(int argc,char **argv) {
  try {
    require_step(argc==3,"Use: metric_step solve|weights|round INPUT");
    require_step(std::numeric_limits<double>::is_iec559 && std::numeric_limits<double>::digits==53 &&
                 std::fegetround()==FE_TONEAREST,"Require nearest-rounding IEEE binary64");
    std::ifstream in(argv[2]);require_step(bool(in),"Cannot open input");
    std::cout << std::setprecision(17);
    std::string mode=argv[1];
    if(mode=="round") {
      const std::size_t n=count(in);require_step(n>=3,"Too few path points");
      double alpha=scalar(in);require_step(alpha>0 && alpha<=1,"Invalid positive bounded step");
      auto path=points(in,n),direction=points(in,n),trial=path;
      require_step(direction.front()==P{0,0,0} && direction.back()==P{0,0,0},"Endpoint direction is not zero");
      for(std::size_t i=1;i+1<n;++i) {
        // Compile without contraction: exactly the original P multiply then add.
        trial[i]=path[i]+direction[i]*alpha;
        for(double x:trial[i])finite(x,"Nonfinite rounded trial coordinate");
      }
      std::cout << "{\"trial\":";array_json(flatten(trial));
      std::cout << ",\"trial_hex\":";hex_json(flatten(trial));std::cout << "}\n";
    } else {
      Vec weights;
      if(mode=="solve") {
        Grid grid;
        std::size_t nx=count(in),ny=count(in),nz=count(in),n=count(in);
        require_step(nx>=2 && ny>=2 && nz>=2 && n>=3,"Incomplete metric grid/path");
        grid.x=values(in,nx);grid.y=values(in,ny);grid.z=values(in,nz);
        for(const Vec *axis:{&grid.x,&grid.y,&grid.z})
          for(std::size_t j=1;j<axis->size();++j)require_step((*axis)[j]>(*axis)[j-1],"Nonincreasing grid axis");
        grid.v=values(in,nx*ny*nz);for(double v:grid.v)require_step(v>0,"Nonpositive grid velocity");
        auto path=points(in,n);
        for(const P &p:path)require_step(grid.contains(p),"Metric path outside physical box");
        for(std::size_t j=1;j<n;++j)require_step(norm(path[j]-path[j-1])>0,"Zero or underflowed metric edge");
        weights=ray_metric_weights(grid,path);
      } else {
        require_step(mode=="weights","Unknown metric mode");
        std::size_t n=count(in);require_step(n>=2,"Too few weights");weights=values(in,n);
      }
      Vec gradient=values(in,3*(weights.size()-1));std::vector<bool> fixed(gradient.size());
      for(std::size_t k=0;k<fixed.size();++k) {std::size_t f=count(in);require_step(f<=1,"Invalid fixed-slot bit");fixed[k]=f;}
      solve_record(weights,gradient,fixed);
    }
    std::string extra;require_step(!(in>>extra),"Unexpected trailing input");
    std::cout.flush();require_step(bool(std::cout),"Metric/trial output write failed");
    return 0;
  } catch(const std::exception &error) {std::cerr << error.what() << '\n';return 1;}
}
