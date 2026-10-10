#!/usr/bin/env python3
"""Freeze one old-kernel Hayward DD attempt with reviewed local-ray trial backtracking."""
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

sys.dont_write_bytecode = True

from run_loma_analytic_simulation import atomic_json, inside, sha, utc, verify_hashes
from run_loma_initial_preflight import disjoint, finite, require, rows, terminate_group, live_group_members
from diagnostics.review_old_kernel_trial_completion import TRIAL_MAIN, review_trials

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
    selected, adoption, adoption_pins = source_adoption(parity, manifest)
    for name,digest in adoption['bridge']['identical_native_numerical_input_sha256'].items():
        require(copied[name]==digest, 'Native input differs from the reviewed old-kernel bridge: '+name)
    require(configuration(data/'run.cfg')==adoption['bridge']['identical_effective_config'],
            'Inverse configuration differs from the reviewed old-kernel bridge')
    evidence = {str(path.relative_to(ROOT)):sha(path) for path in list(pins.values()) +
                [reference/'packaging.json',reference/package['archive'],accuracy_path,parity_path]}
    evidence.update({str((data/n).relative_to(ROOT)):sha(data/n) for n in SAMPLE_FILES})
    evidence.update(adoption_pins)
    return manifest, copied, evidence, parity, selected, adoption, dict(observations=len(observations), rays=count,
              observation_types={str(k):sum(r['type']==str(k) for r in observations) for k in range(3)})


CANDIDATE = 'hayward_old_kernel_trial_backtracking_candidate_001'
ACTUAL = 'hayward_old_kernel_trial_backtracking_controls_001'
INTEGRATION = 'hayward_old_kernel_trial_backtracking_integration_checks_002'
COMPLETION = 'hayward_trial_completion_candidate_002'
COMPLETION_CHECKS = 'hayward_trial_completion_checks_002'
COMPLETION_HELPER = '8406148ed92afa18c43bf96693aaa78185f7961e99e567e4f8aced6d1d858392'
SOURCE_REVIEWS = {
    CANDIDATE+'/prepared.json':'5bb45c57b3f594485abbaf144da3b540f2c7f8d42dc783837976fbe33b5d96dd',
    CANDIDATE+'/root_source_review.json':'c168b6c54018015399608e4d0b28e1854af34020e2cd1a00b78f99e0a466ee54',
    ACTUAL+'/review.json':'fc750af56ea2d2333c7c1c2856a629181ca96a233fec2fd831ee5fd82b5bad5f',
    ACTUAL+'/math_review.json':'f5822b254f0f5404153a6ae1ca69e78a569bfe2cc40907417f1e62068e994e4e',
    INTEGRATION+'/review.json':'7faa22a6bb009a3c8c5470ffb4e7cff6dddf02987dfb3c18db032f7e362fdda6',
    COMPLETION_CHECKS+'/review.json':'e975435edc021696f0e8766e6e7bcb15a45c8bfa2d09e09388ad4e35e2e7374c'}


def compiler_from_cache(text):
    entries=[line for line in text.splitlines() if line.startswith(('CMAKE_CXX_COMPILER:', 'CMAKE_CXX_COMPILER='))]
    require(len(entries)==1 and ':' in entries[0] and '=' in entries[0],
            'Require one well-formed CMake compiler cache key')
    compiler=entries[0].split('=',1)[1]
    require(bool(compiler), 'Require a nonempty CMake compiler cache value')
    return compiler


