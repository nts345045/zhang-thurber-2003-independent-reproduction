#!/usr/bin/env python3
"""Nine invented edges; exact prepartition, explicit-cell 8GL, bounded references.

This compares integrated continuous first variations, not exact derivatives of
the finite quadrature objective. No production kernel or ray optimizer changes.
"""
from bisect import bisect_right
from datetime import datetime
from fractions import Fraction as Q
import hashlib
from itertools import product
import json
import math
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
PRIOR=HERE.parent/'internal_face_contact_controls_001'/'results'/'summary.json'
NODES=tuple(map(Q,(0.1834346424956498,0.5255324099163290,0.7966664774136267,0.9602898564975363)))
WEIGHTS=tuple(map(Q,(0.3626837833783620,0.3137066458778873,0.2223810344533745,0.1012285362903763)))
BUDGET=dict(cases=9,helpers=9,old_segment_calls=9,strict_edge_calls=9,
            strict_pieces=17,strict_samples=136,affine_references=7,
            homogeneous_references=1,trilinear_references=1)


def require(ok,message):
    if not ok: raise ValueError(message)


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def encoded(value):
    if isinstance(value,Q): return str(value)
    if isinstance(value,dict): return {str(k):encoded(v) for k,v in value.items()}
    if isinstance(value,(tuple,list)): return [encoded(v) for v in value]
    return value


def write(path,value):
    temporary=path.with_name(path.name+'.writing')
    with temporary.open('w') as stream:
        json.dump(encoded(value),stream,indent=2,sort_keys=True,allow_nan=False);stream.write('\n')
    temporary.replace(path)


def handoff(value,positive=False):
    result=float(value)
    require(math.isfinite(result) and (not positive or result>0),'Nonfinite or nonpositive represented positive quantity')
    return dict(exact=Q(value),binary64_hex=result.hex(),represented_exact=Q(result))


def roster():
    axes=((-1,0,1),(-1,4),(-1,1));zero=Q(0);delta=Q(1,64)
    cases=[]
    for name,left,right,old_omits in (
            ('below_displacement_cutoff',Q(1,2**42),Q(1,2**42),True),
            ('above_displacement_cutoff',Q(1,2**40),Q(1,2**40),False),
            ('below_endpoint_cutoff',Q(1,2**40),delta,True),
            ('above_endpoint_cutoff',Q(1,2**38),delta,False)):
        cases.append(dict(name=name,axes=axes,a=(-left,zero,zero),b=(right,Q(1),zero),
                          kind='ridge',center=zero,expected_old_omission=old_omits))
    # Adjacent IEEE binary64 values around 1; Python 3.6 has no math.nextafter.
    below=Q(float.fromhex('0x1.fffffffffffffp-1'));above=Q(float.fromhex('0x1.0000000000001p+0'))
    translated=dict(name='translated_nextafter',axes=((0,1,2),axes[1],axes[2]),
                    a=(below,zero,zero),b=(above,Q(1),zero),kind='ridge',center=Q(1),expected_old_omission=True)
    cases.append(translated)
    cases.append(dict(name='constant_velocity',axes=axes,a=(-Q(1,4),zero,zero),b=(Q(1,4),Q(1),zero),
                      kind='constant',center=zero,expected_old_omission=False))
    cases.append(dict(translated,name='translated_reversal',a=translated['b'],b=translated['a']))
    cases.append(dict(name='aligned_face',axes=axes,a=(zero,zero,zero),b=(zero,Q(1),zero),
                      kind='ridge',center=zero,expected_old_omission=False))
    cases.append(dict(name='genuine_trilinear',axes=axes,a=(-Q(1,4),zero,-Q(1,4)),b=(Q(1,4),Q(1),Q(1,4)),
                      kind='trilinear',center=None,expected_old_omission=False))
    return cases


