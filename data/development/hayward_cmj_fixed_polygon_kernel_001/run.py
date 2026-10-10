#!/usr/bin/env python3
"""One frozen compile/eight-polygon evaluation, then saved-oracle comparison."""
import csv
import datetime
from decimal import Decimal
from fractions import Fraction as Q
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
LIFECYCLE = ROOT/'data/development/hayward_cmj_tangent_step_001/run.py'


def require(ok, message):
    if not ok: raise ValueError(message)


def now(): return datetime.datetime.utcnow().isoformat()+'Z'


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''): h.update(block)
    return h.hexdigest()


def read(path):
    with (gzip.open(str(path), 'rt') if path.suffix == '.gz' else path.open()) as stream:
        return json.load(stream)


def encoded(value):
    if isinstance(value, Q): return str(value)
    if isinstance(value, dict): return {k: encoded(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)): return [encoded(v) for v in value]
    return value


def save(path, value):
    data = (json.dumps(encoded(value), indent=2, sort_keys=True, allow_nan=False)+'\n').encode('utf8')
    with path.open('xb') as stream:
        if path.suffix == '.gz':
            with gzip.GzipFile(fileobj=stream, mode='wb', mtime=0) as packed: packed.write(data)
        else: stream.write(data)


def hex_rational(token):
    """Parse the complete binary significand; never narrow extended values."""
    match = re.fullmatch(r'([+-]?)0x([0-9a-fA-F]+)(?:\.([0-9a-fA-F]*))?p([+-]?\d+)', token)
    require(match is not None, 'Finite hexadecimal value required')
    sign, whole, fraction, exponent = match.groups(); fraction = fraction or ''
    value = Q(int(whole+fraction, 16)) * Q(2)**(int(exponent)-4*len(fraction))
    return -value if sign == '-' else value


def number(row, key, binary64=False):
    value = hex_rational(row[key+'_hex'])
    decimal = Decimal(row[key]); require(decimal.is_finite(), 'Finite decimal output')
    # The decimal is a convenience display. Hex is the authoritative value.
    require(abs(Q(decimal)-value) <= Q(10)**decimal.as_tuple().exponent/2,
            'Decimal display does not round from the exact emitted hex')
    if binary64:
        require(float(row[key]).hex() == float.fromhex(row[key+'_hex']).hex()
                and Q(float(row[key])) == value, 'Binary64 decimal/hex round trip')
    return value


def bounds(value):
    lo, hi = map(Q, value); require(lo <= hi, 'Ordered oracle enclosure'); return lo, hi


def error(value, oracle):
    lo, hi = bounds(oracle); low, high = value-hi, value-lo
    return dict(value_exact=value, oracle_bounds=(lo, hi), error_bounds=(low, high),
                distance_to_enclosure=Q(0) if low <= 0 <= high else min(abs(low), abs(high)),
                absolute_error_upper=max(abs(low), abs(high)))


def table(name):
    with (HERE/'results'/name).open(newline='') as stream: return list(csv.DictReader(stream))


