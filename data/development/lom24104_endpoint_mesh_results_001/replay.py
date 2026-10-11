#!/usr/bin/env python3
"""Compile the frozen observer and replay the six independent generated starts."""
import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

sys.dont_write_bytecode = True
from summarize import HERE, fresh_output, numeric, read, require, save, sha, verify_package


def interrupted(signum, frame):
    raise RuntimeError('Interrupted by signal ' + str(signum))


def group_members(pgid):
    """Literal Linux group membership, including zombies; absence is not a wait."""
    result=[]
    for path in Path('/proc').iterdir():
        if not path.name.isdigit(): continue
        try:
            raw=(path/'stat').read_text()
        except FileNotFoundError:
            continue
        fields=raw[raw.rfind(')')+2:].split()
        if int(fields[2])==pgid: result.append(int(path.name))
    return sorted(result)


def settle(pgid):
    for sig in (signal.SIGTERM,signal.SIGKILL):
        if not group_members(pgid): return []
        try: os.killpg(pgid,sig)
        except ProcessLookupError: pass
        deadline=time.monotonic()+5
        while time.monotonic()<deadline:
            members=group_members(pgid)
            if not members: return []
            time.sleep(.05)
    return group_members(pgid)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', help='absent directory under repository tmp/')
    parser.add_argument('--cxx', default=os.environ.get('CXX', 'c++'), help='one compiler executable')
    args = parser.parse_args()
    manifest = verify_package(); output = fresh_output(args.output)
    require(Path('/proc/self/stat').is_file(), 'Linux /proc is required for owned-group closure')
    compiler = shutil.which(args.cxx)
    require(compiler is not None, 'Compiler not found')
    # Preserve the compiler's invocation name (for example c++ versus gcc).
    compiler = os.path.abspath(compiler)
    cases = read(HERE/'cases.json')['cases']
    require(len(cases)==6 and len({c['case_id'] for c in cases})==6, 'Six unique independent starts')
    for case in cases:
        numeric(case)  # Validate full original numerical bytes/identity before outputs.
    output.mkdir(); (output/'tmp').mkdir(); native = output/'native'; native.mkdir()
    env = os.environ.copy()
    env.update(LC_ALL='C', OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
               MKL_NUM_THREADS='1', TMPDIR=str(output/'tmp'))
    record = dict(status='running', package_manifest_sha256=manifest, commands=[],
        environment={k:env[k] for k in ('LC_ALL','OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','TMPDIR')},
        native_cases=cases, compiler_calls=0, native_calls=0, interval_calls=0,
        scope='Fresh six-start optimization only; all original budgets and flags retained. No controls or interval/reference regeneration.')
    watched = (signal.SIGINT, signal.SIGTERM)
    handlers = {s:signal.signal(s,interrupted) for s in watched}

    def run(name, command):
        entry = dict(name=name, command=command, return_code=None, child_reaped=False,
                     process_started=False, remaining_group_members=None)
        record['commands'].append(entry); process = None
        with (output/(name+'.stdout')).open('xb') as stdout, (output/(name+'.stderr')).open('xb') as stderr:
            try:
                old_mask = signal.pthread_sigmask(signal.SIG_BLOCK, watched)
                try:
                    process = subprocess.Popen(command, cwd=str(output), env=env,
                        stdout=stdout, stderr=stderr, start_new_session=True,
                        preexec_fn=lambda: signal.pthread_sigmask(signal.SIG_SETMASK,old_mask))
                    entry['pid'] = process.pid
                    entry['process_started'] = True
                finally:
                    signal.pthread_sigmask(signal.SIG_SETMASK,old_mask)
                entry['return_code'] = process.wait(); entry['child_reaped'] = True
                entry['remaining_group_members'] = settle(process.pid)
                require(not entry['remaining_group_members'], name+' left an unsettled process group')
                require(entry['return_code']==0, name+' failed; output preserved without retry')
            except BaseException:
                if process is not None:
                    mask = signal.pthread_sigmask(signal.SIG_BLOCK,watched)
                    try:
                        for sig in (signal.SIGTERM,signal.SIGKILL):
                            try: os.killpg(process.pid,sig)
                            except ProcessLookupError: pass
                        entry['return_code'] = process.wait(); entry['child_reaped'] = True
                        entry['remaining_group_members'] = settle(process.pid)
                    finally:
                        signal.pthread_sigmask(signal.SIG_SETMASK,mask)
                else:
                    entry['launch_failed_without_child'] = True
                    entry['remaining_group_members'] = []
                raise

    try:
        build = read(HERE/'source_manifest.json')['build']
        require(build['language']=='gnu++17' and build['link_libraries']==['gmp','stdc++fs'], 'Frozen build contract')
        binary = output/'observe_solve'
        command = [compiler,'-std=gnu++17']+build['flags']+[str(HERE/build['translation_unit']),
                   '-lgmp','-lstdc++fs','-o',str(binary)]
        record['compiler_calls'] += 1; run('compile',command)
        record['binary_sha256'] = sha(binary)
        suffixes = ('initial.csv','final.csv','attempts.jsonl','accepted_paths.csv','summary.json','acceleration.jsonl')
        for case in cases:
            name = case['case_id']; prefix = native/name
            for suffix in suffixes:
                filename = name+'_'+suffix
                save(native/(filename+'.identifiers.json'),dict(expected_file=filename,identity=case,
                    role='Fixed-polygon output; inherited flags retained, no convergence/first-arrival promotion',
                    scope='Complete generated scientific identity; fresh replay output.'))
            command = [str(binary),str(HERE/'inputs'/case['numeric_input']),str(prefix),name,'1000','24','10000']
            record['native_calls'] += 1; run(name,command)
            summary = read(native/(name+'_summary.json'))
            require(summary['case_id']==name and summary['status']=='completed_bounded_saved_polygon_reoptimization',
                    'Complete case summary required')
            # A bounded unresolved result is a legitimate outcome, not a failure to preserve.
            require(summary['limits']==dict(updates=1000,halvings=24,support_sweeps=10000)
                    and summary['candidate_convergence_status'] is None and not summary['original_flags_modified'],
                    'Unchanged budgets and scientific status')
        run('summarize',[sys.executable,'-B',str(HERE/'summarize.py'),str(output/'saved_summary.json'),
                         '--native-directory',str(native)])
        require(verify_package()==manifest,'Package unchanged during replay')
        record['status']='completed_six_case_replay'
    except BaseException as error:
        record.update(status='failed_preserved',error=type(error).__name__+': '+str(error)); raise
    finally:
        for signum,handler in handlers.items(): signal.signal(signum,handler)
        # Large accepted histories remain in the fresh output tree, without another scan.
        record['owned_groups_absent']=all(e['remaining_group_members']==[] for e in record['commands'])
        record['scalar_output_sha256']=({str(p.relative_to(output)):sha(p) for p in sorted(output.rglob('*'))
            if p.is_file() and (p.name.endswith('_summary.json') or p.name=='saved_summary.json')}
            if record['owned_groups_absent'] else {})
        save(output/'replay.json',record)
    print(json.dumps(dict(status=record['status'],cases=6,output=str(output))))


if __name__=='__main__':
    main()
