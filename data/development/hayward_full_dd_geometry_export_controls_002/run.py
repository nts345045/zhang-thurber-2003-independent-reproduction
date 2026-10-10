#!/usr/bin/env python3
"""Owned, bounded invented exporter/readback controls; no inverse or field run."""
import csv
import datetime
import importlib.util
import json
import math
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
spec = importlib.util.spec_from_file_location('geometry_reader', str(HERE / 'review_geometry.py'))
reader = importlib.util.module_from_spec(spec); spec.loader.exec_module(reader)
sha = reader.sha
PREFIX = 'dd_full_linearization_'
OLD = ('matrix','rows','suppressed','columns','smoothing_matrix','smoothing_rows','rays','info')


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def dump(path, value):
    with Path(path).open('x') as f:
        json.dump(value, f, indent=2, sort_keys=True, allow_nan=False); f.write('\n')


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def write_table(path, rows):
    with path.open('w', newline='') as f:
        out = csv.DictWriter(f, fieldnames=list(rows[0])); out.writeheader(); out.writerows(rows)


def verify(prepared):
    for names, base in (('original_sha256', ROOT), ('output_sha256', HERE), ('runtime_sha256', Path('/'))):
        for name, digest in prepared[names].items():
            check(sha(base / name) == digest, 'Changed pin: ' + name)


