#!/usr/bin/env python3
"""Full saved-record comparison; no solver or analytical reference evaluation."""
import collections
import csv
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OLD = ROOT / 'data/development/loma_boundary_endpoint_mesh_controls_001'
NEW = HERE / 'results'


def need(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def table(path):
    with path.open(newline='') as stream:
        reader = csv.DictReader(stream)
        return reader.fieldnames, list(reader)


def main():
    output = HERE / 'comparison.json'
    need(not output.exists(), 'Preserve existing comparison')
    pins = {}

    def pin(path, expected=None):
        value = sha(path)
        need(expected is None or expected == value, 'Hash mismatch: ' + str(path))
        pins[str(path.relative_to(ROOT))] = value

    pin(HERE / 'preparation.json', 'f8ae89ae793e169ac15f512d28d4a3e7e343041062068404bdb0971644cde882')
    prepared = read(HERE / 'preparation.json')
    for relative, digest in prepared['input_sha256'].items():
        pin(ROOT / relative, digest)
    for relative, digest in prepared['output_sha256'].items():
        pin(HERE / relative, digest)
    old, new = read(OLD / 'summary.json'), read(NEW / 'summary.json')
    for directory, summary in [(OLD, old), (NEW, new)]:
        pin(directory / 'summary.json')
        need(summary['status'] == 'passed_analytical_contract_controls', 'Controls not terminal/passing')
        need(all(c['return_code'] == 0 and c['status'] == 'completed' for c in summary['commands']),
             'A command did not complete successfully')
        for relative, digest in summary['input_sha256'].items():
            pin(ROOT / relative, digest)
        for relative, digest in summary['artifact_sha256'].items():
            pin(directory / relative, digest)
    need(new['invented_cases'] == old['invented_cases'], 'Invented cases changed')
    need(new['plan_sha256'] == old['plan_sha256'], 'Plan changed')
    need(new['compiler_sha256'] == old['compiler_sha256'], 'Compiler changed')
    need((NEW / 'source/diagnostics/check_endpoint_mesh.cpp').read_bytes() ==
         (OLD / 'source/diagnostics/check_endpoint_mesh.cpp').read_bytes(), 'C++ harness changed')
    need((NEW / 'source/diagnostics/explicit_mesh_trace.hpp').read_bytes() ==
         (HERE / 'preview_explicit_mesh_trace.hpp').read_bytes(), 'Prelaunch trace preview differs')
    need(new['unchanged_optimizer_and_derivative_suffix_sha256'] ==
         prepared['optimizer_and_derivative_suffix_sha256'], 'D optimizer suffix changed')

    cases = []
    for case in new['invented_cases']:
        name = case['name']
        controls = next(c for c in new['controls'] if c['name'] == name)
        prior = next(c for c in old['controls'] if c['name'] == name)
        files = {}
        for basename in ['grid.csv', 'input_path.csv', 'paths.csv', 'parity.csv',
                         'evaluations.csv', 'comparisons.csv']:
            a, b = OLD / name / basename, NEW / name / basename
            af, ar = table(a)
            bf, br = table(b)
            need(af == bf and len(ar) == len(br), 'Row/header roster changed: ' + str(b))
            if basename in ['grid.csv', 'input_path.csv']:
                need(a.read_bytes() == b.read_bytes(), 'Invented input bytes changed')
            changes, columns, maximum = [], collections.Counter(), collections.defaultdict(float)
            for index, (x, y) in enumerate(zip(ar, br)):
                if basename in ['evaluations.csv', 'comparisons.csv', 'paths.csv']:
                    keys = ['run_id', 'observation_index', 'subsegments', 'epsilon_requested_km', 'family']
                    if basename == 'paths.csv':
                        keys.append('node')
                    need(all(x[k] == y[k] for k in keys), 'Ordered row identity changed')
                differences = {k: dict(old=x[k], new=y[k]) for k in af if x[k] != y[k]}
                if differences:
                    item = dict(row_index=index, differing_fields=differences)
                    if 'family' in x:
                        item['identity'] = {k: x[k] for k in
                            ['run_id', 'observation_index', 'subsegments', 'epsilon_requested_km', 'family']}
                    changes.append(item)
                    columns.update(differences.keys())
                    for key in differences:
                        try:
                            u, v = float(x[key]), float(y[key])
                        except ValueError:
                            continue
                        if math.isfinite(u) and math.isfinite(v):
                            maximum[key] = max(maximum[key], abs(u - v))
            files[basename] = dict(rows=len(ar), byte_identical=sha(a) == sha(b),
                old_sha256=sha(a), new_sha256=sha(b), changed_rows=len(changes),
                differing_column_counts=dict(columns), maximum_absolute_numeric_changes=dict(maximum),
                changes=changes)
        _, comparisons = table(NEW / name / 'comparisons.csv')
        optimized = [r for r in comparisons if r['family'] == 'optimized']
        cases.append(dict(name=name, files=files, old_false_flags=prior['optimizer_false_flags'],
            new_false_flags=controls['optimizer_false_flags'],
            old_source_failures=prior['optimized_source_accuracy_failures'],
            new_source_failures=controls['optimized_source_accuracy_failures'],
            optimized_rows=len(optimized),
            maximum_optimized_time_error_s=max(abs(float(r['continuous_time_error_s'])) for r in optimized),
            maximum_optimized_source_norm_error_s_per_km=max(float(r['continuous_source_norm_error_s_per_km'])
                                                          for r in optimized),
            false_flag_rows=[r for r in optimized if r['converged'] == '0'],
            zero_epsilon_optimized_rows=[r for r in optimized if float(r['epsilon_requested_km']) == 0]))
    pin(Path(__file__).resolve())
    for relative, digest in pins.items():
        need(sha(ROOT / relative) == digest, 'Input changed during readback')
    result = dict(status='completed_saved_record_comparison', source_sha256=sha(Path(__file__)),
        input_sha256=pins, cases=cases, total_evaluation_rows=sum(c['files']['evaluations.csv']['rows'] for c in cases),
        evaluation_changed_rows=sum(c['files']['evaluations.csv']['changed_rows'] for c in cases),
        all_non_time_evaluation_fields_equal=all(set(c['files']['evaluations.csv']['differing_column_counts']) <=
                                                {'time_s'} for c in cases),
        all_final_path_files_byte_identical=all(c['files']['paths.csv']['byte_identical'] for c in cases),
        all_parity_files_byte_identical=all(c['files']['parity.csv']['byte_identical'] for c in cases),
        ordinary_explicit_parity_checks=sum(c['files']['parity.csv']['rows'] for c in cases),
        new_analytical_checks=dict(passed=new['passing_checks'], total=new['total_checks']),
        unchanged_source_failure_total=sum(c['new_source_failures'] for c in cases),
        unchanged_false_flag_total=sum(c['new_false_flags'] for c in cases),
        limitations=['Final stored paths/fields and update counts are compared; intermediate optimizer histories were not captured.',
            'D differs from old001 in both outer accumulation and guarded positive curvature; no isolated retention attribution.',
            'Arithmetic/parity checks do not turn failed optimized source comparisons or local flags into passes.',
            'No new native calculation, solver rerun during comparison, physical constraints or stopping changes.'])
    with output.open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ['cases', 'input_sha256', 'limitations']},
                     sort_keys=True))


if __name__ == '__main__':
    main()
