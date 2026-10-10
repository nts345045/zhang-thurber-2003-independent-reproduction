#!/usr/bin/env python3
"""Invented extraction/CC/screen controls; never reads real waveform records."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

import numpy as np
import obspy
import scipy

import normalized_waveform_cc as method

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    out = (ROOT / args.output).resolve()
    out.relative_to(ROOT)
    out.mkdir(parents=True, exist_ok=False)
    checks, saved = [], {}

    def check(name, passed, **detail):
        checks.append(dict(name=name, passed=bool(passed), **detail))

    rng = np.random.default_rng(230310)
    first = rng.normal(size=500)
    template = first[50:306].copy()
    for lag in (-17, 0, 16):
        second = rng.normal(size=500)
        second[50 + lag:306 + lag] = template
        for offset_i, offset_j in ((0, 0), (3_000_000, -2_000_000)):
            r = method.measure(first, -1_000_000_000 + offset_i,
                               second, -1_000_000_000 + offset_j, -.84)
            expected_delay = lag / 100 + (offset_j - offset_i) / 1e9
            check('known_delay_{}_{}_{}'.format(lag, offset_i, offset_j),
                  r['status'] == 'accepted_discrete_measurement'
                  and abs(r['delay_j_minus_i_s'] - expected_delay) < 1e-15
                  and abs(r['dt_cc_i_minus_j_s'] - (-.84 - expected_delay)) < 1e-15
                  and r['passing_bins'] == 20,
                  status=r['status'], expected_delay_s=expected_delay)
            # Direct Pearson coefficients establish the local normalization
            # independently of ObsPy's sliding-sum implementation.
            a = first[50:306] - first[50:306].mean()
            start = r['search_first_sample_index']
            direct = []
            for k in range(len(r['coefficients'])):
                b = second[start + k:start + k + 256]
                b = b - b.mean()
                direct.append(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
            error = float(np.max(abs(r['coefficients'] - direct)))
            check('direct_local_{}_{}_{}'.format(lag, offset_i, offset_j),
                  error < 2e-13, maximum_error=error)
            saved['cc_{}_{}_{}'.format(lag, offset_i, offset_j)] = r['coefficients']
        if lag == 16:
            check('biased_picks_recover_known_true_difference',
                  abs(method.measure(first, -1_000_000_000, second, -1_000_000_000,
                                     4.10 - 4.94)['dt_cc_i_minus_j_s'] + 1) < 1e-15)
            baseline_second = second.copy()
    baseline = method.measure(first, -1_000_000_000, baseline_second, -1_000_000_000, -.84)
    for gain, offset in ((1e-12, 0), (1e12, 0), (7, 1e5)):
        r = method.measure(first, -1_000_000_000,
                           baseline_second * gain + offset, -1_000_000_000, -.84)
        check('gain_offset_{}_{}'.format(gain, offset),
              r['status'] == baseline['status'] and r['peak_index'] == baseline['peak_index']
              and r['dt_cc_i_minus_j_s'] == baseline['dt_cc_i_minus_j_s'])
    for target, start, expected in ((-500_000_000, -995_000_000, 49),
                                    (-500_000_000, -994_999_999, 49),
                                    (-500_000_000, -995_000_001, 50),
                                    (-500_000_000, -495_000_000, -1)):
        check('nearest_sample_{}_{}'.format(target, start),
              method.nearest_sample(target, start) == expected)
    for which in ('template', 'search'):
        x = first[:305] if which == 'template' else first
        y = baseline_second[:330] if which == 'search' else baseline_second
        check('incomplete_entire_support_' + which,
              method.measure(x, -1_000_000_000, y, -1_000_000_000, -.84)['status']
              == 'incomplete_declared_support')
    check('unsupported_rate_retained', method.measure(first, -1_000_000_000,
          baseline_second, -1_000_000_000, -.84, second_rate=50)['status'] == 'unsupported_sample_rate')
    check('constant_template_rejected', method.measure(np.ones(500), -1_000_000_000,
          baseline_second, -1_000_000_000, -.84)['status'] == 'constant_template')
    check('constant_search_rejected', method.measure(first, -1_000_000_000,
          np.ones(500), -1_000_000_000, -.84)['status'] == 'constant_search_windows')
    invalid = first.copy(); invalid[100] = np.nan
    check('nonfinite_rejected', method.measure(invalid, -1_000_000_000,
          baseline_second, -1_000_000_000, -.84)['status'] == 'nonfinite_samples')
    masked = np.ma.array(first, mask=np.zeros(500, dtype=bool)); masked.mask[100] = True
    check('masked_gap_rejected', method.measure(masked, -1_000_000_000,
          baseline_second, -1_000_000_000, -.84)['status'] == 'masked_samples')
    ramp = np.arange(500, dtype=float)
    check('reversed_polarity_not_absolute_peak', method.measure(ramp, -1_000_000_000,
          -ramp, -1_000_000_000, -.84)['status'] == 'nonpositive_peak')
    for k in (25, 75):
        edge = rng.normal(size=500); edge[k:k + 256] = template
        check('boundary_peak_' + str(k), method.measure(first, -1_000_000_000,
              edge, -1_000_000_000, -.84)['status'] == 'boundary_peak')
    periodic = np.tile(np.array([1., -1., 2., -2.]), 125)
    check('multiple_peaks_rejected', method.measure(periodic, -1_000_000_000,
          periodic, -1_000_000_000, -.84)['status'] == 'ambiguous_peak')
    noise = rng.normal(size=256)
    screen = method.spectral_screen(template, noise)
    check('unrelated_screen_fails', screen['coherence_resolved'] and not screen['coherence_pass'])
    constant_screen = method.spectral_screen(np.zeros(256), np.zeros(256))
    check('zero_power_screen_unresolved', not constant_screen['coherence_resolved'])
    # Independent analytic smoothing identity; no real spectra are involved.
    frequencies = np.fft.rfftfreq(256, .01)
    band = (frequencies >= 2) & (frequencies <= 10)
    for delay in (.05, .1, .25):
        cross = np.exp(-2j * np.pi * frequencies * delay)
        numerical = abs(np.convolve(cross, np.ones(5) / 5, mode='same')[band]) ** 2
        theta = np.pi * delay * (100 / 256)
        exact = (np.sin(5 * theta) / (5 * np.sin(theta))) ** 2
        check('spectral_delay_smoothing_' + str(delay),
              np.max(abs(numerical - exact)) < 1e-14,
              expected_squared_coherence=float(exact))
    check('sample_spacing_not_sigma', baseline['sample_spacing_s'] == .01
          and baseline['formal_timing_uncertainty_s'] is None)
    # A large sample outside the selected window must not corrupt that window's
    # local variance. Rolling sum(x*x)-sum(x)**2/N loses this property.
    dynamic_rng = np.random.default_rng(90213)
    dynamic_i = dynamic_rng.integers(-2, 3, 500, dtype=np.int32)
    dynamic_j = dynamic_rng.integers(-2, 3, 500, dtype=np.int32)
    dynamic_j[50:306] = dynamic_i[50:306]
    for spike in (100_000, 10_000_000, 100_000_000, 2_000_000_000):
        dynamic_j[25] = spike
        r = method.measure(dynamic_i, -1_000_000_000, dynamic_j, -1_000_000_000, -.84)
        x = dynamic_i[50:306].astype(float); x -= x.mean()
        direct = []
        for k in range(51):
            y = dynamic_j[25 + k:281 + k].astype(float); y -= y.mean()
            direct.append(np.dot(x, y) / (np.linalg.norm(x) * np.linalg.norm(y)))
        error = float(np.max(abs(r['coefficients'] - direct)))
        check('local_variance_with_margin_spike_' + str(spike),
              r['status'] == 'accepted_discrete_measurement' and r['peak_index'] == 25
              and r['delay_j_minus_i_s'] == 0 and error < 2e-13,
              status=r['status'], maximum_coefficient_error=error)
    saved.update(dynamic_i=dynamic_i, dynamic_j=dynamic_j,
                 dynamic_range_coefficients=r['coefficients'])
    saved.update(first=first, second=baseline_second)
    np.savez(out / 'invented_arrays.npz', **saved)
    sources = [Path(__file__).resolve(), ROOT / 'diagnostics/normalized_waveform_cc.py',
               ROOT / 'data/development/normalized_correlation_specification/README.md']
    for p in sources:
        shutil.copyfile(str(p), str(out / p.name))
    result = dict(status='passed' if all(c['passed'] for c in checks) else 'failed',
                  scope=__doc__, checks=checks,
                  versions=dict(python=sys.version.split()[0], numpy=np.__version__,
                                scipy=scipy.__version__, obspy=obspy.__version__),
                  source_sha256={str(p.relative_to(ROOT)): sha(p) for p in sources},
                  output_sha256={p.name: sha(p) for p in out.iterdir() if p.is_file()},
                  limitations=['Invented arrays only; authoritative decoding, native joins and export are separate.',
                               'Discrete lag and empirical coherence screen do not establish a timing uncertainty.'])
    (out / 'summary.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps(dict(status=result['status'], checks=len(checks), failed=[c for c in checks if not c['passed']]), indent=2))
    if result['status'] != 'passed':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
