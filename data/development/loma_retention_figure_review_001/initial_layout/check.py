#!/usr/bin/env python3
"""Verify saved B/C plot arrays and provenance; do not redraw or retrace."""
import csv
import hashlib
import json
import math
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[3]
FIG=ROOT/'figures/diagnostics'


def need(ok,message):
    if not ok:raise ValueError(message)


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):return json.loads(path.read_text())


def rows(path):
    with path.open(newline='') as stream:return list(csv.DictReader(stream))


def check():
    metadata=load(FIG/'loma_retention.json')
    need(sha(FIG/'loma_retention.json')=='32872e1c40e2fef809f8e9b3508fa592257a7eb925b99819a0884071c20f4b8c','Wrong metadata version')
    need(sha(ROOT/'plot_loma_retention.py')==metadata['plot_source_sha256'],'Plot source changed')
    for name,digest in metadata['input_sha256'].items():need(sha(ROOT/name)==digest,'Input changed: '+name)
    for name,digest in metadata['figure_sha256'].items():need(sha(FIG/name)==digest,'Figure changed: '+name)
    variants=[('Fixed cutoff','loma_seed_loaded_b_native_001',1000,40,564,'0'),
              ('Positive curvature','loma_positive_curvature_native_001',145,145,72,'1')]
    counts={}
    for label,directory,updates,pairs,equal,flag in variants:
        out=ROOT/'data/development'/directory;summary=load(out/'summary.json');review=load(out/'review.json')
        need(review['status']=='passed' and review['summary_sha256']==sha(out/'summary.json'),'Missing terminal review')
        if label=='Positive curvature':
            need(sha(out/'review.json')=='2db46c310cba7c2276765fc2278e41d6215b7d56f1a9fb564b165fa108098a89','Changed C review')
        need(summary['native_context']==metadata['native_context'] and len(metadata['native_context'])==199,'Native plot join differs')
        result=[r for r in rows(out/'results.csv') if r['initialization']=='fmm']
        need(len(result)==1 and result[0]['converged']==flag,'Wrong FMM result')
        result=result[0];history=[r for r in rows(out/'history.csv') if r['run_id']==result['run_id'] and r['phase'] in ('initial','accepted')]
        need(len(history)==updates+1 and all(r['observation_index']=='3426' for r in history),'Incomplete native history')
        cumulative=[];total=0
        for row in history:total+=int(row['curvature_pair_accepted']);cumulative.append(total)
        record=metadata['histories'][label]
        need(record['updates']==[int(r['updates']) for r in history]==list(range(updates+1)),'Update array differs')
        need(record['projected_gradient_s_per_km']==[float(r['projected_gradient']) for r in history] and
             all(math.isfinite(v) and v>0 for v in record['projected_gradient_s_per_km']),'Gradient array differs')
        need(record['accepted_curvature_pairs']==cumulative and total==pairs and record['result']==result,'Retention/result array differs')
        need(record['accepted_equal_binary64_actions']==equal==sum(float(r['action_change_s'])==0 for r in history[1:]),'Equal-action count differs')
        need(metadata['unchanged_straight_result']==[r for r in rows(out/'results.csv') if r['initialization']=='straight'][0],
             'Unchanged straight-start result differs')
        counts[label]={'updates':updates,'pairs':pairs,'equal_approximate_actions':equal,'local_flag':flag,
                       'final_projected_gradient_s_per_km':record['projected_gradient_s_per_km'][-1]}
    pdftext=subprocess.check_output(['pdftotext',str(FIG/'loma_retention.pdf'),'-'],universal_newlines=True)
    need('NC/10090782' in pdftext and 'NC.JSJ..EHZ' in pdftext and 'Accepted updates' in pdftext and
         'Combined stopping: gradient bound' in pdftext and '145 updates; local flag 1' in pdftext,'PDF identity/labels differ')
    info=subprocess.check_output(['pdfinfo',str(FIG/'loma_retention.pdf')],universal_newlines=True)
    need(any(line.split()==['Pages:','1'] for line in info.splitlines()),'PDF page inventory differs')
    source=(ROOT/'plot_loma_retention.py').read_text()
    need("set_yscale('log')" in source and "set_xscale('symlog', linthresh=1, linscale=.5)" in source and
         "axes[0].axhline(1e-5" in source,'Source scale/reference line differs')
    need('small action change' in metadata['note'] and 'safe general retention rule' in metadata['note'] and
         'Equal approximate totals are not exact-action classifications' in metadata['note'],'Scope note missing')
    for name,digest in metadata['input_sha256'].items():need(sha(ROOT/name)==digest,'Input changed during review')
    for name,digest in metadata['figure_sha256'].items():need(sha(FIG/name)==digest,'Figure changed during review')
    return dict(status='passed',material_issue_found=False,checker_sha256=sha(Path(__file__)),
        metadata_sha256=sha(FIG/'loma_retention.json'),plot_source_sha256=metadata['plot_source_sha256'],
        figure_sha256=metadata['figure_sha256'],input_sha256=metadata['input_sha256'],native_context=metadata['native_context'],
        reconstructed_counts=counts,all_saved_plotted_arrays_exactly_reconstructed=True,pdf_pages=1,
        visual_review='PNG viewed directly: axes, units, labels, legend, both histories and endpoint annotation readable; no clipping hides data.',
        scope='Saved-array/native/provenance/source and existing-image/PDF-text review only; no redraw or numerical rerun.',
        limitations=['The dashed line shows only the gradient part of the combined stop; a small action change is also required.',
            'Only accepted-update scalar histories are plotted; equality of prefixes does not prove unsaved-path equality.',
            'C has a local combined-stop flag, not strict-gradient/global-first-arrival or general retention-rule certification.'])


if __name__=='__main__':print(json.dumps(check(),indent=2,allow_nan=False))
