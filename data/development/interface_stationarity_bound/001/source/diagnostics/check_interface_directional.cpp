// Read-only directional probes of frozen polygons. No optimizer is invoked.
#define main frozen_solver_main
#include "../src/main.cpp"
#undef main
#include "loma_path_checks.hpp"
#include "interface_directional.hpp"

long double positive_linear_integral(long double a,long double b) {
  if(a>=0&&b>=0)return (a+b)/2;
  if(a<=0&&b<=0)return 0;
  return a>0 ? a*a/(2*(a-b)) : b*b/(2*(b-a));
}

int main(int argc,char **argv) {
  if(argc!=5)throw std::runtime_error("Usage: check_interface_directional GRID NATIVE_CASE PATH OUTPUT");
  auto native_grid=read_grid(argv[1]);
  auto native_case=csv_table(argv[2]),native_path=csv_table(argv[3]);
  std::map<std::string,size_t> col;for(size_t i=0;i<native_case.header.size();++i)col[native_case.header[i]]=i;
  if(native_case.rows.size()!=1)throw std::runtime_error("Require one identified native case");
  const auto &record=native_case.rows[0];
  std::vector<P> saved;
  for(const auto &row:native_path.rows) {
    if(csv_int(row[0])!=int(saved.size()))throw std::runtime_error("Native path order changed");
    saved.push_back({csv_double(row[1]),csv_double(row[2]),csv_double(row[3])});
  }
  std::string out=argv[4];std::ofstream results(out+"/directional.csv"),secants(out+"/secants.csv"),directions(out+"/directions.csv");
  if(!results||!secants||!directions)throw std::runtime_error("Output directory missing");
  for(auto f:{&results,&secants,&directions})*f<<std::setprecision(21);
  const Strings ids{"event","station","source_event_resource_id","source_origin_resource_id","receiver_channel_seed_id",
    "receiver_channel_fdsn_source_id","receiver_metadata_epoch_start","receiver_metadata_epoch_end"};
  results<<"case,direction,path_nodes,direction_norm,chosen_gradient_norm,chosen_gradient_dot_direction,directional_8point,directional_32point,closed_form_directional,base_exact_action,base_production_action,original_converged,original_updates";
  secants<<"case,direction,step_km,forward_valid,backward_valid,forward_exact_change,backward_exact_change,forward_exact_slope,backward_exact_slope,production_forward_change,production_backward_change";
  directions<<"case,direction,node,x,y,z,dx,dy,dz";
  for(auto f:{&results,&secants,&directions}){for(const auto &key:ids)*f<<','<<key;*f<<'\n';}
  auto emit=[&](const std::string &name,const Grid &g,const std::vector<P> &path,bool native,int model) {
    Vec gradient;double time=path_eval(g,path,&gradient);long double exact=loma_exact_action(g,path);
    auto append=[&](std::ostream &f) {
      for(const auto &key:ids) {
        std::string value;
        if(native)value=record[col.at(key)];
        else if(key=="event"||key=="station")value="0";
        else if(key=="source_event_resource_id")value="fixture:"+name+":event";
        else if(key=="source_origin_resource_id")value="fixture:"+name+":origin";
        else if(key=="receiver_channel_seed_id")value="XX.IFACE..HHZ";
        else if(key=="receiver_channel_fdsn_source_id")value="FDSN:XX_IFACE__H_H_Z";
        f<<','<<csv_quote(value);
      }
      f<<'\n';
    };
    std::vector<bool> interface(gradient.size(),false);
    const Vec *axes[]={&g.x,&g.y,&g.z};
    for(size_t i=1;i<path.size();++i)for(int axis=0;axis<3;++axis)
      if(path[i-1][axis]==path[i][axis])for(size_t j=1;j+1<axes[axis]->size();++j)
        if(path[i][axis]==(*axes[axis])[j]) {
          if(i>1)interface[3*(i-2)+axis]=true;
          if(i+1<path.size())interface[3*(i-1)+axis]=true;
        }
    auto expand=[&](const Vec &v){std::vector<P>d(path.size());for(size_t i=1;i+1<path.size();++i)for(int k=0;k<3;++k)d[i][k]=v[3*(i-1)+k];return d;};
    std::vector<std::pair<std::string,std::vector<P>>> probes;
    Vec negative=gradient;for(double &x:negative)x=-x;
    probes.push_back({"negative_chosen_gradient",expand(negative)});
    for(size_t k=0;k<negative.size();++k)if(interface[k])negative[k]=0;
    probes.push_back({"in_plane_negative_gradient",expand(negative)});
    auto metric=solve_free_ray_metric(ray_metric_weights(g,path),gradient,interface);
    probes.push_back({"in_plane_metric_direction",expand(metric)});
    std::vector<size_t> guide;
    for(size_t i=1;i+1<path.size();++i)if(path[i][0]==0)guide.push_back(i);
    for(int sign:{-1,1}) {
      std::vector<P>d(path.size());for(size_t i:guide)d[i][0]=sign;
      probes.push_back({sign<0?"guide_negative_translation":"guide_positive_translation",d});
    }
    if(guide.size()>1) {
      size_t m=guide.size()/2;
      std::vector<P>d(path.size());d[guide[m-1]][0]=1;d[guide[m]][0]=-1;
      probes.push_back({"opposite_adjacent_guide_normals",d});
    }
    for(auto probe:probes) {
      auto &d=probe.second;double square=0;for(auto x:d)square+=dot(x,x);
      if(square>0)for(auto &x:d)x=x*(1/std::sqrt(square));
      Vec flat(gradient.size());for(size_t i=1;i+1<path.size();++i)for(int k=0;k<3;++k)flat[3*(i-1)+k]=d[i][k];
      long double one=directional_path(g,path,d),four=directional_path(g,path,d,4),closed=0;
      if(model>=0)for(size_t i=1;i<path.size();++i) {
        P delta=path[i]-path[i-1],change=d[i]-d[i-1];long double length=norm(delta);
        closed+=dot(delta,change)/(length*6);
        if(model==1)closed+=length/18*positive_linear_integral(d[i-1][0],d[i][0]);
        if(model==2)closed-=length/18*(positive_linear_integral(d[i-1][0],d[i][0])+positive_linear_integral(-d[i-1][0],-d[i][0]));
      }
      results<<name<<','<<probe.first<<','<<path.size()<<','<<norm(flat)<<','<<norm(gradient)<<','<<dot(gradient,flat)<<','<<one<<','<<four<<',';
      if(model>=0)results<<closed;
      results<<','<<exact<<','<<time<<','<<(native?record[col.at("original_converged")]:"")<<','<<(native?record[col.at("original_updates")]:"");append(results);
      for(size_t i=0;i<path.size();++i) {
        directions<<name<<','<<probe.first<<','<<i;
        for(double x:path[i])directions<<','<<x;for(double x:d[i])directions<<','<<x;append(directions);
      }
      for(double h:{1e-2,1e-3,1e-4,1e-5,1e-6,1e-7,1e-8,1e-9}) {
        auto plus=path,minus=path;bool forward=true,backward=true;
        for(size_t i=0;i<path.size();++i) {
          plus[i]=path[i]+d[i]*h;minus[i]=path[i]-d[i]*h;
          forward=forward&&g.contains(plus[i]);backward=backward&&g.contains(minus[i]);
        }
        long double fp=forward?loma_exact_action(g,plus)-exact:NAN;
        long double fm=backward?loma_exact_action(g,minus)-exact:NAN;
        secants<<name<<','<<probe.first<<','<<h<<','<<forward<<','<<backward<<','<<fp<<','<<fm<<','<<fp/h<<','<<fm/h<<','
          <<(forward?path_eval(g,plus)-time:NAN)<<','<<(backward?path_eval(g,minus)-time:NAN);append(secants);
      }
    }
  };
  Grid control;control.x={-1,0,1};control.y={0,1,2};control.z={-1,0,1};control.v.resize(control.size(),6);
  std::vector<P> straight{{0,0,0},{0,.5,0},{0,1,0},{0,1.5,0},{0,2,0}},bent=straight;bent[2][0]=.25;
  emit("homogeneous_straight",control,straight,false,0);
  emit("homogeneous_bent",control,bent,false,0);
  for(int model:{1,2}) {
    for(size_t k=0;k<control.z.size();++k)for(size_t j=0;j<control.y.size();++j)for(size_t i=0;i<control.x.size();++i)
      control.v[control.id(i,j,k)]=model==1?6-2*std::max(0.,control.x[i]):6+2*std::abs(control.x[i]);
    emit(model==1?"fast_plateau_interface":"cusp_maximum_interface",control,straight,false,model);
  }
  emit("native_row5_retained_h0.03125",native_grid,saved,true,-1);
}
