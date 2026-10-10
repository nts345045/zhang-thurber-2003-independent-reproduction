"""Invented affine-layer connector diagnostic; not used by production rays.

Coordinates are (horizontal km, depth km), speed km/s. The physical domain
has a finite bottom B. Only g>=0 affine speed vB+g*(z-B) is supported.
"""
import math
from fractions import Fraction as Q


def _atanh_minus_x(x):
    if x >= 0.25:
        return math.atanh(x) - x
    term, total, n = x * x * x / 3, 0.0, 1
    while term:
        updated = total + term
        if updated == total:
            break
        total = updated
        term *= x * x * (2 * n + 1) / (2 * n + 3)
        n += 1
    return total


def _asinhc_minus_one(x):
    if abs(x) >= 0.125:
        return math.asinh(x) / x - 1
    total, term, n = 0.0, 1.0, 1
    while term:
        term *= -x * x * (2 * n - 1) ** 2 / (2 * n * (2 * n + 1))
        updated = total + term
        if updated == total:
            break
        total = updated
        n += 1
    return total


def connector(a, b, bottom, bottom_speed, gradient):
    """Return this action and both endpoint derivatives, without optimizing knots.

    Branch membership uses exact rational values of the supplied binary64
    inputs. Arithmetic values/derivatives remain ordinary floating point.
    The stable excess is relative to horizontal distance / bottom_speed.
    No general 3D or nodal-grid Jacobian is supplied.
    """
    values = tuple(a) + tuple(b) + (bottom, bottom_speed, gradient)
    if not all(math.isfinite(x) for x in values):
        raise ValueError('Finite inputs required')
    aq, bq = tuple(map(Q, a)), tuple(map(Q, b))
    B, V, g = Q(bottom), Q(bottom_speed), Q(gradient)
    ea, eb = B - aq[1], B - bq[1]
    vaq, vbq = V - g * ea, V - g * eb
    if g < 0 or V <= 0 or min(ea, eb) < 0 or min(vaq, vbq) <= 0:
        raise ValueError('Require g>=0, positive speeds and endpoints inside bottom')
    rq = abs(bq[0] - aq[0])
    if rq == 0 and aq[1] == bq[1]:
        raise ValueError('Coincident endpoints have no unique derivative')
    R, dz = float(rq), float(aq[1] - bq[1])
    D = math.hypot(R, dz)
    sign = 1.0 if bq[0] > aq[0] else (-1.0 if bq[0] < aq[0] else 0.0)
    if g == 0:
        ga = (-sign * R / (bottom_speed * D), dz / (bottom_speed * D))
        excess = dz * dz / ((D + R) * bottom_speed)
        return dict(branch='homogeneous', time_s=D / bottom_speed,
                    excess_s=excess, source=ga, receiver=tuple(-x for x in ga),
                    guide_length_km=None, critical_distance_km=None)

    # R >= sqrt(A)+sqrt(C), without rounded square-root boundary decisions.
    A = ea * (2 * V - g * ea) / g
    C = eb * (2 * V - g * eb) / g
    left = rq * rq - A - C
    comparison = left * left - 4 * A * C
    guided = left >= 0 and comparison >= 0
    critical = guided and comparison == 0
    va, vb = float(vaq), float(vbq)
    da, db = float(g * ea / V), float(g * eb / V)
    qa = math.sqrt(da * (2 - da))
    qb = math.sqrt(db * (2 - db))
    distance = math.sqrt(float(A)) + math.sqrt(float(C))
    if guided:
        excess = (_atanh_minus_x(qa) + _atanh_minus_x(qb)) / gradient
        length = (0.0 if critical else float(comparison) /
                  ((float(left) + 2 * math.sqrt(float(A * C))) * (R + distance)))
        return dict(branch='critical' if critical else 'guide',
                    time_s=R / bottom_speed + excess, excess_s=excess,
                    source=(-sign / bottom_speed, -qa / va),
                    receiver=(sign / bottom_speed, -qb / vb),
                    guide_length_km=length, critical_distance_km=distance)

    K = math.sqrt(va * vb)
    w = gradient * D / (2 * K)
    correction = _asinhc_minus_one(w)
    H = math.hypot(K, gradient * D / 2)
    ga = (-sign * R / (D * H), dz / (D * H) - gradient * D / (2 * va * H))
    gb = (sign * R / (D * H), -dz / (D * H) - gradient * D / (2 * vb * H))
    # Rationalize D-R and vB-sqrt(va*vb); do not subtract nearly equal totals.
    delta = da + db - da * db
    excess = (dz * dz / ((D + R) * K) +
              R * delta / (K * (1 + math.sqrt(1 - delta))) +
              D / K * correction)
    return dict(branch='interior', time_s=D / K * (1 + correction),
                excess_s=excess, source=ga, receiver=gb,
                guide_length_km=None, critical_distance_km=distance)
