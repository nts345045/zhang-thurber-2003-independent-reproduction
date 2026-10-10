#!/usr/bin/env python3
"""Exact directional controls and separately labeled invented quadrature readback."""
import csv
from decimal import Decimal as D, localcontext
from fractions import Fraction as Q
import json
from pathlib import Path
import sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent

def integral_abs(a,b):
    if a*b>=0:return (abs(a)+abs(b))/2
    return (a*a+b*b)/(2*(abs(a)+abs(b)))

def split_integral(a,b):
    cuts=[Q(0),Q(1)]
    if a!=b:
        root=-a/(b-a)
        if 0<root<1:cuts.insert(1,root)
    return sum((abs(a*(r-l)+(b-a)*(r*r-l*l)/2) for l,r in zip(cuts[:-1],cuts[1:])),Q(0))

def decimal(value):
    value=Q(value)
    return D(value.numerator)/D(value.denominator)

def formula(v,k,x,precision):
    with localcontext() as ctx:
        ctx.prec=precision
        v,k,x=decimal(v),decimal(k),decimal(x)
        h=D(1)/2;u=abs(x)
        if not u:return +D(1)/v,+(-k*h/(v*v))
        length=(h*h+u*u).sqrt();logarithm=((v+k*u)/v).ln()
        mean=logarithm/(k*u)
        mean_prime=(k*u/(v+k*u)-logarithm)/(k*u*u)
        sign=1 if x>0 else -1
        return +(2*length*mean),+(sign*2*(u/length*mean+length*mean_prime))