def source_adoption(parity, preflight):
    """Explicit restored-file bridge; no retrieval, recomputation, or maintained source substitution."""
    development=ROOT/'data/development'; evidence={}
    def pinned(base, mapping):
        for name,digest in mapping.items():
            raw=base/name
            require(not Path(name).is_absolute() and '..' not in Path(name).parts and not raw.is_symlink(),
                    'Unsafe or symlink reviewed evidence path: '+str(raw))
            path=inside(ROOT,raw)
            require(path==raw and path.is_file(),
                    'Missing regular reviewed evidence; restore the published evidence archive: '+str(path))
            require(sha(path)==digest, 'Changed reviewed evidence: '+str(path))
            evidence[str(path.relative_to(ROOT))]=digest
    def document(base,name):
        path=base/name
        require(path.is_file() and not path.is_symlink(), 'Missing restored review document: '+str(path))
        pinned(base,{name:sha(path)})
        return load(path)
    pinned(development,SOURCE_REVIEWS)
    candidate=development/CANDIDATE
    prepared=document(candidate,'prepared.json')
    pinned(ROOT,prepared['input_sha256']);pinned(candidate,prepared['output_sha256'])
    review=document(candidate,'root_source_review.json')
    require(review['status']=='passed_source_review' and review['prepared_sha256']==sha(candidate/'prepared.json'),
            'Source adoption review does not bind the candidate')
    require(prepared['changed_source_files']==['src/main.cpp'], 'Old-kernel candidate changed more than main')
    selected={name:candidate/'after'/name for name in prepared['original_sha256']}
    before=prepared['original_sha256'];after={name:sha(path) for name,path in selected.items()}
    require(before=={name:parity['guarded_source_sha256'].get(name) for name in before}, 'Candidate before-source differs from reviewed guard bridge')
    require(before['src/main.cpp']==REVIEWED_GUARD_MAIN and after['src/main.cpp']==TRIAL_MAIN,
            'Unexpected main in004-to-guard-to-backtracking bridge')
    require(all(after[name]==digest for name,digest in before.items() if name!='src/main.cpp'),
            'A mathematical kernel or CMake file changed')
    require(prepared['bridge']['preflight_main_sha256']==preflight['source_sha256']['src/main.cpp'],
            'Candidate bridge starts from another preflight main')
    for name,digest in prepared['bridge']['identical_shared_kernel_and_cmake_sha256'].items():
        require(preflight['source_sha256'][name]==after[name]==digest, 'Initial mathematical kernel changed: '+name)
    for dirname in (ACTUAL,INTEGRATION,COMPLETION_CHECKS):
        directory=development/dirname
        summary=document(directory,'summary.json');execution=document(directory,'execution.json')
        checked=document(directory,'review.json');plan=document(directory,'prepared.json')
        require(summary['status']==checked['status']=='passed' and execution['status']=='completed' and
                execution['return_code']==0, 'Required reviewed suite did not complete successfully: '+dirname)
        summary_key='controls_summary_sha256' if dirname==COMPLETION_CHECKS else 'summary_sha256'
        require(checked[summary_key]==sha(directory/'summary.json') and
                checked['execution_sha256']==sha(directory/'execution.json'), 'Stale suite review: '+dirname)
        require(summary['prepared_sha256']==sha(directory/'prepared.json'), 'Stale suite preparation')
        for key in ('artifact_sha256','output_sha256','source_sha256'):
            if isinstance(summary.get(key),dict):pinned(directory,summary[key])
        if dirname!=COMPLETION_CHECKS:
            require(plan['candidate_prepared_sha256']==sha(candidate/'prepared.json'), 'Suite used another candidate')
            pinned(ROOT,plan.get('input_sha256',plan.get('original_sha256',{})))
            pinned(directory,plan['output_sha256'])
            source_root=directory/('source/after' if dirname==ACTUAL else 'source')
            require({name:sha(source_root/name) for name in after}==after, 'Suite mathematical source differs')
        else:
            pinned(ROOT,plan['input_sha256']);pinned(directory,plan['prepared_sha256'])
            require(summary['controls_passed']==summary['controls_total']==190, 'Incomplete completion controls')
            for name in ('run_loma_analytic_simulation.py','run_loma_initial_preflight.py',
                         'diagnostics/review_loma_analytic_simulation.py'):
                require(sha(ROOT/name)==plan['prepared_sha256']['source/'+name],
                        'Shared launcher dependency differs from completion controls: '+name)
                pinned(ROOT,{name:sha(ROOT/name)})
            for name,target in summary.get('intentional_symlinks',{}).items():
                require((directory/name).is_symlink() and os.readlink(str(directory/name))==target,
                        'Intentional negative-fixture symlink changed')
    completion=development/COMPLETION
    completion_plan=document(completion,'prepared.json')
    pinned(ROOT,completion_plan['input_sha256']);pinned(completion,completion_plan['output_sha256'])
    helper=completion/'after/diagnostics/review_trial_completion.py'
    require(sha(helper)==COMPLETION_HELPER==sha(ROOT/'diagnostics/review_old_kernel_trial_completion.py'),
            'Completion helper differs from reviewed candidate002 bytes')
    require(prepared['compiler']==parity['compiler'] and prepared['flags']==parity['flags'],
            'Compiler selection or flags differ from the original guard bridge')
    for name,digest in prepared['runtime_sha256'].items():
        require(sha(Path(name))==digest, 'Old-kernel compiler/runtime changed: '+name)
    receipt=dict(candidate_directory=str(candidate.relative_to(ROOT)),candidate_prepared_sha256=sha(candidate/'prepared.json'),
                 bridge=prepared['bridge'],candidate_source_sha256=after,
                 source_mapping={name:str(path.relative_to(ROOT)) for name,path in selected.items()},
                 review_sha256=SOURCE_REVIEWS,completion_helper_sha256=COMPLETION_HELPER,
                 runtime_library_sha256={n:h for n,h in prepared['runtime_sha256'].items() if n!=prepared['compiler']},
                 evidence_scope='Exact old kernel; main-only trial rejection with fixed weights and original halving. No maintained-source replacement.',
                 limitations=['The004-to-guard main change is supported by prior controls, not byte equality.',
                              'Saved completion helper positives and initializer/source-prefix tests do not constitute a full positive controller test with first-arrival residual metadata.',
                              'Initial1Daccuracy does not certify later3Dmodels; final diagnostics and scientific review remain required.'])
    return selected,receipt,evidence


