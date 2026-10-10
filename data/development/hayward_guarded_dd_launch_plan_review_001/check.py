#!/usr/bin/env python3
"""Read the concrete launch plan and invoke only the launcher's read-only gate."""
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
PLAN = ROOT / 'data/development/hayward_guarded_dd_launch_plan_001'


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            digest.update(block)
    return digest.hexdigest()


def need(ok, message):
    if not ok:
        raise ValueError(message)


def load(path):
    return json.loads(path.read_text())


def rows(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def check():
    plan = load(PLAN / 'plan.json')
    need(sha(PLAN / 'plan.json') == '271a02a4ee019eb92193306c264e661550fcce0e658b06b46e144e87fcb2e7e3',
         'Unexpected plan')
    need(plan['status'] == 'prepared_launch_plan_not_executed' and
         not plan['inverse_launched'] and not plan['scientific_success'], 'Plan misstates execution')
    data = ROOT / plan['preflight']
    for name, digest in plan['input_sha256'].items():
        need(sha(data / name) == digest, 'Changed004 input: ' + name)
    for name, digest in plan['source_sha256'].items():
        need(sha(ROOT / name) == sha(PLAN / 'source' / name) == digest, 'Changed plan source: ' + name)
    for name, digest in plan['output_sha256'].items():
        need(sha(PLAN / name) == digest, 'Changed plan artifact: ' + name)
    need((PLAN / 'proposed_run.cfg').read_bytes() == (data / 'run.cfg').read_bytes(), 'Changed scientific configuration')
    named = {key.lstrip('-').replace('-', '_'): plan['command'][i + 1]
             for i, key in enumerate(plan['command']) if key.startswith('--')}
    need(plan['command'][:2] == ['python3', 'run_hayward_guarded_inversion.py'], 'Unexpected command')
    need(named['output'] == plan['output'] and named['build'] == plan['build'] and named['preflight'] == plan['preflight'],
         'Command/plan path mismatch')
    out, build = [ROOT / plan[k] for k in ('output', 'build')]
    protected = [data, ROOT / named['reference'], (ROOT / named['parity_review']).parent,
                 (ROOT / named['accuracy_review']).parent, PLAN]
    need(not out.exists() and not build.exists(), 'Proposed run is not fresh')
    for a in (out, build):
        for b in protected + ([build] if a == out else [out]):
            need(a != b and a not in b.parents and b not in a.parents, 'Proposed run overlaps protected evidence')
    accuracy = ROOT / named['accuracy_review']
    need(sha(accuracy) == 'd1012da3b7a3504db3394bc97892769ca8219836b23437e824aca4a5a91cc448',
         'Unexpected scientific accuracy review')
    for name, digest in load(accuracy)['sha256'].items():
        if name.startswith('sampled_'):
            target = accuracy.parent / ('summary.json' if name == 'sampled_summary' else 'review.json')
            need(sha(target) == digest, 'Changed reviewed sample package: ' + name)
    sys.path.insert(0, str(ROOT))
    spec = importlib.util.spec_from_file_location('reviewed_guarded_launcher', ROOT / plan['command'][1])
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    manifest, copied, evidence, parity, actual = module.reviewed_inputs(
        data, ROOT / named['reference'], accuracy, ROOT / named['parity_review'])
    need(copied == plan['input_sha256'], 'Launcher gate selected different input hashes')
    expected = plan['expected']
    need(actual == dict(observations=expected['observations'], rays=expected['ray_support'],
                        observation_types=expected['observation_types']), 'Launcher support differs from plan')
    events, stations, obs = [rows(data / name) for name in ('initial_events.csv','stations.csv','observations.csv')]
    need(len(events) == expected['events'] == 1092 and len(stations) == expected['native_receiver_epochs'] == 372,
         'Native source/epoch count changed')
    coordinates = {tuple(float(r[a]) for a in 'xyz') for r in stations}
    need(len(coordinates) == expected['physical_receiver_coordinate_keys'] == 37, 'Receiver coordinate sharing changed')
    cfg = module.configuration(PLAN / 'proposed_run.cfg')
    for key, value in [('iterations',18),('stage_length',6),('smoothing',10),('damping',.1),
                       ('pair_distance',10),('catalog_only_dd',1),('ray_initializer',1),
                       ('ray_spacing',.03125),('fmm_spacing',.125),('ray_iterations',1000)]:
        need(cfg[key] == value, 'Changed configuration: ' + key)
    need(not any(k.startswith('stage') and k.endswith('_weight') for k in cfg), 'Unexpected stage override')
    need(plan['numerical_settings']['stage_row_factors'] == [[1,.1,0],[.1,1,0],[.1,1,0]] and
         module.THREADS == plan['numerical_settings']['threads'] == 4 and
         module.LIMIT_GIB == plan['numerical_settings']['address_space_limit_GiB'] == 128,
         'Plan schedule/resources differ from launcher/source')
    need(plan['preflight_manifest_sha256'] == sha(data/'run_manifest.json') and
         plan['preflight_ledger_sha256'] == sha(data/'preflight_execution.json') and
         plan['preflight_checks_sha256'] == sha(data/'preflight.json') and
         plan['adoption_summary_sha256'] == sha(ROOT/named['parity_review']), 'Plan evidence pin changed')
    fixture = ROOT/'data/development/hayward_guarded_launcher_checks/002'
    need(plan['launcher_controls_summary_sha256'] == sha(fixture/'summary.json') and
         plan['launcher_root_review_sha256'] == sha(fixture/'root_review.json'), 'Launcher test/review changed')
    need(plan['compiler']['sha256'] == sha(Path(plan['compiler']['path'])) == parity['compiler_sha256'] and
         plan['compiler']['flags'] == parity['flags'], 'Compiler/flags differ from O3 evidence')
    need(not out.exists() and not build.exists(), 'Read-only gate unexpectedly created run directories')
    for name, digest in plan['source_sha256'].items():
        need(sha(ROOT/name) == sha(PLAN/'source'/name) == digest, 'Source changed during review')
    return dict(status='passed_concrete_plan_review',material_issue_found=False,
                plan_sha256=sha(PLAN/'plan.json'),readme_sha256=sha(PLAN/'README.md'),
                proposed_config_sha256=sha(PLAN/'proposed_run.cfg'),accuracy_review_sha256=sha(accuracy),
                launcher_readonly_gate_passed=True,actual_support=actual,events=len(events),
                native_receiver_epochs=len(stations),exact_receiver_coordinate_keys=len(coordinates),
                frozen_input_pins=len(copied),frozen_source_pins=len(plan['source_sha256']),
                current_and_copied_sources_match=True,fresh_disjoint_output_and_build=True,
                mathematical_headers_and_CMake_match_frozen004=True,
                compiler_and_O3_parity_match=True,source_sha256=plan['source_sha256'],
                reviewed_launcher_evidence_sha256=evidence,checker_sha256=sha(Path(__file__)),
                no_compile_launch_ray_or_reference_evaluation=True,
                source_review_findings=[
                    'catalog_only_dd stage factors and all inherited inverse/discretization settings are unchanged.',
                    'checked_rays gates current, trial and final rays before objective/Jacobian/final use.',
                    'Rejected rays retain identified failure paths and distinct candidate/last-accepted states.',
                    'Fresh source/binary/build/runtime snapshots are reverified against reviewed adoption evidence.',
                    'Completion remains pending final-model diagnostics and scientific_success=false.'],
                limitations=[
                    'The initial depth-only reference does not establish accuracy or global earliest arrivals in later3Dmodels.',
                    'Existing local stopping flags may pass without an independently accurate first arrival; the guard preserves that limitation.',
                    'Accepted-step, LSQR, nonlinear, final-ray/refinement/source and native-output reviews remain required.',
                    'The durable detached controller is a launch-time artifact; this review does not assert its execution or exit status.',
                    'Only the catalog-only DD attempt is assessed; no additional modes or CC rows are selected.'])


if __name__ == '__main__':
    print(json.dumps(check(),indent=2,allow_nan=False))
