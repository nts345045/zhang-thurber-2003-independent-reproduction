#!/usr/bin/env python3
"""Invented serialization and file-I/O controls; never exports real observations."""
import argparse
import collections
import copy
import csv
import hashlib
import json
from pathlib import Path
import shutil

import export_identified_dt_cc as export

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def fixture():
    epochs = []
    for n in range(4):
        station = 'FIX' if n < 2 else 'ALT'
        epochs.append(dict(id=str(n), x=str(n//2), y='2', z='-0.1', latitude_deg='1', longitude_deg='2', sensor_z_geoid_km='-0.1',
            network_code='ZZ', station_code=station, location_code='', channel_code='EHZ',
            channel_seed_id='ZZ.'+station+'..EHZ', channel_fdsn_source_id='FDSN:ZZ_'+station+'__E_H_Z',
            metadata_epoch_start='2000-01-01' if n%2==0 else '2001-01-01', metadata_epoch_end='2001-01-01' if n%2==0 else '',
            source_sha256='a'*64, scope='Invented receiver metadata; no provider record'))
    rows = []
    for n, (i, j, a, b) in enumerate([(0,1,0,1),(0,1,2,3),(1,2,0,1)]):
        cc = .9876543210123456 if n==0 else .8765432101234567
        catalog = -.8400000000000007 if n==0 else .12345678901234566
        delay = .165 if n==0 else -.23456789012345678
        original = dict(original_observation_index=str(101+n), i=str(i), j=str(j), station=str(a), station_j=str(b),
            type='1', observation_basis='catalog P pick difference', value=repr(catalog), uncertainty_s='0.12345', a_priori_weight='0.4567',
            metadata_epoch_start=epochs[a]['metadata_epoch_start'], metadata_epoch_end=epochs[a]['metadata_epoch_end'],
            metadata_epoch_j_start=epochs[b]['metadata_epoch_start'], metadata_epoch_j_end=epochs[b]['metadata_epoch_end'],
            channel_source_sha256=epochs[a]['source_sha256'], channel_j_source_sha256=epochs[b]['source_sha256'])
        original.update({k:epochs[a][k] for k in export.IDENTITY})
        for side, event in [('i',i),('j',j)]:
            for kind in ('event','origin','pick','arrival'):
                original[kind+'_'+side+'_resource_id']='fixture:'+kind+':'+str(event)
        row={export.PREFIX+k:v for k,v in original.items()}
        row.update(measurement_id='local:invented-cc:'+str(n), measurement_status='accepted_discrete_measurement' if n<2 else 'failed_coherence',
            cc_attempted='1', diagnostics_jsonl_row=str(n), dt_cc_i_minus_j_s=repr(catalog-delay) if n<2 else '',
            cc_delay_j_minus_i_s=repr(delay), maximum_cc=repr(cc), maximum_cc_squared=repr(cc**2),
            cc_relative_weight_squared=repr(cc**2) if n<2 else '', cc_formal_timing_uncertainty_s='')
        rows.append(row)
    return rows,epochs


def input_files(base, rows, epochs, defect=None):
    base.mkdir(parents=True)
    ep=base/'epochs.csv.gz';export.csv_save(ep,epochs,list(epochs[0]))
    roster=base/'identified_measurements.csv.gz';export.csv_save(roster,rows,list(rows[0]))
    summary=dict(status='completed_identified_measurements',solver_observations_added=0,original_catalog_values_changed=False,dt_cc_exported=False,
        input_source_sha256={str(ep.relative_to(ROOT)):sha(ep)},output_sha256={roster.name:sha(roster)},
        retained_original_catalog_pairs=len(rows),status_counts=dict(collections.Counter(r['measurement_status'] for r in rows)),
        scope='Invented serializer fixture; not a waveform measurement')
    if defect=='wrong_count':summary['retained_original_catalog_pairs']+=1
    if defect=='wrong_counts':summary['status_counts']['failed_coherence']+=1
    if defect=='changed_catalog_flag':summary['original_catalog_values_changed']=True
    s=base/'summary.json';save(s,summary)
    review=base/'review.json';save(review,dict(status='passed',measurements_summary_sha256='0'*64 if defect=='stale_review' else sha(s),scope='Invented contract review only'))
    execution=dict(status='running' if defect=='incomplete_execution' else 'completed',summary_sha256='0'*64 if defect=='stale_execution' else sha(s),network_requests=0)
    if defect=='nonoffline_execution':execution['network_requests']=1
    save(base/'execution.json',execution)
    if defect=='changed_epoch':
        ep.write_bytes(ep.read_bytes()+b'changed')
    if defect=='changed_roster':
        roster.write_bytes(roster.read_bytes()+b'changed')
    return s,review,ep


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True);args=parser.parse_args()
    out=(ROOT/args.output).resolve();out.relative_to(ROOT);out.mkdir(parents=True)
    sources=[Path(__file__).resolve(),ROOT/'diagnostics/export_identified_dt_cc.py'];frozen=out/'source';frozen.mkdir()
    hashes={str(p.relative_to(ROOT)):sha(p) for p in sources}
    for p in sources:shutil.copyfile(str(p),str(frozen/p.name))
    checks=[]
    def check(name,ok,**details):checks.append(dict(name=name,passed=bool(ok),**details))
    rows,epochs=fixture();text,mapped,events,receivers=export.serialize(rows,epochs)
    lines=text.splitlines();check('exact_pair_header_zero_origin_correction',lines[0]=='# 1 2 0.0' and len(lines)==3)
    for n in range(2):
        values=lines[n+1].split();check('sign_and_binary64_readback_'+str(n),float(values[1])==float(rows[n]['dt_cc_i_minus_j_s']) and float(values[2])==float(rows[n]['maximum_cc_squared']) and values[-1]=='P')
    check('both_positive_and_negative_differentials',float(lines[1].split()[1])<0<float(lines[2].split()[1]))
    check('all_rows_and_original_fields_preserved',len(mapped)==3 and all(all(m[k]==v for k,v in r.items()) for m,r in zip(mapped,rows)))
    check('rejected_row_retained_without_legacy_line',mapped[2]['dt_cc_export_status']=='not_accepted' and mapped[2]['dt_cc_line_number']=='')
    check('line_maps_exact',[(m['dt_cc_line_number'],m['dt_cc_header_line_number']) for m in mapped[:2]]==[(2,1),(3,1)])
    check('event_origin_bijection',[(e['dt_cc_event_id'],e['original_event_index'],e['event_resource_id'],e['origin_resource_id']) for e in events]==[(n+1,n,'fixture:event:'+str(n),'fixture:origin:'+str(n)) for n in range(3)])
    check('both_native_epochs_empty_location',len(receivers)==4 and all(r['location_code']=='' for r in receivers) and receivers[0]['metadata_epoch_start']!=receivers[1]['metadata_epoch_start'])
    check('original_sigma_not_used_as_cc_weight',mapped[0]['original_catalog_uncertainty_s']=='0.12345' and mapped[0]['original_catalog_a_priori_weight']=='0.4567' and float(lines[1].split()[2])!=.4567)
    rejected=copy.deepcopy(rows)
    for r in rejected:r.update(measurement_status='failed_coherence',dt_cc_i_minus_j_s='',cc_relative_weight_squared='')
    empty,rm,em,se=export.serialize(rejected,epochs);check('all_rejected_roster_preserved',empty=='' and len(rm)==3 and len(em)==3 and se==[])

    def rejected_case(name,change):
        r,e=copy.deepcopy(rows),copy.deepcopy(epochs);change(r,e)
        try:export.serialize(r,e);reason=None
        except (ValueError,KeyError) as error:reason=str(error)
        check('reject_'+name,reason is not None,error=reason)

    rejected_case('event_index_collision',lambda r,e:r[1].__setitem__('original_catalog_event_i_resource_id','fixture:event:other'))
    rejected_case('event_origin_ambiguity',lambda r,e:r[1].__setitem__('original_catalog_origin_i_resource_id','fixture:origin:other'))
    rejected_case('negative_event_index',lambda r,e:r[0].__setitem__('original_catalog_i','-1'))
    rejected_case('missing_native_pick',lambda r,e:r[0].__setitem__('original_catalog_pick_j_resource_id',''))
    rejected_case('changed_native_epoch',lambda r,e:r[0].__setitem__('original_catalog_metadata_epoch_j_start','wrong'))
    rejected_case('changed_metadata_hash',lambda r,e:r[0].__setitem__('original_catalog_channel_j_source_sha256','b'*64))
    rejected_case('paired_moved_receiver',lambda r,e:e[1].__setitem__('x','0.01'))
    rejected_case('nonfinite_position',lambda r,e:e[0].__setitem__('z','nan'))
    rejected_case('duplicate_measurement_id',lambda r,e:r[1].__setitem__('measurement_id',r[0]['measurement_id']))
    rejected_case('rejected_row_accepted_value',lambda r,e:r[2].__setitem__('dt_cc_i_minus_j_s','1'))
    rejected_case('wrong_dt_sign',lambda r,e:r[0].__setitem__('dt_cc_i_minus_j_s',repr(-float(r[0]['dt_cc_i_minus_j_s']))))
    rejected_case('formal_sigma_fabricated',lambda r,e:r[0].__setitem__('cc_formal_timing_uncertainty_s','0.01'))
    rejected_case('wrong_cc_weight',lambda r,e:r[0].__setitem__('cc_relative_weight_squared','0.1'))
    rejected_case('nan_dt',lambda r,e:r[0].__setitem__('dt_cc_i_minus_j_s','nan'))
    def large_cc(r,e):r[0].update(maximum_cc='2',maximum_cc_squared='4',cc_relative_weight_squared='4')
    rejected_case('impossible_normalized_cc',large_cc)
    def duplicate(r,e,reverse=False):
        d=copy.deepcopy(r[0]);d['measurement_id']='fixture:new';d['original_catalog_original_observation_index']='999'
        if reverse:
            for a,b in [('i','j'),('station','station_j'),('metadata_epoch_start','metadata_epoch_j_start'),('metadata_epoch_end','metadata_epoch_j_end'),('channel_source_sha256','channel_j_source_sha256')]+[(kind+'_i_resource_id',kind+'_j_resource_id') for kind in ['event','origin','pick','arrival']]:
                ka,kb=export.PREFIX+a,export.PREFIX+b;d[ka],d[kb]=d[kb],d[ka]
            d['original_catalog_value']=repr(-float(d['original_catalog_value']));d['cc_delay_j_minus_i_s']=repr(-float(d['cc_delay_j_minus_i_s']));d['dt_cc_i_minus_j_s']=repr(-float(d['dt_cc_i_minus_j_s']))
        r.append(d)
    rejected_case('duplicate_pair_station_phase',lambda r,e:duplicate(r,e))
    rejected_case('reversed_pair_station_phase',lambda r,e:duplicate(r,e,True))
    def collision(r,e,channel=False):
        for k in [2,3]:
            e[k].update(station_code='FIX',channel_seed_id='ZZ.FIX..HHZ' if channel else 'ZZ.FIX..EHZ',channel_fdsn_source_id='FDSN:ZZ_FIX__H_H_Z' if channel else 'FDSN:ZZ_FIX__E_H_Z',channel_code='HHZ' if channel else 'EHZ')
        for key in export.IDENTITY:r[1][export.PREFIX+key]=e[2][key]
    rejected_case('station_channel_collapse',lambda r,e:collision(r,e,True))
    rejected_case('station_position_collapse',lambda r,e:collision(r,e,False))
    def station_token(r,e):
        for k in [0,1]:e[k].update(station_code='BAD NAME',channel_seed_id='ZZ.BAD NAME..EHZ',channel_fdsn_source_id='FDSN:ZZ_BAD NAME__E_H_Z')
        for key in export.IDENTITY:r[0][export.PREFIX+key]=e[0][key]
    rejected_case('ambiguous_station_token',station_token)

    inputs=input_files(out/'valid_input',rows,epochs);result=export.run(*inputs,out/'valid_output')
    check('run_exact_text_and_sidecar', (out/'valid_output/dt.cc').read_text()==text and export.table(out/'valid_output/dt.cc.identifiers.csv.gz')==[{k:str(v) for k,v in row.items()} for row in mapped])
    check('run_source_and_output_hashes',all(sha(out/'valid_output'/n)==h for n,h in result['output_sha256'].items()))
    check('run_no_solver_import',result['solver_observations_added']==0 and result['original_catalog_values_changed'] is False and result['exported_observations']==2 and result['preserved_unexported_observations']==1)
    try:export.run(*inputs,out/'valid_output');reason=None
    except ValueError as error:reason=str(error)
    check('fresh_export_directory',reason is not None,error=reason)
    empty_inputs=input_files(out/'empty_input',rejected,epochs);empty_result=export.run(*empty_inputs,out/'empty_output')
    check('all_rejected_file_io',empty_result['exported_observations']==0 and (out/'empty_output/dt.cc').read_bytes()==b'' and len(export.table(out/'empty_output/dt.cc.identifiers.csv.gz'))==3)
    for defect in ['stale_review','incomplete_execution','stale_execution','nonoffline_execution','changed_epoch','changed_roster','wrong_count','wrong_counts','changed_catalog_flag']:
        paths=input_files(out/(defect+'_input'),rows,epochs,defect)
        try:export.run(*paths,out/(defect+'_output'));reason=None
        except ValueError as error:reason=str(error)
        check('run_reject_'+defect,reason is not None and not (out/(defect+'_output')).exists(),error=reason)
    for name,h in hashes.items():
        if sha(ROOT/name)!=h:raise ValueError('Source changed during checks: '+name)
    summary=dict(status='passed' if all(c['passed'] for c in checks) else 'failed',scope=__doc__,checks=checks,source_sha256=hashes,
        output_sha256={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()},
        limitations=['Invented serialized values and native identities; no real waveform processing/export or solver import.',
                    'Independent measurement review remains required before any real export.'])
    save(out/'summary.json',summary);print(json.dumps(dict(status=summary['status'],checks=len(checks),failed=[c for c in checks if not c['passed']]),indent=2))
    if summary['status']!='passed':raise SystemExit(1)


if __name__=='__main__':main()
