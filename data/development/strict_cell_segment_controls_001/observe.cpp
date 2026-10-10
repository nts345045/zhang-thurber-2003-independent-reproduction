// Standalone invented comparison: frozen segment versus explicit-cell 8GL.
// Python supplies an exact rational partition and records each rounded handoff.
#include "source/src/core.hpp"
#include <cfenv>

void require_cell(bool ok,const char *message) {
  if(!ok) throw std::runtime_error(message);
}
double finite_cell(double x) {
  require_cell(std::isfinite(x),"Nonfinite explicit-cell arithmetic");return x;
}
double number(std::istream &in) {
  std::string token;require_cell(bool(in>>token),"Missing binary64 input");
  std::size_t used=0;const double x=std::stod(token,&used);
  require_cell(used==token.size(),"Invalid binary64 token");return finite_cell(x);
}
int integer(std::istream &in,int maximum) {
  int x=-1;require_cell(bool(in>>x) && x>=0 && x<=maximum,"Invalid bounded integer");return x;
}
Vec numbers(std::istream &in,int count) {
  Vec result;for(int i=0;i<count;++i)result.push_back(number(in));return result;
}
void emit(const char *name,const Vec &values,const std::array<bool,3> *blocked=nullptr) {
  std::cout<<'"'<<name<<"\":[";
  for(std::size_t i=0;i<values.size();++i) {
    if(i)std::cout<<',';
    if(blocked && (*blocked)[i%3])std::cout<<"null";
    else if(values[i]==0)std::cout<<(std::signbit(values[i])?"-0.0":"0.0");
    else std::cout<<std::setprecision(17)<<finite_cell(values[i]);
  }
  std::cout<<"],\""<<name<<"_hex\":[";
  for(std::size_t i=0;i<values.size();++i) {
    if(i)std::cout<<',';
    if(blocked && (*blocked)[i%3])std::cout<<"null";
    else {std::ostringstream value;value<<std::hexfloat<<values[i];std::cout<<'"'<<value.str()<<'"';}
  }
  std::cout<<']';
}
struct SampleInput {
  double shape[2],weight,basis[3][2];
};
struct PieceInput {
  int cell[3];double width;std::array<SampleInput,8> samples;
};
Grid::Sample explicit_sample(const Grid &g,const PieceInput &piece,const SampleInput &sample) {
  const Vec *axes[]={&g.x,&g.y,&g.z};double h[3];
  for(int k=0;k<3;++k) {
    h[k]=finite_cell((*axes[k])[piece.cell[k]+1]-(*axes[k])[piece.cell[k]]);
    require_cell(h[k]>0,"Nonpositive represented cell width");
  }
  Grid::Sample result;int n=0;
  for(int c=0;c<2;++c)for(int b=0;b<2;++b)for(int a=0;a<2;++a,++n) {
    result.ids[n]=g.id(piece.cell[0]+a,piece.cell[1]+b,piece.cell[2]+c);
    result.w[n]=finite_cell(sample.basis[0][a]*sample.basis[1][b]*sample.basis[2][c]);
    result.v=finite_cell(result.v+finite_cell(result.w[n]*g.v[result.ids[n]]));
  }
  // Retain the frozen sampler's paired nodal differences and summation order.
  // The cell never depends on a rounded global sample coordinate.
  for(int k=0;k<3;++k) {
    const int u=(k+1)%3,v=(k+2)%3;
    for(int a=0;a<2;++a)for(int b=0;b<2;++b) {
      int q[]={piece.cell[0],piece.cell[1],piece.cell[2]};q[u]+=a;q[v]+=b;
      const int lo=g.id(q[0],q[1],q[2]);++q[k];const int hi=g.id(q[0],q[1],q[2]);
      const double term=finite_cell(finite_cell((g.v[hi]-g.v[lo])/h[k])*sample.basis[u][a]*sample.basis[v][b]);
      result.grad[k]=finite_cell(result.grad[k]+term);
    }
  }
  require_cell(result.v>0,"Nonpositive sampled velocity");return result;
}
int main(int argc,char **argv) {
  try {
    require_cell(argc==2,"Use: observe INPUT");
    require_cell(std::numeric_limits<double>::is_iec559 && std::numeric_limits<double>::digits==53 &&
                 std::fegetround()==FE_TONEAREST,"Require nearest IEEE binary64");
    std::ifstream in(argv[1]);require_cell(bool(in),"Cannot open invented input");
    const int nx=integer(in,3),ny=integer(in,2),nz=integer(in,2),np=integer(in,2);
    require_cell(nx==3 && ny==2 && nz==2 && np>=1,"Outside finite invented roster");
    Grid g;g.x=numbers(in,nx);g.y=numbers(in,ny);g.z=numbers(in,nz);g.v=numbers(in,nx*ny*nz);
    const Vec *axes[]={&g.x,&g.y,&g.z};
    for(const auto axis:axes)for(std::size_t i=1;i<axis->size();++i)
      require_cell((*axis)[i-1]<(*axis)[i],"Nonincreasing grid");
    for(double v:g.v)require_cell(v>0,"Nonpositive nodal velocity");
    P a,b;for(auto &v:a)v=number(in);for(auto &v:b)v=number(in);
    require_cell(g.contains(a) && g.contains(b),"Endpoint outside physical box");
    std::array<bool,3> blocked{};int blocked_count=0;
    for(int k=0;k<3;++k) {
      blocked[k]=integer(in,1);bool actual=false;
      for(std::size_t i=1;i+1<axes[k]->size();++i)actual=actual || (a[k]==(*axes[k])[i] && b[k]==a[k]);
      require_cell(actual==blocked[k],"Incorrect aligned-normal availability");blocked_count+=blocked[k];
    }
    require_cell(blocked_count<=1,"Multiple aligned faces outside this roster");
    std::vector<PieceInput> pieces(np);
    for(auto &piece:pieces) {
      for(int k=0;k<3;++k)piece.cell[k]=integer(in,int(axes[k]->size())-2);
      piece.width=number(in);require_cell(piece.width>0,"Positive exact piece not representable");
      for(auto &sample:piece.samples) {
        for(double &s:sample.shape){s=number(in);require_cell(s>=0 && s<=1,"Invalid global endpoint shape");}
        sample.weight=number(in);require_cell(sample.weight>0,"Positive exact quadrature weight not representable");
        for(auto &axis:sample.basis)for(double &s:axis){s=number(in);require_cell(s>=0 && s<=1,"Invalid local basis weight");}
      }
    }
    std::string extra;require_cell(!(in>>extra),"Unexpected trailing input");
    const P d=b-a;for(double v:d)finite_cell(v);
    const double length=finite_cell(norm(d));require_cell(length>0,"Zero or underflowed total length");
    P old_a{},old_b{};const double old_action=finite_cell(segment(g,a,b,&old_a,&old_b));
    P ga{},gb{};double action=0;Vec sampled;
    for(const auto &piece:pieces)for(const auto &sample:piece.samples) {
      const auto s=explicit_sample(g,piece,sample);const double reciprocal=finite_cell(1/s.v);
      require_cell(reciprocal>0,"Positive reciprocal not representable");
      action=finite_cell(action+finite_cell(length*sample.weight*reciprocal));
      sampled.push_back(s.v);for(double v:s.grad)sampled.push_back(v);
      const P gs=s.grad*finite_cell(-reciprocal*reciprocal);for(double v:gs)finite_cell(v);
      for(int k=0;k<3;++k)if(!blocked[k]) {
        const double first=finite_cell(d[k]*(-reciprocal/length)+gs[k]*(length*sample.shape[0]));
        const double last=finite_cell(d[k]*(reciprocal/length)+gs[k]*(length*sample.shape[1]));
        ga[k]=finite_cell(ga[k]+finite_cell(first*sample.weight));
        gb[k]=finite_cell(gb[k]+finite_cell(last*sample.weight));
      }
    }
    Vec cuts{0,1};
    for(int k=0;k<3;++k)if(std::abs(d[k])>1e-12)for(double plane:*axes[k]) {
      const double u=(plane-a[k])/d[k];if(u>1e-10 && u<1-1e-10)cuts.push_back(u);
    }
    std::sort(cuts.begin(),cuts.end());
    std::cout<<"{\"invented_only\":true,";emit("delta",Vec(d.begin(),d.end()));std::cout<<',';
    emit("length",Vec{length});std::cout<<',';emit("old_action",Vec{old_action});std::cout<<',';
    emit("old_endpoint_gradient",Vec{old_a[0],old_a[1],old_a[2],old_b[0],old_b[1],old_b[2]});std::cout<<',';
    emit("strict_action",Vec{action});std::cout<<',';
    emit("strict_continuous_endpoint_gradient",Vec{ga[0],ga[1],ga[2],gb[0],gb[1],gb[2]},&blocked);std::cout<<',';
    emit("strict_sample_velocity_and_gradient",sampled);std::cout<<',';emit("reconstructed_old_cuts",cuts);
    std::cout<<",\"strict_pieces\":"<<np<<",\"strict_samples\":"<<8*np
             <<",\"old_segment_calls\":1,\"strict_edge_calls\":1,\"trace_calls\":0,\"field_calls\":0}\n";
    std::cout.flush();require_cell(bool(std::cout),"Output write failed");return 0;
  } catch(const std::exception &error) {std::cerr<<error.what()<<'\n';return 1;}
}
