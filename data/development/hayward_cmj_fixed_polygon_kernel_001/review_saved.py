#!/usr/bin/env python3
"""Stdlib saved CSV/oracle readback. No evaluator, compiler or project imports."""
import csv
from decimal import Decimal
from fractions import Fraction as Q
import gzip
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
EXPECTED='9fbc70bc9abd73eaf8b8fa2b40403c840af80732777d5b94468389b671cfc7cc'
PINS={}; CHECKS=0

def require(ok,message):
    global CHECKS
    CHECKS+=1
    if not ok: raise ValueError(message)

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''): h.update(b)
    return h.hexdigest()

def pin(p,d):
    require(p.is_file() and sha(p)==d,'Changed pin: '+str(p))
    require(str(p) not in PINS or PINS[str(p)]==d,'Conflicting pin'); PINS[str(p)]=d

def read(p):
    with (gzip.open(str(p),'rt') if p.suffix=='.gz' else p.open()) as f: return json.load(f)

def encoded(x):
    if isinstance(x,Q): return str(x)
    if isinstance(x,dict): return {k:encoded(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)): return [encoded(v) for v in x]
    return x

def table(name):
    with (HERE/'results'/name).open(newline='') as f:
        r=csv.DictReader(f); require(len(r.fieldnames)==len(set(r.fieldnames)),'Duplicate CSV header'); rows=list(r)
    require(all(None not in r for r in rows),'Malformed CSV'); return rows

def hexadecimal(token):
    # Independent base-16 integer parsing retains every extended-significand bit.
    sign=-1 if token.startswith('-') else 1; text=token.lstrip('+-').lower()
    require(text.startswith('0x') and text.count('p')==1,'Finite hex required')
    significand,exponent=text[2:].split('p'); whole,dot,tail=significand.partition('.')
    return sign*Q(int(whole+tail,16))*Q(2)**(int(exponent)-4*len(tail))

def number(row,key,binary64=False):
    q=hexadecimal(row[key+'_hex']); d=Decimal(row[key])
    require(d.is_finite() and abs(Q(d)-q)<=Q(10)**d.as_tuple().exponent/2,'Decimal/wide-hex display join')
    if binary64:
        require(Q(float(row[key]))==q and float(row[key]).hex()==float.fromhex(row[key+'_hex']).hex(),'Binary64 round trip including signed zero')
    return q

def nearest(x,bits):
    """Exact scalar round-to-nearest, ties-to-even for the normal finite values here."""
    if not x: return Q(0)
    sign=1 if x>0 else -1; x=abs(x); e=x.numerator.bit_length()-x.denominator.bit_length()
    if x<Q(2)**e: e-=1
    require(e>=(-1022 if bits==53 else -16382),'No unmodeled subnormal arithmetic')
    unit=Q(2)**(e-bits+1); scaled=x/unit; n,r=divmod(scaled.numerator,scaled.denominator)
    if 2*r>scaled.denominator or (2*r==scaled.denominator and n%2): n+=1
    return sign*n*unit

def accumulated(values,bits):
    result=Q(0)
    for v in values: result=nearest(result+v,bits)
    return result

def bounds(v):
    a,b=map(Q,v); require(a<=b,'Ordered reference enclosure'); return a,b

def error(v,oracle):
    a,b=bounds(oracle); lo,hi=v-b,v-a
    return dict(value_exact=v,oracle_bounds=(a,b),error_bounds=(lo,hi),distance_to_enclosure=max(lo,-hi,Q(0)),absolute_error_upper=max(abs(lo),abs(hi)))

