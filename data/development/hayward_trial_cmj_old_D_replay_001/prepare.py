#!/usr/bin/env python3
"""Freeze exact failed-trial inputs and old/adopted-D source; no numerical calls."""
import ast
import csv
import difflib
import hashlib
import json
from pathlib import Path
import shutil
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RAW = ROOT / 'data/hayward_first_arrival_guarded_001'
PAIRS = ((981, 160), (987, 160))


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def rows(path):
    with path.open() as f:
        return list(csv.DictReader(f))


def write_rows(path, records):
    with path.open('x') as f:
        w = csv.DictWriter(f, fieldnames=list(records[0]), lineterminator='\n')
        w.writeheader(); w.writerows(records)


def main():
    if (HERE / 'prepared.json').exists() or (HERE / 'inputs').exists():
        raise RuntimeError('Exclusive preparation; preserve prior attempts')
    originals = {}

    def pin(path):
        originals[str(path.relative_to(ROOT))] = sha(path)

    def copy(old, new):
        pin(old)
        new.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(str(old), str(new))

    manifest = json.loads((RAW / 'dd_inversion_run_manifest.json').read_text())
    for name in ('dd_inversion_run_manifest.json', 'dd_inversion_execution.json', 'dd_failed_forward_context.csv',
                 'dd_failed_forward_ray_failures.csv', 'guarded_source.tar.gz'):
        copy(RAW / name, HERE / 'inputs' / name)
    for old, new in [('dd_failed_forward_grid.csv', 'trial_grid.csv'),
                     ('dd_failed_forward_events.csv', 'trial_events.csv'), ('stations.csv', 'stations.csv'), ('run.cfg', 'run.cfg')]:
        copy(RAW / old, HERE / 'inputs' / new)
    for name in manifest['build_provenance_sha256']:
        if sha(RAW / name) != manifest['build_provenance_sha256'][name]:
            raise RuntimeError('Original build provenance changed')
        copy(RAW / name, HERE / 'inputs' / name)
    context = rows(HERE / 'inputs/dd_failed_forward_context.csv')
    if len(context) != 1 or any(context[0][k] != v for k,v in
        {'iteration':'0','phase':'line_search_trial','line_search_trial':'0','derivatives_requested':'0','significant_digits':'17'}.items()):
        raise RuntimeError('Unexpected failed-trial context')
    events, stations = rows(HERE / 'inputs/trial_events.csv'), rows(HERE / 'inputs/stations.csv')
    if len(events) != 1092 or len(stations) != 372:
        raise RuntimeError('Unexpected native geometry inventory')
    status_path, path_path = RAW / 'dd_failed_forward_ray_status.csv', RAW / 'dd_failed_forward_ray_paths.csv'
    pin(status_path); pin(path_path)
    statuses = [r for r in rows(status_path) if (int(r['event']), int(r['station'])) in PAIRS]
    with path_path.open() as f:
        paths = [r for r in csv.DictReader(f) if (int(r['event']), int(r['station'])) in PAIRS]
    if [(int(r['event']),int(r['station'])) for r in statuses] != list(PAIRS):
        raise RuntimeError('Original status pair mismatch')
    contexts = []
    for r,(i,k) in zip(statuses,PAIRS):
        if any(r[name] != value for name,value in {'ray_converged':'0','ray_finite':'1',
            'ray_initialization_succeeded':'1','ray_selected_fmm_seed':'1','ray_derivatives_evaluated':'0'}.items()):
            raise RuntimeError('Unexpected original failure flags')
        if any(r['source_d'+a] for a in 'xyz'): raise RuntimeError('Action-only partials must be blank')
        for prefix, native in [('source_',events[i]),('receiver_',stations[k])]:
            for key,value in native.items():
                if key in ('id','t') or (prefix == 'source_' and key == 'coordinate_basis'): continue
                if key in 'xyz' and len(key)==1:
                    if float(r[prefix+key]) != float(value): raise RuntimeError('Native coordinate mismatch')
                elif r[prefix+key] != value: raise RuntimeError('Native identity mismatch: '+key)
        selected = [q for q in paths if int(q['event']) == i and int(q['station']) == k]
        if len(selected) != int(r['ray_path_points']) or [int(q['node']) for q in selected] != list(range(len(selected))):
            raise RuntimeError('Original selected path incomplete')
        contexts.append({'event':i,'station':k,'native_flat_index':i*len(stations)+k,
                         'source_native':events[i],'receiver_native':stations[k],'original_status':r})
    write_rows(HERE / 'inputs/original_status.csv',statuses)
    write_rows(HERE / 'inputs/original_paths.csv',paths)
    with (HERE / 'inputs/native_context.json').open('x') as f:
        json.dump(contexts,f,indent=2,allow_nan=False); f.write('\n')

    archive = RAW / 'guarded_source.tar.gz'
    if sha(archive) != manifest['source_archive_sha256']: raise RuntimeError('Source archive changed')
    with tarfile.open(str(archive)) as t:
        members = {m.name:m for m in t.getmembers()}
        if set(members) != set(manifest['source_sha256']): raise RuntimeError('Source archive inventory mismatch')
        for name, expected in manifest['source_sha256'].items():
            if not members[name].isfile() or Path(name).is_absolute() or '..' in Path(name).parts:
                raise RuntimeError('Unsafe source archive member')
            data = t.extractfile(members[name]).read()
            if hashlib.sha256(data).hexdigest()!=expected: raise RuntimeError('Archived source hash mismatch')
            for variant in ('old','D'):
                target=HERE/'source'/variant/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    expected_D = {'src/core.hpp':'c9500361c5ca3ff55b2fbcec0aedfb3639d3f3b68a53431267e6849c3a933044',
                  'src/usable_ray_curvature.hpp':'5236f9df135dc2449662db70bb68aded36cae3f5ce23e7471caa02d45ce5daac'}
    for name,expected in expected_D.items():
        if sha(ROOT/name)!=expected: raise RuntimeError('Unexpected adopted D source')
        copy(ROOT/name,HERE/'source/D'/name)
    copy(ROOT/'data/development/usable_curvature_adoption_001/adoption.json', HERE/'inputs/adoption.json')
    copy(ROOT/'data/development/usable_curvature_integration_review_001/review.json', HERE/'inputs/integration_review.json')
    for name in manifest['source_sha256']:
        if name!='src/core.hpp' and (HERE/'source/old'/name).read_bytes()!=(HERE/'source/D'/name).read_bytes():
            raise RuntimeError('Unexpected old/D source difference')
    oldcore=(HERE/'source/old/src/core.hpp').read_text();newcore=(HERE/'source/D/src/core.hpp').read_text()
    segment=lambda s:s[s.index('double segment('):s.index('double path_eval(')]
    if segment(oldcore)!=segment(newcore): raise RuntimeError('FMM seed segment arithmetic changed')
    (HERE/'core.hpp.diff').write_text(''.join(difflib.unified_diff(oldcore.splitlines(True),newcore.splitlines(True),fromfile='old/core.hpp',tofile='D/core.hpp')))

    forward=(HERE/'source/old/src/forward.hpp').read_text()
    function=forward[forward.index('Ray trace_first_arrival('):]
    signature='int maxit, bool deriv, const first_arrival::Field &field) {'
    if function.count(signature)!=1 or function.count('auto candidate = field.candidate(source);')!=1:
        raise RuntimeError('Unexpected original configured-forward body')
    generated=function.replace('Ray trace_first_arrival(', 'Ray replay_candidate(',1).replace(signature,
        'int maxit, bool deriv, const std::function<first_arrival::Candidate()> &provider, std::array<Ray, 2> &starts) {',1)
    generated=generated.replace('auto candidate = field.candidate(source);','auto candidate = provider();',1)
    generated=generated.replace('  Ray direct = trace(g, source, receiver, spacing, maxit, deriv);',
        '  ++replay_trace_calls;\n  Ray direct = trace(g, source, receiver, spacing, maxit, deriv);\n  starts[0] = direct;',1)
    generated=generated.replace('    Ray seeded = trace(g, source, receiver, spacing, maxit, deriv, &candidate.path);',
        '    ++replay_trace_calls;\n    Ray seeded = trace(g, source, receiver, spacing, maxit, deriv, &candidate.path);\n    starts[1] = seeded;',1)
    (HERE/'candidate_forward.hpp').write_text('#pragma once\nstatic int replay_trace_calls = 0;\n'+generated)
    (HERE/'candidate_forward.diff').write_text(''.join(difflib.unified_diff(function.splitlines(True),generated.splitlines(True),fromfile='original trace_first_arrival',tofile='candidate-provider transport and returned-start capture')))
    runtime=dict(manifest['runtime_library_sha256']);runtime[manifest['compiler']]=manifest['compiler_sha256']
    for name,expected in runtime.items():
        if sha(Path(name))!=expected: raise RuntimeError('Original compiler/runtime changed')
    ast.parse((HERE/'run.py').read_text())
    baseline_runner=ROOT/'data/development/loma_lon_strict_straight_4000_replay_001/run.py'
    pin(baseline_runner)
    old_ast,new_ast=ast.parse(baseline_runner.read_text()),ast.parse((HERE/'run.py').read_text())
    for name in ('verify','group_members','signal_group','terminate_and_reap','interrupted','command'):
        a=[n for n in ast.walk(old_ast) if isinstance(n,ast.FunctionDef) and n.name==name]
        b=[n for n in ast.walk(new_ast) if isinstance(n,ast.FunctionDef) and n.name==name]
        if len(a)!=1 or len(b)!=1 or ast.dump(a[0])!=ast.dump(b[0]): raise RuntimeError('Lifecycle/check function changed: '+name)
    for name,expected in originals.items():
        if sha(ROOT/name)!=expected: raise RuntimeError('Original changed during preparation')
    result={'status':'prepared_not_executed','events':[981,987],'station':160,'configured_evaluations':4,'trace_subcalls':8,
            'field_constructions':1,'source_intervention':'Original trial core versus adopted D outer accumulation and usable-curvature package; all other archived source unchanged',
            'original_sha256':originals,'runtime_sha256':runtime,'compiler':manifest['compiler'],'flags':manifest['flags'].split(),
            'source_sha256':{str(p.relative_to(HERE)):sha(p) for p in sorted((HERE/'source').rglob('*')) if p.is_file()},
            'output_sha256':{str(p.relative_to(HERE)):sha(p) for p in sorted(HERE.rglob('*')) if p.is_file()},
            'settings':{'path_spacing_km':.03125,'field_spacing_km':.125,'maximum_updates':1000,'derivatives':False,
                        'OMP_NUM_THREADS':4,'address_space_limit_GiB':16,'field_nodes':45603129},
            'old_parity_gate':'All saved original status fields and every selected-path coordinate/native field must match at17-digit serialization before any D trace',
            'limitations':['Standalone two-ray comparison, no inverse restart/trial acceptance/full cohort',
                           'No source/model derivatives or continuous-reference/global accuracy claim',
                           'One complete original field and full Candidate serialization; no final-path seed substitution']}
    with (HERE/'prepared.json').open('x') as f: json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
    print(sha(HERE/'prepared.json'))


if __name__=='__main__': main()
