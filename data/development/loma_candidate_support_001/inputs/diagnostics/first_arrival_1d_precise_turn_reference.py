"""Diagnostic variant: rational turning speed for nondecreasing linear v(z).

The original first_arrival_1d_reference.py remains unchanged. Only turning
candidate reconstruction and its optional rational sampler metadata differ.
No production solver is imported. Inputs are numerical geometry, not provider
records. ``complete`` concerns branch enumeration; ``reference_valid`` also
requires the returned distance residuals to meet the stated numerical limit.
Unresolved interval/tangency cases are returned explicitly, never hidden.
"""
import math
from fractions import Fraction as Q

import numpy as np
from scipy.optimize import brentq


def down(x):
    return float(np.nextafter(x, -np.inf))


def up(x):
    return float(np.nextafter(x, np.inf))


class Interval:
    """Outward binary64 bounds; sqrt assumes correctly rounded IEEE sqrt."""
    def __init__(self, lo, hi=None):
        self.lo, self.hi = float(lo), float(lo if hi is None else hi)

    @staticmethod
    def of(x):
        if isinstance(x, Interval):
            return x
        if isinstance(x, Q):
            f = float(x)
            return Interval(down(f) if Q(f) > x else f,
                            up(f) if Q(f) < x else f)
        return Interval(x)

    def __add__(self, other):
        b = Interval.of(other)
        return Interval(down(self.lo + b.lo), up(self.hi + b.hi))

    __radd__ = __add__

    def __neg__(self):
        return Interval(-self.hi, -self.lo)

    def __sub__(self, other):
        return self + -Interval.of(other)

    def __rsub__(self, other):
        return Interval.of(other) + -self

    def __mul__(self, other):
        b = Interval.of(other)
        values = [a * c for a in (self.lo, self.hi) for c in (b.lo, b.hi)]
        return Interval(down(min(values)), up(max(values)))

    __rmul__ = __mul__

    def __truediv__(self, other):
        b = Interval.of(other)
        if b.lo <= 0 <= b.hi:
            raise ArithmeticError("Interval division includes zero")
        return self * Interval(down(1 / b.hi), up(1 / b.lo))

    def __rtruediv__(self, other):
        return Interval.of(other) / self

    def __pow__(self, n):
        if n == 2:
            lo = 0 if self.lo <= 0 <= self.hi else down(min(self.lo ** 2, self.hi ** 2))
            return Interval(lo, up(max(self.lo ** 2, self.hi ** 2)))
        if n < 1 or not isinstance(n, int):
            raise ValueError("Only positive integer interval powers are used")
        result = self
        for unused in range(n - 1):
            result = result * self
        return result

    def sqrt(self):
        if self.lo < 0:
            raise ArithmeticError("Negative square-root interval")
        return Interval(max(0., down(math.sqrt(self.lo))), up(math.sqrt(self.hi)))

    def sign(self):
        return 1 if self.lo > 0 else -1 if self.hi < 0 else None


