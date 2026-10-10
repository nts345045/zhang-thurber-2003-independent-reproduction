#!/usr/bin/env python3
"""Compare saved production half-polygon gradients with reviewed interval bounds."""
import csv
from fractions import Fraction as Q
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DATA = ROOT/'data/development'
BENCH = DATA/'hayward_cmj_fixed_polygon_kernel_001'
POST = DATA/'hayward_cmj_post_half_step_tangent_001'
POST_REVIEW = DATA/'hayward_cmj_post_half_step_tangent_review_001/review.json'
HALF = DATA/'hayward_cmj_tangent_half_step_001'
PINS = {}


def require(ok, message):
    if not ok: raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''): h.update(block)
    return h.hexdigest()


def pin(path, digest):
    require(sha(path) == digest, 'Changed pin: '+str(path))
    key = str(path.relative_to(ROOT)) if ROOT in path.parents else str(path)
    require(key not in PINS or PINS[key] == digest, 'Conflicting pin')
    PINS[key] = digest


def read(path):
    with (gzip.open(str(path), 'rt') if path.suffix == '.gz' else path.open()) as stream: return json.load(stream)


def encoded(value):
    if isinstance(value, Q): return str(value)
    if isinstance(value, dict): return {k: encoded(v) for k,v in value.items()}
    if isinstance(value, (tuple, list)): return [encoded(v) for v in value]
    return value


def save(path, value):
    payload = (json.dumps(encoded(value), indent=2, sort_keys=True, allow_nan=False)+'\n').encode('utf8')
    with path.open('xb') as stream:
        if path.suffix == '.gz':
            with gzip.GzipFile(fileobj=stream, mode='wb', mtime=0) as output: output.write(payload)
        else: stream.write(payload)


def terminal(folder, review_path, prefix, status):
    review = read(review_path); require(review['status'] == 'passed', 'Passed independent terminal review required')
    pin(review_path, sha(review_path))
    for key,name in ((prefix+'prepared_sha256','prepared.json'), (prefix+'summary_sha256','summary.json'),
                     (prefix+'execution_sha256','execution.json'), ('outer_reaping_sha256','outer_reaping.json')):
        pin(folder/name, review[key])
    prepared=read(folder/'prepared.json'); summary=read(folder/'summary.json'); execution=read(folder/'execution.json'); outer=read(folder/'outer_reaping.json')
    require(summary['status'] == execution['status'] == status and summary['error'] is None and execution['return_code'] == 0, 'Successful terminal result')
    require(outer['status'] == 'completed_and_reaped' and outer['tool_exit_code'] == 0
            and outer['wrapper_pid'] == execution['pid'] and outer['wrapper_process_absent'], 'Owned/reaped terminal result')
    require(outer['summary_sha256'] == sha(folder/'summary.json') and outer['execution_sha256'] == sha(folder/'execution.json')
            and outer['prepared_sha256'] == sha(folder/'prepared.json'), 'Outer receipt binding')
    require(execution['summary_sha256'] == sha(folder/'summary.json') and summary['output_sha256'] == execution['output_sha256'], 'Terminal output map')
    for base,values in ((ROOT,prepared['input_sha256']), (folder,prepared['output_sha256']), (folder,summary['output_sha256'])):
        for name,digest in values.items(): pin(base/name,digest)
    return prepared,summary,execution,review