def main():
    require(not (HERE/'review.json').exists(),'Fresh review only')
    source_review=read(HERE/'review_saved_source.json')
    require(source_review['status']=='passed' and source_review['checker_sha256']==sha(Path(__file__)),'Readback source approval')
    for p in (Path(__file__),HERE/'review_saved_source.json'): pin(p,sha(p))
    prepared=read(HERE/'prepared.json'); summary=read(HERE/'summary.json'); execution=read(HERE/'execution.json'); outer=read(HERE/'outer_reaping.json')
    pin(HERE/'prepared.json',EXPECTED)
    require(summary['status']==execution['status']=='completed_fixed_polygon_comparison' and summary['error'] is None and execution['return_code']==0,'Completed comparison')
    require(outer['status']=='completed_and_reaped' and outer['tool_exit_code']==0 and outer['wrapper_pid']==execution['pid'] and outer['wrapper_process_absent'],'Outer reaping')
    for key,name in [('prepared_sha256','prepared.json'),('summary_sha256','summary.json'),('execution_sha256','execution.json'),('prelaunch_review_sha256','prelaunch_review.json')]: pin(HERE/name,outer[key])
    approval=read(HERE/'prelaunch_review.json'); require(approval['status']=='passed' and approval['prepared_sha256']==EXPECTED,'Native source gate')
    require(summary['prepared_sha256']==execution['prepared_sha256']==EXPECTED and execution['prelaunch_review_sha256']==sha(HERE/'prelaunch_review.json'),'Terminal source link')
    require(execution['outputs_stable'] and execution['unsettled_groups']==[] and len(execution['commands'])==2,'Stable child inventory')
    require([c['command'] for c in execution['commands']]==prepared['commands'] and all(c['return_code']==0 and c['child_reaped'] for c in execution['commands']),'Exact commands both reaped')
    require(summary['output_sha256']==execution['output_sha256'] and execution['summary_sha256']==sha(HERE/'summary.json'),'Terminal output binding')
    for base,key in [(ROOT,'input_sha256'),(HERE,'output_sha256'),(Path('/'),'runtime_sha256')]:
        for name,digest in prepared[key].items(): pin(base/name,digest)
    pin(Path(prepared['python']['executable']),prepared['python']['sha256'])
    files={str(p.relative_to(HERE)) for d in ('results','logs','build') for p in (HERE/d).rglob('*') if p.is_file()}
    require(files==set(summary['output_sha256']),'Exact closed output inventory')
    for name,digest in summary['output_sha256'].items(): pin(HERE/name,digest)
    pin(HERE/'outer_reaping.json',sha(HERE/'outer_reaping.json'))
    oracle=read(HERE/'oracle.json.gz'); identities=read(HERE/'native_contexts.json'); details=read(HERE/'results/comparison_details.json.gz')
    require(identities==oracle['native_contexts']==summary['native_contexts']==execution['native_contexts']==outer['native_contexts']==details['native_contexts'],'All full native contexts')
    require([v['event'] for v in identities]==[981,987] and sum(len(v['catalog_uses']) for v in identities)==18,'Authoritative event/catalog-use roster')
    for identity in identities:
        status=identity['native_context']['original_status']
        require(status['ray_converged']==status['ray_derivatives_evaluated']=='0' and all(status['source_d'+k]=='' for k in 'xyz'),'Original failed flags and blank source partials')
    for folder,names in [('results',['totals.csv','edges.csv','gradients.csv','pairs.csv','comparison_details.json.gz']),('logs',['command_0.stdout','command_0.stderr','command_1.stdout','command_1.stderr'])]:
        for name in names:
            s=read(HERE/folder/(name+'.identifiers.json'))
            require(s['native_contexts']==identities and s['prepared_sha256']==EXPECTED and s['expected_file']==str((HERE/folder/name).relative_to(ROOT)),'Prewritten whole-file identifier sidecar')
            if folder=='results': require(s['oracle_sha256']==sha(HERE/'oracle.json.gz') and s['original_convergence_flag']=='0' and s['candidate_convergence_status'] is None,'Result oracle/flag sidecar')
    require(summary['path_eval_calls']==8 and summary['extra_segment_calls']==8232 and all(summary[k]==0 for k in ('trace_calls','field_calls','optimizer_calls','new_reference_integrations')),'Bounded original numerical calls')
    require((HERE/'logs/command_1.stdout').read_text().strip()=='path_eval_calls=8 extra_segment_calls=8232 trace_calls=0 field_calls=0 optimizer_calls=0 double_digits=53 long_double_digits=64','Recorded arithmetic precision/calls')
    totals,edges,gradients,pair_rows=[table(n) for n in ('totals.csv','edges.csv','gradients.csv','pairs.csv')]
    require([len(totals),len(edges),len(gradients),len(pair_rows)]==[8,8232,24672,4],'Complete numeric table counts')
    edge_map={}; gradient_map={}; action_map={}; cases=[]
    require(len(oracle['polygons'])==len(summary['result']['polygons'])==len(details['polygons'])==8,'Complete polygon comparisons')
    for polygon,row,saved,detail in zip(oracle['polygons'],totals,summary['result']['polygons'],details['polygons']):
        event,stage,n=polygon['event'],polygon['stage_integer'],polygon['node_count']; key=(event,stage)
        require([int(row[k]) for k in ('event','station','stage','nodes')]==[event,160,stage,n],'Native polygon order')
        identity=next(v for v in identities if v['event']==event)
        require(all(polygon[k]==identity[k] for k in ('event','station','native_context','catalog_uses')),'Per-polygon full identity')
        path_file=HERE/polygon['input_file']; tokens=path_file.read_text().split(); require(list(map(int,tokens[:4]))==[event,160,stage,n] and len(tokens)==4+3*n,'Complete fixed geometry input')
        require([Q(float(v)) for v in tokens[4:]]==[Q(v) for p in polygon['coordinates_exact_rational'] for v in p]
                and [float(v).hex() for v in tokens[4:]]==[v for p in polygon['coordinate_hex'] for v in p],'Exact saved geometry transport')
        sidecar=read(Path(str(path_file)+'.identifiers.json')); require(sidecar['file_sha256']==sha(path_file)==polygon['input_sha256'] and all(sidecar[k]==identity[k] for k in ('event','station','native_context','catalog_uses')),'Identified input bytes')
        er=[r for r in edges if (int(r['event']),int(r['stage']))==key]; gr=[r for r in gradients if (int(r['event']),int(r['stage']))==key]
        require([int(r['edge']) for r in er]==list(range(n-1)) and [(int(r['node']),int(r['axis'])) for r in gr]==[(i,k) for i in range(1,n-1) for k in range(3)] and all(int(r['station'])==160 for r in er+gr),'Every native edge/component index')
        actual=[number(r,'action',True) for r in er]; actual_g={(int(r['node']),int(r['axis'])):number(r,'component',True) for r in gr}; edge_map[key]=actual; gradient_map[key]=actual_g
        require(all(v>0 for v in actual),'Positive emitted edge actions')
        ee=[dict(edge=i,emitted_hex=er[i]['action_hex'],**error(v,polygon['action']['edges'][i]['bounds'])) for i,v in enumerate(actual)]
        ce=[]; derivative=polygon['derivatives']
        if derivative['status']=='reviewed_available_internal_components':
            require([r['node'] for r in derivative['component_bounds']]==list(range(1,n-1)),'Available derivative roster')
            for r in derivative['component_bounds']:
                for k,v in enumerate(r['components']):
                    if v is not None: ce.append(dict(node=r['node'],axis=k,**error(actual_g[r['node'],k],v)))
        else: require(derivative['status']=='unavailable' and derivative['component_bounds'] is None,'Unavailable derivative oracle preserved')
        values={k:number(row,k,k!='extended_sum') for k in ('action','ordinary_sum','extended_sum')}; action_map[key]=values['action']
        require(values['ordinary_sum']==accumulated(actual,53) and values['extended_sum']==accumulated(actual,64) and values['action']==nearest(values['extended_sum'],53),'Exact scalar accumulation/narrowing replay')
        times=[Decimal(row[k]) for k in ('path_eval_microseconds','edge_check_microseconds')]; require(all(t.is_finite() and t>=0 for t in times),'Finite nonnegative timing displays')
        report=dict(event=event,station=160,stage=polygon['stage'],node_count=n,action_comparisons={k:error(v,polygon['action']['full_bounds']) for k,v in values.items()},
            exact_sum_of_emitted_binary64_edges=sum(actual,Q(0)),extended_accumulation_error=values['extended_sum']-sum(actual,Q(0)),
            largest_edge_distance=max(v['distance_to_enclosure'] for v in ee),largest_edge_absolute_error_upper=max(v['absolute_error_upper'] for v in ee),
            derivative_oracle_status=derivative['status'],available_component_count=len(ce),derivative_error_norm_squared_bounds=(sum((v['distance_to_enclosure']**2 for v in ce),Q(0)),sum((v['absolute_error_upper']**2 for v in ce),Q(0))) if ce else None,
            largest_component_distance=max((v['distance_to_enclosure'] for v in ce),default=None),path_eval_microseconds=times[0].to_eng_string(),extra_edge_checks_and_output_microseconds=times[1].to_eng_string(),original_convergence_flag='0',candidate_convergence_status=None)
        require(encoded(report)==saved and encoded(dict(report,edges=ee,available_components=ce))==detail,'Every saved action/available-gradient error and norm summary')
        cases.append(dict(identity,stage=polygon['stage'],stage_integer=stage,node_count=n,available_components=len(ce),action_comparisons=report['action_comparisons'],derivative_error_norm_squared_bounds=report['derivative_error_norm_squared_bounds']))
    checked_pairs=[]
    require(len(oracle['pairs'])==len(summary['result']['pairs'])==len(details['pairs'])==4,'Four paired comparisons')
    for expected,row,saved in zip(oracle['pairs'],pair_rows,summary['result']['pairs']):
        event=expected['event']; stage=2 if expected['to_stage']=='second' else 3; alpha=Q(row['alpha'])
        require([int(row[k]) for k in ('event','station','base_stage','trial_stage')]==[event,160,1,stage] and alpha==Q(expected['alpha_exact']),'Native pair/alpha join')
        file=HERE/expected['direction_file']; require(sha(file)==expected['direction_sha256'],'Actual direction bytes')
        tokens=file.read_text().split(); n=len(gradient_map[event,1])//3+2; require(list(map(int,tokens[:3]))==[event,160,n] and len(tokens)==3+3*n,'Direction topology')
        q=[Q(float(v)) for v in tokens[3:]]; require(all(v==0 for v in q[:3]+q[-3:]),'Fixed endpoints')
        first=next(p for p in oracle['polygons'] if p['event']==event and p['stage']=='first')
        for r in first['derivatives']['component_bounds']:
            for k,v in enumerate(r['components']):
                if v is None: require(q[3*r['node']+k]==0,'Unavailable normal has exact zero direction')
        products=[gradient_map[event,1][i,k]*q[3*i+k] for i in range(1,n-1) for k in range(3)]
        changes=[a-b for a,b in zip(edge_map[event,stage],edge_map[event,1])]
        paired=number(row,'paired'); slope=number(row,'slope',True); wide_slope=number(row,'extended_slope'); rhs=number(row,'extended_armijo_rhs'); outer_change=number(row,'outer_change',True)
        require(paired==accumulated([nearest(v,64) for v in changes],64) and slope==accumulated([nearest(v,53) for v in products],53)
                and wide_slope==accumulated([nearest(v,64) for v in products],64),'Paired and gradient-direction scalar operation replay')
        coefficient=Q(float('1e-4')); require(rhs==nearest(nearest(coefficient*alpha,64)*slope,64) and outer_change==nearest(action_map[event,stage]-action_map[event,1],53),'Actual coefficient/RHS/rounded total subtraction')
        saved_rhs=Q(expected['Armijo_rhs_lower']); require(saved_rhs==coefficient*alpha*Q(expected['nominal_slope'][0]),'Reference bound uses same exact coefficient')
        decision=slope<0 and paired<=rhs; require(int(row['paired_armijo'])==int(decision),'Actual full/half Armijo decision')
        report=dict(event=event,station=160,from_stage='first',to_stage=expected['to_stage'],alpha=alpha,paired_comparison=error(paired,expected['paired_difference']),
            exact_sum_of_binary64_edge_differences=sum(changes,Q(0)),paired_accumulation_error=paired-sum(changes,Q(0)),outer_rounded_total_difference=outer_change,
            slope_comparison=error(slope,expected['nominal_slope']),extended_slope_comparison=error(wide_slope,expected['nominal_slope']),exact_sum_of_binary64_gradient_direction_products=sum(products,Q(0)),extended_slope_accumulation_error=wide_slope-sum(products,Q(0)),
            saved_armijo_rhs_lower=saved_rhs,cpp_armijo_rhs=rhs,paired_passes_saved_slope_bound=paired<=saved_rhs,paired_passes_cpp_slope=decision,oracle_armijo=expected['conservative_nominal_armijo'],oracle_status=expected['status'],agrees_with_oracle=decision==expected['conservative_nominal_armijo'])
        require(encoded(report)==saved,'Every saved pair arithmetic/decision field'); checked_pairs.append(report)
    require(encoded(checked_pairs)==details['pairs'],'Detailed pair table parity')
    for p,d in list(PINS.items()): pin(Path(p),d)
    review=dict(status='passed',reviewer='earthscope_discovery',prepared_sha256=EXPECTED,summary_sha256=sha(HERE/'summary.json'),execution_sha256=sha(HERE/'execution.json'),outer_reaping_sha256=sha(HERE/'outer_reaping.json'),
        checker_sha256=sha(Path(__file__)),source_review_sha256=sha(HERE/'review_saved_source.json'),checks=CHECKS,pinned_files=len(PINS),native_contexts=identities,cases=cases,pairs=checked_pairs,
        table_counts=dict(polygons=8,edges=8232,components=24672,pairs=4),new_evaluator_calls=0,new_compiler_calls=0,new_integrations=0,
        limitations=['Saved output and oracle readback only; no segment/path evaluator or reference reintegration.',
                    'Scalar nearest/ties-even arithmetic at recorded 53/64 significand bits reproduces the emitted accumulations; this is not a replay of the physical segment kernel.',
                    'Only existing face/first available internal derivative oracles are assessed; absent second/half derivatives remain unavailable.',
                    'Fixed polygon discrepancy and Armijo comparisons do not certify a stationary ray, source derivative, first arrival or production flag.'])
    with (HERE/'review.json').open('x') as f: json.dump(encoded(review),f,indent=2,sort_keys=True,allow_nan=False); f.write('\n')
    print(json.dumps(dict(status='passed',review_sha256=sha(HERE/'review.json'),checks=CHECKS,pinned_files=len(PINS))))

if __name__=='__main__': main()
