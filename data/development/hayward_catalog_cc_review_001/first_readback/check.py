#!/usr/bin/env python3
"""Read back prepared catalog-plus-CC inputs without invoking their adapter."""
import argparse
from collections import Counter
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PREFIX = 'original_catalog_'
CHANNEL = ('network_code','station_code','location_code','channel_code',
           'channel_seed_id','channel_fdsn_source_id')
EXTRA = ('cc_uncertainty_status','solver_weight_basis','solver_objective_quality_power',
         'provider_pick_identity_role')
PROVENANCE = ('derived_measurement_summary_sha256','derived_measurement_review_sha256',
              'legacy_export_summary_sha256','legacy_export_review_sha256')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1048576), b''):
            digest.update(block)
    return digest.hexdigest()


def open_csv(path):
    return (gzip.open if path.suffix == '.gz' else open)(str(path), 'rt', newline='')


def table(path):
    with open_csv(path) as f:
        reader = csv.DictReader(f); fields = reader.fieldnames; rows = list(reader)
    require(fields and len(fields) == len(set(fields)), 'Duplicate or missing fields')
    require(all(None not in r and None not in r.values() for r in rows), 'Malformed rows')
    return fields, rows


def main(folder):
    folder=folder.resolve();folder.relative_to(ROOT)
    result_path=folder/'independent_review.json'
    require(not result_path.exists(), 'Preserve an existing independent review')
    pins={}
    def pin(path, expected=None):
        path=path.resolve();name=str(path.relative_to(ROOT));digest=sha(path)
        require(expected is None or digest==expected,'Changed pin: '+name)
        require(name not in pins or pins[name]==digest,'Changed during review: '+name)
        pins[name]=digest;return path
    def load(path):
        return json.loads(pin(path).read_text())
    pin(Path(__file__))
    manifest_path=folder/'preparation_manifest.json'
    manifest=load(manifest_path);execution=load(folder/'execution.json')
    require(manifest['status']=='prepared_identified_catalog_plus_cc_inputs' and
        execution['status']=='completed' and execution['return_code']==0 and
        execution['preparation_manifest_sha256']==sha(manifest_path), 'Preparation is not terminal successful')
    require(execution['network_requests']==0 and manifest['solver_invocations']==0 and
        manifest['original_inputs_changed'] is False and manifest['run_configuration_created'] is False and
        not (folder/'run.cfg').exists(), 'Preparation scope differs')
    for name,digest in manifest['input_source_sha256'].items():pin(ROOT/name,digest)
    for mapping in (manifest['output_sha256'],execution['log_sha256']):
        for name,digest in mapping.items():
            path=(folder/name).resolve();path.relative_to(folder);pin(path,digest)
    command=execution['command']
    def argument(flag):
        value=(ROOT/command[command.index(flag)+1]).resolve();value.relative_to(ROOT);return value
    catalog=argument('--catalog-dir');export_path=argument('--export-summary');review_path=argument('--export-review')
    require(argument('--output')==folder,'Execution output mapping differs')
    require(execution['source_sha256']==sha(folder/'source/prepare_hayward_cc.py'), 'Frozen adapter source differs')
    controls_dir=ROOT/'data/development/hayward_cc_input_checks/002'
    controls=load(controls_dir/'summary.json');controls_review=load(controls_dir/'root_review.json')
    require(controls['status']=='passed' and controls_review['status']=='passed' and
        controls_review['controls_summary_sha256']==sha(controls_dir/'summary.json') and
        controls_review['source_sha256']['prepare_hayward_cc.py']==execution['source_sha256']==
        controls['source_sha256']['prepare_hayward_cc.py'], 'Prepared source differs from independently reviewed controls')
    pin(controls_dir/'source/prepare_hayward_cc.py',execution['source_sha256'])
    exported=load(export_path);export_review=load(review_path)
    require(export_review['status']=='passed' and export_review['export_summary_sha256']==sha(export_path),
            'Export review linkage differs')
    require(export_review['export_execution_sha256']==sha(pin(export_path.parent/'execution.json')),
            'Export execution linkage differs')
    for name,digest in exported['output_sha256'].items():pin(export_path.parent/name,digest)
    for name in ('initial_events.csv','initial_grid.csv','stations.csv','authoritative_ids_required'):
        require(sha(pin(catalog/name))==sha(pin(folder/name)), 'Copied input bytes differ: '+name)
    require(sha(pin(catalog/'observations.csv'))==sha(pin(folder/'catalog_provenance/observations.csv')),
            'Original catalog byte copy differs')
    catalog_fields,original=table(catalog/'observations.csv')
    _,events=table(folder/'initial_events.csv');_,stations=table(folder/'stations.csv')
    require(len(original)==58980 and Counter(r['type'] for r in original)=={'0':14262,'1':44718},
            'Original catalog support differs')
    require([r['id'] for r in events]==[str(i) for i in range(len(events))] and
            [r['id'] for r in stations]==[str(i) for i in range(len(stations))], 'Native numerical indices differ')
    accepted=[];seen=set();statuses=Counter()
    with open_csv(export_path.parent/'dt.cc.identifiers.csv.gz') as f:
        reader=csv.DictReader(f);export_fields=reader.fieldnames
        for row in reader:
            q=int(row[PREFIX+'original_observation_index'])
            require(q not in seen and 0<=q<len(original) and original[q]['type']=='1','Duplicate or invalid original pair')
            seen.add(q)
            require(all(row[PREFIX+k]==original[q][k] for k in catalog_fields),'Original full sidecar join differs')
            statuses[row['measurement_status']]+=1
            if row['measurement_status']=='accepted_discrete_measurement':
                require(row['dt_cc_export_status']=='exported','Accepted export status differs');accepted.append(row)
            else:require(row['dt_cc_export_status']=='not_accepted','Unaccepted row exported')
    require(seen=={q for q,r in enumerate(original) if r['type']=='1'} and len(accepted)==98,
            'Complete original pair roster or accepted subset differs')
    extra=list(export_fields)+list(EXTRA)+list(PROVENANCE)
    expected_provenance=dict(zip(PROVENANCE,[export_review['measurements_summary_sha256'],
        export_review['measurements_review_sha256'],sha(export_path),sha(review_path)]))
    original_rays=set();combined_rays=set();accepted_events=set();channels=Counter();cross_epochs=0
    type_counts=Counter();used_epochs=set();derived_ids=set()

    def native(row, target):
        i,j,k,kj=[int(row[x]) for x in ('i','j','station','station_j')]
        kind=int(row['type'])
        require(0<=i<len(events) and 0<=k<len(stations) and kind in (0,1,2),'Invalid native row index')
        require((kind==0 and j==kj==-1) or (kind in (1,2) and 0<=j<len(events) and i!=j and 0<=kj<len(stations)),
                'Invalid second native index')
        for side,index,receiver in [('i',i,k),('j',j,kj)]:
            if index<0:
                require(all(row[t+'_'+side+'_resource_id']=='' for t in ('event','origin','pick','arrival')),
                        'Absolute row carries a second native identity');continue
            event=events[index];station=stations[receiver]
            require(all(row[t+'_'+side+'_resource_id']==event[t+'_resource_id'] for t in ('event','origin')),
                    'Native event/origin mismatch')
            require(all(row[t+'_'+side+'_resource_id'] for t in ('pick','arrival')),'Missing native reference pick/arrival')
            require(all(row[key]==station[key] for key in CHANNEL),'Native channel mismatch')
            for bound in ('start','end'):
                require(row['metadata_epoch_'+('j_' if side=='j' else '')+bound]==station['metadata_epoch_'+bound],
                        'Native epoch mismatch')
            require(row['channel_'+('j_' if side=='j' else '')+'source_sha256']==station['source_sha256'],
                    'Native channel source mismatch')
            target.add((index,receiver))
        if j>=0:
            xyz=lambda r:tuple(float(r[n]) for n in ('x','y','z','latitude_deg','longitude_deg','sensor_z_geoid_km'))
            require(xyz(stations[k])==xyz(stations[kj]) and all(math.isfinite(v) for v in xyz(stations[k])),
                    'Different physical receiver positions')
        return i,j,k,kj

    with open_csv(folder/'observations.csv') as f:
        reader=csv.DictReader(f)
        require(reader.fieldnames==catalog_fields+extra,'Prepared column schema differs')
        for q,row in enumerate(reader):
            require(None not in row and None not in row.values(),'Malformed prepared row')
            type_counts[row['type']]+=1
            if q<len(original):
                require({k:row[k] for k in catalog_fields}==original[q],'Catalog cell or order changed')
                require(all(row[k]=='' for k in extra),'Catalog row gained CC claims')
                native(row,original_rays)
            else:
                n=q-len(original);require(n<len(accepted),'Unexpected appended row');source=accepted[n]
                base=original[int(source[PREFIX+'original_observation_index'])]
                changes={'type':'2','value':source['dt_cc_i_minus_j_s'],
                         'a_priori_weight':source['cc_relative_weight_squared'],'uncertainty_s':'',
                         'observation_basis':'normalized waveform P difference'}
                require(all(row[k]==changes.get(k,base[k]) for k in catalog_fields),'Derived base fields differ')
                require(all(row[k]==v for k,v in source.items()),'Exported native/measurement field changed')
                require(row['cc_uncertainty_status']=='unestimated' and
                    row['solver_weight_basis']=='literal_legacy_CC_squared_row_multiplier' and
                    row['solver_objective_quality_power']=='4' and
                    row['provider_pick_identity_role']=='reference catalog picks; derived waveform measurement is locally identified',
                    'Derived uncertainty or weighting interpretation differs')
                require(all(row[k]==v for k,v in expected_provenance.items()),'Derived source/review linkage differs')
                cc=float(row['maximum_cc']);weight=float(row['a_priori_weight'])
                require(math.isfinite(cc) and cc>0 and weight==cc*cc==float(row['maximum_cc_squared']) and
                    float(row['value'])==float(base['value'])-float(row['cc_delay_j_minus_i_s']),
                    'CC square or differential sign arithmetic differs')
                require(not row['cc_formal_timing_uncertainty_s'] and row['measurement_id'] not in derived_ids,
                    'Invented CC sigma or repeated measurement')
                derived_ids.add(row['measurement_id'])
                accepted_events.update([row['event_i_resource_id'],row['event_j_resource_id']])
                channels[row['channel_seed_id']]+=1
                cross_epochs+=row['station']!=row['station_j']
                used_epochs.update([int(row['station']),int(row['station_j'])])
            native(row,combined_rays)
    prepared_count=q+1
    require(prepared_count==59078==manifest['prepared_rows'] and manifest['original_catalog_rows']==58980 and
            manifest['appended_cc_rows']==98 and dict(type_counts)==manifest['type_counts'], 'Prepared counts differ')
    require(original_rays==combined_rays and len(original_rays)==14262,'New native forward rays introduced')
    require(len(accepted_events)==103 and len(channels)==4 and cross_epochs==38 and len(used_epochs)==22,
            'Accepted native support differs')
    require(channels=={'NC.JPR.02.EHZ':75,'NC.CBR.10.EHZ':19,'NC.JSB.10.EHZ':3,'NC.JSF.10.EHZ':1},
            'Accepted channel counts differ')
    for name,digest in pins.items():require(sha(ROOT/name)==digest,'Input/output changed during review: '+name)
    result=dict(status='passed',reviewer='earthscope_discovery',material_issue_found=False,
        scope='Independent terminal hashes, complete cell/native joins and saved-value arithmetic; adapter, measurements and solver were not rerun.',
        preparation_manifest_sha256=sha(manifest_path),preparation_execution_sha256=sha(folder/'execution.json'),
        review_source_sha256=sha(Path(__file__)),verified_sha256=pins,original_catalog_rows=58980,appended_cc_rows=98,
        prepared_rows=prepared_count,type_counts=dict(type_counts),all_original_catalog_fields_and_order_unchanged=True,
        all_exported_native_measurement_fields_exact=True,both_native_receiver_epochs_preserved=True,
        original_geometry_and_catalog_copy_hashes_match=True,cc_prior_is_literal_saved_CC_squared=True,
        squared_objective_quality_power=4,cc_uncertainty_blank_and_explicitly_unestimated=True,
        accepted_event_count=len(accepted_events),accepted_channel_counts=dict(channels),accepted_native_epochs=len(used_epochs),
        cross_epoch_cc_rows=cross_epochs,original_unique_native_forward_pairs=len(original_rays),
        combined_unique_native_forward_pairs=len(combined_rays),added_unique_native_forward_pairs=0,
        solver_invocations=0,run_configuration_created=False,
        limitations=['Preparation does not establish CC inverse-variance calibration, covariance or inverse-model accuracy.',
                    'CC squared is the selected row multiplier, hence CC to the fourth is its conditional squared-objective factor.',
                    'A later run needs separate explicit stage weights and the existing guarded forward checks; type2 remains outside catalog-pick covariance.'])
    with result_path.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(dict(status=result['status'],prepared_rows=prepared_count,review_sha256=sha(result_path))))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--data',type=Path,required=True)
    main(parser.parse_args().data)
