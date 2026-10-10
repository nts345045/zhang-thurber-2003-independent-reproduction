// Isolated candidate test, not a replacement ray solver or convergence flag.
// A chord between x=0 crossings has action length/6 and is no slower than
// any intervening path, because v<=6 everywhere and v=6 on that entire face.
// The two crossing coordinates remain on the face during the branch search.
#define main unused_solver_main
#include "../src/main.cpp"
#undef main
#include "loma_path_checks.hpp"

struct GuideBranch {
  std::vector<P> path;
  size_t first=0, last=0;
};

GuideBranch straighten(const Grid &g,const std::vector<P> &path) {
  for(size_t k=0;k<g.z.size();++k)for(size_t j=0;j<g.y.size();++j)
    for(size_t i=0;i<g.x.size();++i) {
      double v=g.v[g.id(i,j,k)];
      if(v>6 || (g.x[i]<=0 && v!=6))
        throw std::runtime_error("The stated maximum-speed half-space proof does not apply");
    }
  if(std::find(g.x.begin(),g.x.end(),0)==g.x.end())
    throw std::runtime_error("Missing exact x=0 model interface");
  std::vector<P> split;
  size_t first=0,last=0;
  for(size_t i=0;i<path.size();++i) {
    if(i && path[i-1][0]*path[i][0]<0) {
      double t=-path[i-1][0]/(path[i][0]-path[i-1][0]);
      P crossing=path[i-1]+(path[i]-path[i-1])*t;
      crossing[0]=0; // Exact intersection equation, not a proximity operation.
      split.push_back(crossing);
      if(!first)first=split.size()-1;
      last=split.size()-1;
    }
    split.push_back(path[i]);
  }
  if(!first || last<=first || path.front()[0]<=0 || path.back()[0]<=0)
    throw std::runtime_error("This diagnostic requires two positive-side endpoints and crossings");
  GuideBranch result;
  result.path.insert(result.path.end(),split.begin(),split.begin()+first+1);
  result.path.insert(result.path.end(),split.begin()+last,split.end());
  result.first=first;result.last=first+1;
  if(loma_exact_action(g,result.path)>loma_exact_action(g,path)+1e-12L)
    throw std::runtime_error("Exact-action straightening inequality failed");
  return result;
}

// Restricted branch optimization. The reduced metric keeps the principal
// diagonal, and the two fixed x coordinates are removed from every vector.
// No claim of unrestricted stationarity is made by this norm or stopping test.
void optimize_branch(const Grid &g,GuideBranch &branch,int budget,std::ostream &log,
                     const std::string &run,const std::string &row) {
  auto &p=branch.path;
  std::vector<bool> fixed(3*(p.size()-2),false);
  fixed[3*(branch.first-1)]=fixed[3*(branch.last-1)]=true;
  auto restrict=[&](Vec &q){for(size_t k=0;k<q.size();++k)if(fixed[k])q[k]=0;};
  auto inverse=[&](const Vec &weights,Vec q) {
    for(double &v:q)v=-v;
    return solve_free_ray_metric(weights,q,fixed);
  };
  Vec gradient;double time=path_eval(g,p,&gradient);restrict(gradient);
  std::vector<Vec> steps,changes;Vec rho;
  for(int iteration=0;iteration<=budget;++iteration) {
    log<<run<<','<<row<<','<<iteration<<','<<time<<','<<norm(gradient)<<'\n';
    if(norm(gradient)<1e-7 || iteration==budget)break;
    Vec direction=gradient,alpha(steps.size());
    for(int j=int(steps.size())-1;j>=0;--j) {
      alpha[j]=rho[j]*dot(steps[j],direction);
      for(size_t k=0;k<direction.size();++k)direction[k]-=alpha[j]*changes[j][k];
    }
    auto weights=ray_metric_weights(g,p);
    double scale=steps.empty()?1:dot(steps.back(),changes.back())/
      dot(changes.back(),inverse(weights,changes.back()));
    direction=inverse(weights,direction);
    for(double &v:direction)v*=scale;
    for(size_t j=0;j<steps.size();++j) {
      double beta=rho[j]*dot(changes[j],direction);
      for(size_t k=0;k<direction.size();++k)direction[k]+=steps[j][k]*(alpha[j]-beta);
    }
    for(double &v:direction)v=-v;
    if(!(dot(direction,gradient)<0)) {
      direction=inverse(weights,gradient);
      for(double &v:direction)v=-v;
      steps.clear();changes.clear();rho.clear();
    }
    restrict(direction);
    double slope=dot(direction,gradient),step=1;
    if(!(slope<0))throw std::runtime_error("No restricted descent direction");
    const Vec *axes[]={&g.x,&g.y,&g.z};
    for(size_t i=1;i+1<p.size();++i)for(int axis=0;axis<3;++axis) {
      double d=direction[3*(i-1)+axis];
      if(d>0)step=std::min(step,(axes[axis]->back()-p[i][axis])/d);
      if(d<0)step=std::min(step,(axes[axis]->front()-p[i][axis])/d);
    }
    std::vector<P> trial;bool accepted=false;double next_time=time;
    for(int ls=0;ls<24;++ls,step*=.5) {
      trial=p;bool valid=true;
      for(size_t i=1;i+1<p.size();++i) {
        for(int axis=0;axis<3;++axis)trial[i][axis]+=step*direction[3*(i-1)+axis];
        valid=valid&&g.contains(trial[i]);
      }
      for(size_t i=1;i<trial.size();++i)valid=valid&&norm(trial[i]-trial[i-1])>=1e-8;
      if(!valid)continue;
      next_time=path_eval(g,trial);
      if(next_time<=time+1e-4*step*slope){accepted=true;break;}
    }
    if(!accepted)break;
    Vec next_gradient;path_eval(g,trial,&next_gradient);restrict(next_gradient);
    Vec s(direction.size()),y(direction.size());
    for(size_t k=0;k<s.size();++k){s[k]=step*direction[k];y[k]=next_gradient[k]-gradient[k];}
    double sy=dot(s,y);
    if(sy>1e-14) {
      if(steps.size()==8){steps.erase(steps.begin());changes.erase(changes.begin());rho.erase(rho.begin());}
      steps.push_back(s);changes.push_back(y);rho.push_back(1/sy);
    }
    p=std::move(trial);gradient=std::move(next_gradient);time=next_time;
  }
}

