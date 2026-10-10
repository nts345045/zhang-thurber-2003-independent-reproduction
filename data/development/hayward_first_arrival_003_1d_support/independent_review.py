#!/usr/bin/env python3
"""Reconcile the frozen full-support comparison with terminal preflight evidence."""
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics

HERE = Path(__file__).resolve().parent

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def require(ok, message):
    if not ok:
        raise ValueError(message)

def rows(path):
    with path.open() as stream:
        reader = csv.DictReader(stream)
        names, values = reader.fieldnames, list(reader)
    require(names and len(names) == len(set(names)), 'Invalid header: ' + str(path))
    require(all(None not in r for r in values), 'Invalid row: ' + str(path))
    return values

def stats(values):
    return dict(count=len(values), minimum=min(values), maximum=max(values),
                median=statistics.median(values), mean=statistics.mean(values),
                rms=math.sqrt(sum(v*v for v in values)/len(values)))

def main():
    summary = json.loads((HERE/'summary.json').read_text())
    require(summary['status'] == 'complete', 'Reference run is incomplete')
    prefix = 'data/development/' + HERE.name + '/'
    verified = {}
    for category in ('input_sha256', 'output_sha256'):
        for name, expected in summary[category].items():
            relative = name[len(prefix):] if name.startswith(prefix) else 'source/' + Path(name).name
            require(sha(HERE/relative) == expected, 'Captured source/input hash mismatch: ' + name)
            verified[relative] = expected
    terminal_path = HERE.parent/'hayward_first_arrival_003_review/review.json'
    terminal = json.loads(terminal_path.read_text())
    shared = dict((name, value) for name, value in summary['original_reverified_sha256'].items()
                  if name in terminal['verified_input_sha256'])
    require(all(terminal['verified_input_sha256'][k] == v for k,v in shared.items()),
            'Terminal preflight and reference inputs differ')
    require(len(shared) == 16, 'Unexpected terminal shared-file coverage')
    terminal_ledger = json.loads((terminal_path.parent/'preflight_execution.json').read_text())
    require(terminal_ledger['status'] == 'failed_checks_preserved', 'Unexpected terminal preflight status')
    require(terminal['nonconverged_rays'] == 139, 'Unexpected terminal failure count')
    comparison = rows(HERE/'comparison.csv')
    original = rows(HERE/'inputs/initial_linearization_rows.csv')
    require(len(comparison) == len(original) == 14262, 'Full support count changed')
    for number, (a,b) in enumerate(zip(original, comparison)):
        require(int(a['row']) == int(b['row']) == number, 'Rows are not contiguous')
        require(all(b[k] == v for k,v in a.items()), 'Saved numerical/native metadata changed')
    matrix = {}
    for entry in rows(HERE/'inputs/initial_linearization_matrix.csv'):
        row, col, value = int(entry['row']), int(entry['column']), float(entry['value'])
        offset = col - 4*int(comparison[row]['i'])
        if 0 <= offset < 4:
            require((row,offset) not in matrix, 'Duplicate source entry')
            matrix[row,offset] = value
    with (HERE/'references.jsonl').open() as stream:
        references = [json.loads(line) for line in stream]
    require(len(references) == len(comparison), 'Reference row count changed')
    for number, (r,item) in enumerate(zip(comparison,references)):
        require(all(item[a] == r[b] for a,b in [('row','row'),('observation_row','observation_row'),
                                               ('event','i'),('station','station')]), 'Reference join changed')
        ref=item['reference']; first=ref['first_arrival']
        require(ref['complete'] and ref['reference_valid'] and len(ref['near_ties']) == 1,
                'Reference is not complete, valid and uniquely first')
        require(float(r['reference_time_s']) == first['time_s'], 'Reference time mapping changed')
        require(float(r['production_minus_reference_s']) == float(r['ray_time']) - first['time_s'],
                'Time error mapping changed')
        require(matrix[number,3] == 1, 'Origin derivative is not unity')
        errors=[]
        for d,a in enumerate('xyz'):
            prod=float(r['production_source_d'+a]); exact=first['source_derivative_s_per_km'][d]
            require(prod == matrix[number,d] and exact == float(r['reference_source_d'+a]),
                    'Source derivative column mapping changed')
            error=prod-exact
            require(error == float(r['production_source_d'+a+'_minus_reference']), 'Derivative subtraction changed')
            errors.append(error)
        r['source_error_norm_s_per_km']=math.sqrt(sum(e*e for e in errors))
        require(math.isfinite(r['source_error_norm_s_per_km']), 'Nonfinite source norm')
    groups={}
    for key,subset in [('all',comparison),('local_flag_true',[r for r in comparison if r['ray_converged']=='1']),
                       ('local_flag_false',[r for r in comparison if r['ray_converged']=='0'])]:
        times=[abs(float(r['production_minus_reference_s'])) for r in subset]
        errors=[r['source_error_norm_s_per_km'] for r in subset]
        groups[key]=dict(count=len(subset), absolute_time_error_s=stats(times),
                        source_error_euclidean_norm_s_per_km=stats(errors),
                        time_limit_pass=sum(t <= 2.5e-5 for t in times),
                        source_vector_limit_pass=sum(e <= 3e-6 for e in errors),
                        both_limits_pass=sum(t <= 2.5e-5 and e <= 3e-6 for t,e in zip(times,errors)))
    result=dict(scope='Independent saved-table/hash/native-join review; no ray or reference rerun',
        terminal_preflight_status=terminal_ledger['status'], terminal_review_sha256=sha(terminal_path),
        verified_shared_terminal_files=shared, verified_captured_files=verified,
        comparison_rows_with_all_original_fields_preserved=len(comparison),
        source_derivative_matrix_entries_verified=len(matrix), reference_joins_verified=len(references),
        thresholds=dict(time_s=2.5e-5,source_euclidean_vector_norm_s_per_km=3e-6,
                        basis='Retained analytic component controls; not a relabeling of preflight success'),
        groups=groups, largest_source_error_row=max(comparison,key=lambda r:r['source_error_norm_s_per_km']),
        review_source_sha256=sha(Path(__file__)),
        limitations=['This review verifies captured joins, arithmetic and provenance, not independent reference mathematics.',
                     'Continuous references apply to this initial monotone, horizontally uniform profile only.',
                     'Local stopping flags are insufficient accuracy certificates; a locally flagged ray has the largest error.',
                     'Refining only the 139 failed flags cannot establish full-support accuracy.',
                     'The reference snapshot captured a completed linearization before the overall preflight finished; terminal status is failure and all shared numerical inputs match.'])
    (HERE/'independent_review.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(groups,indent=2))

if __name__=='__main__':
    main()
