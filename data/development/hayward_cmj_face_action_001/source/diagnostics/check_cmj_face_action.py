#!/usr/bin/env python3
"""Bounded action and one tangent witness for two explicitly new CMJ polygons.

No trace, field, optimizer, displacement step, or production status change.
This command requires a reviewed preparation before loading candidate geometry.
"""
import argparse
import csv
from fractions import Fraction as Q
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import signal
import sys
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {981: dict(points=1029,nodes=list(range(724,755))),
            987: dict(points=1031,nodes=list(range(726,758)))}


def require(condition, message):
    if not condition: raise ValueError(message)


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def read_json(path):
    return json.loads(path.read_text())


def rows(path):
    with path.open(newline='') as stream:
        reader=csv.DictReader(stream)
        require(len(reader.fieldnames)==len(set(reader.fieldnames)), 'Duplicate CSV fields')
        result=list(reader)
    require(result and all(None not in row and None not in row.values() for row in result), 'Incomplete CSV')
    return result


def encoded(value):
    if isinstance(value,Q):return str(value)
    if isinstance(value,dict):return {str(k):encoded(v) for k,v in value.items()}
    if isinstance(value,(tuple,list)):return [encoded(v) for v in value]
    return value


def save(path, value):
    with path.open('x') as stream:
        json.dump(encoded(value),stream,sort_keys=True,indent=2,allow_nan=False);stream.write('\n')


def save_gzip(path, value):
    with path.open('xb') as raw:
        with gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as compressed:
            with io.TextIOWrapper(compressed,encoding='utf-8') as stream:
                json.dump(encoded(value),stream,sort_keys=True,separators=(',',':'),allow_nan=False)
                stream.write('\n')
    with gzip.open(str(path),'rt',encoding='utf-8') as stream:
        require(json.load(stream)==encoded(value), 'Compressed output readback mismatch')


def number(text):
    binary=float(text)
    require(math.isfinite(binary), 'Nonfinite recorded binary64 value')
    return Q(binary)


def provenance(text):
    binary=float(text)
    require(math.isfinite(binary), 'Nonfinite recorded binary64 value')
    return dict(raw_text=text,binary64_hex=binary.hex(),exact_rational=Q(binary))


def verify_pins(root, pins):
    for name,digest in pins.items():
        path=(root/name).resolve();path.relative_to(root)
        require(sha(path)==digest, 'Changed pinned file: '+name)


