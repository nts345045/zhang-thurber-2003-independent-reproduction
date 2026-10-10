#!/usr/bin/env python3
"""Check the joint normal variation of the retained two-contact guide edge."""
import argparse
import csv
from fractions import Fraction as Q
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def feasible(a, b):
    mass = a + b
    return 0 <= mass <= 1 and mass*mass/2 <= b <= mass-mass*mass/2


def positive_integral(a, b):
    if a <= 0 and b <= 0:
        return Q(0)
    if a >= 0 and b >= 0:
        return (a+b)/2
    return a*a/(2*(a-b)) if a > 0 else b*b/(2*(b-a))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='data/development/loma_geometry_preflight/row005_straighten_review/result.json')
    args = parser.parse_args()
    out = (ROOT/args.output).resolve()
    out.relative_to(ROOT)
    if out.exists():
        parser.error('Preserve existing evidence; choose a fresh --output path')
    base = ROOT/'data/development/loma_geometry_preflight/row005_straighten001'
    manifest = json.loads((base/'summary.json').read_text())
    if manifest['status'] != 'completed':
        raise ValueError('Candidate run is incomplete')
    hashes = {}
    for name, digest in manifest['output_sha256'].items():
        path = base/name
        if sha(path) != digest:
            raise ValueError('Candidate artifact changed: '+name)
        hashes[str(path.relative_to(ROOT))] = digest
    hashes[str((base/'summary.json').relative_to(ROOT))] = sha(base/'summary.json')
    grid = list(csv.DictReader((base/'truth_grid.csv').open()))
    levels = sorted({(Q(float(r['x'])), Q(float(r['v']))) for r in grid})
    if dict(levels).get(Q(0)) != 6 or dict(levels).get(Q(1)) != 4 or any(v != 6 for x,v in levels if x < 0):
        raise ValueError('The stated normal slowness jump changed')
    cases = []
    for path in sorted(base.glob('spacing*/result.csv')):
        rows = list(csv.DictReader(path.open()))
        original, straight, optimized = rows
        if [r['stage'] for r in rows] != ['original','straightened','branch_optimized']:
            raise ValueError('Unexpected stages')
        length = Q(float(optimized['guide_length_km']))
        c = length/18
        # Reported full gradients include the chosen right-side guide partial
        # c/2 at each end. Remove it to recover the regular-leg contributions.
        ga = Q(float(optimized['guide_start_full_gradient_x']))-c/2
        gb = Q(float(optimized['guide_end_full_gradient_x']))-c/2
        a, b = -ga/c, -gb/c
        mass = a+b
        cases.append(dict(variant=path.parent.name, diagnostic_row=optimized['diagnostic_row'],
                          exact_straightening_reduction_s=float(original['exact_action_s'])-float(straight['exact_action_s']),
                          exact_branch_optimization_reduction_s=float(straight['exact_action_s'])-float(optimized['exact_action_s']),
                          restricted_gradient_s_per_km=float(optimized['restricted_gradient_s_per_km']),
                          existing_restricted_1e_minus7_flag=float(optimized['restricted_gradient_s_per_km'])<1e-7,
                          guide_length_km=float(length), normal_slowness_jump_s_per_km2=1/18,
                          regular_leg_normal_gradients_s_per_km=[float(ga),float(gb)],
                          required_subgradient_moments=[float(a),float(b)],
                          moment_margins=[float(mass),float(1-mass),float(b-mass*mass/2),float(mass-mass*mass/2-b)],
                          retained_two_contact_normal_certificate=feasible(a,b)))
    # Independent coordinate tests pass at (A,B)=(0,1/2), but a coupled motion
    # has negative first variation: I(-3,1)-B=-3/8.
    a, b = Q(0), Q(1,2)
    coordinate = [positive_integral(x,y)-a*x-b*y for x,y in [(Q(1),Q(0)),(Q(-1),Q(0)),(Q(0),Q(1)),(Q(0),Q(-1))]]
    joint = positive_integral(Q(-3),Q(1))-b
    checks = dict(zero_moments_valid=feasible(Q(0),Q(0)),
                  uniform_half_subgradient_valid=feasible(Q(1,4),Q(1,4)),
                  full_right_subgradient_valid=feasible(Q(1,2),Q(1,2)),
                  separate_coordinates_can_miss_descent=all(q>=0 for q in coordinate) and joint==Q(-3,8) and not feasible(a,b))
    result = dict(scope='Algebraic joint-normal certificate for each retained guide edge only; not full-path stationarity',
                  command='PYTHONDONTWRITEBYTECODE=1 python3 '+str(Path(__file__).resolve().relative_to(ROOT))+' --output '+str(out.relative_to(ROOT)),
                  formula='D(a,b)=gA*a+gB*b+(L/18)*integral_0^1 max((1-t)*a+t*b,0)dt',
                  certificate='With A=-gA/(L/18), B=-gB/(L/18), m=A+B: 0<=m<=1 and m^2/2<=B<=m-m^2/2. These are the attainable moments of any measurable theta(t) in[0,1].',
                  arithmetic='Inequalities use exact rational arithmetic on supplied binary64 length/gradient values. This does not interval-certify numerical regular-leg gradients.',
                  invented_checks=checks, cases=cases, input_sha256=hashes,
                  source_sha256=sha(Path(__file__).resolve()),
                  limitations=['All four restricted smooth gradients still exceed the existing1e-7 criterion; the joint-normal result does not override them.',
                               'Only two normal endpoint motions of the retained guide edge are tested. Restoring internal guide knots changes the admissible coupled directions.',
                               'This certificate neither proves a first arrival nor certifies the continuum guide branch or its source sensitivities.'])
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(invented_checks=checks,cases=cases),indent=2))
    if not all(checks.values()):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
