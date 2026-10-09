#!/usr/bin/env python3
"""Plot saved C++ model output; no simulated values are constructed here."""
import argparse
import os
os.environ.setdefault('MPLCONFIGDIR', os.path.abspath('tmp/matplotlib'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

DATA = Path('data/synthetic')
OUT = Path('figures')
OUT.mkdir(exist_ok=True)
plt.rcParams.update({'font.size': 9, 'axes.labelsize': 9, 'savefig.dpi': 180})


def load(name):
    return np.genfromtxt(DATA / name, delimiter=',', names=True)


def save(fig, name):
    fig.savefig(OUT / (name + '.pdf'), bbox_inches='tight')
    fig.savefig(OUT / (name + '.png'), bbox_inches='tight')
    plt.close(fig)


def field(ax, d, key, cmap, vmin, vmax):
    x, y = np.unique(d['x']), np.unique(d['y'])
    values = d[key].reshape(len(y), len(x))
    im = ax.pcolormesh(x, y, values, cmap=cmap, vmin=vmin, vmax=vmax,
                       shading='auto', rasterized=True)
    ax.set_xlabel('Across strike x (km)')
    ax.set_ylabel('Along strike y (km)')
    return im


def fig1():
    d = load('truth_slice.csv')
    fig, ax = plt.subplots(figsize=(5.5, 5))
    im = field(ax, d, 'v', 'viridis', 4, 6)
    fig.colorbar(im, ax=ax, label='P velocity (km/s)')
    ax.set_title('Figure 1: independently generated true model\nz = 7 km; depth-independent profile')
    save(fig, 'figure01')


def fig2():
    e, s, g = load('truth_events.csv'), load('stations.csv'), load('initial_grid.csv')
    fig, ax = plt.subplots(figsize=(6, 6))
    q = g[g['z'] == 0]
    ax.scatter(q['x'], q['y'], marker='+', color='0.65', label='Published inversion grid')
    ax.scatter(s['x'], s['y'], marker='^', facecolors='none', edgecolors='C1', label='Independent stations')
    ax.scatter(e['x'], e['y'], s=9, color='k', label='Independent true sources')
    ax.axvline(0, color='0.5', lw=0.7)
    ax.set(xlabel='Across strike x (km)', ylabel='Along strike y (km)',
           title='Figure 2: partial reconstruction\nIndependently generated geometry, not Loma Prieta observations')
    ax.legend(fontsize=8, loc='lower left')
    save(fig, 'figure02')


def fig3(panel=None):
    specifications = [('a', 'standard', 'v', 'Standard tomography', 4, 6, 'viridis'),
                      ('b', 'dd', 'v', 'Double-difference tomography', 4, 6, 'viridis'),
                      ('c', 'dd', 'error', 'True minus DD velocity', -1, 1, 'RdBu_r'),
                      ('d', 'standard', 'error', 'True minus standard velocity', -1, 1, 'RdBu_r')]
    for label, mode, key, title, vmin, vmax, cmap in specifications:
        if panel is not None and label != panel:
            continue
        d, e = load(mode + '_slices.csv'), load(mode + '_events.csv')
        if key == 'error':
            d['error'] *= -1  # Saved column is recovered minus true; manuscript prose uses the reverse.
        depths = np.unique(d['z'])
        fig, grid_axes = plt.subplots(2, 3, figsize=(9, 8), sharey=True)
        axes = grid_axes.flat
        grid_axes[1, 2].set_visible(False)
        for i, (ax, z) in enumerate(zip(axes, depths)):
            im = field(ax, d[d['z'] == z], key, cmap, vmin, vmax)
            lower = -np.inf if i == 0 else (z + depths[i - 1]) / 2
            upper = np.inf if i == len(depths)-1 else (z + depths[i + 1]) / 2
            mask = (e['z'] >= lower) & (e['z'] < upper)
            ax.scatter(e['x'][mask], e['y'][mask], color='k', s=2, alpha=0.5)
            ax.set_title('z = {:g} km'.format(z))
            if i:
                ax.set_ylabel('')
        fig.subplots_adjust(left=0.1, right=0.9, top=0.87, bottom=0.09, wspace=0.15, hspace=0.32)
        cax = fig.add_axes([0.93, 0.2, 0.015, 0.55])
        fig.colorbar(im, cax=cax, label='Velocity{} (km/s)'.format(' error' if key == 'error' else ''))
        fig.suptitle('Figure 3{}: {}\nPartial reproduction: independently generated geometry and explicit numerical substitutions'.format(label, title))
        save(fig, 'figure03' + label)


def validation():
    d = np.genfromtxt('data/validation_ray.csv', delimiter=',', names=True)
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.6))
    for ax, key, name in zip(axes, ['y', 'z'], ['Along strike y (km)', 'Depth (km)']):
        ax.plot(d['x'], d[key], label='Computed Fermat ray')
        ax.plot([d['x'][0], d['x'][-1]], [d[key][0], d[key][-1]], '--', label='Straight endpoint connection')
        ax.set(xlabel='Across strike x (km)', ylabel=name)
        ax.axvspan(1, 5, color='0.9', zorder=-1)
    axes[1].invert_yaxis()
    axes[0].legend(fontsize=8)
    fig.suptitle('Numerical validation: bending through the specified sandwich model')
    fig.tight_layout()
    save(fig, 'validation_ray')


