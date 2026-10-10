#!/usr/bin/env python3
"""Read-only completion, sample-parity and physical-bound review of this batch."""
import collections
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path

HERE=Path(__file__).resolve().parent


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1048576),b''):h.update(chunk)
    return h.hexdigest()


def velocity(profile,x):
    for (a,va),(b,vb) in zip(profile,profile[1:]):
        if a<=x<=b:return va+(vb-va)*(x-a)/(b-a)
    raise ValueError('Point outside finite profile')


def straight_action(profile,source,receiver):
    """Independent reciprocal-affine segment integral using exact x-plane cuts."""
    delta=[b-a for a,b in zip(source,receiver)];length=math.sqrt(sum(q*q for q in delta))
    cuts=[0.,1.]
    if delta[0]:cuts += [(x-source[0])/delta[0] for x,v in profile if min(source[0],receiver[0])<x<max(source[0],receiver[0])]
    cuts.sort();terms=[]
    for lo,hi in zip(cuts,cuts[1:]):
        va=velocity(profile,source[0]+lo*delta[0]);vb=velocity(profile,source[0]+hi*delta[0]);dv=vb-va
        terms.append(length*(hi-lo)*(math.log1p(dv/va)/dv if dv else 1/va))
    return math.fsum(terms)


def main():
    summary=json.loads((HERE/'summary.json').read_text());ledger=json.loads((HERE/'execution.json').read_text())
    if ledger['status']!='completed' or ledger['summary_sha256']!=sha(HERE/'summary.json'):
        raise ValueError('Batch is not terminal with a matching summary')
    for name,expected in summary['output_sha256'].items():
        if sha(HERE/name)!=expected:raise ValueError('Batch artifact changed: '+name)
    prior=HERE.parent/'loma_geometry_preflight/layered_reference_delta_003'
    prior_summary=json.loads((prior/'summary.json').read_text())
    for name,expected in prior_summary['output_sha256'].items():
        if sha(prior/name)!=expected:raise ValueError('Prior104 artifact changed: '+name)
    known={}
    for line in (prior/'references.jsonl').read_text().splitlines():
        record=json.loads(line);pair=int(record['event'])*52+int(record['station'])
        if pair in known:raise ValueError('Repeated prior sample')
        known[pair]=record
    counts=collections.Counter();matched=[];lower_gaps=[];upper_gaps=[];eikonal=[]
    profile=summary['profile_x_velocity_km_km_s'];vmax=max(v for x,v in profile)
    with gzip.open(str(HERE/'references.csv.gz'),'rt',newline='') as stream:
        for index,row in enumerate(csv.DictReader(stream)):
            if (int(row['pair_index']),int(row['event']),int(row['station']))!=(index,index//52,index%52):
                raise ValueError('Reference pair support differs')
            source=[float(row['source_'+a]) for a in 'xyz'];receiver=[float(row['receiver_'+a]) for a in 'xyz']
            counts['pairs']+=1;counts['reference_valid']+=int(row['reference_valid'])
            if not row['time_s']:continue
            time=float(row['time_s']);straight=straight_action(profile,source,receiver)
            distance=math.sqrt(sum((a-b)**2 for a,b in zip(source,receiver)))
            lower_gaps.append(time-distance/vmax);upper_gaps.append(time-straight)
            gradient=[float(row['source_d'+a+'_s_per_km']) for a in 'xyz']
            eikonal.append(math.sqrt(sum(g*g for g in gradient))-1/velocity(profile,source[0]))
            if not all(math.isfinite(v) for v in (time,straight,distance)+tuple(gradient)):
                raise ValueError('Nonfinite reviewed reference')
            counts['branch_'+row['branch']]+=1
            if int(row['near_tie_count'])>1:counts['near_ties']+=1
    if counts['pairs']!=37648:raise ValueError('Full geometry support missing')
    with gzip.open(str(HERE/'certificates.jsonl.gz'),'rt') as stream:
        for line in stream:
            record=json.loads(line);pair=record['pair_index']
            if pair in known:
                if record['reference']!=known[pair]['reference']:raise ValueError('Prior104 reference changed')
                matched.append(pair)
    if len(matched)!=104 or len(set(matched))!=104:raise ValueError('Prior104 support not found exactly once')
    result=dict(scope='Post-completion readback and physical consistency, with no reference or production ray reruns',
        counts=dict(counts),prior104_full_reference_dictionary_matches=len(matched),
        physical_bounds=dict(minimum_time_minus_euclidean_over_global_vmax_s=min(lower_gaps),
            maximum_time_minus_independent_straight_action_s=max(upper_gaps),
            maximum_absolute_endpoint_eikonal_norm_residual_s_per_km=max(map(abs,eikonal))),
        interpretation='Physical-bound residuals are reported without a new scientific acceptance threshold; floating-point equality can leave roundoff-sized signed differences.',
        limitations=['These bounds are necessary consistency checks, not a separate completeness proof or an interval time-ordering certificate.',
            'Source gradients belong to the selected branch; near ties do not establish a unique ordinary derivative.',
            'No simulated observations, noise, inversion or production solver substitution was performed.'],
        summary_sha256=sha(HERE/'summary.json'),execution_sha256=sha(HERE/'execution.json'),
        prior104_summary_sha256=sha(prior/'summary.json'),review_source_sha256=sha(Path(__file__)))
    (HERE/'review.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
