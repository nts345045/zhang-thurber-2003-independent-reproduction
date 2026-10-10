#!/usr/bin/env python3
"""Saved eligibility/source checks and invented process stubs; no numerical calls."""
import argparse
import ast
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'data/development/hayward_old_kernel_backtracking_launcher_001'
PREPARED_SHA = '39593013076b06ce0ab5fac64d9ac4ec7d23f272762dbbdb6931fc002df8cf3d'
SOURCE = PACKAGE / 'source_snapshot/run_hayward_old_kernel_backtracking.py'
OLD = ROOT / 'data/development/hayward_trial_completion_candidate_002/after/run_hayward_guarded_inversion.py'
FIXTURE = ROOT / 'data/development/hayward_guarded_launcher_checks/002'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text())


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')


def require(ok, message):
    if not ok:
        raise AssertionError(message)


def functions(path):
    return {n.name: n for n in ast.parse(path.read_text()).body if isinstance(n, ast.FunctionDef)}


def canonical(node):
    return ast.dump(node, include_attributes=False)


def imported_launcher():
    # Freeze and verify dependencies, but retain the repository base for read-only evidence joins.
    sys.path.insert(0, str(PACKAGE / 'source_snapshot'))
    sys.path.insert(1, str(ROOT))
    spec = importlib.util.spec_from_file_location('launcher_under_check', str(SOURCE))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ROOT = ROOT
    return module


def verify(base, mapping):
    for name, digest in mapping.items():
        require(sha(base / name) == digest, 'Changed pin: ' + name)


def source_checks(launcher, check):
    old, new = functions(OLD), functions(SOURCE)
    for name in ('configuration', 'check_inverse'):
        check(name + '_AST_unchanged', canonical(old[name]) == canonical(new[name]))
    a, b = old['reviewed_inputs'].body, new['reviewed_inputs'].body
    ia = next(i for i, n in enumerate(a) if 'Main call path differs from the independently reviewed guard' in canonical(n))
    ib = next(i for i, n in enumerate(b) if isinstance(n, ast.Assign) and 'source_adoption' in canonical(n))
    check('eligibility_prefix_AST_unchanged', canonical(ast.Module(body=a[:ia])) == canonical(ast.Module(body=b[:ib])))
    # The common evidence assembly and count expression also remain unchanged.
    ea = next(i for i, n in enumerate(a) if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'evidence' for t in n.targets))
    eb = next(i for i, n in enumerate(b) if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'evidence' for t in n.targets))
    check('common_evidence_AST_unchanged', all(canonical(x) == canonical(y) for x, y in zip(a[ea:ea+2], b[eb:eb+2])))
    check('expected_counts_AST_unchanged', canonical(a[-1].value.elts[-1]) == canonical(b[-1].value.elts[-1]))
    helper = ROOT / 'diagnostics/review_old_kernel_trial_completion.py'
    reference = OLD.parent / 'diagnostics/review_trial_completion.py'
    check('completion_helper_exact_reviewed_bytes', helper.read_bytes() == reference.read_bytes() and sha(helper) == launcher.COMPLETION_HELPER)
    for kind in ('STRING', 'FILEPATH'):
        check('compiler_cache_' + kind, launcher.compiler_from_cache('CMAKE_CXX_COMPILER:' + kind + '=/usr/bin/c++\n') == '/usr/bin/c++')