def main():
    require(not any((HERE/n).exists() for n in ('summary.json','comparison.json.gz','comparison.json.gz.identifiers.json')), 'Fresh saved-only output required')
    approval=read(HERE/'source_review.json')
    require(approval['status']=='passed' and approval['checker_sha256']==sha(Path(__file__)), 'Independent checker source review required')
    for path in (Path(__file__),HERE/'README.md',HERE/'source_review.json'): pin(path,sha(path))
    bp,bs,be,br=terminal(BENCH,BENCH/'review.json','','completed_fixed_polygon_comparison')
    pp,ps,pe,pr=terminal(POST,POST_REVIEW,'native_','completed_bounded_post_half_tangent_and_support')
    require(be['outputs_stable'] and len(be['commands'])==2
            and all(c['child_reaped'] and c['return_code']==0 for c in be['commands']), 'Reaped compile and eight-polygon command')
    identities=bs['native_contexts']; require(identities==ps['native_contexts'] and [i['event'] for i in identities]==[981,987], 'Same full native roster')
    oracle=read(BENCH/'oracle.json.gz'); require(oracle['native_contexts']==identities, 'Frozen benchmark identity roster')
    sidecar=read(BENCH/'results/gradients.csv.identifiers.json')
    require(sidecar['native_contexts']==identities and sidecar['oracle_sha256']==sha(BENCH/'oracle.json.gz')
            and sidecar['expected_file']==str((BENCH/'results/gradients.csv').relative_to(ROOT)), 'Emitted gradient sidecar')
    pin(BENCH/'run.py',bp['output_sha256']['run.py'])
    spec=importlib.util.spec_from_file_location('frozen_benchmark_parser',str(BENCH/'run.py'))
    parser=importlib.util.module_from_spec(spec); spec.loader.exec_module(parser)
    # Only its pure exact-hex/display and error-interval functions are called.
    with (BENCH/'results/gradients.csv').open(newline='') as stream: rows=list(csv.DictReader(stream))
    require(len(rows)==24672, 'Complete eight-polygon emitted gradient table')
    save(HERE/'comparison.json.gz.identifiers.json',dict(native_contexts=identities,
         expected_file=str((HERE/'comparison.json.gz').relative_to(ROOT)),file_sha256=None,
         input_sha256=PINS,original_convergence_flag='0',candidate_convergence_status=None,
         role='Saved half-polygon ordinary gradient versus raw available interval components; unavailable normals have no derivative oracle.'))
    reports=[];details=[]
    for identity in identities:
        event=identity['event']; polygon=next(p for p in oracle['polygons'] if p['event']==event and p['stage_integer']==3)
        post_file=POST/('event_'+str(event)+'.json.gz'); post=read(post_file)
        trial_file=HALF/('event_'+str(event))/'result.json.gz'; trial=read(trial_file)
        pin(trial_file,post['prior_result_sha256'])
        require(all(all(r[k]==identity[k] for k in ('event','station','native_context','catalog_uses')) for r in (polygon,post,trial)), 'Complete event/origin/epoch/catalog joins')
        require(len(identity['catalog_uses'])==9 and post['original_convergence_flag']=='0' and post['candidate_convergence_status'] is None, 'Original flags and catalog roster')
        status=identity['native_context']['original_status']
        require(status['ray_converged']==status['ray_derivatives_evaluated']=='0' and all(status['source_d'+k]=='' for k in 'xyz'), 'Original blank source partials')
        require(post['status']=='completed_tangent_and_support_bounds' and not post['ineligibility'], 'Reviewed current available components')
        path=[tuple(map(Q,p)) for p in trial['result']['trial']];n=len(path)
        require([tuple(map(Q,p)) for p in polygon['coordinates_exact_rational']]==path
                and [tuple(map(Q,p['exact_rational'])) for p in post['coordinate_provenance']]==path
                and polygon['node_count']==n, 'Same exact rounded half geometry')
        require(post['saved_trial_action']==trial['result']['action']['trial_action']==polygon['action']['full_bounds'], 'Same full-action enclosure for this polygon')
        require(polygon['derivatives']['status']=='unavailable', 'Frozen benchmark derivative roster remains unchanged')
        selected=[r for r in rows if int(r['event'])==event and int(r['stage'])==3]
        require([(int(r['node']),int(r['axis'])) for r in selected]==[(i,k) for i in range(1,n-1) for k in range(3)]
                and all(int(r['station'])==160 for r in selected), 'Complete half-stage emitted vector')
        require([r['node'] for r in post['free_node_components']]==list(range(1,n-1)), 'Complete available oracle vector')
        available=[];unavailable=[];actual_norm=Q(0)
        for row in selected:
            node,axis=int(row['node']),int(row['axis']);value=parser.number(row,'component',True)
            enclosure=post['free_node_components'][node-1]['components'][axis]
            entry=dict(node=node,axis=axis,emitted_hex=row['component_hex'],value_exact=value)
            if enclosure is None: unavailable.append(entry);continue
            entry.update(parser.error(value,enclosure));available.append(entry);actual_norm+=value*value
        require([(r['node'],r['axis']) for r in unavailable]==[tuple(v) for v in post['geometric_blocked_slots']], 'Unavailable normals remain separate')
        audit=next(c for c in pr['cases'] if c['event']==event)
        require(all(audit[k]==identity[k] for k in ('event','station','native_context','catalog_uses'))
                and tuple(map(Q,audit['post_squared_bounds']))==(Q(post['post_step_norm']['lower_squared']),Q(post['post_step_norm']['upper_squared'])), 'Reviewed post-half norm binding')
        low=sum((r['distance_to_enclosure']**2 for r in available),Q(0));high=sum((r['absolute_error_upper']**2 for r in available),Q(0))
        report=dict(identity,stage='half',nodes=n,available_components=len(available),unavailable_components=len(unavailable),
            component_error_norm_squared_bounds=(low,high),error_norm_units='s^2/km^2',component_units='s/km',
            largest_component_distance=max(r['distance_to_enclosure'] for r in available),
            largest_component_absolute_error_upper=max(r['absolute_error_upper'] for r in available),
            emitted_available_raw_norm_squared=actual_norm,within_enclosure_count=sum(r['distance_to_enclosure']==0 for r in available),
            original_convergence_flag='0',candidate_convergence_status=None,
            interpretation='Error bounds for raw available components only. Unavailable ordinary normals are not compared with a supporting-vector choice; no stopping or accuracy cutoff.')
        reports.append(report);details.append(dict(report,available_component_errors=available,unavailable_ordinary_components=unavailable,
             saved_action_bounds=post['saved_trial_action'],geometry_sha256=sha(trial_file),post_components_sha256=sha(post_file)))
    for name,digest in list(PINS.items()): pin(ROOT/name,digest)
    save(HERE/'comparison.json.gz',dict(native_contexts=identities,cases=details,input_sha256=PINS,
         action_scope='Exact geometry and existing full-action bounds joined; no additional action comparison or integration.',
         primitive_integrations=0,cpp_calls=0,metric_calls=0,trace_calls=0))
    save(HERE/'summary.json',dict(status='completed_saved_half_gradient_comparison',native_contexts=identities,cases=reports,
         checker_sha256=sha(Path(__file__)),source_review_sha256=sha(HERE/'source_review.json'),input_sha256=PINS,
         benchmark_review_sha256=sha(BENCH/'review.json'),post_half_review_sha256=sha(POST_REVIEW),
         output_sha256={n:sha(HERE/n) for n in ('comparison.json.gz','comparison.json.gz.identifiers.json')},
         numerical_integrations=0,cpp_calls=0,subprocess_calls=0,pure_parser_imports=1))
    print(json.dumps(dict(status='completed_saved_half_gradient_comparison',summary_sha256=sha(HERE/'summary.json'))))


if __name__=='__main__': main()
