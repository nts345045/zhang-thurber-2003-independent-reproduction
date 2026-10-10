#!/usr/bin/env python3
"""Independent saved-only shooting review; never import or call the evaluator."""
import collections
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SUPPLEMENT = ROOT / 'data/development/loma_endpoint_shooting_baselines_001'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(folder, name):
    return json.loads((folder / name).read_text())


def require(test, message):
    if not test:
        raise ValueError(message)


def pins(folder):
    summary = read(folder, 'summary.json')
    checked = {str((folder/'summary.json').relative_to(ROOT)): sha(folder/'summary.json')}
    for name, digest in summary['input_sha256'].items():
        require(sha(ROOT/name) == digest, 'Input pin: ' + name)
        checked[name] = digest
    for name, digest in summary['output_sha256'].items():
        require(sha(folder/name) == digest, 'Output pin: ' + name)
        checked[str((folder/name).relative_to(ROOT))] = digest
    for name in ('README.md',):
        checked[str((folder/name).relative_to(ROOT))] = sha(folder/name)
    execution = read(folder, 'execution.json')
    require(execution['status'] == 'completed' and execution['return_code'] == 0, 'Terminal gate')
    require(execution['input_sha256'] == summary['input_sha256'], 'Execution input pins')
    return summary, checked


def finite(values):
    return all(math.isfinite(v) for v in values)


def basis(point, axes):
    q = [(point[j]-axes[j][0])/(axes[j][1]-axes[j][0]) for j in range(3)]
    return [(q[0] if i else 1-q[0])*(q[1] if j else 1-q[1])*(q[2] if k else 1-q[2])
            for k in (0,1) for j in (0,1) for i in (0,1)]


