#!/usr/bin/env python3
"""Read frozen delivery files; no numerical evaluator or plotting import."""
import collections
import csv
from fractions import Fraction as Q
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
MANIFEST = ROOT / 'data/development/loma_interface_diagnostics_delivery.json'
EXPECTED = '7c21c7cbed4a4184d6215dc1ff1096e1b9a18e56415f38830baab03d3ec0ff78'
PDF_SHA = '8998e62502a8dfb1f7efb386daca06fca75f7f60ebc36c15c6f68115b55bbc8c'


def need(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            result.update(block)
    return result.hexdigest()


def load(path):
    return json.loads(path.read_text())


def rows(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def verify(base, mapping):
    for name, digest in mapping.items():
        need(sha(base / name) == digest, 'Changed pinned file: ' + str(base / name))


def interval(value):
    lo, hi = [Q(value[k]) for k in ('lower_rational', 'upper_rational')]
    need(lo <= hi, 'Reversed saved interval')
    return lo, hi


def check():
    need(sha(MANIFEST) == EXPECTED, 'Wrong final delivery manifest')
    manifest = load(MANIFEST)
    need(len(manifest['sha256']) == 329, 'Unexpected delivery inventory')
    verify(ROOT, manifest['sha256'])
    need(sum((ROOT / name).stat().st_size for name in manifest['sha256']) == 123081724,
         'Unexpected delivery byte count')
    need(not any(name.startswith(('src/', 'tmp/')) or
                 'loma_interface_diagnostics_report_001/' in name or
                 'loma_interface_diagnostics_delivery_review_001/' in name
                 for name in manifest['sha256']), 'Excluded/live scope included')

    meta_path = ROOT / 'figures/diagnostics/loma_interface_candidate.json'
    meta = load(meta_path)
    verify(ROOT, meta['input_sha256'])
    verify(meta_path.parent, meta['figure_sha256'])
    need(meta['plot_source_sha256'] == sha(ROOT / 'plot_loma_interface_candidate.py'),
         'Changed plot source')
    candidate_dir = ROOT / 'data/development/loma_interface_candidates_002'
    support_dir = ROOT / 'data/development/loma_candidate_support_001'
    candidate, support = [load(p / 'summary.json') for p in (candidate_dir, support_dir)]
    for directory, data in ((candidate_dir, candidate), (support_dir, support)):
        review = load(directory / 'review.json')
        need(review['status'] == 'passed' and review['summary_sha256'] == sha(directory / 'summary.json'),
             'Stale independent candidate/support review')
        verify(ROOT, data['input_sha256'])
        verify(directory, data['artifact_sha256'])
    need(meta['native_context'] == candidate['native_context'] == support['native_context'] and
         len(meta['native_context']) == 199, 'Plot native context mismatch')
    need(candidate['original_B_result'] == support['original_B_result'] and
         support['original_B_flag_preserved'] == support['original_B_result']['converged'] == '0',
         'Original B flag/result changed')
    need(meta['candidate_nodes'] == support['selected_candidate_nodes'] == [484, 485] and
         support['ray_solves'] == support['optimizer_steps'] == 0,
         'Wrong candidate or unexpected numerical run')
    need([r['nodes_changed'] for r in candidate['probes']] == [[484], [485], [484, 485]],
         'Wrong plotted candidate roster')
    plotted_actions = []
    for plotted, saved in zip(meta['actions'], candidate['probes']):
        lo, hi = interval(saved['action_change_s'])
        need(plotted['nodes_changed'] == saved['nodes_changed'] and
             plotted['interval_s'] == saved['action_change_s'] and plotted['sign'] == saved['sign'],
             'Plotted action mapping mismatch')
        need(plotted['plotted_midpoint_1e_minus16_s'] == float((lo + hi) * 10**16 / 2),
             'Plotted action value/unit mismatch')
        need((hi < 0 and saved['sign'] == 'decrease') or
             (lo > 0 and saved['sign'] == 'increase'), 'Action sign mismatch')
        plotted_actions.append(plotted['plotted_midpoint_1e_minus16_s'])
    need(len(meta['actions']) == 3 and [r['sign'] for r in meta['actions']] ==
         ['decrease', 'increase', 'decrease'], 'Positive single-vertex result omitted')
    plotted_norms = []
    for plotted, key in zip(meta['same_candidate_support_norms'],
                            ('alpha0_internal_norm_s_per_km', 'support_internal_norm_s_per_km')):
        lo, hi = interval(support[key])
        need(plotted['interval_s_per_km'] == support[key] and
             plotted['plotted_midpoint_microseconds_per_km'] == float((lo + hi) * 10**6 / 2),
             'Plotted support value/unit mismatch')
        plotted_norms.append(plotted['plotted_midpoint_microseconds_per_km'])
    need(len(meta['same_candidate_support_norms']) == len(plotted_norms) == 2 and meta['units'] == dict(panel_A='1e-16 seconds',
         panel_B='microseconds per kilometre'), 'Plot units/roster changed')
    need(meta['exact_zero_components_by_existence'] == support['exact_zero_components_by_existence'] ==
         [[484, 'z'], [485, 'z']] and support['complete_internal_components'] == 3396 and
         support['other_components_unchanged'] is True and
         support['complete_internal_components'] - len(support['exact_zero_components_by_existence']) == 3394, 'Support component scope changed')
    need(support['action_change_s'] == candidate['probes'][2]['action_change_s'] and
         all(interval(support[k])[0] > 0 for k in ('feasibility_margin_A', 'feasibility_margin_B')),
         'Action or strict support margin changed')
    support_review = load(support_dir / 'review.json')
    need(meta['independent_support_review_sha256'] == sha(support_dir / 'review.json') and
         support_review['positive_edges'] == 1133 and support_review['internal_components'] == 3396 and
         [r['precision'] for r in support_review['decimal_readbacks']] == [80, 120],
         'Independent full-support readback scope mismatch')
    for entry in support_review['decimal_readbacks']:
        for key, norm in [('alpha0_internal_norm_s_per_km', 'alpha0_norm'),
                          ('support_internal_norm_s_per_km', 'support_norm')]:
            lo, hi = interval(support[key])
            need(lo <= Q(entry[norm]) <= hi, 'Saved independent norm lies outside enclosure')

    endpoint_dir = ROOT / 'data/development/loma_endpoint_connector_native_001'
    endpoint, endpoint_review = [load(endpoint_dir / name) for name in ('summary.json', 'review.json')]
    need(endpoint_review['status'] == 'passed' and
         endpoint_review['summary_sha256'] == sha(endpoint_dir / 'summary.json'), 'Stale endpoint review')
    verify(ROOT, endpoint['input_sha256']); verify(endpoint_dir, endpoint['output_sha256'])
    need(endpoint['geometry_checks']['full_native_fields'] == len(endpoint['native_context']) == 199 and
         all(endpoint['geometry_checks'][k] for k in ('source_x1_x2_exact_bottom',
             'last_layer_depth_only', 'positive_guide', 'connector_in_affine_layer_and_box')),
         'Endpoint component geometry scope mismatch')
    need(endpoint['baseline_source_connector_dz'] == '0' and float(endpoint['baseline_x1_new_dz']) < 0 and
         endpoint['no_new_forward_or_accuracy_flags'] and not endpoint['new_whole_ray_time_evaluated'] and
         endpoint['original_local_convergence_flag'] == '1', 'Endpoint interpretation/flag changed')
    formula = endpoint_dir / 'exact_baseline_formulas.json'
    side = load(endpoint_dir / 'exact_baseline_formulas.json.identifiers.json')
    need(side['file_sha256'] == sha(formula) and side['native_context'] == endpoint['native_context'],
         'Formula full-native attachment missing')

    capture_dir = ROOT / 'data/development/loma_curvature_capture_native_001'
    capture = load(capture_dir / 'review.json')
    need(capture['status'] == 'passed_saved_capture_review' and not capture['material_issue_found'],
         'Capture review not passed')
    for key, name in [('summary_sha256', 'summary.json'), ('execution_sha256', 'execution.json'),
                      ('prepared_sha256', 'prepared.json'), ('controller_completion_sha256', 'controller_completion.json'),
                      ('packaging_receipt_sha256', 'packaging_receipt.json')]:
        need(capture[key] == sha(capture_dir / name), 'Capture terminal review link mismatch')
    need(capture['accepted_pair_records'] == 1000 and capture['retained_pairs'] == 40 and
         capture['last_retained_iteration'] == 434 and capture['pair_records_after_last_retained'] == 565 and
         capture['component_records'] == 1132000 and len(capture['exact_representative_iterations']) == 22,
         'Capture report counts mismatch')
    need(capture['exact_saved_count_inventory']['computed_positive_rejected'] == 960 and
         capture['exact_classification_inventory']['exact_stored_threshold_differs_from_recorded_retention'] == 0 and
         capture['exact_classification_inventory']['exact_actual_movement_threshold_differs_from_recorded_retention'] == 0 and
         capture['original_FMM_local_flag'] == '0', 'Capture positivity/flag interpretation changed')
    attachment = load(capture_dir / 'packaging_receipt.json')
    verify(ROOT, attachment['input_sha256']); verify(ROOT, attachment['output_sha256'])
    need(attachment['raw_bytes'] == 273739890 and
         (capture_dir / 'curvature_components.csv.gz').stat().st_size == 100494158,
         'Complete capture storage changed')

    panels = load(ROOT / 'data/panel_audit.json')
    counts = dict(collections.Counter(row['status'] for row in panels))
    need(len(panels) == 62 and counts == {'independently reproduced': 1,
         'partially reproduced': 27, 'not reproduced': 34} == manifest['validation']['panel_counts'],
         'Manuscript panel statuses changed')
    readme = (ROOT / 'README.md').read_text()
    links = [p for p in re.findall(r'\[[^\]]*\]\(([^)]+)\)', readme)
             if not p.startswith(('http:', 'https:', 'app:', '#'))]
    need(len(links) == 57 and all((ROOT / p.split('#')[0]).exists() for p in links), 'README link mismatch')
    report = (ROOT / 'report/recovery_checkpoint.tex').read_text()
    paths = re.findall(r'\\path\{([^}]+)\}', report)
    need(len(paths) == 41 and all((ROOT / p).exists() for p in paths), 'Report evidence path mismatch')
    compile_dir = ROOT / 'data/development/loma_interface_diagnostics_report_003'
    compile_receipt = load(compile_dir / 'compile_receipt.json')
    need(compile_receipt['status'] == 'completed' and len(compile_receipt['commands']) == 2 and
         all(c['return_code'] == 0 for c in compile_receipt['commands']), 'Final LaTeX execution incomplete')
    latex_messages = {}
    for name in ('pass_1_stdout.log', 'pass_2_stdout.log'):
        lines = (compile_dir / name).read_text().splitlines()
        need(not any(re.search(r'^!|Overfull|Undefined control', line) for line in lines), 'TeX error/overflow')
        latex_messages[name] = [line for line in lines if re.search(r'LaTeX Warning|undefined references', line)]
    need(not latex_messages['pass_2_stdout.log'], 'Unresolved final LaTeX warnings')
    pdf = ROOT / 'report/report.pdf'
    need(sha(pdf) == compile_receipt['pdf_sha256'] == PDF_SHA and
         pdf.stat().st_size == compile_receipt['pdf_bytes'] == 1847852, 'Compiled PDF mismatch')
    info = subprocess.check_output(['pdfinfo', str(pdf)], universal_newlines=True)
    need(re.search(r'^Pages:\s+106$', info, re.M), 'Compiled PDF page count mismatch')
    text = subprocess.check_output(['pdftotext', str(pdf), '-'], universal_newlines=True)
    page_text = [' '.join(page.split()) for page in text.split('\f')]
    phrases = ['All 960 discarded pairs', 'all 565 subsequent pairs are discarded',
               '22 representative iterations', 'Static interface candidates',
               '3,396 component enclosures', 'Both inward normal endpoint derivatives',
               'does not reoptimize the ray or promote its accuracy flags']
    locations = {}
    for phrase in phrases:
        locations[phrase] = [i + 1 for i, page in enumerate(page_text) if phrase in page]
        need(locations[phrase], 'Compiled scientific text missing: ' + phrase)
    verify(ROOT, manifest['sha256'])
    return dict(status='passed',manifest_sha256=EXPECTED,publication_members_verified=329,
                publication_bytes=123081724,plot_input_pins=len(meta['input_sha256']),figure_hashes_verified=2,
                plot_source_sha256=meta['plot_source_sha256'],full_199_field_native_context_matches=True,
                action_bar_values_1e_minus16_s=plotted_actions,support_bar_values_microseconds_per_km=plotted_norms,
                support_components=3396,capture_exact_representative_iterations=22,
                capture_review_sha256=sha(capture_dir/'review.json'),endpoint_review_sha256=sha(endpoint_dir/'review.json'),
                support_review_sha256=sha(support_dir/'review.json'),panels=62,panel_counts=counts,
                local_readme_links=57,report_evidence_paths=41,pdf_sha256=PDF_SHA,pdf_pages=106,pdf_bytes=1847852,
                latex_successful_passes=2,latex_messages=latex_messages,final_latex_pass_clean=True,
                compiled_phrase_pages=locations,checker_sha256=sha(Path(__file__)),
                scope='Saved arrays, reviewed result arithmetic, metadata, terminal links, hashes and compiled text only; no ray, action, numerical-control or plot rerun.')


if __name__ == '__main__':
    print(json.dumps(check(), indent=2, allow_nan=False))
