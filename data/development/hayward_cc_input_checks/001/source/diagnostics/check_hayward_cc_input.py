#!/usr/bin/env python3
"""Independent invented adapter/loader controls; never import real CC inputs."""
import argparse
import copy
import csv
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fixture():
    events = [dict(id=str(i), x=str(i), y='0', z='2', t='0',
                   event_resource_id='smi:invented/event'+str(i),
                   origin_resource_id='smi:invented/origin'+str(i)) for i in range(2)]
    channel = dict(x='0', y='0', z='0', t='0', latitude_deg='35', longitude_deg='-122',
                   sensor_z_geoid_km='0', network_code='XX', station_code='TEST', location_code='',
                   channel_code='HHZ', channel_seed_id='XX.TEST..HHZ',
                   channel_fdsn_source_id='FDSN:XX_TEST__H_H_Z')
    stations = [dict(channel, id='0', metadata_epoch_start='1984-01-01T00:00:00Z',
                     metadata_epoch_end='1990-01-01T00:00:00Z', source_sha256='a'*64),
                dict(channel, id='1', metadata_epoch_start='1990-01-01T00:00:00Z',
                     metadata_epoch_end='', source_sha256='b'*64)]
    rows = []
    for i, j, k, kj, kind, value in [(0,-1,0,-1,0,'0.875'), (1,-1,1,-1,0,'0.5'),
                                    (0,1,0,1,1,'0.375')]:
        row = dict(i=str(i), j=str(j), station=str(k), type=str(kind), value=value,
                   station_j=str(kj))
        for side, index in [('i',i),('j',j)]:
            for field in ('event','origin','arrival','pick'):
                row[field+'_'+side+'_resource_id'] = ('smi:invented/'+field+str(index)) if index >= 0 else ''
            row['pick_'+side+'_time_utc'] = ('1989-01-01T00:00:00Z' if index == 0 else '1991-01-01T00:00:00Z') if index >= 0 else ''
            row['pick_'+side+'_uncertainty_s'] = '0.05' if index >= 0 else ''
            row['pick_'+side+'_source_sha256'] = 'c'*64 if index >= 0 else ''
        for field in ('network_code','station_code','location_code','channel_code',
                      'channel_seed_id','channel_fdsn_source_id','metadata_epoch_start','metadata_epoch_end'):
            row[field] = stations[k][field]
        row['channel_source_sha256'] = stations[k]['source_sha256']
        row['metadata_epoch_j_start'] = stations[kj]['metadata_epoch_start'] if j >= 0 else ''
        row['metadata_epoch_j_end'] = stations[kj]['metadata_epoch_end'] if j >= 0 else ''
        row['channel_j_source_sha256'] = stations[kj]['source_sha256'] if j >= 0 else ''
        row.update(cross_metadata_epoch=str(int(j >= 0)), uncertainty_s='0.125',
                   a_priori_weight='0.4', observation_basis='invented catalog reference',
                   note='preserve, "quoted"\ntext')
        rows.append(row)
    exported = {'original_catalog_'+key:value for key,value in rows[2].items()}
    exported.update(original_catalog_original_observation_index='2', measurement_id='local:invented/cc0',
        measurement_status='accepted_discrete_measurement', cc_attempted='1', diagnostics_jsonl_row='0',
        dt_cc_i_minus_j_s='0.3125', cc_delay_j_minus_i_s='0.0625', maximum_cc='0.5',
        maximum_cc_squared='0.25', cc_relative_weight_squared='0.25', cc_formal_timing_uncertainty_s='',
        waveform_i_waveform_raw_sha256='d'*64, waveform_j_waveform_raw_sha256='e'*64,
        waveform_i_window_samples_sha256='f'*64, waveform_j_window_samples_sha256='0'*64,
        dt_cc_export_status='exported', dt_cc_event_i='1', dt_cc_event_j='2', dt_cc_station='TEST',
        dt_cc_phase='P', dt_cc_origin_correction_s='0.0', dt_cc_header_line_number='1', dt_cc_line_number='2')
    event_map = [dict(dt_cc_event_id=str(i+1), original_event_index=str(i),
                      event_resource_id=e['event_resource_id'], origin_resource_id=e['origin_resource_id'],
                      mapping_basis='local original event index plus one') for i,e in enumerate(events)]
    epochs = [dict(s, dt_cc_station='TEST') for s in stations]
    return [list(rows[0]), rows, events, stations, [exported], event_map, epochs,
            '# 1 2 0.0\nTEST 0.3125 0.25 P\n']


