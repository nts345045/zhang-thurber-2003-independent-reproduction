"""One fixed-topology metric direction/trial: exact saved-interval accounting.

No native loader or executable entry point. The caller owns pinned inputs,
complete native identities, child lifecycle, and the single-trial inventory.
"""
from fractions import Fraction as Q
import math
import struct


def require(ok, message):
    if not ok: raise ValueError(message)


def binary(value):
    result=float(value)
    require(math.isfinite(result), 'Nonfinite binary64 conversion')
    return result


def exact_binary(value):
    result=binary(value)
    require(Q(result)==value, 'Coordinate/model value is not exactly binary64')
    return result


def start_inputs(t, grid, path, components):
    """Validate the declared subspace and preserve all midpoint conversions."""
    path=[tuple(map(Q,p)) for p in path]
    require(len(path)>=3 and len(components)==len(path), 'Incomplete path/components')
    require(components[0] is None and components[-1] is None, 'Fixed endpoint components must be omitted')
    for p in path:
        require(len(p)==3 and t.contains(grid,p), 'Invalid starting point')
        for x in p: exact_binary(x)
    require(all(all(a[0]<p[k]<a[-1] for k,a in enumerate(grid['axes'])) for p in path[1:-1]),
            'This diagnostic requires physically interior free nodes')
    blocked=set()
    for i,(a,b) in enumerate(zip(path,path[1:])):
        aligned=t.partition(grid,a,b)[3]
        require(len(aligned)<=1, 'Multiple aligned faces are outside this diagnostic')
        for axis,unused in aligned: blocked.update(((i,axis),(i+1,axis)))
    gradient=[];fixed=[];mapping=[]
    for i in range(1,len(path)-1):
        require(len(components[i])==3, 'Missing coordinate component')
        for axis,bounds in enumerate(components[i]):
            unavailable=(i,axis) in blocked
            require((bounds is None)==unavailable, 'Saved availability mask disagrees with exact geometry')
            if unavailable:
                gradient.append(0.0);fixed.append(True)
                mapping.append(dict(node=i,axis=axis,available=False,metric_rhs=0.0))
            else:
                lo,hi=map(Q,bounds);require(lo<=hi, 'Reversed derivative interval')
                midpoint=(lo+hi)/2;converted=binary(midpoint)
                gradient.append(converted);fixed.append(False)
                mapping.append(dict(node=i,axis=axis,available=True,bounds=(lo,hi),midpoint=midpoint,
                                    metric_rhs=converted,binary64_hex=converted.hex(),exact_converted=Q(converted)))
    return path,gradient,fixed,mapping


def solve_input(grid, path, gradient, fixed):
    axes=grid['axes'];tokens=[str(len(a)) for a in axes]+[str(len(path))]
    for axis in axes: tokens.extend(exact_binary(x).hex() for x in axis)
    for k in range(len(axes[2])):
        for j in range(len(axes[1])):
            for i in range(len(axes[0])):tokens.append(exact_binary(grid['velocities'][i,j,k]).hex())
    tokens.extend(exact_binary(x).hex() for p in path for x in p)
    tokens.extend(binary(x).hex() for x in gradient);tokens.extend(str(int(x)) for x in fixed)
    return '\n'.join(tokens)+'\n'


def emitted(values, hex_values):
    require(len(values)==len(hex_values), 'Missing hex values')
    result=[]
    for value,hex_value in zip(values,hex_values):
        x=binary(value);y=float.fromhex(hex_value)
        require(x.hex()==y.hex(), 'Decimal/hex binary64 disagreement')
        result.append(Q(x))
    return result


