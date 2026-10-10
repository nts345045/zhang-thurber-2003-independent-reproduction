#!/usr/bin/env python3
"""Check this document checkpoint against saved reviewed results; no solver calls."""
import collections
import csv
import hashlib
import json
import re
from datetime import datetime
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


def suite(folder, review_hash, summary_key='summary_sha256'):
    base = D/folder
    review = read(base/'review.json', review_hash)
    assert review['status'] == 'passed'
    summary = read(base/'summary.json', review[summary_key])
    execution = read(base/'execution.json', review['execution_sha256'])
    assert summary['status'] == 'passed' and execution['status'] == 'completed'
    return summary, review


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
        assert warnings == [page_group], warnings
        assert any('multiple pdfs with page group included in a single page' in x for x in lines)
        logs[str(number)] = {'errors_or_overfull': errors, 'undefined': undefined,
                            'case_insensitive_warnings': warnings,
                            'existing_warning': 'location_errors.pdf page14; retained from prior checkpoint'}
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
    prior = read(D/'usable_curvature_adoption_report_003/compile.json')
    for name in ('report/panel_table.tex', 'report/panel_details.tex'):
        assert sha(ROOT/name) == prior['tex_source_sha256'][name]

    loop, loop_review = suite('hayward_old_kernel_trial_backtracking_controls_001',
        'fc750af56ea2d2333c7c1c2856a629181ca96a233fec2fd831ee5fd82b5bad5f')
    assert loop['controls'] == {'before': 4, 'after': 1102}
    assert len(loop['all_valid_byte_parity']) == loop_review['all_valid_identical_files'] == 28
    integration, joint = suite('hayward_old_kernel_trial_backtracking_integration_checks_002',
        '7faa22a6bb009a3c8c5470ffb4e7cff6dddf02987dfb3c18db032f7e362fdda6')
    assert integration['core_checks'] == joint['core_checks'] == 48
    assert joint['external_input_categories'] == 11
    assert joint['actual_trial_fixture']['rejected_trial_count'] == 20
    assert joint['accepted_step_fractions'] == [1/512, 1/2048]
    completion, completion_review = suite('hayward_trial_completion_checks_002',
        'e975435edc021696f0e8766e6e7bcb15a45c8bfa2d09e09388ad4e35e2e7374c', 'controls_summary_sha256')
    assert completion['controls_passed'] == completion['controls_total'] == 190
    assert completion_review['unchanged_original_recipes'] == 189
    assert len(completion_review['previously_unsafe_acceptances_now_rejected']) == 3
    assert completion_review['actual_launcher_prefix_cases'] == 7
    assert completion_review['actual_joint_dd_saved_readback']['rejected_trials'] == 20
    ridge = read(D/'internal_ridge_stationarity_controls_001/summary.json',
        '8b094968da699480af6ddbbb18f12c5a67b9bb6f1451525c759c5cb2de500dfc')
    ridge_review = read(D/'internal_ridge_stationarity_controls_001/root_review.json')
    assert ridge_review['status'] == ridge['status'] == 'passed'
    assert ridge_review['summary_sha256'] == sha(D/'internal_ridge_stationarity_controls_001/summary.json')
    assert (ridge['exact_rational_checks'], ridge['numerical_consistency_checks']) == (37, 62)
    assert ridge['trace_calls'] == ridge['optimizer_calls'] == 0
    launcher, launcher_review = suite('hayward_old_kernel_backtracking_launcher_checks_002',
        '8ee63a3c7e825d5ce75d5d70de023b3f67d13fceea8ae5855583752d14848b22')
    assert launcher['controls_passed'] == launcher['controls_total'] == 62
    assert len(launcher['commands']) == len(launcher_review['lifecycle']) == 5
    assert launcher['compiler_calls'] == launcher['numerical_calls'] == launcher['inverse_calls'] == 0
    assert all(row['passed'] for row in launcher['checks'])
    assert any(row['name'] == 'actual_saved_eligibility_readback' for row in launcher['checks'])
    launcher_base = D/'hayward_old_kernel_backtracking_launcher_001'
    prepared = read(launcher_base/'prepared.json', launcher_review['launcher_prepared_sha256'])
    source_review = read(launcher_base/'root_source_review.json', launcher_review['root_source_review_sha256'])
    assert source_review['status'] == 'passed_source_review'
    assert source_review['prepared_sha256'] == sha(launcher_base/'prepared.json')
    assert source_review['source_pins_verified'] == 15 and source_review['inherited004_pins_verified'] == 13
    archive = D/'trial_backtracking_evidence_001'
    packaging = read(archive/'packaging.json')
    restore = read(archive/'restore_review.json', '599a4cf78318005874a521c359ccf49389cf8777ab1b65b94c8b464f31bd6b22')
    assert packaging['status'] == 'verified_lossless' and restore['status'] == 'passed'
    assert restore['packaging_sha256'] == sha(archive/'packaging.json')
    assert restore['archive_sha256'] == packaging['archive_sha256'] == sha(archive/'evidence.tar.gz')
    assert restore['members_sha256'] == packaging['members_sha256'] == sha(archive/'members.json')
    assert restore['restored_member_count'] == packaging['member_count'] == 14924
    assert restore['symbolic_links'] == packaging['symbolic_links'] == 14
    report = (ROOT/'report/recovery_checkpoint.tex').read_text()
    for phrase in ('1,102 recorded assertions', 'passes 190 saved-table controls',
                   '37 exact rational and 62 numerical checks', 'Its 62 checks',
                   'No new field inversion', 'complete positive launcher integration remains separate'):
        assert phrase in report, phrase
    inventory = {'markdown_links': links, 'tex_literal_paths': paths, 'figures': figures,
                 'provider_resource_ids_not_files': provider_ids}
    (OUT/'path_inventory.json').write_text(json.dumps(inventory, indent=2)+'\n')
    pages = int(re.search(r'^Pages:\s+(\d+)', (OUT/'pdfinfo.txt').read_text(), re.M).group(1))
    result = {'status': 'passed', 'checked_utc': datetime.utcnow().isoformat()+'Z',
              'scope': 'Saved document/compile/link/review-count readback only; no numerical calculation or real launch.',
              'checker_sha256': sha(Path(__file__)), 'input_sha256': PINS,
              'compile_passes': 2, 'compile_log_findings': logs, 'tex_sources': 16,
              'readme_sha256': sha(ROOT/'README.md'), 'failure_summary_sha256': sha(ROOT/'FAILURE_SUMMARY.md'),
              'recovery_checkpoint_sha256': sha(ROOT/'report/recovery_checkpoint.tex'),
              'report_sha256': sha(ROOT/'report/report.pdf'), 'pdf_pages': pages,
              'pdf_bytes': (ROOT/'report/report.pdf').stat().st_size,
              'markdown_links': len(links), 'tex_literal_paths': len(paths), 'figures': len(figures),
              'panel_counts': counts, 'path_inventory_sha256': sha(OUT/'path_inventory.json'),
              'new_counts': {'loop_assertions': 1102, 'all_valid_files': 28, 'core_checks': 48,
                  'joint_local_rejections': 20, 'completion_checks': 190, 'ridge_exact': 37,
                  'ridge_numerical': 62, 'launcher_checks': 62, 'lifecycle_cases': 5},
              'visual_review': 'Separate root visual review required; not claimed by this checker.',
              'limits': ['Initial source eligibility is not later-model accuracy.',
                  'No complete positive final-table launcher fixture; exact binary/return binds the final gate.',
                  'No native stopping flag, panel count or scientific acceptance is promoted.']}
    target.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({'status': result['status'], 'pages': pages, 'validation_sha256': sha(target),
                      'report_sha256': result['report_sha256']}))


if __name__ == '__main__':
    main()
