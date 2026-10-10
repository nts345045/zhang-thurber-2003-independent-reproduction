#!/usr/bin/env python3
"""Review saved invented scalar-family tables; no action/minimum evaluation."""
from decimal import Decimal as D, localcontext
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'data/development/loma_endpoint_scalar_contact_controls_001'


def need(ok,message):
    if not ok:raise ValueError(message)


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):return json.loads(path.read_text())


def finite(value):
    number=D(value);need(number.is_finite(),'Nonfinite saved number');return number


def verify(base,mapping):
    for name,digest in mapping.items():need(sha(base/name)==digest,'Changed file: '+str(base/name))


def check():
    summary,execution,plan,checks=[load(OUT/n) for n in ('summary.json','execution.json','invented_inputs.json','checks.json')]
    need(summary['status']=='completed_restricted_family_with_unresolved_perturbed_minima' and
         execution['status']=='completed' and execution['return_code']==0,'Not complete')
    verify(ROOT,summary['input_sha256']);verify(OUT,summary['output_sha256'])
    need(execution['input_sha256']==summary['input_sha256'] and len(checks)==summary['controls_passed']==87 and
         all(c['passed'] is True for c in checks),'Saved control inventory/status differs')
    need(plan['geometry']=='invented; no provider identities' and plan['gauss_points']==32 and
         plan['precisions']==[80,120] and plan['scalar_scan_intervals']==16 and
         plan['node_order']==[[i,j,k] for k in range(2) for j in range(2) for i in range(2)],'Geometry/order/settings differ')
    powers=[None,8,12,16,20,24,28];hpowers=[12,16,20,24];runs=[];inventory=[]
    for precision in (80,120):
        data=load(OUT/('results_'+str(precision)+'.json'));runs.append(data)
        need(data['precision']==precision and len(data['scalar'])==7 and len(data['model'])==224 and
             len(data['perturbed_models'])==448,'Saved roster count differs')
        need([r['epsilon_power'] for r in data['scalar']]==powers,'Scalar order differs')
        roster=[(power,node,hp) for power in powers for node in range(8) for hp in hpowers]
        need([(r['epsilon_power'],r['node'],r['parameter_power']) for r in data['model']]==roster,'Model order differs')
        perturbed={(r['epsilon_power'],r['node'],r['parameter_power'],r['sign']):r for r in data['perturbed_models']}
        need(len(perturbed)==448 and list(perturbed)==[key+(sign,) for key in roster for sign in (-1,1)],'Perturbed order/uniqueness differs')
        with localcontext() as ctx:
            ctx.prec=precision
            for r in data['scalar']:
                boundary=r['epsilon_power'] is None;eps=D(0) if boundary else D(2)**(-r['epsilon_power'])
                need(finite(r['epsilon_km'])==eps,'Epsilon changed')
                c=r['numerical_candidate'];oracle=r['analytic_family_oracle']
                need(0<=finite(c['contact'])<=D('.25') and finite(c['time'])>0,'Invalid baseline candidate')
                need(oracle['minimum_certified'] is True and oracle['uniqueness']==(not boundary),'Baseline proof semantics differs')
                need(finite(r['quadrature_minus_oracle_s'])==finite(c['time'])-finite(oracle['value']), 'Saved oracle subtraction differs')
                if boundary:
                    need(c['minimum_certified'] is True and c['derivative'] is None and
                         r['fixed_contact_source_partial_xyz'] is None and oracle['contact'] is None and
                         finite(oracle['inward_value_derivative'])==0 and r['reoptimized_value_secant_s_per_km'] is None,
                         'Boundary nonuniqueness/degeneracy was overwritten')
                else:
                    need(c['minimum_certified'] is False and c['classification']=='lowest_sampled_stationary_or_endpoint_candidate',
                         'Numerical search claims a certificate')
                    need(len(r['fixed_contact_source_partial_xyz'])==3 and
                         all(finite(v).is_finite() for v in r['fixed_contact_source_partial_xyz']),'Missing full source partial')
                    need(finite(r['reoptimized_value_secant_s_per_km'])==finite(oracle['excess'])/eps and
                         finite(r['polygon_to_curved_excess_ratio'])==finite(oracle['excess'])/finite(oracle['curved_excess']),
                         'Saved secant/coefficient ratio differs')
            failures=[0,0];unresolved=0;uncertified=0
            for row in data['model']:
                key=(row['epsilon_power'],row['node'],row['parameter_power']);h=D(2)**(-key[2])
                need(finite(row['h'])==h,'Parameter step changed')
                v=D(5+int(key[1]>=4));kernel=finite(row['original_nodal_kernel_s2_per_km'])
                column=finite(row['negative_log_column_s']);need(column==-v*kernel,'Original nodal column sign/scaling differs')
                times={}
                for sign in (-1,1):
                    r=perturbed[key+(sign,)];velocities=list(map(finite,r['velocities']))
                    need(len(velocities)==8 and min(velocities)>0,'Invalid nodal speed')
                    need(all(x==D(5+int(j>=4)) for j,x in enumerate(velocities) if j!=key[1]),'More than one model node changed')
                    need((velocities[key[1]]<v)==(sign==1),'Negative-log perturbation sign differs')
                    c=r['scalar_candidate'];times[sign]=finite(c['time'])
                    need(0<=finite(c['contact'])<=D('.25') and times[sign]>0,'Perturbed candidate outside family')
                    boundary=key[0] is None
                    need(c['minimum_certified']==boundary and c['classification']==
                         ('all_contacts_same_curve_exact_family_value' if boundary else 'lowest_sampled_stationary_or_endpoint_candidate'),
                         'Perturbed minimum wrongly certified')
                    if c['derivative'] is not None:finite(c['derivative'])
                    if c['bracket'] is not None:
                        left,right=map(finite,c['bracket']);need(0<=left<=right<=D('.25') and right-left<=D('1e-28'), 'Invalid saved bracket')
                central=(times[1]-times[-1])/(2*h)
                need(central==finite(row['reoptimized_candidate_central_difference_s']),'Saved candidate FD arithmetic differs')
                fixed_error=finite(row['fixed_curve_central_difference_s'])-column;candidate_error=central-column
                need(fixed_error==finite(row['fixed_curve_error_s']) and candidate_error==finite(row['candidate_error_s']), 'Saved column errors differ')
                need(row['fixed_curve_within_declared_budget']==(abs(fixed_error)<=D('1e-10')) and
                     row['candidate_within_declared_budget']==(abs(candidate_error)<=D('1e-10')),'Budget classification differs')
                need(row['restricted_family_envelope_justified']==(key[0] is None) and
                     row['perturbed_global_minima_certified']==(key[0] is None) and
                     row['numerical_derivative_error_certified'] is False,'Unresolved certificate status changed')
                failures[0]+=not row['fixed_curve_within_declared_budget'];failures[1]+=not row['candidate_within_declared_budget']
                unresolved+=not row['restricted_family_envelope_justified'];uncertified+=not row['numerical_derivative_error_certified']
            need(failures==[0,0] and unresolved==192 and uncertified==224,'Declared unresolved/failure counts differ')
            # At y=0, the independently represented mirror-y node kernels coincide.
            lookup={(r['epsilon_power'],r['node'],r['parameter_power']):r for r in data['model']}
            for power in powers:
                for hp in hpowers:
                    for first,last in ((0,2),(1,3),(4,6),(5,7)):
                        need(finite(lookup[(power,first,hp)]['negative_log_column_s'])==
                             finite(lookup[(power,last,hp)]['negative_log_column_s']),'Mirror-y kernel restriction differs')
            inventory.append(dict(precision=precision,scalar_cases=7,model_columns=224,perturbations=448,
                fixed_curve_budget_failures=failures[0],candidate_budget_failures=failures[1],
                unresolved_perturbed_family_envelopes=unresolved,uncertified_error_bounds=uncertified))
    with localcontext() as ctx:
        ctx.prec=120
        difference=max(abs(D(a[k])-D(b[k])) for a,b in zip(runs[0]['model'],runs[1]['model']) for k in
                       ('negative_log_column_s','fixed_curve_central_difference_s','reoptimized_candidate_central_difference_s'))
    need(difference==D(summary['maximum_80_120_digit_model_difference_s']),'Precision difference summary differs')
    verify(ROOT,summary['input_sha256']);verify(OUT,summary['output_sha256'])
    return dict(status='passed',material_issue_found=False,reviewer='scientific_audit/ray_math_review',
        controls_summary_sha256=sha(OUT/'summary.json'),summary_sha256=sha(OUT/'summary.json'),
        execution_sha256=sha(OUT/'execution.json'),checker_sha256=sha(Path(__file__)),
        source_sha256=summary['input_sha256']['diagnostics/check_endpoint_scalar_contact.py'],
        verified_input_sha256=summary['input_sha256'],verified_output_sha256=summary['output_sha256'],
        controls_passed_as_recorded=87,independently_reconstructed_inventory=inventory,
        model_arithmetic_precision_difference_s=str(difference),
        source_math_review=[
            'The i-fastest original eight-node trilinear shape functions and their spatial gradients preserve the stated single-cell model.',
            'Segment time, both endpoint first variations and velocity kernels use the same positive reciprocal-trilinear quadrature action; negative-log columns are -v_j times the velocity kernel.',
            'For positive epsilon, baseline A(r)=alpha*sqrt(r^2+epsilon^2)+(ell-r)/V has positive second derivative alpha*epsilon^2/(r^2+epsilon^2)^(3/2); the stated interior minimizer and excess follow.',
            'At epsilon=0 the whole family follows one horizontal curve; the collapsed source link has no selected endpoint partial, and numerical time remains an uncertified quadrature value.',
            'The right collapsed-link contact derivative uses the valid left limit -1/v(b); positive-epsilon endpoints and all candidate contacts stay in the declared finite cell.',
            'The continuous guide excess at g=1 is atanh(q)-q; the two-link excess approaches the stated 3/(2*sqrt(2)) ratio.'],
        scope='Read-only source/math and saved table/arithmetic/hash inspection, with no family/segment/minimum/FD numerical rerun.',
        limitations=[
            'The 87 recorded controls are not a global perturbed-minimum or numerical-error certificate.',
            'All 192 positive-epsilon perturbed model-envelope comparisons and all 224 derivative error bounds per precision remain unresolved.',
            'The scan may miss stationary roots; high precision and polynomial Gauss moments do not certify continuous quadrature or candidate ranking.',
            'At y=0 mirror-y nodes have identical kernels; eight original model columns remain represented without claiming unrestricted three-dimensional geometry.',
            'No native geometry, production solver, nodal-grid Jacobian promotion or whole-path envelope certification is assessed.'])


if __name__=='__main__':print(json.dumps(check(),indent=2,allow_nan=False))