def write_table(path, fields, rows):
    op = gzip.open if path.suffix == '.gz' else open
    with op(str(path), 'wt', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
        writer.writeheader(); writer.writerows(rows)


def json_file(path, value):
    path.write_text(json.dumps(value, indent=2)+'\n')


def main(output):
    if not __debug__:
        raise ValueError('Checks require Python assertions; do not use -O')
    output = output.resolve(); output.relative_to(ROOT)
    if output.exists():
        raise ValueError('Use a fresh evidence directory')
    output.mkdir(parents=True)
    source_paths = [ROOT/'prepare_hayward_cc.py', Path(__file__).resolve(),
                    ROOT/'diagnostics/check_hayward_cc_input.cpp', ROOT/'src/main.cpp'] + sorted((ROOT/'src').glob('*.hpp'))
    pins = {str(p.relative_to(ROOT)):sha(p) for p in source_paths}
    for p in source_paths:
        target = output/'source'/p.relative_to(ROOT); target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(str(p), str(target))
    spec = importlib.util.spec_from_file_location('tested_adapter', str(ROOT/'prepare_hayward_cc.py'))
    adapter = importlib.util.module_from_spec(spec); spec.loader.exec_module(adapter)
    checks = []
    def check(name, passed):
        checks.append(dict(name=name, passed=bool(passed)))
        if not passed: raise AssertionError(name)
    def reject(name, args):
        try: adapter.assemble(*args)
        except (ValueError,KeyError,IndexError) as error:
            checks.append(dict(name=name,passed=True,error=str(error))); return
        check(name,False)
    def mutate(name, operation):
        args=copy.deepcopy(base); operation(args); reject(name,args)
    commands=[]
    try:
        base=fixture(); fields,combined=adapter.assemble(*copy.deepcopy(base))
        check('three original rows unchanged in every field/order',
              [{k:r[k] for k in base[0]} for r in combined[:3]]==base[1])
        check('only one reviewed type2 appended',len(combined)==4 and [r['type'] for r in combined]==['0','0','1','2'])
        check('original extra fields blank',all(r[k]=='' for r in combined[:3] for k in fields if k not in base[0]))
        cc=combined[3]
        check('derived sign literal square and blank sigma',cc['value']=='0.3125' and cc['a_priori_weight']=='0.25' and cc['uncertainty_s']=='')
        check('unestimated role and objective power explicit',cc['cc_uncertainty_status']=='unestimated' and cc['solver_objective_quality_power']=='4' and cc['solver_weight_basis']=='literal_legacy_CC_squared_row_multiplier' and 'reference catalog picks' in cc['provider_pick_identity_role'])
        check('every exported field retained exactly',all(cc[k]==v for k,v in base[4][0].items()))
        check('distinct epochs empty location and quoted metadata retained',cc['station']=='0' and cc['station_j']=='1' and cc['location_code']=='' and cc['metadata_epoch_end']=='1990-01-01T00:00:00Z' and cc['metadata_epoch_j_end']=='' and cc['note']==base[1][2]['note'])
        # Alter reference provenance while leaving numeric solver indices intact.
        for field in ('event_i_resource_id','origin_j_resource_id','pick_i_resource_id','arrival_j_resource_id',
                      'channel_seed_id','channel_fdsn_source_id','location_code','metadata_epoch_start',
                      'metadata_epoch_j_start','channel_j_source_sha256','value','a_priori_weight','note'):
            mutate('reject changed exact source field '+field,lambda a,k=field:a[4][0].__setitem__('original_catalog_'+k,'changed'))
        mutations=[
            ('wrong original row index',lambda a:a[4][0].__setitem__('original_catalog_original_observation_index','0')),
            ('duplicate original sidecar row',lambda a:a[4].append(copy.deepcopy(a[4][0]))),
            ('wrong event origin in native table',lambda a:a[2][1].__setitem__('origin_resource_id','smi:invented/wrong-origin')),
            ('wrong second receiver epoch',lambda a:a[3][1].__setitem__('metadata_epoch_start','1992-01-01T00:00:00Z')),
            ('different physical second receiver',lambda a:a[3][1].__setitem__('z','0.000000000001')),
            ('missing pick identity',lambda a:a[1][2].__setitem__('pick_j_resource_id','')),
            ('existing catalog type2',lambda a:a[1][2].__setitem__('type','2')),
            ('negative catalog prior',lambda a:a[1][0].__setitem__('a_priori_weight','-1')),
            ('extra native event map',lambda a:a[5].append(dict(a[5][0],original_event_index='7'))),
            ('replaced native origin map',lambda a:a[5][1].__setitem__('origin_resource_id','smi:invented/wrong-map')),
            ('missing second epoch mapping',lambda a:a[6].pop()),
            ('changed full receiver field',lambda a:a[6][1].__setitem__('source_sha256','1'*64)),
            ('accepted row without diagnostics',lambda a:a[4][0].__setitem__('diagnostics_jsonl_row','')),
            ('invented CC sigma',lambda a:a[4][0].__setitem__('cc_formal_timing_uncertainty_s','0.01')),
            ('unsquared prior reinterpretation',lambda a:a[4][0].__setitem__('cc_relative_weight_squared','0.5')),
            ('nonfinite accepted coefficient',lambda a:a[4][0].__setitem__('maximum_cc','nan')),
            ('wrong measured delay sign',lambda a:a[4][0].__setitem__('cc_delay_j_minus_i_s','-0.0625')),
            ('nonzero additional origin correction',lambda a:a[4][0].__setitem__('dt_cc_origin_correction_s','1')),
            ('legacy wrong value',lambda a:a.__setitem__(7,'# 1 2 0.0\nTEST -0.3125 0.25 P\n')),
            ('legacy wrong prior',lambda a:a.__setitem__(7,'# 1 2 0.0\nTEST 0.3125 0.5 P\n')),
            ('legacy extra unassociated line',lambda a:a.__setitem__(7,a[7]+'TEST 0.3125 0.25 P\n')),
            ('reversed legacy header',lambda a:a.__setitem__(7,'# 2 1 0.0\nTEST 0.3125 0.25 P\n')),
            ('accepted status disagreement',lambda a:a[4][0].__setitem__('measurement_status','coherence_failed')),
            ('metadata field collision',lambda a:[r.__setitem__('type','2') for r in a[4]])]
        for name,operation in mutations:mutate('reject '+name,operation)
        rejected=copy.deepcopy(base); rr=rejected[4][0]
        rr.update(measurement_status='coherence_failed',dt_cc_export_status='not_accepted',dt_cc_i_minus_j_s='',cc_relative_weight_squared='',dt_cc_line_number='')
        rejected[6]=[];rejected[7]=''
        _,kept=adapter.assemble(*rejected)
        check('unaccepted measurement remains provenance not solver row',len(kept)==3)

        # A wholly invented reviewed-export envelope tests real path/hash gates.
        fixture_dir=output/'fixtures';catalog=fixture_dir/'catalog';exported=fixture_dir/'export'
        catalog.mkdir(parents=True);exported.mkdir()
        write_table(catalog/'observations.csv',base[0],base[1])
        write_table(catalog/'initial_events.csv',list(base[2][0]),base[2])
        write_table(catalog/'stations.csv',['id','x','y','z','t']+[k for k in base[3][0] if k not in ('id','x','y','z','t')],base[3])
        (catalog/'initial_grid.csv').write_text('x,y,z,v\n0,0,0,5\n')
        (catalog/'authoritative_ids_required').write_text('Invented identity-validation fixture; not real observations.\n')
        write_table(exported/'dt.cc.identifiers.csv.gz',list(base[4][0]),base[4])
        write_table(exported/'event_id_map.csv',list(base[5][0]),base[5])
        write_table(exported/'receiver_epochs.csv.gz',list(base[6][0]),base[6])
        (exported/'dt.cc').write_text(base[7])
        export_summary=dict(status='completed_identified_dt_cc_export',solver_observations_added=0,original_catalog_values_changed=False,
            retained_original_catalog_pairs=1,exported_observations=1,
            input_source_sha256={str((catalog/name).relative_to(ROOT)):sha(catalog/name) for name in ('observations.csv','initial_events.csv','stations.csv')},
            output_sha256={p.name:sha(p) for p in exported.iterdir()})
        summary_path=exported/'summary.json';execution_path=exported/'execution.json';review_path=exported/'review.json'
        json_file(summary_path,export_summary)
        execution=dict(status='completed',return_code=0,summary_sha256=sha(summary_path),network_requests=0)
        json_file(execution_path,execution)
        review=dict(status='passed',export_summary_sha256=sha(summary_path),export_execution_sha256=sha(execution_path),
                    measurements_summary_sha256='2'*64,measurements_review_sha256='3'*64)
        json_file(review_path,review)
        prepared=fixture_dir/'prepared'
        result=adapter.run(catalog,summary_path,review_path,prepared)
        check('invented run prepares exact counts without config or solver',result['original_catalog_rows']==3 and result['appended_cc_rows']==1 and result['prepared_rows']==4 and result['solver_invocations']==0 and not (prepared/'run.cfg').exists())
        check('original catalog bytes and geometry preserved',sha(catalog/'observations.csv')==sha(prepared/'catalog_provenance/observations.csv') and all(sha(catalog/n)==sha(prepared/n) for n in ('initial_events.csv','stations.csv','initial_grid.csv','authoritative_ids_required')))
        before={str(p):sha(p) for p in list(catalog.iterdir())+list(exported.iterdir())}
        def run_reject(name,out):
            try:adapter.run(catalog,summary_path,review_path,out)
            except (ValueError,KeyError) as error:
                checks.append(dict(name=name,passed=True,error=str(error)));return
            check(name,False)
        run_reject('reject existing output',prepared)
        run_reject('reject output beneath original inputs',catalog/'new')
        run_reject('reject output beneath export evidence',exported/'new')
        stale=dict(review,export_summary_sha256='4'*64);json_file(review_path,stale)
        run_reject('reject stale independent export review',fixture_dir/'stale_review_output')
        json_file(review_path,review)
        changed=dict(execution,return_code=1);json_file(execution_path,changed)
        json_file(review_path,dict(review,export_execution_sha256=sha(execution_path)))
        run_reject('reject reviewed failed export execution',fixture_dir/'failed_execution_output')
        json_file(execution_path,execution);json_file(review_path,review)
        original=(catalog/'observations.csv').read_bytes();(catalog/'observations.csv').write_bytes(original+b'\n')
        run_reject('reject changed original catalog bytes',fixture_dir/'changed_catalog_output')
        (catalog/'observations.csv').write_bytes(original)
        original=(exported/'dt.cc').read_bytes();(exported/'dt.cc').write_bytes(original+b'\n')
        run_reject('reject changed legacy payload bytes',fixture_dir/'changed_legacy_output')
        (exported/'dt.cc').write_bytes(original)
        check('all invented pinned input bytes restored',all(sha(Path(p))==h for p,h in before.items()))

        # Compile only the frozen component and canonical sources. No solver CLI
        # is invoked; supplied Ray values exercise the actual row code directly.
        (prepared/'component.cfg').write_text('authoritative_ids_required 1\ncatalog_only_dd 0\npair_distance 10\n'+''.join('stage%d_%s_weight 1\n'%(s,t) for s in (1,2,3) for t in ('absolute','catalog','precise')))
        build=ROOT/'tmp/hayward_cc_input_checks'/output.name;build.mkdir(parents=True,exist_ok=False)
        env=dict(os.environ,TMPDIR=str(build),OMP_NUM_THREADS='1')
        def execute(name,argv):
            command=[str(x) for x in argv];commands.append(dict(name=name,argv=command))
            with (output/(name+'.stdout.log')).open('x') as out,(output/(name+'.stderr.log')).open('x') as err:
                code=subprocess.call(command,cwd=str(ROOT),env=env,stdout=out,stderr=err)
            commands[-1]['return_code']=code
            check(name+' returned zero',code==0)
        binary=build/'component'
        execute('compile',['g++','-std=c++17','-O2','-fopenmp',output/'source/diagnostics/check_hayward_cc_input.cpp','-lstdc++fs','-o',binary])
        execute('component',[binary,prepared,output/'component_result.json'])
        component=json.loads((output/'component_result.json').read_text())
        check('actual loader Matrix objective and metadata component passes',component['status']=='passed' and component['conditional_objective_ratio']==0.0625 and component['ray_traces']==component['inverse_solves']==0)
        for path,digest in pins.items():check('source unchanged '+path,sha(ROOT/path)==digest)
        report=dict(status='passed',scope='Independent invented Python adapter plus actual C++ loader/weight/Matrix controls; no real import, ray trace or inverse solve.',
            checks=checks,source_sha256=pins,commands=commands,binary_sha256=sha(binary),component=component)
    except Exception as error:
        report=dict(status='failed',error=repr(error),checks=checks,source_sha256=pins,commands=commands)
        json_file(output/'summary.json',report)
        raise
    report['output_sha256']={str(p.relative_to(output)):sha(p) for p in output.rglob('*') if p.is_file()}
    json_file(output/'summary.json',report)
    print(json.dumps(dict(status=report['status'],python_checks=len(checks),cpp_checks=component['checks'])))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    main(parser.parse_args().output)
