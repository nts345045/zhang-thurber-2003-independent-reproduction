"""Coupled constant-patch support of a fixed polygon's first variation.

The midpoint fit only proposes feasible binary64 mixture coefficients. Outward
moment/vector bounds, not the fit objective, determine the witness bound.
"""
from fractions import Fraction as Q
import math


def require(ok,message):
    if not ok: raise ValueError(message)


def interval(value):
    lo,hi=map(Q,value); require(lo<=hi,'Reversed component interval'); return lo,hi


def add(a,b): return a[0]+b[0],a[1]+b[1]
def midpoint(a): return (a[0]+a[1])/2


def aligned_patch_moments(grid,a,b,settings,t):
    """Four endpoint normal moments per exact patch, with a common face v."""
    a,b,e,aligned,pieces=t.partition(grid,a,b,subdivisions=settings['subdivisions'])
    if len(aligned)!=1:
        return dict(status='ineligible_single_aligned_face_required',aligned=aligned,patches=[],a_exact=a,b_exact=b)
    axis,index=aligned[0]; length=t.length_interval(e,settings['bits']); records=[]
    for left,right,cell in pieces:
        minus=list(cell); minus[axis]=index-1
        plus=list(cell); plus[axis]=index
        vm,gm,bm=t.cell_polynomials(grid,a,e,left,right,tuple(minus))
        vp,gp,bp=t.cell_polynomials(grid,a,e,left,right,tuple(plus))
        require(vm==vp,'Discontinuous face velocity')
        vertex_bounds=(max(bm[0],bp[0]),min(bm[1],bp[1]))
        require(0<vertex_bounds[0]<=vertex_bounds[1],'Positive common velocity bound')
        jump=t.padd(gm[axis],t.scale(gp[axis],-1)); exact_range=t.quadratic_bounds(jump)
        records.append(dict(a_exact=a,b_exact=b,u=(left,right),normal_axis=axis,
            normal_coordinate=grid['axes'][axis][index],minus_cell=minus,plus_cell=plus,
            velocity_polynomial=vm,minus_velocity_normal_polynomial=gm[axis],plus_velocity_normal_polynomial=gp[axis],
            minus_vertex_bounds=bm,plus_vertex_bounds=bp,velocity_vertex_bounds=vertex_bounds,
            jump_numerator=jump,exact_jump_range=exact_range,convex_normal_jump=exact_range[0]>=0,
            minus=None,plus=None,tail_record=None))
    if not all(r['convex_normal_jump'] for r in records):
        return dict(status='ineligible_nonconvex_normal_jump',normal_axis=axis,length=length,patches=records,a_exact=a,b_exact=b,
                    normal_patch_integrations=0)
    for record in records:
        left,right=record['u']; width=right-left
        weights=((1-left,-width),(left,width))
        numerators=[t.pmul(g,h) for g in (record['minus_velocity_normal_polynomial'],record['plus_velocity_normal_polynomial']) for h in weights]
        require(all(len(f)<=4 for f in numerators),'Normal endpoint numerator exceeds degree three')
        unused,values,tail=t.reciprocal_integrals(record['velocity_polynomial'],numerators,record['velocity_vertex_bounds'],settings['terms'])
        moments=[t.rounded(t.mul(t.point(-width),t.mul(length,v)),settings['bits']) for v in values]
        record.update(minus=moments[:2],plus=moments[2:],tail_record=tail,numerators=numerators,inverse_square_integral_bounds=values)
    return dict(status='bounded_convex_patch_moments',normal_axis=axis,length=length,patches=records,a_exact=a,b_exact=b,
                normal_patch_integrations=len(records),units='s/km',
                interpretation='One shared constant theta per patch blends both endpoint moments; this is a restricted feasible support family.')