def compare(oracle):
    totals = table('totals.csv'); edges = table('edges.csv'); gradients = table('gradients.csv'); pairs = table('pairs.csv')
    require(len(totals) == 8 and len(edges) == 8232 and len(gradients) == 24672 and len(pairs) == 4,
            'Exact output inventories')
    edge_map = {}; gradient_map = {}; reports = []; details = []
    for polygon, row in zip(oracle['polygons'], totals):
        key = (polygon['event'], polygon['stage_integer']); count = polygon['node_count']
        require((int(row['event']), int(row['stage'])) == key and int(row['station']) == 160
                and int(row['nodes']) == count, 'Native polygon output order')
        selected = [r for r in edges if (int(r['event']), int(r['stage'])) == key]
        require(len(selected) == count-1 and [int(r['edge']) for r in selected] == list(range(count-1)), 'Ordered edge outputs')
        actual = [number(r, 'action', True) for r in selected]; edge_map[key] = actual
        expected = polygon['action']['edges']; require([r['edge'] for r in expected] == list(range(count-1)), 'Oracle edge order')
        edge_errors = [dict(edge=i, emitted_hex=selected[i]['action_hex'], **error(v, expected[i]['bounds'])) for i, v in enumerate(actual)]
        values = [r for r in gradients if (int(r['event']), int(r['stage'])) == key]
        require([(int(r['node']), int(r['axis'])) for r in values] == [(i, k) for i in range(1, count-1) for k in range(3)], 'Free component order')
        require(all(int(r['station']) == 160 for r in selected+values), 'Native receiver outputs')
        actual_gradient = {(int(r['node']), int(r['axis'])): number(r, 'component', True) for r in values}
        gradient_map[key] = actual_gradient
        component_errors = []; derivative = polygon['derivatives']
        if derivative['status'] == 'reviewed_available_internal_components':
            require([r['node'] for r in derivative['component_bounds']] == list(range(1, count-1)), 'Oracle free-node order')
            for item in derivative['component_bounds']:
                for axis, enclosure in enumerate(item['components']):
                    if enclosure is not None:
                        component_errors.append(dict(node=item['node'], axis=axis,
                            **error(actual_gradient[item['node'], axis], enclosure)))
        else:
            require(derivative['status'] == 'unavailable' and not derivative.get('component_bounds'), 'No invented derivative oracle')
        squared_lower = sum((r['distance_to_enclosure']**2 for r in component_errors), Q(0))
        squared_upper = sum((r['absolute_error_upper']**2 for r in component_errors), Q(0))
        actions = {name: error(number(row, name, name != 'extended_sum'), polygon['action']['full_bounds'])
                   for name in ('action', 'ordinary_sum', 'extended_sum')}
        report = dict(event=key[0], station=160, stage=polygon['stage'], node_count=count,
            action_comparisons=actions, exact_sum_of_emitted_binary64_edges=sum(actual, Q(0)),
            extended_accumulation_error=number(row, 'extended_sum')-sum(actual, Q(0)),
            largest_edge_distance=max(v['distance_to_enclosure'] for v in edge_errors),
            largest_edge_absolute_error_upper=max(v['absolute_error_upper'] for v in edge_errors),
            derivative_oracle_status=derivative['status'], available_component_count=len(component_errors),
            derivative_error_norm_squared_bounds=(squared_lower, squared_upper) if component_errors else None,
            largest_component_distance=max((v['distance_to_enclosure'] for v in component_errors), default=None),
            path_eval_microseconds=Decimal(row['path_eval_microseconds']).to_eng_string(),
            extra_edge_checks_and_output_microseconds=Decimal(row['edge_check_microseconds']).to_eng_string(),
            original_convergence_flag='0', candidate_convergence_status=None)
        reports.append(report); details.append(dict(report, edges=edge_errors, available_components=component_errors))
    pair_reports = []
    for expected, row in zip(oracle['pairs'], pairs):
        event = expected['event']; stage = 2 if expected['to_stage'] == 'second' else 3
        require(int(row['event']) == event and int(row['station']) == 160 and int(row['base_stage']) == 1
                and int(row['trial_stage']) == stage, 'Native pair order')
        alpha = Q(float(row['alpha'])); require(alpha == Q(float.fromhex(expected['alpha_hex'])), 'Same saved fraction')
        paired = number(row, 'paired'); exact_edges = sum((a-b for a, b in zip(edge_map[event, stage], edge_map[event, 1])), Q(0))
        saved_rhs = Q(expected['Armijo_rhs_lower']); cpp_rhs = number(row, 'extended_armijo_rhs')
        slope = number(row, 'slope', True); extended_slope = number(row, 'extended_slope')
        direction_file = HERE/expected['direction_file']
        require(sha(direction_file) == expected['direction_sha256'], 'Saved direction hash')
        tokens = direction_file.read_text().split(); n = len(gradient_map[event, 1])//3+2
        require(list(map(int, tokens[:3])) == [event, 160, n] and len(tokens) == 3+3*n, 'Complete direction input')
        q = [Q(float(x)) for x in tokens[3:]]
        exact_slope = sum((gradient_map[event, 1][node, axis]*q[3*node+axis]
                           for node in range(1, n-1) for axis in range(3)), Q(0))
        cpp_pass = slope < 0 and paired <= cpp_rhs
        require(int(row['paired_armijo']) == int(cpp_pass), 'Emitted Armijo decision')
        pair_reports.append(dict(event=event, station=160, from_stage='first', to_stage=expected['to_stage'], alpha=alpha,
            paired_comparison=error(paired, expected['paired_difference']),
            exact_sum_of_binary64_edge_differences=exact_edges, paired_accumulation_error=paired-exact_edges,
            outer_rounded_total_difference=number(row, 'outer_change', True),
            slope_comparison=error(slope, expected['nominal_slope']), extended_slope_comparison=error(extended_slope, expected['nominal_slope']),
            exact_sum_of_binary64_gradient_direction_products=exact_slope, extended_slope_accumulation_error=extended_slope-exact_slope,
            saved_armijo_rhs_lower=saved_rhs, cpp_armijo_rhs=cpp_rhs,
            paired_passes_saved_slope_bound=paired <= saved_rhs, paired_passes_cpp_slope=cpp_pass,
            oracle_armijo=expected['conservative_nominal_armijo'], oracle_status=expected['status'],
            agrees_with_oracle=cpp_pass == expected['conservative_nominal_armijo']))
    save(HERE/'results/comparison_details.json.gz', dict(native_contexts=oracle['native_contexts'], polygons=details, pairs=pair_reports))
    return dict(polygons=reports, pairs=pair_reports,
                interpretation='Errors and decision agreement on fixed saved polygons; no stationarity, first-arrival or production-accuracy certificate.')


