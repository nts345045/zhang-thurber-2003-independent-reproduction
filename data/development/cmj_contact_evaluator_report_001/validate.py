#!/usr/bin/env python3
"""Saved report checks only; original-audit bindings remain pending until closure."""
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
ORIGINAL_REVIEW_SHA256 = '51b5368792fc4ac73d60c3581b04324e719313e3970b93e0cf37a251e6770207'
ORIGINAL_RECEIPT_SHA256 = '929d0ceef35705df8388c7ef6c5bd1f37f040ecaa3a7b2c485413af401d40215'
CHANGED_PAGES = [29,30,31,32,33]
ORIGINAL_PROSE = ('All 6,168 internal components are ordinary', '59,290 saved-data checks over all 2,058 edges', 'Both original failure flags remain unchanged', '4.9649\\times10^{-4}', '4.9379\\times10^{-4}', '1.0564\\times10^{-15}', '1.0436\\times10^{-15}')


def pin(path, expected=None):
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert expected is None or digest == expected, str(path)
    PINS[str(path.relative_to(ROOT))] = digest
    return digest


def read(path, expected=None):
    pin(path, expected)
    return json.loads(path.read_text())


def reviewed(directory, review_directory, digest, summary_name='results/summary.json'):
    base = D/directory
    review = read(D/review_directory/'review.json', digest)
    assert review['status'] == 'passed'
    prefix = 'native_' if 'native_summary_sha256' in review else ''
    summary = read(base/summary_name, review[prefix+'summary_sha256'])
    execution = read(base/'execution.json', review[prefix+'execution_sha256'])
    outer = read(base/'outer_reaping.json', review['outer_reaping_sha256'])
    read(base/'prepared.json', review[prefix+'prepared_sha256'])
    assert execution['return_code'] == 0 and outer['status'] == 'completed_and_reaped'
    assert outer['tool_exit_code'] == 0 and outer['wrapper_process_absent']
    for record in (execution, outer):
        assert record['summary_sha256'] == pin(base/summary_name)
        assert record['prepared_sha256'] == pin(base/'prepared.json')
    assert outer['execution_sha256'] == pin(base/'execution.json')
    for name, expected in execution['output_sha256'].items(): pin(base/name, expected)
    return review, summary


def interval(values):
    lo, hi = map(Q, values)
    assert lo <= hi
    return lo, hi


def displayed_norm(bounds, number):
    # Five-significant-digit report rounding only, not an accuracy criterion.
    mantissa, exponent = number.split('e')
    half_unit = Q(1, 2)*Q(10)**(int(exponent) - 4)
    value = Q(number)
    lo, hi = interval(bounds)
    assert 0 <= (value-half_unit)**2 <= lo <= hi < (value+half_unit)**2


