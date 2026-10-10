#!/usr/bin/env python3
"""Summarize existing identified comparison tables; no reference or solver rerun."""
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics

HERE = Path(__file__).resolve().parent
summary = json.loads((HERE/'summary.json').read_text())
for name, expected in summary['output_sha256'].items():
    if hashlib.sha256((HERE/name).read_bytes()).hexdigest()!=expected:
        raise ValueError('Changed comparison evidence: '+name)
with (HERE/'comparison.csv').open() as stream: rows=list(csv.DictReader(stream))
with (HERE/'derivative_comparison.csv').open() as stream: derivatives=list(csv.DictReader(stream))


def stats(values):
    return dict(count=len(values),minimum=min(values),maximum=max(values),
        median=statistics.median(values),rms=math.sqrt(sum(v*v for v in values)/len(values)))


groups={}
worst={}
for mode in ('production','refined'):
    groups[mode]={}
    for state in ('0','1'):
        selected=[r for r in rows if r[mode+'_converged']==state]
        groups[mode]['saved_converged_'+state]=stats([float(r[mode+'_minus_reference_s']) for r in selected])
    worst[mode]=sorted(rows,key=lambda r:float(r[mode+'_minus_reference_s']),reverse=True)[:5]
vectors=[]
for q in range(8):
    subset=[r for r in derivatives if r['diagnostic_row']==str(q)]
    if {r['axis'] for r in subset}!={'0','1','2'}:raise ValueError('Incomplete saved derivative vector')
    vector=dict(diagnostic_row=q,source_event_resource_id=rows[q]['saved_source_event_resource_id'],
        source_origin_resource_id=rows[q]['saved_source_origin_resource_id'],
        receiver_channel_seed_id=rows[q]['saved_receiver_channel_seed_id'],
        receiver_metadata_epoch_start=rows[q]['saved_receiver_metadata_epoch_start'],
        receiver_metadata_epoch_end=rows[q]['saved_receiver_metadata_epoch_end'])
    for mode in ('production','refined'):
        vector[mode+'_source_error_norm_s_per_km']=math.sqrt(sum(float(r[mode+'_minus_reference_s_per_km'])**2 for r in subset))
    vectors.append(vector)
report=dict(scope='Descriptive grouping of all104 unchanged stopping flags and existing reference errors',
    summary_sha256=hashlib.sha256((HERE/'summary.json').read_bytes()).hexdigest(),
    helper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    time_errors_by_saved_flag=groups,identified_worst_five=worst,available_source_error_vectors=vectors,
    limitations=['No new field acceptance threshold is imposed.','Small negative time differences inherit saved12-significant-digit rounding.',
                 'Native identities are retained in every worst-case row and derivative-vector record.'])
(HERE/'review.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
print(json.dumps(groups,indent=2))
