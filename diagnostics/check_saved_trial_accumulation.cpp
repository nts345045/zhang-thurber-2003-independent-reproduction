// Evaluate saved polygons only. No optimizer, path, or acceptance flag changes.
#define main frozen_solver_entry
#include "../src/main.cpp"
#undef main

template<class Real> Real sample_value(const Grid &g, const std::array<Real,3> &p) {
  const Vec *axes[] = {&g.x,&g.y,&g.z};
  int index[3]; Real t[3];
  for (int k=0;k<3;k++) {
    const auto &axis=*axes[k];
    index[k]=std::clamp(int(std::upper_bound(axis.begin(),axis.end(),p[k])-axis.begin())-1,
                        0,int(axis.size())-2);
    t[k]=(p[k]-Real(axis[index[k]]))/(Real(axis[index[k]+1])-Real(axis[index[k]]));
  }
  Real value=0;
  for(int c=0;c<2;c++)for(int b=0;b<2;b++)for(int a=0;a<2;a++) {
    const int bits[]={a,b,c}; Real w[3];
    for(int k=0;k<3;k++)w[k]=bits[k]?t[k]:1-t[k];
    value+=(w[0]*w[1]*w[2])*Real(g.v[g.id(index[0]+a,index[1]+b,index[2]+c)]);
  }
  return value;
}

template<class Real> Real segment_value(const Grid &g, P aa, P bb) {
  std::array<Real,3> a,d;
  for(int k=0;k<3;k++){a[k]=Real(aa[k]);d[k]=Real(bb[k])-a[k];}
  const Real length=std::sqrt(d[0]*d[0]+d[1]*d[1]+d[2]*d[2]);
  if(length<Real(1e-12))return 0;
  std::vector<Real> cuts{0,1};
  const Vec *axes[]={&g.x,&g.y,&g.z};
  for(int k=0;k<3;k++)if(std::abs(d[k])>Real(1e-12))for(double q:*axes[k]) {
    const Real t=(Real(q)-a[k])/d[k];
    if(t>Real(1e-10)&&t<Real(1-1e-10))cuts.push_back(t);
  }
  std::sort(cuts.begin(),cuts.end());
  // Preserve the frozen binary64 coefficients when increasing arithmetic precision.
  static constexpr double nodes[]={0.1834346424956498,0.5255324099163290,
                                   0.7966664774136267,0.9602898564975363};
  static constexpr double weights[]={0.3626837833783620,0.3137066458778873,
                                     0.2223810344533745,0.1012285362903763};
  Real action=0;
  for(size_t j=1;j<cuts.size();j++) {
    const Real mid=(cuts[j]+cuts[j-1])/2,half=(cuts[j]-cuts[j-1])/2;
    for(int point=0;point<4;point++)for(double sign:{-1.,1.}) {
      const Real t=mid+Real(sign)*half*Real(nodes[point]);
      std::array<Real,3> p;
      for(int k=0;k<3;k++)p[k]=a[k]+d[k]*t;
      const Real u=1/sample_value(g,p),weight=half*Real(weights[point]);
      action+=length*weight*u;
    }
  }
  return action;
}

void require(bool value,const std::string &message) {
  if(!value)throw std::runtime_error(message);
}

struct SavedPath { std::string observation,run; int trial=-1; double step=0; std::vector<P> points; };
std::vector<SavedPath> paths(const std::string &file,bool trials) {
  const auto table=csv_table(file);
  std::map<std::string,size_t> col;
  for(size_t k=0;k<table.header.size();k++)col[table.header[k]]=k;
  std::vector<SavedPath> result;
  for(const auto &row:table.rows)if(row[col.at("run_id")]=="fmm_0.031250_1000") {
    const int trial=trials?csv_int(row[col.at("trial_index")]): -1;
    if(result.empty()||result.back().trial!=trial) {
      SavedPath p; p.run=row[col.at("run_id")];p.observation=row[col.at("observation_index")];
      p.trial=trial;p.step=trials?csv_double(row[col.at("step")]):0;result.push_back(p);
    }
    auto &p=result.back();
    require(row[col.at("observation_index")]==p.observation&&p.observation=="3426","Mixed identity");
    require(csv_int(row[col.at("node")])==int(p.points.size()),"Unordered path nodes");
    if(trials)require(csv_double(row[col.at("step")])==p.step,"Changed step within path");
    p.points.push_back({csv_double(row[col.at("x")]),csv_double(row[col.at("y")]),csv_double(row[col.at("z")])});
  }
  return result;
}

