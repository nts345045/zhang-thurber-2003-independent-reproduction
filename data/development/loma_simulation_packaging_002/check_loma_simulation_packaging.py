#!/usr/bin/env python3
"""Invented completed-run packaging, restore, and rejection checks."""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
import random
import shutil

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True); parser.add_argument('--work', required=True)
    args = parser.parse_args()
    out, work = [(ROOT/name).resolve() for name in (args.output,args.work)]
    for path in (out,work):
        path.relative_to(ROOT); path.mkdir(parents=True)
    source = ROOT/'diagnostics/package_loma_simulation.py'
    spec = importlib.util.spec_from_file_location('packager',str(source))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    fixture = ROOT/'data/development/analytic_simulation_launcher_002/invented_simulation'
    reviewed = ROOT/'data/development/loma_simulation_packaging_001/fixture_review.json'
    checks = []
    def reject(name, call):
        try:
            call()
        except (ValueError,FileExistsError,FileNotFoundError,OSError,EOFError) as error:
            checks.append(dict(name=name,passed=True,error_type=type(error).__name__,error=str(error)))
        else:
            raise AssertionError('Unexpected acceptance: '+name)
    before = {name:module.info(path) for name,path in module.files(fixture).items()}
    result = module.package(fixture,reviewed,out/'package',4096)
    manifest = json.loads((out/'package/manifest.json').read_text())
    assert len(manifest['parts']) > 1 and all(0<p['bytes']<=4096 for p in manifest['parts'])
    checks.append(dict(name='completed independent-reviewed fixture split and full stream readback',passed=True,**result))
    module.verify(out/'package',manifest,work/'restored')
    restored = {name:module.info(path) for name,path in module.files(work/'restored').items()}
    assert restored == before
    checks.append(dict(name='fresh restore preserves every original byte and filename',passed=True,members=len(restored)))
    reject('existing restore directory',lambda:module.verify(out/'package',manifest,work/'restored'))
    reject('existing archive directory',lambda:module.package(fixture,reviewed,out/'package',4096))
    reject('part bound greater than 50 MiB',lambda:module.package(fixture,reviewed,work/'too_large',module.MAX_PART+1))
    reject('live or interrupted simulation',lambda:module.package(fixture.parent/'interrupted_simulation',reviewed,work/'interrupted',4096))
    stale = work/'stale';shutil.copytree(str(fixture),str(stale))
    with (stale/'observations.csv').open('a') as stream:stream.write('changed\n')
    reject('changed reviewed observations',lambda:module.package(stale,reviewed,work/'stale_output',4096))
    bad = json.loads(reviewed.read_text());bad['simulation_execution_sha256']='0'*64
    module.json_write(work/'stale_review.json',bad)
    reject('review refers to different execution',lambda:module.package(fixture,work/'stale_review.json',work/'wrong_review',4096))
    bad['status']='failed';module.json_write(work/'failed_review.json',bad)
    reject('failed independent review',lambda:module.package(fixture,work/'failed_review.json',work/'failed_review_output',4096))
    corrupt = work/'corrupt';shutil.copytree(str(out/'package'),str(corrupt))
    part = corrupt/manifest['parts'][1]['file'];data=bytearray(part.read_bytes());data[len(data)//2]^=1;part.write_bytes(data)
    reject('corrupted compressed part',lambda:module.verify(corrupt,manifest))
    missing = work/'missing';shutil.copytree(str(out/'package'),str(missing))
    (missing/manifest['parts'][1]['file']).unlink()
    reject('missing compressed part',lambda:module.verify(missing,manifest))
    wrong=copy.deepcopy(manifest);wrong['members']['observations.csv']['sha256']='0'*64
    reject('wrong member hash',lambda:module.verify(out/'package',wrong))
    wrong=copy.deepcopy(manifest);wrong['members']['../escape'] = wrong['members'].pop('observations.csv')
    reject('unsafe member manifest path',lambda:module.verify(out/'package',wrong,work/'unsafe_restore'))
    assert not (work/'unsafe_restore').exists()
    big=work/'large_member';shutil.copytree(str(fixture),str(big))
    rng=random.Random(190); (big/'invented_random_payload.bin').write_bytes(bytes(rng.getrandbits(8) for _ in range(2*module.BLOCK+31)))
    large=module.package(big,reviewed,work/'large_package',65536)
    m=json.loads((work/'large_package/manifest.json').read_text());module.verify(work/'large_package',m,work/'large_restored')
    assert module.info(big/'invented_random_payload.bin')==module.info(work/'large_restored/invented_random_payload.bin')
    checks.append(dict(name='member larger than stream buffer crosses many part boundaries losslessly',passed=True,**large))
    assert {name:module.info(path)for name,path in module.files(fixture).items()}==before
    shutil.copyfile(str(source),str(out/'package_loma_simulation.py'))
    shutil.copyfile(str(Path(__file__).resolve()),str(out/'check_loma_simulation_packaging.py'))
    summary=dict(status='passed',scope='Invented two-event/two-receiver simulation only; no real archive',checks=checks,
        original_fixture_files_unchanged=True,fixture=str(fixture.relative_to(ROOT)),
        independent_fixture_review=str(reviewed.relative_to(ROOT)),review_sha256=module.info(reviewed)['sha256'],
        output_sha256={str(p.relative_to(out)):module.info(p)['sha256']for p in out.rglob('*')if p.is_file()})
    module.json_write(out/'summary.json',summary)
    print(json.dumps(dict(status='passed',checks=len(checks),members=result['members_verified'],parts=result['parts_verified']),indent=2))


if __name__=='__main__':main()
