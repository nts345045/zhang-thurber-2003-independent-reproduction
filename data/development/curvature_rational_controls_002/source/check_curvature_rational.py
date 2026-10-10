#!/usr/bin/env python3
"""Invented cancellation/rounding controls for saved-component rational sums."""
import argparse
import csv
from fractions import Fraction
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    os.chdir(str(ROOT))
    out = (ROOT / args.output).resolve()
    out.relative_to(ROOT)
    if out.exists():
        raise ValueError('Fresh control directory required')
    (out / 'source').mkdir(parents=True)
    pins = {}
    for name in ('reconstruct_curvature_capture.py', 'check_curvature_rational.py'):
        path = ROOT / 'diagnostics' / name
        pins[str(path.relative_to(ROOT))] = sha(path)
        shutil.copyfile(str(path), str(out / 'source' / name))
    source = out / 'source/reconstruct_curvature_capture.py'
    spec = importlib.util.spec_from_file_location('frozen_reconstruction', str(source))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    checks, cases = [], []

    def check(name, passed):
        checks.append(dict(name=name, passed=bool(passed)))
        if not passed:
            raise ValueError('Failed control: ' + name)

    def case(name, s, y, actual=None, base=2., accepted=1., slope=-.25, step=.5):
        actual = s if actual is None else actual
        computed = 0.
        for a, b in zip(s, y):
            computed += a*b
        pair = dict(run_id=name, observation_index='invented_' + name, iteration='0', update='1',
                    retained=str(int(computed > 1e-14)), computed_sy=format(computed, '.17g'),
                    threshold=format(1e-14, '.17g'), components=str(len(s)), step=format(step, '.17g'),
                    base_action_s=format(base, '.17g'), accepted_action_s=format(accepted, '.17g'),
                    directional_slope=format(slope, '.17g'), armijo_rhs_s=format(base+1e-4*step*slope, '.17g'))
        components = []
        for node in range(len(s)//3):
            row = dict(run_id=name, observation_index=pair['observation_index'], iteration='0', node=str(node+1))
            for axis, label in enumerate('xyz'):
                for prefix, values in [('s_', s), ('y_', y), ('rounded_displacement_', actual)]:
                    row[prefix+label] = format(values[3*node+axis], '.17g')
            components.append(row)
        result = module.exact_pair(pair, components)
        cases.append((pair, components, result))
        return result

    try:
        r = case('dyadic', [.5, -.25, .125], [2., -4., 8.])
        check('dyadic_exact_dot_three', Fraction(r['exact_stored_s_dot_y']) == 3)
        check('dyadic_exact_squared_norms', Fraction(r['exact_s_squared']) == Fraction(21,64) and Fraction(r['exact_y_squared']) == 84)
        check('dyadic_no_cancellation', Fraction(r['exact_normalized_cancellation_ratio']) == 1)
        check('dyadic_rounded_movement_identical', r['rounded_displacement_different_components'] == 0)
        r = case('lost_positive_unit', [1e16, 1., -1e16], [1., 1., 1.])
        check('cancelled_binary64_zero_preserved', r['computed_sy'] == '0' and r['rounded_dot_reconstruction'] == '0.0')
        check('cancelled_exact_positive_unit_recovered', Fraction(r['exact_stored_s_dot_y']) == 1 and r['exact_stored_s_dot_y_sign'] == 1)
        check('positive_exact_sum_does_not_override_rejection', r['retained'] == '0' and r['exact_dot_exceeds_binary64_threshold'] == 1)
        r = case('rounded_negative_exact_zero', [1e16, 1., -1e16, -1., 0., 0.], [1.]*6)
        check('negative_computed_dot_exact_zero_distinguished', r['computed_sy'] == '-1' and Fraction(r['exact_stored_s_dot_y']) == 0)
        r = case('rounded_stationary_coordinate', [2.**-54, 0., 0.], [1., 0., 0.], actual=[0., 0., 0.])
        check('stored_step_and_actual_movement_distinguished', Fraction(r['exact_stored_s_dot_y']) == Fraction(1,2**54) and Fraction(r['exact_actual_displacement_dot_y']) == 0)
        check('movement_difference_exact_squared', r['rounded_displacement_different_components'] == 1 and Fraction(r['exact_displacement_difference_squared']) == Fraction(1,2**108))
        # Adjacent binary64 values are created without relying on Python3.9 nextafter.
        import struct
        bits = struct.unpack('>Q', struct.pack('>d', 1e-14))[0]
        for offset, expected in [(-1, False), (0, False), (1, True)]:
            value = struct.unpack('>d', struct.pack('>Q', bits+offset))[0]
            r = case('threshold_' + str(offset+1), [value, 0., 0.], [1., 0., 0.])
            check('binary64_threshold_decision_' + str(offset), bool(int(r['retained'])) == expected and bool(r['exact_dot_exceeds_binary64_threshold']) == expected)
        r = case('signed_zero', [-0., 0., 0.], [1., 1., 1.])
        check('signed_zero_fraction_is_zero', Fraction(r['exact_stored_s_dot_y']) == 0 and r['rounded_dot_matches_computed'] == 1)
        r = case('rounded_armijo_rhs', [1., 0., 0.], [1., 0., 0.], base=1., accepted=1., slope=-2.**-54, step=1.)
        check('rounded_rhs_acceptance_kept', r['recorded_binary64_armijo_pass'] == 1 and r['rhs_binary64_reconstruction_matches'] == 1)
        check('exact_recorded_total_margin_distinguished', r['exact_declared_recorded_total_armijo_pass'] == 0 and Fraction(r['exact_declared_recorded_total_armijo_margin']) < 0)
        pair, components, unused = cases[0]
        for name, change in [('wrong_identity', lambda p,c: c[0].update(observation_index='wrong')),
                             ('wrong_node_order', lambda p,c: c[0].update(node='2')),
                             ('missing_component_inventory', lambda p,c: p.update(components='6')),
                             ('retention_override', lambda p,c: p.update(retained='0')),
                             ('nonfinite_component', lambda p,c: c[0].update(s_x='nan'))]:
            copied_pair, copied_components = dict(pair), [dict(c) for c in components]
            change(copied_pair, copied_components)
            rejected = False
            try:
                module.exact_pair(copied_pair, copied_components)
            except ValueError:
                rejected = True
            check('reject_' + name, rejected)
        for filename, values in [('pairs.csv', [c[0] for c in cases]), ('components.csv', [row for c in cases for row in c[1]])]:
            with (out / filename).open('w', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=list(values[0]), lineterminator='\n')
                writer.writeheader(); writer.writerows(values)
        command = [sys.executable, str(source.relative_to(ROOT)), '--pairs', str((out/'pairs.csv').relative_to(ROOT)),
                   '--components', str((out/'components.csv').relative_to(ROOT)), '--output', str((out/'readback').relative_to(ROOT))]
        with (out/'stdout.log').open('w') as stdout, (out/'stderr.log').open('w') as stderr:
            process = subprocess.run(command, stdout=stdout, stderr=stderr)
        check('frozen_cli_return_zero', process.returncode == 0)
        with (out/'readback/exact_sums.csv').open() as stream:
            saved = list(csv.DictReader(stream))
        check('all_invented_rows_preserved_in_order', [key['run_id'] for key in saved] == [c[0]['run_id'] for c in cases])
        check('all_exact_csv_fields_roundtrip', saved == [{k:str(v) for k,v in c[2].items()} for c in cases])
        manifest = json.loads((out/'readback/summary.json').read_text())
        check('cli_hashes_match', all(sha(ROOT/name) == digest for name,digest in manifest['input_sha256'].items()) and
              sha(out/'readback/exact_sums.csv') == manifest['output_sha256']['exact_sums.csv'])
        with (out/'repeat_stdout.log').open('w') as stdout, (out/'repeat_stderr.log').open('w') as stderr:
            repeated = subprocess.run(command, stdout=stdout, stderr=stderr)
        check('existing_output_rejected', repeated.returncode != 0)
        check('sources_unchanged', all(sha(ROOT/name) == digest for name,digest in pins.items()))
        result = dict(status='passed', command=command, checks=checks, check_count=len(checks), source_sha256=pins,
                      scope='Invented saved binary64 component/scalar controls only; no action evaluation or ray trace',
                      output_sha256={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()})
    except BaseException as error:
        result = dict(status='failed', failure=repr(error), checks=checks, source_sha256=pins)
        raise
    finally:
        (out/'summary.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(str(out/'summary.json'),flush=True)


if __name__ == '__main__':
    main()
