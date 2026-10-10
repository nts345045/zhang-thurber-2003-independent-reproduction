"""Independent analytic straight-edge oracle for v(x)=6+sigma*abs(x).

The split affine action is L*log(B/A)/(B-A). Its endpoint derivatives
use U=(B/A-1-log(B/A))/(B-A)^2 and
V=(log(B/A)+A/B-1)/(B-A)^2. We evaluate these divided differences through
their cancellation-free atanh series below, not through quadrature or the
trilinear reciprocal-integral implementation. All arithmetic is rational;
the length is enclosed by an independently squared-checked integer root.
An aligned x=0 edge has no ordinary normal derivative: its normal slots
remain None. Its true directional variation is a separate contact oracle.
"""
from fractions import Fraction as Q


def require(ok, message):
    if not ok:
        raise ValueError(message)


def add(a, b):
    return a[0] + b[0], a[1] + b[1]


def multiply(a, b):
    values = [x * y for x in a for y in b]
    return min(values), max(values)


def scale(a, value):
    return multiply(a, (value, value))


def integer_root(n):
    require(type(n) is int and n >= 0, 'Nonnegative integer root input')
    if n == 0:
        return 0
    x = 1 << ((n.bit_length() + 1) // 2)
    while True:
        y = (x + n // x) // 2
        if y >= x:
            require(x * x <= n < (x + 1) * (x + 1), 'Integer root squared check')
            return x
        x = y


def length_bounds(delta, bits):
    require(type(bits) is int and bits >= 2, 'Declared positive bound precision')
    square = sum((x * x for x in delta), Q(0))
    require(square > 0, 'Zero-length edge has no ordinary endpoint gradient')
    denominator = 1 << bits
    k = integer_root((square.numerator * denominator * denominator) // square.denominator)
    lo = Q(k, denominator); hi = lo if lo * lo == square else Q(k + 1, denominator)
    require(0 < lo and lo * lo <= square <= hi * hi, 'Positive length enclosure; increase declared bits if unresolved')
    return lo, hi


def affine_moments(a, b, terms):
    """J=int1/v, U=int(1-t)/v^2, V=int t/v^2, local t in [0,1]."""
    a, b = Q(a), Q(b)
    require(a > 0 and b > 0 and type(terms) is int and terms >= 1, 'Positive affine speeds and fixed series count')
    center = (a + b) / 2; z = (b - a) / (b + a)
    require(abs(z) < 1, 'Positive speeds imply convergent atanh series')
    j = sum((z ** (2 * n) / Q(2 * n + 1) for n in range(terms + 1)), Q(0)) / center
    j_tail = abs(z) ** (2 * terms + 2) / (center * (2 * terms + 3) * (1 - z * z))
    difference = sum((Q(2 * m, 2 * m + 1) * z ** (2 * m - 1) for m in range(1, terms + 1)), Q(0)) / (center * center)
    d_tail = abs(z) ** (2 * terms + 1) / (center * center * (1 - z * z))
    # Every omitted term has the sign of z; J's omitted terms are nonnegative.
    db = (difference, difference + d_tail) if z >= 0 else (difference - d_tail, difference)
    total = 1 / (a * b)  # U+V is exact, including the equal-speed limit.
    u = ((total + db[0]) / 2, (total + db[1]) / 2)
    v = ((total - db[1]) / 2, (total - db[0]) / 2)
    return dict(J=(j, j + j_tail), U=u, V=v, S=total, D=db,
                center=center, z=z, J_tail=j_tail, D_absolute_tail=d_tail,
                J_terms=terms + 1, D_terms=terms)


def edge(a, b, sigma, axes, terms=16, bits=128):
    """Action and ordinary endpoint components for one exact binary64/Q edge."""
    a = tuple(map(Q, a)); b = tuple(map(Q, b)); axes = tuple(tuple(map(Q, v)) for v in axes)
    require(len(a) == len(b) == len(axes) == 3 and type(sigma) is int and sigma in (-1, 1), 'Three-dimensional declared affine fixture with exact integer sign')
    require(all(len(v) >= 2 and all(x < y for x, y in zip(v, v[1:])) for v in axes) and Q(0) in axes[0][1:-1], 'Increasing finite grid with internal x=0 face')
    require(all(axes[k][0] <= p[k] <= axes[k][-1] for p in (a, b) for k in range(3)), 'Closed finite-box endpoints')
    require(min(6 + sigma * abs(x) for x in axes[0]) > 0, 'Positive affine fixture throughout the box')
    delta = tuple(y - x for x, y in zip(a, b)); length = length_bounds(delta, bits)
    cuts = {Q(0), Q(1)}
    for k, coordinates in enumerate(axes):
        if delta[k]:
            cuts.update((x - a[k]) / delta[k] for x in coordinates[1:-1] if 0 < (x - a[k]) / delta[k] < 1)
    cuts = sorted(cuts); aligned = a[0] == b[0] == 0
    average = (Q(0), Q(0)); wa = wb = (Q(0), Q(0)); pieces = []
    for left, right in zip(cuts, cuts[1:]):
        width = right - left; xa = a[0] + left * delta[0]; xb = a[0] + right * delta[0]
        middle = (xa + xb) / 2
        require(aligned or middle != 0, 'Every nonaligned open piece lies on one affine side')
        velocity_a, velocity_b = 6 + sigma * abs(xa), 6 + sigma * abs(xb)
        moments = affine_moments(velocity_a, velocity_b, terms)
        average = add(average, scale(moments['J'], width))
        slope = None if aligned else sigma * (1 if middle > 0 else -1)
        ka = scale(add(scale(moments['U'], 1 - left), scale(moments['V'], 1 - right)), width)
        kb = scale(add(scale(moments['U'], left), scale(moments['V'], right)), width)
        if slope is not None:
            wa = add(wa, scale(ka, slope)); wb = add(wb, scale(kb, slope))
        pieces.append(dict(u=(left, right), A=velocity_a, B=velocity_b, velocity_slope_x=slope,
                           global_first_weight=ka, global_last_weight=kb, **moments))
    inverse_length = (1 / length[1], 1 / length[0]); geometry = multiply(average, inverse_length)
    ga = [scale(geometry, -x) for x in delta]; gb = [scale(geometry, x) for x in delta]
    if aligned:
        ga[0] = gb[0] = None
    else:
        ga[0] = add(ga[0], scale(multiply(length, wa), -1))
        gb[0] = add(gb[0], scale(multiply(length, wb), -1))
    return dict(action=multiply(length, average), components=[ga, gb], ordinary_normal=not aligned,
                blocked_axes=[0] if aligned else [], length=length, a_exact=a, b_exact=b,
                pieces=pieces, sigma=sigma, terms=terms, bits=bits,
                interpretation='Analytic split-action derivatives; no ordinary normal assigned on an aligned edge.')


def path(points, sigma, axes, terms=16, bits=128):
    """Fixed-endpoint path sum; aligned normals remain explicitly unavailable."""
    points = [tuple(map(Q, p)) for p in points]
    require(len(points) >= 2, 'Two fixed endpoints required')
    action = (Q(0), Q(0)); components = [[(Q(0), Q(0)) for k in range(3)] for p in points]
    records = []; blocked = set()
    for index, (a, b) in enumerate(zip(points, points[1:])):
        record = edge(a, b, sigma, axes, terms=terms, bits=bits)
        record.update(edge=index, endpoint_nodes=[index, index + 1]); records.append(record)
        action = add(action, record['action'])
        for side, gradient in enumerate(record['components']):
            node = index + side
            if not 0 < node < len(points) - 1:
                continue
            for axis, value in enumerate(gradient):
                if value is None:
                    blocked.add((node, axis))
                else:
                    components[node][axis] = add(components[node][axis], value)
    ordinary = [dict(edge=v['edge'], side=side, node=v['edge'] + side, axis=axis, contribution=value)
                for v in records for side, gradient in enumerate(v['components']) for axis, value in enumerate(gradient)
                if value is not None and (v['edge'] + side, axis) in blocked]
    for node, axis in blocked:
        components[node][axis] = None
    return dict(action=action, internal_components=components[1:-1], edge_records=records,
                blocked_slots=sorted(blocked), ordinary_contributions_in_blocked_slots=ordinary,
                sigma=sigma, terms=terms, bits=bits,
                interpretation='None means an aligned nonsmooth normal, not a zero derivative; ordinary neighboring contributions remain in edge records.')
