#!/usr/bin/env python3
"""Freeze one guarded Hayward DD attempt after independently reviewed preflight."""
import argparse
import csv
import json
import math
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import sys
import tarfile

from run_loma_analytic_simulation import atomic_json, inside, sha, utc, verify_hashes
from run_loma_initial_preflight import disjoint, finite, require, rows, terminate_group

ROOT = Path(__file__).resolve().parent
COPIED = ('initial_events.csv', 'initial_grid.csv', 'stations.csv', 'observations.csv',
          'selection_manifest.json', 'authoritative_ids_required', 'event_pairs.csv',
          'event_selection.csv', 'initial_geographic_events.csv', 'excluded_picks.csv', 'run.cfg')
THREADS, LIMIT_GIB = 4, 128
REVIEWED_GUARD_MAIN = '8a6f1ea8ea8c37ec71fe01a8971cd63227895192411c91ccc3b82f20727be4ae'
LIMITS = dict(absolute_time_s=2.5e-5, source_euclidean_norm_s_per_km=3e-6)
SAMPLE_FILES = ('initial_ray_convergence.csv', 'initial_ray_derivatives.csv', 'initial_ray_identifiers.csv')
REVIEW_CHECKS = ('full_reference_controls_pass', 'sample_local_flags_pass',
                 'sample_accuracy_assessed', 'finite_difference_truncation_assessed')


def load(path):
    return json.loads(path.read_text())


def configuration(path):
    values = {}
    for line in path.read_text().splitlines():
        words = line.split('#', 1)[0].split()
        if words:
            require(len(words) == 2, 'Malformed inherited configuration')
            values[words[0]] = finite(words[1])
    require(values.get('matrix_preflight_only', 0) == 0 and values.get('iterations', 0) > 0,
            'Require an actual inverse configuration')
    require(values.get('ray_initializer') == 1 and values.get('ray_spacing') == .03125 and
            values.get('fmm_spacing') == .125 and values.get('ray_iterations') == 1000,
            'Configuration differs from assessed forward settings')
    require(values.get('raycheck_receiver_batch', 0) == 0, 'Preserve004 default receiver batching')
    return values


