#!/usr/bin/env python3
"""One identified cross-spectral pilot with explicit assumptions; no solver input."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import shutil
import sys

import numpy as np
import obspy

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / 'data/authoritative/waveforms/pilot_001'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def estimate(cross, auto_i, auto_j, frequencies, width):
    kernel = np.ones(width) / width
    c = np.convolve(cross, kernel, mode='same')
    a = np.convolve(auto_i, kernel, mode='same')
    b = np.convolve(auto_j, kernel, mode='same')
    band = (frequencies >= 2) & (frequencies <= 10)
    frequency = frequencies[band]
    coherence = abs(c[band]) ** 2 / (a[band] * b[band])
    if not np.isfinite(coherence).all() or np.any(coherence < 0) or np.any(coherence > 1 + 1e-12):
        raise ValueError('Invalid squared coherence')
    phase = np.unwrap(np.angle(c[band]))
    good = coherence > 0.9
    passed = int(good.sum()) * 2 >= len(good)
    delay = slope = intercept = rms = None
    if good.sum() >= 2:
        design = np.column_stack((frequency[good], np.ones(int(good.sum()))))
        slope, intercept = np.linalg.lstsq(design, phase[good], rcond=None)[0]
        delay = -float(slope) / (2 * np.pi)
        rms = float(np.sqrt(np.mean((phase[good] - design @ np.array([slope, intercept])) ** 2)))
    return dict(coherence_pass=bool(passed), passing_bins=int(good.sum()), evaluation_bins=len(good),
        residual_feature_delay_j_minus_i_s=delay, phase_fit_slope_rad_per_hz=None if slope is None else float(slope),
        phase_fit_intercept_rad=None if intercept is None else float(intercept), phase_fit_rms_rad=rms,
        mean_squared_coherence=float(coherence.mean()), minimum_squared_coherence=float(coherence.min()),
        maximum_squared_coherence=float(coherence.max())), list(zip(frequency, coherence, phase, good))


def controls(frequencies):
    rows = []
    for width in (3, 5, 7):
        for delay in (-0.2, -0.037, 0., 0.037, 0.2):
            c = np.exp(-2j * np.pi * frequencies * delay)
            result, _ = estimate(c, np.ones(len(c)), np.ones(len(c)), frequencies, width)
            error = (abs(result['residual_feature_delay_j_minus_i_s'] - delay)
                     if result['residual_feature_delay_j_minus_i_s'] is not None else None)
            # Large delays decorrelate a broad smoothing kernel. Preserve that
            # expected effect; require exact slope only when coherent bins exist.
            if result['residual_feature_delay_j_minus_i_s'] is not None and error > 1e-12:
                raise ValueError('Analytic phase-delay sign/fit control failed')
            rows.append(dict(kind='invented constant-power analytic delayed cross spectrum', width=width,
                input_delay_j_minus_i_s=delay, recovered_delay_s=result['residual_feature_delay_j_minus_i_s'],
                coherence_pass=result['coherence_pass'], delay_error_s=error))
    sample = np.arange(256) / 100.
    wave = np.exp(-((sample-1.1)/0.3)**2) * np.cos(2*np.pi*5*sample)
    x = np.fft.rfft((wave-wave.mean()) * np.hanning(256))
    result, _ = estimate(np.conj(x)*x, abs(x)**2, abs(x)**2, frequencies, 5)
    if not result['coherence_pass'] or abs(result['residual_feature_delay_j_minus_i_s']) > 1e-12:
        raise ValueError('Identical finite-window control failed')
    rows.append(dict(kind='invented identical demeaned Hann-window signal', coherence_pass=True,
        recovered_delay_s=result['residual_feature_delay_j_minus_i_s']))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    out = (ROOT / args.output).resolve()
    out.relative_to(ROOT)
    out.mkdir(parents=True)
    review = json.loads((PILOT/'review.json').read_text())
    for name, expected in review['output_sha256'].items():
        if sha(PILOT/name) != expected:
            raise ValueError('Pinned waveform pilot changed: '+name)
    context = json.loads((PILOT/'partner_probe_identity.json').read_text())
    pair = context['existing_differential_pair']['original_observation']
    inputs = {str(p.relative_to(ROOT)): sha(p) for p in PILOT.iterdir() if p.is_file()}
    specification = ROOT/'data/development/waveform_correlation_specification/README.md'
    inputs[str(specification.relative_to(ROOT))] = sha(specification)
    records = {}
    for prefix in ('', 'partner_'):
        native = json.loads((PILOT/(prefix+'probe_identity.json')).read_text())['original_observation']
        stream = obspy.read(str(PILOT/(prefix+'waveform.mseed')), format='MSEED')
        if len(stream) != 1 or stream[0].id != native['channel_seed_id'] or stream[0].stats.sampling_rate != 100:
            raise ValueError('Native waveform identity/rate mismatch')
        records[native['pick_i_resource_id']] = (native, stream[0])
    if set(records) != {pair['pick_i_resource_id'], pair['pick_j_resource_id']}:
        raise ValueError('Waveforms do not match both existing differential-pick identities')
    identity = dict(pair)
    identity['local_diagnostic_id'] = 'waveform_correlation_pilot:existing_observation_15108'
    identity['derived_provider_resource_id'] = ''
    frequency = np.fft.rfftfreq(256, 0.01)
    checks = controls(frequency)
    spectra, results, display_windows = [], [], {}
    for before in (0.25, 0.5, 0.75):
        waves = []
        for side in ('i', 'j'):
            native, trace = records[pair['pick_'+side+'_resource_id']]
            start = obspy.UTCDateTime(native['pick_i_time_utc']) - before
            offset = float(start-trace.stats.starttime)*100
            index = round(offset)
            if abs(offset-index) > 1e-8 or index < 0 or index+256 > len(trace.data):
                raise ValueError('Window is not a complete native-grid 256-sample window')
            samples = trace.data[index:index+256].astype(float)
            samples -= samples.mean()
            waves.append(samples)
        x, y = [np.fft.rfft(wave*np.hanning(256)) for wave in waves]
        if before == 0.5:
            display_windows = dict(i=waves[0], j=waves[1])
        for width in (3, 5, 7):
            result, bins = estimate(np.conj(x)*y, abs(x)**2, abs(y)**2, frequency, width)
            result.update(window_before_pick_s=before, smoothing_bins=width, primary=before == 0.5 and width == 5)
            result['candidate_waveform_difference_i_minus_j_s'] = (
                float(pair['value'])-result['residual_feature_delay_j_minus_i_s']
                if result['coherence_pass'] and result['residual_feature_delay_j_minus_i_s'] is not None else None)
            results.append(result)
            for f, coherence, phase, good in bins:
                spectra.append(dict(identity, window_before_pick_s=before, smoothing_bins=width,
                    frequency_hz=float(f), squared_coherence=float(coherence), unwrapped_phase_rad=float(phase),
                    phase_fit_included=int(good)))
    with (out/'identified_spectra.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(spectra[0]),lineterminator='\n')
        writer.writeheader();writer.writerows(spectra)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    primary = next(r for r in results if r['primary'])
    selected = [r for r in spectra if r['window_before_pick_s']==0.5 and r['smoothing_bins']==5]
    fig, axes = plt.subplots(3,1,figsize=(7.4,7.4),constrained_layout=True)
    t=np.arange(256)/100.-0.5
    for side,color in [('i','tab:blue'),('j','tab:orange')]:
        wave=display_windows[side]
        axes[0].plot(t,wave/max(abs(wave)),color=color,label='Event '+pair['event_'+side+'_resource_id'].split('/')[-1])
    axes[0].axvline(0,color='0.6',lw=0.7);axes[0].set(xlabel='Time relative to catalog P pick (s)',ylabel='Demeaned normalized counts')
    axes[0].legend(frameon=False)
    f=np.array([r['frequency_hz'] for r in selected])
    axes[1].plot(f,[r['squared_coherence'] for r in selected],'o-');axes[1].axhline(0.9,color='0.4',ls='--')
    axes[1].set(xlabel='Frequency (Hz)',ylabel='Squared coherence',ylim=(0,1.03))
    axes[2].plot(f,[r['unwrapped_phase_rad'] for r in selected],'o-',label='All band bins')
    if primary['phase_fit_slope_rad_per_hz'] is not None:
        axes[2].plot(f,primary['phase_fit_slope_rad_per_hz']*f+primary['phase_fit_intercept_rad'],'--',label='Fit to coherence >0.9')
    axes[2].set(xlabel='Frequency (Hz)',ylabel='Unwrapped cross phase (rad)');axes[2].legend(frameon=False)
    fig.suptitle('One-pair cross-spectral diagnostic: '+('coherence criterion passed' if primary['coherence_pass'] else 'coherence criterion failed'))
    fig.savefig(out/'diagnostic.png',dpi=160);fig.savefig(out/'diagnostic.pdf');plt.close(fig)
    (out/'figure_identifiers.json').write_text(json.dumps(dict(native_pair=identity,input_sha256=inputs),indent=2)+'\n')
    shutil.copyfile(str(Path(__file__).resolve()),str(out/'check_waveform_correlation.py'))
    shutil.copyfile(str(specification),str(out/'specification.md'))
    for name, expected in inputs.items():
        if sha(ROOT/name)!=expected:raise ValueError('Pilot/specification changed during diagnostic')
    summary=dict(scope='Independent one-pair signal-processing diagnostic; no inversion observation written',
        native_pair=identity,primary=primary,all_variants=results,controls=checks,input_sha256=inputs,
        versions=dict(python=sys.version.split()[0],numpy=np.__version__,obspy=obspy.__version__,matplotlib=matplotlib.__version__),
        limitations=['Taper/window/smoothing/phase-fit choices are explicit independent assumptions.',
            'Frequency bins are smoothed and correlated; no formal delay uncertainty or millisecond precision is claimed.',
            'Nearest-adjacent phase unwrapping leaves cycle ambiguity; a diagnostic candidate is not a validated inversion observation.',
            'All sensitivity variants and any rejected pair are preserved without changing the primary selection.'])
    summary['output_sha256']={p.name:sha(p) for p in out.iterdir() if p.is_file()}
    (out/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    print(json.dumps(primary,indent=2))


if __name__=='__main__':main()