def integer_sqrt(n):
    if not n:
        return 0
    x = 1 << ((n.bit_length() + 1) // 2)
    while True:
        y = (x + n // x) // 2
        if y >= x:
            return x
        x = y


def sqrt(x):
    if isinstance(x, Interval):
        return x.sqrt()
    if isinstance(x, Q):
        a, b = integer_sqrt(x.numerator), integer_sqrt(x.denominator)
        if a * a != x.numerator or b * b != x.denominator:
            raise ArithmeticError("Square root is not rational")
        return Q(a, b)
    return math.sqrt(x)


def candidate_sqrt_enclosure(value, bits=128):
    """Rational sqrt enclosure with width/sqrt(value) <= 2**(1-bits).

    The scale follows the exact numerator/denominator bit lengths. Integer
    square root and the final squared inequalities use exact integers/Fractions;
    no floating-point or Decimal sqrt enters this candidate reconstruction.
    """
    value = Q(value)
    if value < 0 or not isinstance(bits, int) or bits < 2:
        raise ValueError("Require nonnegative square and at least two precision bits")
    if not value:
        return Q(0), (Q(0), Q(0))
    exponent = (value.numerator.bit_length() - value.denominator.bit_length()) // 2
    quantum = Q(2) ** (exponent - bits)
    scaled = value / (quantum * quantum)
    n = integer_sqrt(scaled.numerator // scaled.denominator)
    lower, upper = n * quantum, (n + 1) * quantum
    if lower * lower == value:
        upper = lower
    if not (lower * lower <= value <= upper * upper and
            (upper - lower) ** 2 <= value * Q(2) ** (2 * (1 - bits))):
        raise ArithmeticError("Rational square-root enclosure failed exact bounds")
    return (lower + upper) / 2, (lower, upper)


def constant(x, variable):
    return Interval.of(x) if isinstance(variable, Interval) else x if isinstance(variable, Q) else float(x)


def velocity(profile, depth):
    for (a, va), (b, vb) in zip(profile, profile[1:]):
        if a <= depth <= b:
            return va + (vb - va) * (depth - a) / (b - a)
    raise ValueError("Endpoint outside depth domain")


def pieces(profile, a, b):
    for (lo, va), (hi, vb) in zip(profile, profile[1:]):
        x, y = max(a, lo), min(b, hi)
        if y > x:
            g = (vb - va) / (hi - lo)
            yield x, y, va + g * (x - lo), va + g * (y - lo), g


def coefficients(profile, start, stop):
    c, k = {}, {}
    for a, b, va, vb, g in pieces(profile, start, stop):
        if g:
            c[va * va] = c.get(va * va, Q(0)) + 1 / g
            c[vb * vb] = c.get(vb * vb, Q(0)) - 1 / g
        else:
            k[va * va] = k.get(va * va, Q(0)) + (b - a) * va
    return c, k


def branch(profile, zs, zr, layer):
    (a, va), (b, vb) = profile[layer:layer + 2]
    g = (vb - va) / (b - a)
    u0 = max(velocity(profile, zs), velocity(profile, zr), va)
    c, k = {}, {}
    for endpoint in (zs, zr):
        cc, kk = coefficients(profile, endpoint, max(endpoint, a))
        for target, source in ((c, cc), (k, kk)):
            for key, value in source.items():
                target[key] = target.get(key, Q(0)) + value
        entry = velocity(profile, max(endpoint, a))
        c[entry * entry] = c.get(entry * entry, Q(0)) + 1 / g
    return dict(layer=layer, u0=u0, upper=vb, span=vb * vb - u0 * u0,
                c0=c.get(u0 * u0, Q(0)), k0=k.get(u0 * u0, Q(0)),
                c=[(u0 * u0 - key, value) for key, value in c.items() if value and key != u0 * u0],
                k=[(u0 * u0 - key, value) for key, value in k.items() if value and key != u0 * u0])


def equation(spec, r, distance):
    """F, F', F'': r=sqrt(u^2-u0^2); multiply X-R by r if singular."""
    c0, k0, target = [constant(q, r) for q in (spec["c0"], spec["k0"], distance)]
    squared = r ** 2
    singular = bool(spec["k0"])
    if singular:
        f, first, second = c0 * squared + k0 - target * r, 2 * c0 * r - target, 2 * c0
    else:
        f, first, second = c0 * r - target, c0, constant(Q(0), r)
    for d, value in spec["c"]:
        d, value = constant(d, r), constant(value, r)
        q = sqrt(squared + d)
        if singular:
            f += value * r * q
            first += value * (2 * squared + d) / q
            second += value * r * (2 * squared + 3 * d) / q ** 3
        else:
            f += value * q
            first += value * r / q
            second += value * d / q ** 3
    for d, value in spec["k"]:
        d, value = constant(d, r), constant(value, r)
        q = sqrt(squared + d)
        if singular:
            f += value * r / q
            first += value * d / q ** 3
            second -= 3 * value * d * r / q ** 5
        else:
            f += value / q
            first -= value * r / q ** 3
            second += value * (2 * squared - d) / q ** 5
    return f, first, second


def point_sign(spec, r, distance, derivative=0):
    try:
        value = equation(spec, Q(r), distance)[derivative]
        return (value > 0) - (value < 0)
    except ArithmeticError:
        return equation(spec, Interval(r), distance)[derivative].sign()


def turning_roots(spec, distance, tolerance, max_boxes):
    """Cover the entire parameter interval; unresolved boxes remain explicit."""
    roots, unresolved = [], []
    end = Interval.of(spec["span"]).sqrt().hi
    # Exact quadratic includes flat-over-affine double roots and tangencies.
    if not spec["c"] and not spec["k"] and spec["c0"] > 0:
        c, k = spec["c0"], spec["k0"]
        if not k:
            r = Interval.of(distance / c)
            roots.append((r.lo, r.hi, "exact_linear"))
        else:
            discriminant = distance * distance - 4 * c * k
            if discriminant == 0:
                r = Interval.of(distance / (2 * c))
                roots.append((r.lo, r.hi, "exact_double_root"))
            elif discriminant > 0:
                large = (Interval.of(distance) + Interval.of(discriminant).sqrt()) / (2 * c)
                small = Interval.of(k) / (c * large)
                roots += [(small.lo, small.hi, "exact_quadratic"),
                          (large.lo, large.hi, "exact_quadratic")]
        return roots, unresolved, 0
    queue, boxes = [(0., end)], 0
    while queue and boxes < max_boxes:
        lo, hi = queue.pop()
        boxes += 1
        f, first, second = equation(spec, Interval(lo, hi), distance)
        if f.sign() is not None:
            continue
        a, b = point_sign(spec, lo, distance), point_sign(spec, hi, distance)
        if first.sign() is not None:
            if a == 0 or b == 0:
                r = lo if a == 0 else hi
                roots.append((r, r, "exact_endpoint_and_monotonicity"))
                continue
            if a is not None and b is not None:
                if a == b:
                    continue
                left, right, sign = lo, hi, a
                while right - left > tolerance:
                    middle = (left + right) / 2
                    s = point_sign(spec, middle, distance)
                    if s == 0:
                        left = right = middle
                        break
                    if s is None:
                        # Preserve the proven sign bracket when arithmetic cannot
                        # decide an almost-zero midpoint; try its two quarters.
                        moved = False
                        for t in ((left + middle) / 2, (middle + right) / 2):
                            ss = point_sign(spec, t, distance)
                            if ss == sign:
                                left, moved = t, True
                            elif ss == -sign:
                                right, moved = t, True
                        if not moved:
                            break
                    elif s == sign:
                        left = middle
                    else:
                        right = middle
                roots.append((left, right, "interval_monotonicity_and_sign_change"))
                continue
        middle = (lo + hi) / 2
        tangent = next((point for point in (lo, middle, hi)
                        if second.sign() is not None and point_sign(spec, point, distance) == 0
                        and point_sign(spec, point, distance, 1) == 0), None)
        if tangent is not None:
            roots.append((tangent, tangent, "exact_tangency_and_convexity"))
            continue
        if hi - lo <= tolerance or middle == lo or middle == hi:
            unresolved.append([lo, hi])
        else:
            queue += [(lo, middle), (middle, hi)]
    unresolved += [list(pair) for pair in queue]
    # Adjacent boxes can prove the same exact endpoint root.
    roots = sorted(set(roots))
    return roots, unresolved, boxes


def leg(profile, a, b, u=None):
    """Positive-depth traversal. u=None is the vertical p=0 limit."""
    x, t = 0., 0.
    for lo, hi, va, vb, g in pieces(profile, a, b):
        h = float(hi - lo)
        if u is None:
            t += math.log1p(float((vb - va) / va)) / float(g) if g else h / float(va)
            continue
        qa, qb = math.sqrt(float(u * u - va * va)), math.sqrt(float(u * u - vb * vb))
        if g:
            x += float((vb - va) * (vb + va) / g) / (qa + qb)
            # Split the log ratio into two positive log1p terms. Form delta-v
            # before conversion, and rationalize qa-qb, to retain the flat limit.
            delta_q = float((vb - va) * (vb + va)) / (qa + qb)
            t += (math.log1p(float((vb - va) / va)) +
                  math.log1p(delta_q / (float(u) + qb))) / float(g)
        elif not qa:
            return math.inf, math.inf
        else:
            x += h * float(va) / qa
            t += h * float(u / va) / qa
    return x, t


def distance_limit(profile, a, b, u):
    """Exact rational sign when possible, outward interval otherwise."""
    def calculate(interval):
        total = Interval(0) if interval else Q(0)
        for lo, hi, va, vb, g in pieces(profile, a, b):
            qa2, qb2 = u * u - va * va, u * u - vb * vb
            qa = sqrt(Interval.of(qa2) if interval else qa2)
            qb = sqrt(Interval.of(qb2) if interval else qb2)
            if g:
                total += (qa - qb) / g
            elif not qa2:
                return math.inf
            else:
                total += (hi - lo) * va / qa
        return total
    try:
        return calculate(False)
    except ArithmeticError:
        return calculate(True)


def compare_limit(distance, value):
    if isinstance(value, Interval):
        return 1 if distance > value.hi else -1 if distance < value.lo else None
    return (distance > value) - (distance < value)


def enumerate_arrivals(depths, speeds, source, receiver, root_tolerance=1e-12,
                       distance_tolerance=1e-8, max_boxes=20000):
    """Return all certified candidates and explicit unresolved/unsupported cases.

    Depth increases downward. The horizontal model is unbounded, or any convex
    rectangle containing both endpoints. Arithmetic treats input binary64 values
    (including computed horizontal distance) as exact numerical inputs.
    """
    result = dict(complete=False, reference_valid=False, candidates=[], unresolved=[],
                  root_tolerance=root_tolerance, distance_tolerance_km=distance_tolerance,
                  isolation_boxes=0, max_isolation_boxes_per_layer=max_boxes,
                  certificate_basis="Exact rational coefficients from binary64 inputs; outward interval arithmetic and exact rational special cases",
                  near_tie_time_tolerance_s=1e-9,
                  time_ordering="Ordinary floating-point action evaluation; branch count is certified, but no interval bound on minimum-time ordering is claimed")
    if (len(source) != 3 or len(receiver) != 3 or len(depths) != len(speeds) or len(depths) < 2 or
            not all(math.isfinite(float(x)) for x in list(depths) + list(speeds) + list(source) + list(receiver)) or
            any(b <= a for a, b in zip(depths, depths[1:])) or
            any(v <= 0 for v in speeds) or any(b < a for a, b in zip(speeds, speeds[1:]))):
        result["unresolved"].append(dict(reason="Unsupported profile: require finite increasing depths and positive nondecreasing velocities"))
        return result
    profile = [(Q(float(z)), Q(float(v))) for z, v in zip(depths, speeds)]
    zs, zr = Q(float(source[2])), Q(float(receiver[2]))
    if min(zs, zr) < profile[0][0] or max(zs, zr) > profile[-1][0]:
        result["unresolved"].append(dict(reason="Endpoint outside finite depth domain"))
        return result
    dx, dy = receiver[0] - source[0], receiver[1] - source[1]
    r = math.hypot(dx, dy)
    distance = Q(r)
    vs, vr = velocity(profile, zs), velocity(profile, zr)

    def add(kind, u, time, predicted, sigma, turn=None, certificate=None):
        p = 0. if u is None else 1 / float(u)
        vertical = (1 / float(vs) if u is None else
                    math.sqrt(float(u * u - vs * vs)) / float(u * vs))
        gradient = [-p * dx / r if r else 0., -p * dy / r if r else 0., -sigma * vertical]
        candidate = dict(kind=kind, time_s=time, p_s_per_km=p,
                         source_derivative_s_per_km=gradient,
                         distance_residual_km=predicted - r,
                         turning_depth_km=None if turn is None else float(turn),
                         certificate=certificate)
        result["candidates"].append(candidate)

    shallow, deep = min(zs, zr), max(zs, zr)
    sigma = (zr > zs) - (zr < zs)
    if not r:
        time = leg(profile, shallow, deep)[1]
        add("vertical_direct", None, time, 0., sigma)
        if zs == zr:
            result["candidates"][0]["source_derivative_s_per_km"] = None
        result.update(complete=True, reference_valid=True, first_arrival=result["candidates"][0], near_ties=[0])
        return result
    flat_container = vs == vr and (shallow < deep or any(
        va == vb and a <= shallow <= b for (a, va), (b, vb) in zip(profile, profile[1:])))
    if flat_container:
        length = math.hypot(r, float(zr - zs))
        candidate = dict(kind="flat_direct", time_s=length / float(vs),
                         p_s_per_km=r / (float(vs) * length),
                         source_derivative_s_per_km=[(source[i] - receiver[i]) / (float(vs) * length) for i in range(3)],
                         distance_residual_km=0., turning_depth_km=None,
                         certificate="Straight path contained in one constant-velocity interval")
        result["candidates"].append(candidate)
    elif shallow < deep:
        vd = max(vs, vr)
        limit = distance_limit(profile, shallow, deep, vd)
        relation = compare_limit(distance, limit)
        if relation is None:
            result["unresolved"].append(dict(reason="Direct-branch distance is indistinguishable from its grazing limit"))
        elif relation <= 0:
            if relation == 0:
                u = vd
            else:
                def value(k):
                    if k == 0:
                        return -r
                    if k == 1:
                        return math.inf if limit == math.inf else float(limit.hi if isinstance(limit, Interval) else limit) - r
                    return leg(profile, shallow, deep, vd / Q(k))[0] - r
                k = brentq(value, 0., 1., xtol=float(np.nextafter(0., 1.)),
                           rtol=4 * np.finfo(float).eps)
                u = vd / Q(k)
            x, time = leg(profile, shallow, deep, u)
            add("direct", u, time, x, sigma, certificate="Strictly increasing direct distance in p")
    for index, ((a, va), (b, vb)) in enumerate(zip(profile, profile[1:])):
        if vb <= va or b < deep:
            continue
        spec = branch(profile, zs, zr, index)
        if spec["span"] < 0:
            continue
        roots, unresolved, boxes = turning_roots(spec, distance, root_tolerance, max_boxes)
        result["isolation_boxes"] += boxes
        result["unresolved"] += [dict(layer=index, r_interval=q, reason="Root count or tangency unresolved") for q in unresolved]
        for lo, hi, certificate in roots:
            if hi < 0 or Q(lo) ** 2 > spec["span"]:
                continue
            middle = (lo + hi) / 2
            squared_u = spec["u0"] ** 2 + Q(middle) ** 2
            enclosure = None
            if Q(middle) ** 2 == spec["span"] and point_sign(spec, middle, distance) == 0:
                u = spec["upper"]
            elif middle == 0:
                u = spec["u0"]
            elif lo < 0 or Q(hi) ** 2 > spec["span"]:
                result["unresolved"].append(dict(layer=index, r_interval=[lo, hi], reason="Root overlaps a turning-layer boundary"))
                continue
            else:
                u, enclosure = candidate_sqrt_enclosure(squared_u)
            if u < spec["u0"] or u > spec["upper"]:
                result["unresolved"].append(dict(layer=index, r_interval=[lo, hi], reason="Turning velocity rounded outside its interval"))
                continue
            turn = a + (u - va) * (b - a) / (vb - va)
            x1, t1 = leg(profile, zs, turn, u)
            x2, t2 = leg(profile, zr, turn, u)
            add("turning", u, t1 + t2, x1 + x2, 1, turn, certificate)
            if enclosure is None:
                enclosure = (u, u)
            result["candidates"][-1].update(layer=index, root_interval=[lo, hi],
                u_rational=str(u), turning_depth_rational=str(turn),
                turning_u_squared_rational=str(squared_u),
                turning_u_enclosure_rational=[str(q) for q in enclosure],
                turning_u_enclosure_relative_bits=128)
    # Every accessible plateau top is a grazing horizontal family. The bottom
    # is another such constrained family, even when its final gradient is >0.
    guides = [(profile[-1][0], "bottom_boundary")]
    guides += [(a, "plateau_grazing") for (a, va), (b, vb) in zip(profile, profile[1:])
               if va == vb and a >= deep]
    for depth, kind in guides:
        if depth < deep:
            continue
        u = velocity(profile, depth)
        limits = [distance_limit(profile, endpoint, depth, u) for endpoint in (zs, zr)]
        if any(q == math.inf for q in limits):
            continue
        limit = limits[0] + limits[1]
        relation = compare_limit(distance, limit)
        if relation is None:
            result["unresolved"].append(dict(reason="Grazing horizontal length has unresolved sign", depth_km=float(depth)))
        elif relation >= 0:
            x1, t1 = leg(profile, zs, depth, u)
            x2, t2 = leg(profile, zr, depth, u)
            extra = max(0., r - x1 - x2)  # exact sign was established above
            add(kind, u, t1 + t2 + extra / float(u), r, 1, depth,
                "Tangent legs plus a proven nonnegative horizontal interval")
            result["candidates"][-1]["horizontal_guide_length_km"] = extra
    result["complete"] = not result["unresolved"]
    # Identical limiting rays at adjacent layers are retained with both labels;
    # retaining duplicates cannot remove a branch or alter the minimum.
    candidates = result["candidates"]
    result["reference_valid"] = result["complete"] and bool(candidates) and all(
        math.isfinite(c["time_s"]) and abs(c["distance_residual_km"]) <= distance_tolerance for c in candidates)
    if candidates:
        best = min(range(len(candidates)), key=lambda n: candidates[n]["time_s"])
        result["first_arrival"] = candidates[best] if result["reference_valid"] else None
        result["best_enumerated_candidate"] = candidates[best]
        result["near_ties"] = [n for n, c in enumerate(candidates)
                               if abs(c["time_s"] - candidates[best]["time_s"]) <= 1e-9]
    return result


def sample_path(depths, speeds, source, receiver, candidate, spacing_km=.25):
    """Analytic branch samples with exact endpoints, knots, and turn/guide depth.

    Positive-gradient pieces use equal angle increments on the circular arc;
    flat pieces and horizontal guides use equal distance increments.
    """
    if spacing_km <= 0:
        raise ValueError("Path spacing must be positive")
    profile = [(Q(float(z)), Q(float(v))) for z, v in zip(depths, speeds)]
    source, receiver = list(source), list(receiver)
    r = math.hypot(receiver[0] - source[0], receiver[1] - source[1])
    if candidate["kind"] in ("flat_direct", "vertical_direct"):
        corners = [(0., source), (1., receiver)]
        if source[2] != receiver[2]:
            for knot in depths:
                t = (knot - source[2]) / (receiver[2] - source[2])
                if 0 < t < 1:
                    point = [a + (b - a) * t for a, b in zip(source, receiver)]
                    point[2] = knot
                    corners.append((t, point))
        corners.sort(key=lambda item: item[0])
        points = [source]
        for (unused, a), (unused, b) in zip(corners, corners[1:]):
            length = math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))
            n = max(1, int(math.ceil(length / spacing_km)))
            points += [[x + (y - x) * i / n for x, y in zip(a, b)] for i in range(1, n)] + [b]
        points[0], points[-1] = source, receiver
        return points
    p = candidate["p_s_per_km"]
    rational_parameters = "u_rational" in candidate
    u_exact = Q(candidate["u_rational"]) if rational_parameters else Q(1 / p)
    u = float(u_exact)

    def downleg(start, stop):
        points, offset = [(0., start)], 0.
        start_q = Q(start) if rational_parameters else Q(float(start))
        stop_q = Q(stop) if rational_parameters else Q(float(stop))
        for a, b, va, vb, g in pieces(profile, start_q, stop_q):
            qa_squared = u_exact ** 2 - (va if rational_parameters else Q(float(va))) ** 2
            qb_squared = u_exact ** 2 - (vb if rational_parameters else Q(float(vb))) ** 2
            delta_v = float(vb - va)
            a, b, va, vb, g = map(float, (a, b, va, vb, g))
            # Clip only computed critical-angle roundoff to its mathematical domain;
            # root closure is recorded separately in the candidate residual.
            qa = math.sqrt(max(0., float(qa_squared)))
            qb = math.sqrt(max(0., float(qb_squared)))
            ta = math.atan2(va, qa)
            if g:
                radius = u / g
                # tan((theta_b-theta_a)/2)=(vb-va)/(qa+qb). The chord
                # formula avoids subtracting nearly equal angles/large centers.
                angle = 2 * math.atan2(delta_v, qa + qb)
                n = max(1, int(math.ceil(radius * angle / spacing_km)))
                for i in range(1, n + 1):
                    half = angle * i / (2 * n)
                    chord = 2 * radius * math.sin(half)
                    points.append((offset + chord * math.sin(ta + half),
                                   b if i == n else a + chord * math.cos(ta + half)))
            else:
                vertical_cosine = math.cos(ta)
                length = (b - a) / vertical_cosine
                n = max(1, int(math.ceil(length / spacing_km)))
                width = length * math.sin(ta)
                points += [(offset + width * i / n, b if i == n else a + (b - a) * i / n)
                           for i in range(1, n + 1)]
            offset = points[-1][0]
        return points

    zs, zr = source[2], receiver[2]
    if candidate["kind"] == "direct":
        flat = downleg(min(zs, zr), max(zs, zr))
        if zs > zr:
            total = flat[-1][0]
            flat = [(total - x, z) for x, z in reversed(flat)]
    else:
        depth = Q(candidate["turning_depth_rational"]) if rational_parameters else candidate["turning_depth_km"]
        left, right = downleg(zs, depth), downleg(zr, depth)
        extra = candidate.get("horizontal_guide_length_km", 0.)
        flat = left
        n = max(1, int(math.ceil(extra / spacing_km)))
        if extra:
            flat += [(left[-1][0] + extra * i / n, depth) for i in range(1, n + 1)]
        total = left[-1][0] + right[-1][0]  # left includes the guide after extension
        flat += [(total - x, z) for x, z in list(reversed(right))[1:]]
    points = [[source[0] + x * (receiver[0] - source[0]) / r,
               source[1] + x * (receiver[1] - source[1]) / r, z] for x, z in flat]
    points[0], points[-1] = source, receiver
    return points