def metric_record(record, gradient, fixed, count):
    weights=[Q(binary(w)) for w in record['weights']]
    require(len(weights)==count-1 and all(w>0 for w in weights), 'Invalid positive weight inventory')
    flat=emitted(record['direction'],record['direction_hex'])
    require(len(flat)==3*(count-2)==len(gradient)==len(fixed), 'Direction inventory mismatch')
    require(all(not flag or d==0 for flag,d in zip(fixed,flat)), 'Unavailable normal moved')
    require(len(record['pivots'])==len(flat) and all(binary(x)>0 for x in record['pivots']), 'Invalid positive pivot inventory')
    direction=[(Q(0),)*3]+[tuple(flat[k:k+3]) for k in range(0,len(flat),3)]+[(Q(0),)*3]
    slope=sum(Q(g)*d for g,d in zip(gradient,flat))
    energy=sum(w*sum((b[k]-a[k])**2 for k in range(3))
               for w,a,b in zip(weights,direction,direction[1:]))
    residual=[]
    for i in range(1,count-1):
        for axis in range(3):
            k=3*(i-1)+axis
            value=(weights[i-1]+weights[i])*direction[i][axis]-weights[i-1]*direction[i-1][axis]-weights[i]*direction[i+1][axis]
            residual.append(dict(node=i,axis=axis,fixed=fixed[k],exact_recorded_equation_residual=value+Q(gradient[k])))
    return direction,dict(exact_recorded_midpoint_slope=slope,exact_recorded_metric_energy=energy,
                          exact_recorded_residuals=residual,
                          interpretation='Exact algebra of emitted binary64 data; no numerical-solve or Fermat certificate.')


def contraction(components, direction):
    require(len(components)==len(direction)>=3, 'Incomplete direction/components')
    require(tuple(direction[0])==tuple(direction[-1])==(0,0,0), 'Endpoints moved')
    require(components[0] is None and components[-1] is None, 'Unexpected endpoint components')
    lo=Q(0);hi=Q(0)
    for row,d in zip(components[1:-1],direction[1:-1]):
        require(len(row)==len(d)==3, 'Missing direction/component axis')
        for bounds,value in zip(row,d):
            value=Q(value)
            if bounds is None:
                require(value==0, 'Unavailable derivative has nonzero displacement')
            else:
                a,b=map(Q,bounds);require(a<=b, 'Reversed interval')
                x,y=a*value,b*value;lo+=min(x,y);hi+=max(x,y)
    return lo,hi


def downward_step(bound):
    bound=min(Q(1),Q(bound));require(bound>0, 'No positive geometric step')
    result=float(bound)
    if Q(result)>bound:
        bits=struct.unpack('>Q',struct.pack('>d',result))[0]
        result=struct.unpack('>d',struct.pack('>Q',bits-1))[0]
    require(0<result<=1 and math.isfinite(result) and Q(result)<=bound, 'Positive step is not representable')
    return result


def trial_input(path, direction, alpha):
    tokens=[str(len(path)),binary(alpha).hex()]
    tokens.extend(exact_binary(x).hex() for p in path for x in p)
    tokens.extend(exact_binary(x).hex() for d in direction for x in d)
    return '\n'.join(tokens)+'\n'


def trial_geometry(t, grid, path, direction, components, alpha, record):
    values=emitted(record['trial'],record['trial_hex'])
    require(len(values)==3*len(path), 'Trial inventory changed')
    trial=[tuple(values[k:k+3]) for k in range(0,len(values),3)]
    require(trial[0]==path[0] and trial[-1]==path[-1], 'Fixed endpoint changed')
    for i,p in enumerate(trial):
        require(t.contains(grid,p), 'Rounded trial outside physical box')
        if 0<i<len(path)-1:
            for axis in range(3):
                # Two Python scalar operations independently check the declared
                # C++ no-contraction multiply/add result, including ties.
                product=binary(alpha)*exact_binary(direction[i][axis])
                expected=exact_binary(path[i][axis])+product
                require(math.isfinite(expected) and Q(expected)==p[axis], 'Unexpected rounded coordinate')
                require(components[i][axis] is not None or p[axis]==path[i][axis], 'Unavailable normal changed')
    require(all(a!=b for a,b in zip(trial,trial[1:])), 'Rounded trial collapsed an edge')
    displacement=[tuple(y-x for x,y in zip(a,b)) for a,b in zip(path,trial)]
    return trial,displacement,contraction(components,displacement)