def ordinary_base(path,edge_records):
    """Retain all ordinary terms, including normals of adjacent unaligned edges."""
    require(len(path)>=2,'At least two fixed endpoints required')
    require([r['edge'] for r in edge_records]==list(range(len(path)-1)),'Complete ordered edge components required')
    components=[[(Q(0),Q(0)) for k in range(3)] for p in path]; components[0]=components[-1]=None
    aligned={}; blocked=set(); ordinary=[]
    for r in edge_records:
        edge=r['edge']; axes=r['blocked_axes']; require(len(axes)<=1,'Multiple aligned faces unsupported')
        require(len(r['components'])==2,'Two endpoint records required')
        if axes: aligned[edge]=axes[0]
        for side in (0,1):
            node=edge+side
            if not 0<node<len(path)-1: continue
            require(r['components'][side] is not None and len(r['components'][side])==3,'Complete internal endpoint components')
            for axis,value in enumerate(r['components'][side]):
                require((value is None)==(axis in axes),'Edge normal availability mismatch')
                if value is None: blocked.add((node,axis))
                else: components[node][axis]=add(components[node][axis],interval(value))
    for r in edge_records:
        for side in (0,1):
            node=r['edge']+side
            if not 0<node<len(path)-1: continue
            for axis,value in enumerate(r['components'][side]):
                if (node,axis) in blocked and value is not None:
                    ordinary.append(dict(edge=r['edge'],side=side,node=node,axis=axis,contribution=interval(value)))
    return dict(components=components,aligned_edges=aligned,blocked_slots=sorted(blocked),ordinary_contributions_in_blocked_slots=ordinary)


def validate_patches(path,base,patches):
    by_edge={edge:[] for edge in base['aligned_edges']}
    for patch in patches:
        edge=patch['edge']; require(edge in by_edge and patch['normal_axis']==base['aligned_edges'][edge],'Patch/edge normal join')
        require(tuple(map(Q,patch['a_exact']))==tuple(map(Q,path[edge])) and tuple(map(Q,patch['b_exact']))==tuple(map(Q,path[edge+1])),'Patch coordinate join')
        require(patch['convex_normal_jump'] and Q(patch['exact_jump_range'][0])>=0,'Unproved convex normal jump')
        left,right=map(Q,patch['u']); require(0<=left<right<=1,'Positive patch interval')
        require(len(patch['minus'])==len(patch['plus'])==2,'Both endpoint moments required')
        for value in patch['minus']+patch['plus']: interval(value)
        by_edge[edge].append((left,right))
    for pieces in by_edge.values():
        require(pieces and pieces[0][0]==0 and pieces[-1][1]==1 and all(a[1]==b[0] for a,b in zip(pieces,pieces[1:])),'Complete ordered patch partition')


