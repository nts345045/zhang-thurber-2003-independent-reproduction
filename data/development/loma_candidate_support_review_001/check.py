#!/usr/bin/env python3
"""Independent physical-xyz Decimal readback of the prescribed support bound."""
import argparse
import csv
from decimal import Decimal as D, localcontext
from fractions import Fraction as Q
import hashlib
import itertools
import json
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[3]
CASE = ROOT / 'data/development/loma_candidate_support_001'


def need(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def dec(q):
    return D(q.numerator) / D(q.denominator)


def bounds(record):
    return Q(record['lower_rational']), Q(record['upper_rational'])


def contains(interval, value):
    return dec(interval[0]) <= value <= dec(interval[1])


def squared(interval):
    a, b = interval
    need(a <= b, 'Reversed interval')
    return (Q(0) if a <= 0 <= b else min(a*a, b*b), max(a*a, b*b))


def product(a, b):
    values = [x*y for x in a for y in b]
    return min(values), max(values)


def add(a, b):
    return a[0]+b[0], a[1]+b[1]


def physical_segment(a, b, profile):
    """Integrate endpoint first variations in xyz; no depth-axis permutation.

    ∂a S = −t∫s du + L∫(1−u)∇s du, ∂b S = t∫s du + L∫u∇s du.
    The sole aligned convex kink uses its lower-depth-side slope (alpha=0).
    """
    a, b = [tuple(map(dec, p)) for p in (a, b)]
    profile = [(dec(z), dec(v)) for z, v in profile]
    delta = tuple(y-x for x, y in zip(a, b))
    length = sum(d*d for d in delta).sqrt()
    need(length > 0, 'Zero edge in independent readback')
    cuts = [D(0), D(1)]
    if delta[2]:
        cuts += [(z-a[2])/delta[2] for z, v in profile if 0 < (z-a[2])/delta[2] < 1]
    cuts = sorted(cuts)
    integral, normal0, normal1 = D(0), D(0), D(0)
    for lo, hi in zip(cuts, cuts[1:]):
        zmid = a[2] + (lo+hi)*delta[2]/2
        layer = next(i for i in range(len(profile)-1)
                     if profile[i][0] <= zmid <= profile[i+1][0])
        z, v = profile[layer]
        zp, vp = profile[layer+1]
        slope = (vp-v)/(zp-z)
        va = v + slope*(a[2]+lo*delta[2]-z)
        vb = v + slope*(a[2]+hi*delta[2]-z)
        B = slope*delta[2]
        width = hi-lo
        if B == 0:
            integral += width/va
            normal0 += -slope*width/(va*va)
            normal1 += -slope*(hi*hi-lo*lo)/(2*va*va)
        else:
            logarithm = (vb/va).ln()
            integral += logarithm/B
            normal0 += -slope*width/(va*vb)
            A = va-B*lo
            normal1 += -slope*(logarithm + A*(1/vb-1/va))/(B*B)
    ga = [-d/length*integral for d in delta]
    gb = [d/length*integral for d in delta]
    ga[2] += length*(normal0-normal1)
    gb[2] += length*normal1
    return length*integral, ga, gb, length


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default=str(Path(__file__).with_name('review.json')))
    args = parser.parse_args()
    output = Path(args.output).resolve()
    output.relative_to(ROOT)
    need(not output.exists(), 'Fresh review output required')
    s = json.loads((CASE / 'summary.json').read_text())
    need(s['status'] == 'completed_prescribed_polygon_support_existence', 'Wrong calculation status')
    for name, digest in s['input_sha256'].items():
        need(sha(ROOT / name) == sha(CASE / 'inputs' / name) == digest, 'Changed input: '+name)
    for name, digest in s['artifact_sha256'].items():
        need(sha(CASE / name) == digest, 'Changed artifact: '+name)
    controls = json.loads((CASE / 'controls.json').read_text())
    need(controls['status'] == 'passed' and len(controls['checks']) == s['controls_passed'] == 25 and
         all(c['passed'] for c in controls['checks']), 'Control result changed')
    table = rows(CASE / 'candidate_support.csv')
    identity = rows(CASE / 'identified_ray.csv')
    need(identity == [s['native_context']], 'Native context changed')
    sidecar = json.loads((CASE / 'candidate_support.csv.identifiers.json').read_text())
    need(sidecar['native_context'] == identity[0] and sidecar['file_sha256'] == sha(CASE / 'candidate_support.csv') and
         sidecar['context_sha256'] == sha(CASE / 'identified_ray.csv'), 'Identity sidecar changed')
    need(len(table) == 1134 and [int(r['node']) for r in table] == list(range(1134)) and
         all(r['observation_index'] == '3426' and r['original_run_id'] == 'fmm_0.031250_1000' for r in table), 'Table join changed')
    points = [tuple(Q(r[a+'_rational']) for a in 'xyz') for r in table]
    native = CASE / 'inputs/data/development/loma_outer_accumulation_native_001'
    old = [r for r in rows(native/'paths.csv') if r['run_id'] == 'fmm_0.031250_1000']
    old_points = [tuple(Q(float(r[a])) for a in 'xyz') for r in old]
    changed = [(i, k) for i in range(1134) for k in range(3) if points[i][k] != old_points[i][k]]
    need(changed == [(484, 2), (485, 2)] and points[484][2] == points[485][2] == 7, 'Candidate changed')
    grid = rows(native/'inputs/initial_grid.csv')
    axes = [sorted({Q(float(r[a])) for r in grid}) for a in 'xyz']
    grid_points = [tuple(Q(float(r[a])) for a in 'xyz') for r in grid]
    need(len(grid_points) == len(set(grid_points)) and set(grid_points) == set(itertools.product(*axes)), 'Grid incomplete')
    profile = sorted({(Q(float(r['z'])), Q(float(r['v']))) for r in grid})
    need(len(profile) == len(axes[2]) and all(v > 0 for z, v in profile), 'Grid not depth-only/positive')
    need(all(axes[k][0] < p[k] < axes[k][-1] for p in points[1:-1] for k in range(3)), 'Internal boundary contact')
    need(points[0] == old_points[0] and points[-1] == old_points[-1], 'Endpoints changed')
    slopes = [(profile[i+1][1]-profile[i][1])/(profile[i+1][0]-profile[i][0]) for i in range(len(profile)-1)]
    aligned = []
    for i, (a, b) in enumerate(zip(points, points[1:])):
        need(a != b, 'Zero-length edge')
        for j in range(1, len(profile)-1):
            if a[2] == b[2] == profile[j][0] and slopes[j] != slopes[j-1]:
                aligned.append((i, j))
    need(aligned == [(484, 3)], 'Extra aligned kink')
    jump = (slopes[2]-slopes[3])/(profile[3][1]**2)
    need(jump > 0 and jump == Q(s['slowness_normal_jump_rational']), 'Nonconstant or wrong jump')
    vectors = {label: [] for label in ('alpha0', 'support')}
    for i, row in enumerate(table):
        endpoint = i in (0, 1133)
        need(int(row['endpoint_fixed']) == endpoint and int(row['normal_cancelled_by_existence']) == (i in (484,485)), 'Role changed')
        for label in vectors:
            vector = []
            for k, a in enumerate('xyz'):
                entries = [row[label+'_'+a+'_'+b+'_rational'] for b in ('lower', 'upper')]
                if endpoint:
                    need(entries == ['', ''], 'Endpoint derivative unexpectedly chosen')
                    continue
                interval = tuple(map(Q, entries))
                need(interval[0] <= interval[1], 'Reversed component enclosure')
                vector.append(interval)
            vectors[label].append(vector)
    for i in range(1, 1133):
        for k in range(3):
            need(vectors['support'][i][k] == ((Q(0),Q(0)) if (i,k) in changed else vectors['alpha0'][i][k]),
                 'Unsupported component change')
    c, a, b = [bounds(s[name]) for name in ('c_s_per_km','target_A_s_per_km','target_B_s_per_km')]
    need(a == tuple(-x for x in reversed(vectors['alpha0'][484][2])) and
         b == tuple(-x for x in reversed(vectors['alpha0'][485][2])), 'Cancellation signs changed')
    mass2 = squared(add(a,b))
    for key, moment in (('feasibility_margin_A', a), ('feasibility_margin_B', b)):
        cp = product(c,moment)
        margin = (2*cp[0]-mass2[1], 2*cp[1]-mass2[0])
        need(margin == bounds(s[key]) and margin[0] > 0 and c[0] > 0, 'Moment feasibility not established')
    for label in vectors:
        total = (Q(0),Q(0))
        for vector in vectors[label][1:-1]:
            for interval in vector:
                total = add(total, squared(interval))
        need(total == bounds(s[label+'_squared_norm']), 'Incomplete norm sum')
        lower, upper = bounds(s[label+'_internal_norm_s_per_km'])
        need(0 <= lower and lower*lower <= total[0] <= total[1] <= upper*upper, 'Norm square root not outward')
    readbacks = []
    for precision in (80, 120):
        with localcontext() as ctx:
            ctx.prec = precision
            action, gradient, length484 = D(0), [[D(0)]*3 for p in points], None
            for i, (a0,b0) in enumerate(zip(points,points[1:])):
                value, ga, gb, length = physical_segment(a0,b0,profile)
                action += value
                for k in range(3):
                    gradient[i][k] += ga[k]
                    gradient[i+1][k] += gb[k]
                if i == 484:
                    length484 = length
            need(contains(bounds(s['action_s']), action), 'Independent action outside enclosure')
            need(contains(c,length484*dec(jump)), 'Independent jump moment scale outside enclosure')
            for i in range(1,1133):
                for k in range(3):
                    need(contains(vectors['alpha0'][i][k], gradient[i][k]), 'Independent gradient outside enclosure '+str((i,k)))
            alpha = sum(g*g for row in gradient[1:-1] for g in row).sqrt()
            gradient[484][2] = gradient[485][2] = D(0)
            support = sum(g*g for row in gradient[1:-1] for g in row).sqrt()
            need(contains(bounds(s['alpha0_internal_norm_s_per_km']),alpha) and
                 contains(bounds(s['support_internal_norm_s_per_km']),support), 'Independent norm outside enclosure')
            readbacks.append(dict(precision=precision, action_s=str(action), alpha0_norm=str(alpha), support_norm=str(support)))
    need(s['original_B_flag_preserved'] == s['original_B_result']['converged'] == '0', 'Original B flag changed')
    result = dict(status='passed', reviewer='root', reviewed_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        summary_sha256=sha(CASE/'summary.json'), checker_sha256=sha(Path(__file__).resolve()),
        verified_inputs=len(s['input_sha256']), verified_artifacts=len(s['artifact_sha256']), controls=25,
        native_context_fields=len(identity[0]), positive_edges=1133, internal_components=3396,
        certified_normal_zero_components=[[484,'z'],[485,'z']], decimal_readbacks=readbacks,
        findings=['Full physical-xyz first variations independently agree with every alpha0 interval at80/120digits.',
                  'The positive constant jump and both strict outward moment margins establish simultaneous cancellation.',
                  'All3396 internal components enter the norm, with exactly the two certified normal components zero.',
                  'Original B geometry/results stay distinct from the prescribed candidate and original false flag is preserved.'],
        limitations=['Decimal agreement is an independent consistency check, not an additional interval proof.',
                     'This is existence of a supporting vector for the prescribed fixed-topology polygon; no minimum-norm or general-model claim.',
                     'No ray solve, source/model derivative update, convergence promotion or inverse result follows.'])
    output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(output=str(output.relative_to(ROOT)),sha256=sha(output),readbacks=readbacks),indent=2))


if __name__ == '__main__':
    main()
