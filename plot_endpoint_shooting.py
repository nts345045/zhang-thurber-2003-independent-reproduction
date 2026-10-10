#!/usr/bin/env python3
"""Plot saved invented endpoint secants and original-node kernel comparisons."""
import hashlib
import json
import math
import os
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
os.environ.setdefault('MPLCONFIGDIR', str(ROOT / 'tmp/matplotlib'))
DATA = ROOT / 'data/development/loma_endpoint_shooting_controls_001'
EXPECTED = '0ca944a3fa240721e62b193b7db6361604137d40f34bccabca8566ddf5e61945'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    if sha(DATA / 'summary.json') != EXPECTED:
        raise ValueError('Frozen shooting summary changed')
    summary = json.loads((DATA / 'summary.json').read_text())
    pins = {str((DATA / 'summary.json').relative_to(ROOT)): EXPECTED}
    for name, expected in summary['output_sha256'].items():
        path = DATA / name
        if sha(path) != expected:
            raise ValueError('Frozen output changed: ' + name)
        pins[str(path.relative_to(ROOT))] = expected
    for name, expected in summary['input_sha256'].items():
        if sha(ROOT / name) != expected:
            raise ValueError('Frozen input changed: ' + name)
        pins[name] = expected
    pins[str(Path(__file__).resolve().relative_to(ROOT))] = sha(Path(__file__))
    rows = json.loads((DATA / 'perturbations.json').read_text())
    boundary = [r for r in rows if r['kind']=='endpoint' and r['inward_one_sided']]
    models = [r for r in rows if r['kind']=='model']
    if len(boundary)!=24 or len(models)!=80 or not all(r['same_value_candidates'] for r in boundary+models):
        raise ValueError('Unexpected saved comparison roster')
    colors = ['#2166ac', '#27845e', '#b65e20', '#874d9b']
    fixture_labels = ['Affine, bottom receiver', 'Mixed, bottom receiver',
                      'Mixed, both bottom: source', 'Mixed, both bottom: receiver']
    boundary_keys = [(False,False,1), (True,False,1), (True,True,0), (True,True,1)]
    fig, axes = plt.subplots(1, 2, figsize=(11.8, 5.8))
    fig.subplots_adjust(left=.08, right=.985, top=.79, bottom=.30, wspace=.36)
    fig.suptitle('Invented one-cell shooting candidates', fontsize=14, y=.975)
    fig.text(.5, .92, 'Saved finite differences; no native calculation or production correction',
             ha='center', fontsize=10)
    plotted_boundary, plotted_models = [], []
    for n, key in enumerate(boundary_keys):
        for setting in ['base','tight']:
            group = sorted([r for r in boundary if (r['mixed'],r['both_bottom'],r['side'])==key and
                            r['setting']==setting], key=lambda r:r['h'])
            x=[r['h'] for r in group]; y=[abs(r['difference_s_per_km']) for r in group]
            axes[0].loglog(x, y, color=colors[n], linestyle='-' if setting=='base' else '--',
                           marker='o' if setting=='base' else '+', markerfacecolor='none',
                           markersize=6 if setting=='base' else 8, linewidth=1.1, alpha=.85)
            plotted_boundary.append(dict(fixture=fixture_labels[n], setting=setting, h_km=x,
                                          absolute_secant_minus_momentum_s_per_km=y))
    reference_x=[1e-8,3e-7]
    coefficient=2*math.sqrt(2)/(3*6**1.5)
    reference_y=[coefficient*math.sqrt(h) for h in reference_x]
    axes[0].loglog(reference_x,reference_y,color='0.2',linestyle=':',linewidth=2.2,zorder=1)
    axes[0].text(1.5e-8,1.7e-5,r'$\sqrt{h}$ reference slope',fontsize=9,color='0.25')
    axes[0].axhline(3e-6,color='#ab3333',linestyle='-.',linewidth=1.)
    axes[0].text(1e-8,3.25e-6,r'Existing $3\times10^{-6}$ s/km limit',fontsize=9,color='#ab3333')
    axes[0].set_xlim(2.5e-9,1.4e-6); axes[0].set_ylim(2.3e-6,1e-4)
    axes[0].set_xticks([2**-28,2**-24,2**-20],labels=[r'$2^{-28}$',r'$2^{-24}$',r'$2^{-20}$'])
    axes[0].set_xlabel('Inward endpoint step h (km)')
    axes[0].set_ylabel('Absolute secant − momentum (s/km)')
    axes[0].set_title('A  Bottom-normal finite-step errors remain',loc='left',fontsize=10.5)
    family_labels=['Affine, one cap','Mixed, one cap','Mixed, both bottom']
    zero_count=0
    for n,key in enumerate([(False,False),(True,False),(True,True)]):
        for setting in ['base','tight']:
            group=[r for r in models if (r['mixed'],r['both_bottom'])==key and r['setting']==setting]
            hs=sorted(set(r['h'] for r in group))
            maxima=[]
            for h in hs:
                same=[r for r in group if r['h']==h]
                if sorted(r['node'] for r in same)!=list(range(8)):
                    raise ValueError('Original-node roster incomplete')
                errors=[abs(r['difference_s']) for r in same]
                maxima.append(max(errors)); zero_count += sum(e==0 for e in errors)
                for r,e in zip(same,errors):
                    plotted_models.append(dict(fixture=family_labels[n],setting=setting,node=r['node'],
                                                h=h,absolute_fd_minus_kernel_s=e,
                                                finite_difference_s=r['finite_difference_s'],kernel_s=r['kernel_s']))
                positive=[e for e in errors if e>0]
                axes[1].loglog([h]*len(positive),positive,linestyle='none',color=colors[n],
                               marker='.' if setting=='base' else '+',markersize=4,alpha=.3)
            axes[1].loglog(hs,maxima,color=colors[n],linestyle='-' if setting=='base' else '--',
                           marker='o' if setting=='base' else '+',markerfacecolor='none',
                           markersize=6 if setting=='base' else 8,linewidth=1.2)
    axes[1].set_xlim(6e-7,2.4e-5); axes[1].set_ylim(1e-16,1.8e-9)
    axes[1].set_xticks([2**-20,2**-16],labels=[r'$2^{-20}$',r'$2^{-16}$'])
    axes[1].set_xlabel('Log-slowness perturbation h (dimensionless)')
    axes[1].set_ylabel('Absolute central FD − original-node kernel (s)')
    axes[1].set_title('B  Smaller model steps reveal a numerical floor',loc='left',fontsize=10.5)
    axes[1].text(.04,.24,'Lines: maximum over eight original nodes\nFaint symbols: individual nodes',
                 transform=axes[1].transAxes,fontsize=8.5,va='top')
    for axis in axes:
        axis.grid(which='major',alpha=.2)
        axis.spines['top'].set_visible(False); axis.spines['right'].set_visible(False)
    axes[0].legend([Line2D([0],[0],color=colors[n],linewidth=2) for n in range(4)],fixture_labels,
                   loc='upper left',bbox_to_anchor=(-.015,-.22),fontsize=8.3,frameon=False,ncol=2)
    axes[1].legend([Line2D([0],[0],color=colors[n],linewidth=2) for n in range(3)],family_labels,
                   loc='upper left',bbox_to_anchor=(-.015,-.22),fontsize=8.3,frameon=False,ncol=2)
    fig.legend([Line2D([0],[0],color='0.2',marker='o',markerfacecolor='none'),
                Line2D([0],[0],color='0.2',linestyle='--',marker='+')],
               ['Base ODE settings','Tighter ODE settings (often overlapping)'],
               loc='lower center',bbox_to_anchor=(.5,.067),ncol=2,frameon=False,fontsize=9)
    fig.text(.5,.026,'All 24 bottom-normal discrepancies exceed the limit. '+str(zero_count)+
             ' zero node discrepancies are retained in metadata and omitted from log axes.',ha='center',fontsize=8.5)
    out=ROOT/'figures/diagnostics'; out.mkdir(parents=True,exist_ok=True)
    outputs={}
    for suffix in ['pdf','png']:
        path=out/('loma_endpoint_shooting.'+suffix)
        fig.savefig(path,dpi=200,metadata={'Creator':'plot_endpoint_shooting.py'} if suffix=='pdf' else None)
        outputs[str(path.relative_to(ROOT))]=sha(path)
    plt.close(fig)
    for name,expected in pins.items():
        if sha(ROOT/name)!=expected:
            raise ValueError('Input changed during plotting: '+name)
    metadata=dict(status='saved_table_plot_completed',command=sys.argv,matplotlib_version=matplotlib.__version__,
                  input_sha256=pins,figure_sha256=outputs,geometry='invented; native IDs do not apply',
                  boundary_curves=plotted_boundary,model_columns=plotted_models,
                  reference_slope=dict(formula='2*sqrt(2)/(3*6**1.5)*sqrt(h)',
                                       scope='Leading affine bottom-normal secant for g=1, vB=6',h_km=reference_x,error_s_per_km=reference_y),
                  zero_model_errors_not_displayed=zero_count,
                  limitations=['Saved numerical comparisons only; no shooting/ODE/root calculation.',
                               'All raw boundary discrepancies remain failures against 3e-6 s/km.',
                               'No derivative certificate, global-minimum claim, native run or production correction.'])
    path=out/'loma_endpoint_shooting.json'
    path.write_text(json.dumps(metadata,indent=2,allow_nan=False)+'\n')
    receipt=DATA/'plot_receipt.json'
    if receipt.exists():
        raise ValueError('Plot receipt already exists; preserve previous publication')
    receipt.write_text(json.dumps(dict(metadata_path=str(path.relative_to(ROOT)),metadata_sha256=sha(path),
                                      figure_sha256=outputs,plot_source_sha256=sha(Path(__file__))),indent=2)+'\n')
    print(json.dumps(dict(figures=outputs,metadata_sha256=sha(path)),indent=2))


if __name__=='__main__':
    main()
