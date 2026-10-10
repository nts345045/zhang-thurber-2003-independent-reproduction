#!/usr/bin/env python3
"""Check boundary endpoint derivatives on a frozen path, without optimization."""
import argparse
import csv
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from observe_loma_initial_failure import ROOT, records, require, sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('observer', 'output', 'build'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    os.chdir(str(ROOT))
    observer, out, build = [(ROOT / p).resolve() for p in (args.observer, args.output, args.build)]
    for p in (observer, out, build):
        p.relative_to(ROOT)
        require(p != ROOT, 'Do not use repository root')
    for a, b in ((observer, out), (observer, build), (out, build)):
        require(a != b and a not in b.parents and b not in a.parents, 'Overlapping evidence/output')
    require(not out.exists() and not build.exists(), 'Require fresh output/build')
    original = json.loads((observer / 'summary.json').read_text())
    require(original['status'] == 'completed_with_original_flags_preserved' and
            original['selected_full_preflight_result_matches'] and
            original['observed_paths_and_arrays_match_unobserved'], 'Require completed neutral observer')
    for name, digest in original['output_sha256'].items():
        p = (observer / name).resolve(); p.relative_to(observer)
        require(sha(p) == digest, 'Observer artifact changed: ' + name)
    require(sha(Path(original['compiler'])) == original['compiler_sha256'], 'Compiler changed')
    out.mkdir(parents=True); build.mkdir(parents=True)
    summary = dict(status='preparing', started_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                   scope='Fixed polygon subdivision and tied-knot chain rule; no tracing, optimization, inverse or flag change',
                   input_sha256={}, commands=[], native_context=original['native_context'])

    def save():
        temp = out / 'summary.json.new'
        temp.write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n')
        temp.replace(out / 'summary.json')

    def copy(source, destination):
        destination.parent.mkdir(parents=True, exist_ok=True)
        digest = sha(source)
        shutil.copyfile(str(source), str(destination))
        require(sha(destination) == digest, 'Copy mismatch')
        summary['input_sha256'][str(source.relative_to(ROOT))] = digest

    def command(name, argv):
        record = dict(stage=name, command=[str(p.relative_to(ROOT)) if isinstance(p, Path) else p for p in argv])
        summary['commands'].append(record); save()
        started = time.time()
        with (out / (name + '_stdout.log')).open('w') as stdout, (out / (name + '_stderr.log')).open('w') as stderr:
            result = subprocess.run(record['command'], stdout=stdout, stderr=stderr,
                                    env=dict(os.environ, OMP_NUM_THREADS='1', TMPDIR=str(ROOT / 'tmp')))
        record.update(return_code=result.returncode, seconds=time.time() - started); save()
        require(result.returncode == 0, name + ' failed')

    try:
        for name in ('paths.csv', 'identified_ray.csv', 'summary.json', 'inputs/initial_grid.csv'):
            copy(observer / name, out / 'inputs' / Path(name).name)
        for p in (observer / 'source/src').iterdir():
            if p.is_file():
                copy(p, out / 'source/src' / p.name)
        for name in ('check_boundary_endpoint.cpp', 'run_boundary_endpoint_check.py', 'observe_loma_initial_failure.py'):
            copy(ROOT / 'diagnostics' / name, out / 'source/diagnostics' / name)
        binary = build / 'check'
        command('compile', [original['compiler'], '-std=gnu++17', '-O3', '-Wall', '-Wextra', '-Wpedantic', '-fopenmp',
                            out / 'source/diagnostics/check_boundary_endpoint.cpp', '-lstdc++fs', '-o', binary])
        summary['binary_sha256'] = sha(binary)
        # Independent exact values for a unit horizontal edge at z=1 in v=5+z.
        fixtures = out / 'invented'; fixtures.mkdir()
        with (fixtures / 'grid.csv').open('w', newline='') as stream:
            writer = csv.writer(stream, lineterminator='\n'); writer.writerow(['x','y','z','v'])
            for z in (0, 1):
                for y in (-1, 1):
                    for x in (-2, 2):
                        writer.writerow([x, y, z, 5+z])
        (fixtures / 'path.csv').write_text('run_id,observation_index,node,x,y,z\ninvented,invented,0,0,0,1\ninvented,invented,1,1,0,1\n')
        command('invented', [binary, fixtures / 'grid.csv', fixtures / 'path.csv', 'invented', fixtures / 'result.csv'])
        checks = []
        control = records(fixtures / 'result.csv')
        require([int(r['leading_subsegments']) for r in control] == [1,2,4,8,16], 'Incomplete invented control')
        for row in control:
            n = int(row['leading_subsegments'])
            for field, exact in [('action_s',1/6), ('fixed_inserted_source_dx',-1/6),
                                 ('fixed_inserted_source_dz',-1/(72*n)), ('tied_inserted_source_dz',-1/72),
                                 ('analytic_fixed_source_dz_s_per_km',-1/(72*n))]:
                error = abs(float(row[field])-exact)
                allowance = 64*sys.float_info.epsilon*abs(exact)
                checks.append(dict(subsegments=n, field=field, error=error, arithmetic_allowance=allowance,
                                   passed=error <= allowance))
        require(all(c['passed'] for c in checks), 'Invented closed-form derivative/action control failed')
        summary['invented_checks'] = checks
        (fixtures / 'README.md').write_text('Invented unit horizontal edge at depth 1 km in v=5+z km/s.\n'
            'Exact action=1/6 s; fixed inserted-knot normal derivative=-1/(72 n) s/km;\n'
            'affinely tied inserted-knot derivative=-1/72 s/km. The 64-epsilon allowance\n'
            'only checks floating-point algebra against these exact values.\n')
        selected = min(original['results'], key=lambda r: float(r['time_s']))
        command('native', [binary, out / 'inputs/initial_grid.csv', out / 'inputs/paths.csv', selected['run_id'], out / 'subdivision.csv'])
        values = records(out / 'subdivision.csv')
        require([int(r['leading_subsegments']) for r in values] == [1,2,4,8,16], 'Incomplete native subdivision')
        require(all(r['observation_index'] == str(original['pair_index']) and r['run_id'] == selected['run_id'] for r in values),
                'Native pair/run mapping changed')
        require(all(math.isfinite(float(value)) for row in values for key,value in row.items()
                    if key not in ('run_id','observation_index')), 'Nonfinite native scalar')
        require(all(float(values[0]['original_source_d'+axis]) == float(selected['source_d'+axis]) for axis in 'xyz'),
                'Original segment source derivative changed')
        identities = dict(file='subdivision.csv', file_sha256=sha(out / 'subdivision.csv'),
                          join_keys=['run_id','observation_index'], native_context=original['native_context'],
                          original_observer_summary_sha256=sha(observer / 'summary.json'),
                          provider_identity_basis='Provider catalog and receiver geometry; saved initial coordinates are synthetic perturbations')
        (out / 'subdivision.csv.identifiers.json').write_text(json.dumps(identities, indent=2) + '\n')
        for name, digest in summary['input_sha256'].items():
            require(sha(ROOT / name) == digest, 'Frozen input changed during diagnostic: ' + name)
        summary.update(status='completed_scalar_subdivision_diagnostic', original_local_flag=selected['converged'],
                       results=values, limitations=[
                           'Exact subdivision preserves the saved geometric curve; binary insertion collinearity and action differences are reported.',
                           'Holding inserted knots fixed changes the endpoint variation family. Tied-knot contraction recovers the original family.',
                           'No optimized travel-time derivative is substituted, no stopping flag is changed, and no production correction is implemented.'])
        summary['output_sha256'] = {str(p.relative_to(out)):sha(p) for p in out.rglob('*')
                                   if p.is_file() and p.name not in ('summary.json','summary.json.new')}
    except BaseException as error:
        summary.update(status='failed', failure=repr(error)); save(); raise
    summary['finished_utc'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    save(); print(str(out / 'summary.json'), flush=True)


if __name__ == '__main__':
    main()
