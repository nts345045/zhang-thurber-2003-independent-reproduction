#!/usr/bin/env python3
"""Freeze and run an explicitly prepared analytic-truth simulation, without inversion."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parent
MUTABLE_INPUTS = {'truth_events.csv', 'authoritative_geometry'}
NEW_OUTPUTS = ('initial_events.csv', 'arrivals.csv', 'observations.csv',
               'simulation_truth_status.csv', 'simulation_truth_mode.txt')


def sha(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1048576), b''):
            value.update(chunk)
    return value.hexdigest()


def inside(parent, path):
    path = path.resolve()
    path.relative_to(parent.resolve())
    return path


def verify_hashes(parent, hashes):
    for name, expected in hashes.items():
        path = inside(parent, parent / name)
        if sha(path) != expected:
            raise ValueError('Pinned artifact changed: ' + str(path))


def verify_prepared(data):
    path = data / 'analytic_truth_manifest.json'
    manifest = json.loads(path.read_text())
    if manifest['status'] != 'prepared' or manifest['truth_mode'] != 'continuous_layered_reference':
        raise ValueError('Require an explicitly prepared continuous-reference bundle')
    required = {'run.cfg', 'preparation_manifest.json', 'authoritative_geometry',
                'truth_events.csv', 'truth_grid.csv', 'initial_grid.csv', 'stations.csv',
                'analytic_truth/references.csv', 'analytic_truth/provenance/summary.json',
                'analytic_truth/provenance/execution.json', 'analytic_truth/provenance/review.json',
                'analytic_truth/provenance/independent_review.json',
                'analytic_truth/provenance/certificates.jsonl.gz'}
    required.update('analytic_truth/inputs/' + name for name in
                    ('truth_events.csv', 'truth_grid.csv', 'stations.csv'))
    hashes = manifest['prepared_sha256']
    if not required <= set(hashes):
        raise ValueError('Missing pinned geometry, configuration, reference, or review')
    if manifest['source_count'] * manifest['receiver_count'] != manifest['pairs'] or manifest['pairs'] < 1:
        raise ValueError('Invalid prepared Cartesian support')
    verify_hashes(data, hashes)
    for name in ('truth_events.csv', 'truth_grid.csv', 'stations.csv'):
        if hashes[name] != hashes['analytic_truth/inputs/' + name]:
            raise ValueError('Prepared geometry differs from the reviewed truth bundle: ' + name)
    if any((data / name).exists() for name in NEW_OUTPUTS + ('simulation_ray_status.csv',)):
        raise ValueError('Preserve previous simulation outputs; use freshly prepared inputs')
    return manifest, sha(path)


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def atomic_json(path, value):
    temporary = path.with_name(path.name + '.temporary')
    with temporary.open('w') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
    os.replace(str(temporary), str(path))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', required=True)
    parser.add_argument('--build', required=True, help='Fresh project-local build directory')
    parser.add_argument('--threads', type=int, default=4)
    args = parser.parse_args()
    if args.threads < 1:
        parser.error('threads must be positive')
    data, build = [inside(ROOT, ROOT / p) for p in (args.data, args.build)]
    if build.exists() or build == data or data in build.parents or build in data.parents:
        parser.error('Use a fresh build directory separate from prepared data')
    prepared, prepared_hash = verify_prepared(data)
    ledger_path = data / 'simulation_execution.json'
    ledger = dict(status='preparing', started_utc=utc(), driver_pid=os.getpid(),
                  command=sys.argv, threads=args.threads, completed_commands=[],
                  analytic_truth_manifest_sha256=prepared_hash,
                  scope='Synthetic observations from reviewed continuous layered truth; no inverse calculation or forward-solver acceptance')
    with ledger_path.open('x') as stream:
        json.dump(ledger, stream, indent=2); stream.write('\n')
    active = None
    env = dict(os.environ, TMPDIR=str(ROOT / 'tmp'), PYTHONDONTWRITEBYTECODE='1',
               OMP_NUM_THREADS=str(args.threads), OPENBLAS_NUM_THREADS='1')

    def run(command, stage, limited=False):
        nonlocal active
        command = [str(x) for x in command]
        ledger.update(status='running', current_stage=stage, current_command=command,
                      current_command_started_utc=utc(), current_child_pid=None)
        atomic_json(ledger_path, ledger)
        def limit():
            resource.setrlimit(resource.RLIMIT_AS, (128 * 1024**3, 128 * 1024**3))
        with (data / (stage + '_stdout.log')).open('x') as stdout, (data / (stage + '_stderr.log')).open('x') as stderr:
            active = subprocess.Popen(command, cwd=str(ROOT), env=env, stdout=stdout, stderr=stderr,
                                      start_new_session=True, preexec_fn=limit if limited else None)
            ledger['current_child_pid'] = active.pid
            atomic_json(ledger_path, ledger)
            code = active.wait()
        ledger['completed_commands'].append(dict(stage=stage, command=command, pid=active.pid,
                                                return_code=code, finished_utc=utc()))
        active = None
        atomic_json(ledger_path, ledger)
        if code:
            raise subprocess.CalledProcessError(code, command)

    def interrupted(signum, unused):
        raise SystemExit(128 + signum)

    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    try:
        snapshot = build / 'source'
        snapshot.mkdir(parents=True)
        sources = [Path('CMakeLists.txt'), Path(__file__).resolve().relative_to(ROOT)]
        sources += [p.relative_to(ROOT) for p in sorted((ROOT / 'src').iterdir()) if p.is_file()]
        source_hashes = {str(p): sha(ROOT / p) for p in sources}
        for name in sources:
            target = snapshot / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(str(ROOT / name), str(target))
        verify_hashes(ROOT, source_hashes)
        verify_hashes(snapshot, source_hashes)
        def normalize(info):
            info.uid = info.gid = info.mtime = 0
            info.uname = info.gname = ''; info.pax_headers = {}
            return info
        archive = data / 'simulation_source.tar.gz'
        with tarfile.open(str(archive), 'x:gz') as stream:
            for name in sources:
                stream.add(str(snapshot / name), arcname=str(name), filter=normalize)
        original = data / 'inputs_before_simulation'
        original.mkdir()
        for name in sorted(MUTABLE_INPUTS):
            shutil.copyfile(str(data / name), str(original / name))
        verify_hashes(original, {name: prepared['prepared_sha256'][name] for name in MUTABLE_INPUTS})
        run(['cmake', '--version'], 'simulation_cmake_version')
        run(['cmake', '-S', snapshot, '-B', build / 'compiled'], 'simulation_configure')
        cache = (build / 'compiled/CMakeCache.txt').read_text().splitlines()
        compiler = next(line.split('=', 1)[1] for line in cache if line.startswith('CMAKE_CXX_COMPILER:FILEPATH='))
        run([compiler, '--version'], 'simulation_compiler_version')
        run(['cmake', '--build', build / 'compiled', '-j', '2'], 'simulation_compile')
        binary = build / 'compiled/dd'
        run(['ldd', binary], 'simulation_runtime_libraries')
        libraries = {}
        for line in (data / 'simulation_runtime_libraries_stdout.log').read_text().splitlines():
            paths = [word for word in line.split() if word.startswith('/')]
            for name in paths:
                libraries[name] = sha(Path(name))
        command = [binary, 'simulate', data / 'run.cfg', data, '--analytic-truth', data / 'analytic_truth']
        manifest = dict(truth_mode='continuous_layered_reference', prepared_manifest_sha256=prepared_hash,
            base_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=str(ROOT), universal_newlines=True).strip(),
            binary=str(binary.relative_to(ROOT)), binary_sha256=sha(binary),
            compiler=compiler, compiler_sha256=sha(Path(compiler)), runtime_library_sha256=libraries,
            source_sha256=source_hashes, source_directory=str(snapshot.relative_to(ROOT)),
            source_archive_sha256=sha(archive), simulation_command=[str(x) for x in command],
            environment={name: env[name] for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'TMPDIR', 'PYTHONDONTWRITEBYTECODE')},
            address_space_limit_GiB=128, mutable_input_files=sorted(MUTABLE_INPUTS),
            expected_counts=json.loads((data / 'preparation_manifest.json').read_text())['counts'],
            limitations=['Simulation completion does not validate the inverse forward operator or reproduce an inverted manuscript panel.',
                        'The continuous truth timing definition explicitly replaces the generic preparation manifest local-ray definition.',
                        'The full output identity and numerical audit is separate from this execution ledger.'])
        atomic_json(data / 'simulation_run_manifest.json', manifest)
        # Pin prepared bytes again immediately before the executable consumes them.
        verify_prepared(data)
        if sha(data / 'analytic_truth_manifest.json') != prepared_hash:
            raise ValueError('Prepared manifest changed during build')
        verify_hashes(snapshot, source_hashes)
        if sha(binary) != manifest['binary_sha256']:
            raise ValueError('Executable changed before simulation')
        run(command, 'simulate', limited=True)
        if (data / 'simulation_truth_mode.txt').read_text().splitlines()[0] != 'truth_mode continuous_layered_snell_reference':
            raise ValueError('Simulator did not record the explicit analytic truth mode')
        if (data / 'simulation_ray_status.csv').exists():
            raise ValueError('Analytic truth run unexpectedly produced polygon ray flags')
        immutable = {name: digest for name, digest in prepared['prepared_sha256'].items() if name not in MUTABLE_INPUTS}
        verify_hashes(data, immutable)
        verify_hashes(snapshot, source_hashes)
        if sha(binary) != manifest['binary_sha256'] or sha(archive) != manifest['source_archive_sha256']:
            raise ValueError('Frozen executable or source archive changed')
        for name, expected in libraries.items():
            if sha(Path(name)) != expected:
                raise ValueError('Runtime library changed during simulation: ' + name)
        if sha(data / 'analytic_truth_manifest.json') != prepared_hash:
            raise ValueError('Prepared manifest changed during simulation')
        outputs = {name: sha(data / name) for name in NEW_OUTPUTS + tuple(sorted(MUTABLE_INPUTS))}
        outputs.update({p.name: sha(p) for p in data.glob('*_*.log')})
        outputs['simulation_run_manifest.json'] = sha(data / 'simulation_run_manifest.json')
        ledger.update(status='completed', finished_utc=utc(), return_code=0,
                      result_status='simulation_complete_awaiting_independent_output_review',
                      immutable_prepared_files_verified=len(immutable), output_sha256=outputs)
        atomic_json(ledger_path, ledger)
        print('Analytic-truth simulation completed; independent output review and inverse forward validation remain.')
    except BaseException as error:
        if active is not None:
            if active.poll() is None:
                try:
                    os.killpg(active.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass  # The child may have exited after poll().
                try:
                    active.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(active.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    active.wait()
            ledger['exception_child'] = dict(pid=active.pid, return_code=active.returncode)
        ledger.update(status='interrupted' if isinstance(error, (SystemExit, KeyboardInterrupt)) else 'failed',
                      finished_utc=utc(), error=str(error),
                      return_code=getattr(error, 'returncode', getattr(error, 'code', None)))
        atomic_json(ledger_path, ledger)
        raise


if __name__ == '__main__':
    main()
