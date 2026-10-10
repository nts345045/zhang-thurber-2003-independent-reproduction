"""Isolated finite-domain reference for positive continuous piecewise-linear v(z).

The normal coordinate is source[2]; transverse coordinates are source[:2].
No production ray solver is imported. This extends, without changing, the
exact-leg and interval-root primitives of first_arrival_1d_reference.

Candidate completeness uses the following variational argument. Tangential
translation symmetry gives conserved p>0 and monotone transverse progress.
For u=1/p, every traversed speed is <=u. After the first normal turn (v=u),
replace any subsequent excursions by the monotone leg to the receiver and a
guide at that turn to restore removed transverse distance. The removed excess
is integral sqrt(v^-2-p^2)|dz|>0. Thus a multiply-turning nondegenerate ray is
not first. The feasible comparison guide need not itself be stationary.
First arrivals therefore occur among direct monotone legs, single outward
turns, or critical guides at accessible maxima/plateaus/domain faces. Equal
maxima can give nonunique guide allocations with identical time and momentum.

This numerical implementation must be independently validated before use as a
simulation reference. Unresolved signs/roots remain explicit; floating-point
time ordering is not an interval certificate of the minimum.
"""
import math

import numpy as np
from scipy.optimize import brentq

from first_arrival_1d_reference import (Q, Interval, coefficients, compare_limit,
    distance_limit, leg, point_sign, turning_roots, velocity)


def maximum(profile, a, b):
    """Exact maximum on a closed interval, including interpolated endpoints."""
    a, b = min(a, b), max(a, b)
    return max([velocity(profile, a), velocity(profile, b)] +
               [v for z, v in profile if a < z < b])


def turning_spec(profile, zs, zr, layer):
    """Rightward increasing-layer turn; every preceding speed constrains u."""
    (a, va), (b, vb) = profile[layer:layer + 2]
    gradient = (vb - va) / (b - a)
    if gradient <= 0 or b < max(zs, zr):
        raise ValueError('Not an outward increasing turning layer')
    u0 = max(maximum(profile, endpoint, max(endpoint, a)) for endpoint in (zs, zr))
    c, k = {}, {}
    for endpoint in (zs, zr):
        cc, kk = coefficients(profile, endpoint, max(endpoint, a))
        for target, source in ((c, cc), (k, kk)):
            for key, value in source.items():
                target[key] = target.get(key, Q(0)) + value
        entry = velocity(profile, max(endpoint, a))
        c[entry * entry] = c.get(entry * entry, Q(0)) + 1 / gradient
    return dict(u0=u0, upper=vb, span=vb * vb - u0 * u0,
        c0=c.get(u0 * u0, Q(0)), k0=k.get(u0 * u0, Q(0)),
        c=[(u0 * u0 - key, value) for key, value in c.items() if value and key != u0 * u0],
        k=[(u0 * u0 - key, value) for key, value in k.items() if value and key != u0 * u0])


