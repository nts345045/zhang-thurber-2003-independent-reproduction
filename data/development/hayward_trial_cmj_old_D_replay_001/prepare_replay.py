#!/usr/bin/env python3
"""Restore only replay dependencies into an exclusive minimal scratch root."""
import argparse, hashlib, importlib.util, json, shutil, sys, tarfile
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
ARCHIVE=ROOT/'data/development/hayward_guarded_failure_001'
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def safe(name):
    p=Path(name)
    if p.is_absolute() or '..' in p.parts:raise RuntimeError('Unsafe relative path '+name)
    return p
def main():
    parser=argparse.ArgumentParser();parser.add_argument('scratch_root',help='fresh relative directory under this checkout/tmp')
    args=parser.parse_args();rel=safe(args.scratch_root)
    if not rel.parts or rel.parts[0]!='tmp':raise RuntimeError('Scratch root must be under checkout/tmp')
    dest=ROOT/rel
    if dest.exists() or dest.is_symlink():raise RuntimeError('Refusing existing scratch root')
    for p in dest.parents:
        if p==ROOT:break
        if p.is_symlink():raise RuntimeError('Refusing symlink ancestor')
    dest.resolve().relative_to(ROOT.resolve())
    prepared=json.loads((HERE/'prepared.json').read_text());review=json.loads((HERE/'prelaunch_review.json').read_text())
    if review['status']!='passed' or review['prepared_sha256']!=sha(HERE/'prepared.json'):raise RuntimeError('Preparation review changed')
    manifest=json.loads((ARCHIVE/'manifest.json').read_text())
    archive=ARCHIVE/manifest['archive_files'][0]['file']
    if len(manifest['archive_files'])!=1 or sha(archive)!=manifest['compressed_sha256']:raise RuntimeError('Archive changed')
    needed={}
    for name,record in manifest['members'].items():
        original=record['original_repository_path']
        if original in prepared['original_sha256']:
            if record['sha256']!=prepared['original_sha256'][original]:raise RuntimeError('Archive/source pin mismatch')
            if original in needed:raise RuntimeError('Ambiguous archive origin')
            needed[original]=(name,record)
    if len(needed)!=14:raise RuntimeError('Expected exactly14 archived dependencies')
    for group,base in [('output_sha256',HERE),('runtime_sha256',Path('/'))]:
        for name,h in prepared[group].items():
            if sha(base/name)!=h:raise RuntimeError('Stale '+group+': '+name)
    for name,h in prepared['original_sha256'].items():
        if name not in needed and sha(ROOT/safe(name))!=h:raise RuntimeError('Nonarchive original changed: '+name)
    dest.mkdir(parents=True)
    restored={}
    with tarfile.open(str(archive),'r:gz') as t:
        names=set()
        wanted={v[0]:(k,v[1]) for k,v in needed.items()}
        for member in t:
            if member.name in names:raise RuntimeError('Duplicate archive member')
            names.add(member.name)
            if member.name not in wanted:continue
            original,record=wanted[member.name]
            if not member.isfile() or member.size!=record['bytes']:raise RuntimeError('Unsafe/incomplete member')
            target=dest/safe(original);target.parent.mkdir(parents=True,exist_ok=True)
            with t.extractfile(member) as src,target.open('xb') as out:shutil.copyfileobj(src,out,1048576)
            if sha(target)!=record['sha256']:raise RuntimeError('Restored member differs')
            restored[original]={'archive_member':member.name,'sha256':record['sha256'],'bytes':record['bytes']}
        if set(wanted)-names:raise RuntimeError('Missing archive dependency')
    copies={}
    for name,h in prepared['original_sha256'].items():
        if name in restored:continue
        target=dest/safe(name);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(str(ROOT/name),str(target));copies[name]=h
    replay_rel=Path('data/development/hayward_trial_cmj_old_D_replay_REPLAY');replay=dest/replay_rel
    for name in list(prepared['output_sha256'])+['prepared.json','prelaunch_review.json']:
        target=replay/safe(name);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(str(HERE/name),str(target))
    spec=importlib.util.spec_from_file_location('cmj_replay_verify',str(replay/'run.py'));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.verify(json.loads((replay/'prepared.json').read_text()))
    expected=set(prepared['output_sha256'])|{'prepared.json','prelaunch_review.json'}
    actual={str(p.relative_to(replay)) for p in replay.rglob('*') if p.is_file()}
    if actual!=expected:raise RuntimeError('Replay copied an executed/generated artifact')
    result={'status':'passed_input_closure_only','source_sha256':sha(Path(__file__)),'prepared_sha256':sha(HERE/'prepared.json'),'prelaunch_review_sha256':sha(HERE/'prelaunch_review.json'),'archive_manifest_sha256':sha(ARCHIVE/'manifest.json'),'archive_sha256':sha(archive),'scratch_root':str(rel),'replay_directory':str(rel/replay_rel),'archive_restored':restored,'repository_copies':copies,'verified_counts':{'original':len(prepared['original_sha256']),'runtime':len(prepared['runtime_sha256']),'prepared':len(prepared['output_sha256']),'replay_files':len(actual)},'compiler_field_ray_or_inverse_calls':0,'execution_files_copied':False,'replay_input_sha256':{n:sha(replay/n) for n in sorted(actual)},'limitations':['Runtime/compiler pins are checked against this host. Other environments require explicit reviewed provenance; this helper does not rewrite hashes.','The archived full failed-ray path table is restored only in scratch because unchanged run.verify requires its historical hash. It is not duplicated in the publication.']}
    with (dest/'closure.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(str(dest/'closure.json'));print(sha(dest/'closure.json'))
if __name__=='__main__':main()
