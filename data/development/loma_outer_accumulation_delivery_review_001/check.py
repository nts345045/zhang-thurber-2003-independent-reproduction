#!/usr/bin/env python3
"""Check the frozen B publication using saved files only; no plotting or solver run."""
import collections
import csv
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
MANIFEST = ROOT / 'data/development/loma_outer_accumulation_delivery.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text())


def need(ok, message):
    if not ok:
        raise ValueError(message)


def rows(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def check():
    manifest = load(MANIFEST)
    need(sha(MANIFEST) == '5e5565824988625d97814f9cddb5d97da1d621b2bbdb939e2ba22f14df2c6ef0',
         'Unexpected delivery manifest')
    need(len(manifest['sha256']) == 147, 'Unexpected inventory')
    for name, digest in manifest['sha256'].items():
        need(sha(ROOT / name) == digest, 'Changed publication member: ' + name)
    need(not any(name.startswith('src/') or any(token in name for token in
                 ('curvature_capture', 'endpoint_connector', 'interface_candidate'))
                 for name in manifest['sha256']), 'Unreviewed scope included')
    meta_path = ROOT / 'figures/diagnostics/loma_outer_accumulation.json'
    meta = load(meta_path)
    for name, digest in meta['input_sha256'].items():
        need(sha(ROOT / name) == digest, 'Changed plotted input')
    need(meta['plot_source_sha256'] == sha(ROOT / 'plot_outer_accumulation.py'), 'Plot source changed')
    for name, digest in meta['figure_sha256'].items():
        need(sha(meta_path.parent / name) == digest, 'Figure changed')
    history_counts = {}
    for label, folder in [('Original', 'loma_initial_failure_3426_001'),
                          ('Extended outer sum', 'loma_outer_accumulation_native_001')]:
        source = ROOT / 'data/development' / folder
        summary, review = load(source / 'summary.json'), load(source / 'review.json')
        need(review['summary_sha256'] == sha(source / 'summary.json'), 'Stale plotted review')
        result = [r for r in rows(source / 'results.csv') if r['initialization'] == 'fmm']
        need(len(result) == 1 and result[0]['converged'] == '0', 'FMM flag lost')
        result = result[0]
        history = [r for r in rows(source / 'history.csv') if
                   r['run_id'] == result['run_id'] and r['phase'] in ('initial', 'accepted')]
        plotted = meta['histories'][label]
        need(plotted['result'] == result and meta['native_context'] == summary['native_context'],
             'Native/result mismatch')
        need(plotted['updates'] == [int(r['updates']) for r in history] ==
             list(range(int(result['updates']) + 1)), 'Plotted update omission/order')
        need(plotted['projected_gradient_s_per_km'] == [float(r['projected_gradient']) for r in history],
             'Plotted gradient mismatch')
        total, pairs = 0, []
        for row in history:
            total += int(row['curvature_pair_accepted']); pairs.append(total)
        need(plotted['accepted_curvature_pairs'] == pairs, 'Cumulative curvature mismatch')
        equal = sum(float(r['action_change_s']) == 0 for r in history if r['phase'] == 'accepted')
        need(plotted['accepted_equal_binary64_actions'] == equal, 'Equal-action count mismatch')
        history_counts[label] = dict(points=len(history), accepted_updates=int(result['updates']),
                                    curvature_pairs=total, equal_actions=equal, local_flag=result['converged'])
    panels = load(ROOT / 'data/panel_audit.json')
    counts = collections.Counter(p['status'] for p in panels)
    need(len(panels) == 62 and dict(counts) == {'independently reproduced': 1,
         'partially reproduced': 27, 'not reproduced': 34}, 'Panel status changed')
    old = load(ROOT / 'data/development/loma_failed_search_delivery.json')
    need(old['validation']['panel_statuses'] == dict(counts) and
         manifest['validation']['panel_counts'] == dict(reproduced=1, partial=27, not_reproduced=34),
         'Panel counts differ from preceding delivery')
    readme = (ROOT / 'README.md').read_text()
    links = [p for p in re.findall(r'\[[^\]]*\]\(([^)]+)\)', readme)
             if not p.startswith(('http:', 'https:', 'app:', '#'))]
    need(len(links) == 53 and all((ROOT / p.split('#')[0]).exists() for p in links), 'Broken local README link')
    report = (ROOT / 'report/recovery_checkpoint.tex').read_text()
    paths = re.findall(r'\\path\{([^}]+)\}', report)
    need(len(paths) == 34 and all((ROOT / p).exists() for p in paths), 'Broken report evidence path')
    receipt_dir = ROOT / 'data/development/loma_outer_accumulation_report_001'
    receipt = load(receipt_dir / 'compile_receipt.json')
    need(receipt['status'] == 'completed' and len(receipt['commands']) == 2 and
         all(c['return_code'] == 0 for c in receipt['commands']), 'LaTeX pass failed')
    latex_messages = {}
    for name in ('pass_1_stdout.log', 'pass_2_stdout.log'):
        lines = (receipt_dir / name).read_text().splitlines()
        need(not any(re.search(r'^!|Overfull|Undefined control', line) for line in lines),
             'TeX error/overfull box in saved log')
        latex_messages[name] = [line for line in lines if re.search(r'LaTeX Warning|undefined references', line)]
    need(not latex_messages['pass_2_stdout.log'], 'Final LaTeX pass has unresolved warnings')
    pdf = ROOT / 'report/report.pdf'
    need(sha(pdf) == receipt['pdf_sha256'] ==
         'e2d1c753eb045df6dc1b9e24beb909f8913ee91ebc43750eac5d1ec97d0d3dfd' and
         pdf.stat().st_size == receipt['pdf_bytes'] == 1819469, 'Compiled PDF mismatch')
    info = subprocess.check_output(['pdfinfo', str(pdf)], universal_newlines=True)
    need(re.search(r'^Pages:\s+104$', info, re.M), 'PDF page count mismatch')
    text = subprocess.check_output(['pdftotext', '-f', '31', '-l', '32', str(pdf), '-'], universal_newlines=True)
    for phrase in ('436 strict decreases and 564 equal values', 'at update 435',
                   '0.860614 microseconds', '1.36618 microseconds',
                   'Figure 14:', 'does not resolve local'):
        need(phrase in text, 'Published B text missing: ' + phrase)
    for name, digest in manifest['sha256'].items():
        need(sha(ROOT / name) == digest, 'Publication changed during review')
    return dict(status='passed', manifest_sha256=sha(MANIFEST), publication_members_verified=147,
                plot_input_hashes_verified=len(meta['input_sha256']), figure_hashes_verified=2,
                plot_source_sha256=meta['plot_source_sha256'], plotted_history_counts=history_counts,
                full_native_context_matches=True, panel_counts=dict(counts), panels=62,
                local_readme_links=53, report_evidence_paths=34, pdf_sha256=sha(pdf),
                pdf_bytes=pdf.stat().st_size, pdf_pages=104, latex_successful_passes=2,
                latex_messages=latex_messages, final_latex_pass_clean=True,
                check_source_sha256=sha(Path(__file__)),
                scope='Saved arrays, hashes, links, terminal receipts and compiled text; no plot, ray or numerical-control rerun.')


if __name__ == '__main__':
    print(json.dumps(check(), indent=2, allow_nan=False))