def enumerate_arrivals(depths, speeds, source, receiver, bounds=None,
                       root_tolerance=1e-12, distance_tolerance=1e-8, max_boxes=20000):
    """Enumerate candidates or explicitly retain unsupported/critical cases.

    Optional bounds is a three-axis closed box; its normal interval must equal
    the supplied profile domain. Without bounds the transverse plane is free.
    Candidate paths have monotone transverse coordinates, so any convex box
    containing both endpoints contains that part of every candidate.
    """
    result = dict(complete=False, reference_valid=False, candidates=[], unresolved=[],
        rejected_families=[], isolation_boxes=0, root_tolerance=root_tolerance,
        distance_tolerance_km=distance_tolerance, max_isolation_boxes_per_layer=max_boxes,
        near_tie_time_tolerance_s=1e-9, implementation_status='isolated nonmonotone extension',
        certificate_basis='Exact binary64-derived rational coefficients; reused outward interval root isolation',
        time_ordering='Ordinary floating-point evaluation; candidate enumeration is distinct from interval-certified time ranking',
        topology_basis='Direct, one outward turn, or accessible critical guide; repeated excursions admit a strictly earlier feasible shortcut')
    if (len(source) != 3 or len(receiver) != 3 or len(depths) != len(speeds) or len(depths) < 2 or
            not all(math.isfinite(float(x)) for x in list(depths) + list(speeds) + list(source) + list(receiver)) or
            any(b <= a for a, b in zip(depths, depths[1:])) or any(v <= 0 for v in speeds)):
        result['unresolved'].append(dict(reason='Require finite endpoints, increasing depths and positive velocities'))
        return result
    if bounds is not None:
        if (len(bounds) != 3 or any(len(pair) != 2 for pair in bounds) or
                any(not math.isfinite(float(x)) for pair in bounds for x in pair) or
                any(pair[1] < pair[0] for pair in bounds) or
                tuple(map(float, bounds[2])) != (float(depths[0]), float(depths[-1]))):
            result['unresolved'].append(dict(reason='Closed box normal interval must equal the profile domain'))
            return result
        if any(not bounds[d][0] <= p[d] <= bounds[d][1] for d in range(3) for p in (source, receiver)):
            result['unresolved'].append(dict(reason='Endpoint outside finite box'))
            return result
    profile = [(Q(float(z)), Q(float(v))) for z, v in zip(depths, speeds)]
    zs, zr = Q(float(source[2])), Q(float(receiver[2]))
    if min(zs, zr) < profile[0][0] or max(zs, zr) > profile[-1][0]:
        result['unresolved'].append(dict(reason='Endpoint outside finite normal domain'))
        return result
    result['finite_normal_domain_km'] = [float(profile[0][0]), float(profile[-1][0])]
    dx, dy = receiver[0] - source[0], receiver[1] - source[1]
    r = math.hypot(dx, dy)
    distance, vs, vr = Q(r), velocity(profile, zs), velocity(profile, zr)

    def add(kind, u, time, predicted, normal_sign, turn=None, certificate=None, **extra):
        p = 0. if u is None else 1. / float(u)
        normal = 1. / float(vs) if u is None else math.sqrt(float(u * u - vs * vs)) / float(u * vs)
        candidate = dict(kind=kind, time_s=time, p_s_per_km=p,
            source_derivative_s_per_km=[-p * dx / r if r else 0., -p * dy / r if r else 0., -normal_sign * normal],
            distance_residual_km=predicted - r, turning_depth_km=float(turn) if turn is not None else None,
            certificate=certificate)
        if u is not None:
            # Retain the parameter used in the rational leg calculation. Using
            # 1 / rounded p in a later sampler can lose a near-critical offset.
            candidate['phase_velocity_exact_ratio'] = [str(u.numerator), str(u.denominator)]
        candidate.update(extra)
        result['candidates'].append(candidate)

    shallow, deep = min(zs, zr), max(zs, zr)
    sign = (zr > zs) - (zr < zs)
    if not r:
        add('vertical_direct', None, leg(profile, shallow, deep)[1], 0., sign,
            certificate='Every path action is at least integral slowness times absolute normal displacement')
        if zs == zr:
            result['candidates'][0]['source_derivative_s_per_km'] = None
    else:
        # Equal endpoint speeds alone do not imply a constant intervening region.
        constant_interval = vs == vr and maximum(profile, shallow, deep) == vs and all(
            v == vs for z, v in profile if shallow < z < deep)
        if shallow == deep:
            constant_interval = any(va == vb and a <= shallow <= b
                for (a, va), (b, vb) in zip(profile, profile[1:]))
        if constant_interval:
            length = math.hypot(r, float(zr - zs))
            result['candidates'].append(dict(kind='flat_direct', time_s=length / float(vs),
                p_s_per_km=r / (float(vs) * length), turning_depth_km=None,
                source_derivative_s_per_km=[(source[d] - receiver[d]) / (float(vs) * length) for d in range(3)],
                distance_residual_km=0., certificate='Whole intervening interval has constant velocity'))
        elif shallow < deep:
            vmax = maximum(profile, shallow, deep)
            limit = distance_limit(profile, shallow, deep, vmax)
            relation = compare_limit(distance, limit)
            if relation is None:
                result['unresolved'].append(dict(reason='Direct distance indistinguishable from a critical limit'))
            elif relation <= 0:
                try:
                    if relation == 0:
                        u = vmax
                    else:
                        # X decreases with delta=u-vmax. Exact rational addition
                        # preserves offsets too small to store in k=p*vmax near 1.
                        def value(delta):
                            if delta == 0:
                                return math.inf if limit == math.inf else float(limit.hi if isinstance(limit, Interval) else limit) - r
                            return leg(profile, shallow, deep, vmax + Q(delta))[0] - r
                        upper = float(vmax)
                        while value(upper) > 0:
                            upper *= 2
                            if not math.isfinite(upper):
                                raise ArithmeticError('Direct offset bracket overflow')
                        delta = brentq(value, 0., upper, xtol=float(np.nextafter(0., 1.)), rtol=4 * np.finfo(float).eps)
                        u = vmax + Q(delta)
                    x, time = leg(profile, shallow, deep, u)
                    add('direct', u, time, x, sign, certificate='Strictly increasing direct distance in p; full interval speed bound')
                except (ArithmeticError, ValueError) as error:
                    result['unresolved'].append(dict(reason='Direct-root arithmetic unresolved', exception=str(error)))

        for direction in (1, -1):
            oriented = profile if direction == 1 else [(-z, v) for z, v in reversed(profile)]
            os, ore = direction * zs, direction * zr
            for index, ((a, va), (b, vb)) in enumerate(zip(oriented, oriented[1:])):
                if vb <= va or b < max(os, ore):
                    continue
                spec = turning_spec(oriented, os, ore, index)
                if spec['span'] < 0:
                    result['rejected_families'].append(dict(kind='turning', direction=direction, layer=index,
                        reason='A preceding velocity maximum blocks this turning layer'))
                    continue
                roots, unresolved, boxes = turning_roots(spec, distance, root_tolerance, max_boxes)
                result['isolation_boxes'] += boxes
                result['unresolved'] += [dict(direction=direction, layer=index, r_interval=q,
                    reason='Turning root count or tangency unresolved') for q in unresolved]
                for lo, hi, certificate in roots:
                    if hi < 0 or Q(lo) ** 2 > spec['span']:
                        continue
                    middle = (lo + hi) / 2
                    if Q(middle) ** 2 == spec['span'] and point_sign(spec, middle, distance) == 0:
                        u = spec['upper']
                    elif middle == 0:
                        u = spec['u0']
                    elif lo < 0 or Q(hi) ** 2 > spec['span']:
                        result['unresolved'].append(dict(direction=direction, layer=index, r_interval=[lo, hi],
                            reason='Root overlaps a turning-layer boundary'))
                        continue
                    else:
                        u = Q(math.sqrt(float(spec['u0'] ** 2 + Q(middle) ** 2)))
                    if u < spec['u0'] or u > spec['upper']:
                        result['unresolved'].append(dict(direction=direction, layer=index,
                            reason='Turning velocity rounded outside its interval'))
                        continue
                    turn = a + (u - va) * (b - a) / (vb - va)
                    x1, t1 = leg(oriented, os, turn, u)
                    x2, t2 = leg(oriented, ore, turn, u)
                    add('turning', u, t1 + t2, x1 + x2, direction, direction * turn,
                        certificate, direction=direction, oriented_layer=index, root_interval=[lo, hi])

        guides = [(profile[0][0], 'lower_boundary'), (profile[-1][0], 'upper_boundary')]
        guides += [(z, 'critical_maximum_or_plateau') for k, (z, v) in enumerate(profile[1:-1], 1)
                   if profile[k - 1][1] <= v and profile[k + 1][1] <= v]
        for depth, kind in guides:
            u = velocity(profile, depth)
            if any(maximum(profile, endpoint, depth) > u for endpoint in (zs, zr)):
                result['rejected_families'].append(dict(kind=kind, depth_km=float(depth),
                    reason='Intervening faster material blocks critical legs'))
                continue
            limits = [distance_limit(profile, min(endpoint, depth), max(endpoint, depth), u) for endpoint in (zs, zr)]
            if any(q == math.inf for q in limits):
                result['rejected_families'].append(dict(kind=kind, depth_km=float(depth),
                    reason='Positive-width constant critical-speed leg has infinite transverse distance'))
                continue
            relation = compare_limit(distance, limits[0] + limits[1])
            if relation is None:
                result['unresolved'].append(dict(reason='Critical guide length has unresolved sign', depth_km=float(depth)))
            elif relation >= 0:
                x1, t1 = leg(profile, min(zs, depth), max(zs, depth), u)
                x2, t2 = leg(profile, min(zr, depth), max(zr, depth), u)
                extra = max(0., r - x1 - x2)  # its exact sign was established above
                add(kind, u, t1 + t2 + extra / float(u), r, (depth > zs) - (depth < zs), depth,
                    'Accessible tangent legs and certified nonnegative guide in the finite box', horizontal_guide_length_km=extra)

    result['complete'] = not result['unresolved']
    candidates = result['candidates']
    result['reference_valid'] = result['complete'] and bool(candidates) and all(
        math.isfinite(c['time_s']) and abs(c['distance_residual_km']) <= distance_tolerance for c in candidates)
    if candidates:
        best = min(range(len(candidates)), key=lambda n: candidates[n]['time_s'])
        result['first_arrival'] = candidates[best] if result['reference_valid'] else None
        result['best_enumerated_candidate'] = candidates[best]
        result['near_ties'] = [n for n, c in enumerate(candidates) if abs(c['time_s'] - candidates[best]['time_s']) <= 1e-9]
    else:
        result['first_arrival'] = None
    return result
