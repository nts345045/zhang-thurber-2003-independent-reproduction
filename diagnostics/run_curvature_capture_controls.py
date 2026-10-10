#!/usr/bin/env python3
"""Freeze and run invented controls against an existing immutable preparation."""
import csv
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def save(path, value):
    with path.open('x') as f:
        json.dump(value, f, indent=2, sort_keys=True)
        f.write('\n')


def verify(out, prepared):
    count = 0
    for key, base in [('input_sha256', ROOT), ('source_sha256', out / 'source'),
                      ('prepared_file_sha256', out)]:
        for name, digest in prepared[key].items():
            if sha(base / name) != digest:
                raise RuntimeError('Changed prepared pin: ' + key + '/' + name)
            count += 1
    return count


def main():
    if len(sys.argv) != 2:
        raise RuntimeError('Expected prepared controls directory relative to repository')
    out = (ROOT / sys.argv[1]).resolve()
    out.relative_to(ROOT)
    prepared_path = out / 'prepared.json'
    prepared = json.loads(prepared_path.read_text())
    prepared_hash = sha(prepared_path)
    verified = verify(out, prepared)
    fixture = out / 'fixture'
    fixture.mkdir()
    sources = [ROOT / 'diagnostics/check_curvature_capture.cpp', Path(__file__).resolve()]
    for p in sources:
        shutil.copyfile(str(p), str(fixture / p.name))
    source_pins = {str(p.relative_to(ROOT)): sha(p) for p in sources}
    source_pins.update({str(p.relative_to(ROOT)): sha(p) for p in fixture.iterdir()})
    for p in (out / 'source').rglob('*'):
        if p.is_file():
            source_pins[str(p.relative_to(ROOT))] = sha(p)
    header = ROOT / 'diagnostics/curvature_capture.hpp'
    source_pins[str(header.relative_to(ROOT))] = sha(header)
    if sha(header) != sha(out / 'source/diagnostics/curvature_capture.hpp'):
        raise RuntimeError('Maintained and frozen capture headers differ')
    compiler = Path(prepared['compiler'])
    if sha(compiler) != prepared['compiler_sha256']:
        raise RuntimeError('Compiler changed')
    build = ROOT / 'tmp/curvature_capture_invented_001'
    build.mkdir()
    binary = build / 'check_curvature_capture'
    cmd = [str(compiler), '-std=gnu++17', '-O3', '-Wall', '-Wextra', '-Wpedantic',
           '-fopenmp', '-DAUDIT_PRODUCTION_HYBRID', '-DAUDIT_CONE_METRIC',
           '-I' + str((out / 'source/diagnostics').relative_to(ROOT)),
           str((fixture / 'check_curvature_capture.cpp').relative_to(ROOT)),
           '-o', str(binary.relative_to(ROOT)), '-lstdc++fs']
    env = os.environ.copy()
    env.update(TMPDIR=str(ROOT / 'tmp'), OMP_NUM_THREADS='1', PYTHONDONTWRITEBYTECODE='1')
    commands = []
    started = datetime.datetime.utcnow().isoformat() + 'Z'
    for label, command in [('compile', cmd), ('invented_controls', [str(binary.relative_to(ROOT)), str((out / 'results').relative_to(ROOT))])]:
        with (fixture / (label + '_stdout.log')).open('xb') as stdout, (fixture / (label + '_stderr.log')).open('xb') as stderr:
            code = subprocess.call(command, cwd=str(ROOT), env=env, stdout=stdout, stderr=stderr)
        commands.append(dict(label=label, command=command, return_code=code))
        if code:
            break
    completed = len(commands) == 2 and all(c['return_code'] == 0 for c in commands)
    checks = []
    if (out / 'results/checks.csv').exists():
        with (out / 'results/checks.csv').open() as f:
            checks = list(csv.DictReader(f))
    rays = []
    if (out / 'results/invented_ray_parity.csv').exists():
        with (out / 'results/invented_ray_parity.csv').open() as f:
            rays = list(csv.DictReader(f))
    for name, digest in source_pins.items():
        if sha(ROOT / name) != digest:
            raise RuntimeError('Changed control source: ' + name)
    verify(out, prepared)
    if sha(prepared_path) != prepared_hash:
        raise RuntimeError('Preparation changed')
    outputs = {str(p.relative_to(out)): sha(p) for base in [fixture, out / 'results']
               for p in base.rglob('*') if p.is_file()}
    passed = completed and bool(checks) and all(c['passed'] == '1' for c in checks) and len(rays) == 6
    summary = dict(status='passed' if passed else 'failed_preserved', started_utc=started,
                   completed_utc=datetime.datetime.utcnow().isoformat() + 'Z',
                   prepared_sha256=prepared_hash, source_sha256=source_pins,
                   output_sha256=outputs, compiler=str(compiler), compiler_sha256=sha(compiler),
                   commands=commands, verified_prepared_pins=verified,
                   binary=str(binary.relative_to(ROOT)), binary_sha256=sha(binary) if binary.exists() else None,
                   check_count=len(checks), passed_count=sum(c['passed'] == '1' for c in checks),
                   invented_ray_cases=len(rays), ray_results=rays,
                   scope='Invented telemetry and six small invented homogeneous/affine/kink rays; no authoritative ray or production mutation',
                   limitations=['Logging parity is not a first-arrival, accuracy or convergence certificate.',
                                'Manual telemetry records intentionally need not satisfy ray dynamics.',
                                'The frozen unused renamed driver main may produce a return-type warning; it is never called.'])
    save(out / 'controls_summary.json', summary)
    print(json.dumps(dict(status=summary['status'], checks=len(checks), summary_sha256=sha(out / 'controls_summary.json'))))
    return 0 if passed else 1


if __name__ == '__main__':
    sys.exit(main())
