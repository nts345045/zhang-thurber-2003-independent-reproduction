#!/usr/bin/env python3
"""Compare arithmetic on recorded trials after controls and exact-action review."""
import csv
from decimal import Decimal, localcontext
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
REPLAY = ROOT/'data/development/loma_failed_search_3426_001'
EXACT = ROOT/'data/development/loma_failed_trial_exact_001'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text())


def rows(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def require(value, message):
    if not value:
        raise ValueError(message)


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


def main():
    os.chdir(str(ROOT))
    controls = load(OUT/'controls_execution.json')
    review = load(OUT/'controls_review.json')
    require(controls['status']=='passed_controls' and review['status']=='passed' and
            review['controls_execution_sha256']==sha(OUT/'controls_execution.json'), 'Controls/review mismatch')
    for name,digest in controls['source_sha256'].items():
        require(sha(ROOT/name)==digest, 'Source changed: '+name)
    for name,digest in controls['artifact_sha256'].items():
        require(sha(OUT/name)==digest, 'Control artifact changed: '+name)
    binary = ROOT/controls['compile_command'][-1]
    require(sha(binary)==controls['binary_sha256'], 'Binary changed')
    original,exact = load(REPLAY/'summary.json'),load(EXACT/'summary.json')
    require(original['native_context']==exact['native_context'], 'Native identities differ')
    require(original['status']=='completed_with_original_flags_preserved' and
            exact['status']=='completed_exact_saved_trial_comparison', 'Incomplete prior calculations')
    for directory in (REPLAY,EXACT):
        prior_review=load(directory/'review.json')
        require(prior_review['status']=='passed_saved_evidence_review' and
                prior_review['summary_sha256']==sha(directory/'summary.json'), 'Prior review mismatch')
    for name in ('identified_ray.csv','inputs/initial_grid.csv'):
        require(sha(REPLAY/name)==original['output_sha256'][name], 'Replay geometry/context changed')
    require(rows(REPLAY/'identified_ray.csv')==[original['native_context']], 'Identified native row differs')
    inputs = [OUT/'controls_execution.json',OUT/'controls_review.json',Path(__file__).resolve(),
              REPLAY/'summary.json',REPLAY/'review.json',REPLAY/'identified_ray.csv',REPLAY/'inputs/initial_grid.csv',
              EXACT/'summary.json',EXACT/'review.json']
    for name in ('failed_search_directions.csv','failed_search_trials.csv','failed_search_decisions.csv'):
        inputs += [REPLAY/name,REPLAY/(name+'.identifiers.json')]
        require(sha(REPLAY/name)==original['output_sha256'][name], 'Replay table changed')
        sidecar=load(REPLAY/(name+'.identifiers.json'))
        require(sidecar['file_sha256']==sha(REPLAY/name) and
                sidecar['context_sha256']==sha(REPLAY/'identified_ray.csv') and
                sidecar['native_context']==original['native_context'],
                'Replay identity/hash mismatch')
    pins={str(path.relative_to(ROOT)):sha(path) for path in inputs}
    require(not (OUT/'summary.json').exists() and not (OUT/'inputs').exists(), 'Use a fresh native execution')
    for source in inputs:
        target=OUT/'inputs'/source.relative_to(ROOT)
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(str(source),str(target))
        require(sha(target)==sha(source), 'Copy changed')
    frozen=OUT/'inputs'/REPLAY.relative_to(ROOT)
    command=[str(binary.relative_to(ROOT)),str((frozen/'inputs/initial_grid.csv').relative_to(ROOT)),
             str((frozen/'failed_search_directions.csv').relative_to(ROOT)),
             str((frozen/'failed_search_trials.csv').relative_to(ROOT)),
             str((OUT/'segments.csv').relative_to(ROOT)),str((OUT/'totals.csv').relative_to(ROOT))]
    summary=dict(status='running',input_sha256=pins,binary_sha256=sha(binary),command=command,
                 native_context=original['native_context'],original_local_flag='0',
                 started_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
    save(OUT/'summary.json',summary)
    try:
        with (OUT/'native_stdout.log').open('w') as out,(OUT/'native_stderr.log').open('w') as err:
            process=subprocess.run(command,stdout=out,stderr=err,
                env=dict(os.environ,OMP_NUM_THREADS='1',TMPDIR=str(ROOT/'tmp')))
        summary['return_code']=process.returncode
        require(process.returncode==0, 'Native saved-path evaluation failed')
        totals,segments=rows(OUT/'totals.csv'),rows(OUT/'segments.csv')
        require(len(totals)==25 and len(segments)==25*1133, 'Incomplete arithmetic outputs')
        decisions=rows(frozen/'failed_search_decisions.csv')
        require(len(decisions)==24, 'Unexpected decision inventory')
        original_segments={}
        for row in segments:
            require(row['run_id']=='fmm_0.031250_1000' and row['observation_index']=='3426','Output identity differs')
            key=int(row['trial_index']); edge=int(row['edge'])
            group=original_segments.setdefault(key,[])
            require(edge==len(group), 'Segment order differs')
            group.append(Fraction(float(row['original_segment_s'])))
        base=totals[0]
        require(set(original_segments)==set(range(-1,24)) and
                all(len(group)==1133 for group in original_segments.values()), 'Incomplete segment groups')
        require(base['trial_index']=='-1' and base['run_id']=='fmm_0.031250_1000' and
                base['observation_index']=='3426' and
                float(base['original_total_s'])==float(decisions[0]['cached_base_action_s']),
                'Original base action differs from replay')
        base_sum=sum(original_segments[-1],Fraction(0))
        comparisons=[]
        with localcontext() as context:
            context.prec=80
            for i,(row,decision,bound) in enumerate(zip(totals[1:],decisions,exact['trials'])):
                require(int(row['trial_index'])==i==int(decision['trial_index']) and
                        row['run_id']==decision['run_id'] and row['observation_index']==decision['observation_index'],
                        'Trial join differs')
                require(float(row['original_total_s'])==float(decision['trial_action_s']) and
                        int(row['changed_edges'])==bound['changed_edges'], 'Original output differs from neutral replay')
                action_delta_lower=Fraction(bound['exact_action_change_s']['lower_rational'])
                action_delta_upper=Fraction(bound['exact_action_change_s']['upper_rational'])
                target=Fraction(bound['exact_saved_slope_armijo_target_s']['lower_rational'])
                exact_segment_sum_change=sum(original_segments[i],Fraction(0))-base_sum
                values={
                    'original_total_difference_s':Fraction(float(row['original_total_s']))-Fraction(float(base['original_total_s'])),
                    'exact_sum_of_original_segment_changes_s':exact_segment_sum_change,
                    'extended_sum_of_original_totals_difference_s':Decimal(row['extended_sum_original_segments_s'])-Decimal(base['extended_sum_original_segments_s']),
                    'paired_original_segment_change_s':Decimal(row['paired_original_segment_change_s']),
                    'extended_total_difference_s':Decimal(row['extended_total_s'])-Decimal(base['extended_total_s']),
                    'paired_extended_segment_change_s':Decimal(row['paired_extended_segment_change_s'])}
                record=dict(trial_index=i,step=decision['step'],exact_action_change_s=bound['exact_action_change_s'],
                            exact_armijo_classification=bound['exact_saved_slope_armijo'],methods={})
                for name,value in values.items():
                    rational=Fraction(value)
                    record['methods'][name]=dict(value_decimal=str(value) if isinstance(value,Decimal) else
                        str(Decimal(value.numerator)/Decimal(value.denominator)),
                        value_display=float(value),
                        minus_exact_change_lower_display=float(rational-action_delta_upper),
                        minus_exact_change_upper_display=float(rational-action_delta_lower),
                        approximate_armijo_pass=rational<=target)
                comparisons.append(record)
        for name in ('segments.csv','totals.csv'):
            save(OUT/(name+'.identifiers.json'),dict(file=name,file_sha256=sha(OUT/name),
                join_keys=['run_id','observation_index'],native_context=original['native_context'],
                source_replay_summary_sha256=sha(REPLAY/'summary.json'),
                identity_basis='Authoritative event and receiver identities; paths use saved perturbed simulation geometry'))
        for name,digest in pins.items():require(sha(ROOT/name)==digest,'Input changed: '+name)
        summary.update(status='completed_saved_path_arithmetic_comparison',comparisons=comparisons,
            original_double_segments_and_totals_preserved=True,
            limitations=['Extended arithmetic keeps the original binary64 Gauss coefficients and thresholds.',
                'Experimental signs are approximate arithmetic decisions, not certified action enclosures.',
                'Differences of printed extended totals include their final decimal display rounding.',
                'Exact summation of original binary64 segment values isolates outer accumulation only.',
                'No ray optimization, production edit, local flag or scientific threshold changes.'])
    except BaseException as error:
        summary.update(status='failed',failure=repr(error));save(OUT/'summary.json',summary);raise
    summary['finished_utc']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
    summary['artifact_sha256']={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*')
                               if p.is_file() and p!=OUT/'summary.json' and '__pycache__' not in p.parts}
    save(OUT/'summary.json',summary)
    print(summary['status'])


if __name__=='__main__':
    main()