def science():
    contact, cs = reviewed('internal_face_contact_controls_001', 'internal_face_contact_controls_001',
        '8c0d9b507c877baa675891c2a667d98d79c664f71f4d69d2901ec48773e54a9b')
    strict, ss = reviewed('strict_cell_segment_controls_001', 'strict_cell_segment_controls_001',
        '51f9416cbba5d35938be42203d2529259eb3fc2a33705bc9f173e4121db06dab')
    for summary, count in ((cs,30),(ss,59)):
        assert summary['status'] == 'passed' and len(summary['checks']) == count
        assert all(x['passed'] for x in summary['checks']) and summary['invented_only']
        assert all(summary[k] == 0 for k in ('native_calls','trace_calls','field_calls'))
        assert summary['candidate_convergence_status'] is None and not summary['unresolved_children']
    cr = read(D/'internal_face_contact_controls_001/review_execution.json',
        '2b833ebaa9c794e2afe47be600e869a4773c48c2e22e25ba8638516dffe1d90f')
    assert cr['status'] == 'completed_passed' and cr['return_code'] is None
    assert cr['review_sha256'] == pin(D/'internal_face_contact_controls_001/review.json')
    pin(D/'internal_face_contact_controls_001/review_saved.py', cr['stdin_source_sha256'])
    sr = read(D/'strict_cell_segment_controls_001/review_execution.json',
        '9d350dbdb9126a84b1288a30ac17c58dc15d14008c38c238455522ed15cc4cef')
    assert sr['status'] == 'completed_passed' and sr['return_code'] == sr['tool_result']['exit_code'] == 0
    assert sr['review_sha256'] == pin(D/'strict_cell_segment_controls_001/review.json')
    pin(D/'strict_cell_segment_controls_001/review_saved.py', sr['checker_sha256'])
    assert contact['saved_checks_verified'] == 1136 and contact['unique_hashes_verified'] == 73
    assert strict['checks'] == 3715 and strict['unique_pins'] == 80
    assert cs['counts'] == contact['actual_counts'] == dict(affine_edge_references=22,combined_edge_calls=22,
        directional_edge_calls=24,fast_searches=2,helper_calls=10,slow_searches=1)
    assert [x['contacts'] for x in contact['trials']] == [[1],[2],[]]
    lo,hi=interval(contact['near_cut_errors'][0]['action_error'])
    assert Q('5.24265e-17') <= lo <= hi < Q('5.24275e-17')
    for trial, printed in zip(contact['trials'], ('-4.2569e-4','-1.9651e-4','-8.2554e-4')):
        lo,hi=interval(trial['difference']); value=Q(printed); half=Q('0.00005e-4')
        assert value-half <= lo <= hi < value+half < 0
    slow=cs['families'][1]
    assert slow['closed_form_true_directional'] == '-1/18' and slow['branch_hull_zero_is_not_a_support']
    assert all(interval(slow[k]['derivative'])[0] <= Q(-1,18) <= interval(slow[k]['derivative'])[1] for k in ('plus','minus'))
    assert ss['counts'] == dict(affine_references=7,cases=9,helpers=9,homogeneous_references=1,
        old_segment_calls=9,strict_edge_calls=9,strict_pieces=17,strict_samples=136,trilinear_references=1)
    assert ss['reference_settings'] == dict(affine_length_bits=192,affine_terms=16,trilinear=dict(bits=192,subdivisions=4,terms=16))
    assert ss['generic_subtraction_supported'] is ss['production_cut_patch'] is False
    assert all(x['prior_old_output_parity'] for x in ss['cases'][:4])
    quantities=[]
    table=[(0,'1.1322e-4','7.4166e-17'),(1,'6.1085e-17','6.1085e-17'),
        (2,'3.2342e-12','5.7856e-18'),(3,'5.0938e-18','3.8688e-18'),
        (4,'7.5209e-3','2.2902e-17'),(8,'1.2275e-17','1.2542e-17')]
    for i,old,new in table:
        row=strict['cases'][i]
        displayed_norm(row['old_error_squared_bounds'],old); displayed_norm(row['strict_error_squared_bounds'],new)
        quantities.append(dict(case=row['name'],old_display=old,strict_display=new,
            old_squared_error=row['old_error_squared_bounds'],strict_squared_error=row['strict_error_squared_bounds']))
    assert [x['mismatch_sample_count'] for x in strict['cases']] == [0,0,0,0,4,0,4,0,0]
    assert sum(x['prepared_samples'] for x in strict['cases']) == 136
    original, os = reviewed('hayward_cmj_original_gradient_bounds_001','hayward_cmj_original_gradient_bounds_review_001',
        ORIGINAL_REVIEW_SHA256, 'summary.json')
    receipt=read(D/'hayward_cmj_original_gradient_bounds_review_001/execution_receipt.json',ORIGINAL_RECEIPT_SHA256)
    assert receipt['status'] == 'passed' and receipt['return_code'] == 0 and receipt['child_reaped']
    assert receipt['review_sha256'] == pin(D/'hayward_cmj_original_gradient_bounds_review_001/review.json')
    pin(D/'hayward_cmj_original_gradient_bounds_review_001/check_saved.py',original['checker_sha256'])
    assert receipt['checker_sha256'] == original['checker_sha256'] and original['checks'] == 59290 and len(original['input_sha256']) == 131
    for name,digest in receipt['output_sha256'].items(): pin(D/'hayward_cmj_original_gradient_bounds_review_001'/name,digest)
    assert original['native_contexts'] == os['native_contexts'] and original['original_catalog_rows'] == 58980
    assert [x['event'] for x in original['cases']] == [981,987] and all(len(x['catalog_uses']) == 9 for x in original['native_contexts'])
    assert os['attempted_component_edges'] == os['completed_component_edges'] == 2058 and os['error'] is None
    assert os['original_convergence_flag'] == '0' and os['candidate_convergence_status'] is None
    assert all(os[k] == 0 for k in ('subprocess_calls','trace_calls','field_calls','metric_solves','rounded_trials','optimizer_iterations','source_model_partials'))
    for i,case in enumerate(original['cases']):
        assert case['available_components'] == (3081,3087)[i] and case['unavailable_components'] == case['exact_physical_boundary_components'] == 0
        assert case['original_convergence_flag'] == '0' and case['candidate_convergence_status'] is None
        assert case['reference_available_squared_bounds'] == case['reference_true_box_squared_bounds']
        displayed_norm(case['reference_available_squared_bounds'],('4.9649e-4','4.9379e-4')[i])
        displayed_norm(case['raw_error_squared_bounds'],('1.0564e-15','1.0436e-15')[i])
    assert sum(case['available_components'] for case in original['cases']) == 6168
    for directory in ('internal_face_contact_controls_001','strict_cell_segment_controls_001','hayward_cmj_original_gradient_bounds_001'):
        pin(D/directory/'RESULTS.md')
    return dict(contact_trials=contact['trials'],strict_table=quantities,original_components=original['cases'],
        contact_review_exit_code_unrecorded=True,prepared_global_cell_mismatches=8,
        original_scope='Component error, reference magnitude and physical-box projections remain separate; fixed original geometry only.')


