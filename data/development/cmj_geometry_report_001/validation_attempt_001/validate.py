#!/usr/bin/env python3
"""Check this document checkpoint against saved reviewed results; no solver calls."""
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


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path, expected=None):
    digest = sha(path)
    if expected is not None:
        assert digest == expected, str(path)
    PINS[str(path.relative_to(ROOT))] = digest
    return json.loads(path.read_text())


def local_pins(base, mapping):
    for name, digest in mapping.items():
        path = base/name
        assert sha(path) == digest, str(path)
        PINS[str(path.relative_to(ROOT))] = digest


def native_terminal_record():
    base = D/'hayward_cmj_face_action_001'
    checked = D/'hayward_cmj_face_action_review_001'
    review = read(base/'review.json',
        '447091d4ec796691e7c3cfe8f852d0ae23a11cc7be74e11fcded101f6a37afc2')
    assert review['status'] == 'passed' and sha(checked/'review.json') == sha(base/'review.json')
    summary = read(base/'summary.json', review['summary_sha256'])
    execution = read(base/'execution.json', review['execution_sha256'])
    readback = read(checked/'execution.json',
        '36a81d6f249045158cc57a6affe49dbb783c90b77c2656344d024ce3ba0a3ec7')
    assert summary['status'] == 'completed_bounded_calculation' and summary['error'] is None
    for receipt in (execution, readback):
        assert receipt['status'] == 'completed' and receipt['return_code'] == 0 and receipt['child_reaped']
    assert all(summary[k] == 0 for k in ('native_trace_calls', 'field_calls', 'optimizer_calls', 'descent_steps'))
    local_pins(base, execution['output_sha256'])
    local_pins(ROOT, readback['input_sha256'])
    local_pins(ROOT, readback['output_sha256'])
    prepared = read(base/'prepared.json', review['prepared_sha256'])
    local_pins(ROOT, prepared['input_sha256'])
    local_pins(base, prepared['output_sha256'])
    assert prepared['settings'] == summary['settings'] == dict(terms=8, subdivisions=1, bits=128)
    assert sha(checked/'review_saved.py') == review['checker_sha256']
    norms = read(checked/'tangent_norms.json', review['tangent_norms_sha256'])
    assert [r['event'] for r in review['cases']] == [981, 987]
    assert review['check_counts']['independent_jump_coefficients'] == 65
    assert review['check_counts']['full_adjacent_edge_component_sum'] == 2056
    cases = []
    for index, (result, audited, saved_norm) in enumerate(zip(summary['results'], review['cases'], norms['cases'])):
        assert result['native_context'] == audited['native_context'] == saved_norm['native_context']
        assert result['original_convergence_flag_preserved'] == audited['original_flag'] == '0'
        assert result['candidate_convergence_status'] is audited['candidate_flag'] is None
        assert result['action_classification'] == audited['action_classification'] == 'decreased'
        delta = list(map(Q, result['candidate_minus_original']['exact_rational_bounds']))
        assert delta == list(map(Q, audited['action_bounds']['candidate_minus_original'])) and delta[1] < 0
        assert audited['single_face_edges'] == (30, 31)[index]
        assert audited['multiple_face_edges'] == 0 and audited['all_single_face_patches_convex']
        assert Q(audited['minimum_jump_numerator']) > 0
        norm = audited['tangent_projected_norm']
        assert norm == saved_norm['summary']
        assert norm['available_component_count'] == (3050, 3055)[index]
        assert norm['unavailable_face_normal_count'] == (31, 32)[index]
        assert norm['exact_physical_boundary_component_count'] == 0
        assert Q(norm['lower_squared']) <= Q(norm['upper_squared'])
        assert Q(norm['lower_squared']) > Q(1, 10**10)
        assert all(v['classification'] == 'strictly_above' and v['diagnostic_only'] for v in norm['threshold_scales'].values())
        lower = sum((Q(row['squared_bounds'][0]) for row in saved_norm['components']), Q(0))
        upper = sum((Q(row['squared_bounds'][1]) for row in saved_norm['components']), Q(0))
        assert (lower, upper) == (Q(norm['lower_squared']), Q(norm['upper_squared']))
        witness = result['tangent_witness']
        assert witness['status'] == 'negative_tangent_witness' and witness['node'] == 1
        assert not witness['selected_near_face_node'] and not witness['incident_to_exact_face_edge']
        cases.append(dict(event=result['event'], station=result['station'], native_context=result['native_context'],
            candidate_minus_original=result['candidate_minus_original'], tangent_projected_norm=norm,
            original_flag='0', candidate_flag=None))
    assert sum(r['counts']['action_edge_evaluations'] for r in summary['results']) == 2123
    return dict(summary_sha256=sha(base/'summary.json'), review_sha256=sha(base/'review.json'),
                execution_sha256=sha(base/'execution.json'), cases=cases,
                interpretation='Two prescribed polygons; face alignment alone leaves tangent residuals above both gradient scales.')


