#!/usr/bin/env python3
"""Validate this report against closed saved evidence; no numerical evaluator."""
import collections
import csv
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
        assert not errors and not undefined
        assert warnings.count(known) == 1 and all(w in allowed for w in warnings), warnings
        assert any('multiple pdfs with page group included in a single page' in x for x in lines)
        logs[str(number)] = dict(errors_or_overfull=errors, undefined=undefined, warnings=warnings)

    half, hs = reviewed('hayward_cmj_tangent_half_step_001',
        'hayward_cmj_tangent_half_step_review_001/review.json',
        '31a42fe26d47987e6afa065e60498ec8d3839793fe4f28d04657702db62f9c88')
    zero, zs = reviewed('hayward_cmj_post_step_zero_support_001',
        'hayward_cmj_post_step_zero_support_review_002/review.json',
        '784f1b4d4ac732819d4848625c812da5c6df0bd7c78f541187e66dfc1b3098f4')
    post, ps = reviewed('hayward_cmj_post_half_step_tangent_001',
        'hayward_cmj_post_half_step_tangent_review_001/review.json',
        'd16b1da181b06530ed283ee0cd90eecc642bdd6b65674905ab5863e1b176a818')
    kernel, ks = reviewed('hayward_cmj_fixed_polygon_kernel_001',
        'hayward_cmj_fixed_polygon_kernel_001/review.json',
        'c37e04d163a922e822df00bf95bc122736459becea753ec270bd00a945eaa440')
    failed = read(D/'hayward_cmj_post_step_zero_support_review_001/execution_attempt_001.json',
        '118b9d3ce4a947de7619d781a77dccf6e5c48059efb4a5cc0933154212a95f68')
    assert failed['return_code'] == 1 and failed['status'] == 'failed_preserved' and failed['child_reaped']
    pin(D/'hayward_cmj_post_step_zero_support_review_001/check_saved.py', failed['checker_sha256'])
    comparison = read(D/'hayward_cmj_half_gradient_comparison_001/summary.json',
        '775754c10cad0f57bba55da4d21f05cea4a69d8f63586b881dfa4fdf765a736f')
    receipt = read(D/'hayward_cmj_half_gradient_comparison_001/execution_receipt.json',
        '278294323bcab5cadd4ba2655248caad6264b9431116a09eb214e173dc63b156')
    assert receipt['return_code'] == 0 and receipt['child_reaped'] and receipt['status'] == 'passed'
    assert receipt['summary_sha256'] == pin(D/'hayward_cmj_half_gradient_comparison_001/summary.json')
    assert comparison['benchmark_review_sha256'] == pin(D/'hayward_cmj_fixed_polygon_kernel_001/review.json')
    assert comparison['post_half_review_sha256'] == pin(D/'hayward_cmj_post_half_step_tangent_review_001/review.json')
    assert all(comparison[k] == 0 for k in ('cpp_calls', 'numerical_integrations', 'subprocess_calls'))
    assert half['total_new_action_edges'] == ps['completed_tangent_edges'] == 2058
    assert sum(c['rounded_trials'] for c in half['cases']) == 2
    assert all(c['metric_solves'] == 0 for c in half['cases'])
    assert ps['sign_edges_completed'] == 61 and ps['sign_patches_completed'] == 65
    assert sum(c['sign_patches'] for c in zero['cases']) == 65
    quantities = []
    for i, (h, z, p, c) in enumerate(zip(half['cases'], zero['cases'], post['cases'], comparison['cases'])):
        assert h['event'] == z['event'] == p['event'] == c['event'] == (981, 987)[i]
        assert h['native_context'] == z['native_context'] == p['native_context'] == c['native_context']
        assert h['catalog_uses'] == z['catalog_uses'] == p['catalog_uses'] == c['catalog_uses']
        assert len(h['catalog_uses']) == 9
        assert all(x['original_convergence_flag'] == '0' and x['candidate_convergence_status'] is None for x in (h,z,p,c))
        lo, hi = map(Q, h['action']['paired_difference'])
        assert hi < -Q('1e-11') and hi-lo < Q('6e-32') and h['action']['conservative_nominal_armijo']
        assert h['alpha'] == '1/2' and h['status'] == 'diagnostic_trial_accepted'
        assert p['same_available_mask'] and not p['failed_edges'] and not z['failed_edges']
        assert p['available_components'] == c['available_components'] == (3050,3055)[i]
        assert p['unavailable_components'] == c['unavailable_components'] == (31,32)[i]
        assert Q(p['post_squared_bounds'][0]) > Q('1e-7')**2
        assert Q(p['post_squared_bounds'][1]) < Q('1e-5')**2
        assert Q(p['post_squared_bounds'][1]) < Q(p['pre_squared_bounds'][0])
        assert z['ordinary_contributions_retained'] == p['ordinary_contributions_retained'] == 2
        assert Q(c['component_error_norm_squared_bounds'][1]) < Q('1.020e-15')**2
        quantities.append(dict(event=h['event'], half_action_bounds=h['action']['paired_difference'],
            post_half_squared_norm=p['post_squared_bounds'], pre_squared_norm=p['pre_squared_bounds'],
            first_support_norm=z['feasible_full_support_norm'], half_support_norm=p['feasible_full_support_norm'],
            half_cpp_error_squared_bounds=c['component_error_norm_squared_bounds']))
    assert ks['path_eval_calls'] == 8 and ks['extra_segment_calls'] == 8232
    polygons, pairs = ks['result']['polygons'], ks['result']['pairs']
    assert len(polygons) == 8 and len(pairs) == 4
    assert all(Q(c['paired_comparison']['absolute_error_upper']) < Q('4e-17') for c in pairs)
    assert all(c['agrees_with_oracle'] and c['oracle_armijo'] == (c['to_stage']=='half') for c in pairs)
    available = [c for c in polygons if c['derivative_oracle_status']=='reviewed_available_internal_components']
    assert len(available) == 4 and all(Q(c['derivative_error_norm_squared_bounds'][1]) < Q('1.057e-15')**2 for c in available)
    timings = [Q(c['path_eval_microseconds']) for c in polygons]
    assert all(Q('1835') <= t < Q('3425') for t in timings)  # Two-decimal ms displays 1.84--3.42.

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
    prior = read(D/'cmj_tangent_continuation_report_001/compile.json')
    for name in ('report/panel_table.tex','report/panel_details.tex'):
        pin(ROOT/name, prior['tex_source_sha256'][name])
    prose = ' '.join((ROOT/'report/recovery_checkpoint.tex').read_text().split())
    for phrase in ('-1.9272', '-7.5767', '2.5528', '6.7473', '0.8212', '0.5306',
                   '4.4053', '2.2711', '4.4155', '2.4963', '1.057', '1.020', '1.84--3.42',
                   'not establish its accuracy on every later polygon', 'original oracle inventory unchanged'):
        assert phrase in prose, phrase
    assert 'cmj_tangent_iterator' not in prose
    inventory = dict(markdown_links=links, tex_literal_paths=literals, figures=figures, provider_resource_ids=resource_ids)
    (OUT/'path_inventory.json').write_text(json.dumps(inventory,indent=2)+'\n')
    pin(OUT/'path_inventory.json')
    pages = int(re.search(r'^Pages:\s+(\d+)',(OUT/'pdfinfo.txt').read_text(),re.M).group(1))
    result = dict(status='passed', checked_utc=datetime.utcnow().isoformat()+'Z', checker_sha256=pin(Path(__file__).resolve()),
        scope='Compilation, document links and closed reviewed quantities only; no numerical evaluator or new scientific threshold.',
        compile_sha256=pin(OUT/'compile.json'), report_sha256=compilation['report_sha256'], pdf_pages=pages,
        compile_tool_session=5700, compile_tool_chunk_id='f7a0dc', compile_tool_exit_code=0,
        compile_passes=2, tex_sources=16, logs=logs, input_sha256=PINS, panel_counts=counts,
        markdown_links=len(links), tex_literal_paths=len(literals), figures=len(figures),
        changed_pages_for_visual_review=[27,28,29,30], new_quantities=quantities,
        full_half_decisions=[dict(event=p['event'],trial=p['to_stage'],accepted=p['oracle_armijo'],
                                  paired_error_upper=p['paired_comparison']['absolute_error_upper']) for p in pairs],
        visual_review_status='pending root inspection of separately rendered pages')
    target.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status='passed',validation_sha256=pin(target),pdf_pages=pages,
                         markdown_links=len(links),tex_literal_paths=len(literals),figures=len(figures))))


if __name__ == '__main__':
    main()