def main():
    prepared = read(HERE/'prepared.json'); approval = read(HERE/'prelaunch_review.json')
    require(approval['status'] == 'passed' and approval['prepared_sha256'] == sha(HERE/'prepared.json'), 'Root prelaunch review required')
    def verify():
        for base, pins in ((ROOT, prepared['input_sha256']), (HERE, prepared['output_sha256'])):
            for name, digest in pins.items(): require(sha(base/name) == digest, 'Changed pin: '+name)
        for name, digest in prepared['runtime_sha256'].items(): require(sha(name) == digest, 'Changed runtime: '+name)
        require(sha(sys.executable) == prepared['python']['sha256'], 'Changed Python executable')
    verify(); oracle = read(HERE/'oracle.json.gz'); os.environ.update(prepared['environment'])
    require(not any((HERE/name).exists() for name in ('execution.json', 'summary.json', 'results', 'build', 'logs')), 'Fresh execution paths required')
    spec = importlib.util.spec_from_file_location('frozen_lifecycle', str(LIFECYCLE))
    lifecycle = importlib.util.module_from_spec(spec); spec.loader.exec_module(lifecycle)
    for name in ('results', 'build', 'logs'): (HERE/name).mkdir()
    # Sidecars precede every derived numeric output, including the input-free logs.
    for name in ('totals.csv', 'edges.csv', 'gradients.csv', 'pairs.csv', 'comparison_details.json.gz'):
        save(HERE/'results'/(name+'.identifiers.json'), dict(native_contexts=oracle['native_contexts'],
            expected_file=str((HERE/'results'/name).relative_to(ROOT)), original_convergence_flag='0',
            candidate_convergence_status=None, prepared_sha256=sha(HERE/'prepared.json'), oracle_sha256=sha(HERE/'oracle.json.gz')))
    for index in (0, 1):
        for suffix in ('stdout', 'stderr'):
            name = 'command_%d.%s' % (index, suffix)
            save(HERE/'logs'/(name+'.identifiers.json'), dict(native_contexts=oracle['native_contexts'],
                expected_file=str((HERE/'logs'/name).relative_to(ROOT)), prepared_sha256=sha(HERE/'prepared.json')))
    ledger = dict(status='running', pid=os.getpid(), started_utc=now(), commands=[], native_contexts=oracle['native_contexts'],
                  prepared_sha256=sha(HERE/'prepared.json'), prelaunch_review_sha256=sha(HERE/'prelaunch_review.json'))
    def update():
        temporary = HERE/'execution.json.new'; temporary.write_text(json.dumps(ledger, indent=2, sort_keys=True)+'\n'); temporary.replace(HERE/'execution.json')
    def interrupted(sig, unused): raise SystemExit(128+sig)
    signal.signal(signal.SIGTERM, interrupted); signal.signal(signal.SIGINT, interrupted)
    update(); unsettled = []; code = 1; result = None
    try:
        for index, command in enumerate(prepared['commands']):
            item = dict(command=command, started_utc=now()); ledger['commands'].append(item); update()
            with (HERE/'logs'/('command_%d.stdout'%index)).open('x') as stdout, (HERE/'logs'/('command_%d.stderr'%index)).open('x') as stderr:
                mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGINT, signal.SIGTERM})
                try: child = subprocess.Popen(command, cwd=str(HERE), env=os.environ.copy(), stdout=stdout, stderr=stderr, start_new_session=True)
                except BaseException:
                    signal.pthread_sigmask(signal.SIG_SETMASK, mask); raise
                item['pid'] = child.pid
                try:
                    signal.pthread_sigmask(signal.SIG_SETMASK, mask); update(); returned = child.wait()
                    if returned != 0 or lifecycle.group_members(child.pid): raise RuntimeError('Child failed or left a live writer')
                except BaseException:
                    cleanup = lifecycle.stop_group(child); item['cleanup'] = cleanup
                    if cleanup['live_members'] or not cleanup['child_reaped']: unsettled.append(cleanup)
                    raise
                finally:
                    item.update(return_code=child.returncode, child_reaped=child.poll() is not None, finished_utc=now()); update()
        require((HERE/'logs/command_1.stdout').read_text().startswith('path_eval_calls=8 extra_segment_calls=8232 trace_calls=0 field_calls=0 optimizer_calls=0'), 'Declared actual call inventory')
        result = compare(oracle); verify(); ledger['status'] = 'completed_fixed_polygon_comparison'; code = 0
    except BaseException as exc:
        if isinstance(exc, SystemExit) and isinstance(exc.code, int): code = exc.code
        ledger.update(status='failed_preserved', error=dict(type=type(exc).__name__, message=str(exc)))
    finally:
        stable = not unsettled and all(c.get('child_reaped') for c in ledger['commands'])
        outputs = {} if not stable else {str(p.relative_to(HERE)): sha(p) for folder in ('results', 'logs', 'build') for p in sorted((HERE/folder).rglob('*')) if p.is_file()}
        summary = dict(status=ledger['status'], error=ledger.get('error'), result=result, native_contexts=oracle['native_contexts'],
            prepared_sha256=sha(HERE/'prepared.json'), output_sha256=outputs, path_eval_calls=8 if result is not None else None,
            extra_segment_calls=8232 if result is not None else None, trace_calls=0, field_calls=0, optimizer_calls=0,
            new_reference_integrations=0, original_convergence_flag='0', candidate_convergence_status=None)
        save(HERE/'summary.json', summary)
        ledger.update(return_code=code, finished_utc=now(), outputs_stable=stable, unsettled_groups=unsettled,
                      summary_sha256=sha(HERE/'summary.json'), output_sha256=outputs); update()
    return code


if __name__ == '__main__': sys.exit(main())