def invented_eligibility(out):
    """Reuse saved invented tables; only directory/hash bindings are regenerated."""
    data, reference = out / 'invented_preflight', out / 'invented_reference'
    shutil.copytree(str(FIXTURE / 'invented_preflight'), str(data))
    shutil.copytree(str(FIXTURE / 'invented_reference'), str(reference))
    old_prefix = str((FIXTURE / 'invented_preflight').relative_to(ROOT)) + '/'
    new_prefix = str(data.relative_to(ROOT)) + '/'
    def rebound(mapping):
        return {(new_prefix + k[len(old_prefix):] if k.startswith(old_prefix) else k): v for k, v in mapping.items()}
    manifest = load(data / 'run_manifest.json')
    manifest['sha256'] = rebound(manifest['sha256'])
    dump(data / 'run_manifest.json', manifest)
    full = load(reference / 'summary.json')
    full['original_reverified_sha256'] = rebound(full['original_reverified_sha256'])
    dump(reference / 'summary.json', full)
    review = load(reference / 'independent_review.json')
    review['summary_sha256'] = sha(reference / 'summary.json')
    dump(reference / 'independent_review.json', review)
    accuracy = load(FIXTURE / 'invented_accuracy_review.json')
    accuracy['preflight_directory'] = str(data.relative_to(ROOT))
    for name, path in [('preflight_manifest', data / 'run_manifest.json'), ('preflight_ledger', data / 'preflight_execution.json'),
                       ('preflight_checks', data / 'preflight.json'), ('full_reference_summary', reference / 'summary.json'),
                       ('full_reference_review', reference / 'independent_review.json')]:
        accuracy['sha256'][name] = sha(path)
    accuracy_path = out / 'invented_accuracy_review.json'
    dump(accuracy_path, accuracy)
    return data, reference, accuracy_path


def stub(case, out):
    """Only commands used by the lifecycle fixture. Never invokes a compiler or solver."""
    if case == 'writer':
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        (out / 'writer_pid.txt').write_text(str(os.getpid()))
        with (out / 'writer.txt').open('a') as f:
            for n in range(1500):
                f.write(str(n) + '\n'); f.flush(); time.sleep(.02)
        return
    if case in ('zero', 'nonzero'):
        print('invented stub ' + case)
        raise SystemExit(0 if case == 'zero' else 7)
    child = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '--stub', 'writer', '--output', str(out)])
    deadline = time.monotonic() + 10
    while not (out / 'writer_pid.txt').exists() and time.monotonic() < deadline:
        time.sleep(.02)
    require((out / 'writer_pid.txt').exists(), 'Invented writer did not start')
    (out / 'stub_ready.txt').write_text(str(child.pid))
    if case == 'early_zero':
        raise SystemExit(0)
    if case == 'early_nonzero':
        raise SystemExit(7)
    time.sleep(40)


def lifecycle_child(case, out):
    """Execute exact nested run/interrupt/except AST, excluding the numerical main body."""
    launcher = imported_launcher()
    main = functions(SOURCE)['main']
    nested = {n.name: n for n in main.body if isinstance(n, ast.FunctionDef)}
    original_try = next(n for n in main.body if isinstance(n, ast.Try))
    hash_node = next(n for n in original_try.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'outputs' for t in n.targets))
    template = ast.parse('''
def exercise():
    active = None
    def run_placeholder(): pass
    def interrupted_placeholder(): pass
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    try:
        run(stub_command, 'stub')
        outputs = None
        ledger.update(status='fixture_completed', return_code=0, output_sha256=outputs)
        atomic_json(ledger_path, ledger)
    except BaseException as error:
        pass
exercise()
''')
    body = template.body[0].body
    body[1], body[2] = copy.deepcopy(nested['run']), copy.deepcopy(nested['interrupted'])
    test_try = next(n for n in body if isinstance(n, ast.Try))
    test_try.body[1] = copy.deepcopy(hash_node)
    test_try.handlers = copy.deepcopy(original_try.handlers)
    ast.fix_missing_locations(template)
    ledger = dict(status='preparing', completed_commands=[], scientific_success=False,
                  scope='Isolated actual launcher lifecycle AST with invented process stubs only; not a positive full controller test')
    namespace = dict(launcher.__dict__)
    namespace.update(out=out, ledger_path=out / 'dd_inversion_execution.json', ledger=ledger,
        env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1', TMPDIR=str(ROOT / 'tmp')),
        stub_command=[sys.executable, str(Path(__file__).resolve()), '--stub', case, '--output', str(out)])
    launcher.atomic_json(namespace['ledger_path'], ledger)
    exec(compile(template, str(SOURCE) + ':extracted_lifecycle', 'exec'), namespace)