def main():
    if len(sys.argv)!=2:raise ValueError('Usage: check.py RESULTS_DIRECTORY')
    out=Path(sys.argv[1]).resolve();out.relative_to(HERE)
    checks=[]
    def check(name,condition):
        checks.append({'name':name,'passed':bool(condition)})
        if not condition:raise AssertionError(name)
    values=list(map(Q,[-2,-1,0,1,2]))
    for a in values:
        for b in values:check('independent_split_integral_%s_%s'%(a,b),integral_abs(a,b)==split_integral(a,b))
    h=Q(1,2)
    fast=h/36;slow=-h/25
    check('fast_two_edges_give_midpoint_directional_coefficient',2*h*integral_abs(Q(0),Q(1))/36==fast)
    check('slow_two_edges_give_midpoint_directional_coefficient',-2*h*integral_abs(Q(0),Q(1))/25==slow)
    check('fast_normal_directions_nonnegative',fast>0)
    check('slow_both_normal_directions_strictly_negative',slow<0)
    check('slow_clarke_interval_contains_zero',slow<0<-slow)
    c=Q(1);bias=(-3*c/8,3*c/8)
    def directional(a,b):return bias[0]*a+bias[1]*b+c*integral_abs(a,b)
    coordinate_values=[]
    for a,b in [(Q(1),Q(0)),(Q(-1),Q(0)),(Q(0),Q(1)),(Q(0),Q(-1))]:
        value=directional(a,b);coordinate_values.append(str(value));check('positive_coordinate_probe_%s_%s'%(a,b),value>=c/8)
    coupled=directional(Q(1),Q(-1))
    check('coupled_direction_decreases',coupled==-c/4)
    target=(-bias[0]/c,-bias[1]/c)
    check('independent_marginal_box_contains_canceling_target',all(-Q(1,2)<=v<=Q(1,2) for v in target))
    A=(target[0]+Q(1,2))/2;B=(target[1]+Q(1,2))/2
    check('true_correlated_moment_set_excludes_canceling_target',not((A+B)**2<=2*A and (A+B)**2<=2*B))
    exact={'units':{'coordinates':'km','velocity':'km/s','action':'s','directional_gradient':'s/km'},
           'fast_ridge':{'v':'6-|x|','half_separation_km':'1/2','minimum_time_s':'1/6','normal_directional_coefficient':str(fast),
                         'selected_right_cell_midpoint_partial':str(fast),'global_minimum_basis':'v<=6 everywhere and every connecting curve has length>=1'},
           'slow_face':{'v':'5+|x|','face_time_s':'1/5','normal_directional_coefficient':str(slow),
                        'clarke_normal_interval':[str(slow),str(-slow)],'directional_stationary':False},
           'false_box_component':{'scope':'Exact abstract segment directional component plus declared smooth linear term, not a full constructed physical ray.',
                                  'c':str(c),'smooth_bias':[str(x) for x in bias],'coordinate_directional_values':coordinate_values,
                                  'coupled_direction':['1','-1'],'coupled_directional_value':str(coupled),
                                  'canceling_target':[str(x) for x in target],'positive_selector_moments':[str(A),str(B)]}}
    with (out/'exact_controls.json').open('x') as f:json.dump({'identities':exact,'checks':checks},f,indent=2);f.write('\n')
    # Decimal ln/sqrt comparisons are numerical consistency checks, not interval proofs.
    with (out/'paths.csv').open() as f:rows=list(csv.DictReader(f))
    assert len(rows)==14
    expected_x=[0.]+[s*2.**(-e) for e in (8,16,24) for s in (-1,1)]
    comparisons=[];numerical=[]
    def numeric_check(name,condition):
        numerical.append({'name':name,'passed':bool(condition)})
        if not condition:raise AssertionError(name)
    for model,v,k in [('fast_ridge',6,-1),('slow_face',5,1)]:
        selected=[r for r in rows if r['model']==model]
        assert [float(r['midpoint_x_km']) for r in selected]==expected_x
        for row in selected:
            x=Q(float(row['midpoint_x_km']));a80,g80=formula(v,k,x,80);a100,g100=formula(v,k,x,100)
            with localcontext() as ctx:
                ctx.prec=100
                action_error=D.from_float(float(row['path_action_s']))-a100
                grad_error=D.from_float(float(row['midpoint_gx_s_per_km']))-g100
                cross_action=a80-a100;cross_gradient=g80-g100
            suffix=model+'_'+str(x)
            numeric_check('action_consistency_'+suffix,abs(action_error)<D('5e-14'))
            numeric_check('gradient_consistency_'+suffix,abs(grad_error)<D('5e-12'))
            numeric_check('decimal_precision_consistency_'+suffix,abs(cross_action)<D('1e-65') and abs(cross_gradient)<D('1e-60'))
            numeric_check('zero_tangent_gradient_'+suffix,abs(float(row['midpoint_gy_s_per_km']))<1e-14 and float(row['midpoint_gz_s_per_km'])==0)
            comparisons.append({'recorded':row,'exact_binary64_x':str(x),'decimal_80_action':str(a80),'decimal_100_action':str(a100),
                                'decimal_80_gradient':str(g80),'decimal_100_gradient':str(g100),'quadrature_action_error_s':str(action_error),
                                'quadrature_midpoint_gradient_error_s_per_km':str(grad_error),
                                'x_zero_gradient_interpretation':'selected right-cell partial, not an ordinary derivative at the kink' if not x else 'ordinary smooth partial'})
    with (out/'face_segments.csv').open() as f:segments=list(csv.DictReader(f))
    assert [r['model'] for r in segments]==['fast_ridge','slow_face']
    for row,v,k in zip(segments,[6,5],[-1,1]):
        normal=-Q(k,2*v*v)
        for end in ('a','b'):
            numeric_check('face_endpoint_normal_'+row['model']+'_'+end,abs(Q(float(row[end+'_gx_s_per_km']))-normal)<Q(1,10**12))
        numeric_check('face_segment_action_'+row['model'],abs(Q(float(row['action_s']))-Q(1,v))<Q(1,10**13))
    summary={'status':'passed','exact_rational_checks':len(checks),'numerical_consistency_checks':len(numerical),
             'continuous_claim_basis':'Analytic derivation in README plus exact rational first-variation controls; binary64 quadrature is separately observed.',
             'path_evaluations':14,'direct_segment_evaluations':2,'trace_calls':0,'optimizer_calls':0,
             'comparisons':comparisons,'numerical_checks':numerical,
             'limitations':['The numerical consistency tolerances are control comparisons, not native stationarity or ray acceptance thresholds.',
                            'No native state, stopping criterion, optimizer or production source changed.',
                            'The false-box example is a declared directional component, not a reconstructed physical whole path.',
                            'Decimal agreement is not a rigorous interval enclosure; general trilinear variable-coefficient support is derived but not evaluated.']}
    with (out/'checks.json').open('x') as f:json.dump(summary,f,indent=2,allow_nan=False);f.write('\n')
    print('exact_rational_checks=%d numerical_consistency_checks=%d'%(len(checks),len(numerical)))

if __name__=='__main__':main()