def main():
    assert __debug__, 'Assertions must remain enabled'
    assert all((ORIGINAL_REVIEW_SHA256,ORIGINAL_RECEIPT_SHA256,CHANGED_PAGES,ORIGINAL_PROSE)), 'Pending original review and final prose/page bindings'
    target=OUT/'validation.json'
    assert not target.exists() and not (OUT/'path_inventory.json').exists(), 'Preserve prior validation artifacts'
    compilation=read(OUT/'compile.json')
    assert compilation['status'] == 'completed' and [x['return_code'] for x in compilation['commands']] == [0,0]
    pin(ROOT/'report/report.pdf',compilation['report_sha256'])
    pin(ROOT/'README.md',compilation['readme_sha256']); pin(ROOT/'FAILURE_SUMMARY.md',compilation['failure_summary_sha256'])
    assert len(compilation['tex_source_sha256']) == 16
    for name,digest in compilation['tex_source_sha256'].items(): pin(ROOT/name,digest)
    for name,digest in compilation['output_sha256'].items(): pin(OUT/name,digest)
    receipt=read(OUT/'compile_execution_receipt.json')
    assert receipt['status'] == 'completed_and_reaped' and receipt['return_code'] == 0 and receipt['child_reaped']
    assert receipt['compile_sha256'] == pin(OUT/'compile.json') and receipt['report_sha256'] == compilation['report_sha256']
    logs={}
    for number in (1,2):
        lines=(OUT/('pass%d_report.log'%number)).read_text().splitlines()
        errors=[x for x in lines if re.search(r'^!|Overfull',x)]
        undefined=[x for x in lines if re.search(r'undefined',x,re.I)]
        warnings=[x for x in lines if re.search(r'\bwarning:',x,re.I)]
        known='pdfTeX warning: pdflatex (file ../figures/location_errors.pdf): PDF inclusion: '
        allowed=[known]
        if number == 1:
            references=[x for x in warnings if re.fullmatch(r"LaTeX Warning: Reference `tab:synthetic_cut_errors' on page \d+ undefined on inp(?:ut)?\s*",x)]
            allowed+=references+['LaTeX Warning: There were undefined references.','LaTeX Warning: Label(s) may have changed. Rerun to get cross-references right.']
            assert all(x in references+['LaTeX Warning: There were undefined references.'] for x in undefined)
        else: assert not undefined
        assert not errors and warnings.count(known) == 1 and all(x in allowed for x in warnings), warnings
        assert any('multiple pdfs with page group included in a single page' in x for x in lines)
        logs[str(number)]=dict(errors_or_overfull=errors,undefined=undefined,warnings=warnings)
    prior=read(D/'cmj_tangent_support_report_001/validation.json','eece304709cb6af8b4b25f8378bfce22765b559e7bfa1cf13609d6242f322d17')
    assert prior['status'] == 'passed'
    previous_compile=read(D/'cmj_tangent_support_report_001/compile.json',prior['compile_sha256'])
    assert compilation['previous_report_sha256'] == previous_compile['report_sha256']
    pin(OUT/'compile.py','d51d2bc32daa4c6aaf30a0722579f3406f022d4bb816cd759ff0e932ccd963a1')
    quantities=science()
    links=[]; literals=[]; figures=[]; ids=[]
    for name in ('README.md','FAILURE_SUMMARY.md'):
        for link in re.findall(r'\[[^\]]*\]\(([^)]+)\)',(ROOT/name).read_text()):
            if re.match(r'(?:https?://|mailto:|#)',link): continue
            path=link.split('#')[0]; assert (ROOT/path).exists(),path
            links.append(dict(document=name,path=path))
    for name in compilation['tex_source_sha256']:
        path=ROOT/name; text=path.read_text()
        for literal in re.findall(r'\\path\{([^}]+)\}',text):
            if literal.startswith('quakeml:'): ids.append(dict(document=name,resource_id=literal)); continue
            resolved=ROOT/literal
            if not resolved.exists():
                assert '/' not in literal.rstrip('/'),literal
                resolved=D/literal
            assert resolved.exists(),literal
            literals.append(dict(document=name,path=str(resolved.relative_to(ROOT))))
        for literal in re.findall(r'\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}',text):
            resolved=next((p.resolve() for p in (path.parent/literal,ROOT/'figures'/literal) if p.exists()),None)
            assert resolved is not None,literal
            figures.append(dict(document=name,path=str(resolved.relative_to(ROOT)),sha256=pin(resolved)))
    panels=list(csv.DictReader((ROOT/'data/panel_audit.csv').open())); pin(ROOT/'data/panel_audit.csv')
    panel_json=read(ROOT/'data/panel_audit.json'); counts=dict(collections.Counter(x['status'] for x in panels))
    assert counts == {'independently reproduced':1,'partially reproduced':61}
    assert [(x['panel'],x['status']) for x in panels] == [(x['panel'],x['status']) for x in panel_json]
    for name in ('report/panel_table.tex','report/panel_details.tex'): pin(ROOT/name,previous_compile['tex_source_sha256'][name])
    prose=' '.join((ROOT/'report/recovery_checkpoint.tex').read_text().split())
    for phrase in ('two successive exact event proposals','-1/18','All 30 checks pass','59 structural checks pass',
        'reciprocal-series degree 16 (17 retained powers)','not exact derivatives of the finite floating-point quadrature sum',
        'does not isolate the effect of cell selection from partitioning')+tuple(ORIGINAL_PROSE):
        assert phrase in prose,phrase
    inventory=dict(markdown_links=links,tex_literal_paths=literals,figures=figures,provider_resource_ids=ids)
    (OUT/'path_inventory.json').write_text(json.dumps(inventory,indent=2)+'\n'); pin(OUT/'path_inventory.json')
    pages=int(re.search(r'^Pages:\s+(\d+)',(OUT/'pdfinfo.txt').read_text(),re.M).group(1))
    result=dict(status='passed',checked_utc=datetime.utcnow().isoformat()+'Z',checker_sha256=pin(Path(__file__).resolve()),
        scope='Closed saved evidence, compilation and document links only; no numerical evaluator or new scientific threshold.',
        compile_sha256=pin(OUT/'compile.json'),compile_execution_receipt_sha256=pin(OUT/'compile_execution_receipt.json'),
        report_sha256=compilation['report_sha256'],pdf_pages=pages,compile_passes=2,tex_sources=16,logs=logs,
        input_sha256=PINS,panel_counts=counts,markdown_links=len(links),tex_literal_paths=len(literals),figures=len(figures),
        changed_pages_for_visual_review=CHANGED_PAGES,new_quantities=quantities,visual_review_status='pending root inspection')
    target.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status='passed',validation_sha256=pin(target),pdf_pages=pages)))


if __name__ == '__main__':
    main()
