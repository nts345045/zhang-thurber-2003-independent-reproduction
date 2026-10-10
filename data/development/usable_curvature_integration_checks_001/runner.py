#!/usr/bin/env python3
"""Run the approved bounded checks on an isolated, reviewed source candidate."""
import argparse
import csv
import difflib
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
PREPARED = '9da308676201e909a7be446570f4529067b00f01d814f755905e53ecce6a48c1'
DEPENDENCIES = ['check_inversion_ray_gate.cpp', 'check_external_inputs.cpp',
    'check_fmm_initialization.cpp', 'check_fmm_rotated_affine.cpp', 'first_arrival_fmm.hpp',
    'production_entry_checks.hpp', 'seeded_bending.py',
    'run_fmm_initialization_audit.py', 'run_fmm_rotated_affine.py']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def need(ok, message):
    if not ok:
        raise ValueError(message)


def utc():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def save(path, value):
    temporary = path.with_name(path.name + '.new')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    temporary.replace(path)


def inventory(path):
    return {str(p.relative_to(path)): sha(p) for p in sorted(path.rglob('*')) if p.is_file()}


def live_members(pgid):
    members = []
    for path in Path('/proc').glob('[0-9]*/stat'):
        try:
            fields = path.read_text().rsplit(')', 1)[1].split()
            if int(fields[2]) == pgid and fields[0] != 'Z':
                members.append(int(path.parent.name))
        except (OSError, ValueError, IndexError):
            pass
    return members


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--build', required=True)
    args = parser.parse_args()
    out, build = [(ROOT / p).resolve() for p in (args.output, args.build)]
    for path in (out, build):
        path.relative_to(ROOT)
        need(path != ROOT and not path.exists(), 'Fresh repository subdirectory required')
    need(out not in build.parents and build not in out.parents and out != build, 'Disjoint output/build required')
    candidate = ROOT / 'data/development/usable_curvature_integration_prepared_001'
    need(sha(candidate / 'prepared.json') == PREPARED, 'Changed reviewed candidate')
    prepared = json.loads((candidate / 'prepared.json').read_text())
    need(prepared['status'] == 'prepared_only_not_applied', 'Unexpected candidate state')
    pins = {str((candidate / 'prepared.json').relative_to(ROOT)): PREPARED}
    for name, digest in prepared['prepared_file_sha256'].items():
        path = candidate / name
        need(sha(path) == digest, 'Changed prepared member: ' + name)
        pins[str(path.relative_to(ROOT))] = digest
    for name, digest in prepared['baseline_source_sha256'].items():
        need(sha(ROOT / name) == digest, 'Maintained source changed before snapshot: ' + name)
        pins[name] = digest
    for name in DEPENDENCIES:
        pins['diagnostics/' + name] = sha(ROOT / 'diagnostics' / name)
    pins[str(Path(__file__).resolve().relative_to(ROOT))] = sha(Path(__file__).resolve())
    out.mkdir(parents=True); build.mkdir(parents=True)
    source, workspace = out / 'source', build / 'workspace'
    shutil.copytree(str(candidate / 'after'), str(source))
    (source / 'diagnostics').mkdir()
    (out / 'runner_before').mkdir()
    for name in DEPENDENCIES:
        content = (ROOT / 'diagnostics' / name).read_text()
        if name.startswith('run_fmm_'):
            (out / 'runner_before' / name).write_text(content)
            token = '"src/ray_metric.hpp",' if name == 'run_fmm_initialization_audit.py' else "'src/ray_metric.hpp',"
            addition = ' "src/usable_ray_curvature.hpp",' if token.startswith('"') else " 'src/usable_ray_curvature.hpp',"
            need(content.count(token) == 1, 'Expected unique runner source-list entry')
            updated = content.replace(token, token + addition, 1)
            (out / (name + '.packaging.diff')).write_text(''.join(difflib.unified_diff(
                content.splitlines(True), updated.splitlines(True), fromfile='original/' + name, tofile='copied/' + name)))
            content = updated
        (source / 'diagnostics' / name).write_text(content)
    shutil.copyfile(str(Path(__file__).resolve()), str(out / 'runner.py'))
    shutil.copytree(str(source), str(workspace))
    (workspace / 'tmp').mkdir()
    source_pins = inventory(source)
    summary = dict(status='running', started_utc=utc(), driver_pid=os.getpid(), commands=[],
        candidate_prepared_sha256=PREPARED, input_sha256=pins, source_sha256=source_pins,
        workspace=str(workspace.relative_to(ROOT)), production_sources_changed=False,
        scope='Bounded invented core/guard/identity/analytic first-arrival checks; no real full-cohort tracing or inversion.')
    child = None
    execution = dict(status='running', pid=os.getpid(), started_utc=utc())
    save(out / 'execution.json', execution)

    def interrupted(signum, frame):
        raise InterruptedError('Signal ' + str(signum))

    for signum in (signal.SIGTERM, signal.SIGINT):
        signal.signal(signum, interrupted)

    def run(label, argv, require_success=True, threads=1):
        nonlocal child
        command = list(map(str, argv))
        record = dict(label=label, argv=[s.replace(str(ROOT) + '/', '') for s in command],
            cwd=str(workspace.relative_to(ROOT)), started_utc=utc(), threads=threads, status='running')
        summary['commands'].append(record)
        with (out / (label + '_stdout.log')).open('wb') as stdout, (out / (label + '_stderr.log')).open('wb') as stderr:
            child = subprocess.Popen(command, cwd=str(workspace), stdout=stdout, stderr=stderr, start_new_session=True,
                env=dict(os.environ, OMP_NUM_THREADS=str(threads), OPENBLAS_NUM_THREADS='1',
                         PYTHONDONTWRITEBYTECODE='1', TMPDIR=str(workspace / 'tmp')))
            record['pid'] = child.pid
            save(out / 'summary.json', summary)
            code = child.wait()
        child = None
        record.update(status='completed', return_code=code, finished_utc=utc())
        save(out / 'summary.json', summary)
        need(not require_success or code == 0, label + ' failed; outputs preserved')
        return code

    try:
        compiled = build / 'cmake'
        run('cmake_configure', ['cmake', '-S', workspace, '-B', compiled])
        run('cmake_build', ['cmake', '--build', compiled, '-j', '2'])
        flags = (compiled / 'CMakeFiles/dd.dir/flags.make').read_text().split('CXX_FLAGS = ', 1)[1].splitlines()[0]
        need('-O3' in flags and '-fopenmp' in flags and '-DNDEBUG' not in flags, 'Expected original optimized assertion-enabled flags')
        compiler = Path(next(line.split('=', 1)[1] for line in (compiled / 'CMakeCache.txt').read_text().splitlines()
                            if line.startswith('CMAKE_CXX_COMPILER:FILEPATH=')))
        summary.update(compiler=str(compiler), compiler_sha256=sha(compiler), flags=flags,
                       binary_sha256={'dd': sha(compiled / 'dd')})
        run('compiler_version', [compiler, '--version'])
        run('runtime_libraries', ['ldd', compiled / 'dd'])
        libraries = {}
        for line in (out / 'runtime_libraries_stdout.log').read_text().splitlines():
            for token in line.split():
                if token.startswith('/') and Path(token).is_file():
                    libraries[token] = sha(Path(token))
        summary['runtime_library_sha256'] = libraries
        results = workspace / 'results'; results.mkdir()
        run('core_validate', [compiled / 'dd', 'validate', results / 'core'])
        with (results / 'core/validation.csv').open() as stream:
            checks = list(csv.DictReader(stream))
        need(checks and all(r['passed'] == '1' for r in checks), 'Core validation gate failed')
        summary['core_checks'] = len(checks)
        for label, source_name in [('inversion_gate', 'check_inversion_ray_gate.cpp'), ('external_input', 'check_external_inputs.cpp')]:
            binary = build / label
            run('compile_' + label, [compiler] + flags.split() +
                [workspace / 'diagnostics' / source_name, '-lstdc++fs', '-o', binary])
            summary['binary_sha256'][label] = sha(binary)
            destination = results / label
            command = [binary, destination] if label == 'inversion_gate' else [binary, results / 'external_input.json', destination]
            run(label, command, threads=4)
            result_path = destination / 'summary.json' if label == 'inversion_gate' else results / 'external_input.json'
            result = json.loads(result_path.read_text())
            need(result['status'] == 'passed', label + ' component failed')
            summary[label] = result
        layered = run('layered', [sys.executable, 'diagnostics/run_fmm_initialization_audit.py', '--variant',
            'usable_curvature_001', '--refine', '--order', '2', '--closed-seed-cells', '--production-entry'], False)
        oblique = run('oblique', [sys.executable, 'diagnostics/run_fmm_rotated_affine.py', '--variant',
            'usable_curvature_001', '--production-entry'], False)
        for label, directory in [('layered', 'fmm_initialization_usable_curvature_001'),
                                 ('oblique', 'fmm_rotated_affine_usable_curvature_001')]:
            path = workspace / 'data/development' / directory / 'summary.json'
            need(path.exists(), label + ' summary missing')
            summary[label] = json.loads(path.read_text())
        need(layered == oblique == 0, 'Analytic regression failed; both outcomes preserved')
        for name, digest in pins.items():
            need(sha(ROOT / name) == digest, 'Input/maintained source changed: ' + name)
        need(inventory(source) == source_pins, 'Frozen source changed')
        for name, digest in source_pins.items():
            need(sha(workspace / name) == digest, 'Executed source changed: ' + name)
        need(sha(compiler) == summary['compiler_sha256'], 'Compiler changed')
        summary.update(status='passed', maintained_sources_unchanged=True, executed_sources_unchanged=True,
            limitations=['Only the declared bounded controls are assessed; no general first-arrival or convergence certificate.',
                         'First-arrival child runners differ solely by an added frozen helper dependency.',
                         'No historical full-cohort numerical equivalence or new inverse acceptance is asserted.'])
        execution.update(status='completed', return_code=0)
    except BaseException as error:
        if child is not None:
            for sig, seconds in ((signal.SIGTERM, 2), (signal.SIGKILL, 5)):
                try:
                    os.killpg(child.pid, sig)
                except ProcessLookupError:
                    pass
                deadline = time.monotonic() + seconds
                while live_members(child.pid) and time.monotonic() < deadline:
                    time.sleep(.1)
                if not live_members(child.pid):
                    break
            survivors = live_members(child.pid)
            execution['exception_child'] = dict(pid=child.pid, live_group_survivors=survivors,
                return_code=child.poll() if survivors else child.wait())
        summary.update(status='failed', error=repr(error))
        execution.update(status='interrupted' if isinstance(error, InterruptedError) else 'failed', error=repr(error))
        raise
    finally:
        alive = execution.get('exception_child', {}).get('live_group_survivors', [])
        if not alive:
            for origin, name in [(workspace / 'results', 'results'), (workspace / 'data/development', 'analytic_results')]:
                if origin.exists():
                    shutil.copytree(str(origin), str(out / name))
        summary.update(finished_utc=utc(), partial_hashes_withheld_live_descendants=bool(alive))
        summary['output_sha256'] = {} if alive else {name: digest for name, digest in inventory(out).items()
            if name not in ('summary.json', 'summary.json.new', 'execution.json', 'execution.json.new')}
        save(out / 'summary.json', summary)
        execution.update(finished_utc=utc(), summary_sha256=sha(out / 'summary.json'))
        save(out / 'execution.json', execution)
    print(str(out / 'summary.json'), flush=True)


if __name__ == '__main__':
    main()
