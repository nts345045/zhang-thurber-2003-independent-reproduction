#!/usr/bin/env python3
"""Saved-only independent cap-change review; no compilation or ray calls."""
import ast
import datetime
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = ROOT / 'data/development/loma_lon_strict_straight_replay_001'

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()

def main():
    p = json.loads((HERE/'prepared.json').read_text())
    assert sha(HERE/'prepared.json') == '79b62dce3635d2da9b478a63573406fb16f35847984b6c9153f9bfebb0ca4da5'
    counts = {}
    for key, root in [('original_sha256', ROOT), ('runtime_sha256', Path('/')), ('output_sha256', HERE), ('source_sha256', HERE)]:
        for name, expected in p[key].items():
            assert sha(root/name) == expected, (key, name)
        counts[key] = len(p[key])
    oldp = json.loads((BASE/'prepared.json').read_text())
    oldr = json.loads((BASE/'review.json').read_text())
    assert oldr['status'] == 'passed'
    assert p['strict_1000_review_sha256'] == sha(BASE/'review.json') == '981487f2a95910d63790f7415ccb64da25f796c11093cf0d303e8858f1e71af0'
    for name in ('summary', 'execution', 'controller_completion', 'prelaunch_review'):
        assert oldr[name+'_sha256'] == sha(BASE/(name+'.json'))
    assert p['native_pairs'] == [8670,8674] and p['native_calls'] == 2
    assert p['compiler'] == oldp['compiler'] and p['flags'] == oldp['flags']
    expected_settings = dict(oldp['settings'], maximum_updates=4000)
    assert p['settings'] == expected_settings
    oldsource = {str(f.relative_to(BASE/'source/strict')): sha(f) for f in (BASE/'source/strict').rglob('*') if f.is_file()}
    newsource = {str(f.relative_to(HERE/'source/strict')): sha(f) for f in (HERE/'source/strict').rglob('*') if f.is_file()}
    assert oldsource == newsource and len(newsource) == 14
    for f in (BASE/'inputs').rglob('*'):
        if f.is_file() and f.name != 'run.cfg':
            assert f.read_bytes() == (HERE/'inputs'/f.relative_to(BASE/'inputs')).read_bytes()
    config = (BASE/'inputs/run.cfg').read_bytes()
    assert config.count(b'ray_iterations 1000\n') == 1
    assert (HERE/'inputs/run.cfg').read_bytes() == config.replace(b'ray_iterations 1000\n',b'ray_iterations 4000\n')
    driver = (BASE/'driver.cpp').read_bytes()
    assert driver.count(b'config.get("ray_iterations") != 1000') == 1
    assert (HERE/'driver.cpp').read_bytes() == driver.replace(b'config.get("ray_iterations") != 1000',b'config.get("ray_iterations") != 4000')
    for f in (BASE/'results/strict').glob('*.csv'):
        assert f.read_bytes() == (HERE/'inputs/strict_1000'/f.name).read_bytes()
    trees = [ast.parse((f/'run.py').read_text()) for f in (BASE,HERE)]
    unchanged = ['verify','group_members','signal_group','terminate_and_reap','interrupted','command']
    for name in unchanged:
        functions = [[n for n in ast.walk(t) if isinstance(n,ast.FunctionDef) and n.name==name] for t in trees]
        assert [len(x) for x in functions] == [1,1]
        assert ast.dump(functions[0][0]) == ast.dump(functions[1][0]), name
    assert 'MAX_UPDATES = 4000' in (HERE/'run.py').read_text()
    assert "for variant in ('strict',):" in (HERE/'run.py').read_text()
    for name in ('build','logs','results','execution.json','summary.json'):
        assert not (HERE/name).exists(), name
    review = {'status':'passed','reviewer':'scientific_audit',
        'reviewed_utc':datetime.datetime.utcnow().isoformat()+'Z',
        'scope':'Independent saved source/input/hash/prelaunch review only; no compiler, ray, reference, action, network or live-job invocation.',
        'prepared_sha256':sha(HERE/'prepared.json'),'runner_sha256':sha(HERE/'run.py'),
        'driver_sha256':sha(HERE/'driver.cpp'),'checker_sha256':sha(Path(__file__)),
        'strict_1000_review_sha256':sha(BASE/'review.json'),'pin_counts':counts,
        'identical_numerical_source_members':len(newsource),
        'changes':'Only ray_iterations 1000 to 4000 in the copied configuration, with the matching driver validation guard. The strict numerical source is byte-identical; the runner uses the new cap for bookkeeping and adds comparisons with saved1000 outputs.',
        'preserved_lifecycle_functions_ast_equal':unchanged,
        'native_context':json.loads((HERE/'inputs/native_context.json').read_text()),
        'execution_scope':'Exactly two null-seed straight calls for8670 and8674, no FMM/baseline repeats or escalation beyond4000.',
        'limits':expected_settings,
        'interpretation_conditions':['Report budget exhaustion separately from the post-return strict flag.',
            'Compare source-vector accuracy independently of action reduction and local flags; preserve any worsened control.',
            'Report any node-count or merge difference; no fixed-representation claim if merging occurs.',
            'No production tolerance, live source/binary, full-cohort or inversion acceptance change.']}
    with (HERE/'prelaunch_review.json').open('x') as stream:
        json.dump(review,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({'status':'passed','review_sha256':sha(HERE/'prelaunch_review.json'),'pins':counts}))

if __name__ == '__main__':
    main()
