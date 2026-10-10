"""Rational bounds for fixed polygons in a positive trilinear model.

No ray search, native loader, source/model derivative, or convergence flag.
First variations exclude edges aligned with multiple internal grid faces.
"""
from bisect import bisect_right
from fractions import Fraction as Q
from itertools import product
import math

from diagnostics.check_native_interface_support import point, add, sub, mul, div, rounded
from diagnostics.first_arrival_1d_precise_turn_reference import candidate_sqrt_enclosure


def require(ok, message):
    if not ok:
        raise ValueError(message)


def exact(value):
    require(type(value) in (int, float, Q), 'Use integers, Fractions, or finite binary64 inputs')
    if isinstance(value, float):
        require(math.isfinite(value), 'Nonfinite binary64 input')
    return Q(value)


def vector(values):
    require(len(values) == 3, 'Require three coordinates')
    return tuple(exact(x) for x in values)


def poly(values):
    values = list(map(Q, values))
    while len(values) > 1 and values[-1] == 0:
        values.pop()
    return tuple(values or [Q(0)])


def padd(a, b):
    return poly((a[k] if k < len(a) else 0) + (b[k] if k < len(b) else 0)
                for k in range(max(len(a), len(b))))


def scale(a, c):
    return poly(x*c for x in a)


def pmul(a, b):
    result = [Q(0)] * (len(a)+len(b)-1)
    for i, x in enumerate(a):
        for j, y in enumerate(b):
            result[i+j] += x*y
    return poly(result)


def value(a, t):
    result = Q(0)
    for x in reversed(a):
        result = result*t+x
    return result


def integral(a):
    return sum((x/Q(k+1) for k, x in enumerate(a)), Q(0))


def choose(n, k):
    result = 1
    for j in range(1, k+1):
        result = result*(n-j+1)//j
    return result


def polynomial_bounds(a):
    """Power-to-Bernstein conversion on [0,1], with exact rational coefficients."""
    n = len(a)-1
    coefficients = [sum((a[j]*Q(choose(i,j), choose(n,j)) for j in range(i+1)), Q(0))
                    for i in range(n+1)]
    return min(coefficients), max(coefficients)


def quadratic_bounds(a):
    require(len(a) <= 3, 'Jump numerator is not quadratic')
    samples = [value(a, Q(0)), value(a, Q(1))]
    if len(a) == 3 and a[2]:
        t = -a[1]/(2*a[2])
        if 0 < t < 1:
            samples.append(value(a, t))
    return min(samples), max(samples)


def model(axes, velocities):
    axes = tuple(tuple(exact(x) for x in axis) for axis in axes)
    require(len(axes) == 3 and all(len(a) >= 2 for a in axes), 'Incomplete Cartesian axes')
    require(all(all(x < y for x,y in zip(a,a[1:])) for a in axes), 'Axes must increase strictly')
    keys = set(product(*(range(len(a)) for a in axes)))
    require(set(velocities) == keys, 'Incomplete or extra Cartesian velocity nodes')
    velocities = {k: exact(v) for k,v in velocities.items()}
    require(all(v > 0 for v in velocities.values()), 'Require strictly positive nodal velocities')
    return dict(axes=axes, velocities=velocities)


def contains(grid, p):
    return all(axis[0] <= x <= axis[-1] for axis,x in zip(grid['axes'],p))


def options(terms=32, subdivisions=4, bits=128):
    require(type(terms) is int and terms >= 0, 'Nonnegative finite series degree required')
    require(type(subdivisions) is int and subdivisions >= 1, 'Positive finite subdivision count required')
    require(type(bits) is int and bits >= 2, 'At least two rational bound bits required')
    return dict(terms=terms, subdivisions=subdivisions, bits=bits)


