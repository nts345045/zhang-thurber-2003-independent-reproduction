#!/usr/bin/env python3
"""Independent saved-source/native-pin review; no compile, field, or ray calls."""
import ast, csv, hashlib, json, tarfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''): h.update(b)
    return h.hexdigest()
def rows(p):
    with p.open() as f:return list(csv.DictReader(f))
p=json.loads((HERE/'prepared.json').read_text())
assert sha(HERE/'prepared.json')=='b83f9691eb0fc58d2580e269dded1a70d069daa560d716999139460ee6a8f159'
counts={}
for key,base in [('original_sha256',ROOT),('runtime_sha256',Path('/')),('output_sha256',HERE),('source_sha256',HERE)]:
    for n,h in p[key].items():assert sha(base/n)==h,(key,n)
    counts[key]=len(p[key])
ledger=json.loads((HERE/'inputs/dd_inversion_execution.json').read_text())
assert ledger['status']=='failed'
manifest=json.loads((HERE/'inputs/dd_inversion_run_manifest.json').read_text())
assert sha(HERE/'inputs/guarded_source.tar.gz')==manifest['source_archive_sha256']
with tarfile.open(str(HERE/'inputs/guarded_source.tar.gz')) as t:
    assert set(t.getnames())==set(manifest['source_sha256'])
    for n,h in manifest['source_sha256'].items():
        b=t.extractfile(n).read();assert hashlib.sha256(b).hexdigest()==h
        assert (HERE/'source/old'/n).read_bytes()==b
        if n!='src/core.hpp':assert (HERE/'source/D'/n).read_bytes()==b
assert sha(HERE/'source/D/src/core.hpp')=='c9500361c5ca3ff55b2fbcec0aedfb3639d3f3b68a53431267e6849c3a933044'
assert sha(HERE/'source/D/src/usable_ray_curvature.hpp')=='5236f9df135dc2449662db70bb68aded36cae3f5ce23e7471caa02d45ce5daac'
contexts=json.loads((HERE/'inputs/native_context.json').read_text())
status=rows(HERE/'inputs/original_status.csv');paths=rows(HERE/'inputs/original_paths.csv')
events=rows(HERE/'inputs/trial_events.csv');stations=rows(HERE/'inputs/stations.csv')
assert [(int(r['event']),int(r['station'])) for r in status]==[(981,160),(987,160)]
native_cells=0
for c,r in zip(contexts,status):
    i,k=int(r['event']),int(r['station']);assert c['source_native']==events[i] and c['receiver_native']==stations[k] and c['original_status']==r
    assert r['ray_converged']=='0' and r['ray_initialization_succeeded']=='1' and r['ray_selected_fmm_seed']=='1'
    nodes=[q for q in paths if (int(q['event']),int(q['station']))==(i,k)]
    assert len(nodes)==int(r['ray_path_points']) and [int(q['node']) for q in nodes]==list(range(len(nodes)))
    for prefix,record in [('source_',events[i]),('receiver_',stations[k])]:
        for name,value in record.items():
            if name in ('id','t') or (prefix=='source_' and name=='coordinate_basis'):continue
            if name in ('x','y','z'):assert float(r[prefix+name])==float(value)
            else:
                assert r[prefix+name]==value
                for q in nodes:assert q[prefix+name]==value;native_cells+=1
    assert [float(nodes[0][a]) for a in 'xyz']==[float(r['source_'+a]) for a in 'xyz']
    assert [float(nodes[-1][a]) for a in 'xyz']==[float(r['receiver_'+a]) for a in 'xyz']
assert len(paths)==sum(int(r['ray_path_points']) for r in status)
original=(HERE/'source/old/src/forward.hpp').read_text();original=original[original.index('Ray trace_first_arrival('):]
expected=original.replace('Ray trace_first_arrival(', 'Ray replay_candidate(',1).replace('int maxit, bool deriv, const first_arrival::Field &field) {','int maxit, bool deriv, const std::function<first_arrival::Candidate()> &provider, std::array<Ray, 2> &starts) {',1)
expected=expected.replace('auto candidate = field.candidate(source);','auto candidate = provider();',1).replace('  Ray direct = trace(g, source, receiver, spacing, maxit, deriv);','  ++replay_trace_calls;\n  Ray direct = trace(g, source, receiver, spacing, maxit, deriv);\n  starts[0] = direct;',1).replace('    Ray seeded = trace(g, source, receiver, spacing, maxit, deriv, &candidate.path);','    ++replay_trace_calls;\n    Ray seeded = trace(g, source, receiver, spacing, maxit, deriv, &candidate.path);\n    starts[1] = seeded;',1)
assert (HERE/'candidate_forward.hpp').read_text()=='#pragma once\nstatic int replay_trace_calls = 0;\n'+expected
oldast=ast.parse((ROOT/'data/development/loma_lon_strict_straight_4000_replay_001/run.py').read_text());newast=ast.parse((HERE/'run.py').read_text())
for name in ('verify','group_members','signal_group','terminate_and_reap','interrupted','command'):
    a=[n for n in ast.walk(oldast) if isinstance(n,ast.FunctionDef) and n.name==name];b=[n for n in ast.walk(newast) if isinstance(n,ast.FunctionDef) and n.name==name]
    assert len(a)==len(b)==1 and ast.dump(a[0])==ast.dump(b[0])
assert not any((HERE/n).exists() for n in ('execution.json','results','build'))
review={'status':'passed','reviewer':'scientific_audit','prepared_sha256':sha(HERE/'prepared.json'),'review_source_sha256':sha(Path(__file__)), 'verified_pin_counts':counts,'native_metadata_cells':native_cells,'native_pairs':contexts,'source_review':'Exact archived old sources; adopted D changes only core plus usable-curvature header. Copied selection function differs only provider transport, returned-start copies and call counters; same strict time selection and both starts. Old full17-digit status and selected-path parity gates all D calls. Candidate fields and every coordinate/time roundtrip binary64 exactly. One common original FMM field; no selected optimized path used as seed. Source/model derivatives intentionally disabled.', 'lifecycle_review':'All six existing reviewed verify/lifecycle function ASTs unchanged; child process groups reaped before immutable hashes; frozen original/runtime/prepared sources rechecked before each numerical variant. Exclusive execution ledger prevents reused output.', 'limitations':['Two identified rays in one actual rejected3D trial; no whole-cohort, inversion acceptance or continuous/global accuracy claim.','D changes outer action accumulation and usable curvature together; this is not a single-cause intervention.','Unselected start summaries are preserved, but only selected full paths are exported.','Execution and old numerical parity remain unperformed; this review authorizes only the bounded four configured evaluations/eight trace subcalls.']}
with (HERE/'prelaunch_review.json').open('x') as f:json.dump(review,f,indent=2,allow_nan=False);f.write('\n')
print(sha(HERE/'prelaunch_review.json'))
