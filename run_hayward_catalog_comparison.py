#!/usr/bin/env python3
"""Prepare, build and attempt one guarded catalog-only Hayward comparison."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import signal
import sys

import rebuild_hayward_corrected as run


ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT / 'data/development/hayward_catalog_comparisons_001'
HELPER_SHA256 = 'a9a07fa490b8eecdbdc10e3118288fbc3692b04800b75b224a53d8e763182769'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', required=True, choices=('standard', 'loc1d'))
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--build', required=True, type=Path)
    parser.add_argument('--preparation-python', default=sys.executable)
    parser.add_argument('--cxx', default='c++')
    args = parser.parse_args()
    run.require(sys.platform.startswith('linux'), 'Linux process-group ownership is required')
    run.require(run.sha(ROOT / 'rebuild_hayward_corrected.py') == HELPER_SHA256,
                'Shared preparation/lifecycle helper changed')
    output = run.fresh_path(args.output, ROOT / 'data')
    build = run.fresh_path(args.build, ROOT / 'tmp')
    preparation_python, cxx, cmake = [run.executable(v) for v in
                                     (args.preparation_python, args.cxx, 'cmake')]
    mapping = json.loads((run.SOURCES / 'source_mapping.json').read_text())
    expected = json.loads((run.SOURCES / 'scientific_inputs.json').read_text())
    package = json.loads((PACKAGE / 'manifest.json').read_text())
    run.verify(run.SOURCES, mapping['package_sha256'])
    run.verify(ROOT, package['sha256'])
    # This comparison consumes the saved catalog selection only, with no CC inputs.
    inputs = {name: digest for name, digest in expected['input_sha256'].items()
              if name.startswith('data/authoritative/')}
    inputs.update(expected['provider_source_sha256'])
    run.verify(ROOT, inputs)
    build.mkdir(parents=True)
    for name in ('logs', 'tmp', 'cache', 'cache/matplotlib', 'cache/texmf'):
        (build / name).mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    for name in ('PYTHONOPTIMIZE', 'PYTHONPATH', 'CFLAGS', 'CXXFLAGS', 'CPPFLAGS',
                 'LDFLAGS', 'CMAKE_PREFIX_PATH'):
        env.pop(name, None)
    env.update(PYTHONPATH=str(ROOT), PYTHONDONTWRITEBYTECODE='1', OMP_NUM_THREADS='4',
               OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1', LC_ALL='C', CXX=cxx,
               TMPDIR=str(build / 'tmp'), XDG_CACHE_HOME=str(build / 'cache'),
               MPLCONFIGDIR=str(build / 'cache/matplotlib'),
               TEXMFHOME=str(build / 'cache/texmf'), TEXMFVAR=str(build / 'cache/texmf'),
               TEXMFCONFIG=str(build / 'cache/texmf'))
    outcome = dict(status='running', mode=args.mode, started_utc=run.utc(), commands=[],
                   return_code=None, failed_stage=None, outputs_stable=False,
                   scientific_success=False, input_sha256=inputs, output_sha256={},
                   entrypoint_sha256=run.sha(Path(__file__)), helper_sha256=HELPER_SHA256,
                   source_mapping_sha256=run.sha(run.SOURCES / 'source_mapping.json'),
                   comparison_manifest_sha256=run.sha(PACKAGE / 'manifest.json'),
                   history_metrics_scope='pre-update',
                   limitations=['Catalog-only comparison; no new waveform measurement.',
                                'Initial reference accuracy does not validate later moved sources or models.',
                                'Command completion and raw accepted snapshot names require separate scientific review.',
                                'No automatic retry, covariance calculation or result promotion.'])
    previous = {}

    def interrupted(signum, frame):
        raise KeyboardInterrupt('Received signal %d; closing only the owned child group' % signum)

    for sig in (signal.SIGINT, signal.SIGTERM):
        previous[sig] = signal.signal(sig, interrupted)
    stage = 'preparation_runtime'
    try:
        run.write_json(build / 'execution.json', outcome)
        run.run_stage([preparation_python, '-c',
                       'import json,sys,numpy,requests; print(json.dumps(dict(python=sys.version, '
                       'numpy=numpy.__version__, requests=requests.__version__)))'],
                      stage, build, env, outcome)
        outcome['preparation_runtime'] = json.loads((build / 'logs/preparation_runtime.stdout').read_text())
        stage = 'catalog_preparation'
        run.run_stage([preparation_python, run.SOURCES / 'prepare_hayward.py',
                       '--selection', 'reproduction', '--output', output], stage, build, env, outcome)
        stage = 'catalog_compatibility'
        run.catalog_compatibility(output, expected)
        shutil.copyfile(str(PACKAGE / 'run.cfg'), str(output / 'run.cfg'))
        outcome['prepared_input_sha256'] = {str(p.relative_to(output)): run.sha(p)
                                           for p in output.rglob('*') if p.is_file()}
        outcome['counts'] = dict(events=1092, receiver_epochs=372, grid_nodes=462,
                                 absolute_rows=14262, catalog_dd_rows=44718, cc_rows=0,
                                 observations=58980, native_rays=14262)
        shutil.copytree(str(run.SOURCES / 'source'), str(build / 'source'))
        stage = 'cmake_configure'
        run.run_stage([cmake, '-S', build / 'source', '-B', build / 'build',
                       '-DCMAKE_CXX_COMPILER=' + cxx, '-DCMAKE_BUILD_TYPE=',
                       '-DCMAKE_CXX_FLAGS=', '-DCMAKE_EXE_LINKER_FLAGS='], stage, build, env, outcome)
        stage = 'cmake_build'
        run.run_stage([cmake, '--build', build / 'build', '--parallel', '2'], stage, build, env, outcome)
        binary = build / 'build/dd'
        outcome['binary_sha256'] = run.sha(binary)
        outcome['built_source_sha256'] = {str(p.relative_to(build / 'source')): run.sha(p)
                                         for p in (build / 'source').rglob('*') if p.is_file()}
        run.require(outcome['built_source_sha256'] == mapping['numerical_source_sha256'],
                    'Compiled source differs from the frozen guarded snapshot')
        stage = 'runtime_libraries'
        run.run_stage([run.executable('ldd'), binary], stage, build, env, outcome)
        linked = (build / 'logs/runtime_libraries.stdout').read_text()
        run.require('not found' not in linked, 'Unresolved runtime library')
        libraries = sorted(set(re.findall(r'(?:=>\s*)?(/[^\s(]+)', linked)))
        run.require(libraries, 'No compiled runtime libraries recorded')
        outcome['runtime_library_sha256'] = {p: run.sha(Path(p)) for p in libraries}
        run.verify(ROOT, inputs)
        run.verify(ROOT, package['sha256'])
        run.verify(run.SOURCES, mapping['package_sha256'])
        run.verify(output, outcome['prepared_input_sha256'])
        stage = args.mode + '_invert'
        run.run_stage([binary, 'invert', output / 'run.cfg', output, args.mode],
                      stage, build, env, outcome, native=True)
        outcome.update(status='completed_attempt_pending_scientific_review', return_code=0)
    except BaseException as error:
        last = outcome['commands'][-1] if outcome['commands'] else {}
        code = last.get('return_code') if last.get('stage') == stage else None
        outcome.update(status='failed_preserved', failed_stage=stage, error=repr(error),
                       return_code=code if code not in (None, 0) else
                       (130 if isinstance(error, KeyboardInterrupt) else 1))
    finally:
        outcome['finished_utc'] = run.utc()
        outcome['outputs_stable'] = all(c['outputs_stable'] for c in outcome['commands'])
        try:
            if outcome['outputs_stable']:
                output.mkdir(exist_ok=True)
                outcome['output_sha256'] = {str(p.relative_to(output)): run.sha(p)
                                           for p in output.rglob('*') if p.is_file()}
                run.write_json(output / 'comparison_outcome.json', outcome)
            run.write_json(build / 'execution.json', outcome)
        finally:
            for sig, handler in previous.items():
                signal.signal(sig, handler)
    print(json.dumps({k: outcome[k] for k in
                      ('mode', 'status', 'return_code', 'failed_stage', 'outputs_stable')}, sort_keys=True))
    code = outcome['return_code']
    return code if code >= 0 else 128 - code


if __name__ == '__main__':
    sys.exit(main())
