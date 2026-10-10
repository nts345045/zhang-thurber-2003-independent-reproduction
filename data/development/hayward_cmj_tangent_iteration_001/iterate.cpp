// Restricted tangent iteration on two saved polygons. This is not trace().
// Compile with -ffp-contract=off; original false/null statuses never change.
#include "source/core.hpp"
#include <cerrno>
#include <cfenv>
#include <sys/stat.h>

void require(bool ok, const std::string &message) {
  if (!ok) throw std::runtime_error(message);
}
double number(std::istream &in) {
  std::string token; require(bool(in >> token), "Missing binary64 input");
  size_t used=0; double x=std::stod(token,&used);
  require(used==token.size() && std::isfinite(x), "Invalid binary64 input"); return x;
}
void end(std::istream &in) {
  std::string extra; require(!(in >> extra) && in.eof(), "Trailing input");
}
template<class T> void value(std::ostream &out,T x) {
  require(std::isfinite(x), "Nonfinite recorded value");
  out << ',' << std::setprecision(std::numeric_limits<T>::max_digits10);
  if(x==0) out << (std::signbit(x)?"-0.0":"0.0"); else out << x;
  out << ',' << std::hexfloat << x << std::defaultfloat;
}
template<class T> void optional(std::ostream &out,T x,bool present) {
  if(present)value(out,x);else out << ",,";
}
std::ofstream output(const std::string &name) {
  struct stat s; const int result=lstat(name.c_str(),&s);
  require(result!=0 && errno==ENOENT,"Refuse existing or inaccessible output: "+name);
  std::ofstream out(name); require(bool(out),"Cannot create output: "+name);return out;
}
Grid model(const std::string &name) {
  std::ifstream in(name);require(bool(in),"Missing model");int nx=0,ny=0,nz=0;in>>nx>>ny>>nz;
  require(nx>=2 && ny>=2 && nz>=2 && nx<=462 && ny<=462 && nz<=462 && nx*ny*nz==462,"Grid dimensions");
  Grid g;g.x.resize(nx);g.y.resize(ny);g.z.resize(nz);g.v.resize(g.size());
  for(Vec *axis:{&g.x,&g.y,&g.z}) {
    for(double &x:*axis)x=number(in);
    for(size_t i=1;i<axis->size();++i)require((*axis)[i]>(*axis)[i-1],"Grid axis order");
  }
  for(double &v:g.v){v=number(in);require(v>0,"Positive grid velocity");}
  end(in);return g;
}
std::vector<P> points(const std::string &name,int event) {
  std::ifstream in(name);require(bool(in),"Missing saved half polygon");int e=0,s=0,stage=0,n=0;in>>e>>s>>stage>>n;
  require(e==event && s==160 && stage==3 && n==(event==981?1029:1031),"Saved half identity/topology");
  std::vector<P> p(n);for(P &x:p)for(double &v:x)v=number(in);end(in);return p;
}
std::vector<bool> availability(const Grid &g,const std::vector<P> &p,bool &multiple) {
  std::vector<bool> fixed(3*(p.size()-2));multiple=false;const Vec *axes[]={&g.x,&g.y,&g.z};
  for(size_t edge=0;edge+1<p.size();++edge) {
    int faces=0;
    for(int k=0;k<3;++k)if(p[edge][k]==p[edge+1][k] &&
        std::find(axes[k]->begin()+1,axes[k]->end()-1,p[edge][k])!=axes[k]->end()-1) {
      ++faces;
      for(size_t node:{edge,edge+1})if(node && node+1<p.size())fixed[3*(node-1)+k]=true;
    }
    multiple=multiple || faces>1;
  }
  return fixed;
}
std::string geometry_event(const Grid &g,const std::vector<P> &p,const std::vector<bool> &fixed) {
  const Vec *axes[]={&g.x,&g.y,&g.z};
  for(size_t i=0;i<p.size();++i) {
    for(double x:p[i])if(!std::isfinite(x))return "nonfinite_geometry";
    if(!g.contains(p[i]))return "physical_box_event";
    if(i && i+1<p.size())for(int k=0;k<3;++k)
      if(p[i][k]==axes[k]->front() || p[i][k]==axes[k]->back())return "physical_box_event";
    if(i) {
      const double length=norm(p[i]-p[i-1]);
      if(!std::isfinite(length))return "nonfinite_length";
      if(length==0)return "zero_edge_event";
      if(length<1e-12)return "existing_segment_cutoff_event";
    }
  }
  bool multiple=false;auto actual=availability(g,p,multiple);
  if(multiple)return "multiple_aligned_faces_event";
  if(actual!=fixed)return "availability_event";
  return "";
}
double available_norm(const Vec &gradient,const std::vector<bool> &fixed) {
  require(gradient.size()==fixed.size(),"Gradient dimensions");Vec free=gradient;
  for(size_t k=0;k<free.size();++k){require(std::isfinite(free[k]),"Finite gradient");if(fixed[k])free[k]=0;}
  const double r=norm(free);require(std::isfinite(r),"Finite available norm");return r;
}
Vec direction(const Grid &g,const std::vector<P> &p,const Vec &gradient,const std::vector<bool> &fixed) {
  const Vec weights=ray_metric_weights(g,p);const size_t n=p.size()-2;
  require(weights.size()==n+1 && gradient.size()==3*n && fixed.size()==3*n,"Principal dimensions");
  for(double w:weights)require(std::isfinite(w) && w>0,"Positive finite metric weights");
  Vec pivots(3*n),rhs(3*n);
  // Same checked elimination expressions as the reviewed one-step helper.
  // The principal block retains both incident weights in every free diagonal.
  for(int axis=0;axis<3;++axis)for(size_t i=0;i<n;++i) {
    const size_t k=3*i+axis;double d=fixed[k]?1:weights[i]+weights[i+1],r=fixed[k]?0:-gradient[k];
    require(std::isfinite(d) && std::isfinite(r),"Finite principal system");
    if(i && !fixed[k] && !fixed[k-3]) {
      const double ratio=-weights[i]/pivots[k-3],a=ratio*(-weights[i]),b=ratio*rhs[k-3];
      require(std::isfinite(ratio) && std::isfinite(a) && std::isfinite(b),"Finite elimination products");d-=a;r-=b;
    }
    require(d>0 && std::isfinite(d) && std::isfinite(r),"Usable principal pivot/RHS");pivots[k]=d;rhs[k]=r;
  }
  Vec q=solve_free_ray_metric(weights,gradient,fixed);
  for(size_t k=0;k<q.size();++k)require(std::isfinite(q[k]) && (!fixed[k] || q[k]==0),"Finite direction/fixed search normal");
  return q;
}
Vec edge_values(const Grid &g,const std::vector<P> &p,size_t &calls) {
  Vec values;values.reserve(p.size()-1);
  for(size_t i=1;i<p.size();++i) {
    const double t=segment(g,p[i-1],p[i]);++calls;
    require(std::isfinite(t) && t>0,"Positive finite core segment action");values.push_back(t);
  }
  return values;
}
double total(const Vec &edges) {
  long double s=0;for(double t:edges)s+=t;
  require(std::isfinite(s) && std::isfinite(static_cast<double>(s)),"Finite extended total");return static_cast<double>(s);
}
void arrays(int event,const char *state,const std::vector<P> &p,const Vec &g,const Vec &edges,
            const std::vector<bool> &fixed,std::vector<std::ofstream> &out) {
  for(size_t i=0;i<p.size();++i) {
    out[4]<<event<<",160,"<<state<<','<<i;for(double x:p[i])value(out[4],x);out[4]<<'\n';
    if(i && i+1<p.size())for(int k=0;k<3;++k) {
      out[5]<<event<<",160,"<<state<<','<<i<<','<<k<<','<<!fixed[3*(i-1)+k];value(out[5],g[3*(i-1)+k]);out[5]<<'\n';
    }
  }
  for(size_t e=0;e<edges.size();++e){out[6]<<event<<",160,"<<state<<','<<e;value(out[6],edges[e]);out[6]<<'\n';}
}
void iterate(const Grid &g,int event,const std::string &input,std::vector<std::ofstream> &out) {
  auto p=points(input+"/"+std::to_string(event)+"_half.txt",event);const P source=p.front(),receiver=p.back();
  bool multiple=false;const auto fixed=availability(g,p,multiple);
  require(!multiple && geometry_event(g,p,fixed).empty(),"Eligible initial half-step geometry required");
  size_t path_calls=0,segment_calls=0,trials=0,updates=0,metric_calls=0;Vec gradient;
  double T=path_eval(g,p,&gradient);++path_calls;Vec edges=edge_values(g,p,segment_calls);
  require(std::isfinite(T) && T==total(edges),"Initial actual core/cached-edge total parity");
  arrays(event,"initial",p,gradient,edges,fixed,out);
  auto update_record=[&](double step,bool accepted){
    out[1]<<event<<",160,"<<updates;optional(out[1],step,accepted);value(out[1],T);
    value(out[1],available_norm(gradient,fixed));value(out[1],norm(gradient));out[1]<<'\n';
  };
  update_record(0,false);std::string stop;
  while(true) {
    if(available_norm(gradient,fixed)<=1e-7){stop="diagnostic_available_norm_reached";break;}
    if(updates==1000){stop="update_budget";break;}
    const Vec q=direction(g,p,gradient,fixed);++metric_calls;const double slope=dot(gradient,q);
    require(std::isfinite(slope) && slope<0,"Finite strict nominal descent");
    for(size_t i=1;i+1<p.size();++i){out[3]<<event<<",160,"<<updates<<','<<i;for(int k=0;k<3;++k)value(out[3],q[3*(i-1)+k]);out[3]<<'\n';}
    double step=1;const Vec *axes[]={&g.x,&g.y,&g.z};
    for(size_t i=1;i+1<p.size();++i)for(int k=0;k<3;++k) {
      const double d=q[3*(i-1)+k];
      if(d>0)step=std::min(step,(axes[k]->back()-p[i][k])/d);
      if(d<0)step=std::min(step,(axes[k]->front()-p[i][k])/d);
    }
    if(!(step>0) || !std::isfinite(step)){stop="physical_box_step_event";break;}
    bool accepted=false;
    for(int attempt=0;attempt<24;++attempt,step*=0.5) {
      ++trials;auto trial=p;
      for(size_t i=1;i+1<p.size();++i)for(int k=0;k<3;++k)
        if(!fixed[3*(i-1)+k])trial[i][k]+=step*q[3*(i-1)+k];
      require(trial.front()==source && trial.back()==receiver,"Fixed endpoints");
      std::string reason=geometry_event(g,trial,fixed);const bool noop=trial==p;
      if(reason.empty() && noop)reason="rounded_no_op";
      long double actual=0;const bool actual_evaluated=reason!="nonfinite_geometry";
      if(actual_evaluated)for(size_t i=1;i+1<p.size();++i)for(int k=0;k<3;++k)
        actual+=static_cast<long double>(gradient[3*(i-1)+k])*(static_cast<long double>(trial[i][k])-static_cast<long double>(p[i][k]));
      require(std::isfinite(actual),"Finite actual rounded-displacement slope");
      const bool actual_descent=actual_evaluated && actual<0;
      long double paired=0,rhs=static_cast<long double>(1e-4)*step*slope;double newT=0,outer_change=0;Vec trial_edges;
      require(std::isfinite(rhs),"Finite Armijo RHS");bool evaluated=false,ordinary_armijo=false;
      if(reason.empty() && !actual_descent)reason="rounded_non_descent";
      if(reason.empty()) {
        trial_edges=edge_values(g,trial,segment_calls);evaluated=true;newT=total(trial_edges);outer_change=newT-T;
        for(size_t e=0;e<edges.size();++e)paired+=static_cast<long double>(trial_edges[e])-static_cast<long double>(edges[e]);
        require(std::isfinite(paired),"Finite paired difference");ordinary_armijo=newT<=T+1e-4*step*slope;
        accepted=paired<=rhs;reason=accepted?"accepted":"paired_armijo_rejected";
      }
      out[2]<<event<<",160,"<<updates<<','<<attempt;value(out[2],step);value(out[2],slope);optional(out[2],actual,actual_evaluated);
      out[2]<<','<<actual_descent<<','<<noop<<','<<evaluated;optional(out[2],paired,evaluated);optional(out[2],outer_change,evaluated);value(out[2],rhs);
      out[2]<<','<<ordinary_armijo<<','<<accepted<<','<<reason<<'\n';
      if(accepted) {
        Vec next;const double checked=path_eval(g,trial,&next);++path_calls;
        require(std::isfinite(checked) && checked==newT,"Accepted actual core/cached-edge total parity");
        p=std::move(trial);gradient=std::move(next);edges=std::move(trial_edges);T=newT;++updates;update_record(step,true);break;
      }
      if(reason!="paired_armijo_rejected" && reason!="rounded_non_descent"){stop=reason;break;}
    }
    for(auto &stream:out){stream.flush();require(bool(stream),"Iteration evidence write failed");}
    if(!accepted){if(stop.empty())stop="halving_budget";break;}
  }
  arrays(event,"final",p,gradient,edges,fixed,out);
  out[0]<<event<<",160,"<<stop<<','<<updates<<','<<trials<<','<<metric_calls<<','<<path_calls<<','<<segment_calls
        <<','<<std::count(fixed.begin(),fixed.end(),true);value(out[0],T);value(out[0],available_norm(gradient,fixed));value(out[0],norm(gradient));
  out[0]<<",0,null,0,0,0\n";
}
int main(int argc,char **argv) {
  try {
    require(argc==4,"Use GRID INPUT_DIRECTORY OUTPUT_DIRECTORY");
    require(std::numeric_limits<double>::is_iec559 && std::numeric_limits<double>::digits==53 && std::fegetround()==FE_TONEAREST
            && std::numeric_limits<long double>::digits>53,"Binary64 nearest and extended accumulation required");
    const Grid g=model(argv[1]);const std::string input=argv[2],folder=argv[3];std::vector<std::ofstream> out;
    for(const char *name:{"summary.csv","updates.csv","trials.csv","directions.csv","paths.csv","gradients.csv","edges.csv"})out.push_back(output(folder+"/"+name));
    out[0]<<"event,station,reason,updates,trials,metric_calls,path_eval_calls,extra_segment_calls,fixed_slots,action,action_hex,available_norm,available_norm_hex,ordinary_norm,ordinary_norm_hex,original_convergence_flag,candidate_convergence_status,trace_calls,field_calls,source_model_partials\n";
    out[1]<<"event,station,update,accepted_step,accepted_step_hex,action,action_hex,available_norm,available_norm_hex,ordinary_norm,ordinary_norm_hex\n";
    out[2]<<"event,station,update,attempt,step,step_hex,nominal_slope,nominal_slope_hex,actual_slope_extended,actual_slope_extended_hex,actual_descent,no_op,action_evaluated,paired_change,paired_change_hex,outer_change,outer_change_hex,armijo_rhs_extended,armijo_rhs_extended_hex,ordinary_armijo,paired_armijo,reason\n";
    out[3]<<"event,station,update,node,qx,qx_hex,qy,qy_hex,qz,qz_hex\n";
    out[4]<<"event,station,state,node,x,x_hex,y,y_hex,z,z_hex\n";
    out[5]<<"event,station,state,node,axis,available,component,component_hex\n";
    out[6]<<"event,station,state,edge,action,action_hex\n";
    for(int event:{981,987})iterate(g,event,input,out);
    for(auto &stream:out){stream.flush();stream.close();require(bool(stream),"Terminal evidence write failed");}
    std::cout<<"cases=2 max_updates_per_case=1000 max_trials_per_update=24 trace_calls=0 field_calls=0 source_model_partials=0 convergence_promotions=0\n";
    std::cout.flush();require(bool(std::cout),"Terminal stdout write failed");return 0;
  } catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}
}