def main():
    original, original_pins = pins(HERE)
    supplement, supplement_pins = pins(SUPPLEMENT)
    require(sha(HERE/'summary.json') == supplement['original_summary_sha256'], 'Original association')
    inputs = read(HERE, 'invented_inputs.json')
    require(inputs['resource_ids'] is None and inputs['geometry'] == 'invented only', 'Invented-only scope')
    axes = inputs['axes']
    cases = {r['name']: r for r in inputs['cases']}
    settings = inputs['settings']
    bs = read(HERE, 'baseline_results.json')
    cs = read(HERE, 'comparisons.json')
    ps = read(HERE, 'perturbations.json')
    supplemental = read(SUPPLEMENT, 'baseline_candidates.json')
    sc = read(SUPPLEMENT, 'comparison.json')
    bm = {(r['setting'],r['case']):r['result'] for r in bs}
    sm = {(r['setting'],r['both_bottom']):r for r in supplemental}
    require(len(bs)==len(bm)==len(cs)==40 and len(cases)==20, 'Baseline support')
    require(set(bm)=={(s['name'],c) for s in settings['ode'] for c in cases}, 'Baseline roster')
    require(len(sm)==len(supplemental)==4 and set(sm)=={(s,b) for s in ('base','tight') for b in (False,True)}, 'Supplement support')
    require(read(SUPPLEMENT,'execution.json')['environment']==read(HERE,'execution.json')['environment'], 'Replay environment')
    require(len(ps)==160 and all(r['same_value_candidates'] for r in ps), 'Perturbation support')
    selected_count, full_points = 0, 0
    largest_domain, largest_invariant, largest_kernel_identity_error = 0.,0.,0.
    baseline_topologies = collections.Counter()

    def inspect_result(result, nodes=None):
        nonlocal selected_count, full_points, largest_domain, largest_invariant, largest_kernel_identity_error
        good = [r for r in result['candidates'] if r['valid']]
        require(good and result['selected']==min(good,key=lambda r:r['time']), 'Least saved admissible candidate')
        selected_count += 1
        for r in good:
            require(r['root_success'] and r['time']>0 and math.isfinite(r['time']), 'Finite matched candidate')
            require(len(r['source'])==len(r['receiver'])==3 and len(r['kernels'])==8, 'Derivative dimensions')
            require(finite(r['source']+r['receiver']+r['kernels']+r['endpoint_match']), 'Finite arrays')
            require(r['maximum_endpoint_mismatch_km']<5e-11 and r['maximum_domain_violation_km']<5e-11 and
                    r['maximum_invariant_error']<1e-9, 'Recorded numerical admissibility')
            require(r['numerical_admissibility_only'] and not r['global_minimum_or_root_completeness_certified'], 'Scope flags')
            if r['topology']!='direct':
                require(r['durations'][1]>0 and all(t>=0 for t in r['durations']), 'Guide duration')
            for piece in r['pieces']:
                require(piece['minimum_reaction'] is None or piece['minimum_reaction']>=0, 'Guide reaction')
                points = piece.get('points',[])
                if not points:
                    continue
                require(nodes is not None, 'Saved points without model')
                for point in points:
                    require(len(point)==6 and finite(point), 'Finite phase-space sample')
                    violation=max([0.]+[axes[j][0]-point[j] for j in range(3)]+[point[j]-axes[j][1] for j in range(3)])
                    require(violation<5e-11, 'Saved sample outside declared box tolerance')
                    v=sum(n*w for n,w in zip(nodes,basis(point,axes)))
                    require(v>0 and math.isfinite(v), 'Positive sampled velocity')
                    invariant=abs(v*v*sum(p*p for p in point[3:])-1.)
                    require(invariant<1e-9, 'Saved invariant sample')
                    largest_domain=max(largest_domain,violation)
                    largest_invariant=max(largest_invariant,invariant)
                    full_points+=1
            if nodes is not None:
                error=abs(r['time']+sum(n*k for n,k in zip(nodes,r['kernels'])))
                largest_kernel_identity_error=max(largest_kernel_identity_error,error)
                require(error<1e-13, 'Original-node kernel/action scaling identity')

    for row in bs:
        inspect_result(row['result'],cases[row['case']]['nodes'])
        baseline_topologies[row['result']['selected']['topology']]+=1
    for row in supplemental:
        require(row['mixed'] is True, 'Supplement is mixed')
        require(row['a']==[0.,0.,0. if row['both_bottom'] else -2.**-12] and row['b']==[.2,.15,0.], 'Supplement geometry')
        inspect_result(row['result'],row['original_nodes'])
    max_time=max_source=max_receiver=0.
    for row in cs:
        selected=bm[(row['setting'],row['case'])]['selected']; oracle=row['oracle']
        require(row['selected_valid'] and row['time_error_s']==selected['time']-oracle['time'], 'Saved time difference')
        for side in ('source','receiver'):
            norm=math.sqrt(sum((a-b)**2 for a,b in zip(selected[side],oracle[side])))
            require(abs(norm-row[side+'_error_s_per_km'])<=1e-26, 'Saved vector norm')
        passed=abs(row['time_error_s'])<=25e-6 and max(row['source_error_s_per_km'],row['receiver_error_s_per_km'])<=3e-6
        require(row['accuracy_pass']==passed and passed, 'Unchanged analytic criteria')
        max_time=max(max_time,abs(row['time_error_s'])); max_source=max(max_source,row['source_error_s_per_km']); max_receiver=max(max_receiver,row['receiver_error_s_per_km'])
    comparison_keys=lambda r:tuple((k,r[k]) for k in ('kind','setting','mixed','both_bottom','node','side','axis','h') if k in r)
    require(len(set(comparison_keys(r) for r in ps))==160,'Unique comparison rows')
    stored_components=boundary_reconstructed=0
    groups=collections.defaultdict(list)
    counts=collections.Counter(); maxima=collections.defaultdict(float)
    scm={comparison_keys(r):r for r in sc}
    require(len(sc)==len(scm)==102,'Supplement comparison support')
    for row in ps:
        for result in row['results']:
            inspect_result(result)
        base=(sm[(row['setting'],row['both_bottom'])]['result']['selected'] if row['mixed'] else
              bm[(row['setting'],'scalar_regime_12')]['selected'])
        if row['kind']=='model':
            counts['model']+=1
            nodes=sm[(row['setting'],row['both_bottom'])]['original_nodes'] if row['mixed'] else cases['scalar_regime_12']['nodes']
            component=-nodes[row['node']]*base['kernels'][row['node']]
            require(component==row['kernel_s'],'Original-node log-slowness column')
            fd=(row['results'][1]['selected']['time']-row['results'][0]['selected']['time'])/(2*row['h'])
            require(fd==row['finite_difference_s'] and fd-component==row['difference_s'],'Model finite difference arithmetic')
            maxima['model_s']=max(maxima['model_s'],abs(row['difference_s']))
        else:
            component=base['source' if row['side']==0 else 'receiver'][row['axis']]
            require(component==row['momentum_component'],'Endpoint component')
            if row['inward_one_sided']:
                counts['boundary']+=1
                fd=(base['time']-row['results'][0]['selected']['time'])/row['h']
                groups[(row['setting'],row['mixed'],row['both_bottom'],row['side'])].append(row)
                require(abs(row['difference_s_per_km'])>3e-6,'Raw boundary failure retained')
                if row['mixed']: boundary_reconstructed+=1
            else:
                counts['central']+=1
                fd=(row['results'][1]['selected']['time']-row['results'][0]['selected']['time'])/(2*row['h'])
                maxima['central_s_per_km']=max(maxima['central_s_per_km'],abs(row['difference_s_per_km']))
            require(fd==row['finite_difference_s_per_km'] and fd-component==row['difference_s_per_km'],'Endpoint finite difference arithmetic')
        if row['mixed']:
            saved=scm[comparison_keys(row)]
            require(saved['exact_match'] and saved['recorded_component']==saved['supplemental_component']==component,'Supplement component join')
            stored_components+=1
            if row['kind']=='endpoint' and row['inward_one_sided']:
                require(saved['exact_secant_match'] and saved['recorded_secant']==saved['supplemental_secant']==fd,'Supplement secant join')
    require(dict(counts)==dict(model=80,central=56,boundary=24),'Comparison classes')
    require(stored_components==102 and boundary_reconstructed==18,'Replay counts')
    ratios=[]
    for group in groups.values():
        group.sort(key=lambda r:r['h'],reverse=True)
        require([r['h'] for r in group]==[2.**-20,2.**-24,2.**-28],'Boundary ladder')
        errors=[abs(r['difference_s_per_km']) for r in group]
        ratios += [errors[j]/errors[j+1] for j in range(2)]
    require(len(groups)==8,'Boundary groups')
    common=dict(status='passed', reviewer='/root/scientific_audit/ray_math_review',
        method='Complete source/math read plus independent saved-table, finite-array, sampled-state and hash checks; no evaluator import, ODE, root search, action reintegration or native calculation.',
        checker_sha256=sha(Path(__file__)), material_issue_found=False,
        sampled_phase_space_points_rechecked=full_points,
        maximum_saved_sample_domain_violation_km=largest_domain,
        maximum_reconstructed_sample_invariant_error=largest_invariant,
        maximum_original_node_kernel_action_identity_error_s=largest_kernel_identity_error,
        numerical_comparison_tolerances=dict(saved_vector_norm_reconstruction=1e-26,kernel_action_identity_s=1e-13),
        limitations=['One root per topology and numerical sampled admissibility; no global root completeness, exact envelope or continuous-domain certificate.',
                    'Original 24 raw bottom-normal finite-step discrepancies remain failures; no extrapolation or flag promotion.',
                    'The four-baseline supplement repeats the same numerical implementation and is not an independent ODE validation.',
                    'No native correction, production ray behavior or inverse acceptance follows.'])
    review=dict(common,summary_sha256=sha(HERE/'summary.json'),execution_sha256=sha(HERE/'execution.json'),
        source_sha256=sha(HERE/'source/check_endpoint_shooting.py'),
        original_input_pins=3,original_output_pins=8,
        input_sha256=original_pins,
        baseline_comparisons=40,baseline_accuracy_passes=40,baseline_selected_topologies=dict(baseline_topologies),
        perturbation_comparisons=160,comparison_classes=dict(counts),
        maximum_affine_time_error_s=max_time,maximum_affine_source_norm_s_per_km=max_source,maximum_affine_receiver_norm_s_per_km=max_receiver,
        maximum_model_fd_discrepancy_s=maxima['model_s'],maximum_central_endpoint_discrepancy_s_per_km=maxima['central_s_per_km'],
        raw_boundary_failures=24,boundary_error_reduction_factors=[min(ratios),max(ratios)],
        math_review=['Hamiltonian full off-shell equations, positive action and original-node kernels have consistent signs.',
                    'Backward first-cap action and kernels enter with a minus sign; endpoint momenta keep the physical forward orientation.',
                    'Reduced zero-cap matching systems, tangential momentum matching and nonnegative bottom reaction are consistent for z<=B.',
                    'Strictly negative bilinear bottom reaction precheck rejects only an everywhere-negative face; mixed signs are tested on the candidate.',
                    'Original-node log-slowness columns are -v_j K_j. Affine oracles are separate; all trial models use the same trilinear action.'],
        original_retention_gap='Four mixed baselines were absent from original outputs; the separately pinned supplement supplies them without changing original results.',
        supplemental_summary_sha256=sha(SUPPLEMENT/'summary.json'))
    supplementary=dict(common,summary_sha256=sha(SUPPLEMENT/'summary.json'),execution_sha256=sha(SUPPLEMENT/'execution.json'),
        original_summary_sha256=sha(HERE/'summary.json'),input_sha256=supplement_pins,
        frozen_evaluator_matches_original=True,exact_runtime_matches_original=True,
        baseline_count=4,original_components_exactly_reproduced=102,old_mixed_boundary_secants_exactly_reproduced=18,
        changed_original_results=0,independently_reintegrated_trajectories=0)
    for folder,record in ((HERE,review),(SUPPLEMENT,supplementary)):
        for path,digest in record['input_sha256'].items(): require(sha(ROOT/path)==digest,'Post-read pin')
        with (folder/'review.json').open('x') as stream:
            stream.write(json.dumps(record,indent=2,allow_nan=False)+'\n')
        print(str((folder/'review.json').relative_to(ROOT)),sha(folder/'review.json'))
    print(json.dumps(dict(selected_results_checked=selected_count,full_points=full_points,classes=dict(counts),boundary_failures=24)))


if __name__=='__main__':
    main()