def partition(grid, a, b, da=None, db=None, subdivisions=1):
    a, b = vector(a), vector(b)
    require(contains(grid,a) and contains(grid,b), 'Edge outside the finite box')
    e = tuple(y-x for x,y in zip(a,b))
    require(any(e), 'Zero-length edge is outside this variation')
    cuts = {Q(0),Q(1)}; aligned = []
    for axis, coordinates in enumerate(grid['axes']):
        if e[axis]:
            cuts.update((x-a[axis])/e[axis] for x in coordinates[1:-1]
                        if 0 < (x-a[axis])/e[axis] < 1)
        elif a[axis] in coordinates[1:-1]:
            aligned.append((axis, coordinates.index(a[axis])))
    if da is not None:
        require(db is not None and len(aligned) <= 1, 'Multiple aligned internal faces are outside the first variation')
        da, db = vector(da), vector(db)
        for axis, unused in aligned:
            delta = db[axis]-da[axis]
            if delta and 0 < -da[axis]/delta < 1:
                cuts.add(-da[axis]/delta)
    original = sorted(cuts)
    cuts = sorted({left+(right-left)*Q(j,subdivisions)
                   for left,right in zip(original,original[1:]) for j in range(subdivisions+1)})
    pieces = []
    for left,right in zip(cuts,cuts[1:]):
        mid = (left+right)/2
        cell = [min(len(axis)-2,max(0,bisect_right(axis,a[k]+mid*e[k])-1))
                for k,axis in enumerate(grid['axes'])]
        for axis,index in aligned:
            q = Q(0) if da is None else da[axis]+mid*(db[axis]-da[axis])
            cell[axis] = index-1 if q < 0 else index
        pieces.append((left,right,tuple(cell)))
    return a,b,e,aligned,pieces


def cell_polynomials(grid, a, e, left, right, cell):
    """Velocity and spatial derivatives versus local t in [0,1]."""
    fractions = []; widths = []
    for k,axis in enumerate(grid['axes']):
        width = axis[cell[k]+1]-axis[cell[k]]; widths.append(width)
        f = poly(((a[k]+left*e[k]-axis[cell[k]])/width, (right-left)*e[k]/width))
        require(0 <= value(f,Q(0)) <= 1 and 0 <= value(f,Q(1)) <= 1, 'Restriction leaves its certified closed cell')
        fractions.append((padd((Q(1),),scale(f,-1)),f))
    v = (Q(0),); grad = [(Q(0),)]*3; vertices = []
    for corner in product((0,1), repeat=3):
        speed = grid['velocities'][tuple(cell[k]+corner[k] for k in range(3))]
        vertices.append(speed)
        basis = (Q(1),)
        for k in range(3): basis = pmul(basis,fractions[k][corner[k]])
        v = padd(v,scale(basis,speed))
        for axis in range(3):
            derivative = (Q(1 if corner[axis] else -1)/widths[axis],)
            for k in range(3):
                if k != axis: derivative = pmul(derivative,fractions[k][corner[k]])
            grad[axis] = padd(grad[axis],scale(derivative,speed))
    return v,grad,(min(vertices),max(vertices))


def reciprocal_integrals(v, numerators, vertex_bounds, terms):
    """Unit-parameter integrals of 1/v and each f/v^2, with explicit tails."""
    lo,hi = polynomial_bounds(v)
    lo,hi = max(lo,vertex_bounds[0]),min(hi,vertex_bounds[1])
    require(0 < lo <= hi, 'Positive velocity bound failed')
    c = (lo+hi)/2; rho = (hi-lo)/(hi+lo)
    q = scale(padd((c,),scale(v,-1)),1/c)
    n = 0 if rho == 0 else terms
    power = (Q(1),); average = Q(0); inverse = [Q(0)]*len(numerators)
    for k in range(n+1):
        average += integral(power)/c
        for j,f in enumerate(numerators): inverse[j] += (k+1)*integral(pmul(f,power))/(c*c)
        if k != n: power = pmul(power,q)
    tail = rho**(n+1)/(c*(1-rho))
    factor = rho**(n+1)*((n+2)-(n+1)*rho)/(c*c*(1-rho)**2)
    tails = [max(abs(x) for x in polynomial_bounds(f))*factor for f in numerators]
    average_bound = (max(average-tail,1/hi),min(average+tail,1/lo))
    require(average_bound[0] <= average_bound[1], 'Inconsistent reciprocal enclosure')
    return average_bound,[(x-t,x+t) for x,t in zip(inverse,tails)],dict(
        velocity_bounds=(lo,hi),rho=rho,series_degree=n,reciprocal_tail=tail,inverse_square_tails=tails)


def length_interval(e, bits):
    square = sum(x*x for x in e)
    require(square > 0, 'Zero edge square')
    unused,bounds = candidate_sqrt_enclosure(square,bits)
    require(0 < bounds[0] and bounds[0]**2 <= square <= bounds[1]**2, 'Invalid rational square-root enclosure')
    return bounds