int main(int argc,char **argv) {
  if(argc!=5)throw std::runtime_error("Usage: straighten_loma_guide GRID PATHS RUN_ID OUTPUT_DIR");
  auto grid=read_grid(argv[1]);auto table=csv_table(argv[2]);
  std::map<std::string,size_t> columns;
  for(size_t i=0;i<table.header.size();++i)columns[table.header[i]]=i;
  std::vector<P> original;std::string run=argv[3],row;
  for(const auto &record:table.rows)if(record[columns.at("run_id")]==run) {
    if(csv_int(record[columns.at("node")])!=int(original.size()))
      throw std::runtime_error("Nonconsecutive saved path");
    row=record[columns.at("diagnostic_row")];
    original.push_back({csv_double(record[columns.at("x")]),csv_double(record[columns.at("y")]),csv_double(record[columns.at("z")])});
  }
  if(original.size()<3)throw std::runtime_error("Missing saved path");
  auto branch=straighten(grid,original);
  std::string out=argv[4];
  std::ofstream history(out+"/history.csv"),result(out+"/result.csv"),paths(out+"/paths.csv");
  if(!history||!result||!paths)throw std::runtime_error("Cannot create branch output");
  for(auto stream:{&history,&result,&paths})*stream<<std::setprecision(17);
  history<<"run_id,diagnostic_row,iteration,time_s,restricted_gradient_s_per_km\n";
  result<<"run_id,diagnostic_row,stage,time_s,exact_action_s,path_nodes,restricted_gradient_s_per_km,source_dx,source_dy,source_dz,guide_start_node,guide_end_node,guide_length_km,guide_start_full_gradient_x,guide_end_full_gradient_x\n";
  paths<<"run_id,diagnostic_row,stage,node,x_km,y_km,z_km\n";
  auto write=[&](const std::string &stage,const std::vector<P> &p) {
    Vec grad;double time=path_eval(grid,p,&grad);P source{};segment(grid,p[0],p[1],&source);
    double ga=NAN,gb=NAN,length=NAN;
    if(stage!="original") {
      ga=grad[3*(branch.first-1)];gb=grad[3*(branch.last-1)];
      grad[3*(branch.first-1)]=grad[3*(branch.last-1)]=0;
      length=norm(p[branch.last]-p[branch.first]);
    }
    result<<run<<','<<row<<','<<stage<<','<<time<<','<<loma_exact_action(grid,p)<<','<<p.size()<<','<<norm(grad);
    for(double v:source)result<<','<<v;
    result<<','<<(stage=="original"?0:branch.first)<<','<<(stage=="original"?0:branch.last)<<','<<length<<','<<ga<<','<<gb<<'\n';
    for(size_t i=0;i<p.size();++i)paths<<run<<','<<row<<','<<stage<<','<<i<<','<<p[i][0]<<','<<p[i][1]<<','<<p[i][2]<<'\n';
  };
  write("original",original);write("straightened",branch.path);
  optimize_branch(grid,branch,4000,history,run,row);
  write("branch_optimized",branch.path);
}
