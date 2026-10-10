#!/usr/bin/env python3
"""Bounded invented core/external/guard checks of a frozen old-kernel candidate."""
import csv
from fractions import Fraction as Q
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()

def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def dump(path, value):
    with Path(path).open('x') as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write('\n')

def read(path):
    with Path(path).open() as f:
        return list(csv.DictReader(f))

def verify(prepared):
    for name, expected in prepared['original_sha256'].items():
        if sha(ROOT / name) != expected:
            raise RuntimeError('Original input/source changed: ' + name)
    for name, expected in prepared['runtime_sha256'].items():
        if sha(name) != expected:
            raise RuntimeError('Compiler/runtime changed: ' + name)
    for name, expected in prepared['output_sha256'].items():
        if sha(HERE / name) != expected:
            raise RuntimeError('Prepared file changed: ' + name)

def main():
    prepared=json.loads((HERE/'prepared.json').read_text())
    review=json.loads((HERE/'prelaunch_review.json').read_text())
    if review.get('status')!='passed' or review.get('prepared_sha256')!=sha(HERE/'prepared.json'):
        raise RuntimeError('Missing passed hash-bound source/preparation review')
    verify(prepared)
    control=ROOT/prepared['controls_review']
    controls=json.loads(control.read_text())
    if controls.get('status')!='passed':raise RuntimeError('Upstream actual-loop controls review is not passed')
    ledger={'status':'running','started_utc':now(),'prepared_sha256':sha(HERE/'prepared.json'),
            'prelaunch_review_sha256':sha(HERE/'prelaunch_review.json'),'commands':[],
            'scope':'Invented core/external/guard fixtures only; no authoritative rays, cohort or inversion.'}
    ledger_path=HERE/'execution.json';dump(ledger_path,ledger)
    def update():
        temporary=HERE/'execution.json.new'
        with temporary.open('w') as f:json.dump(ledger,f,indent=2,allow_nan=False);f.write('\n')
        os.replace(str(temporary),str(ledger_path))
    unsettled_groups = []
    def group_members(pgid):
        result = []
        for entry in Path('/proc').iterdir():
            if not entry.name.isdigit():
                continue
            try:
                fields = (entry / 'stat').read_text().rsplit(')', 1)[1].split()
                if int(fields[2]) == pgid and fields[0] != 'Z':
                    result.append(int(entry.name))
            except (FileNotFoundError, ProcessLookupError):
                continue
        return result
    def signal_group(pgid, sig):
        try:
            os.killpg(pgid, sig)
        except ProcessLookupError:
            pass
    def terminate_and_reap(process):
        # Ignore a second interruption until the original child is reaped and
        # every live compiler/worker in its process group is accounted for.
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        signal_group(process.pid, signal.SIGTERM)
        deadline = time.monotonic() + 10
        while group_members(process.pid) and time.monotonic() < deadline:
            time.sleep(.1)
        if group_members(process.pid):
            signal_group(process.pid, signal.SIGKILL)
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            pass
        deadline = time.monotonic() + 10
        while group_members(process.pid) and time.monotonic() < deadline:
            time.sleep(.1)
        remaining = group_members(process.pid)
        if remaining or process.poll() is None:
            unsettled_groups.append({'pgid': process.pid, 'live_members': remaining,
                                     'direct_child_reaped': process.poll() is not None})
    def interrupted(sig, frame):
        raise RuntimeError('Interrupted by signal ' + str(sig))
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    env = dict(os.environ, OMP_NUM_THREADS='4', OPENBLAS_NUM_THREADS='1', LC_ALL='C',
               TMPDIR=str(ROOT / 'tmp'), PYTHONDONTWRITEBYTECODE='1')
    ledger['environment'] = {k: env[k] for k in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'LC_ALL', 'TMPDIR', 'PYTHONDONTWRITEBYTECODE')}
    def command(stage, cmd):
        stdout, stderr = HERE / 'logs' / (stage + '.stdout.log'), HERE / 'logs' / (stage + '.stderr.log')
        item = {'stage': stage, 'command': cmd, 'started_utc': now()}
        ledger['commands'].append(item)
        ledger['current_stage'] = stage
        update()
        with stdout.open('x') as out, stderr.open('x') as err:
            process = subprocess.Popen(cmd, cwd=str(HERE), env=env, stdout=out, stderr=err, start_new_session=True)
            try:
                item['pid'] = process.pid
                update()
                code = process.wait()
                # A supervisor exit alone does not freeze descendants' logs.
                deadline = time.monotonic() + 10
                while group_members(process.pid) and time.monotonic() < deadline:
                    time.sleep(.1)
                if group_members(process.pid):
                    raise RuntimeError('Live process-group member after supervisor exit')
            except BaseException:
                terminate_and_reap(process)
                item['return_code'] = process.returncode
                item['finished_utc'] = now()
                item['unsettled_groups'] = list(unsettled_groups)
                raise
        item.update({'return_code': code, 'finished_utc': now(), 'stdout_sha256': sha(stdout), 'stderr_sha256': sha(stderr)})
        update()
        if code != 0:
            raise RuntimeError(stage + ' failed with code ' + str(code))
    try:
        for name in ('build','logs','results'):(HERE/name).mkdir()
        build=HERE/'build/cmake';source=HERE/'source'
        command('cmake_configure',[prepared['cmake'],'-S',str(source),'-B',str(build),
                                  '-DCMAKE_CXX_COMPILER='+prepared['compiler']])
        command('cmake_build',[prepared['cmake'],'--build',str(build),'-j','2'])
        flags=(build/'CMakeFiles/dd.dir/flags.make').read_text().split('CXX_FLAGS = ',1)[1].splitlines()[0].split()
        if sorted(flags)!=sorted(prepared['flags']):raise RuntimeError('Original optimized assertion-enabled flags changed')
        compiler_rows=[line for line in (build/'CMakeCache.txt').read_text().splitlines()
                       if line.split(':',1)[0]=='CMAKE_CXX_COMPILER']
        if len(compiler_rows)!=1 or '=' not in compiler_rows[0]:
            raise RuntimeError('Missing or ambiguous CMake compiler cache key')
        compiler=compiler_rows[0].split('=',1)[1]
        if sha(compiler)!=prepared['runtime_sha256'][prepared['compiler']]:raise RuntimeError('CMake compiler changed')
        command('compiler_version',[compiler,'--version'])
        command('runtime_libraries',['ldd',str(build/'dd')])
        command('core_validate',[str(build/'dd'),'validate',str(HERE/'results/core')])
        core=read(HERE/'results/core/validation.csv')
        if len(core)!=48 or not all(r['passed']=='1' for r in core):raise RuntimeError('Core validation failed')
        results={}
        for label,name in [('external_input','check_external_inputs.cpp'),('inversion_gate','check_inversion_ray_gate.cpp')]:
            binary=HERE/'build'/label
            command('compile_'+label,[compiler]+flags+[str(source/'diagnostics'/name),'-lstdc++fs','-o',str(binary)])
            dest=HERE/'results'/label
            argv=[str(binary),str(dest)] if label=='inversion_gate' else [str(binary),str(HERE/'results/external_input.json'),str(dest)]
            command(label,argv)
            result=dest/'summary.json' if label=='inversion_gate' else HERE/'results/external_input.json'
            results[label]=json.loads(result.read_text())
            if results[label].get('status')!='passed':raise RuntimeError(label+' fixture failed')
        verify(prepared)
        summary={'status':'passed','prepared_sha256':sha(HERE/'prepared.json'),
                 'controls_review_sha256':sha(control),'core_checks':len(core),'components':results,
                 'flags':flags,'compiler':compiler,'compiler_sha256':sha(compiler),
                 'scope':'Invented core/external/guard fixtures only; no authoritative rays, cohort or inversion.',
                 'limitations':['The adapted trial fixture retains its original inputs/settings and records the actual permitted terminal outcome.',
                                'Only first pure-quality rejection and its subsequent actual ledger/state contracts are required; later current/final guard failure is distinct from no-evaluable-trial exhaustion.',
                                'No whole native trial or inversion acceptance is established.'],
                 'output_sha256':{str(p.relative_to(HERE)):sha(p) for sub in ('build','logs','results') for p in sorted((HERE/sub).rglob('*')) if p.is_file()}}
        dump(HERE/'summary.json',summary)
        ledger.update(status='completed',return_code=0,finished_utc=now(),summary_sha256=sha(HERE/'summary.json'))
        update();print(ledger['summary_sha256'])
    except BaseException as error:
        ledger.update(status='failed_preserved',finished_utc=now(),error=str(error),outputs_stable=not unsettled_groups,unsettled_process_groups=unsettled_groups,
            output_sha256={} if unsettled_groups else {str(p.relative_to(HERE)):sha(p) for sub in ('build','logs','results') if (HERE/sub).exists() for p in sorted((HERE/sub).rglob('*')) if p.is_file()})
        update();raise

if __name__=='__main__':main()
