#!/usr/bin/env python3
"""Compile the adopted integration sources; no ray or inverse execution."""
import ast
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    plan = json.loads((HERE / 'adoption.json').read_text())
    assert not (HERE / 'compile.json').exists()
    for name, digest in plan['after_sha256'].items():
        assert sha(ROOT / name) == digest, name
        target = HERE / 'source' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(str(ROOT / name), str(target))
    reader = ROOT / 'diagnostics/review_full_dd_geometry.py'
    assert sha(reader) == plan['reader_sha256']
    ast.parse(reader.read_text())
    build = ROOT / 'tmp/full_dd_geometry_adoption_002'
    build.mkdir()
    commands = [['cmake', '-S', str(HERE / 'source'), '-B', str(build)],
                ['cmake', '--build', str(build), '-j', '2']]
    record = dict(status='running', started_utc=datetime.datetime.utcnow().isoformat() + 'Z',
                  adoption_sha256=sha(HERE / 'adoption.json'), commands=[], reader_syntax_passed=True,
                  script_sha256=sha(Path(__file__)), native_evaluations=0)
    active = None
    try:
        for i, argv in enumerate(commands):
            output = HERE / ('compile_' + str(i) + '.log')
            with output.open('x') as log:
                active = subprocess.Popen(argv, cwd=str(ROOT), stdout=log, stderr=subprocess.STDOUT,
                                          env=dict(os.environ, TMPDIR=str(ROOT / 'tmp'), CXX='/usr/bin/c++'),
                                          start_new_session=True)
                code = active.wait()
            record['commands'].append(dict(argv=argv, return_code=code, reaped=True,
                                            log=output.name, log_sha256=sha(output)))
            active = None
            if code:
                raise RuntimeError('Compile command failed: ' + str(code))
        for name, digest in plan['after_sha256'].items():
            assert sha(ROOT / name) == sha(HERE / 'source' / name) == digest, name
        record.update(status='passed', binary=str((build / 'dd').relative_to(ROOT)),
                      binary_sha256=sha(build / 'dd'), compiler_sha256=sha(Path('/usr/bin/c++')),
                      cmake_sha256=sha(Path(shutil.which('cmake'))))
    except BaseException as error:
        if active is not None and active.poll() is None:
            os.killpg(active.pid, signal.SIGTERM)
            try:
                active.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(active.pid, signal.SIGKILL)
                active.wait()
        record.update(status='failed', error=str(error))
        raise
    finally:
        record['finished_utc'] = datetime.datetime.utcnow().isoformat() + 'Z'
        with (HERE / 'compile.json').open('x') as f:
            json.dump(record, f, indent=2, sort_keys=True)
            f.write('\n')
    print(json.dumps(record, sort_keys=True))


if __name__ == '__main__':
    main()
