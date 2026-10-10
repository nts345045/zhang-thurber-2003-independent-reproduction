// Compile this same fixture against frozen legacy and current core headers;
// compare stdout byte-for-byte. No random geometry or observations are used.
#ifndef MATRIX_HEADER
#define MATRIX_HEADER "../src/core.hpp"
#endif
#include MATRIX_HEADER
#include <cassert>
#include <iomanip>
#include <iostream>
int main() {
  std::cout << std::hexfloat;
  for (int fixture = 0; fixture < 9; ++fixture) {
    int n = 17, m = 29;
    Matrix A(n);
#ifndef LEGACY_MATRIX
    A.reserve(m+n, m*13+n);
#endif
    size_t entries = 0;
    for (int i = 0; i < m; ++i) {
      Row row;
      for (int j = 0; j < i%12; ++j) {
        int col = (i*7+j*3) % n;
        double val = ((i*19+j*11)%31 - 15) / 7.;
        if (fixture == 1) val *= 1e-3;
        if (fixture == 2 && col%3 == 0) val *= 1e3;
        if (fixture == 3 && col%3 == 0) val = 0;
        row.push_back({col,val});
      }
      if (i%3 == 0) { // Exact duplicate column; coalescing changes damping.
        row.push_back({3,1.25}); row.push_back({3,-0.5});
      }
      double rhs = fixture == 4 ? 0 : ((i*17)%13 - 6) / 3.;
      double weight = i%7 == 0 ? 0 : (i%5 + 1)/5.;
      A.add(row,rhs,weight);
      entries += row.size();
    }
#ifndef LEGACY_MATRIX
    assert(A.values.size() == entries && A.offsets.size() == size_t(m+1));
    assert(A.columns.size() == entries && A.rhs.size() == size_t(m));
    assert(Matrix::storage_bytes(m,entries) == (m+1)*sizeof(size_t)+m*sizeof(double)+entries*(sizeof(int)+sizeof(double)));
#endif
    Vec x(n),y(m);
    for(int i=0;i<n;++i) x[i]=(i-8)/11.;
    for(int i=0;i<m;++i) y[i]=(i-7)/13.;
    for(double q:A.mul(x)) std::cout << q << '\n';
    for(double q:A.trans(y)) std::cout << q << '\n';
    for(double damping:{0.,.2,4.}) {
      LSQRInfo info;
      Vec solved=solve(A,damping,&info);
      std::cout << fixture << ' ' << damping << ' ' << info.iterations << ' '
                << info.relative_normal_residual << ' ' << info.converged << '\n';
      for(double q:solved) std::cout << q << '\n';
      for(double q:A.mul(solved)) std::cout << q << '\n';
      // Move consumption must yield precisely the same result as copied input.
      Matrix copied=A;
      LSQRInfo moved_info;
      assert(solve(std::move(copied),damping,&moved_info)==solved);
      assert(moved_info.iterations==info.iterations &&
             moved_info.relative_normal_residual==info.relative_normal_residual &&
             moved_info.converged==info.converged);
    }
  }
}