def prepartition(case):
    axes=tuple(tuple(map(Q,axis)) for axis in case['axes']);a=case['a'];b=case['b']
    delta=tuple(y-x for x,y in zip(a,b));require(any(delta),'Zero edge')
    require(all(axes[k][0]<=p[k]<=axes[k][-1] for p in (a,b) for k in range(3)),'Outside physical box')
    inputs=[x for axis in axes for x in axis]+list(a)+list(b)
    require(all(Q(float(x))==x for x in inputs),'Finite roster requires binary64-exact original coordinates')
    represented_delta=tuple(Q(float(y)-float(x)) for x,y in zip(a,b))
    require(represented_delta==delta,'Finite-roster exact subtraction invariant; no mixed endpoint line')
    cuts={Q(0):[],Q(1):[]};aligned=[]
    for k,axis in enumerate(axes):
        if delta[k]:
            for index,plane in enumerate(axis[1:-1],1):
                if min(a[k],b[k])<plane<max(a[k],b[k]):
                    u=(plane-a[k])/delta[k];require(0<u<1,'Strict open crossing')
                    cuts.setdefault(u,[]).append(dict(axis=k,plane_index=index,plane=plane))
        elif a[k] in axis[1:-1]: aligned.append(k)
    require(len(aligned)<=1,'Multiple aligned faces outside this bounded experiment')
    order=sorted(cuts);pieces=[]
    for left,right in zip(order,order[1:]):
        width=right-left;require(width>0,'Nonpositive exact piece')
        middle=tuple(a[k]+(left+right)*delta[k]/2 for k in range(3))
        cell=tuple(min(len(axis)-2,max(0,bisect_right(axis,middle[k])-1)) for k,axis in enumerate(axes))
        piece=dict(left=left,right=right,cell=cell,width=handoff(width,positive=True),samples=[])
        for j in range(4):
            for sign in (-1,1):
                u=left+width*(1+sign*NODES[j])/2;point=tuple(a[k]+u*delta[k] for k in range(3))
                basis=[]
                for k,axis in enumerate(axes):
                    f=(point[k]-axis[cell[k]])/(axis[cell[k]+1]-axis[cell[k]])
                    require(0<=f<=1,'Exact sample outside declared closed cell')
                    basis.append([handoff(1-f),handoff(f)])
                piece['samples'].append(dict(node=j,sign=sign,u_exact=u,point_exact=point,
                    point_binary64_hex=[float(x).hex() for x in point],basis=basis,
                    endpoint_shapes=[handoff(1-u),handoff(u)],weight=handoff(width*WEIGHTS[j]/2,positive=True)))
        pieces.append(piece)
    return dict(axes=axes,a=a,b=b,delta_exact=delta,delta_binary64_exact=represented_delta,
                cuts=[dict(u=u,events=cuts[u]) for u in order],aligned_axes=aligned,pieces=pieces)


def nodal_values(case):
    values={}
    for k in product(range(3),range(2),range(2)):
        x,y,z=(Q(case['axes'][axis][k[axis]]) for axis in range(3))
        value=(2+x)*(3+y)*(4+z) if case['kind']=='trilinear' else Q(6) if case['kind']=='constant' else 6-abs(x-case['center'])
        require(value>0 and Q(float(value))==value,'Positive binary64-exact manufactured model')
        values[k]=value
    return values


def input_text(partition,velocities):
    tokens=['3','2','2',str(len(partition['pieces']))]
    tokens.extend(float(x).hex() for axis in partition['axes'] for x in axis)
    tokens.extend(float(velocities[i,j,k]).hex() for k in range(2) for j in range(2) for i in range(3))
    tokens.extend(float(x).hex() for p in (partition['a'],partition['b']) for x in p)
    tokens.extend(str(int(k in partition['aligned_axes'])) for k in range(3))
    for piece in partition['pieces']:
        tokens.extend(map(str,piece['cell']));tokens.append(piece['width']['binary64_hex'])
        for sample in piece['samples']:
            tokens.extend(v['binary64_hex'] for v in sample['endpoint_shapes']);tokens.append(sample['weight']['binary64_hex'])
            tokens.extend(v['binary64_hex'] for axis in sample['basis'] for v in axis)
    return ' '.join(tokens)+'\n'


