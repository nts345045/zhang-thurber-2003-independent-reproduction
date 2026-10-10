"""Independent exact readback of saved invented controls; no new module import."""
import datetime
from fractions import Fraction as Q
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pair(values):
    lo, hi = map(Q, values)
    assert lo <= hi
    return lo, hi


def plus(a, b):
    return a[0]+b[0], a[1]+b[1]


def times(c, a):
    return (c*a[0], c*a[1]) if c >= 0 else (c*a[1], c*a[0])


def log_bound(x):
    # log(x)=2*atanh((x-1)/(x+1)); retain a rigorous absolute tail.
    z = (x-1)/(x+1)
    power, total = z, Q(0)
    for n in range(256):
        total += 2*power/(2*n+1)
        power *= z*z
        tail = 2*abs(power)/((2*n+3)*(1-z*z))
        if tail < Q(1, 2**180):
            return total-tail, total+tail
    raise ArithmeticError('Independent log budget exhausted')


def main():
    prepared = json.loads((HERE/'prepared.json').read_text())
    summary = json.loads((HERE/'summary.json').read_text())
    execution = json.loads((HERE/'execution.json').read_text())
    data = json.loads((HERE/'results.json').read_text())
    checks = json.loads((HERE/'checks.json').read_text())
    assert summary['status'] == 'passed' and len(checks) == 80
    assert sum(x['passed'] for x in checks) == 80
    assert execution['return_code'] == 0 and execution['child_reaped']
    assert summary['prepared_sha256'] == execution['prepared_sha256'] == sha(HERE/'prepared.json')
    assert summary['prelaunch_review_sha256'] == execution['prelaunch_review_sha256'] == sha(HERE/'prelaunch_review.json')
    for name, digest in prepared['input_sha256'].items():
        assert sha(ROOT/name) == digest, name
    for name, digest in prepared['output_sha256'].items():
        assert sha(HERE/name) == digest, name
    for name, digest in execution['output_sha256'].items():
        assert sha(HERE/name) == digest, name
    records = []

    def encloses(name, saved, reference):
        a, b = pair(saved)
        assert a <= reference[0] <= reference[1] <= b, name
        records.append(dict(name=name, saved=[str(a), str(b)],
                            reference=list(map(str, reference))))

    encloses('constant_action', data['constant']['action']['action'], (Q(5, 6),)*2)
    encloses('constant_endpoint_direction', data['constant']['derivative']['derivative'], (Q(1, 10),)*2)
    a, b = pair(data['constant']['witness']['evaluation']['derivative'])
    assert b < 0 and b*b <= Q(1, 18) <= a*a  # -sqrt(2)/6
    for case in data['reciprocal_affine']:
        slope = case['slope']; va = Q(5 if slope == 1 else 6); vb = va+slope
        encloses('affine_action_'+str(slope), case['action']['action'], times(Q(1, slope), log_bound(vb/va)))
        encloses('affine_source_'+str(slope), case['source']['derivative'], (-1/va,)*2)
        encloses('affine_receiver_'+str(slope), case['receiver']['derivative'], (-1/vb,)*2)
    cubic = data['cubic_and_partition']
    root3 = times(-60, pair(cubic['inward_oracle']))
    assert 0 < root3[0] and root3[0]**2 <= 3 <= root3[1]**2
    primitive = plus(plus(times(Q(1, 2), log_bound(Q(3, 2))),
                          times(-1, log_bound(Q(4, 3)))), times(Q(1, 2), log_bound(Q(5, 4))))
    assert primitive[0] > 0
    encloses('cubic_action', cubic['action']['action'],
             (root3[0]*primitive[0], root3[1]*primitive[1]))
    for name in ('inward', 'crossed_inward'):
        encloses('cubic_'+name, cubic[name]['derivative'], times(Q(-1, 60), root3))
    for case in data['ridge']['cases']:
        truth = Q(1, 72) if case['label'] == 'fast' else Q(-1, 50)
        for number, saved in enumerate(case['variations']+[case['crossing']]):
            encloses(case['label']+'_normal_'+str(number), saved['derivative'], (truth,)*2)
    assert Q(data['ridge']['abstract_component_only']['coupled_value']) == Q(-1, 4)
    assert all(Q(x) > 0 for x in data['ridge']['abstract_component_only']['coordinate_values'])
    variable = data['variable_face']
    jump = variable['changing_jumps'][0]
    assert list(map(Q, jump['jump_numerator'])) == [Q(3, 16), Q(-1), Q(1)]
    assert pair(jump['jump_numerator_bounds']) == (Q(-1, 16), Q(3, 16))
    assert jump['convex_normal_jump'] is False
    # On the recorded z=1/2 two-edge path, the triangular middle-node z
    # direction gives -(4/49)*7*log(49/48) = -(4/7)*log(49/48).
    # This independently includes both edges; no new integration is performed.
    tangent_oracle = times(Q(-4, 7), log_bound(Q(49, 48)))
    encloses('two_adjacent_edge_tangent_closed_form',
             variable['witness']['evaluation']['derivative'], tangent_oracle)
    assert variable['witness']['axis'] == 2
    assert Q(variable['witness']['evaluation']['feasible_step_bound']) > 0
    assert variable['boundary']['status'] == 'no_negative_tangent_witness_resolved'
    failure = data['failure_and_cancellation']
    assert pair(failure['identical']['difference']) == (0, 0)
    assert failure['identical']['changed_edges'] == []
    lo, hi = pair(failure['unresolved']['difference']); assert lo < 0 < hi
    lo, hi = pair(failure['difference']['difference']); assert 0 < lo <= hi
    assert len(failure['difference']['changed_edges']) == 2
    assert float(sum(pair(failure['before']['action']))/2) == float(sum(pair(failure['after']['action']))/2)
    result = dict(status='passed', reviewed_utc=datetime.datetime.utcnow().isoformat()+'Z',
        reviewer='root', checker_sha256=sha(Path(__file__)),
        input_sha256={n:sha(HERE/n) for n in ('prepared.json', 'prelaunch_review.json',
            'execution.json', 'summary.json', 'checks.json', 'results.json')},
        original_pin_checks=7, frozen_pin_checks=8,
        recorded_checks=80, mathematical_checks=65, families=6,
        independent_exact_comparisons=records,
        additional_findings=['Rational squared bounds verify the constant witness and cubic radical.',
            'Whole-interval jump sign, coupled descent, boundary refusal and unresolved/cancellation results preserved.'],
        limits='Saved invented readback only. No native polygon, ray, optimizer, source/model accuracy or stationarity claim.')
    with (HERE/'review.json').open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True); stream.write('\n')
    print(json.dumps(dict(status='passed', exact_comparisons=len(records), review_sha256=sha(HERE/'review.json'))))


if __name__ == '__main__':
    main()