def edge_action(grid, a, b, settings):
    a,b,e,aligned,pieces = partition(grid,a,b,subdivisions=settings['subdivisions'])
    length = length_interval(e,settings['bits']); total = point(0); records = []
    for left,right,cell in pieces:
        v,unused,bounds = cell_polynomials(grid,a,e,left,right,cell)
        average,unused,record = reciprocal_integrals(v,[],bounds,settings['terms'])
        total = add(total,rounded(mul(point(right-left),average),settings['bits']))
        records.append(dict(record,u=(left,right),cell=cell,velocity_polynomial=v))
    return dict(action=rounded(mul(length,total),settings['bits']),length=length,aligned=aligned,pieces=records)


def feasible_directions(grid, path, direction):
    require(len(path) == len(direction) and len(path) >= 2, 'Path/direction inventory mismatch')
    path, direction = list(map(vector,path)),list(map(vector,direction))
    require(direction[0] == direction[-1] == (0,0,0), 'Source and receiver directions must be fixed')
    maximum = None
    for p,d in zip(path,direction):
        require(contains(grid,p), 'Path outside finite box')
        for axis,x,dx in zip(grid['axes'],p,d):
            if dx:
                bound = (axis[-1]-x)/dx if dx > 0 else (axis[0]-x)/dx
                require(bound > 0, 'Direction points out of a boundary')
                maximum = bound if maximum is None else min(maximum,bound)
    for a,b,da,db in zip(path,path[1:],direction,direction[1:]):
        e = tuple(y-x for x,y in zip(a,b)); delta = tuple(y-x for x,y in zip(da,db))
        length = length_interval(e,128)
        if any(delta):
            speed = length_interval(delta,128)
            bound = length[0]/(2*speed[1])
            maximum = bound if maximum is None else min(maximum,bound)
    return maximum  # A closed positive bound; no perturbed coordinates are generated.


def edge_directional(grid, a, b, da, db, settings):
    """Right directional derivative for physically feasible endpoint directions."""
    da,db = vector(da),vector(db)
    a,b,e,aligned,pieces = partition(grid,a,b,da,db,settings['subdivisions'])
    for p,d in ((a,da),(b,db)):
        require(all(not (x == axis[0] and dx < 0) and not (x == axis[-1] and dx > 0)
                    for axis,x,dx in zip(grid['axes'],p,d)), 'Direction points out of a boundary')
    length = length_interval(e,settings['bits'])
    geometric = sum(e[k]*(db[k]-da[k]) for k in range(3))
    average_total,medium_total = point(0),point(0); records = []
    for left,right,cell in pieces:
        v,grad,bounds = cell_polynomials(grid,a,e,left,right,cell)
        numerator = (Q(0),)
        for k in range(3):
            d = poly((da[k]+left*(db[k]-da[k]),(right-left)*(db[k]-da[k])))
            numerator = padd(numerator,pmul(grad[k],d))
        average,medium,record = reciprocal_integrals(v,[numerator],bounds,settings['terms'])
        average_total = add(average_total,rounded(mul(point(right-left),average),settings['bits']))
        medium_total = add(medium_total,rounded(mul(point(right-left),medium[0]),settings['bits']))
        records.append(dict(record,u=(left,right),cell=cell,velocity_polynomial=v,numerator=numerator))
    derivative = sub(mul(div(point(geometric),length),average_total),mul(length,medium_total))
    return dict(derivative=rounded(derivative,settings['bits']),pieces=records,aligned=aligned)


def edge_tangent_components(grid, a, b, settings):
    a,b,e,aligned,pieces = partition(grid,a,b,subdivisions=settings['subdivisions'])
    require(len(aligned) <= 1, 'Multiple aligned internal faces are outside tangent components')
    blocked = {axis for axis,index in aligned}
    length = length_interval(e,settings['bits']); total = point(0)
    slots = [(side,axis) for side in (0,1) for axis in range(3) if axis not in blocked]
    medium = [point(0) for unused in slots]
    for left,right,cell in pieces:
        v,grad,bounds = cell_polynomials(grid,a,e,left,right,cell)
        numerators = [pmul(grad[axis],poly((1-left,-(right-left)) if side == 0 else (left,right-left)))
                      for side,axis in slots]
        average,values,unused = reciprocal_integrals(v,numerators,bounds,settings['terms'])
        total = add(total,rounded(mul(point(right-left),average),settings['bits']))
        medium = [add(old,rounded(mul(point(right-left),new),settings['bits'])) for old,new in zip(medium,values)]
    result = [[None]*3,[None]*3]
    for (side,axis),term in zip(slots,medium):
        geometric = mul(div(point((-1 if side == 0 else 1)*e[axis]),length),total)
        result[side][axis] = rounded(sub(geometric,mul(length,term)),settings['bits'])
    return dict(components=result,blocked_axes=sorted(blocked))