def values(record,name):
    decimals,hexes=record[name],record[name+'_hex'];require(len(decimals)==len(hexes),'Decimal/hex dimensions')
    result=[]
    for decimal,hexa in zip(decimals,hexes):
        if decimal is None or hexa is None:
            require(decimal is None and hexa is None,'Unavailable decimal/hex mismatch');result.append(None);continue
        x=float.fromhex(hexa);require(math.isfinite(x) and float(decimal).hex()==x.hex(),'Decimal/hex mismatch')
        result.append(Q(x))
    return result


def error_bounds(actual,reference):
    components=[];squared=(Q(0),Q(0));widths=[]
    for index,(value,bounds) in enumerate(zip(actual,reference)):
        if bounds is None:
            components.append(dict(component=index,ordinary_unavailable=True,observed_branch_value=value));continue
        require(value is not None,'Missing available gradient')
        lo,hi=value-bounds[1],value-bounds[0];widths.append(bounds[1]-bounds[0])
        lower=Q(0) if lo<=0<=hi else min(lo*lo,hi*hi);upper=max(lo*lo,hi*hi)
        squared=(squared[0]+lower,squared[1]+upper);components.append(dict(component=index,error=(lo,hi)))
    return dict(components=components,squared_norm=squared,squared_norm_units='s^2/km^2',
                reference_component_widths=widths,error_scope='Combined quadrature and floating arithmetic error for the continuous variation.')


