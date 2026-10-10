#!/usr/bin/env python3
"""Invented native miniSEED/identity controls; never reads observed waveforms."""
import argparse
import copy
import csv
from fractions import Fraction as Q
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil

import numpy as np
import obspy

import run_native_waveform_cc as runner

ROOT = Path(__file__).resolve().parents[1]
DECODER = ROOT / 'data/authoritative/waveforms/cohort_samples_001/acquire.py'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def table(path, rows):
    with runner.compressed(path) as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader(); writer.writerows(rows)


def fixture(base, defect=None):
    base.mkdir(parents=True); plan = base / 'plan'; plan.mkdir(); samples = base / 'samples'; samples.mkdir()
    (samples / 'raw').mkdir(); (samples / 'source').mkdir()
    shutil.copyfile(str(DECODER), str(samples / 'source/acquire.py'))
    spec = importlib.util.spec_from_file_location('invented_decoder', str(DECODER)); decoder = importlib.util.module_from_spec(spec); spec.loader.exec_module(decoder)
    rng = np.random.default_rng(541038)
    arrays = [rng.integers(-10000, 10001, 500, dtype=np.int32) for unused in range(8)]
    arrays[1][66:322] = arrays[0][50:306]
    arrays[5] = arrays[5][:250]; arrays[7][:] = 12
    metadata = base / 'invented_station_metadata.json'; save(metadata, dict(scope='Invented receiver metadata, not a provider reply'))
    station_hash = sha(metadata); picks, epochs, events, traces = [], [], [], []
    for n in range(8):
        pick_ns = obspy.UTCDateTime('2020-01-01T10:00:00Z').ns + n * 2 * 86400 * 10**9
        pick_time = str(obspy.UTCDateTime(ns=pick_ns)); value = '4.1' if n == 0 else '4.94' if n == 1 else str(Q(40+n,10))
        # Rational strings are converted to decimal seconds for the catalog CSV.
        value = str(float(Q(value)))
        origin_time = str(obspy.UTCDateTime(ns=pick_ns-int(Q(value)*10**9)))
        first_epoch = str(obspy.UTCDateTime(ns=pick_ns-3600*10**9)); last_epoch = str(obspy.UTCDateTime(ns=pick_ns+3600*10**9))
        dip = '' if n == 2 else '0' if n == 3 else '-90'
        orientation = 'dip missing in cached channel metadata' if n == 2 else 'provider-declared nonvertical' if n == 3 else 'provider-declared vertical'
        rate = 50 if n == 5 else 100
        station = dict(id=str(n), x='1' if n == 6 else '0', y='0', z='0', latitude_deg='1', longitude_deg='2', sensor_z_geoid_km='0',
            network_code='ZZ', station_code='FIX', location_code='', channel_code='EHZ', channel_seed_id='ZZ.FIX..EHZ',
            channel_fdsn_source_id='FDSN:ZZ_FIX__E_H_Z', metadata_epoch_start=first_epoch, metadata_epoch_end=last_epoch,
            source_sha256=station_hash, provider_dip_deg=dip, orientation_status=orientation)
        epochs.append(station)
        events.append(dict(id=str(n), event_resource_id='fixture:event:'+str(n), origin_resource_id='fixture:origin:'+str(n), reference_origin_time_utc=origin_time))
        p = dict(original_observation_index=str(n), i=str(n), j='-1', station=str(n), station_j='-1', type='0', value=value,
            event_i_resource_id='fixture:event:'+str(n), origin_i_resource_id='fixture:origin:'+str(n),
            pick_i_resource_id='fixture:pick:'+str(n), arrival_i_resource_id='fixture:association:'+str(n), pick_i_time_utc=pick_time,
            pick_i_source_sha256=station_hash, channel_source_sha256=station_hash, provider_dip_deg=dip, orientation_status=orientation,
            response_status='not required; invented response unavailable', request_start_utc=str(obspy.UTCDateTime(ns=pick_ns-10**9)),
            request_end_utc=str(obspy.UTCDateTime(ns=pick_ns+4*10**9)), availability_status='no_covering_span_reported' if n == 4 else 'provider_reports_covering_span',
            availability_sample_rates_hz=json.dumps([rate]), availability_quality_codes='["D"]')
        p.update({k: station[k] for k in runner.IDENTITY+runner.EPOCH}); picks.append(p)
        if n != 4:
            offset = 3000000 if n == 0 else -2000000 if n == 1 else 0
            values = np.concatenate((np.array([117], dtype=np.int32), arrays[n])) if n == 1 else arrays[n]
            trace = obspy.Trace(values.copy(), header=dict(network='ZZ', station='FIX', location='', channel='EHZ',
                sampling_rate=rate, starttime=obspy.UTCDateTime(ns=pick_ns-10**9+offset)))
            traces.append(trace)
    pairs = []
    for n in range(1,8):
        a,b=picks[0],picks[n]
        r=dict(original_observation_index=str(100+n), i='0', j=str(n), station='0', station_j=str(n), type='1',
            value=repr(float(a['value'])-float(b['value'])), uncertainty_s='0.123', a_priori_weight='0.456',
            observation_basis='invented catalog pick difference', cross_metadata_epoch='1',
            channel_source_sha256=station_hash, channel_j_source_sha256=station_hash,
            metadata_epoch_start=a['metadata_epoch_start'], metadata_epoch_end=a['metadata_epoch_end'],
            metadata_epoch_j_start=b['metadata_epoch_start'], metadata_epoch_j_end=b['metadata_epoch_end'])
        r.update({k:a[k] for k in runner.IDENTITY})
        for side,p in [('i',a),('j',b)]:
            for key in ['event','origin','pick','arrival']:
                r[key+'_'+side+'_resource_id']=p[key+'_i_resource_id']
            r['pick_'+side+'_time_utc']=p['pick_i_time_utc']
        pairs.append(r)
    if defect == 'pair_channel':pairs[0]['channel_seed_id']='ZZ.OTHER..EHZ'
    if defect == 'pair_origin':pairs[0]['origin_j_resource_id']='fixture:wrong_origin'
    if defect == 'pair_pick_time':pairs[0]['pick_j_time_utc']=picks[0]['pick_i_time_utc']
    if defect == 'pair_epoch':pairs[0]['metadata_epoch_j_start']=pairs[0]['metadata_epoch_start']
    if defect == 'pair_station_index':pairs[0]['station_j']='2'
    if defect == 'pair_metadata_hash':pairs[0]['channel_j_source_sha256']='0'*64
    if defect == 'pair_difference':pairs[0]['value']='99'
    if defect == 'duplicate_pair':pairs[1]['original_observation_index']=pairs[0]['original_observation_index']
    if defect == 'pick_travel_time':picks[0]['value']='99'
    events_path=base/'events.csv'
    with events_path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(events[0]),lineterminator='\n');w.writeheader();w.writerows(events)
    table(plan/'identified_picks.csv.gz',picks);table(plan/'identified_catalog_differences.csv.gz',pairs);table(plan/'identified_used_epochs.csv.gz',epochs)
    plan_summary=dict(selections_changed=False, retained_picks=len(picks), retained_catalog_differences=len(pairs),
        input_sha256={runner.relative(events_path):sha(events_path),runner.relative(metadata):sha(metadata)},
        output_sha256={p.name:sha(p) for p in plan.iterdir()})
    save(plan/'summary.json',plan_summary)
    pins={runner.relative(plan/'summary.json'):sha(plan/'summary.json')}
    pins.update({runner.relative(plan/name):h for name,h in plan_summary['output_sha256'].items()})
    pins.update(plan_summary['input_sha256'])
    native=[copy.deepcopy(p) for p in picks if p['availability_status']=='provider_reports_covering_span']
    raw=samples/'raw/dataselect_000.response';obspy.Stream(traces).write(str(raw),format='MSEED',encoding='STEIM2',reclen=512)
    decoded=decoder.decode(raw.read_bytes(),native)
    if defect=='decoded_start':decoded['windows'][0]['first_sample_unix_ns_rational']=str(Q(decoded['windows'][0]['first_sample_unix_ns_rational'])+1)
    if defect=='gap':
        old=traces[0];left=old.copy();left.data=old.data[:200];right=old.copy();right.data=old.data[201:];right.stats.starttime=old.stats.starttime+2.01
        obspy.Stream([left,right]+traces[1:]).write(str(raw),format='MSEED',encoding='STEIM2',reclen=512)
    decoded_path=raw.with_name(raw.name+'.decoded.json');save(decoded_path,decoded)
    context=dict(native_picks=native,input_sha256=pins,scope='Invented miniSEED fixture; never requested')
    body=''.join(' '.join([p['network_code'],p['station_code'],p['location_code'] or '--',p['channel_code'],p['request_start_utc'].rstrip('Z'),p['request_end_utc'].rstrip('Z')])+'\n' for p in native)
    request=raw.with_name(raw.name+'.request.txt');request.write_text(body)
    save(request.with_name(request.name+'.identifiers.json'),dict(request_sha256=sha(request),request_context=context))
    save(raw.with_name(raw.name+'.identifiers.json'),dict(source_sha256=sha(raw),request_context=context))
    url='https://service.ncedc.org/fdsnws/dataselect/1/query'
    save(raw.with_name(raw.name+'.provenance.json'),dict(http_status=200,method='POST',request_url=url,final_url=url,sha256=sha(raw),
        byte_count=raw.stat().st_size,request_sha256=sha(request),acquisition_source_sha256=sha(DECODER),scope='Invented fixture; HTTP metadata is simulated and no request occurred'))
    fields=['trace_index','first_sample_index','stop_sample_index_exclusive','sample_count','sample_rate_hz','miniseed_quality',
        'first_sample_unix_ns_rational','last_sample_unix_ns_rational','window_samples_sha256','decoded_sample_byte_order','no_response_correction','waveform_raw_file','waveform_raw_sha256']
    for p in picks:
        p.update({k:'' for k in fields});p['waveform_status']='not_requested_no_reported_span'
    for w in decoded['windows']:
        p=picks[int(w['original_observation_index'])];p.update({k:str(v) for k,v in w.items() if k!='native_pick'})
        p.update(waveform_status='decoded_native_samples',waveform_raw_file=runner.relative(raw),waveform_raw_sha256=sha(raw))
    picks_path=samples/'samples.picks.csv.gz';table(picks_path,picks)
    summary=dict(status='completed_requested_batches',all_reported_available_non_cmw1_windows_acquired=defect!='incomplete_acquisition',
        started_or_cached_batches=1,total_planned_batches=1,waveform_measurements_added=0,provider=url,
        retained_original_picks=len(picks),retained_catalog_differences=len(pairs),decoded_native_windows=len(native),
        selected_reported_available_non_cmw1_windows=len(native),source_sha256=sha(DECODER),input_sha256=pins,
        results=[dict(batch=0,raw_file='raw/'+raw.name,raw_sha256=sha(raw),decoded_file='raw/'+decoded_path.name,
                      decoded_sha256=sha(decoded_path),native_window_count=len(native))],output_sha256={picks_path.name:sha(picks_path)},
        scope='Invented complete native sample fixture, never a real provider retrieval')
    samples_path=samples/'samples.json';save(samples_path,summary)
    review=samples/'review.json';save(review,dict(status='passed',samples_summary_sha256='0'*64 if defect=='stale_review' else sha(samples_path),scope='Invented review record for contract controls only'))
    if defect=='raw_hash':
        with raw.open('ab') as f:f.write(b'changed')
    return samples_path,review,plan/'summary.json',events_path


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True);args=parser.parse_args()
    out=(ROOT/args.output).resolve();out.relative_to(ROOT);out.mkdir(parents=True)
    sources=[Path(__file__).resolve(),ROOT/'diagnostics/run_native_waveform_cc.py',ROOT/'diagnostics/normalized_waveform_cc.py',runner.SPEC,DECODER]
    frozen=out/'source';frozen.mkdir()
    for p in sources:shutil.copyfile(str(p),str(frozen/('sample_decoder.py' if p==DECODER else p.name)))
    checks=[]
    def check(name,ok,**detail):checks.append(dict(name=name,passed=bool(ok),**detail))
    valid=fixture(out/'valid_fixture');result=runner.run(*valid,out/'valid_result')
    saved=runner.table(out/'valid_result/identified_measurements.csv.gz')
    with gzip.open(str(out/'valid_result/attempted_diagnostics.jsonl.gz'),'rt') as f:details=[json.loads(line) for line in f]
    check('full_native_support_preserved',len(saved)==7 and result['retained_original_picks']==8 and result['attempted_pairs']==2)
    check('empty_location_and_cross_epoch_retained',saved[0]['original_catalog_location_code']=='' and saved[0]['original_catalog_metadata_epoch_start']!=saved[0]['original_catalog_metadata_epoch_j_start'])
    check('accepted_actual_grid_offset_sign',saved[0]['measurement_status']=='accepted_discrete_measurement' and abs(float(saved[0]['cc_delay_j_minus_i_s'])-.165)<1e-15 and abs(float(saved[0]['dt_cc_i_minus_j_s'])-(-.84-.165))<1e-15)
    check('integer_own_pick_offsets_retained',details[0]['diagnostics']['sample_i_start_from_own_pick_ns']==-997000000 and details[0]['diagnostics']['sample_j_start_from_own_pick_ns']==-992000000)
    check('relative_weight_not_sigma',float(saved[0]['cc_relative_weight_squared'])==float(saved[0]['maximum_cc_squared']) and saved[0]['cc_formal_timing_uncertainty_s']=='')
    check('original_sigma_and_catalog_value_labeled',saved[0]['original_catalog_uncertainty_s']=='0.123' and saved[0]['original_catalog_a_priori_weight']=='0.456' and float(saved[0]['original_catalog_value'])!=float(saved[0]['dt_cc_i_minus_j_s']))
    for index,reason in [(1,'orientation_j:'),(2,'orientation_j:'),(3,'waveform_j:'),(4,'unsupported_native_sample_rate_j'),(5,'different_reported_receiver_position')]:
        check('unattempted_status_'+str(index),saved[index]['measurement_status']=='not_attempted' and any(x.startswith(reason) for x in json.loads(saved[index]['cc_ineligibility_reasons_json'])))
    check('undefined_search_arrays_retained',saved[6]['measurement_status']=='constant_search_windows' and len(details[1]['diagnostics']['coefficients'])==51 and all(x is None for x in details[1]['diagnostics']['coefficients']))
    check('accepted_full_lag_and_coherence_arrays',len(details[0]['diagnostics']['lag_ns'])==50 and len(details[0]['diagnostics']['frequency_hz'])==20 and len(details[0]['diagnostics']['squared_coherence'])==20)
    check('both_native_sidecars_complete',all(details[0]['waveform_'+s]['pick_i_resource_id']==details[0]['original_catalog']['pick_'+s+'_resource_id'] for s in ['i','j']))
    check('no_solver_import_or_export',result['solver_observations_added']==0 and result['dt_cc_exported'] is False and result['original_catalog_values_changed'] is False)
    try:runner.run(*valid,out/'valid_result');rejected=False
    except FileExistsError:rejected=True
    check('fresh_output_required',rejected)
    defects=['pair_channel','pair_origin','pair_pick_time','pair_epoch','pair_station_index','pair_metadata_hash','pair_difference','duplicate_pair','pick_travel_time','decoded_start','gap','incomplete_acquisition','stale_review','raw_hash']
    for defect in defects:
        inputs=fixture(out/(defect+'_fixture'),defect)
        try:runner.run(*inputs,out/(defect+'_result'));error=None
        except ValueError as e:error=str(e)
        check('reject_'+defect,error is not None,error=error)
        execution=json.loads((out/(defect+'_result')/'execution.json').read_text())
        check('failure_record_'+defect,execution['status']=='failed' and not (out/(defect+'_result')/'summary.json').exists())
    summary=dict(status='passed' if all(c['passed'] for c in checks) else 'failed',scope=__doc__,checks=checks,
        source_sha256={runner.relative(p):sha(p) for p in sources},output_sha256={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()},
        limitations=['Invented native data only; no real correlation or legacy dt.cc serialization.',
            'The core method has its own independent numerical tests; these controls test decoding, identities, timing, table preservation and gates.'])
    save(out/'summary.json',summary);print(json.dumps(dict(status=summary['status'],checks=len(checks),failed=[c for c in checks if not c['passed']]),indent=2))
    if summary['status']!='passed':raise SystemExit(1)


if __name__=='__main__':main()
