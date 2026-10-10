#!/usr/bin/env python3
"""Saved document, link, figure and reviewed-claim readback; no science reruns."""
import collections
import csv
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load(p):
    return json.loads(p.read_text())


def main():
    if not __debug__:
        raise RuntimeError('Validation requires assertions enabled')
    target = OUT/'validation.json'
    if target.exists():
        raise RuntimeError('Preserve the existing validation record')
    compile_record = load(OUT/'compile.json')
    assert compile_record['status'] == 'completed'
    assert len(compile_record['commands']) == 2
    assert all(x['return_code'] == 0 for x in compile_record['commands'])
    assert sha(ROOT/'report/report.pdf') == compile_record['report_sha256']
    assert sha(ROOT/'README.md') == compile_record['readme_sha256']
    assert all(sha(ROOT/name) == digest for name, digest in compile_record['tex_source_sha256'].items())
    assert all(sha(OUT/name) == digest for name, digest in compile_record['output_sha256'].items())
    logs = {}
    for n in (1, 2):
        lines = (OUT/('pass%d_report.log' % n)).read_text().splitlines()
        errors = [x for x in lines if re.search(r'^!|Overfull', x)]
        undefined = [x for x in lines if re.search(r'undefined', x, re.I)]
        warnings = [x for x in lines if re.search(r'\bwarning:', x, re.I)]
        page_group = 'pdfTeX warning: pdflatex (file ../figures/location_errors.pdf): PDF inclusion: '
        assert not errors
        assert warnings.count(page_group) == 1
        assert any('multiple pdfs with page group included in a single page' in x for x in lines)
        if n == 2:
            assert warnings == [page_group] and not undefined
        else:
            expected = [page_group,
                "LaTeX Warning: Reference `fig:cmj_trial_geometry' on page 26 undefined on input",
                'LaTeX Warning: There were undefined references.',
                'LaTeX Warning: Label(s) may have changed. Rerun to get cross-references right.']
            assert warnings == expected
            assert undefined == expected[1:3]
        logs[str(n)] = {'errors_overfull': errors, 'undefined': undefined,
                       'warnings': warnings,
                       'existing_page_group_warning': 'location_errors.pdf, page14; visually inspected in prior checkpoint',
                       'first_pass_new_figure_reference_resolved_in_second_pass': n == 1}
    links = re.findall(r'\[[^\]]*\]\(([^)]+)\)', (ROOT/'README.md').read_text())
    local_links = [x.split('#')[0] for x in links if not re.match(r'(?:https?://|mailto:|#)', x)]
    assert all((ROOT/x).exists() for x in local_links)
    paths, figures = [], []
    provider_ids = []
    for name in compile_record['tex_source_sha256']:
        p = ROOT/name
        text = p.read_text()
        for literal in re.findall(r'\\path\{([^}]+)\}', text):
            if literal.startswith('quakeml:'):
                provider_ids.append({'document': name, 'provider_resource_id': literal})
                continue
            resolved = ROOT/literal
            basis = 'repository root'
            if not resolved.exists():
                # These seven abbreviations explicitly say "same parent" or
                # follow the data/development parent in the existing prose.
                assert '/' not in literal.rstrip('/')
                resolved = ROOT/'data/development'/literal
                basis = 'explicit data/development parent in adjoining prose'
            assert resolved.exists(), literal
            paths.append({'document': name, 'literal': literal,
                          'resolved': str(resolved.relative_to(ROOT)), 'basis': basis})
        for literal in re.findall(r'\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}', text):
            options = [p.parent/literal, ROOT/'figures'/literal]
            resolved = next((q.resolve() for q in options if q.exists()), None)
            assert resolved is not None, literal
            figures.append({'document': name, 'literal': literal,
                            'resolved': str(resolved.relative_to(ROOT)), 'sha256': sha(resolved)})
    panels = list(csv.DictReader((ROOT/'data/panel_audit.csv').open()))
    panel_json = load(ROOT/'data/panel_audit.json')
    counts = dict(collections.Counter(row['status'] for row in panels))
    assert counts == {'independently reproduced': 1, 'partially reproduced': 61}
    assert [(x['panel'], x['status']) for x in panels] == [(x['panel'], x['status']) for x in panel_json]
    old_compile = load(ROOT/'data/development/usable_curvature_adoption_report_003/compile.json')
    for name in ('report/panel_table.tex', 'report/panel_details.tex'):
        assert sha(ROOT/name) == old_compile['tex_source_sha256'][name]
    scientific_paths = [
        'data/development/full_dd_resolution_ray_input_checks_001/review.json',
        'data/development/full_dd_resolution_ray_input_checks_001/new_checks/results.json',
        'data/development/full_dd_resolution_ray_input_checks_001/prior39_comparison.json',
        'data/development/loma_lon_straight_curvature_replay_001/summary.json',
        'data/development/loma_lon_straight_curvature_replay_001/execution.json',
        'data/development/loma_lon_straight_curvature_replay_001/review.json',
        'data/development/loma_lon_first_edge_decomposition_001/calculation/summary.json',
        'data/development/loma_lon_first_edge_decomposition_001/review.json']
    evidence = [load(ROOT/p) for p in scientific_paths]
    guard_review, guard_controls, prior, replay, execution, replay_review, edge, edge_review = evidence
    assert guard_review['status'] == guard_controls['status'] == prior['status'] == 'passed'
    assert len(guard_controls['checks']) == 56 and all(x['passed'] for x in guard_controls['checks'])
    assert prior['original_control_records'] == 39 and prior['all_original_control_records_exactly_equal']
    assert replay['status'] == 'completed_four_calls'
    assert execution['status'] == 'completed' and execution['native_calls_completed'] == 4
    assert replay_review['status'] == 'passed'
    assert replay_review['summary_sha256'] == execution['summary_sha256'] == sha(ROOT/scientific_paths[3])
    assert replay_review['execution_sha256'] == sha(ROOT/scientific_paths[4])
    assert edge_review['status'] == 'passed'
    assert edge_review['summary_sha256'] == sha(ROOT/scientific_paths[6])
    assert edge['closed_form_controls_passed'] == 4
    assert [x['saved_source_meets_original_limit'] for x in edge['results']] == [False, True]
    assert [x['local_curved_component_meets_same_numeric_limit'] for x in edge['results']] == [False, True]
    report = (ROOT/'report/recovery_checkpoint.tex').read_text()
    assert r'$(4.80706\to4.84264)\times10^{-6}$' in report
    assert r'$(1.05998\to1.06845)\times10^{-6}$' in report
    strict_records = []
    for package, cap in [('loma_lon_strict_straight_replay_001', 1000),
                         ('loma_lon_strict_straight_4000_replay_001', 4000)]:
        base = 'data/development/' + package + '/'
        sr = load(ROOT/(base+'summary.json'))
        rv = load(ROOT/(base+'review.json'))
        ex = load(ROOT/(base+'execution.json'))
        assert rv['status'] == 'passed'
        assert rv['summary_sha256'] == sha(ROOT/(base+'summary.json'))
        assert rv['execution_sha256'] == sha(ROOT/(base+'execution.json'))
        assert ex['native_calls_completed'] == 2 and ex['status'] == 'completed'
        pairs = sr['variants']['strict']
        assert len(pairs) == 2
        for row in pairs:
            assert row['derived_loop_termination'] == 'update_budget_exhausted'
            assert row['local_flag'] == 0 and not row['strict_gradient_test_pass']
            assert row['time_limit_pass'] and row['source_limit_pass']
            assert int(row['scalars_17']['ray_iterations']) == cap
            assert int(row['scalars_17']['ray_merged_nodes']) == 0
        strict_records.append({'cap': cap, 'source_errors_s_per_km': [r['source_error_euclidean_norm_s_per_km'] for r in pairs],
                               'local_flags': [r['local_flag'] for r in pairs]})
        scientific_paths.extend(base+x for x in ('summary.json','review.json','execution.json'))
    base = 'data/development/hayward_guarded_failure_001/'
    failure = load(ROOT/(base+'classification/summary.json'))
    archive = load(ROOT/(base+'archive_verification.json'))
    manifest = load(ROOT/(base+'manifest.json'))
    assert failure['status'] == 'passed_saved_failure_audit'
    assert failure['native_rays'] == 14262 and failure['native_failed_rays'] == 181
    assert failure['accepted_updates'] == failure['history_rows'] == 0
    assert failure['last_accepted_state_numerically_equals_initial'] and failure['controller_reaped']
    assert failure['derived_selected_termination_counts'] == {'update_budget_exhausted':106, 'line_search_exhausted':75}
    assert archive['status'] == 'passed' and archive['manifest_sha256'] == sha(ROOT/(base+'manifest.json'))
    assert archive['compressed_sha256'] == sha(ROOT/(base+'archive/failed_run.tar.gz'))
    assert archive['verified_members'] == 61 and archive['original_run_files_rehashed_unchanged'] == 57
    independent = load(ROOT/(base+'independent_archive_review.json'))
    assert independent['status'] == 'passed'
    assert independent['manifest_sha256'] == sha(ROOT/(base+'manifest.json'))
    assert independent['archive_sha256'] == archive['compressed_sha256']
    assert independent['archive_members'] == 61 and independent['classification_inputs_resolved'] == 68
    assert all(sha(ROOT/(base+p)) == digest for p,digest in independent['input_sha256'].items())
    scientific_paths.extend(base+x for x in ('classification/summary.json','manifest.json','archive_verification.json','restore_check.json','independent_archive_review.json'))
    cmj_base = 'data/development/hayward_trial_cmj_old_D_replay_001/'
    cmj = load(ROOT/(cmj_base+'summary.json'))
    cmj_review = load(ROOT/(cmj_base+'review.json'))
    assert cmj_review['status'] == 'passed'
    assert cmj_review['summary_sha256'] == sha(ROOT/(cmj_base+'summary.json'))
    assert cmj_review['execution_sha256'] == sha(ROOT/(cmj_base+'execution.json'))
    assert (cmj['field_constructions'], cmj['configured_evaluations'], cmj['trace_subcalls']) == (1, 4, 8)
    assert not cmj['derivatives_evaluated'] and not cmj['accuracy_reference_available']
    assert cmj_review['old_exact_original_status_and_selected_path_parity']
    assert cmj_review['candidate_files_byte_identical_old_D']
    assert len(cmj['variants']['old']) == len(cmj['variants']['D']) == 2
    for variant, cases in cmj['variants'].items():
        for case in cases:
            assert case['status']['ray_converged'] == '0'
            assert len(case['starts']) == 2
            for start in case['starts']:
                assert start['converged'] == '0' and start['merged_nodes'] == '0'
                if variant == 'D':
                    assert start['iterations'] == '1000'
    scientific_paths.extend(cmj_base+x for x in ('summary.json','review.json','execution.json','replay_input_closure.json'))
    geometry_base = 'data/development/hayward_cmj_interface_geometry_001/'
    geometry = load(ROOT/(geometry_base+'summary.json'))
    geometry_review = load(ROOT/(geometry_base+'review.json'))
    assert geometry_review['status'] == 'passed' and not geometry_review['material_issue_found']
    assert geometry_review['summary_sha256'] == sha(ROOT/(geometry_base+'summary.json'))
    assert [x['nodes_with_abs_x_below_1e_minus6_km'] for x in geometry['results']] == [31,32]
    assert [x['exact_positive_left_negative_right_count'] for x in geometry['results']] == [31,32]
    plot = load(ROOT/(geometry_base+'plot_receipt.json'))
    assert plot['source_sha256'] == sha(ROOT/(geometry_base+'plot.py'))
    for group in ('input_sha256','output_sha256'):
        assert all(sha(ROOT/(geometry_base+name)) == digest for name,digest in plot[group].items())
    scientific_paths.extend(geometry_base+x for x in ('summary.json','review.json','plot_receipt.json'))
    gradient_base = 'data/development/hayward_cmj_saved_gradient_001/'
    gradient = load(ROOT/(gradient_base+'summary.json'))
    gradient_review = load(ROOT/(gradient_base+'review.json'))
    assert gradient_review['status'] == 'passed'
    assert gradient_review['summary_sha256'] == sha(ROOT/(gradient_base+'summary.json'))
    assert gradient_review['execution_sha256'] == sha(ROOT/(gradient_base+'execution.json'))
    assert (gradient['fixed_path_evaluations'],gradient['trace_calls'],gradient['field_constructions']) == (4,0,0)
    assert gradient['all_recorded_17_digit_raw_and_projected_norms_reproduced']
    fractions = []
    for case in gradient['cases']:
        fraction = case['squared_component_decomposition']['raw']['near_face_x_fraction_of_total']
        assert fraction == case['squared_component_decomposition']['projected']['near_face_x_fraction_of_total']
        assert case['saved_status_and_diagnostic_norms']['ray_converged'] == '0'
        fractions.append({'variant': case['variant'], 'event':case['event'], 'fraction':fraction['float_display']})
    assert ['%.3f' % (x['fraction']*100) for x in fractions] == ['99.513','99.295','99.446','99.638']
    scientific_paths.extend(gradient_base+x for x in ('summary.json','review.json','execution.json'))
    visual = load(OUT/'visual_review.json')
    assert visual['source_pdf_sha256'] == compile_record['report_sha256']
    assert visual['pages'] == [26,27,28,36,37]
    inventory = {'readme_local_links': local_links, 'tex_literal_paths': paths,
                 'tex_provider_resource_ids_not_files': provider_ids, 'figures': figures}
    (OUT/'path_inventory.json').write_text(json.dumps(inventory, indent=2) + '\n')
    pages = int(re.search(r'^Pages:\s+(\d+)', (OUT/'pdfinfo.txt').read_text(), re.M).group(1))
    result = {'status': 'passed', 'checked_utc': datetime.utcnow().isoformat()+'Z',
              'scope': 'Current documents/compiled PDF and saved reviewed evidence only; no numerical rerun or new ray/inverse acceptance.',
              'checker_sha256': sha(Path(__file__)),
              'compile_receipt_sha256': sha(OUT/'compile.json'),
              'compile_output_files_checked': len(compile_record['output_sha256']),
              'compile_passes': 2, 'compile_log_findings': logs,
              'tex_source_files_checked': len(compile_record['tex_source_sha256']),
              'readme_sha256': sha(ROOT/'README.md'),
              'recovery_checkpoint_sha256': sha(ROOT/'report/recovery_checkpoint.tex'),
              'report_sha256': sha(ROOT/'report/report.pdf'),
              'pdf_pages': pages, 'pdf_bytes': (ROOT/'report/report.pdf').stat().st_size,
              'markdown_links_checked': len(local_links), 'external_markdown_links_not_requested': len(links)-len(local_links),
              'literal_recovery_paths_checked': sum(x['document']=='report/recovery_checkpoint.tex' for x in paths),
              'all_tex_literal_paths_checked': len(paths),
              'contextually_abbreviated_paths': sum(x['basis']!='repository root' for x in paths),
              'figure_references_checked': len(figures), 'missing_paths': [],
              'path_inventory_sha256': sha(OUT/'path_inventory.json'),
              'unchanged_panel_counts': counts, 'unchanged_panel_tex_compared_to': 'usable_curvature_adoption_report_003',
              'canonical_panel_inventory_sha256': {str(p.relative_to(ROOT)): sha(p) for p in [ROOT/'data/panel_audit.csv', ROOT/'data/panel_audit.json']},
              'reviewed_evidence_sha256': {p: sha(ROOT/p) for p in scientific_paths},
              'new_ray_input_controls_passed': 56, 'prior_covariance_controls_unchanged': 39,
              'native_replay_calls_already_completed': 4,
              'first_edge_result_scope': 'Fixed first knot and unchanged remainder; exact straight derivative agrees at roundoff, local curving does not remedy the failed global source criterion.',
              'visual_review_pages': [26, 27, 28, 36, 37],
              'visual_review_basis': 'Root inspected final PDF pages rendered at1400pixel maximum dimension; new CMJ replay, geometry and fixed-gradient text, figure/caption and retained strict-stopping text have no clipping or overlap.',
              'visual_render_receipt': str((OUT/'visual_review.json').relative_to(ROOT)),
              'visual_render_receipt_sha256': sha(OUT/'visual_review.json'),
              'strict_diagnostics': strict_records,
              'hayward_guarded_outcome': {'accepted_updates': 0, 'failed_rays': 181, 'status': 'failed_before_first_trial_objective'},
              'archive_members_verified': archive['verified_members'],
              'cmj_gradient_normal_squared_norm_fractions': fractions,
              'document_change': 'Recorded matched failed CMJ old/D replay, saved near-face geometry and fixed-path gradient localization; no panel promotion or maintained solver change.'}
    target.write_text(json.dumps(result, indent=2, sort_keys=True)+'\n')
    print(json.dumps({'validation_sha256': sha(target), 'pdf_pages': pages,
                      'report_sha256': result['report_sha256'], 'counts': counts}))


if __name__ == '__main__':
    main()