def load_inputs(out, t):
    inputs=out/'inputs'
    statuses=rows(inputs/'original_status.csv');paths=rows(inputs/'original_paths.csv')
    selected=rows(inputs/'near_face_nodes.csv');grid_rows=rows(inputs/'trial_grid.csv')
    contexts=read_json(inputs/'native_context.json')
    events={int(r['id']):r for r in rows(inputs/'trial_events.csv')}
    stations={int(r['id']):r for r in rows(inputs/'stations.csv')}
    require([(int(r['event']),int(r['station'])) for r in statuses]==[(981,160),(987,160)], 'Wrong status roster')
    require([(int(r['event']),int(r['station'])) for r in contexts]==[(981,160),(987,160)], 'Wrong native context roster')
    require(set((int(r['event']),int(r['station'])) for r in paths)=={(981,160),(987,160)}, 'Extra native path')
    require(set((int(r['event']),int(r['station'])) for r in selected)=={(981,160),(987,160)}, 'Extra selected native path')
    axes=tuple(tuple(sorted({number(row[axis]) for row in grid_rows})) for axis in 'xyz')
    locations={tuple(number(row[a]) for a in 'xyz'):number(row['v']) for row in grid_rows}
    require(len(grid_rows)==len(locations)==462, 'Wrong or duplicate grid inventory')
    axis_index=[{x:i for i,x in enumerate(axis)} for axis in axes]
    velocity={tuple(axis_index[k][p[k]] for k in range(3)):v for p,v in locations.items()}
    grid=t.model(axes,velocity)
    require(Q(0) in axes[0][1:-1], 'Missing internal x=0 face')
    cases=[]
    for status,context in zip(statuses,contexts):
        event=int(status['event']);expected=EXPECTED[event]
        require(context['original_status']==status, 'Original status/context mismatch')
        require(context['source_native']==events[event] and context['receiver_native']==stations[160], 'Native table mapping mismatch')
        require(status['ray_converged']=='0' and status['ray_derivatives_evaluated']=='0', 'Preserve original false status and unevaluated partials')
        require(all(status[k]=='1' for k in ('ray_finite','ray_path_in_domain','ray_exact_source_endpoint',
                                           'ray_exact_receiver_endpoint')), 'Original geometric validity mismatch')
        require(status['ray_merged_nodes']=='0' and all(status[k]=='' for k in ('source_dx','source_dy','source_dz')),
                'Original source partials or merge state changed')
        native=[r for r in paths if int(r['event'])==event]
        require(len(native)==expected['points']==int(status['ray_path_points']), 'Wrong path count')
        require([int(r['node']) for r in native]==list(range(len(native))), 'Path order mismatch')
        metadata=[k for k in native[0] if k.startswith(('source_','receiver_'))]
        require(all(row[k]==status[k] for row in native for k in metadata), 'Path native identity mismatch')
        require(status['receiver_channel_seed_id']=='NC.CMJ..EHZ' and status['receiver_location_code']=='', 'Lost native channel or empty location')
        selection=[r for r in selected if int(r['event'])==event]
        require([int(r['node']) for r in selection]==expected['nodes'], 'Changed reviewed node inventory')
        for row in selection:
            source=native[int(row['node'])]
            require(all(row[k]==v for k,v in source.items()) and number(row['face_x_km'])==0,
                    'Selection no longer joins exact original path row')
        original=[tuple(number(row[a]) for a in 'xyz') for row in native]
        require(original[0]==tuple(number(status['source_'+a]) for a in 'xyz') and
                original[-1]==tuple(number(status['receiver_'+a]) for a in 'xyz'), 'Exact endpoint mismatch')
        require(original[0]==tuple(number(events[event][a]) for a in 'xyz') and
                original[-1]==tuple(number(stations[160][a]) for a in 'xyz'), 'Endpoint/table geometry mismatch')
        require(all(0<i<len(original)-1 for i in expected['nodes']), 'Selection includes an endpoint')
        chosen=set(expected['nodes'])
        candidate=[(Q(0),p[1],p[2]) if i in chosen else p for i,p in enumerate(original)]
        require(candidate[0]==original[0] and candidate[-1]==original[-1], 'Candidate changed an endpoint')
        require(all(t.contains(grid,p) for p in original), 'Original polygon outside physical box')
        require(all(a!=b for a,b in zip(original,original[1:])), 'Original zero-length edge')
        ineligible=[]
        outside=[i for i,p in enumerate(candidate) if not t.contains(grid,p)]
        collapsed=[i for i,(a,b) in enumerate(zip(candidate,candidate[1:])) if a==b]
        if outside:ineligible.append(dict(reason='candidate_outside_physical_box',nodes=outside))
        if collapsed:ineligible.append(dict(reason='candidate_zero_length_edges_no_merging',edges=collapsed))
        cases.append(dict(event=event,station=160,native_context=context,
            full_metadata={k:status[k] for k in metadata},original_status=status,
            original=original,candidate=candidate,selected_nodes=expected['nodes'],
            candidate_ineligibility=ineligible,
            coordinate_provenance=[dict(node=i,original={a:provenance(row[a]) for a in 'xyz'},
                candidate_exact_rational=candidate[i],x_replaced_with_exact_zero=i in chosen)
                for i,row in enumerate(native)]))
    model_provenance=dict(applies_to_pairs=[(981,160),(987,160)],native_contexts=contexts,
        recorded_grid_sha256=sha(inputs/'trial_grid.csv'),axes_exact_rational=axes,
        interpretation='Continuous trilinear interpolant of the exact recorded binary64 nodal values.',
        nodes=[dict(csv_row=i,values={a:provenance(row[a]) for a in ('x','y','z','v')})
               for i,row in enumerate(grid_rows)])
    return grid,cases,model_provenance


def interval_record(bounds, units):
    return dict(exact_rational_bounds=bounds,units=units,
                rounded_binary64_display_only=[float(x) for x in bounds],
                contains_zero=bounds[0]<=0<=bounds[1])


