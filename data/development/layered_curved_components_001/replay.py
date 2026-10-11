#!/usr/bin/env python3
"""Compile and replay the two invented controls in one fresh directory."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys


HERE = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_package():
    manifest = json.loads((HERE / 'manifest.json').read_text())
    for name, expected in manifest['sha256'].items():
        relative = Path(name)
        if relative.is_absolute() or '..' in relative.parts:
            raise RuntimeError('Invalid package manifest path')
        path = HERE / relative
        if path.is_symlink() or not path.is_file() or digest(path) != expected:
            raise RuntimeError('Package hash mismatch: ' + name)
    return digest(HERE / 'manifest.json')


def interrupted(signum, frame):
    raise RuntimeError('Interrupted by signal ' + str(signum))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', help='absent output directory outside this package')
    parser.add_argument('--cxx', default=os.environ.get('CXX', 'c++'),
                        help='one C++ compiler executable, without extra flags')
    args = parser.parse_args()
    manifest_sha256 = verify_package()
    requested = Path(args.output).expanduser().absolute()
    if requested.exists() or requested.is_symlink():
        raise RuntimeError('Output path already exists')
    output = requested.parent.resolve() / requested.name
    if output == HERE or HERE in output.parents:
        raise RuntimeError('Output directory must be outside the scientific package')
    compiler = shutil.which(args.cxx)
    if compiler is None:
        raise RuntimeError('C++ compiler not found: ' + args.cxx)
    compiler = str(Path(compiler).resolve())
    output.mkdir()
    (output / 'tmp').mkdir()
    env = os.environ.copy()
    env.update(LC_ALL='C', OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
               MKL_NUM_THREADS='1', TMPDIR=str(output / 'tmp'))
    record = {'status': 'running', 'package_manifest_sha256': manifest_sha256,
              'commands': [], 'numerical_scope': 'invented controls only'}
    watched_signals = (signal.SIGINT, signal.SIGTERM)
    old_handlers = {s: signal.signal(s, interrupted) for s in watched_signals}

    def run(name, command, stdout_name):
        entry = {'name': name, 'command': command, 'return_code': None,
                 'child_reaped': False}
        record['commands'].append(entry)
        process = None
        with (output / stdout_name).open('xb') as stdout, \
                (output / (name + '.stderr')).open('xb') as stderr:
            try:
                old_mask = signal.pthread_sigmask(signal.SIG_BLOCK, watched_signals)
                try:
                    process = subprocess.Popen(
                        command, cwd=str(output), env=env, stdout=stdout,
                        stderr=stderr, start_new_session=True,
                        preexec_fn=lambda: signal.pthread_sigmask(
                            signal.SIG_SETMASK, old_mask))
                finally:
                    # Any queued signal now sees the assigned child handle.
                    signal.pthread_sigmask(signal.SIG_SETMASK, old_mask)
                entry['return_code'] = process.wait()
                entry['child_reaped'] = True
            except BaseException:
                if process is not None:
                    cleanup_mask = signal.pthread_sigmask(
                        signal.SIG_BLOCK, watched_signals)
                    try:
                        # Include compiler descendants in its private group.
                        for sig in (signal.SIGTERM, signal.SIGKILL):
                            try:
                                os.killpg(process.pid, sig)
                            except ProcessLookupError:
                                pass
                        entry['return_code'] = process.wait()
                        entry['child_reaped'] = True
                    finally:
                        signal.pthread_sigmask(signal.SIG_SETMASK, cleanup_mask)
                raise
        if entry['return_code'] != 0:
            raise RuntimeError(name + ' returned ' + str(entry['return_code']))

    try:
        flags = ['-std=c++17', '-O2', '-Wall', '-Wextra', '-Wpedantic']
        for name in ('check_affine_arrival', 'check_curved_integrals'):
            run('compile_' + name,
                [compiler] + flags + [str(HERE / 'source' / (name + '.cpp')),
                                     '-o', str(output / name)],
                'compile_' + name + '.stdout')
        run('affine', [str(output / 'check_affine_arrival')], 'affine.json')
        run('curved_integrals', [str(output / 'check_curved_integrals'),
                                str(output / 'curved_integrals_summary.json')],
            'curved_integrals.jsonl')
        affine = json.loads((output / 'affine.json').read_text())
        curved = json.loads((output / 'curved_integrals_summary.json').read_text())
        rows = [json.loads(line) for line in
                (output / 'curved_integrals.jsonl').read_text().splitlines()]
        assertions = [row for row in rows if row.get('type') == 'assertion']
        if not (affine['status'] == 'passed' and affine['checks'] == 58
                and affine['failed'] == 0 and len(affine['cases']) == 9
                and all(case['passed'] for case in affine['cases'])):
            raise RuntimeError('Affine result inventory did not pass')
        expected = {'status': 'passed', 'groups': 6, 'checks': 24,
                    'integrate_attempts': 7, 'successful_integrations': 6,
                    'rejected_before_samples': 1, 'subpieces': 27, 'samples': 648,
                    'display_calls': 2, 'real_data_calls': 0,
                    'branch_enumerator_calls': 0, 'optimizer_calls': 0,
                    'interval_certificate': False}
        if not (curved == expected and len(rows) == 44 and len(assertions) == 24
                and all(row['passed'] is True for row in assertions)):
            raise RuntimeError('Nodal result inventory did not pass')
        if verify_package() != manifest_sha256:
            raise RuntimeError('Package manifest changed during replay')
        record['status'] = 'passed'
        record['checks'] = {'affine': 58, 'full_nodal': 24}
    except BaseException as error:
        record['status'] = 'failed'
        record['error'] = type(error).__name__ + ': ' + str(error)
        raise
    finally:
        for signum, handler in old_handlers.items():
            signal.signal(signum, handler)
        record['output_sha256'] = {
            str(path.relative_to(output)): digest(path)
            for path in sorted(output.iterdir()) if path.is_file()}
        with (output / 'replay.json').open('x') as stream:
            json.dump(record, stream, indent=2, sort_keys=True, allow_nan=False)
            stream.write('\n')
    print(json.dumps({'status': 'passed', 'output': str(output),
                      'checks': record['checks']}, sort_keys=True))


if __name__ == '__main__':
    main()