def reviewed_inputs(data, reference, accuracy_path, parity_path):
    manifest = load(data / 'run_manifest.json')
    require(manifest['threads'] == THREADS, 'Preflight thread count differs')
    verify_hashes(ROOT, manifest['sha256'])
    copied = {}
    for name in COPIED:
        key = str((data / name).relative_to(ROOT))
        require(key in manifest['sha256'], 'Unpinned inverse input: ' + name)
        copied[name] = manifest['sha256'][key]
    configuration(data / 'run.cfg')
    ledger = load(data / 'preflight_execution.json'); preflight = load(data / 'preflight.json')
    require(ledger['status'] == 'ready_for_accuracy_review' and ledger['return_code'] == 0 and
            ledger['current_command_return_code'] == 0, 'Preflight is not terminal and successful')
    for name in ('initial_linearize', 'initial_raycheck'):
        matches = [c for c in ledger['completed_commands'] if c['stage'] == name]
        require(len(matches) == 1 and matches[0]['return_code'] == 0, 'Missing successful preflight command: ' + name)
    require(preflight['status'] == 'ready_for_accuracy_review' and not preflight['failures'],
            'Failed preflight diagnostics')
    verify_hashes(data, preflight['sha256'])
    require(set(SAMPLE_FILES) <= set(preflight['sha256']), 'Missing pinned sampled diagnostics')
    observations = list(rows(data / 'observations.csv'))
    absolute = [r for r in observations if r['type'] == '0']
    support = {(r['i'], r['station']) for r in observations}
    support.update((r['j'], r['station_j']) for r in observations if int(r['j']) >= 0)
    require(len(absolute) == len(support) == preflight['absolute_rays'] and
            {(r['i'],r['station']) for r in absolute} == support, 'Initial absolute/full support differs')
    sample, derivatives = [list(rows(data / n)) for n in SAMPLE_FILES[:2]]
    require(len(sample) == preflight['sample_rays'] and len(derivatives) == preflight['derivative_components'],
            'Sample inventory differs')
    for row in sample:
        for prefix in ('production_', 'refined_'):
            require(all(row[prefix + key] == '1' for key in ('converged','initialization_attempted','initialization_succeeded')),
                    'Sample local/initializer flag failed at identified row ' + row['diagnostic_row'])
        for key in ('production_time','refined_time','difference','production_gradient','refined_gradient'):
            finite(row[key])
        for key,value in [('production_path_spacing',.03125),('refined_path_spacing',.015625),
                          ('production_requested_fmm_spacing',.125),('refined_requested_fmm_spacing',.0625)]:
            require(finite(row[key]) == value, 'Sample spacing differs')
    for row in derivatives:
        for prefix in ('plus_','minus_'):
            require(all(row[prefix + key] == '1' for key in ('converged','initialization_attempted','initialization_succeeded')),
                    'Perturbed local/initializer flag failed at identified row ' + row['diagnostic_row'])
        for key in ('production_derivative','refined_derivative','finite_difference','production_error','refined_error'):
            finite(row[key])
    full = load(reference / 'summary.json'); review = load(reference / 'independent_review.json')
    require(full['status'] == 'complete' and review['status'] == 'passed' and not review['material_issue_found'],
            'Full reference was not independently accepted')
    require(review['summary_sha256'] == sha(reference / 'summary.json'), 'Stale full-reference review')
    for key,limit in LIMITS.items():
        require(full['accuracy_control_limits'][key] == limit, 'Reference control limit changed')
    count = len(support)
    require(full['rays'] == full['unique_native_pairs'] == review['verified_pairs'] == count and
            full['accuracy']['all']['both_limits_pass'] == review['both_limits_pass'] == count,
            'Not all native rays pass both continuous-reference controls')
    require(all(review[k] for k in ('native_metadata_fields_all_match','source_column_metadata_all_match',
                'complete_original_absolute_support','source_derivatives_reconstructed_from_sparse_triplets')),
            'Native full-reference audit incomplete')
    require(review['saved_local_convergence_pass'] == review['saved_initialization_pass'] == count,
            'Full reference retains failed ray flags')
    require(finite(review['maximum_absolute_time_error_s']) <= LIMITS['absolute_time_s'] and
            finite(review['maximum_source_error_euclidean_norm_s_per_km']) <= LIMITS['source_euclidean_norm_s_per_km'],
            'Full reference accuracy failed')
    for name in COPIED:
        key = str((data/name).relative_to(ROOT))
        require(full['original_reverified_sha256'].get(key) == copied[name], 'Reference input differs: ' + name)
    for name,digest in preflight['sha256'].items():
        if name.startswith('initial_linearization_'):
            require(full['original_reverified_sha256'].get(str((data/name).relative_to(ROOT))) == digest,
                    'Full reference binds a different linearization')
    package = load(reference / 'packaging.json')
    require(package['status'] == 'verified_lossless' and review['packaging_sha256'] == sha(reference/'packaging.json') and
            sha(reference/package['archive']) == package['archive_info']['sha256'], 'Full reference archive differs')
    accuracy = load(accuracy_path)
    pins = {'preflight_manifest':data/'run_manifest.json','preflight_ledger':data/'preflight_execution.json',
            'preflight_checks':data/'preflight.json','full_reference_summary':reference/'summary.json',
            'full_reference_review':reference/'independent_review.json'}
    require(accuracy['status'] == 'passed' and accuracy['decision'] == 'eligible_for_guarded_dd_attempt' and
            all(accuracy['checks'][k] is True for k in REVIEW_CHECKS), 'Final scientific accuracy review not accepted')
    require(accuracy['preflight_directory'] == str(data.relative_to(ROOT)), 'Accuracy review is for another experiment')
    for key,path in pins.items():
        require(accuracy['sha256'][key] == sha(path), 'Stale scientific review: ' + key)
    require(accuracy['sampled_tables_sha256'] == {n:sha(data/n) for n in SAMPLE_FILES}, 'Stale sampled accuracy review')
    require(bool(accuracy.get('interpretation')) and bool(accuracy.get('limitations')), 'Require scientific interpretation and limitations')
    parity = load(parity_path)
    require(parity['status'] == 'passed' and parity['mathematical_evidence_reuse_eligible'] and
            parity['checks'] and all(r['passed'] for r in parity['checks']), 'Guard adoption controls did not pass')
    require(parity['original004_binary_sha256'] == manifest['sha256'][manifest['binary']], 'Parity baseline differs')
    verify_hashes(parity_path.parent, parity['artifact_sha256'])
    for name,digest in manifest['source_sha256'].items():
        if name.startswith('src/') or name == 'CMakeLists.txt':
            require(parity['baseline_source_sha256'].get(name) == digest, 'Parity used different baseline source: '+name)
            if name != 'src/main.cpp':
                require(parity['guarded_source_sha256'].get(name) == digest,
                        'Mathematical header or CMake changed since full preflight: '+name)
    require(sha(ROOT/'src/main.cpp') == REVIEWED_GUARD_MAIN,
            'Main call path differs from the independently reviewed guard')
    source_names = ['CMakeLists.txt'] + [str(p.relative_to(ROOT)) for p in sorted((ROOT/'src').glob('*')) if p.is_file()]
    for name in source_names:
        require(parity['guarded_source_sha256'].get(name) == sha(ROOT/name), 'Guarded source differs from O3 controls: '+name)
    evidence = {str(path.relative_to(ROOT)):sha(path) for path in list(pins.values()) +
                [reference/'packaging.json',reference/package['archive'],accuracy_path,parity_path]}
    evidence.update({str((data/n).relative_to(ROOT)):sha(data/n) for n in SAMPLE_FILES})
    return manifest, copied, evidence, parity, dict(observations=len(observations), rays=count,
              observation_types={str(k):sum(r['type']==str(k) for r in observations) for k in range(3)})


