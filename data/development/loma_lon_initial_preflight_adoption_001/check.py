#!/usr/bin/env python3
"""Compare only invented matrix-preflight outputs with existing frozen O3 binaries."""
import csv
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from run_loma_analytic_simulation import sha

HERE = Path(__file__).resolve().parent


def main():
    out = HERE / 'controls'
    out.mkdir()
    lom = json.loads((ROOT / 'data/loma_lom_initial_preflight_001/preflight_run_manifest.json').read_text())
    parity = json.loads((ROOT / 'data/development/hayward_guard_adoption_checks/001/summary.json').read_text())
    binaries = {'baseline': ROOT / lom['binary'],
                'guarded': ROOT / 'tmp/hayward_guard_adoption_checks/001/guarded/dd'}
    assert sha(binaries['baseline']) == lom['binary_sha256']
    assert sha(binaries['guarded']) == parity['binary_sha256']['guarded']
    source_roots = {'baseline': ROOT / lom['source_directory'],
                    'guarded': ROOT / 'data/development/hayward_guard_adoption_checks/001/guarded_source'}
    summary = dict(status='running', scope=__doc__, commands=[], checks=[],
                   binary_sha256={k:sha(p) for k,p in binaries.items()}, source_sha256={})
    for label, source in source_roots.items():
        names = ['CMakeLists.txt'] + [str(p.relative_to(source)) for p in sorted((source/'src').glob('*')) if p.is_file()]
        summary['source_sha256'][label] = {name:sha(source/name) for name in names}
        for name in names:
            target=out/(label+'_source')/name;target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(str(source/name),str(target))
    for name,digest in summary['source_sha256']['baseline'].items():
        if name!='src/main.cpp': assert summary['source_sha256']['guarded'][name] == digest
    for name,digest in summary['source_sha256']['guarded'].items(): assert sha(ROOT/name)==digest
    summary['checks'].append('All numerical headers/CMake are identical; guarded source is current and matches reviewed O3 binary')
    fixture=ROOT/'data/development/inversion_ray_gate_checks/004/baseline_preflight'
    inputs=('initial_events.csv','initial_grid.csv','stations.csv','observations.csv','truth_grid.csv')
    outputs=('dd_history.csv','dd_matrix_preflight.csv','dd_preflight_ray_status.csv')
    for kind in ('failed_local_flags','declared_spacings'):
        cfg=(fixture/'run.cfg').read_text()
        values=dict(line.split() for line in cfg.splitlines() if line.strip())
        values.update(iterations='1',matrix_preflight_only='1')
        if kind=='declared_spacings':
            values.update(ray_initializer='1',ray_iterations='1000',ray_spacing='0.03125',
                          fmm_spacing='0.125',raycheck_receiver_batch='4')
        cfg=''.join(k+' '+v+'\n' for k,v in values.items())
        for threads in (1,4):
            for label,binary in binaries.items():
                dest=out/('{}_{}_t{}'.format(kind,label,threads));dest.mkdir()
                for name in inputs:shutil.copyfile(str(fixture/name),str(dest/name))
                (dest/'run.cfg').write_text(cfg)
                cmd=[str(binary),'invert',str(dest/'run.cfg'),str(dest),'dd']
                with (dest/'stdout.log').open('x')as stdout,(dest/'stderr.log').open('x')as stderr:
                    code=subprocess.call(cmd,cwd=str(ROOT),env=dict(os.environ,OMP_NUM_THREADS=str(threads),LC_ALL='C'),stdout=stdout,stderr=stderr)
                summary['commands'].append(dict(command=[str(Path(v).relative_to(ROOT)) if v.startswith(str(ROOT)) else v for v in cmd],threads=threads,return_code=code))
                assert code==0
                assert not any((dest/n).exists() for n in ('dd_grid.csv','dd_events.csv','dd_residuals.csv'))
                with (dest/'dd_history.csv').open()as f:assert not list(csv.DictReader(f))
                with (dest/'dd_matrix_preflight.csv').open()as f:
                    matrix=list(csv.DictReader(f));assert len(matrix)==1 and matrix[0]['iteration']=='0'
                with (dest/'dd_preflight_ray_status.csv').open()as f:rays=list(csv.DictReader(f))
                if kind=='failed_local_flags':assert any(r['ray_converged']=='0'for r in rays)
            a=out/('{}_baseline_t{}'.format(kind,threads));b=out/('{}_guarded_t{}'.format(kind,threads))
            assert all((a/n).read_bytes()==(b/n).read_bytes()for n in outputs)
            summary['checks'].append('{}: all three matrix-only outputs byte-identical at {} threads; no inverse result'.format(kind,threads))
        a=out/(kind+'_guarded_t1');b=out/(kind+'_guarded_t4')
        assert all((a/n).read_bytes()==(b/n).read_bytes()for n in outputs)
        summary['checks'].append(kind+': one/four-thread byte parity')
    for label,binary in binaries.items():assert sha(binary)==summary['binary_sha256'][label]
    summary.update(status='passed',real_forward_or_inverse_runs=0,
        mathematical_scope='The guard leaves matrix_preflight_only and diagnostics unchanged; no real LON forward-accuracy or inverse acceptance inferred.',
        artifact_sha256={str(p.relative_to(HERE)):sha(p) for p in sorted(HERE.rglob('*')) if p.is_file()and p.name!='summary.json'})
    (HERE/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(status=summary['status'],checks=len(summary['checks']))))


if __name__=='__main__':main()
