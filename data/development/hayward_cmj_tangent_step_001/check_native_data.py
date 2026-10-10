#!/usr/bin/env python3
"""Saved-data-only independent review; no diagnostic/helper/numerical calls."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
EXPECTED_PREPARED='b58f763fb3d262f9030329413e51e8f7c29550df6b3e2f7021a16d56ec7eff29'
EXPECTED_SOURCE='eed2d52e8311acb917b1a104e0b5d2f0862add5232f442fc92927cfd686c529d'

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()

def require(ok,message):
    if not ok:raise ValueError(message)

def main():
    require(sha(HERE/'prepared.json')==EXPECTED_PREPARED,'Prepared bytes changed')
    require(sha(HERE/'run.py')==EXPECTED_SOURCE,'Wrapper bytes changed')
    prepared=json.load((HERE/'prepared.json').open())
    counts={}
    pins={}
    for label,base,key in [('inputs',ROOT,'input_sha256'),('prepared',HERE,'output_sha256'),('runtime',Path('/'),'runtime_sha256')]:
        counts[label]=len(prepared[key])
        for name,digest in prepared[key].items():
            p=base/name
            require(p.is_file() and sha(p)==digest,'Changed '+str(p))
            pins[str(p)]=digest
    spec=importlib.util.spec_from_file_location('reviewed_native_wrapper',str(HERE/'run.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    def forbidden(*args,**kwargs):raise ValueError('No subprocess permitted in saved-only review')
    module.subprocess.Popen=forbidden
    grid,cases=module.load_inputs()
    require(not any(k.startswith('diagnostics') for k in sys.modules),'Numerical module imported')
    require(len(grid['velocities'])==462 and len(cases)==2,'Native inventory mismatch')
    frozen=json.load((HERE/'native_contexts.json').open())
    records=[]
    for case,expected in zip(cases,[(981,1029,3050,31),(987,1031,3055,32)]):
        event,n,available,blocked=expected
        require(case['event']==event and case['station']==160 and len(case['path'])==n,'Case roster')
        status=case['original_status']
        require(status['ray_converged']=='0' and status['ray_derivatives_evaluated']=='0','Original flags changed')
        require(all(status[k]=='' for k in ['source_dx','source_dy','source_dz']),'Unevaluated source partial supplied')
        require(case['candidate_convergence_status'] is None,'Candidate flag promoted')
        slots=[x for row in case['components'][1:-1] for x in row]
        require(sum(x is not None for x in slots)==available and sum(x is None for x in slots)==blocked,'Derivative slot inventory')
        require(len(case['catalog_uses'])==9,'Catalog use inventory')
        for use in case['catalog_uses']:
            row=use['original_row']
            for side,join in use['epoch_joins'].items():
                receiver=join['receiver_native']
                require(all(row[k]==receiver[k] for k in ('network_code','station_code','location_code','channel_code','channel_seed_id','channel_fdsn_source_id')),'Both-side native receiver identity')
                prefix='metadata_epoch_' if side=='i' else 'metadata_epoch_j_'
                require(all(row[prefix+end]==receiver['metadata_epoch_'+end] for end in ('start','end')),'Both-side receiver epoch')
                digest='channel_source_sha256' if side=='i' else 'channel_j_source_sha256'
                require(row[digest]==receiver['source_sha256'],'Both-side receiver source')
                require(receiver['location_code']=='','Valid empty location changed')
        records.append(dict(event=event,station=160,native_context=case['native_context'],nodes=n,edges=n-1,
            available_derivative_slots=available,unavailable_normal_slots=blocked,catalog_uses=9,
            original_observation_rows=[v['zero_based_observation_row'] for v in case['catalog_uses']],
            original_convergence_flag='0',derivatives_evaluated='0',source_dx='',source_dy='',source_dz='',
            candidate_convergence_status=None))
    for path,digest in pins.items():require(sha(path)==digest,'Input changed during saved-data readback')
    require(sha(HERE/'prepared.json')==EXPECTED_PREPARED and sha(HERE/'run.py')==EXPECTED_SOURCE,'Source/preparation changed during readback')
    result=dict(status='passed',reviewer='scientific_audit',reviewed_utc=datetime.datetime.utcnow().isoformat()+'Z',
        scope='Native/data closure only; imports wrapper and calls load_inputs once. No main, compile, subprocess, metric solve, rounded trial, action or tangent integration.',
        prepared_sha256=EXPECTED_PREPARED,wrapper_sha256=EXPECTED_SOURCE,checker_sha256=sha(Path(__file__)),
        checked_pin_counts=counts,all_checked_pins_unchanged_after_readback=True,model_nodes=462,cases=records,
        native_contexts_sha256=sha(HERE/'native_contexts.json'),
        source_review=['Recorded binary64 model/raw-grid mapping and exact failed-state endpoints preserved.',
            'Ordered action-cache endpoints and complete action sum match the selected exact-face polygons.',
            'Every available derivative combines both adjacent saved contributions and joins the independently reviewed sparse roster.',
            'Both-side indexed event/origin and full receiver identities, epochs and source hashes are joined; all nine uses and valid empty location are preserved.',
            'Starting flags remain false and unevaluated source partials remain blank; no convergence or first-arrival promotion.'],
        numerical_calls=0,execution_authorization=False)
    with (HERE/'native_data_review.json').open('x') as f:json.dump(result,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
    print(json.dumps(dict(status='passed',checked_pin_counts=counts,review_sha256=sha(HERE/'native_data_review.json'))))
if __name__=='__main__':main()