def check_inverse(data, expected):
    original, final = [list(rows(data/n)) for n in ('initial_events.csv','dd_events.csv')]
    grid0, grid = [list(rows(data/n)) for n in ('initial_grid.csv','dd_grid.csv')]
    require(len(original)==len(final) and len(grid0)==len(grid), 'Changed output model/source inventory')
    bounds={a:(min(finite(r[a]) for r in grid0),max(finite(r[a]) for r in grid0)) for a in 'xyz'}
    for a,b in zip(original,final):
        for key in a:
            if key not in ('x','y','z','t','coordinate_basis'): require(a[key]==b[key], 'Final event identity changed: '+key)
        require(all(bounds[k][0] <= finite(b[k]) <= bounds[k][1] for k in 'xyz'), 'Final source outside grid')
        finite(b['t'])
    for a,b in zip(grid0,grid):
        require(all(finite(b[k])==float(format(float(a[k]),'.12g')) for k in 'xyz') and finite(b['v'])>0,
                'Final grid geometry or velocity invalid')
    observations=list(rows(data/'observations.csv')); residuals=list(rows(data/'dd_residuals.csv'))
    require(len(observations)==len(residuals)==expected['observations'], 'Residual support changed')
    for a,b in zip(observations,residuals):
        require(all(b[k]==v for k,v in a.items() if k!='value'), 'Residual native observation identity changed')
        finite(b['residual'])
        for prefix in ('i_', 'j_') if int(a['j']) >= 0 else ('i_',):
            require(b[prefix+'initialization_attempted'] == b[prefix+'initialization_succeeded'] == '1',
                    'Final residual initializer status failed')
        if int(a['j']) < 0:
            require(all(not value for key,value in b.items() if key.startswith('j_')),
                    'Absolute residual contains an invented j-side initializer')
    coverage=list(rows(data/'dd_coverage.csv'))
    require(len(coverage) == len(grid) and all(r['node'] == str(i) and finite(r['path_length']) >= 0
            for i,r in enumerate(coverage)), 'Invalid or incomplete final ray coverage')
    matrix=list(rows(data/'dd_matrix_preflight.csv'))
    require(bool(matrix) and all(int(r['observation_rows']) == expected['observations'] and
            int(r['columns']) == 4*len(final)+len(grid) for r in matrix), 'Matrix census dimensions changed')
    # Authoritative field data intentionally have no synthetic truth/error slices.
    require(not (data/'dd_slices.csv').exists(), 'Unexpected synthetic truth slices for authoritative field data')
    history=list(rows(data/'dd_history.csv')); require(bool(history),'No completed DD iteration')
    for r in history:
        require(int(r['ray_count'])==int(r['ray_converged_count'])==expected['rays'], 'History contains failed forward rays')
        require(int(r['ray_initialization_attempted_count']) == int(r['ray_initialization_succeeded_count']) == expected['rays'],
                'History contains missing or failed first-arrival initialization')
        for key in ('velocity_step','location_step','step_fraction','objective_before','objective_after',
                    'lsqr_relative_normal_residual','ray_projected_gradient_max','ray_raw_gradient_max'):
            finite(r[key])
        for kind,name in [('0','absolute_rms'),('1','catalog_rms'),('2','precise_rms')]:
            if expected['observation_types'][kind]: finite(r[name])
    require(not list(data.glob('dd_failed_forward*')), 'Failure snapshots coexist with claimed completed inverse')
    return dict(status='completed_pending_final_diagnostics', native_events=len(final), native_observations=len(residuals),
                iterations=len(history), last_stage=int(history[-1]['stage']),
                lsqr_converged_iterations=sum(r['lsqr_converged']=='1' for r in history),
                accepted_iterations=sum(float(r['step_fraction'])>0 for r in history),
                scientific_success=False, final_ray_refinement_and_source_checks='required follow-up',
                limitation='Per-evaluation local guard does not certify global first arrival, updated3Daccuracy, or nonlinear convergence')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('preflight','reference','accuracy-review','parity-review','output','build'): parser.add_argument('--'+name,required=True)
    args=parser.parse_args()
    data,reference,accuracy_path,parity_path,out,build=[inside(ROOT,ROOT/p) for p in
        (args.preflight,args.reference,args.accuracy_review,args.parity_review,args.output,args.build)]
    disjoint(data,out,build)
    for protected in (reference,parity_path.parent):
        for target in (out,build):
            require(target != protected and target not in protected.parents and protected not in target.parents,
                    'Run directories overlap reviewed evidence')
    require(not out.exists() and not build.exists(),'Require fresh output/build directories')
    manifest,copied,evidence,parity,expected=reviewed_inputs(data,reference,accuracy_path,parity_path)
    out.mkdir(parents=True)
    ledger_path=out/'dd_inversion_execution.json'
    ledger=dict(status='preparing',mode='dd',started_utc=utc(),driver_pid=os.getpid(),command=sys.argv,
                threads=THREADS,completed_commands=[],inherited_preflight=str(data.relative_to(ROOT)),
                scientific_success=False,scope='One guarded DD attempt; no automatic other-mode cascade')
    atomic_json(ledger_path,ledger); active=None
    env=dict(os.environ,TMPDIR=str(ROOT/'tmp'),PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS=str(THREADS),
             OPENBLAS_NUM_THREADS='1',LC_ALL='C',CXX=parity['compiler'])
    def run(command,stage,limited=False):
        nonlocal active
        command=list(map(str,command)); measured=['/usr/bin/time','-v','-o',str(out/(stage+'_resources.txt'))]+command
        ledger.update(status='running',current_stage=stage,current_command=command,current_child_pid=None,
                      current_command_started_utc=utc(),child_pid_semantics='GNU time process-group leader')
        atomic_json(ledger_path,ledger)
        def limit():resource.setrlimit(resource.RLIMIT_AS,(LIMIT_GIB*1024**3,LIMIT_GIB*1024**3))
        with (out/(stage+'_stdout.log')).open('x') as stdout,(out/(stage+'_stderr.log')).open('x') as stderr:
            active=subprocess.Popen(measured,cwd=str(ROOT),env=env,stdout=stdout,stderr=stderr,
                                    start_new_session=True,preexec_fn=limit if limited else None)
            ledger['current_child_pid']=active.pid; atomic_json(ledger_path,ledger); code=active.wait()
        record=dict(stage=stage,command=command,supervisor_command=measured,pid=active.pid,return_code=code,finished_utc=utc())
        for line in (out/(stage+'_resources.txt')).read_text().splitlines():
            if 'Maximum resident set size (kbytes):' in line:record['maximum_resident_set_kbytes']=int(line.rsplit(':',1)[1])
        ledger['completed_commands'].append(record); active=None; atomic_json(ledger_path,ledger)
        if code:raise subprocess.CalledProcessError(code,command)
    def interrupted(signum,unused):raise SystemExit(128+signum)
    signal.signal(signal.SIGTERM,interrupted); signal.signal(signal.SIGINT,interrupted)
    try:
        for name in COPIED:shutil.copyfile(str(data/name),str(out/name))
        verify_hashes(out,copied)
        provenance=out/'preflight_provenance';provenance.mkdir()
        provenance_hashes={}
        for label,path in [('manifest',data/'run_manifest.json'),('ledger',data/'preflight_execution.json'),
                           ('checks',data/'preflight.json'),('reference_summary',reference/'summary.json'),
                           ('reference_review',reference/'independent_review.json'),('accuracy_review',accuracy_path),('parity_review',parity_path)]:
            shutil.copyfile(str(path),str(provenance/(label+'.json')))
            provenance_hashes['preflight_provenance/'+label+'.json']=sha(path)
        source=build/'source'; source.mkdir(parents=True)
        names=['CMakeLists.txt','run_hayward_guarded_inversion.py','run_loma_initial_preflight.py',
               'run_loma_analytic_simulation.py','diagnostics/review_loma_analytic_simulation.py']
        names += [str(p.relative_to(ROOT)) for p in sorted((ROOT/'src').glob('*')) if p.is_file()]
        source_hashes={name:sha(ROOT/name) for name in names}
        for name in names:
            target=source/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(str(ROOT/name),str(target))
        verify_hashes(source,source_hashes)
        for name,digest in source_hashes.items():
            if name.startswith('src/') or name == 'CMakeLists.txt':
                require(parity['guarded_source_sha256'].get(name) == digest,
                        'Source changed between eligibility review and frozen copy: '+name)
        require(source_hashes['src/main.cpp'] == REVIEWED_GUARD_MAIN, 'Copied guard call path changed')
        def normalize(info):
            info.uid=info.gid=info.mtime=0;info.uname=info.gname='';info.pax_headers={};return info
        archive=out/'guarded_source.tar.gz'
        with tarfile.open(str(archive),'x:gz') as stream:
            for name in names:stream.add(str(source/name),arcname=name,filter=normalize)
        run(['cmake','--version'],'cmake_version');run(['cmake','-S',source,'-B',build/'compiled'],'configure')
        compiler=next(line.split('=',1)[1] for line in (build/'compiled/CMakeCache.txt').read_text().splitlines() if line.startswith('CMAKE_CXX_COMPILER:FILEPATH='))
        require(sha(Path(compiler))==parity['compiler_sha256'],'Compiler differs from adoption controls')
        flags=(build/'compiled/CMakeFiles/dd.dir/flags.make').read_text().split('CXX_FLAGS = ',1)[1].splitlines()[0]
        require(flags==parity['flags'],'Compiler flags differ from adoption controls')
        run([compiler,'--version'],'compiler_version');run(['cmake','--build',build/'compiled','-j','2'],'compile')
        build_records={}
        for name in ('CMakeCache.txt','CMakeFiles/dd.dir/flags.make','CMakeFiles/dd.dir/link.txt'):
            target=out/'build_provenance'/name;target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(str(build/'compiled'/name),str(target))
            build_records['build_provenance/'+name]=sha(target)
        binary=build/'compiled/dd';run(['ldd',binary],'runtime_libraries')
        libraries={name:sha(Path(name)) for line in (out/'runtime_libraries_stdout.log').read_text().splitlines() for name in line.split() if name.startswith('/')}
        frozen=dict(mode='dd',base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=str(ROOT),universal_newlines=True).strip(),
                    inherited_preflight=str(data.relative_to(ROOT)),inherited_evidence_sha256=evidence,
                    inherited_binary=manifest['binary'],inherited_binary_sha256=manifest['sha256'][manifest['binary']],
                    source_sha256=source_hashes,source_archive_sha256=sha(archive),input_sha256=copied,
                    copied_provenance_sha256=provenance_hashes,build_provenance_sha256=build_records,
                    binary=str(binary.relative_to(ROOT)),binary_sha256=sha(binary),compiler=compiler,
                    compiler_sha256=sha(Path(compiler)),flags=flags,runtime_library_sha256=libraries,
                    cmake_sha256=sha(Path(shutil.which('cmake'))),
                    threads=THREADS,address_space_limit_GiB=LIMIT_GIB,expected_counts=expected,
                    environment={k:env[k] for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','LC_ALL','CXX','TMPDIR')},
                    limitations=['Initial1Dreference applies only to the unchanged starting model and geometry.',
                                 'Per-evaluation guard preserves existing flags; it is not global first-arrival certification.',
                                 'Completion requires later final-model diagnostics and scientific output review.'])
        atomic_json(out/'dd_inversion_run_manifest.json',frozen)
        def verify():
            verify_hashes(out,copied);verify_hashes(source,source_hashes);verify_hashes(ROOT,evidence)
            verify_hashes(out,provenance_hashes);verify_hashes(out,build_records)
            require(sha(binary)==frozen['binary_sha256'] and sha(archive)==frozen['source_archive_sha256'],'Frozen executable/source changed')
            require(sha(Path(compiler))==frozen['compiler_sha256'],'Compiler changed')
            for name,digest in libraries.items():require(sha(Path(name))==digest,'Runtime library changed')
        verify()
        run([binary,'invert',out/'run.cfg',out,'dd'],'dd_invert',True)
        result=check_inverse(out,expected);verify();verify_hashes(data,copied)
        atomic_json(out/'dd_output_contract.json',result)
        outputs={p.name:sha(p) for p in out.iterdir() if p.is_file() and p.name not in set(COPIED)|{'dd_inversion_execution.json'}}
        ledger.update(status='completed_pending_final_diagnostics',return_code=0,finished_utc=utc(),output_sha256=outputs,
                      immutable_inputs_verified=True,original_preflight_verified=True)
        atomic_json(ledger_path,ledger)
    except BaseException as error:
        if active is not None:ledger['exception_child']=terminate_group(active)
        ledger.update(status='interrupted' if isinstance(error,(SystemExit,KeyboardInterrupt)) else 'failed',
                      finished_utc=utc(),error=str(error),return_code=getattr(error,'returncode',getattr(error,'code',None)))
        if ledger.get('exception_child',{}).get('remaining_live_group_members'):
            ledger['partial_output_hash_status']='not frozen: process-group writers remain after TERM/KILL'
        else:
            ledger['partial_output_sha256']={p.name:sha(p) for p in out.iterdir() if p.is_file() and p.name not in set(COPIED)|{'dd_inversion_execution.json'}}
        atomic_json(ledger_path,ledger);raise


if __name__=='__main__':main()