def main():
    if not __debug__:
        raise RuntimeError('Validation requires assertions enabled')
    target = OUT/'validation.json'
    if target.exists():
        raise RuntimeError('Preserve the existing validation record')
    compile_record = read(OUT/'compile.json')
    assert compile_record['status'] == 'completed'
    assert len(compile_record['commands']) == 2
    assert all(x['return_code'] == 0 for x in compile_record['commands'])
    assert sha(ROOT/'report/report.pdf') == compile_record['report_sha256']
    assert sha(ROOT/'README.md') == compile_record['readme_sha256']
    assert sha(ROOT/'FAILURE_SUMMARY.md') == compile_record['failure_summary_sha256']
    assert len(compile_record['tex_source_sha256']) == 16
    assert all(sha(ROOT/n) == h for n, h in compile_record['tex_source_sha256'].items())
    assert all(sha(OUT/n) == h for n, h in compile_record['output_sha256'].items())
    logs = {}
    for number in (1, 2):
        lines = (OUT/('pass%d_report.log' % number)).read_text().splitlines()
        errors = [x for x in lines if re.search(r'^!|Overfull', x)]
        undefined = [x for x in lines if re.search(r'undefined', x, re.I)]
        warnings = [x for x in lines if re.search(r'\bwarning:', x, re.I)]
        page_group = 'pdfTeX warning: pdflatex (file ../figures/location_errors.pdf): PDF inclusion: '
        assert not errors and not undefined
        allowed = [page_group]
        if number == 1:
            allowed.append('LaTeX Warning: Label(s) may have changed. Rerun to get cross-references right.')
        assert warnings.count(page_group) == 1 and all(w in allowed for w in warnings), warnings
        assert any('multiple pdfs with page group included in a single page' in x for x in lines)
        logs[str(number)] = {'errors_or_overfull': errors, 'undefined': undefined,
                            'case_insensitive_warnings': warnings,
                            'existing_warning': 'location_errors.pdf page-group warning retained from prior checkpoint; page location requires visual review'}
    links = []
    for name in ('README.md', 'FAILURE_SUMMARY.md'):
        for link in re.findall(r'\[[^\]]*\]\(([^)]+)\)', (ROOT/name).read_text()):
            if re.match(r'(?:https?://|mailto:|#)', link):
                continue
            path = link.split('#')[0]
            assert (ROOT/path).exists(), path
            links.append({'document': name, 'path': path})
    paths, figures, provider_ids = [], [], []
    for name in compile_record['tex_source_sha256']:
        p = ROOT/name
        text = p.read_text()
        for literal in re.findall(r'\\path\{([^}]+)\}', text):
            if literal.startswith('quakeml:'):
                provider_ids.append({'document': name, 'resource_id': literal})
                continue
            resolved = ROOT/literal
            basis = 'repository root'
            if not resolved.exists():
                assert '/' not in literal.rstrip('/')
                resolved = D/literal
                basis = 'explicit data/development parent in adjoining prose'
            assert resolved.exists(), literal
            paths.append({'document': name, 'literal': literal,
                          'resolved': str(resolved.relative_to(ROOT)), 'basis': basis})
        for literal in re.findall(r'\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}', text):
            resolved = next((q.resolve() for q in (p.parent/literal, ROOT/'figures'/literal) if q.exists()), None)
            assert resolved is not None, literal
            figures.append({'document': name, 'literal': literal,
                            'resolved': str(resolved.relative_to(ROOT)), 'sha256': sha(resolved)})
    panels = list(csv.DictReader((ROOT/'data/panel_audit.csv').open()))
    panel_json = read(ROOT/'data/panel_audit.json')
    counts = dict(collections.Counter(row['status'] for row in panels))
    assert counts == {'independently reproduced': 1, 'partially reproduced': 61}
    assert [(x['panel'], x['status']) for x in panels] == [(x['panel'], x['status']) for x in panel_json]
    prior = read(D/'trial_backtracking_report_001/compile.json')
    for name in ('report/panel_table.tex', 'report/panel_details.tex'):
        assert sha(ROOT/name) == prior['tex_source_sha256'][name]

    math_base = D/'trilinear_action_controls_001'
    math_review = read(math_base/'review.json',
        '033cc56252dbcb34ea86ae0ac73679f36913fbd25a89a9e79e4877d4006342c3')
    assert math_review['status'] == 'passed'
    local_pins(math_base, math_review['input_sha256'])
    math_summary = read(math_base/'summary.json')
    math_execution = read(math_base/'execution.json')
    assert math_summary['status'] == 'passed'
    assert math_execution['status'] == 'completed' and math_execution['return_code'] == 0 and math_execution['child_reaped']
    assert math_summary['controls_passed'] == math_summary['controls_total'] == math_review['recorded_checks'] == 80
    assert math_review['mathematical_checks'] == 65
    assert math_review['original_pin_checks'] + math_review['frozen_pin_checks'] == 15
    assert len(math_review['independent_exact_comparisons']) == 18
    assert math_summary['native_evaluations'] == math_summary['ray_calls'] == math_summary['optimizer_calls'] == 0
    local_pins(math_base, math_execution['output_sha256'])
    local_pins(ROOT, math_summary['input_sha256'])
    assert sha(ROOT/'diagnostics/trilinear_action_bounds.py') == 'c3ea236e9f234659061eec6c44c55bacc83ee45313b2d8488061eb5405f103da'

    geometry = D/'hayward_full_dd_geometry_export_controls_002'
    geometry_review = read(geometry/'review.json',
        '87e8e5599fe7d087c49042f043d3b2e8db007cf5ae401d4405bb91a0838d891b')
    assert geometry_review['status'] == 'passed'
    local_pins(geometry, geometry_review['input_sha256'])
    geometry_summary = read(geometry/'summary.json')
    geometry_execution = read(geometry/'execution.json')
    assert geometry_summary['status'] == 'passed'
    assert geometry_summary['passed'] == geometry_summary['total'] == geometry_review['control_records'] == 82
    assert geometry_review['original_files_byte_identical'] == 8
    assert geometry_review['actual_used_pairs'] == 3 and geometry_review['actual_path_nodes'] == 24
    assert geometry_execution['status'] == 'completed' and geometry_execution['return_code'] == 0
    assert geometry_execution['all_direct_children_reaped'] and all(c['reaped'] for c in geometry_execution['commands'])
    assert geometry_execution['summary_sha256'] == sha(geometry/'summary.json')
    assert geometry_execution['prepared_sha256'] == geometry_summary['prepared_sha256'] == sha(geometry/'prepared.json')
    assert sha(ROOT/'diagnostics/review_full_dd_geometry.py') == sha(geometry/'review_geometry.py') == '144547cc7a80bf3c914e02fb1302813d07004b5350f6470cebc07776d715f398'

    adoption = D/'hayward_full_dd_geometry_adoption_002'
    source_review = read(adoption/'source_review.json',
        '4ac2a8ed3c95167c67deea6d862ac3636e4c9d356546382c84b1baa6ecbafc3b')
    assert source_review['status'] == 'passed' and source_review['executed_numerical_calls'] == 0
    for number, digest, status, codes in (
            (1, '487a97d703c8c1c2c34aa82ef53fc926b99fb3c08e7819369c3754497f00329d', 'failed', [0,2]),
            (2, '029883546116df5be22615c3d67a604f865cd7b7374a25ad8266fc36aabba28f', 'passed', [0,0])):
        base = D/('hayward_full_dd_geometry_adoption_%03d' % number)
        compilation = read(base/'compile.json', digest)
        saved = read(base/'adoption.json', compilation['adoption_sha256'])
        assert compilation['status'] == status and compilation['native_evaluations'] == 0
        assert [c['return_code'] for c in compilation['commands']] == codes
        assert all(c['reaped'] for c in compilation['commands'])
        for command in compilation['commands']:
            local_pins(base, {command['log']: command['log_sha256']})
        local_pins(base/'source', saved['after_sha256'])
    assert source_review['adoption_sha256'] == sha(adoption/'adoption.json')

    archive = D/'geometry_export_evidence_001'
    archive_review = read(archive/'review.json',
        '62ea9e36a021e69dad6f65cf8f363639cddf71bf7bc055652f1c22f0f846de84')
    assert archive_review['status'] == 'passed'
    local_pins(archive, archive_review['input_sha256'])
    packaging = read(archive/'packaging.json')
    restoration = read(archive/'restore_check.json')
    assert packaging['status'] == 'verified_lossless' and restoration['status'] == 'passed'
    assert restoration['packaging_sha256'] == sha(archive/'packaging.json')
    assert restoration['archive_sha256'] == packaging['archive_sha256'] == sha(archive/'evidence.tar.gz')
    assert restoration['members_sha256'] == packaging['members_sha256'] == sha(archive/'members.json')
    assert restoration['verified_members'] == packaging['member_count'] == archive_review['verified_members'] == 1154
    assert packaging['symbolic_links'] == archive_review['links'] == 0
    assert len(packaging['compiled_binaries']) == archive_review['compiled_fixtures_preserved_not_executed'] == 3
    assert restoration['original_bytes_and_modes_unchanged'] and restoration['exact_restored_roster']
    native = native_terminal_record()  # Required; never silently skip pending native review.
    new_counts = dict(trilinear_checks=80, mathematical_checks=65, pin_checks=15,
                      independent_exact_comparisons=18, geometry_controls=82,
                      original_export_files_byte_identical=8, archived_members=1154)
    report = ' '.join((ROOT/'report/recovery_checkpoint.tex').read_text().split())
    for phrase in ('All 80 invented checks pass', '65 mathematical checks and 15 source/file hash',
                   '18 exact comparisons', 'All 82 invented controls',
                   'original eight export files', 'parsed saved 12-digit model',
                   'No new field resolution has been calculated'):
        assert phrase in report, phrase
    inventory = {'markdown_links': links, 'tex_literal_paths': paths, 'figures': figures,
                 'provider_resource_ids_not_files': provider_ids}
    (OUT/'path_inventory.json').write_text(json.dumps(inventory, indent=2)+'\n')
    pages = int(re.search(r'^Pages:\s+(\d+)', (OUT/'pdfinfo.txt').read_text(), re.M).group(1))
    result = {'status': 'passed', 'checked_utc': datetime.utcnow().isoformat()+'Z',
              'scope': 'Saved document/compile/link/review-count readback only; no numerical calculation or launch by this checker.',
              'checker_sha256': sha(Path(__file__)), 'input_sha256': PINS,
              'compile_passes': 2, 'compile_log_findings': logs, 'tex_sources': 16,
              'readme_sha256': sha(ROOT/'README.md'), 'failure_summary_sha256': sha(ROOT/'FAILURE_SUMMARY.md'),
              'recovery_checkpoint_sha256': sha(ROOT/'report/recovery_checkpoint.tex'),
              'report_sha256': sha(ROOT/'report/report.pdf'), 'pdf_pages': pages,
              'pdf_bytes': (ROOT/'report/report.pdf').stat().st_size,
              'markdown_links': len(links), 'tex_literal_paths': len(paths), 'figures': len(figures),
              'panel_counts': counts, 'path_inventory_sha256': sha(OUT/'path_inventory.json'),
              'new_counts': new_counts, 'native_reviewed_record': native,
              'visual_review': 'Separate root visual review required; not claimed by this checker.',
              'limits': ['Invented arithmetic and export controls are not field accuracy.',
                  'Export evaluation uses the parsed saved12-digit model; covariance is not accepted here.',
                  'Native completion, action signs and tangent eligibility remain distinct; original flags and panel counts are preserved.']}
    target.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({'status': result['status'], 'pages': pages, 'validation_sha256': sha(target),
                      'report_sha256': result['report_sha256']}))


if __name__ == '__main__':
    main()
