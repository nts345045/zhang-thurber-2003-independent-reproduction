#!/usr/bin/env python3
"""Pin the distinct LON initial-z reference inputs after its complete output audit."""
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'diagnostics'))
from run_loma_initial_reference import sha, table, geometry, checked_inputs, REFERENCE_SHA256


def main():
    data=ROOT/'data/loma_lon_analytic_001';lom=ROOT/'data/loma_lom_analytic_001'
    review=json.loads((data/'independent_simulation_review.json').read_text())
    ledger=json.loads((data/'simulation_execution.json').read_text())
    manifest=json.loads((data/'simulation_run_manifest.json').read_text())
    if review['status']!='passed' or ledger['status']!='completed' or ledger['return_code']!=0:
        raise ValueError('Require terminal audited LON simulation')
    for name,key in [('simulation_execution.json','simulation_execution_sha256'),('simulation_run_manifest.json','simulation_run_manifest_sha256')]:
        if sha(data/name)!=review[key]:raise ValueError('Changed review link: '+name)
    counts=manifest['expected_counts'];expected=(counts['events'],counts['receivers'])
    _,events=table(data/'initial_events.csv');_,stations=table(data/'stations.csv');_,grid=table(data/'initial_grid.csv')
    profile,box=geometry(events,stations,grid,expected)
    names=['initial_events.csv','stations.csv','initial_grid.csv','run.cfg','ray_samples.csv','preparation_manifest.json',
        'analytic_truth_manifest.json','simulation_execution.json','simulation_run_manifest.json','independent_simulation_review.json']
    hashes={name:sha(data/name) for name in names}
    for name,digest in hashes.items():
        if name!='independent_simulation_review.json' and review['input_sha256'][name]!=digest:
            raise ValueError('Changed reviewed LON input: '+name)
    unchanged=ROOT/'diagnostics/first_arrival_1d_reference.py'
    if sha(unchanged)!=REFERENCE_SHA256:raise ValueError('Numerical reference helper changed')
    shared={name:dict(lom=sha(lom/name),lon=hashes[name],byte_identical=sha(lom/name)==hashes[name])
        for name in ('initial_events.csv','stations.csv','initial_grid.csv')}
    oldreview=json.loads((lom/'independent_simulation_review.json').read_text())
    result=dict(status='reference_only_plan',scope='Independent full initial-z references for the saved LON model; no forward solver or inverse launch',
        actual_run=str(data.relative_to(ROOT)),input_sha256=hashes,source_sha256={
            'diagnostics/first_arrival_1d_reference.py':sha(unchanged),
            'diagnostics/run_loma_initial_reference.py':sha(ROOT/'diagnostics/run_loma_initial_reference.py'),
            str(Path(__file__).resolve().relative_to(ROOT)):sha(Path(__file__))},
        expected_pairs=counts['unique_rays'],source_count=expected[0],receiver_count=expected[1],initial_profile_depth_velocity=profile,
        original_box_km=box,initial_nodes=len(grid),source_time_included=False,
        shared_geometry_and_distinct_grid=shared,
        reviewed_observation_sha256_equal=review['input_sha256']['observations.csv']==oldreview['input_sha256']['observations.csv'],
        observation_hash_basis='The two passed exhaustive audits bind these hashes; observations are not reread or reused by this reference calculation.',
        limitations=['Only geometry may be byte identical to LOM; the initial velocity profile differs and every LON reference is recomputed.',
            'Existing root/closure gates, native identities and finite box remain unchanged.',
            'This is not a request or acceptance for LON numerical forward or inverse calculations.'])
    with (HERE/'plan.json').open('x') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
    files,checked=checked_inputs(data,HERE/'plan.json')
    if checked!=expected:raise ValueError('Wrapper eligibility changed')
    print(json.dumps(dict(status='ready',expected_pairs=result['expected_pairs'],profile=profile,shared=shared),indent=2))

if __name__=='__main__':main()
