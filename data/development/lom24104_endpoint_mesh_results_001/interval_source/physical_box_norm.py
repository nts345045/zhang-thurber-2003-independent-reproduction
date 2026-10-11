"""Exact copied physical-box interval projection; no numerical integrations."""
from fractions import Fraction as Q


def require(ok,message):
    if not ok:raise ValueError(message)


def interval(value):
    a,b=map(Q,value);require(a<=b,'Reversed saved bounds');return a,b


def add(a,b):return a[0]+b[0],a[1]+b[1]


def projected_norm(path,components,axes):
    """Exact physical-box projection and sums; no square-root approximation."""
    total=(Q(0),Q(0));records=[];blocked=[];boundary=0
    for node in range(1,len(path)-1):
        require(len(components[node])==3,'Missing physical component')
        for axis,saved in enumerate(components[node]):
            if saved is None:blocked.append((node,axis));continue
            lo,hi=interval(saved);position=path[node][axis];where='interior';projected=(lo,hi)
            require(axes[axis][0]<=position<=axes[axis][-1],'Outside physical box')
            if position==axes[axis][0]:where='exact_lower';projected=(min(lo,Q(0)),min(hi,Q(0)))
            elif position==axes[axis][-1]:where='exact_upper';projected=(max(lo,Q(0)),max(hi,Q(0)))
            a,b=projected;square=(Q(0) if a<=0<=b else min(a*a,b*b),max(a*a,b*b))
            total=add(total,square);boundary+=int(where!='interior')
            records.append(dict(node=node,axis=axis,coordinate_exact=position,component_bounds=(lo,hi),
                                physical_box_position=where,projected_bounds=projected,squared_bounds=square))
    scales={}
    for name,scale in (('strict_gradient_scale',Q(1,10**7)),('combined_gradient_scale',Q(1,10**5))):
        squared=scale*scale
        scales[name]=dict(scale_squared=squared,classification='strictly_above' if total[0]>squared else
                         ('strictly_below' if total[1]<squared else 'overlapping'),diagnostic_only=True)
    return dict(lower_squared=total[0],upper_squared=total[1],units='s^2/km^2',
                available_component_count=len(records),unavailable_component_count=len(blocked),
                exact_physical_boundary_component_count=boundary,threshold_scales=scales,
                activity_rule='Exact physical box only; no 1e-10 activity band.'),records,blocked
