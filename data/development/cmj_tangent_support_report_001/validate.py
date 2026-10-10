#!/usr/bin/env python3
"""Validate this report against closed saved evidence; no numerical evaluator."""
import collections
import csv
import gzip
import hashlib
import json
import re
from datetime import datetime
from fractions import Fraction as Q
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
D = ROOT/'data/development'
PINS = {}


def pin(path, expected=None):
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert expected is None or digest == expected, str(path)
    PINS[str(path.relative_to(ROOT))] = digest
    return digest


def read(path, expected=None):
    pin(path, expected)
    if path.suffix == '.gz':
        with gzip.open(str(path), 'rt') as stream: return json.load(stream)
    return json.loads(path.read_text())


def reviewed(base_name, review_name, digest):
    base = D/base_name
    review = read(D/review_name, digest)
    assert review['status'] == 'passed'
    prefix = 'native_' if 'native_summary_sha256' in review else ''
    summary = read(base/'summary.json', review[prefix+'summary_sha256'])
    execution = read(base/'execution.json', review[prefix+'execution_sha256'])
    outer = read(base/'outer_reaping.json', review['outer_reaping_sha256'])
    assert execution['return_code'] == 0 and summary['error'] is None
    assert execution['summary_sha256'] == pin(base/'summary.json')
    assert outer['status'] == 'completed_and_reaped' and outer['tool_exit_code'] == 0
    assert outer['summary_sha256'] == pin(base/'summary.json')
    read(base/'prepared.json', review[prefix+'prepared_sha256'])
    return review, summary


