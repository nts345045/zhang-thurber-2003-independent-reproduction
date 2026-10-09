#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p tmp/matplotlib tmp/cache tmp/texmf data figures report
export TMPDIR="$PWD/tmp"
export MPLCONFIGDIR="$PWD/tmp/matplotlib"
export XDG_CACHE_HOME="$PWD/tmp/cache"
export TEXMFVAR="$PWD/tmp/texmf"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-8}"
start_seconds=$SECONDS
rm -f data/rebuild_result.txt data/rebuild_failure.txt
inversion_pids=()
inversion_labels=()
record_failure() {
  local exit_code=$?
  if (( exit_code != 0 )); then
    for pid in "${inversion_pids[@]}"; do
      kill "$pid" 2>/dev/null || true
    done
    for pid in "${inversion_pids[@]}"; do
      wait "$pid" 2>/dev/null || true
    done
    printf 'Failed rebuild after %s seconds (exit %s)\n' "$((SECONDS-start_seconds))" "$exit_code" | tee data/rebuild_failure.txt >&2
  fi
}
trap record_failure EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
cmake -S . -B build
cmake --build build --clean-first -j 2
./build/dd validate data | tee data/validation_run.txt
for experiment in synthetic recovery joint_recovery synthetic_lom synthetic_lon; do
  ./build/dd generate "configs/${experiment}.cfg" "data/${experiment}"
done
./build/dd raycheck configs/synthetic.cfg data/synthetic

start_inversion() {
  local config=$1 output_dir=$2 mode=$3
  ./build/dd invert "$config" "$output_dir" "$mode" > "${output_dir}/${mode}_run.txt" 2>&1 &
  inversion_pids+=("$!")
  inversion_labels+=("${output_dir}/${mode}")
}
for mode in standard dd loc1d loc3d; do
  start_inversion configs/synthetic.cfg data/synthetic "$mode"
done
start_inversion configs/recovery.cfg data/recovery loc3d
start_inversion configs/joint_recovery.cfg data/joint_recovery dd
start_inversion configs/synthetic_lom.cfg data/synthetic_lom dd
start_inversion configs/synthetic_lon.cfg data/synthetic_lon dd
inversion_status=0
for index in "${!inversion_pids[@]}"; do
  if wait "${inversion_pids[$index]}"; then
    printf 'Completed inversion %s\n' "${inversion_labels[$index]}"
  else
    inversion_status=$?
    printf 'Failed inversion %s (exit %s)\n' "${inversion_labels[$index]}" "$inversion_status" >&2
  fi
  unset "inversion_pids[$index]"
done
if (( inversion_status != 0 )); then
  exit "$inversion_status"
fi

./build/dd raycheck configs/synthetic.cfg data/synthetic standard
./build/dd raycheck configs/synthetic.cfg data/synthetic dd
python3 audit.py
python3 analyze.py
python3 plot.py
(cd report && pdflatex -interaction=nonstopmode -halt-on-error report.tex > compile_stdout.txt && pdflatex -interaction=nonstopmode -halt-on-error report.tex >> compile_stdout.txt)
printf 'Successful rebuild in %s seconds\n' "$((SECONDS-start_seconds))" | tee data/rebuild_result.txt