def main():
    require(len(sys.argv)==3,'Use: check_controls.py BINARY EXPECTED_BINARY_SHA256')
    binary=Path(sys.argv[1]).resolve();require(sha(binary)==sys.argv[2],'Binary hash mismatch')
    output=HERE/'results';output.mkdir(exist_ok=True)
    require(not (output/'summary.json').exists() and not (output/'calls').exists(),'Preserve prior execution')
    (output/'calls').mkdir();sys.path.insert(0,str(HERE/'source'));sys.path.insert(0,str(HERE))
    import affine_log_reference as affine
    from diagnostics import trilinear_action_bounds as t
    settings=t.options(16,4,192);cases=[];checks=[];commands=[];unresolved=[]
    prior=json.loads(PRIOR.read_text());require(prior['status']=='passed','Prior contact controls not passed')
    prior_cuts={record['name']:record for family in prior['families'] if family['family']=='near_cut_inventory' for record in family['cases']}
    counts={key:0 for key in BUDGET}
    def checkpoint(): write(output/'progress.json',dict(cases=cases,checks=checks,commands=commands,counts=counts))
    def check(name,condition):
        checks.append(dict(name=name,passed=bool(condition)));checkpoint();require(condition,name)
    for case in roster():
        item=dict(case=case,status='preparing');cases.append(item);checkpoint()
        try:
            p=prepartition(case);velocities=nodal_values(case);item.update(partition=p,nodal_velocities=velocities)
            require(counts['strict_pieces']+len(p['pieces'])<=BUDGET['strict_pieces'],'Strict piece budget')
            index=counts['helpers'];require(index<BUDGET['helpers'] and not unresolved,'Helper budget or unresolved cleanup')
            stem=output/'calls'/('{:02d}_{}'.format(index,case['name']));input_path=stem.with_suffix('.input')
            with input_path.open('x') as stream: stream.write(input_text(p,velocities))
            command=dict(index=index,command=[str(binary),str(input_path)],input_sha256=sha(input_path),
                         pid=None,return_code=None,child_reaped=False,started_utc=datetime.utcnow().isoformat()+'Z')
            commands.append(command);counts['helpers']+=1;checkpoint()
            with stem.with_suffix('.stdout.json').open('x') as out,stem.with_suffix('.stderr.log').open('x') as err:
                child=subprocess.Popen(command['command'],cwd=str(ROOT),stdout=out,stderr=err)
                try:
                    command['pid']=child.pid;checkpoint();command['return_code']=child.wait();command['child_reaped']=True
                finally:
                    if not command['child_reaped']:
                        try:
                            if child.poll() is None:
                                try: child.terminate()
                                except ProcessLookupError: pass
                            try: command['return_code']=child.wait(timeout=10)
                            except subprocess.TimeoutExpired:
                                try: child.kill()
                                except ProcessLookupError: pass
                                command['return_code']=child.wait(timeout=10)
                            command['child_reaped']=True;command['exceptional_cleanup']='terminated_if_live_and_reaped'
                        except BaseException as exc:
                            unresolved.append(child.pid);command['cleanup_error']=dict(type=type(exc).__name__,message=str(exc));raise
            command.update(finished_utc=datetime.utcnow().isoformat()+'Z',stdout_sha256=sha(stem.with_suffix('.stdout.json')),
                           stderr_sha256=sha(stem.with_suffix('.stderr.log')));checkpoint()
            require(command['return_code']==0,'Observer failed; preserve output')
            observed=json.loads(stem.with_suffix('.stdout.json').read_text());item['observed']=observed;checkpoint()
            check(case['name']+'_scope',observed['invented_only'] and observed['trace_calls']==observed['field_calls']==0)
            check(case['name']+'_exact_endpoint_subtraction',tuple(values(observed,'delta'))==p['delta_exact'])
            check(case['name']+'_piece_inventory',observed['strict_pieces']==len(p['pieces']) and observed['strict_samples']==8*len(p['pieces']))
            for key in ('old_segment_calls','strict_edge_calls','strict_pieces','strict_samples'): counts[key]+=observed[key]
            oldcuts=values(observed,'reconstructed_old_cuts')
            check(case['name']+'_old_cut_inventory',(len(oldcuts)<len(p['cuts']))==case['expected_old_omission'])
            if case['name'] in prior_cuts:
                original=prior_cuts[case['name']]['assessment'];saved=original['observed']['record']
                item['prior_old_output_parity']=dict(
                    exact_geometry=[tuple(map(Q,row)) for row in original['path']]==[case['a'],case['b']],
                    action=values(observed,'old_action')==values(saved,'action'),
                    endpoint_gradient=values(observed,'old_endpoint_gradient')==values(saved,'endpoint_gradient'),
                    cuts=oldcuts==values(saved,'reconstructed_core_cuts'))
                check(case['name']+'_unchanged_prior_old_output',all(item['prior_old_output_parity'].values()))
            if case['kind']=='ridge':
                counts['affine_references']+=1;center=case['center']
                shift=lambda point:(point[0]-center,point[1],point[2])
                shifted_axes=(tuple(Q(x)-center for x in case['axes'][0]),case['axes'][1],case['axes'][2])
                reference=affine.edge(shift(case['a']),shift(case['b']),-1,shifted_axes,terms=16,bits=192)
                reference['exact_translation_center']=center
            elif case['kind']=='constant':
                counts['homogeneous_references']+=1;length=affine.length_bounds(p['delta_exact'],192)
                inverse=(1/length[1],1/length[0]);first=[affine.scale(inverse,-d/6) for d in p['delta_exact']]
                last=[affine.scale(inverse,d/6) for d in p['delta_exact']]
                reference=dict(action=affine.scale(length,Q(1,6)),components=[first,last],length=length,
                               interpretation='Independent homogeneous radical action and endpoint gradients.')
            else:
                counts['trilinear_references']+=1
                reference=t.edge_tangent_components(t.model(case['axes'],velocities),case['a'],case['b'],settings)
                reference['length']=affine.length_bounds(p['delta_exact'],192)
                reference['length_basis']='Independent integer-root enclosure; no additional action or derivative integral.'
            item['reference']=reference;checkpoint()
            expected=[value for side in reference['components'] for value in side]
            strict=values(observed,'strict_continuous_endpoint_gradient');old=values(observed,'old_endpoint_gradient')
            check(case['name']+'_ordinary_availability',all((value is None)==(k%3 in p['aligned_axes']) for k,value in enumerate(strict))
                  and all((a is None)==(b is None) for a,b in zip(strict,expected)))
            item['old_gradient_error']=error_bounds(old,expected);item['strict_gradient_error']=error_bounds(strict,expected)
            item['strict_gradient_error_resolved_smaller_than_old']=item['strict_gradient_error']['squared_norm'][1]<item['old_gradient_error']['squared_norm'][0]
            item['action_errors']={label:(values(observed,label+'_action')[0]-reference['action'][1],
                                         values(observed,label+'_action')[0]-reference['action'][0]) for label in ('old','strict')}
            item['reference_action_width']=reference['action'][1]-reference['action'][0]
            item['binary64_length_error']=(values(observed,'length')[0]-reference['length'][1],values(observed,'length')[0]-reference['length'][0])
            sampled=values(observed,'strict_sample_velocity_and_gradient')
            require(len(sampled)==4*observed['strict_samples'],'Sample output inventory')
            if case['kind']=='trilinear':
                check('genuine_3d_nonzero_velocity_derivatives',all(sampled[i+k]!=0 for i in range(0,len(sampled),4) for k in (1,2,3)))
            else:
                axes=(1,2,3) if case['kind']=='constant' else (2,3)
                check(case['name']+'_constant_axes_exact_zero',all(sampled[i+k]==0 for i in range(0,len(sampled),4) for k in axes))
            counts['cases']+=1;item['status']='completed';checkpoint()
        except Exception as exc:
            item.update(status='failed_preserved',error=dict(type=type(exc).__name__,message=str(exc)));checkpoint()
        if unresolved: break
    checks.append(dict(name='declared_complete_call_inventory',passed=counts==BUDGET));checkpoint()
    sources=[Path(__file__).resolve(),HERE/'observe.cpp',HERE/'affine_log_reference.py']+sorted((HERE/'source').rglob('*.py'))+sorted((HERE/'source').rglob('*.hpp'))
    status='passed' if not unresolved and all(item['status']=='completed' for item in cases) and all(c['passed'] for c in checks) else 'failed_preserved'
    payload=dict(status=status,invented_only=True,cases=cases,checks=checks,commands=commands,counts=counts,budgets=BUDGET,
                 source_sha256={str(p.relative_to(ROOT)):sha(p) for p in sources},binary_sha256=sha(binary),
                 input_sha256={str(PRIOR.relative_to(ROOT)):sha(PRIOR)},
                 prepared_sha256=sha(HERE/'prepared.json'),unresolved_children=unresolved,
                 reference_settings=dict(affine_terms=16,affine_length_bits=192,trilinear=settings),
                 accuracy_scope='All error intervals retained; structural controls do not assert an accuracy threshold or rounding-only error.',
                 arithmetic_scope='Exact endpoint line and fixed cell; separately rounded local/global shapes and scaled weights; binary64 norm and accumulation.',
                 derivative_scope='Quadrature of continuous first variations; not the exact derivative of the finite quadrature action.',
                 generic_subtraction_supported=False,production_cut_patch=False,native_calls=0,trace_calls=0,field_calls=0,
                 candidate_convergence_status=None)
    payload['output_sha256']={str(p.relative_to(output)):sha(p) for p in sorted(output.rglob('*')) if p.is_file()}
    with (output/'summary.json').open('x') as stream:
        json.dump(encoded(payload),stream,indent=2,sort_keys=True,allow_nan=False);stream.write('\n')
    print(json.dumps(dict(status=status,checks=len(checks),summary_sha256=sha(output/'summary.json'))))
    return 0 if status=='passed' else 1


if __name__=='__main__': sys.exit(main())