def face_jumps(grid, a, b):
    a,b,e,aligned,pieces = partition(grid,a,b)
    require(len(aligned) == 1, 'Require exactly one aligned internal face')
    axis,index = aligned[0]; records = []
    for left,right,cell in pieces:
        minus=list(cell);minus[axis]=index-1
        plus=list(cell);plus[axis]=index
        vm,gm,unused = cell_polynomials(grid,a,e,left,right,tuple(minus))
        vp,gp,unused = cell_polynomials(grid,a,e,left,right,tuple(plus))
        require(vm == vp, 'Internal face velocity is discontinuous')
        numerator = padd(gm[axis],scale(gp[axis],-1))
        bounds = quadratic_bounds(numerator)
        records.append(dict(u=(left,right),normal_axis=axis,jump_numerator=numerator,
                            jump_numerator_bounds=bounds,convex_normal_jump=bounds[0] >= 0))
    return records


def path_action(grid, path, settings):
    require(len(path) >= 2, 'Path is too short')
    records = [edge_action(grid,a,b,settings) for a,b in zip(path,path[1:])]
    total = point(0)
    for record in records: total = add(total,record['action'])
    return dict(action=total,edges=records)


def action_difference(grid, original, candidate, settings):
    require(len(original) == len(candidate) >= 2, 'Fixed positive-length topology required')
    original,candidate = list(map(vector,original)),list(map(vector,candidate))
    require(original[0] == candidate[0] and original[-1] == candidate[-1], 'Candidate changes a fixed endpoint')
    delta=point(0);changed=[]
    for i,(a,b,c,d) in enumerate(zip(original,original[1:],candidate,candidate[1:])):
        require(contains(grid,a) and contains(grid,b) and contains(grid,c) and contains(grid,d), 'Path outside finite box')
        require(a != b and c != d, 'Zero-length edge')
        if a == c and b == d: continue
        before,after = edge_action(grid,a,b,settings),edge_action(grid,c,d,settings)
        edge_delta = sub(after['action'],before['action'])
        delta=add(delta,edge_delta);changed.append(dict(edge=i,difference=edge_delta))
    return dict(difference=delta,changed_edges=changed)


def path_directional(grid, path, direction, settings):
    feasible = feasible_directions(grid,path,direction)
    total=point(0);records=[]
    for a,b,da,db in zip(path,path[1:],direction,direction[1:]):
        record=edge_directional(grid,a,b,da,db,settings)
        total=add(total,record['derivative']);records.append(record)
    return dict(derivative=total,feasible_step_bound=feasible,edges=records)


def tangent_witness(grid, path, settings):
    path=list(map(vector,path));require(len(path)>=2, 'Path is too short')
    components=[[point(0) for k in range(3)] for p in path];blocked=set()
    for i,(a,b) in enumerate(zip(path,path[1:])):
        record=edge_tangent_components(grid,a,b,settings)
        for side in (0,1):
            for axis,term in enumerate(record['components'][side]):
                if term is None: blocked.add((i+side,axis))
                else: components[i+side][axis]=add(components[i+side][axis],term)
    for i,axis in blocked: components[i][axis]=None
    for i in range(1,len(path)-1):
        for axis,bounds in enumerate(components[i]):
            if bounds is None or bounds[0] <= 0 <= bounds[1]: continue
            sign = -1 if bounds[0] > 0 else 1
            if (sign < 0 and path[i][axis] == grid['axes'][axis][0]) or (sign > 0 and path[i][axis] == grid['axes'][axis][-1]): continue
            direction=[(Q(0),Q(0),Q(0)) for p in path]
            d=[Q(0)]*3;d[axis]=Q(sign);direction[i]=tuple(d)
            evaluated=path_directional(grid,path,direction,settings)
            if evaluated['derivative'][1] < 0:
                return dict(status='negative_tangent_witness',node=i,axis=axis,direction=direction,
                            components=components,evaluation=evaluated)
    return dict(status='no_negative_tangent_witness_resolved',components=components,
                limitation='This is not an all-direction stationarity or minimum test.')
