"""Generate an isolated seeded entry point using the unchanged ray optimizer.

The generated header lives in tmp. This avoids maintaining a second copy of
the optimizer or modifying production code during a frozen inversion run.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def write_header(destination, source_path=None):
    source = Path(source_path or ROOT / "src/core.hpp").read_text()
    start = source.index("Ray trace(const Grid &g,")
    body = source.index("  int merged = merge_close_nodes(p), updates = 0;", start)
    end = source.index("\nstruct Entry {", body)
    optimizer = source[body:end]
    if not optimizer.endswith("\n}"):
        raise ValueError("Production trace function boundary changed")
    prefix = r'''// Generated from src/core.hpp by diagnostics/seeded_bending.py.
// Only path initialization differs; the optimizer body is copied unchanged.
#pragma once

Ray bend_seed(const Grid &g, const std::vector<P> &seed, double spacing,
              int maxit = 1000, bool deriv = true) {
  if (!(spacing > 0) || !std::isfinite(spacing) || seed.size() < 2)
    throw std::runtime_error("Invalid seeded ray spacing or path");
  Vec arc(seed.size(), 0);
  for (size_t i = 0; i < seed.size(); ++i) {
    if (!g.contains(seed[i]))
      throw std::runtime_error("Seeded ray must stay inside the model");
    if (i) arc[i] = arc[i-1] + norm(seed[i] - seed[i-1]);
  }
  if (!(arc.back() > 0) || !std::isfinite(arc.back()))
    throw std::runtime_error("Seeded ray has zero or nonfinite length");
  const int count = std::max(2, int(std::ceil(arc.back() / spacing)));
  std::vector<P> p(count + 1);
  p.front() = seed.front();
  p.back() = seed.back();
  size_t next = 1;
  for (int i = 1; i < count; ++i) {
    const double distance = arc.back() * i / count;
    while (next + 1 < arc.size() && arc[next] <= distance) ++next;
    const double fraction = (distance - arc[next-1]) / (arc[next] - arc[next-1]);
    p[i] = seed[next-1] + (seed[next] - seed[next-1]) * fraction;
  }
'''
    Path(destination).write_text(prefix + optimizer + "\n")


if __name__ == "__main__":
    import sys
    write_header(sys.argv[1])
