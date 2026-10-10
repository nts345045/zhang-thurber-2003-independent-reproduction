#!/usr/bin/env python3
"""Build the invented interface case against the frozen Loma run001 core."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='data/development/interface_stationarity/frozen_run001')
    args = parser.parse_args()
    out = (ROOT / args.output).resolve()
    out.relative_to(ROOT)
    if out.exists():
        parser.error('Choose a fresh output directory; preserve previous evidence')
    build = ROOT / 'tmp/interface_stationarity'
    build.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True)
    source = out / 'source'
    frozen = ROOT / 'data/development/loma_geometry_preflight/001/source/src'
    inputs = [(ROOT / 'diagnostics/check_interface_stationarity.cpp', 'diagnostics/check_interface_stationarity.cpp')]
    inputs += [(frozen / name, 'src/' + name) for name in ('core.hpp', 'ray_metric.hpp')]
    for original, relative in inputs:
        target = source / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(str(original), str(target))
    binary = build / ('check_' + hashlib.sha256(str(out.relative_to(ROOT)).encode()).hexdigest()[:12])
    command = ['c++', '-O3', '-std=c++17', '-Wall', '-Wextra', '-Wpedantic',
               str((source/'diagnostics/check_interface_stationarity.cpp').relative_to(ROOT)),
               '-o', str(binary.relative_to(ROOT))]
    environment = dict(os.environ, TMPDIR=str(ROOT/'tmp'))
    result = subprocess.run(command, cwd=str(ROOT), env=environment, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, universal_newlines=True)
    (out/'compile_stdout.txt').write_text(result.stdout)
    (out/'compile_stderr.txt').write_text(result.stderr)
    if result.returncode:
        raise RuntimeError('Component compilation failed')
    executed = subprocess.run([str(binary)], cwd=str(ROOT), env=environment, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, universal_newlines=True)
    (out/'raw_results.json').write_text(executed.stdout)
    (out/'stderr.txt').write_text(executed.stderr)
    if executed.returncode:
        raise RuntimeError('Component execution failed')
    r = json.loads(executed.stdout)
    ray = r['ray']
    error = max(abs(p['time_s']-p['exact_time_s']) for p in r['path_cases'])
    roundoff = 64*sys.float_info.epsilon
    checks = dict(actions_match_exact_formula_at_roundoff=error <= roundoff,
                  ray_attains_proven_global_lower_bound=abs(ray['time_s']-1/3) <= roundoff,
                  exact_minimum_rejected_by_ordinary_gradient_stopping=not ray['converged'] and ray['updates']==0,
                  ordinary_gradient_chooses_right_derivative=abs(ray['projected_gradient']-1/18)<=roundoff,
                  raw_source_dx_is_nonzero_right_cell_partial=abs(ray['source_derivative_s_per_km'][0]-1/36)<=roundoff)
    evidence = dict(scope='Invented bounded interface model evaluated with frozen actual segment/trace; no real geometry or inversion',
                    command='PYTHONDONTWRITEBYTECODE=1 python3 '+str(Path(__file__).resolve().relative_to(ROOT))+' --output '+str(out.relative_to(ROOT)),
                    compile_command=command, run_command=[str(binary.relative_to(ROOT))], TMPDIR='tmp',
                    checks=checks, all_checks_passed=all(checks.values()),
                    maximum_action_formula_error_s=error, arithmetic_tolerance_s=roundoff,
                    model='v(x)=6-2 max(x,0) km/s on x[-1,1], y[0,2], z[-1,1] km',
                    path='S=(0,0,0), P=(p,1,0), R=(0,2,0)',
                    exact_action_s=dict(nonpositive_p='sqrt(1+p^2)/3',positive_p='sqrt(1+p^2)*[-log(1-p/3)]/p',at_zero=1/3),
                    one_sided_internal_derivatives_s_per_km=dict(left=0,right=1/18),
                    global_minimum_proof='v<=6 throughout the box and every endpoint-joining path has length>=2, so T>=1/3. The x=0 straight path attains the bound.',
                    source_derivative=dict(expected_optimized_dx_s_per_km=0,returned_raw_dx_s_per_km=ray['source_derivative_s_per_km'][0],
                        proof='For source x=epsilon<0 the fast-side straight path has O(epsilon^2) excess over 1/3. For epsilon>0, a Snell leg tangent to x=0 plus a nonnegative guide has excess integral_0^epsilon sqrt(1/(6-2x)^2-1/36) dx=O(epsilon^(3/2)). The endpoint-distance/6 lower bound and these feasible upper bounds give derivative zero from both sides.'),
                    input_sha256={str(p.relative_to(ROOT)):sha(p) for p,unused in inputs},
                    runner_sha256=sha(Path(__file__).resolve()),
                    snapshot_sha256={str(p.relative_to(out)):sha(p) for p in source.rglob('*') if p.is_file()},
                    binary_sha256=sha(binary), output_sha256={name:sha(out/name) for name in ('raw_results.json','compile_stdout.txt','compile_stderr.txt','stderr.txt')},
                    limitations=['This counterexample establishes a solver assumption failure, not attribution of an active Loma ray failure.',
                                 'The action itself is nonsmooth for a positive-length interface segment. Splitting quadrature at transverse crossings does not remove this interface cusp.',
                                 'An ordinary-gradient stopping replacement must also address consistent endpoint sensitivities; accepting this ray while keeping its raw source-x partial would retain an error.',
                                 'No production equations, thresholds, flags, inputs or active processes were changed.'])
    (out/'summary.json').write_text(json.dumps(evidence,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(checks=checks,ray=ray,maximum_action_formula_error_s=error),indent=2))
    if not all(checks.values()):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
