#!/usr/bin/env python3
"""Check stale-reference rejection with invented geometry, plus saved full-run parity."""
import copy
import hashlib
import json
from pathlib import Path
import shutil

from compare_hayward_1d_support import ROOT, cached_references, sha


def main():
    out = ROOT / 'data/development/reference_cache_controls_001'
    if out.exists():
        raise ValueError('Preserve prior checks; use a fresh output directory')
    out.mkdir(parents=True)
    cache, data = out / 'cache', out / 'data'
    (cache / 'inputs').mkdir(parents=True)
    (cache / 'source').mkdir()
    data.mkdir()
    source = out / 'invented_reference_module.py'
    source.write_text('# Invented module identity fixture; no scientific computation.\n')
    module = cache / 'source' / source.name
    shutil.copyfile(str(source), str(module))
    files = ['initial_events.csv', 'stations.csv', 'initial_grid.csv', 'observations.csv']
    for name in files:
        for parent in (data, cache / 'inputs'):
            (parent / name).write_text('invented_fixture,identity\n0,control\n')
    first = dict(time_s=1., source_derivative_s_per_km=[.1, .2, .3])
    entry = dict(row='0', observation_row='0', event='0', station='0',
                 reference=dict(complete=True, reference_valid=True, first_arrival=first,
                                candidates=[first], near_ties=[0]))
    ref = cache / 'references.jsonl'

    def write_reference(record):
        ref.write_text(json.dumps(record) + '\n')

    write_reference(entry)
    summary = dict(status='complete', rays=1,
        input_sha256={str((cache / 'inputs' / name).relative_to(ROOT)): sha(cache / 'inputs' / name) for name in files},
        output_sha256={str(p.relative_to(ROOT)): sha(p) for p in (ref, module)})

    def write_summary(record):
        (cache / 'summary.json').write_text(json.dumps(record, indent=2) + '\n')

    write_summary(summary)
    baseline = {p: p.read_bytes() for p in out.rglob('*') if p.is_file()}
    results = []

    def reset():
        for path, content in baseline.items():
            path.write_bytes(content)

    def check(name, mutate, reject=True):
        reset()
        mutate()
        try:
            values, verified = cached_references(cache, data, source)
        except ValueError as error:
            if not reject:
                raise
            results.append(dict(name=name, passed=True, rejected=True, message=str(error)))
        else:
            if reject:
                raise AssertionError('Failed to reject ' + name)
            assert values == [entry] and len(verified) == 7
            results.append(dict(name=name, passed=True, rejected=False))

    check('identical_complete_reference', lambda: None, reject=False)
    for name in files:
        check('changed_current_' + name, lambda name=name: (data / name).write_text('different fixture\n'))
    check('changed_cached_geometry', lambda: (cache / 'inputs' / files[0]).write_text('changed\n'))
    check('changed_maintained_module', lambda: source.write_text('# Changed\n'))
    check('changed_cached_module', lambda: module.write_text('# Changed\n'))
    check('changed_candidate_bytes', lambda: ref.write_text('{}\n'))
    changed = dict(summary, status='unresolved_cases_preserved')
    check('unresolved_cache_status', lambda: write_summary(changed))
    check('candidate_count_mismatch', lambda: write_summary(dict(summary, rays=2)))

    def candidate_change(key, value):
        record = copy.deepcopy(entry)
        record['reference'][key] = value
        write_reference(record)
        header = copy.deepcopy(summary)
        header['output_sha256'][str(ref.relative_to(ROOT))] = sha(ref)
        write_summary(header)

    for key, value in [('complete', False), ('reference_valid', False), ('near_ties', [0, 1]),
                       ('first_arrival', None), ('first_arrival', dict(first, source_derivative_s_per_km=None))]:
        check('reject_' + key + '_' + str(value), lambda key=key, value=value: candidate_change(key, value))
    reset()
    # The full real-data replay must preserve every original CSV byte and candidate.
    old = ROOT / 'data/development/hayward_first_arrival_003_1d_support'
    new = ROOT / 'data/development/hayward_cached_reference_check_001'
    replay = json.loads((new / 'summary.json').read_text())
    independent = json.loads((old / 'independent_review.json').read_text())
    for name in ('comparison.csv', 'references.jsonl'):
        assert sha(old / name) == sha(new / name), name
    for label in ('all', 'local_flag_true', 'local_flag_false'):
        for key in ('count', 'time_limit_pass', 'source_vector_limit_pass', 'both_limits_pass'):
            assert replay['accuracy'][label][key] == independent['groups'][label][key], (label, key)
    assert replay['accuracy']['all']['count'] == 14262
    assert replay['accuracy']['all']['both_limits_pass'] == 603
    results.append(dict(name='full_14262_replay_bytes_and_norm_counts', passed=True))
    frozen = out / 'source'
    frozen.mkdir()
    for p in (Path(__file__).resolve(), ROOT / 'diagnostics/compare_hayward_1d_support.py'):
        shutil.copyfile(str(p), str(frozen / p.name))
    record = dict(status='passed', checks=results,
        scope='Invented cache rejection controls and byte-identical full 003 replay; no ray/reference rerun',
        replay_summary_sha256=sha(new / 'summary.json'),
        original_independent_review_sha256=sha(old / 'independent_review.json'),
        full_reference_count=14262,
        output_sha256={str(p.relative_to(out)): sha(p) for p in out.rglob('*') if p.is_file()})
    (out / 'summary.json').write_text(json.dumps(record, indent=2) + '\n')
    print('Passed {} cache/replay checks'.format(len(results)))


if __name__ == '__main__':
    main()