def trial_actions(t, grid, path, trial, starting_edges, settings, alpha, slope):
    """Full action with exact unchanged-edge cancellation; at most one trial."""
    require(len(path)==len(trial)==len(starting_edges)+1, 'Starting edge inventory mismatch')
    require(path[0]==trial[0] and path[-1]==trial[-1], 'Fixed endpoints changed')
    cache={};old_total=t.point(0);trial_total=t.point(0);delta=t.point(0);rows=[];new_records=[]
    for i,(a,b) in enumerate(zip(path,path[1:])):
        require(a!=b and t.contains(grid,a) and t.contains(grid,b), 'Invalid starting edge')
        value=tuple(map(Q,starting_edges[i]['action']));require(0<value[0]<=value[1], 'Invalid saved action')
        if (a,b) in cache:require(cache[a,b]['action']==value, 'Conflicting saved identical-edge bounds')
        cache[a,b]=dict(action=value,source='saved_start',edge=i)
    for i,(a,b,c,d) in enumerate(zip(path,path[1:],trial,trial[1:])):
        require(c!=d and t.contains(grid,c) and t.contains(grid,d), 'Invalid trial edge')
        before=tuple(map(Q,starting_edges[i]['action']));old_total=t.add(old_total,before)
        if (c,d) not in cache:
            record=t.edge_action(grid,c,d,settings);key=len(new_records)
            new_records.append(dict(record_id=key,a=c,b=d,record=record))
            cache[c,d]=dict(action=record['action'],source='new_trial',record_id=key)
        after=cache[c,d];trial_total=t.add(trial_total,after['action'])
        change=t.point(0) if (a,b)==(c,d) else t.sub(after['action'],before)
        delta=t.add(delta,change)
        rows.append(dict(edge=i,identical=(a,b)==(c,d),trial_record=after,difference=change))
    full_difference=t.sub(trial_total,old_total)
    require(max(delta[0],full_difference[0])<=min(delta[1],full_difference[1]), 'Full/paired actions inconsistent')
    rhs=Q(float('1e-4'))*Q(alpha)*Q(slope[0])
    return dict(starting_action=old_total,trial_action=trial_total,paired_difference=delta,
                full_difference=full_difference,edge_joins=rows,new_edge_records=new_records,
                action_edge_evaluations=len(new_records),strict_decrease=delta[1]<0,
                strict_increase=delta[0]>0,nominal_armijo_rhs_lower=rhs,
                conservative_nominal_armijo=delta[1]<=rhs,
                interpretation='Armijo uses nominal direction slope and actual rounded trial action; no new convergence status.')


def single_trial(t, grid, path, components, starting_edges, settings, metric_call, round_call):
    """One direction, at most one trial; callbacks perform only the named I/O."""
    result=dict(status='ineligible_start',metric_solves=0,rounded_trials=0,action_edge_evaluations=0,
                new_convergence_status=None,original_status_changed=False)
    try:
        require(settings==dict(terms=8,subdivisions=1,bits=128), 'This experiment has one fixed integration budget')
        path,rhs,fixed,mapping=start_inputs(t,grid,path,components)
        result['midpoint_mapping']=mapping
        result['metric_solves']=1;result['status']='unusable_metric'
        metric=metric_call(solve_input(grid,path,rhs,fixed));result['metric']=metric
        direction,account=metric_record(metric,rhs,fixed,len(path))
        slope=contraction(components,direction)
        result.update(direction=direction,metric_exact_account=account,nominal_slope=slope,status='nominal_slope_unresolved')
        if slope[1]>=0:return result
        bound=t.feasible_directions(grid,path,direction);alpha=downward_step(bound)
        result.update(geometric_bound=bound,alpha=alpha,alpha_hex=alpha.hex(),status='unusable_rounded_trial',rounded_trials=1)
        raw=round_call(trial_input(path,direction,alpha));result['rounded_record']=raw
        trial,displacement,actual_slope=trial_geometry(t,grid,path,direction,components,alpha,raw)
        result.update(trial=trial,actual_displacement=displacement,actual_displacement_slope=actual_slope,
                      status='actual_displacement_slope_unresolved')
        if actual_slope[1]>=0:return result
        result['status']='action_evaluation_failed'
        # A failure may occur after a prior edge completed. Zero would make an
        # unsupported no-evaluation claim; retain unknown until full completion.
        result['action_edge_evaluations']=None
        action=trial_actions(t,grid,path,trial,starting_edges,settings,alpha,slope)
        result.update(action=action,action_edge_evaluations=action['action_edge_evaluations'],
                      status='diagnostic_trial_accepted' if action['conservative_nominal_armijo'] else 'diagnostic_trial_not_accepted')
    except (ValueError,OverflowError) as error:
        result['error']=dict(type=type(error).__name__,message=str(error))
    return result
