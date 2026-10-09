#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p tmp/matplotlib tmp/cache tmp/texmf data/hayward figures/hayward
export TMPDIR="$PWD/tmp"
export MPLCONFIGDIR="$PWD/tmp/matplotlib"
export XDG_CACHE_HOME="$PWD/tmp/cache"
export TEXMFVAR="$PWD/tmp/texmf"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-8}"
export OPENBLAS_NUM_THREADS=1
start_seconds=$SECONDS
pids=()
finish() {
  local status=$?
  if (( status != 0 )); then
    for pid in "${pids[@]}"; do kill "$pid" 2>/dev/null || true; done
    for pid in "${pids[@]}"; do wait "$pid" 2>/dev/null || true; done
  fi
  printf 'Exit %s after %s seconds\n' "$status" "$((SECONDS-start_seconds))" > data/hayward/rebuild_result.txt
}
trap finish EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
cmake -S . -B build
cmake --build build -j 2
# Existing raw authoritative responses are reused; no network query is made.
python3 prepare_hayward.py --selection reproduction
python3 - <<'PY'
import hashlib, json, os, subprocess
from datetime import datetime, timezone
from pathlib import Path
root = Path.cwd()
files = [Path('configs/hayward.cfg'), Path('prepare_hayward.py'), Path('rebuild_hayward.sh'),
         Path('build/dd'), *sorted(Path('src').glob('*.*'))]
files += [Path('data/hayward') / name for name in ('initial_events.csv', 'initial_grid.csv',
          'stations.csv', 'observations.csv', 'selection_manifest.json')]
manifest = {'started_utc': datetime.now(timezone.utc).isoformat(),
            'command': './rebuild_hayward.sh', 'modes': ['standard', 'dd', 'loc1d'],
            'omp_threads_per_process': int(os.environ['OMP_NUM_THREADS']),
            'base_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], universal_newlines=True).strip(),
            'sha256': {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
Path('data/hayward/run_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
PY
./build/dd raycheck configs/hayward.cfg data/hayward initial
for mode in standard dd loc1d; do
  ./build/dd invert configs/hayward.cfg data/hayward "$mode" > "data/hayward/${mode}_run.txt" 2>&1 &
  pids+=("$!")
done
for index in "${!pids[@]}"; do
  wait "${pids[$index]}"
  unset 'pids[index]'
done
for mode in standard dd loc1d; do
  ./build/dd raycheck configs/hayward.cfg data/hayward "$mode"
done
./build/dd linearize configs/hayward.cfg data/hayward dd
python3 resolution_hayward.py
python3 plot_hayward.py
python3 audit.py
python3 analyze.py
(cd report && pdflatex -interaction=nonstopmode -halt-on-error report.tex > compile_stdout.txt && pdflatex -interaction=nonstopmode -halt-on-error report.tex >> compile_stdout.txt)