def main():
    assert __debug__, 'Assertions must remain enabled'
    target = OUT/'validation.json'
    assert not target.exists(), 'Preserve existing validation'
    compilation = read(OUT/'compile.json')
    assert compilation['status'] == 'completed'
    assert [x['return_code'] for x in compilation['commands']] == [0, 0]
    pin(ROOT/'report/report.pdf', compilation['report_sha256'])
    pin(ROOT/'README.md', compilation['readme_sha256'])
    pin(ROOT/'FAILURE_SUMMARY.md', compilation['failure_summary_sha256'])
    assert len(compilation['tex_source_sha256']) == 16
    for name, digest in compilation['tex_source_sha256'].items():
        pin(ROOT/name, digest)
    for name, digest in compilation['output_sha256'].items():
        pin(OUT/name, digest)
    closed_compile = read(OUT/'compile_execution_receipt.json')
    assert closed_compile['status'] == 'completed_and_reaped' and closed_compile['return_code'] == 0 and closed_compile['child_reaped']
    assert closed_compile['compile_sha256'] == pin(OUT/'compile.json') and closed_compile['report_sha256'] == compilation['report_sha256']
    logs = {}
    for number in (1, 2):
        lines = (OUT/('pass%d_report.log' % number)).read_text().splitlines()
        errors = [x for x in lines if re.search(r'^!|Overfull', x)]
        undefined = [x for x in lines if re.search(r'undefined', x, re.I)]
        warnings = [x for x in lines if re.search(r'\bwarning:', x, re.I)]
        known = 'pdfTeX warning: pdflatex (file ../figures/location_errors.pdf): PDF inclusion: '
        allowed = [known]
        if number == 1:
            allowed.append('LaTeX Warning: Label(s) may have changed. Rerun to get cross-references right.')
        if number == 1:
            first_reference = [x for x in warnings if re.fullmatch(r"LaTeX Warning: Reference `tab:cmj_final_support' on page \d+ undefined on input ", x)]
            assert len(first_reference) == 1
            allowed += first_reference + ['LaTeX Warning: There were undefined references.']
            assert set(undefined) == set(first_reference + ['LaTeX Warning: There were undefined references.'])
        else:
            assert not undefined
        assert not errors
        assert warnings.count(known) == 1 and all(w in allowed for w in warnings), warnings
        assert any('multiple pdfs with page group included in a single page' in x for x in lines)
        logs[str(number)] = dict(errors_or_overfull=errors, undefined=undefined, warnings=warnings)

    prior_validation = read(D/'cmj_half_step_kernel_report_001/validation.json',
        'a932eed55821624f48e4533f4894c78254fdcb3107a753be63a9c2b05c55b0a2')
    assert prior_validation['status'] == 'passed'
    iteration, its = reviewed('hayward_cmj_tangent_iteration_001',
        'hayward_cmj_tangent_iteration_review_001/review.json',
        '4bba5bf6122237776c7478780da0619f6c531d714d717372c60b062772fdc57b')
    final, fs = reviewed('hayward_cmj_final_tangent_support_001',
        'hayward_cmj_final_tangent_support_review_001/review.json',
        'a6020400eb0d8fe33ed1a63f6668f6c042b6fccbcfc688442887d4f49e8612e3')
    for directory, digest, checker in [
        ('hayward_cmj_tangent_iteration_review_001','286b6e6c230227c9beb59ba90fda8fafc3fe939d48336da3528cb4867c9aa0cd',iteration),
        ('hayward_cmj_final_tangent_support_review_001','3b5b3ef63fe5f77a58a5ba7ef572d5af87010d00d2253b3dca753964c9ac9515',final)]:
        receipt = read(D/directory/'execution_receipt.json', digest)
        assert receipt['status'] == 'passed' and receipt['return_code'] == 0 and receipt['child_reaped']
        for name, expected in receipt['output_sha256'].items(): pin(D/directory/name, expected)
        pin(D/directory/'check_saved.py', checker['checker_sha256'])
    assert iteration['pure_scalar_checks'] == 676006 and final['checks'] == 90213
    assert len(final['input_sha256']) == 378
    assert all(iteration[k] == 0 for k in ('new_compiler_calls','new_evaluator_calls','new_gradient_integrations','new_metric_calls'))
    assert all(final[k] == 0 for k in ('numerical_integrations','numerical_evaluator_imports','fitting_calls','native_calls'))
    assert fs['counts'] == dict(attempted_edges=2058,completed_edges=2058,attempted_normal_patches=65,completed_normal_patches=65,proposal_calls=2)
    assert all(fs[k] == 0 for k in ('trace_calls','field_calls','optimizer_iterations','metric_solves','rounded_trials'))
    assert fs['fixed_endpoint_partials_reported'] is fs['source_model_accuracy_assessed'] is False
    controls = read(D/'hayward_cmj_final_tangent_support_001/controls/summary.json',
        'c640ff4c1174e28a704705c80c49e201113fb1c76949bd9a2defcfb0d44eb8b4')
    control_review = read(D/'hayward_cmj_final_tangent_support_001/controls/review.json',
        '7cd2307868429e1a4aed4b75245e2000884ab3f8c3ec147d16d4b117ee1bed45')
    assert controls['status'] == control_review['status'] == 'passed' and len(controls['checks']) == 20 and all(v['passed'] for v in controls['checks'])
    assert control_review['summary_sha256'] == pin(D/'hayward_cmj_final_tangent_support_001/controls/summary.json')
    cut_dir = D/'hayward_cmj_original_cut_inventory_001'
    cut = read(cut_dir/'review.json','3c597f4b8f56657b5b80118c83d353b38c1a39bed6bfafce68b43f45b35461d1')
    cut_receipt = read(cut_dir/'review_execution.json','ae145bc387eab072fa363f3a2fd7b5f29ed1901f0b2fc329b08667087699eeba')
    cut_run = read(cut_dir/'execution_receipt.json',cut['execution_receipt_sha256'])
    cs = read(cut_dir/'summary.json',cut['summary_sha256'])
    assert cut['status'] == cut_receipt['status'] == cut_run['status'] == 'passed'
    assert cut_receipt['return_code'] == cut_run['return_code'] == 0 and cut_receipt['child_reaped'] and cut_run['child_reaped']
    assert cut_receipt['review_sha256'] == pin(cut_dir/'review.json') and cut_run['summary_sha256'] == pin(cut_dir/'summary.json')
    for receipt in (cut_receipt,cut_run):
        for name, expected in receipt['output_sha256'].items(): pin(cut_dir/name, expected)
    pin(cut_dir/'review_saved.py',cut['checker_sha256']); pin(cut_dir/'run.py',cs['source_sha256'])
    assert all(cs[k] == 0 for k in ('evaluator_calls','field_calls','integration_calls','path_mutations'))
    assert iteration['native_contexts'] == final['native_contexts'] == fs['native_contexts'] == cut['native_contexts'] == cs['native_contexts']
    assert [x['event'] for x in iteration['cases']] == [x['event'] for x in final['cases']] == [x['event'] for x in cs['cases']] == [981,987]
    quantities = []
    for i, (it, fa, original) in enumerate(zip(iteration['cases'], final['cases'], cs['cases'])):
        identity = final['native_contexts'][i]
        assert all(it[k] == fa[k] == identity[k] for k in ('event','station','native_context','catalog_uses')) and len(identity['catalog_uses']) == 9
        assert it['accepted_updates'] == (16,38)[i] and it['action_evaluated_trials'] == (32,152)[i]
        assert it['attempt_counts'] == [(2,4)[i]]*(16,38)[i] and it['reason'] == 'diagnostic_available_norm_reached'
        computed = Q(float.fromhex(it['final_available_norm_hex']))
        assert (Q('8.18205e-8'),Q('9.61835e-8'))[i] <= computed < (Q('8.18215e-8'),Q('9.61845e-8'))[i]
        assert all(x['original_convergence_flag'] == '0' and x['candidate_convergence_status'] is None for x in (it,fa))
        assert fa['saved_edges'] == (1028,1030)[i] and fa['aligned_edges'] == (30,31)[i] and fa['normal_patches'] == (32,33)[i]
        assert fa['full_support_status'] == 'feasible_constant_patch_support'
        available = list(map(Q,fa['available_squared_bounds'])); support = list(map(Q,fa['feasible_support_squared_bounds']))
        assert 0 <= available[0] <= available[1] < Q('1e-7')**2 and 0 <= support[0] <= support[1] < (Q('8.1822e-8'),Q('9.6185e-8'))[i]**2 < Q('1e-7')**2
        assert (Q('8.18205e-8'),Q('9.61835e-8'))[i]**2 <= available[0] <= available[1] < (Q('8.18215e-8'),Q('9.61845e-8'))[i]**2
        lo,hi = map(Q,fa['net_action'])
        assert lo <= hi < 0 and hi-lo < Q('6e-32') and fa['net_action_classification'] == 'resolved_decrease'
        assert (Q('-3.39215e-11'),Q('-5.89975e-11'))[i] <= lo <= hi < (Q('-3.39205e-11'),Q('-5.89965e-11'))[i]
        brief=fs['cases'][i]; detailed=read(D/'hayward_cmj_final_tangent_support_001'/brief['result_file'],brief['result_sha256'])
        assert detailed['proposal']['sweeps'] == (10000,1894)[i] and detailed['proposal']['termination'] == ('sweep_budget','coefficients_unchanged')[i]
        assert len(detailed['full_support']['ordinary_contributions_in_blocked_slots']) == 2
        assert detailed['full_support']['norm']['available_component_count'] == (3081,3087)[i]
        assert detailed['full_support']['norm']['unavailable_component_count'] == detailed['full_support']['norm']['exact_physical_boundary_component_count'] == 0
        assert detailed['available_norm']['available_component_count'] == (3050,3055)[i] and detailed['available_norm']['unavailable_component_count'] == (31,32)[i]
        assert original['exact_crossings'] == original['core_plane_insertions'] == 30
        assert all(original[k] == 0 for k in ('omitted_exact_crossings','spurious_extra_cuts','skipped_segments','duplicate_binary_cuts'))
        quantities.append(dict(event=it['event'],accepted_updates=it['accepted_updates'],trials=it['action_evaluated_trials'],
            accepted_fraction=('1/2','1/8')[i],computed_available_norm_exact=str(computed),available_squared_bounds=fa['available_squared_bounds'],
            feasible_support_squared_bounds=fa['feasible_support_squared_bounds'],net_action=fa['net_action'],
            fit_sweeps=detailed['proposal']['sweeps'],fit_termination=detailed['proposal']['termination'],original_crossings=30,original_cut_omissions=0))
    assert sum(v['trials'] for v in quantities) == 184

    links, literals, figures, resource_ids = [], [], [], []
    for name in ('README.md', 'FAILURE_SUMMARY.md'):
        for link in re.findall(r'\[[^\]]*\]\(([^)]+)\)', (ROOT/name).read_text()):
            if re.match(r'(?:https?://|mailto:|#)', link):
                continue
            path = link.split('#')[0]
            assert (ROOT/path).exists(), path
            links.append(dict(document=name, path=path))
    for name in compilation['tex_source_sha256']:
        path = ROOT/name
        text = path.read_text()
        for literal in re.findall(r'\\path\{([^}]+)\}', text):
            if literal.startswith('quakeml:'):
                resource_ids.append(dict(document=name, resource_id=literal))
                continue
            resolved = ROOT/literal
            if not resolved.exists():
                assert '/' not in literal.rstrip('/'), literal
                resolved = D/literal
            assert resolved.exists(), literal
            literals.append(dict(document=name, path=str(resolved.relative_to(ROOT))))
        for literal in re.findall(r'\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}', text):
            resolved = next((p.resolve() for p in (path.parent/literal, ROOT/'figures'/literal) if p.exists()), None)
            assert resolved is not None, literal
            figures.append(dict(document=name, path=str(resolved.relative_to(ROOT)), sha256=pin(resolved)))
    panels = list(csv.DictReader((ROOT/'data/panel_audit.csv').open()))
    pin(ROOT/'data/panel_audit.csv')
    panel_json = read(ROOT/'data/panel_audit.json')
    counts = dict(collections.Counter(x['status'] for x in panels))
    assert counts == {'independently reproduced':1, 'partially reproduced':61}
    assert [(x['panel'],x['status']) for x in panels] == [(x['panel'],x['status']) for x in panel_json]
    prior = read(D/'cmj_half_step_kernel_report_001/compile.json')
    for name in ('report/panel_table.tex','report/panel_details.tex'):
        pin(ROOT/name, prior['tex_source_sha256'][name])
    prose = ' '.join((ROOT/'report/recovery_checkpoint.tex').read_text().split())
    for phrase in ('16 and 38 updates in 32 and 152 trials', '184 rounded trial geometries',
                   '8.1821', '9.6184', '8.1822', '9.6185', '-3.3921', '-5.8997',
                   '10,000-sweep cap', '1,894 sweeps', '90,213 checks', '65 face pieces',
                   'a complete supporting vector for the first variation', 'Neither outcome certifies a minimum',
                   'source/model derivative accuracy or first-arrival selection', '30 open-segment grid-plane crossings'):
        assert phrase in prose, phrase
    inventory = dict(markdown_links=links, tex_literal_paths=literals, figures=figures, provider_resource_ids=resource_ids)
    (OUT/'path_inventory.json').write_text(json.dumps(inventory,indent=2)+'\n')
    pin(OUT/'path_inventory.json')
    pages = int(re.search(r'^Pages:\s+(\d+)',(OUT/'pdfinfo.txt').read_text(),re.M).group(1))
    result = dict(status='passed', checked_utc=datetime.utcnow().isoformat()+'Z', checker_sha256=pin(Path(__file__).resolve()),
        scope='Compilation, document links and closed reviewed quantities only; no numerical evaluator or new scientific threshold.',
        compile_sha256=pin(OUT/'compile.json'), report_sha256=compilation['report_sha256'], pdf_pages=pages,
        compile_execution_receipt_sha256=pin(OUT/'compile_execution_receipt.json'),
        compile_passes=2, tex_sources=16, logs=logs, input_sha256=PINS, panel_counts=counts,
        markdown_links=len(links), tex_literal_paths=len(literals), figures=len(figures),
        changed_pages_for_visual_review=[28,29,30,31], new_quantities=quantities,
        visual_review_status='pending root inspection of separately rendered pages')
    target.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status='passed',validation_sha256=pin(target),pdf_pages=pages,
                         markdown_links=len(links),tex_literal_paths=len(literals),figures=len(figures))))


if __name__ == '__main__':
    main()
