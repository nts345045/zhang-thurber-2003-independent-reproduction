#pragma once
// Exact arithmetic, input validation and record types extracted from the frozen baseline.
// Arithmetic expressions unchanged; the old segment implementation is excluded.
#include "source/src/core.hpp"
#include "dependency/include/gmp.h"
#include <cfenv>
#include <climits>
#include <cstdint>
#include <cstring>
#include <initializer_list>

namespace exact_cell {
using W = long double;
using WP = std::array<W,3>;
inline void need(bool ok,const char *why) { if(!ok) throw std::runtime_error(why); }
inline void format() {
  need(sizeof(double)==8 && std::numeric_limits<double>::is_iec559 &&
       std::numeric_limits<double>::digits==53 && std::numeric_limits<double>::radix==2,
       "Require IEEE binary64 inputs");
  need(std::numeric_limits<W>::radix==2 && std::numeric_limits<W>::digits==64 &&
       std::numeric_limits<W>::min_exponent==-16381 && std::numeric_limits<W>::max_exponent==16384 &&
       std::numeric_limits<W>::has_denorm==std::denorm_present && std::fegetround()==FE_TONEAREST,
       "Require nearest 64-bit-significand extended arithmetic with subnormals");
  need(__GNU_MP_VERSION==6 && __GNU_MP_VERSION_MINOR==1 && __GNU_MP_VERSION_PATCHLEVEL==2 &&
       std::strcmp(gmp_version,"6.1.2")==0 && sizeof(mp_limb_t)*CHAR_BIT==64 && GMP_NAIL_BITS==0,
       "Require pinned GMP 6.1.2 with 64-bit limbs and no nails");
}
struct Z {
  mpz_t v;
  Z() { mpz_init(v); } ~Z() { mpz_clear(v); }
  Z(const Z&)=delete; Z& operator=(const Z&)=delete;
};
struct Q {
  mpq_t v;
  Q(long n=0) { mpq_init(v); mpq_set_si(v,n,1); }
  Q(const Q &x) { mpq_init(v); mpq_set(v,x.v); }
  Q(Q &&x) noexcept { mpq_init(v); mpq_swap(v,x.v); }
  ~Q() { mpq_clear(v); }
  Q& operator=(Q x) noexcept { mpq_swap(v,x.v); return *this; }
  friend Q operator+(const Q&a,const Q&b) { Q r;mpq_add(r.v,a.v,b.v);return r; }
  friend Q operator-(const Q&a,const Q&b) { Q r;mpq_sub(r.v,a.v,b.v);return r; }
  friend Q operator-(const Q&a) { Q r;mpq_neg(r.v,a.v);return r; }
  friend Q operator*(const Q&a,const Q&b) { Q r;mpq_mul(r.v,a.v,b.v);return r; }
  friend Q operator/(const Q&a,const Q&b) { need(mpq_sgn(b.v)!=0,"Exact division by zero");Q r;mpq_div(r.v,a.v,b.v);return r; }
  friend bool operator<(const Q&a,const Q&b) { return mpq_cmp(a.v,b.v)<0; }
  friend bool operator==(const Q&a,const Q&b) { return mpq_equal(a.v,b.v)!=0; }
  friend bool operator!=(const Q&a,const Q&b) { return !(a==b); }
  friend bool operator<=(const Q&a,const Q&b) { return !(b<a); }
  std::string str() const {
    std::vector<char> s(mpz_sizeinbase(mpq_numref(v),10)+mpz_sizeinbase(mpq_denref(v),10)+4);
    mpq_get_str(s.data(),10,v);return s.data();
  }
};
using QP = std::array<Q,3>;
inline Q power2(int e) {
  Q r(1);if(e>=0)mpq_mul_2exp(r.v,r.v,e);else mpq_div_2exp(r.v,r.v,-e);return r;
}
inline Q exact(double x) {
  // GMP's documented mpq_set_d conversion preserves every finite binary64
  // exactly. Signed zero is retained by the observer's original-input hex.
  need(std::isfinite(x),"Nonfinite binary64 input");Q r;mpq_set_d(r.v,x);return r;
}
// Exact quotient/remainder rounding; no mpq_get_d or intermediate binary64.
struct Rounded { std::uint64_t mantissa;int quantum;bool negative; };
inline Rounded rounded(const Q &x,bool subnormal_quantum) {
  need(mpq_sgn(x.v)!=0,"Zero has no normalized significand");Z n,d,tmp,m,rem;
  mpz_abs(n.v,mpq_numref(x.v));mpz_set(d.v,mpq_denref(x.v));
  int e=int(mpz_sizeinbase(n.v,2))-int(mpz_sizeinbase(d.v,2));
  if(e>=0) { mpz_mul_2exp(tmp.v,d.v,e);if(mpz_cmp(n.v,tmp.v)<0)--e; }
  else { mpz_mul_2exp(tmp.v,n.v,-e);if(mpz_cmp(tmp.v,d.v)<0)--e; }
  int k=e-63;if(subnormal_quantum)k=std::max(k,-16445);
  if(k>=0)mpz_mul_2exp(d.v,d.v,k);else mpz_mul_2exp(n.v,n.v,-k);
  mpz_fdiv_qr(m.v,rem.v,n.v,d.v);mpz_mul_2exp(rem.v,rem.v,1);
  const int c=mpz_cmp(rem.v,d.v);
  if(c>0 || (c==0 && mpz_odd_p(m.v)))mpz_add_ui(m.v,m.v,1);
  if(mpz_sizeinbase(m.v,2)>64) { mpz_fdiv_q_2exp(m.v,m.v,1);++k; }
  need(mpz_sizeinbase(m.v,2)<=64,"Unexpected significand width");
  std::uint64_t bits=0;std::size_t count=0;mpz_export(&bits,&count,1,sizeof(bits),0,0,m.v);
  need(count<=1,"Significand export overflow");return {bits,k,mpq_sgn(x.v)<0};
}
inline W nonzero(W x,const char *why) { need(std::isfinite(x) && x!=0,why);return x; }
inline W wide(const Q &q) {
  if (q == Q(0)) return 0;
  const auto r = rounded(q, true);
  W v=std::ldexp(W(r.mantissa),r.quantum);if(r.negative)v=-v;
  return nonzero(v,"Exact rational does not have a nonzero finite wide handoff");
}
// Scale positive/negative factors together. An exact tiny cut width need not
// survive an isolated floating conversion when its physical measure can.
inline W times(const Q &q,std::initializer_list<W> factors,int shift=0) {
  if (q == Q(0)) return 0;
  const auto r = rounded(q, false);
  W f=std::ldexp(W(r.mantissa),-64);int e=r.quantum+64+shift;if(r.negative)f=-f;
  for(W x:factors) {
    need(std::isfinite(x),"Nonfinite product operand");if(x==0)return 0;
    int k=0;f*=std::frexp(x,&k);e+=k;
    int j=0;f=std::frexp(f,&j);e+=j;
  }
  return nonzero(std::ldexp(f,e),"Nonzero scaled product underflow or overflow");
}
inline W plus(W a,W b) { W c=a+b;need(std::isfinite(c),"Nonfinite accumulation");return c; }
struct GridData {
  const Grid &g;std::array<std::vector<Q>,3> axis;std::vector<Q> velocity;
  explicit GridData(const Grid &input):g(input) {
    format();const Vec *raw[]={&g.x,&g.y,&g.z};std::size_t count=1;
    for(int k=0;k<3;++k) {
      need(raw[k]->size()>=2 && raw[k]->size()<=std::size_t(INT_MAX)/count,"Invalid grid size");count*=raw[k]->size();
      for(double x:*raw[k])axis[k].push_back(exact(x));
      for(std::size_t j=1;j<axis[k].size();++j)need(axis[k][j-1]<axis[k][j],"Nonincreasing grid");
    }
    need(count==g.v.size(),"Grid velocity count mismatch");
    for(double x:g.v) { Q v=exact(x);need(Q(0)<v,"Nonpositive nodal velocity");velocity.push_back(v); }
  }
};
struct Event { Q u;std::vector<std::pair<int,int>> planes; };
struct Sample {
  Q u,weight;std::array<Q,2> shape;std::array<std::array<Q,2>,3> basis;
  std::array<W,2> shape_wide;std::array<std::array<W,2>,3> basis_wide;
  W measure=0,velocity=0;WP gradient{};std::array<int,8> ids{};std::array<W,8> nodal{};
};
struct Piece { Q left,right;std::array<int,3> cell;std::vector<Sample> samples; };
} // namespace exact_cell