def convergence():
    fig, axes = plt.subplots(1, 3, figsize=(9, 3.5))
    for mode in ['standard', 'dd']:
        d = load(mode + '_history.csv')
        for ax, key, title in zip(axes, ['absolute_rms', 'catalog_rms', 'precise_rms'],
                                 ['Absolute arrivals', 'Catalog differences', 'Precise differences']):
            ax.semilogy(d['iteration'], d[key], '.-', label=mode)
            ax.set(xlabel='Nonlinear iteration (before update)', ylabel='Unweighted RMS residual (s)', title=title)
    for ax in axes:
        ax.tick_params(labelsize=10)
        ax.xaxis.label.set_size(10)
        ax.yaxis.label.set_size(10)
        ax.title.set_size(11)
    axes[0].legend(fontsize=10)
    fig.tight_layout()
    save(fig, 'convergence')


def locations():
    truth, initial = load('truth_events.csv'), load('initial_events.csv')
    fig, axes = plt.subplots(1, 3, figsize=(9, 3.5))
    for mode in ['initial', 'loc1d', 'loc3d', 'standard', 'dd']:
        d = initial if mode == 'initial' else load(mode + '_events.csv')
        for ax, key in zip(axes, ['x', 'y', 'z']):
            errors = np.sort(np.abs(d[key] - truth[key]))
            ax.plot(errors, np.arange(1, len(errors) + 1) / len(errors), label=mode)
            ax.set(xlabel='Absolute {} error (km)'.format(key), ylabel='Empirical cumulative fraction')
    for ax in axes:
        ax.tick_params(labelsize=10)
        ax.xaxis.label.set_size(10)
        ax.yaxis.label.set_size(10)
    axes[-1].legend(fontsize=10)
    fig.suptitle('Independent synthetic location errors (Table 1 methodology comparison)')
    fig.tight_layout(rect=[0, 0, 1, 0.9])
    save(fig, 'location_errors')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--figure', choices=['1', '2', '3', '3a', '3b', '3c', '3d', 'validation', 'convergence', 'locations', 'all'], default='all')
    args = parser.parse_args()
    tasks = {'1': fig1, '2': fig2, '3': fig3, 'validation': validation,
             'convergence': convergence, 'locations': locations}
    if args.figure in ['3a', '3b', '3c', '3d']:
        fig3(args.figure[-1])
    for key, task in tasks.items():
        if args.figure in [key, 'all']:
            task()
