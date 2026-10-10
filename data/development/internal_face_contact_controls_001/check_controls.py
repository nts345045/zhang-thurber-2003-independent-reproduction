#!/usr/bin/env python3
"""Finite invented contact experiment. Source review precedes any execution."""
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
AXES=((-1,0,1),(-1,4),(-1,1))
DELTA=Q(1,64)
ZERO=(Q(0),Q(0),Q(0))
BUDGET=dict(fast_searches=2,slow_searches=1,trials_per_search=24,
            helper_calls=79,combined_edge_calls=229,directional_edge_calls=231,
            near_cut_edges=4,affine_edge_references=229)


def encoded(value):
    if isinstance(value,Q): return str(value)
    if isinstance(value,dict): return {str(k):encoded(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)): return [encoded(v) for v in value]
    return value


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path,value):
    temporary=path.with_name(path.name+'.writing')
    with temporary.open('w') as stream:
        json.dump(encoded(value),stream,indent=2,sort_keys=True,allow_nan=False);stream.write('\n')
    temporary.replace(path)


def require(ok,message):
    if not ok: raise ValueError(message)


def main():
    require(len(sys.argv)==3,'Use: check_controls.py BINARY EXPECTED_BINARY_SHA256')
    binary=Path(sys.argv[1]).resolve();require(sha(binary)==sys.argv[2],'Binary hash mismatch')
    output=HERE/'results';output.mkdir(exist_ok=True)
    require(not (output/'summary.json').exists() and not (output/'calls').exists(),'Preserve existing execution')
    (output/'calls').mkdir()
    sys.path.insert(0,str(HERE/'source'));sys.path.insert(0,str(HERE))
    from diagnostics import trilinear_action_bounds as t
    import affine_log_reference as affine
    settings=t.options(8,1,128);coefficient=Q(float('1e-4'))
    commands=[];families=[];checks=[];unresolved_children=[];counts=dict(helper_calls=0,combined_edge_calls=0,
        directional_edge_calls=0,affine_edge_references=0,fast_searches=0,slow_searches=0)
    point=lambda x:(Q(x),Q(x))
    def checkpoint(): write(output/'progress.json',dict(families=families,checks=checks,commands=commands,counts=counts))
    def check(name,condition):
        checks.append(dict(name=name,passed=bool(condition)));checkpoint()
        require(condition,name)
    def model(sigma):
        return t.model(AXES,{k:6+sigma*abs(AXES[0][k[0]]) for k in product(range(3),range(2),range(2))})
    def values(record,key):
        raw,hexa=record[key],record[key+'_hex'];require(len(raw)==len(hexa),'Decimal/hex dimensions')
        result=[]
        for a,b in zip(raw,hexa):
            x,y=float(a),float.fromhex(b)
            require(math.isfinite(x) and x.hex()==y.hex(),'Decimal/hex binary64 disagreement')
            result.append(Q(y))
        return result
    def observe(mode,path,sigma,fixed=None):
        require(not unresolved_children,'Unresolved helper cleanup; no further launches')
        require(counts['helper_calls']<BUDGET['helper_calls'],'Helper call budget')
        index=counts['helper_calls'];counts['helper_calls']+=1
        stem=output/'calls'/('{:03d}_{}'.format(index,mode));input_path=stem.with_suffix('.input')
        tokens=['3','2','2',str(len(path))]
        tokens.extend(float(x).hex() for axis in AXES for x in axis)
        tokens.extend(float(6+sigma*abs(AXES[0][i])).hex() for k in range(2) for j in range(2) for i in range(3))
        tokens.extend(float(x).hex() for p in path for x in p)
        if fixed is not None: tokens.extend(str(int(x)) for x in fixed)
        with input_path.open('x') as stream: stream.write(' '.join(tokens)+'\n')
        item=dict(index=index,mode=mode,invented_only=True,command=[str(binary),mode,str(input_path)],
                  input_sha256=sha(input_path),started_utc=datetime.utcnow().isoformat()+'Z',
                  return_code=None,child_reaped=False,pid=None)
        commands.append(item);checkpoint()
        # Inherit the owned controller's process group. No helper creates children.
        with stem.with_suffix('.stdout.json').open('x') as out,stem.with_suffix('.stderr.log').open('x') as err:
            child=subprocess.Popen(item['command'],cwd=str(ROOT),stdout=out,stderr=err)
            try:
                item['pid']=child.pid;checkpoint();item['return_code']=child.wait();item['child_reaped']=True
            finally:
                if not item['child_reaped']:
                    try:
                        if child.poll() is None:
                            try: child.terminate()
                            except ProcessLookupError: pass
                        try: item['return_code']=child.wait(timeout=10)
                        except subprocess.TimeoutExpired:
                            try: child.kill()
                            except ProcessLookupError: pass
                            item['return_code']=child.wait(timeout=10)
                        item['child_reaped']=True;item['exceptional_cleanup']='terminated_if_live_and_reaped'
                    except BaseException as exc:
                        unresolved_children.append(child.pid);item['exceptional_cleanup']='unresolved'
                        item['cleanup_error']=dict(type=type(exc).__name__,message=str(exc));raise
        item['finished_utc']=datetime.utcnow().isoformat()+'Z'
        item['stdout_sha256']=sha(stem.with_suffix('.stdout.json'));item['stderr_sha256']=sha(stem.with_suffix('.stderr.log'));checkpoint()
        require(item['return_code']==0,'Observer failed; output preserved')
        raw=json.loads(stem.with_suffix('.stdout.json').read_text())
        require(raw['invented_only'] is True and raw['trace_calls']==raw['field_calls']==0,'Observer scope')
        require(values(raw,'path')==[x for p in path for x in p],'Observer input round trip')
        if mode=='solve': values(raw['metric'],'direction')
        return dict(command=index,record=raw)
    def square(bounds):
        lo,hi=bounds;return (Q(0) if lo<=0<=hi else min(lo*lo,hi*hi),max(lo*lo,hi*hi))
    def error_vector(actual,bounds):
        records=[];norm=(Q(0),Q(0))
        for i,(x,b) in enumerate(zip(actual,bounds)):
            if b is None: records.append(dict(component=i,unavailable=True,observed=x));continue
            error=t.sub(point(x),b);norm=t.add(norm,square(error));records.append(dict(component=i,error=error))
        return dict(components=records,squared_norm=norm,units='s^2/km^2')
    def assessment(path,sigma,observed):
        g=model(sigma);records=[];action=point(0);components=[[point(0) for axis in range(3)] for p in path];blocked=set()
        for edge,(a,b) in enumerate(zip(path,path[1:])):
            counts['combined_edge_calls']+=1;require(counts['combined_edge_calls']<=BUDGET['combined_edge_calls'],'Combined-edge budget')
            r=t.edge_tangent_components(g,a,b,settings);records.append(dict(r,edge=edge));action=t.add(action,r['action'])
            for side in (0,1):
                for axis,value in enumerate(r['components'][side]):
                    if value is None: blocked.add((edge+side,axis))
                    else: components[edge+side][axis]=t.add(components[edge+side][axis],value)
        for node,axis in blocked: components[node][axis]=None
        counts['affine_edge_references']+=len(path)-1
        require(counts['affine_edge_references']<=BUDGET['affine_edge_references'],'Affine reference budget')
        oracle=affine.edge(path[0],path[1],sigma,AXES,terms=16,bits=192) if len(path)==2 else affine.path(path,sigma,AXES,terms=16,bits=192)
        exact_components=oracle['components'] if len(path)==2 else oracle['internal_components']
        expected=[x for row in exact_components for x in row]
        emitted=values(observed['record'],'endpoint_gradient' if len(path)==2 else 'gradient')
        compared=components if len(path)==2 else components[1:-1]
        require(len(expected)==len(emitted),'Independent derivative dimensions')
        agreement=all(a is None and b is None or a is not None and b is not None and max(a[0],b[0])<=min(a[1],b[1])
                      for a,b in zip([x for row in compared for x in row],expected))
        available_norm=point(0)
        for row in components[1:-1]:
            for value in row:
                if value is not None: available_norm=t.add(available_norm,square(value))
        result=dict(path=path,observed=observed,action=action,edge_records=records,available_components=components[1:-1],
                    blocked_slots=sorted((i,k) for i,k in blocked if 0<i<len(path)-1),
                    available_squared_norm=available_norm,affine_reference=oracle,
                    ordinary_gradient_error=error_vector(emitted,expected),
                    action_error=t.sub(point(values(observed['record'],'action')[0]),oracle['action']),
                    interval_oracle_overlap=agreement and max(action[0],oracle['action'][0])<=min(action[1],oracle['action'][1]),
                    full_stopping='Not claimed; blocked normals are not omitted from any full stationarity assertion.')
        return result
    def directional(path,direction,sigma):
        counts['directional_edge_calls']+=len(path)-1
        require(counts['directional_edge_calls']<=BUDGET['directional_edge_calls'],'Directional-edge budget')
        return t.path_directional(model(sigma),path,direction,settings)
    def geometry(path,trial,fixed):
        require(trial[0]==path[0] and trial[-1]==path[-1],'Fixed endpoints changed')
        require(all(t.contains(model(-1),p) for p in trial),'Trial outside physical box')
        require(all(a!=b for a,b in zip(trial,trial[1:])),'Zero trial edge')
        require(all(not bit or trial[i+1][k]==path[i+1][k] for i in range(2) for k,bit in enumerate(fixed[3*i:3*i+3])),'Search-fixed coordinate moved')
    def search(item,start,path,direction,sigma,alpha,fixed,expected_hits,core_slope,nominal=None):
        nominal=directional(path,direction,sigma) if nominal is None else nominal
        item.update(nominal_directional=nominal,trials=[]);checkpoint()
        check(item['name']+'_true_nominal_descent',nominal['derivative'][1]<0)
        for halving in range(24):
            step=alpha/Q(2**halving)
            exact=[tuple(p[k]+step*d[k] for k in range(3)) for p,d in zip(path,direction)]
            trial=[tuple(Q(float(x)) for x in p) for p in exact]
            entry=dict(halving=halving,step=step,event_fraction=alpha,unrounded=exact,trial=trial,
                       trial_hex=[[float(x).hex() for x in p] for p in trial],status='constructed')
            item['trials'].append(entry);checkpoint();geometry(path,trial,fixed)
            if trial==path: entry['status']='no_op';checkpoint();return None
            hits=[i for i in (1,2) if path[i][0]!=0 and trial[i][0]==0]
            if expected_hits is not None:
                require(all(p[0]>=0 for p in trial),'Unintended crossing beyond fast contact')
                require(hits==(expected_hits if halving==0 else []),'Unexpected rounded contact inventory')
            displacement=[tuple(q[k]-p[k] for k in range(3)) for p,q in zip(path,trial)]
            actual=directional(path,displacement,sigma);entry['actual_displacement_directional']=actual
            observed=observe('path',trial,sigma);after=assessment(trial,sigma,observed);entry['assessment']=after;checkpoint()
            check(item['name']+'_trial_{}_oracle'.format(halving),after['interval_oracle_overlap'])
            difference=point(0);changed=[]
            for edge,(a,b,c,d) in enumerate(zip(path,path[1:],trial,trial[1:])):
                if a==c and b==d: continue
                delta=t.sub(after['edge_records'][edge]['action'],start['edge_records'][edge]['action'])
                difference=t.add(difference,delta);changed.append(dict(edge=edge,difference=delta))
            rhs=coefficient*step*nominal['derivative'][0]
            before_core=float(start['observed']['record']['action'][0]);after_core=float(observed['record']['action'][0])
            core_rhs=before_core+float(coefficient)*float(step)*core_slope
            accepted=actual['derivative'][1]<0 and difference[1]<=rhs and after_core<=core_rhs
            entry.update(difference=difference,changed_edges=changed,conservative_armijo_rhs=rhs,
                         recorded_core_rhs=core_rhs,recorded_core_acceptance=after_core<=core_rhs,
                         accepted=accepted,status='accepted' if accepted else 'rejected',hits=hits)
            checkpoint()
            if accepted: return dict(path=trial,assessment=after,halving=halving,hits=hits)
        item['terminal_reason']='trial_budget';checkpoint();return None
    def fast(item):
        path=[(DELTA,Q(0),Q(0)),(DELTA/2,Q(1),Q(0)),(DELTA,Q(2),Q(0)),(DELTA,Q(3),Q(0))]
        item.update(initial=path,searches=[],analytic_derivative_lower=Q(1,36)-Q(2,383),temporary_contact=None,
                    candidate_convergence_status=None,interpretation='Two normal-coordinate search proposals, not constraints on Fermat paths.')
        retained=None
        for stage in range(2):
            counts['fast_searches']+=1;fixed=[i%3!=0 or retained is not None and i//3+1==retained for i in range(6)]
            observed=observe('solve',path,-1,fixed);start=assessment(path,-1,observed)
            flat=values(observed['record']['metric'],'direction');direction=[ZERO,tuple(flat[:3]),tuple(flat[3:]),ZERO]
            proposal=dict(name='fast_{}'.format(stage),start=start,search_fixed=fixed,direction=direction);item['searches'].append(proposal);checkpoint()
            check(proposal['name']+'_oracle',start['interval_oracle_overlap'])
            moving=[i for i in (1,2) if not fixed[3*(i-1)]]
            check(proposal['name']+'_negative_free_normals',all(direction[i][0]<0 for i in moving))
            events=sorted(((-path[i][0]/direction[i][0]),i) for i in moving)
            alpha=events[0][0];hits=[i for tau,i in events if tau==alpha]
            proposal.update(exact_events=events,first_event=alpha,expected_hits=hits);checkpoint()
            check(proposal['name']+'_event_within_unit_step',0<alpha<=1)
            check(proposal['name']+'_declared_contact_order',hits==[stage+1])
            result=search(proposal,start,path,direction,-1,alpha,fixed,hits,float(observed['record']['metric']['slope_binary64']))
            if result is None or result['halving']!=0:
                item['outcome']='contact_not_reached_within_declared_search';checkpoint()
                check(proposal['name']+'_full_event_accepted',False)
            path=result['path'];item['current']=result
            if stage==0:
                retained=hits[0];item['temporary_contact']=retained
                release=[ZERO,(-Q(1),Q(0),Q(0)),ZERO,ZERO]
                item['isolated_release_directional']=directional(path,release,-1);checkpoint()
                check('isolated_contact_is_not_aligned_or_stationary',not result['assessment']['blocked_slots']
                      and result['assessment']['available_components'][0][0][0]>0 and item['isolated_release_directional']['derivative'][1]<0)
        item['outcome']='two_exact_contacts_formed';item['temporary_contact']=None
        check('positive_length_face_edge_formed',path[1][0]==path[2][0]==0 and path[1]!=path[2]
              and item['current']['assessment']['blocked_slots']==[(1,0),(2,0)])
    def slow(item):
        path=[(Q(0),Q(i),Q(0)) for i in range(4)]
        observed=observe('path',path,1);start=assessment(path,1,observed)
        plus=[ZERO,(Q(1),Q(0),Q(0)),(Q(1),Q(0),Q(0)),ZERO]
        minus=[tuple(-x for x in p) for p in plus]
        forward,backward=directional(path,plus,1),directional(path,minus,1)
        item.update(start=start,plus=forward,minus=backward,closed_form_true_directional=-Q(1,18),
                    branch_hull_zero_is_not_a_support=True,candidate_convergence_status=None);checkpoint()
        check('slow_oracle',start['interval_oracle_overlap'])
        check('affine_equal_speed_limit',all(piece['J']==point(Q(1,6)) and piece['U']==piece['V']==point(Q(1,72))
              for edge in start['affine_reference']['edge_records'] for piece in edge['pieces']))
        check('slow_true_release_both_signs',all(r['derivative'][0]<=-Q(1,18)<=r['derivative'][1]<0 for r in (forward,backward)))
        check('slow_tangent_zero_does_not_stop',all(value is None or value==point(0)
              for row in start['affine_reference']['internal_components'] for value in row))
        check('main_tangent_bounds_contain_exact_zero',all(value is None or value[0]<=0<=value[1]
              for row in start['available_components'] for value in row) and start['available_squared_norm'][0]==0)
        counts['slow_searches']+=1;proposal=dict(name='slow_release');item['search']=proposal
        # Fixed ordering selects +x. It is not selected by a branch-gradient hull.
        item['result']=search(proposal,start,path,plus,1,DELTA,[False,True,True]*2,None,float(-Q(1,18)),nominal=forward)
        check('slow_release_accepted',item['result'] is not None and all(item['result']['path'][i][0]>0 for i in (1,2)))
    def cuts(item):
        roster=[('below_displacement_cutoff',Q(1,2**42),Q(1,2**42),True),
                ('above_displacement_cutoff',Q(1,2**40),Q(1,2**40),False),
                ('below_endpoint_cutoff',Q(1,2**40),DELTA,True),
                ('above_endpoint_cutoff',Q(1,2**38),DELTA,False)]
        item['cases']=[]
        for name,left,right,omitted in roster:
            path=[(-left,Q(0),Q(0)),(right,Q(1),Q(0))]
            observed=observe('edge',path,-1);r=assessment(path,-1,observed)
            core_cuts=values(observed['record'],'reconstructed_core_cuts');exact_cut=left/(left+right)
            record=dict(name=name,assessment=r,exact_cut=exact_cut,reconstructed_core_cuts=core_cuts,
                        omitted_internal_cut=len(core_cuts)==2,expected_omission=omitted,
                        interpretation='All observed old-kernel errors are retained; no strict-cut replacement is used.')
            item['cases'].append(record);checkpoint()
            check(name+'_oracle',r['interval_oracle_overlap'])
            check(name+'_cut_inventory',0<exact_cut<1 and (len(core_cuts)==2)==omitted)
    for name,function in (('fast_ridge_contact',fast),('slow_face_release',slow),('near_cut_inventory',cuts)):
        item=dict(family=name,status='running');families.append(item);checkpoint()
        try: function(item);item['status']='completed'
        except Exception as exc: item.update(status='failed_preserved',error=dict(type=type(exc).__name__,message=str(exc)))
        checkpoint()
        if unresolved_children: break
    sources=[Path(__file__).resolve(),HERE/'observe.cpp',HERE/'affine_log_reference.py']+sorted((HERE/'source').rglob('*.py'))+sorted((HERE/'source').rglob('*.hpp'))+sorted((HERE/'source').rglob('*.cpp'))
    status='passed' if len(families)==3 and not unresolved_children and all(r['status']=='completed' for r in families) and all(c['passed'] for c in checks) else 'failed_preserved'
    payload=dict(status=status,invented_only=True,families=families,checks=checks,commands=commands,counts=counts,budgets=BUDGET,
                 source_sha256={str(p.relative_to(ROOT)):sha(p) for p in sources},binary_sha256=sha(binary),settings=settings,
                 action_acceptance='True actual-displacement descent, conservative exact-interval Armijo, and recorded core Armijo; no tolerance relaxation.',
                 unresolved_children=unresolved_children,no_stationarity_or_first_arrival_claim=True,
                 candidate_convergence_status=None,native_calls=0,trace_calls=0,field_calls=0)
    payload['output_sha256']={str(p.relative_to(output)):sha(p) for p in sorted(output.rglob('*')) if p.is_file()}
    with (output/'summary.json').open('x') as stream: json.dump(encoded(payload),stream,indent=2,sort_keys=True,allow_nan=False);stream.write('\n')
    print(json.dumps(dict(status=status,checks=len(checks),summary_sha256=sha(output/'summary.json'))))
    return 0 if status=='passed' else 1


if __name__=='__main__': sys.exit(main())
