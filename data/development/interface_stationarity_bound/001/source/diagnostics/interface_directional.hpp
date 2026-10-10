#pragma once
// Diagnostic first variation of the continuous piecewise-trilinear Fermat
// action. No change to segment(), trace(), geometry, or stopping flags.
using LP = std::array<long double,3>;
struct IncidentSample { long double velocity=0; LP gradient{}; };

IncidentSample incident_sample(const Grid &g,LP p,const int aligned[3],LP direction) {
  const Vec *axes[]={&g.x,&g.y,&g.z};
  int cell[3];long double fraction[3],width[3];
  for(int a=0;a<3;++a) {
    const auto &axis=*axes[a];
    cell[a]=std::clamp(int(std::upper_bound(axis.begin(),axis.end(),p[a])-axis.begin())-1,0,int(axis.size())-2);
    // An exact internal-face index is supplied by the unperturbed segment.
    // Choose its incident cell by the actual interpolated knot direction.
    if(aligned[a]>=0) cell[a]=direction[a]<0 ? aligned[a]-1 : aligned[a];
    width[a]=(long double)axis[cell[a]+1]-axis[cell[a]];
    fraction[a]=(p[a]-axis[cell[a]])/width[a];
  }
  IncidentSample result;
  for(int c=0;c<2;++c)for(int b=0;b<2;++b)for(int a=0;a<2;++a) {
    int bit[]={a,b,c};long double weight=1;
    for(int d=0;d<3;++d)weight*=bit[d]?fraction[d]:1-fraction[d];
    result.velocity+=weight*g.v[g.id(cell[0]+a,cell[1]+b,cell[2]+c)];
  }
  for(int d=0;d<3;++d) {
    int u=(d+1)%3,v=(d+2)%3;
    for(int a=0;a<2;++a)for(int b=0;b<2;++b) {
      int q[]={cell[0],cell[1],cell[2]};q[u]+=a;q[v]+=b;
      long double lo=g.v[g.id(q[0],q[1],q[2])];++q[d];
      long double hi=g.v[g.id(q[0],q[1],q[2])];
      result.gradient[d]+=(hi-lo)/width[d]*(a?fraction[u]:1-fraction[u])*(b?fraction[v]:1-fraction[v]);
    }
  }
  if(!(result.velocity>0))throw std::runtime_error("Nonpositive diagnostic velocity");
  return result;
}

long double directional_segment(const Grid &g,P a,P b,P da,P db,int subdivisions=1) {
  const Vec *axes[]={&g.x,&g.y,&g.z};
  LP delta{},change{};long double square=0,geometric=0;
  std::vector<long double> cuts{0,1};int aligned[]={-1,-1,-1};
  for(int k=0;k<3;++k) {
    delta[k]=(long double)b[k]-a[k];change[k]=(long double)db[k]-da[k];
    square+=delta[k]*delta[k];geometric+=delta[k]*change[k];
    if(delta[k]!=0) {
      for(double x:*axes[k]) {
        long double u=((long double)x-a[k])/delta[k];
        if(u>0&&u<1)cuts.push_back(u);
      }
    } else {
      for(size_t j=1;j+1<axes[k]->size();++j)if(a[k]==(*axes[k])[j])aligned[k]=int(j);
      if(aligned[k]>=0&&change[k]!=0) {
        long double u=-(long double)da[k]/change[k];
        if(u>0&&u<1)cuts.push_back(u); // Side changes within this aligned segment.
      }
    }
  }
  const long double length=std::sqrt(square);
  if(!(length>0))throw std::runtime_error("Zero-length segment has a separate nonsmooth variation");
  std::sort(cuts.begin(),cuts.end());cuts.erase(std::unique(cuts.begin(),cuts.end()),cuts.end());
  static constexpr long double nodes[]={0.18343464249564980494L,0.52553240991632898582L,
    0.79666647741362673959L,0.96028985649753623168L};
  static constexpr long double weights[]={0.36268378337836198297L,0.31370664587788728734L,
    0.22238103445337447054L,0.10122853629037625915L};
  long double result=0;
  for(size_t j=1;j<cuts.size();++j)for(int sub=0;sub<subdivisions;++sub) {
    long double left=cuts[j-1]+(cuts[j]-cuts[j-1])*sub/subdivisions;
    long double right=cuts[j-1]+(cuts[j]-cuts[j-1])*(sub+1)/subdivisions;
    long double half=(right-left)/2,mid=(right+left)/2;
    for(int m=0;m<4;++m)for(int sign:{-1,1}) {
      long double u=mid+sign*half*nodes[m];LP point{},direction{};
      for(int k=0;k<3;++k){point[k]=a[k]+u*delta[k];direction[k]=da[k]+u*change[k];}
      auto sample=incident_sample(g,point,aligned,direction);
      long double slope=geometric/(length*sample.velocity);
      for(int k=0;k<3;++k)slope-=length*sample.gradient[k]*direction[k]/(sample.velocity*sample.velocity);
      result+=half*weights[m]*slope;
    }
  }
  return result;
}

long double directional_path(const Grid &g,const std::vector<P> &path,const std::vector<P> &direction,int subdivisions=1) {
  if(path.size()!=direction.size()||path.size()<2)throw std::runtime_error("Direction/path dimensions differ");
  const Vec *axes[]={&g.x,&g.y,&g.z};
  for(size_t i=0;i<path.size();++i)for(int k=0;k<3;++k) {
    if(!std::isfinite(direction[i][k])||!g.contains(path[i]))throw std::runtime_error("Invalid path/direction");
    if((path[i][k]==axes[k]->front()&&direction[i][k]<0)||
       (path[i][k]==axes[k]->back()&&direction[i][k]>0))throw std::runtime_error("Outward boundary direction");
  }
  long double result=0;
  for(size_t i=1;i<path.size();++i)result+=directional_segment(g,path[i-1],path[i],direction[i-1],direction[i],subdivisions);
  return result;
}