def lifecycle_controls(out, launcher, check, commands):
    for case in ('zero', 'nonzero', 'early_zero', 'early_nonzero', 'sigterm'):
        directory = out / ('lifecycle_' + case); directory.mkdir()
        command = [sys.executable, str(Path(__file__).resolve()), '--lifecycle-child', case, '--output', str(directory)]
        process = None; group = None
        try:
            # Controller logs live outside the child output directory: the child
            # cannot freeze its own still-open traceback/driver streams.
            with (out / (case + '_driver_stdout.log')).open('x') as a, (out / (case + '_driver_stderr.log')).open('x') as b:
                process = subprocess.Popen(command, cwd=str(ROOT), env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'),
                                           stdout=a, stderr=b, start_new_session=True)
                if case == 'sigterm':
                    deadline = time.monotonic() + 20
                    while not (directory / 'stub_ready.txt').exists() and process.poll() is None and time.monotonic() < deadline:
                        time.sleep(.03)
                    require((directory / 'stub_ready.txt').exists() and process.poll() is None, 'Missing SIGTERM writer point')
                    process.send_signal(signal.SIGTERM)
                    # A second signal must not interrupt the launcher's cleanup.
                    time.sleep(.15)
                    if process.poll() is None: process.send_signal(signal.SIGTERM)
                code = process.wait(timeout=35)
            ledger = load(directory / 'dd_inversion_execution.json')
            group = ledger.get('current_child_pid')
            commands.append(dict(case=case, command=command, return_code=code, child_group=group))
            expected = 'fixture_completed' if case == 'zero' else ('interrupted' if case == 'sigterm' else 'failed')
            check(case + '_status', ledger['status'] == expected and ((code == 0) == (case == 'zero')))
            check(case + '_group_reaped', group is not None and not launcher.live_group_members(group))
            mapping = ledger.get('output_sha256', ledger.get('partial_output_sha256'))
            require(mapping is not None, 'Missing stable fixture hashes')
            verify(directory, mapping)
            time.sleep(.1)
            verify(directory, mapping)
            check(case + '_hashes_stable_after_writers', True)
            if case in ('early_zero', 'early_nonzero'):
                check(case + '_orphan_reported', bool(ledger['completed_commands'][0]['remaining_live_group_members']) and
                      not ledger['exception_child']['remaining_live_group_members'])
            if case == 'nonzero': check('nonzero_code_preserved', ledger['return_code'] == 7)
            if case == 'sigterm': check('sigterm_code_preserved', code == 143 and ledger['return_code'] == 143)
        finally:
            # Test ownership applies even if a tested launcher regresses.
            if group is None and (directory / 'dd_inversion_execution.json').exists():
                group = load(directory / 'dd_inversion_execution.json').get('current_child_pid')
            if group is not None and launcher.live_group_members(group):
                try: os.killpg(group, signal.SIGKILL)
                except ProcessLookupError: pass
                deadline = time.monotonic() + 5
                while launcher.live_group_members(group) and time.monotonic() < deadline: time.sleep(.03)
            if process is not None and process.poll() is None:
                process.kill(); process.wait()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--stub')
    parser.add_argument('--lifecycle-child')
    args = parser.parse_args()
    out = (ROOT / args.output).resolve(); out.relative_to(ROOT)
    if args.stub: return stub(args.stub, out)
    if args.lifecycle_child: return lifecycle_child(args.lifecycle_child, out)
    require(not (out / 'summary.json').exists(), 'Require a fresh control result')
    out.mkdir(parents=True, exist_ok=True)
    harness_plan = load(out / 'prepared.json')
    require(sha(Path(__file__).resolve()) == harness_plan['harness_sha256'], 'Control harness changed after preparation')
    verify(out, harness_plan['output_sha256'])
    require(sha(PACKAGE / 'prepared.json') == PREPARED_SHA, 'Launcher preparation changed')
    plan = load(PACKAGE / 'prepared.json')
    verify(ROOT, plan['input_sha256']); verify(PACKAGE, plan['output_sha256'])
    launcher = imported_launcher()
    summary = dict(status='running', prepared_sha256=PREPARED_SHA, checks=[], commands=[],
        numerical_calls=0, compiler_calls=0, inverse_calls=0,
        limitations=['No complete positive controller-final fixture with the required initializer=1 metadata is available.',
                     'Exact helper/check_inverse equivalence preserves that requirement; no fixture status is promoted to scientific success.',
                     'Lifecycle fixtures execute the actual nested run/handler AST in isolation, not the complete build/inverse main.'])
    def check(name, ok):
        summary['checks'].append(dict(name=name, passed=bool(ok)))
        dump(out / 'summary.json', summary)
        require(ok, name)
    def rejected(name, fn):
        try: fn()
        except (ValueError, AssertionError, KeyError, FileNotFoundError) as error:
            summary['checks'].append(dict(name=name, passed=True, rejection_type=type(error).__name__, rejection=str(error)))
            dump(out / 'summary.json', summary)
        else: raise AssertionError('Unexpected acceptance: ' + name)
    def mutate_json(path, fn, action, name):
        original = path.read_bytes()
        try:
            value = load(path); fn(value); dump(path, value)
            rejected(name, action)
        finally: path.write_bytes(original)
    try:
        source_checks(launcher, check)
        for name, text in [('missing',''), ('empty','CMAKE_CXX_COMPILER:STRING=\n'),
                           ('malformed','CMAKE_CXX_COMPILER=/usr/bin/c++\n'),
                           ('duplicate','CMAKE_CXX_COMPILER:STRING=/a\nCMAKE_CXX_COMPILER:FILEPATH=/a\n'),
                           ('malformed_duplicate','CMAKE_CXX_COMPILER:STRING=/a\nCMAKE_CXX_COMPILER:FILEPATH\n')]:
            rejected('cache_' + name, lambda text=text: launcher.compiler_from_cache(text))
        data, reference, accuracy = invented_eligibility(out)
        parity_path = ROOT / 'data/development/hayward_guard_adoption_checks/001/summary.json'
        parity = load(parity_path); manifest = load(data / 'run_manifest.json')
        selected, adoption, evidence = launcher.source_adoption(parity, manifest)
        check('004_guard_main_only_bridge_accepted', adoption['candidate_source_sha256'] == plan['source_adoption']['candidate_source_sha256'])
        real_plan = load(ROOT/'data/development/hayward_guarded_dd_launch_plan_001/plan.json')
        command = real_plan['command']
        get = lambda flag: ROOT/command[command.index(flag)+1]
        result = launcher.reviewed_inputs(get('--preflight'), get('--reference'), get('--accuracy-review'), get('--parity-review'))
        check('actual_saved_eligibility_readback', result[-1] == plan['expected_counts'])
        # The new source bridge intentionally forbids substituting invented
        # native inputs. Stop at its call boundary to test only the inherited
        # eligibility prefix; reaching this sentinel is not full eligibility.
        class PrefixReached(Exception): pass
        actual_adoption = launcher.source_adoption
        def sentinel(*unused): raise PrefixReached('Inherited prefix reached the explicit source bridge boundary')
        launcher.source_adoption = sentinel
        eligibility = lambda: launcher.reviewed_inputs(data, reference, accuracy, parity_path)
        try:
            try: eligibility()
            except PrefixReached: check('invented_prefix_reached_source_boundary_only', True)
            else: raise AssertionError('Inherited prefix did not reach declared sentinel')
            for name, path, change in [
                ('running_preflight', data/'preflight_execution.json', lambda x: x.update(status='running')),
                ('missing_preflight_child', data/'preflight_execution.json', lambda x: x.update(completed_commands=[])),
                ('failed_preflight', data/'preflight.json', lambda x: x.update(failures=['invented failure'])),
                ('stale_scientific_review', accuracy, lambda x: x['sha256'].update(preflight_ledger='0'*64)),
                ('unassessed_FD', accuracy, lambda x: x['checks'].update(finite_difference_truncation_assessed=False)),
                ('failed_full_reference', reference/'independent_review.json', lambda x: x.update(both_limits_pass=2)),
                ('changed_accuracy_gate', reference/'summary.json', lambda x: x['accuracy_control_limits'].update(source_euclidean_norm_s_per_km=1e-5))]:
                mutate_json(path, change, eligibility, name)
            for name in ('observations.csv','run.cfg','stations.csv'):
                path=data/name; original=path.read_bytes()
                try:
                    path.write_bytes(original+b'changed fixture\n'); rejected('changed_input_'+name, eligibility)
                finally: path.write_bytes(original)
        finally: launcher.source_adoption = actual_adoption
        rejected('invented_inputs_rejected_by_real_source_bridge', eligibility)
        old_candidate, old_reviews = launcher.CANDIDATE, launcher.SOURCE_REVIEWS
        copied_candidate = out / 'copied_candidate'
        shutil.copytree(str(ROOT/'data/development'/old_candidate), str(copied_candidate))
        launcher.CANDIDATE = str(copied_candidate.relative_to(ROOT/'data/development'))
        launcher.SOURCE_REVIEWS = {(launcher.CANDIDATE+k[len(old_candidate):] if k.startswith(old_candidate+'/') else k):v
                                   for k,v in old_reviews.items()}
        source_gate = lambda: launcher.source_adoption(parity, manifest)
        try:
            source_gate(); check('copied_candidate_same_source_bridge', True)
            for name in ('after/src/core.hpp','root_source_review.json'):
                path=copied_candidate/name; original=path.read_bytes()
                try:
                    path.write_bytes(original+b'changed fixture\n'); rejected('changed_'+name, source_gate)
                    path.unlink(); rejected('missing_'+name, source_gate)
                    path.symlink_to(Path(name).name+'.absent'); rejected('symlink_'+name, source_gate)
                    path.unlink()
                    regular = path.with_name(path.name+'.regular_fixture'); regular.write_bytes(original)
                    path.symlink_to(regular.name); rejected('existing_target_symlink_'+name, source_gate)
                finally:
                    if path.is_symlink(): path.unlink()
                    path.write_bytes(original)
            directory=copied_candidate/'after/src'; relocated=copied_candidate/'after/src_regular_fixture'
            directory.rename(relocated)
            try:
                directory.symlink_to(relocated.name, target_is_directory=True)
                rejected('existing_parent_alias_rejected', source_gate)
            finally:
                directory.unlink(); relocated.rename(directory)
            changed=copy.deepcopy(parity); changed['guarded_source_sha256']['src/main.cpp']='0'*64
            rejected('wrong_guard_bridge_main', lambda: launcher.source_adoption(changed,manifest))
            changed=copy.deepcopy(manifest); changed['source_sha256']['src/main.cpp']='0'*64
            rejected('wrong_preflight_bridge_main', lambda: launcher.source_adoption(parity,changed))
            changed=copy.deepcopy(parity); changed['guarded_source_sha256']['src/core.hpp']='0'*64
            rejected('wrong_kernel_bridge', lambda: launcher.source_adoption(changed,manifest))
            changed=copy.deepcopy(parity); changed['compiler']='/invented/wrong/compiler'
            rejected('wrong_compiler_bridge', lambda: launcher.source_adoption(changed,manifest))
            # Declared hash-reader fault injection, not mutation of the shared
            # maintained/frozen completion helper or its accepted review.
            original_sha = launcher.sha
            helper = ROOT/'diagnostics/review_old_kernel_trial_completion.py'
            launcher.sha = lambda path: '0'*64 if path == helper else original_sha(path)
            try: rejected('changed_completion_helper_hash_report_rejected', source_gate)
            finally: launcher.sha = original_sha
        finally: launcher.CANDIDATE, launcher.SOURCE_REVIEWS = old_candidate, old_reviews
        lifecycle_controls(out, launcher, check, summary['commands'])
        verify(ROOT, plan['input_sha256']); verify(PACKAGE, plan['output_sha256'])
        check('original_evidence_and_frozen_source_unchanged', True)
        summary.update(status='passed', controls_total=len(summary['checks']), controls_passed=sum(x['passed'] for x in summary['checks']))
    except BaseException as error:
        summary.update(status='failed', error_type=type(error).__name__, error=str(error))
        raise
    finally:
        summary['source_sha256']={str(Path(__file__).resolve().relative_to(ROOT)):sha(Path(__file__).resolve()),
                                  str(SOURCE.relative_to(ROOT)):sha(SOURCE)}
        summary['artifact_sha256']={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file() and not p.is_symlink() and p!=out/'summary.json'}
        dump(out/'summary.json',summary)
    print(json.dumps(dict(status=summary['status'],checks=len(summary['checks'])),indent=2))


if __name__ == '__main__':
    main()