def main():
    prepared = json.loads((HERE/'prepared.json').read_text())
    prelaunch = json.loads((HERE/'prelaunch_review.json').read_text())
    check(prelaunch.get('status') == 'passed' and prelaunch.get('prepared_sha256') == sha(HERE/'prepared.json'),
          'Require passed source/harness review of this preparation')
    verify(prepared)
    ledger = {'status':'running', 'driver_pid':os.getpid(), 'started_utc':now(), 'commands':[],
              'prepared_sha256':sha(HERE/'prepared.json'), 'prelaunch_review_sha256':sha(HERE/'prelaunch_review.json')}
    dump(HERE/'execution.json', ledger)
    checks, unsettled = [], []
    def update():
        tmp = HERE/'execution.json.new'
        with tmp.open('w') as f:json.dump(ledger,f,indent=2,sort_keys=True);f.write('\n')
        os.replace(str(tmp), str(HERE/'execution.json'))
    def members(group):
        result = []
        for entry in Path('/proc').iterdir():
            if not entry.name.isdigit():continue
            try:
                fields = (entry/'stat').read_text().rsplit(')',1)[1].split()
                if int(fields[2]) == group and fields[0] != 'Z':result.append(int(entry.name))
            except (FileNotFoundError, ProcessLookupError):pass
        return result
    def send(group, sig):
        try:os.killpg(group, sig)
        except ProcessLookupError:pass
    def cleanup(process):
        signal.signal(signal.SIGTERM, signal.SIG_IGN);signal.signal(signal.SIGINT, signal.SIG_IGN)
        send(process.pid, signal.SIGTERM); deadline = time.monotonic()+10
        while members(process.pid) and time.monotonic()<deadline:time.sleep(.1)
        if members(process.pid):send(process.pid, signal.SIGKILL)
        try:process.wait(timeout=10)
        except subprocess.TimeoutExpired:pass
        if process.poll() is None or members(process.pid):unsettled.append(process.pid)
    def interrupted(sig, frame):raise RuntimeError('Interrupted by signal '+str(sig))
    signal.signal(signal.SIGTERM, interrupted);signal.signal(signal.SIGINT, interrupted)
    env = dict(os.environ, OMP_NUM_THREADS='4', OPENBLAS_NUM_THREADS='1', LC_ALL='C',
               TMPDIR=str(ROOT/'tmp'), PYTHONDONTWRITEBYTECODE='1')
    ledger['environment'] = {k:env[k] for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','LC_ALL','TMPDIR','PYTHONDONTWRITEBYTECODE')}
    def command(label, argv, expected=0):
        item = {'label':label, 'argv':argv, 'expected_return_code':expected, 'started_utc':now()}
        ledger['commands'].append(item);update()
        out, err = HERE/'logs'/(label+'.stdout.log'), HERE/'logs'/(label+'.stderr.log')
        with out.open('x') as stdout, err.open('x') as stderr:
            process = subprocess.Popen(argv,cwd=str(HERE),env=env,stdout=stdout,stderr=stderr,start_new_session=True)
            try:
                item['pid']=process.pid;update();code=process.wait()
                if members(process.pid):raise RuntimeError('Live descendant after child exit')
            except BaseException:
                cleanup(process);item['return_code']=process.returncode;item['reaped']=process.poll() is not None;update();raise
        item.update(return_code=code,reaped=True,finished_utc=now(),stdout_sha256=sha(out),stderr_sha256=sha(err));update()
        check(code == expected, label+' unexpected return code '+str(code))
    def record(name, fn):
        try:
            detail = fn();checks.append({'name':name,'passed':True,'detail':detail})
        except Exception as error:
            checks.append({'name':name,'passed':False,'error':str(error),'error_type':type(error).__name__})
    def inputs(name):
        path=HERE/'results'/name;shutil.copytree(str(HERE/'inputs'),str(path));return path
    def rows(path):return list(reader.records(path))
    def rejected(path):
        try:reader.review(path,path/'run.cfg')
        except (ValueError,KeyError,FileNotFoundError) as error:return str(error)
        raise AssertionError('Malformed/failed geometry unexpectedly accepted')
    try:
        for name in ('build','logs','results'):(HERE/name).mkdir()
        binary = {}
        for variant in ('before','after','after_io'):
            binary[variant]=HERE/'build'/variant
            argv=[prepared['compiler']]+prepared['flags']+['-I'+str(HERE/'source'/variant/'src'),
                  str(HERE/'fixture.cpp'),'-lstdc++fs','-o',str(binary[variant])]
            command('compile_'+variant,argv)
        command('compiler_version',[prepared['compiler'],'--version'])
        command('runtime_libraries',['ldd',str(binary['after'])])
        before, after = inputs('actual_before'), inputs('actual_after')
        command('actual_before',[str(binary['before']),'cli',str(before),'actual'])
        command('actual_after',[str(binary['after']),'cli',str(after),'actual'])
        for suffix in OLD:
            def parity(suffix=suffix):
                a,b=before/(PREFIX+suffix+'.csv'),after/(PREFIX+suffix+'.csv')
                check(a.read_bytes()==b.read_bytes(),'Original output differs: '+suffix)
                return {'sha256':sha(a),'bytes':a.stat().st_size}
            record('eight_file_parity_'+suffix,parity)
        def actual_review():
            result=reader.review(after,after/'run.cfg');dump(HERE/'results/actual_geometry_review.json',result);return result
        record('actual_geometry_readback',actual_review)
        def omitted():
            exported=rows(after/(PREFIX+'rows.csv'));geom=rows(after/(PREFIX+'ray_geometry.csv'))
            check(exported[3]['active']=='0' and (1,0) in [(int(r['event']),int(r['station'])) for r in geom],
                  'Zero-prior-only native support omitted')
            return {'omitted_observation':3,'retained_pair':[1,0]}
        record('zero_prior_native_support',omitted)
        def point():
            native=rows(after/'dd_events.csv')[0];geom=rows(after/(PREFIX+'ray_geometry.csv'))[0]
            check(float(native['x'])!=1/3 and float(native['x'])==float(geom['source_x']),
                  'Saved 12-digit point not used exactly')
            return {'saved_input':native['x'],'new_serialization':geom['source_x'],'earlier_fixture_value':1/3}
        record('parsed_saved_model_point',point)
        cases=json.loads((HERE/'cases.json').read_text())
        throwing={'empty','nan_path','nan_time','nan_source','short_dv','short_length','wrong_array','io_geometry','io_paths'}
        for case in cases['array_cases']:
            path=inputs('array_'+case)
            if case=='unattempted':(path/'run.cfg').write_text((path/'run.cfg').read_text().replace('ray_initializer 1','ray_initializer 0'))
            command('array_'+case,[str(binary['after_io' if case.startswith('io_') else 'after']),'arrays',str(path),case])
            def array_check(case=case,path=path):
                outcome=rows(path/'writer_outcome.csv')[0]
                check((outcome['threw']=='1')==(case in throwing),'Wrong original exporter failure behavior')
                if case=='wrong_array':
                    check(not (path/(PREFIX+'ray_geometry.csv')).exists() and not (path/(PREFIX+'ray_paths.csv')).exists(),
                          'Incomplete Ray inventory fabricated outputs')
                    check('Incomplete full-linearization ray array' in outcome['error'],'Wrong array-size failure')
                elif case.startswith('io_'):
                    suffix='ray_geometry' if case=='io_geometry' else 'ray_paths'
                    check('Cannot finish writing ' in outcome['error'] and suffix in outcome['error'],'Expected real checked-close error')
                    check(not (path/(PREFIX+'matrix.csv')).exists(),'Assembly followed I/O failure')
                else:
                    geom=rows(path/(PREFIX+'ray_geometry.csv'));nodes=rows(path/(PREFIX+'ray_paths.csv'))
                    check(len(geom)==3,'Failed-ray native support not retained')
                    check(len(nodes)==(6 if case=='empty' else 9),'Failed path-node inventory changed')
                    if case in ('short_dv','short_length'):
                        check(geom[0]['ray_derivatives_evaluated']=='0' and all(geom[0]['source_d'+a]=='' for a in 'xyz'),
                              'Missing derivatives represented as evaluated zeros')
                    if case=='empty':check(geom[0]['ray_path_points']=='0','Empty path fabricated nodes')
                    if case=='local':check(geom[0]['ray_converged']=='0','Local failure promoted')
                    if case=='initializer_failed':check(geom[0]['ray_initialization_succeeded']=='0','Initializer failure promoted')
                    if case in ('valid','unattempted'):
                        outcome['readback']=reader.review(path,path/'run.cfg')
                    else:outcome['readback_rejection']=rejected(path)
                return outcome
            record('array_'+case,array_check)
        valid=HERE/'results/array_valid'
        def mutate(path,case):
            names={'geometry':'ray_geometry','paths':'ray_paths','legacy':'rays','rows':'rows','matrix':'matrix','info':'info'}
            tables={key:rows(path/(PREFIX+value+'.csv')) for key,value in names.items()}
            g,p,l,r,m,info=[tables[key] for key in ('geometry','paths','legacy','rows','matrix','info')]
            if case=='missing_pair':g.pop()
            elif case=='duplicate_pair':g.append(g[0].copy())
            elif case in ('wrong_event_id','wrong_origin_id','wrong_channel','wrong_epoch'):
                key={'wrong_event_id':'source_event_resource_id','wrong_origin_id':'source_origin_resource_id',
                     'wrong_channel':'receiver_channel_fdsn_source_id','wrong_epoch':'receiver_metadata_epoch_start'}[case]
                g[0][key]+=':changed'
            elif case=='bad_source_coordinate':g[0]['source_x']=str(float(g[0]['source_x'])+.01)
            elif case=='bad_source_t':g[0]['source_t']=str(float(g[0]['source_t'])+.01)
            elif case=='drop_node':p.pop(1)
            elif case=='duplicate_node':p.insert(1,p[0].copy())
            elif case=='node_order':p[0],p[1]=p[1],p[0]
            elif case=='wrong_count':g[0]['ray_path_points']=str(int(g[0]['ray_path_points'])+1)
            elif case=='bad_source_endpoint':p[0]['x']=str(float(p[0]['x'])+.01)
            elif case=='bad_receiver_endpoint':p[2]['x']=str(float(p[2]['x'])+.01)
            elif case=='outside_node':p[1]['x']='2.0000000000000004'
            elif case.startswith('false_'):
                key={'false_domain':'ray_path_in_domain','false_evaluated':'ray_derivatives_evaluated',
                     'false_finite':'ray_finite','false_local':'ray_converged'}[case];g[0][key]='0'
            elif case=='initializer_failed':g[0]['ray_initialization_succeeded']='0'
            elif case=='initializer_missing':g[0]['ray_initialization_attempted']='0'
            elif case=='bad_node_native':p[1]['source_event_resource_id']+=':changed'
            elif case=='legacy_coordinate':l[0]['source_x']=str(float(l[0]['source_x'])+.01)
            elif case=='legacy_flag':l[0]['ray_converged']='0'
            elif case=='observed_value':r[0]['observed']=str(float(r[0]['observed'])+.01)
            elif case=='observation_metadata':r[0]['observation_note']+=':changed'
            elif case=='second_epoch':
                obs=rows(path/'observations.csv');obs[2]['metadata_epoch_j_start']+=':changed';write_table(path/'observations.csv',obs)
            elif case=='matrix_partial':m[0]['value']=str(float(m[0]['value'])+.01)
            elif case=='missing_matrix_source':m.pop(0)
            elif case=='bad_initializer_config':
                (path/'run.cfg').write_text((path/'run.cfg').read_text().replace('ray_initializer 1','ray_initializer 2'))
            elif case=='info_count':
                for entry in info:
                    if entry['key']=='observed_rays':entry['value']='4'
            elif case.startswith('coordinated_'):
                q,key={
                    'coordinated_absolute_event':(0,'event_i_resource_id'),
                    'coordinated_absolute_origin':(0,'origin_i_resource_id'),
                    'coordinated_dd_event_j':(2,'event_j_resource_id'),
                    'coordinated_dd_origin_j':(2,'origin_j_resource_id'),
                    'coordinated_absent_event_j':(0,'event_j_resource_id'),
                    'coordinated_absent_origin_j':(0,'origin_j_resource_id'),
                    'coordinated_absolute_seed':(0,'channel_seed_id'),
                    'coordinated_absolute_fdsn':(0,'channel_fdsn_source_id'),
                    'coordinated_absolute_location':(0,'location_code'),
                    'coordinated_absolute_epoch_start':(0,'metadata_epoch_start'),
                    'coordinated_absolute_epoch_end':(0,'metadata_epoch_end')}[case]
                obs=rows(path/'observations.csv');obs[q][key]+=':changed';write_table(path/'observations.csv',obs)
                r[q]['observation_'+key]=obs[q][key]
            elif case not in ('duplicate_header','missing_original_file'):raise RuntimeError('Unknown mutation')
            for key,table in tables.items():write_table(path/(PREFIX+names[key]+'.csv'),table)
            if case=='duplicate_header':
                name=path/(PREFIX+'ray_geometry.csv')
                with name.open(newline='') as f:raw=list(csv.reader(f))
                for row in raw:row.append(row[0])
                with name.open('w',newline='') as f:csv.writer(f).writerows(raw)
            if case=='missing_original_file':(path/(PREFIX+'suppressed.csv')).unlink()
        for case in cases['malformed_cases']:
            path=HERE/'results'/('malformed_'+case);shutil.copytree(str(valid),str(path))
            def malformed(case=case,path=path):mutate(path,case);return {'rejection':rejected(path)}
            record('malformed_'+case,malformed)
        for case in cases['preservation_cases']:
            action,suffix,kind=case.split('_');path=inputs('preserve_'+case)
            target=path/(PREFIX+'ray_'+suffix+'.csv')
            if kind=='regular':target.write_text('preserve this exact evidence\n')
            else:target.symlink_to('missing-invented-target')
            original=target.read_bytes() if kind=='regular' else os.readlink(str(target))
            if action=='cli':
                for name in ('dd_events.csv','dd_grid.csv','stations.csv','observations.csv'):(path/name).unlink()
            command('preserve_'+case,[str(binary['after']),'cli' if action=='cli' else 'arrays',str(path),'valid'],1 if action=='cli' else 0)
            def preserved(case=case,path=path,target=target,kind=kind,original=original,action=action):
                check((target.read_bytes() if kind=='regular' else os.readlink(str(target)))==original,'Existing artifact changed')
                error=(HERE/'logs'/('preserve_'+case+'.stderr.log')).read_text() if action=='cli' else rows(path/'writer_outcome.csv')[0]['error']
                check('Refusing prior failure/audit artifact' in error,'Refusal did not precede input/assembly work')
                check(not (path/(PREFIX+'matrix.csv')).exists(),'Assembly happened after prior-file refusal')
                other='ray_paths' if target.name.endswith('_ray_geometry.csv') else 'ray_geometry'
                check(not (path/(PREFIX+other+'.csv')).exists(),'Another new diagnostic was written before prior-file refusal')
                return {'kind':kind,'error':error,'artifact_unchanged':True,
                        'original_link_target':original if kind=='dangling' else None}
            record('preserve_'+case,preserved)
            if kind=='dangling':target.unlink() # Record behavior, not a dangling runtime artifact.
        for kind in ('regular','dangling'):
            target=HERE/'results'/('prior_review_'+kind+'.json')
            if kind=='regular':target.write_text('preserve review\n')
            else:target.symlink_to('missing-invented-review')
            prior=target.read_bytes() if kind=='regular' else os.readlink(str(target))
            command('reader_preserve_'+kind,[prepared['python'],str(HERE/'review_geometry.py'),'--data-dir',str(HERE/'absent'),
                    '--config',str(HERE/'absent.cfg'),'--output',str(target)],1)
            def output_preserved(kind=kind,target=target,prior=prior):
                check((target.read_bytes() if kind=='regular' else os.readlink(str(target)))==prior,'Prior review changed')
                check('preserve existing geometry review' in (HERE/'logs'/('reader_preserve_'+kind+'.stderr.log')).read_text(),
                      'Reader did not refuse before inputs')
                return {'prior_review_unchanged':True}
            record('reader_preserve_'+kind,output_preserved)
            if kind=='dangling':target.unlink()
        verify(prepared)
        expected=11+len(cases['array_cases'])+len(cases['malformed_cases'])+len(cases['preservation_cases'])+2
        check(len(checks)==expected,'Declared check roster incomplete')
        artifacts={str(p.relative_to(HERE)):sha(p) for name in ('results','logs','build') for p in sorted((HERE/name).rglob('*')) if p.is_file()}
        summary={'status':'passed' if all(c['passed'] for c in checks) else 'failed', 'checks':checks,
                 'passed':sum(c['passed'] for c in checks),'total':len(checks),'artifact_sha256':artifacts,
                 'prepared_sha256':sha(HERE/'prepared.json'),'scope':'Six used-pair evaluations across two tiny exports; other Rays supplied, no inverse/field/covariance.',
                 'limitations':'Geometry is a prerequisite only; the first-arrival/final-model/derivative-accuracy questions remain separate.'}
        dump(HERE/'summary.json',summary)
        ledger.update(status='completed',finished_utc=now(),return_code=0 if summary['status']=='passed' else 1,
                      summary_sha256=sha(HERE/'summary.json'),all_direct_children_reaped=True)
        update();print(json.dumps({'status':summary['status'],'passed':summary['passed'],'total':summary['total']}))
        return ledger['return_code']
    except BaseException as error:
        ledger.update(status='failed',finished_utc=now(),failure=str(error),unsettled_groups=unsettled)
        if not unsettled:ledger['partial_checks']=checks
        update();raise


if __name__ == '__main__':
    sys.exit(main())