def check_inverse(data, expected):
    # Completion keeps the independently reviewed candidate002 helper and all final initializer gates.
    manifest = load(data/'dd_inversion_run_manifest.json')
    execution = load(data/'dd_inversion_execution.json')
    inverse = [r for r in execution['completed_commands'] if r['stage'] == 'dd_invert']
    require(len(inverse) == 1 and inverse[0]['return_code'] == 0,
            'Require one completed zero-exit inverse command')
    require(manifest['source_sha256']['src/main.cpp'] == TRIAL_MAIN,
            'Completion call path differs from exact candidate003')
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
    trial_evidence = review_trials(data, 'dd', configuration(data/'run.cfg'), history, matrix)
    return dict(status='completed_pending_final_diagnostics', native_events=len(final), native_observations=len(residuals),
                iterations=len(history), last_stage=int(history[-1]['stage']),
                lsqr_converged_iterations=sum(r['lsqr_converged']=='1' for r in history),
                accepted_iterations=sum(float(r['step_fraction'])>0 for r in history),
                scientific_success=False, final_ray_refinement_and_source_checks='required follow-up',
                trial_evidence=trial_evidence,
                final_full_gate=dict(evidence='exact candidate003 main plus successful child return',
                                     source_sha256=TRIAL_MAIN, independent_final_ray_table=False,
                                     limitation='Final finite/local/domain/endpoint/initializer/derivative gate is enforced by the pinned binary; no standalone all-success ray table is emitted.'),
                limitation='Per-evaluation local guard does not certify global first arrival, updated3Daccuracy, or nonlinear convergence')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('preflight','reference','accuracy-review','parity-review','output','build'): parser.add_argument('--'+name,required=True)
    args=parser.parse_args()
    data,reference,accuracy_path,parity_path,out,build=[inside(ROOT,ROOT/p) for p in
        (args.preflight,args.reference,args.accuracy_review,args.parity_review,args.output,args.build)]
    disjoint(data,out,build)
    for protected in (reference,parity_path.parent,ROOT/'data/development'):
        for target in (out,build):
            require(target != protected and target not in protected.parents and protected not in target.parents,
                    'Run directories overlap reviewed evidence')
    require(not out.exists() and not build.exists(),'Require fresh output/build directories')
    manifest,copied,evidence,parity,selected,adoption,expected=reviewed_inputs(data,reference,accuracy_path,parity_path)
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
        record['remaining_live_group_members']=live_group_members(active.pid)
        ledger['completed_commands'].append(record); atomic_json(ledger_path,ledger)
        require(not record['remaining_live_group_members'], 'Supervisor exited while process-group writers remain')
        if code:raise subprocess.CalledProcessError(code,command)
        active=None
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
        scripts=('run_hayward_old_kernel_backtracking.py','run_loma_initial_preflight.py',
                 'run_loma_analytic_simulation.py','diagnostics/review_loma_analytic_simulation.py',
                 'diagnostics/review_old_kernel_trial_completion.py')
        sources=dict(selected)
        sources.update({name:ROOT/name for name in scripts})
        names=sorted(sources)
        source_hashes={name:sha(sources[name]) for name in names}
        for name in names:
            target=source/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(str(sources[name]),str(target))
        verify_hashes(source,source_hashes)
        require({name:source_hashes[name] for name in selected} == adoption['candidate_source_sha256'],
                'Selected old-kernel source changed during frozen copy')
        require(source_hashes['diagnostics/review_old_kernel_trial_completion.py'] == COMPLETION_HELPER,
                'Copied completion helper changed')
        def normalize(info):
            info.uid=info.gid=info.mtime=0;info.uname=info.gname='';info.pax_headers={};return info
        archive=out/'guarded_source.tar.gz'
        with tarfile.open(str(archive),'x:gz') as stream:
            for name in names:stream.add(str(source/name),arcname=name,filter=normalize)
        run(['cmake','--version'],'cmake_version');run(['cmake','-S',source,'-B',build/'compiled'],'configure')
        compiler=compiler_from_cache((build/'compiled/CMakeCache.txt').read_text())
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
        require(libraries == adoption['runtime_library_sha256'], 'Runtime libraries differ from old-kernel controls')
        frozen=dict(mode='dd',source_adoption=adoption,base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=str(ROOT),universal_newlines=True).strip(),
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
                                 'Pure local stopping failures only may reject an unevaluated trial; current/final/mixed failures remain fatal.',
                                 'Old initial forward evidence is reused through004-to-guard-to-main-only-backtracking controls; no direct main or binary equality claim.',
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
        if active is not None:
            signal.signal(signal.SIGTERM,signal.SIG_IGN);signal.signal(signal.SIGINT,signal.SIG_IGN)
            ledger['exception_child']=terminate_group(active)
        ledger.update(status='interrupted' if isinstance(error,(SystemExit,KeyboardInterrupt)) else 'failed',
                      finished_utc=utc(),error=str(error),return_code=getattr(error,'returncode',getattr(error,'code',None)))
        if ledger.get('exception_child',{}).get('remaining_live_group_members'):
            ledger['partial_output_hash_status']='not frozen: process-group writers remain after TERM/KILL'
        else:
            ledger['partial_output_sha256']={p.name:sha(p) for p in out.iterdir() if p.is_file() and p.name not in set(COPIED)|{'dd_inversion_execution.json'}}
        atomic_json(ledger_path,ledger);raise


if __name__=='__main__':main()