def propose_theta(path,base,patches,max_sweeps=10000):
    """Cyclic clipped midpoint proposal, never an optimum or certificate."""
    require(type(max_sweeps) is int and 1<=max_sweeps<=10000,'Declared sweep budget required')
    validate_patches(path,base,patches)
    baseline=[list(v) if v is not None else None for v in base['components']]; exact_columns=[]
    for patch in patches:
        column=[]; axis=patch['normal_axis']
        for side in (0,1):
            node=patch['edge']+side
            if not 0<node<len(path)-1: continue
            minus,plus=interval(patch['minus'][side]),interval(patch['plus'][side])
            baseline[node][axis]=add(baseline[node][axis],minus)
            value=midpoint(plus)-midpoint(minus)
            if value: column.append((3*(node-1)+axis,value))
        exact_columns.append(column)
    theta=[0.5]*len(patches); columns=[]; denominators=[]; zero_columns=[]; coefficients_changed=0; sweeps=0
    initial_objective=None; final_objective=None; termination='sweep_budget'; reason=None; b=[]
    try:
        b=[float(midpoint(v)) for row in baseline[1:-1] for v in row]
        require(all(math.isfinite(v) for v in b),'Nonfinite midpoint baseline')
        for j,exact_column in enumerate(exact_columns):
            column=[(i,float(v)) for i,v in exact_column]
            require(all(math.isfinite(v) and v!=0 for i,v in column),'Nonfinite or underflowed nonzero midpoint column')
            denominator=sum(v*v for i,v in column)
            if not column: zero_columns.append(j)
            else: require(math.isfinite(denominator) and denominator>0,'Unusable positive midpoint denominator')
            columns.append(column); denominators.append(denominator)
        def residual():
            r=list(b)
            for value,column in zip(theta,columns):
                for i,a in column: r[i]+=value*a
            require(all(math.isfinite(v) for v in r),'Nonfinite midpoint residual')
            return r
        r=residual(); initial_objective=sum(v*v for v in r)
        require(math.isfinite(initial_objective),'Nonfinite initial midpoint objective')
        for sweep in range(max_sweeps):
            changed=False
            for j,column in enumerate(columns):
                if not column: continue
                numerator=sum(a*r[i] for i,a in column)
                proposal=theta[j]-numerator/denominators[j]
                require(math.isfinite(proposal),'Nonfinite coordinate proposal')
                value=min(1.0,max(0.0,proposal)); delta=value-theta[j]
                if delta==0: continue
                updates=[(i,r[i]+a*delta) for i,a in column]
                require(all(math.isfinite(v) for i,v in updates),'Nonfinite coordinate residual update')
                theta[j]=value
                for i,v in updates: r[i]=v
                changed=True; coefficients_changed+=1
            sweeps=sweep+1
            if not changed: termination='coefficients_unchanged'; break
        r=residual(); final_objective=sum(v*v for v in r)
        require(math.isfinite(final_objective),'Nonfinite final midpoint objective')
    except (ValueError,OverflowError,ZeroDivisionError) as error:
        termination='unusable_midpoint_arithmetic'; reason=str(error)
        if initial_objective is not None and not math.isfinite(initial_objective): initial_objective=None
        if final_objective is not None and not math.isfinite(final_objective): final_objective=None
    require(all(math.isfinite(v) and 0<=v<=1 for v in theta),'Finite feasible theta required')
    return dict(status='proposal_unusable' if reason else 'bounded_midpoint_proposal',termination=termination,reason=reason,
        theta=theta,theta_hex=[v.hex() for v in theta],theta_exact=[Q(v) for v in theta],
        max_sweeps=max_sweeps,sweeps=sweeps,coordinate_updates=coefficients_changed,exact_zero_midpoint_columns=zero_columns,
        initial_midpoint_objective=initial_objective,final_midpoint_objective=final_objective,
        interpretation='Midpoint arithmetic only proposes a feasible constant mixture. No tolerance, rank cutoff or optimality claim; interval assembly is independent.')


def assemble_support(path,base,patches,theta,axes,projected_norm):
    """One full feasible interval vector, with true physical-box projection."""
    validate_patches(path,base,patches); require(len(theta)==len(patches),'One coefficient per patch')
    theta=list(map(Q,theta)); require(all(0<=v<=1 for v in theta),'Mixture outside [0,1]')
    components=[list(v) if v is not None else None for v in base['components']]; contributions=[]
    for index,(patch,weight) in enumerate(zip(patches,theta)):
        for side in (0,1):
            node=patch['edge']+side; axis=patch['normal_axis']
            minus,plus=interval(patch['minus'][side]),interval(patch['plus'][side])
            term=((1-weight)*minus[0]+weight*plus[0],(1-weight)*minus[1]+weight*plus[1])
            contributions.append(dict(patch=index,edge=patch['edge'],side=side,node=node,axis=axis,theta_exact=weight,contribution=term,fixed_endpoint=node in (0,len(path)-1)))
            if 0<node<len(path)-1: components[node][axis]=add(components[node][axis],term)
    norm,projected,blocked=projected_norm(path,components,axes)
    require(not blocked,'Full support has an unavailable component')
    return dict(status='feasible_constant_patch_support',theta_exact=theta,
        vector=[dict(node=i,components=components[i]) for i in range(1,len(path)-1)],patch_contributions=contributions,
        ordinary_contributions_in_blocked_slots=base['ordinary_contributions_in_blocked_slots'],projected_components=projected,norm=norm,
        interpretation='Upper squared norm bounds this feasible full supporting vector. Neither its lower nor upper bound is the minimum over all supports. A large bound is inconclusive; no convergence or minimum claim.')