def evaluate_case(t, grid, case, settings):
    original,candidate=case['original'],case['candidate']
    cache={};records=[];counts=dict(action_edge_evaluations=0,tangent_edge_evaluations=0,
                                   witness_nonzero_edge_evaluations=0)
    if case['candidate_ineligibility']:
        return dict(event=case['event'],station=160,native_context=case['native_context'],full_metadata=case['full_metadata'],
            original_status=case['original_status'],original_convergence_flag_preserved='0',candidate_convergence_status=None,
            candidate_basis='Prescribed polygon; no repair or merging.',selected_nodes=case['selected_nodes'],
            coordinate_provenance=case['coordinate_provenance'],candidate_ineligibility=case['candidate_ineligibility'],
            settings=settings,counts=counts,original_action=None,candidate_action=None,candidate_minus_original=None,
            action_classification='ineligible_candidate',unchanged_edge_count=None,
            tangent_witness=dict(status='ineligible_candidate',reasons=case['candidate_ineligibility']),
            interpretation='Identified geometry retained; no action or variation evaluated for this case.')
    def action(a,b):
        key=(a,b)
        if key not in cache:
            cache[key]=len(records)
            records.append(dict(cache_id=cache[key],a_exact=a,b_exact=b,record=t.edge_action(grid,a,b,settings)))
            counts['action_edge_evaluations']+=1
        return cache[key]
    old_ids=[action(a,b) for a,b in zip(original,original[1:])]
    new_ids=[action(a,b) for a,b in zip(candidate,candidate[1:])]
    old_total,new_total,difference=t.point(0),t.point(0),t.point(0);changed=[]
    for i,(old,new) in enumerate(zip(old_ids,new_ids)):
        before,after=records[old]['record']['action'],records[new]['record']['action']
        old_total=t.add(old_total,before);new_total=t.add(new_total,after)
        if old==new:continue
        delta=t.sub(after,before);difference=t.add(difference,delta)
        changed.append(dict(edge=i,original_record=old,candidate_record=new,difference=delta))
    naive=t.sub(new_total,old_total)
    require(max(naive[0],difference[0])<=min(naive[1],difference[1]), 'Inconsistent paired/full action bounds')
    components=[[t.point(0) for axis in range(3)] for p in candidate]
    blocked=set();edge_components=[];jump_records=[];unsupported=[]
    for i,key in enumerate(new_ids):
        aligned=records[key]['record']['aligned']
        if len(aligned)>1:unsupported.append(dict(edge=i,aligned=aligned))
        elif aligned:jump_records.append(dict(edge=i,whole_piece_jumps=t.face_jumps(grid,candidate[i],candidate[i+1])))
    witness=dict(status='unsupported_multiple_aligned_faces',edges=unsupported) if unsupported else None
    if not unsupported:
        for i,(a,b) in enumerate(zip(candidate,candidate[1:])):
            record=t.edge_tangent_components(grid,a,b,settings)
            counts['tangent_edge_evaluations']+=1
            saved_components=[list(part) for part in record['components']]
            fixed=[]
            if i==0:saved_components[0]=None;fixed.append(0)
            if i==len(candidate)-2:saved_components[1]=None;fixed.append(1)
            edge_components.append(dict(edge=i,components=saved_components,
                blocked_axes=record['blocked_axes'],fixed_endpoint_slots_omitted=fixed))
            for side in (0,1):
                for axis,term in enumerate(record['components'][side]):
                    if term is None:blocked.add((i+side,axis))
                    else:components[i+side][axis]=t.add(components[i+side][axis],term)
        for i,axis in blocked:components[i][axis]=None
        witness=dict(status='no_sign_resolved_feasible_tangent_component',
                     limitation='Not an all-direction stationarity result.')
        chosen=None
        for i in range(1,len(candidate)-1):
            for axis,bounds in enumerate(components[i]):
                if bounds is None or bounds[0]<=0<=bounds[1]:continue
                sign=-1 if bounds[0]>0 else 1
                if ((sign<0 and candidate[i][axis]==grid['axes'][axis][0]) or
                    (sign>0 and candidate[i][axis]==grid['axes'][axis][-1])):continue
                chosen=(i,axis,sign);break
            if chosen is not None:break
        if chosen is not None:
            i,axis,sign=chosen;direction=[(Q(0),)*3 for p in candidate]
            d=[Q(0)]*3;d[axis]=Q(sign);direction[i]=tuple(d)
            feasible=t.feasible_directions(grid,candidate,direction)
            derivative=t.point(0);terms=[]
            # Every omitted edge has both endpoint directions zero, so both
            # complete first-variation terms vanish exactly. No action is sampled.
            for edge in (i-1,i):
                record=t.edge_directional(grid,candidate[edge],candidate[edge+1],
                                          direction[edge],direction[edge+1],settings)
                derivative=t.add(derivative,record['derivative']);terms.append(dict(edge=edge,record=record))
                counts['witness_nonzero_edge_evaluations']+=1
            require(feasible is not None and feasible>0, 'No positive feasible witness step')
            witness=dict(status='negative_tangent_witness' if derivative[1]<0 else 'directional_interval_unresolved',
                node=i,axis='xyz'[axis],sign=sign,selected_near_face_node=i in case['selected_nodes'],
                incident_to_exact_face_edge=any(node==i for node,unused in blocked),
                distance_in_node_indices_to_selected_set=min(abs(i-j) for j in case['selected_nodes']),
                nonzero_direction=direction[i],direction_euclidean_norm_exact=Q(1),
                full_directional=interval_record(derivative,'s per dimensionless perturbation'),
                descent_magnitude_bounds=(-derivative[1],-derivative[0]) if derivative[1]<0 else None,
                feasible_positive_step_bound=feasible,nonzero_edge_terms=terms,
                exactly_zero_other_edge_count=len(candidate)-3,
                choice='First sign-resolved physically feasible tangent component in node/axis order; one direction only.',
                limitation='No step taken; no alternative direction if the full interval remains unresolved.')
    require(counts['action_edge_evaluations']<=len(original)-1+len(case['selected_nodes'])+1, 'Unexpected action inventory')
    require(counts['tangent_edge_evaluations']<=len(candidate)-1 and counts['witness_nonzero_edge_evaluations']<=2,
            'Unexpected first-variation inventory')
    return dict(event=case['event'],station=160,native_context=case['native_context'],full_metadata=case['full_metadata'],
        original_status=case['original_status'],original_convergence_flag_preserved='0',candidate_convergence_status=None,
        candidate_basis='Prescribed polygon: only the reviewed original node x values are replaced by exact zero.',
        candidate_ineligibility=[],
        selected_nodes=case['selected_nodes'],coordinate_provenance=case['coordinate_provenance'],
        settings=settings,counts=counts,original_action=interval_record(old_total,'s'),
        candidate_action=interval_record(new_total,'s'),candidate_minus_original=interval_record(difference,'s'),
        action_classification='decreased' if difference[1]<0 else ('increased' if difference[0]>0 else 'unresolved'),
        unchanged_edge_count=len(old_ids)-len(changed),changed_edges=changed,
        original_edge_record_ids=old_ids,candidate_edge_record_ids=new_ids,unique_action_edge_records=records,
        candidate_free_node_tangent_components=[dict(node=i,components=components[i]) for i in range(1,len(candidate)-1)] if not unsupported else None,
        candidate_edge_tangent_records=edge_components,face_jump_records=jump_records,tangent_witness=witness,
        interpretation='New polygon action and feasible directional bounds only; no stationarity, cause, first-arrival or source/model derivative claim.')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True);args=parser.parse_args()
    out=(ROOT/args.output).resolve();out.relative_to(ROOT)
    require(not (out/'summary.json').exists() and not list(out.glob('event_*.json.gz')) and
            not (out/'model_provenance.json').exists(), 'Preserve previous or partial calculations')
    prepared=read_json(out/'prepared.json');review=read_json(out/'prelaunch_review.json')
    require(review.get('status')=='passed' and review.get('prepared_sha256')==sha(out/'prepared.json'), 'Require exact independent prelaunch review')
    verify_pins(ROOT,prepared['input_sha256']);verify_pins(out,prepared['output_sha256'])
    sys.path.insert(0,str(out/'source'))
    from diagnostics import trilinear_action_bounds as t
    require(Path(t.__file__).resolve()==out/'source/diagnostics/trilinear_action_bounds.py', 'Arithmetic module not frozen')
    settings=t.options(**prepared['settings'])
    require(settings==dict(terms=8,subdivisions=1,bits=128), 'Changed finite integration budget')
    def interrupted(signum,unused):raise SystemExit(128+signum)
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    started=time.time();status='failed';error=None;results=[];outputs={}
    try:
        grid,cases,model_provenance=load_inputs(out,t)
        save(out/'model_provenance.json',model_provenance)
        outputs['model_provenance.json']=sha(out/'model_provenance.json')
        for case in cases:
            result=evaluate_case(t,grid,case,settings)
            name='event_'+str(case['event'])+'.json.gz';save_gzip(out/name,result);outputs[name]=sha(out/name)
            results.append({key:result[key] for key in ('event','station','native_context','original_convergence_flag_preserved',
                'candidate_convergence_status','counts','original_action','candidate_action','candidate_minus_original',
                'action_classification','unchanged_edge_count','tangent_witness')})
        verify_pins(ROOT,prepared['input_sha256']);verify_pins(out,prepared['output_sha256'])
        status='completed_bounded_calculation'
    except BaseException as exc:
        error=dict(type=type(exc).__name__,message=str(exc));raise
    finally:
        # Preserve hashes even for a partial output left by an interrupted write.
        outputs={path.name:sha(path) for path in list(out.glob('event_*.json.gz'))+
                 ([out/'model_provenance.json'] if (out/'model_provenance.json').exists() else [])}
        save(out/'summary.json',dict(status=status,error=error,elapsed_seconds=time.time()-started,settings=settings,
            prepared_sha256=sha(out/'prepared.json'),prelaunch_review_sha256=sha(out/'prelaunch_review.json'),
            input_sha256=prepared['input_sha256'],output_sha256=outputs,results=results,
            native_trace_calls=0,field_calls=0,optimizer_calls=0,descent_steps=0,
            scientific_scope='Two prescribed native polygons only; calculation completion is not a convergence or accuracy pass.'))


if __name__=='__main__':main()
