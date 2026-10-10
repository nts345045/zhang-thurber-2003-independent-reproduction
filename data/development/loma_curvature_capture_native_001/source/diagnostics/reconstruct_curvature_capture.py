#!/usr/bin/env python3
"""Reconstruct exact rational sums of captured binary64 curvature components."""
import argparse
import csv
from fractions import Fraction
import gzip
import hashlib
import itertools
import json
import math
from pathlib import Path


def need(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            digest.update(block)
    return digest.hexdigest()


def records(path):
    opener = gzip.open if path.suffix == '.gz' else open
    with opener(str(path), 'rt', newline='') as stream:
        for row in csv.DictReader(stream):
            yield row


def key(row):
    return (row['run_id'], row['observation_index'], int(row['iteration']))


def binary(value):
    number = float(value)
    need(math.isfinite(number), 'Nonfinite captured component/scalar')
    return number, Fraction.from_float(number)


def exact_pair(pair, components):
    """No action or gradient reevaluation; all fractions describe saved doubles."""
    zero = Fraction(0)
    dot, absolute_products, ss, yy, actual_dot, displacement_difference = [zero] * 6
    rounded_dot = 0.0
    different = 0
    dimension = 0
    for node, row in enumerate(components, 1):
        need(key(row) == key(pair) and int(row['node']) == node, 'Component identity/order mismatch')
        for axis in 'xyz':
            sf, s = binary(row['s_' + axis])
            yf, y = binary(row['y_' + axis])
            unused, actual = binary(row['rounded_displacement_' + axis])
            rounded_dot += sf * yf
            product = s * y
            dot += product
            absolute_products += abs(product)
            ss += s * s
            yy += y * y
            actual_dot += actual * y
            displacement_difference += (actual - s) ** 2
            different += actual != s
            dimension += 1
    need(dimension == int(pair['components']), 'Incomplete captured pair components')
    computed, exact_computed = binary(pair['computed_sy'])
    threshold, exact_threshold = binary(pair['threshold'])
    retained = pair['retained'] == '1'
    need(pair['retained'] in ('0', '1') and retained == (computed > threshold), 'Recorded retention differs from original rule')
    base, exact_base = binary(pair['base_action_s'])
    accepted, exact_accepted = binary(pair['accepted_action_s'])
    step, exact_step = binary(pair['step'])
    slope, exact_slope = binary(pair['directional_slope'])
    rhs, exact_rhs = binary(pair['armijo_rhs_s'])
    exact_declared_bound = exact_base + Fraction.from_float(1e-4) * exact_step * exact_slope
    return dict(run_id=pair['run_id'], observation_index=pair['observation_index'], iteration=pair['iteration'],
                update=pair['update'], retained=pair['retained'], components=dimension,
                computed_sy=pair['computed_sy'], rounded_dot_reconstruction=repr(rounded_dot),
                rounded_dot_matches_computed=int(rounded_dot == computed),
                exact_stored_s_dot_y=str(dot), exact_stored_s_dot_y_sign=(dot > 0) - (dot < 0),
                exact_actual_displacement_dot_y=str(actual_dot), exact_actual_displacement_dot_y_sign=(actual_dot > 0) - (actual_dot < 0),
                exact_dot_minus_computed_sy=str(dot-exact_computed), exact_binary64_threshold=str(exact_threshold),
                exact_dot_exceeds_binary64_threshold=int(dot > exact_threshold),
                exact_s_squared=str(ss), exact_y_squared=str(yy), exact_sum_absolute_products=str(absolute_products),
                exact_normalized_cancellation_ratio=str(dot/absolute_products) if absolute_products else '',
                rounded_displacement_different_components=different,
                exact_displacement_difference_squared=str(displacement_difference),
                exact_difference_of_recorded_action_totals=str(exact_accepted-exact_base),
                recorded_binary64_armijo_pass=int(accepted <= rhs),
                rhs_binary64_reconstruction_matches=int(rhs == base + 1e-4*step*slope),
                exact_declared_recorded_total_armijo_margin=str(exact_declared_bound-exact_accepted),
                exact_declared_recorded_total_armijo_pass=int(exact_accepted <= exact_declared_bound),
                exact_rhs_rounding_error=str(exact_rhs-exact_declared_bound))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pairs', required=True)
    parser.add_argument('--components', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    pairs, components, out = map(lambda value: Path(value).resolve(), (args.pairs, args.components, args.output))
    root = Path.cwd().resolve()
    for path in (pairs, components, out, Path(__file__).resolve()):
        path.relative_to(root)
    need(not out.exists() and pairs != out and components != out, 'Fresh output directory required')
    pins = {str(path.relative_to(root)): sha(path) for path in (pairs, components, Path(__file__).resolve())}
    out.mkdir(parents=True)
    groups = itertools.groupby(records(components), key)
    seen = set()
    counts = dict(pairs=0, rounded_dot_mismatches=0, computed_positive_rejected=0,
                  exact_stored_dot_positive_rejected=0, exact_actual_dot_positive_rejected=0,
                  exact_stored_dot_nonpositive_retained=0, stored_s_differs_from_actual_displacement=0,
                  recorded_binary64_armijo_failures=0, exact_declared_recorded_total_armijo_failures=0)
    with (out / 'exact_sums.csv').open('w', newline='') as stream:
        writer = None
        for pair in records(pairs):
            group_key, entries = next(groups, (None, None))
            need(group_key == key(pair) and group_key not in seen, 'Missing, duplicate or unsorted component group')
            seen.add(group_key)
            result = exact_pair(pair, entries)
            if writer is None:
                writer = csv.DictWriter(stream, fieldnames=list(result), lineterminator='\n')
                writer.writeheader()
            writer.writerow(result)
            rejected = result['retained'] == '0'
            counts['pairs'] += 1
            counts['rounded_dot_mismatches'] += not result['rounded_dot_matches_computed']
            counts['computed_positive_rejected'] += rejected and float(result['computed_sy']) > 0
            counts['exact_stored_dot_positive_rejected'] += rejected and result['exact_stored_s_dot_y_sign'] > 0
            counts['exact_actual_dot_positive_rejected'] += rejected and result['exact_actual_displacement_dot_y_sign'] > 0
            counts['exact_stored_dot_nonpositive_retained'] += not rejected and result['exact_stored_s_dot_y_sign'] <= 0
            counts['stored_s_differs_from_actual_displacement'] += result['rounded_displacement_different_components'] > 0
            counts['recorded_binary64_armijo_failures'] += not result['recorded_binary64_armijo_pass']
            counts['exact_declared_recorded_total_armijo_failures'] += not result['exact_declared_recorded_total_armijo_pass']
        need(writer is not None and next(groups, None) is None, 'Empty pairs or trailing components')
    for name, digest in pins.items():
        need(sha(root / name) == digest, 'Input changed during rational reconstruction')
    summary = dict(status='completed_exact_sums_of_saved_binary64_components', input_sha256=pins, counts=counts,
                   output_sha256={'exact_sums.csv': sha(out / 'exact_sums.csv')},
                   interpretation=['Fractions reconstruct the exact algebraic products/sums of saved binary64 values, not continuum curvature.',
                                   'Computed sy and its actual retention decision remain unchanged and are exported alongside reconstructed sums.',
                                   'The actual-displacement dot product uses the separately captured rounded coordinate differences.',
                                   'Recorded-total Armijo margins concern approximate saved totals; they do not certify exact Fermat action changes.',
                                   'Positive curvature alone does not establish an informative or admissible replacement memory pair.'])
    (out / 'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n')
    print(str(out / 'summary.json'), flush=True)


if __name__ == '__main__':
    main()