void controls(const std::string &file) {
  auto result=output(file);
  result<<std::setprecision(std::numeric_limits<long double>::max_digits10)
        <<"name,value,reference,allowance,passed\n";
  auto check=[&](const std::string &name,long double value,long double reference,long double allowance) {
    const bool pass=std::abs(value-reference)<=allowance;
    result<<name<<','<<value<<','<<reference<<','<<allowance<<','<<pass<<'\n';
    require(pass,"Control failed: "+name);
  };
  Grid g;g.x={-1,4};g.y={-1,5};g.z={-1,2};g.v.assign(g.size(),5);
  const long double allowance=64*std::numeric_limits<double>::epsilon();
  check("homogeneous_original",segment(g,{0,0,0},{3,4,0}),1,allowance);
  check("homogeneous_template_double",segment_value<double>(g,{0,0,0},{3,4,0}),1,allowance);
  check("homogeneous_extended",segment_value<long double>(g,{0,0,0},{3,4,0}),1,allowance);
  for(size_t k=0;k<g.z.size();k++)for(size_t j=0;j<g.y.size();j++)for(size_t i=0;i<g.x.size();i++)
    g.v[g.id(i,j,k)]=5+g.z[k];
  const long double vertical=std::log(6.L/5.L);
  check("affine_vertical_original",segment(g,{0,0,0},{0,0,1}),vertical,allowance*vertical);
  check("affine_vertical_extended",segment_value<long double>(g,{0,0,0},{0,0,1}),vertical,allowance*vertical);
  check("affine_reversed_extended",segment_value<long double>(g,{0,0,1},{0,0,0}),vertical,allowance*vertical);
  check("affine_horizontal_extended",segment_value<long double>(g,{0,0,1},{3,4,1}),5.L/6.L,allowance);
  const std::vector<double> values{1e16,1,-1e16};double ordinary=0;long double extended=0;
  for(double value:values){ordinary+=value;extended+=static_cast<long double>(value);}
  check("double_cancellation",ordinary,0,0);check("extended_cancellation",extended,1,0);
}

int main(int argc,char **argv) {
  require(std::numeric_limits<long double>::digits>std::numeric_limits<double>::digits,
          "This diagnostic needs extended arithmetic");
  if(argc==3&&std::string(argv[1])=="--controls"){controls(argv[2]);return 0;}
  require(argc==6,"Expected GRID BASE_DIRECTIONS TRIAL_PATHS SEGMENTS TOTALS");
  const Grid g=read_grid(argv[1]);
  auto bases=paths(argv[2],false),trials=paths(argv[3],true);
  require(bases.size()==1&&trials.size()==24,"Incomplete saved paths");
  const auto &base=bases[0];
  require(base.points.size()==1134,"Changed base node count");
  for(int j=0;j<24;j++)require(trials[j].trial==j&&trials[j].step==std::ldexp(1.,-j),"Changed trial order/step");
  std::vector<double> old_segments;
  std::vector<long double> old_extended;
  auto segments=output(argv[4]),totals=output(argv[5]);
  segments<<std::setprecision(std::numeric_limits<long double>::max_digits10)
    <<"run_id,observation_index,trial_index,edge,original_segment_s,extended_segment_s,unchanged_edge\n";
  totals<<std::setprecision(std::numeric_limits<long double>::max_digits10)
    <<"run_id,observation_index,trial_index,step,original_total_s,extended_sum_original_segments_s,"
      "paired_original_segment_change_s,extended_total_s,paired_extended_segment_change_s,changed_edges,"
      "double_mantissa_bits,extended_mantissa_bits\n";
  trials.insert(trials.begin(),base);
  for(const auto &p:trials) {
    require(p.points.size()==base.points.size()&&p.points.front()==base.points.front()&&
            p.points.back()==base.points.back(),"Changed topology/endpoints");
    double native_total=0;long double better_sum=0,paired=0,extended_total=0,extended_paired=0;
    size_t changed=0;
    for(size_t i=1;i<p.points.size();i++) {
      require(g.contains(p.points[i-1])&&g.contains(p.points[i]),"Outside saved domain");
      const double original=segment(g,p.points[i-1],p.points[i]);
      require(original==segment_value<double>(g,p.points[i-1],p.points[i]),"Double template differs from original segment");
      const long double extended=segment_value<long double>(g,p.points[i-1],p.points[i]);
      const bool same=p.points[i-1]==base.points[i-1]&&p.points[i]==base.points[i];
      native_total+=original;better_sum+=static_cast<long double>(original);extended_total+=extended;
      if(p.trial<0){old_segments.push_back(original);old_extended.push_back(extended);}
      else if(!same){paired+=static_cast<long double>(original)-old_segments[i-1];
                    extended_paired+=extended-old_extended[i-1];changed++;}
      segments<<p.run<<','<<p.observation<<','<<p.trial<<','<<i-1<<','<<original<<','<<extended<<','<<same<<'\n';
    }
    require(native_total==path_eval(g,p.points),"Original path total changed");
    totals<<p.run<<','<<p.observation<<','<<p.trial<<','<<p.step<<','<<native_total<<','<<better_sum<<','<<paired
          <<','<<extended_total<<','<<extended_paired<<','<<changed<<','<<std::numeric_limits<double>::digits
          <<','<<std::numeric_limits<long double>::digits<<'\n';
  }
}
