#!/usr/bin/env python3
"""Invented controls for local normalized correlation and the dt.cc lag sign.

No authoritative waveform is read and no differential observation is created.
"""
import argparse
import hashlib
import inspect
import json
from pathlib import Path
import shutil
import sys

import numpy as np
import obspy
import scipy
from obspy.signal.cross_correlation import correlate_template

ROOT = Path(__file__).resolve().parents[1]


def direct_definition(search, template):
    """Direct local-mean Pearson coefficient; NaN denotes zero variance."""
    template = template - template.mean()
    output = []
    for start in range(len(search) - len(template) + 1):
        window = search[start:start + len(template)]
        window = window - window.mean()
        denominator = np.linalg.norm(template) * np.linalg.norm(window)
        output.append(np.dot(template, window) / denominator if denominator else np.nan)
    return np.array(output)


def cc_with_stable_scale(search, template):
    """Affine scaling preserves local NCC and avoids large-offset cancellation."""
    values = []
    for array in (search, template):
        array = np.asarray(array, dtype=np.float64)
        if array.ndim != 1 or not np.isfinite(array).all():
            raise ValueError('Require finite, one-dimensional samples')
        centered = array - array.mean()
        scale = np.max(np.abs(centered))
        values.append(centered / scale if scale else centered)
    return correlate_template(values[0], values[1], mode='valid',
                              normalize='full', demean=True, method='direct')


def differential_time(catalog_i_minus_j, template_start_from_pick,
                      search_start_from_pick, peak_index, sample_rate):
    delay_j_minus_i = search_start_from_pick + peak_index / sample_rate - template_start_from_pick
    return catalog_i_minus_j - delay_j_minus_i, delay_j_minus_i


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    out = (ROOT / args.output).resolve()
    out.relative_to(ROOT)
    out.mkdir(parents=True, exist_ok=False)
    checks = []

    def check(name, condition, **evidence):
        checks.append(dict(name=name, passed=bool(condition), **evidence))

    rng = np.random.default_rng(2303)
    template = rng.normal(size=256)
    search = rng.normal(size=306)
    search[31:31 + len(template)] = 3.7 * template + 11.0
    reference = direct_definition(search, template)
    baseline = cc_with_stable_scale(search, template)
    error = float(np.max(np.abs(reference - baseline)))
    check('local_definition', error < 2e-13, maximum_coefficient_error=error)
    check('known_peak', int(np.argmax(baseline)) == 31 and abs(baseline[31] - 1) < 2e-13)
    for label, gain, offset in [('small', 1e-12, 0.), ('large', 1e12, 0.),
                                ('offset', 1., 1e5), ('gain_and_offset', 7., -500.)]:
        observed = cc_with_stable_scale(search * gain + offset, template)
        expected = direct_definition(search * gain + offset, template)
        error = float(np.max(np.abs(observed - expected)))
        check('local_definition_' + label, error < 2e-12, maximum_coefficient_error=error)
        # The large DC offset rounds individual binary64 samples; compare with
        # that actual represented input, then record its departure separately.
        check('same_peak_' + label, int(np.argmax(observed)) == 31,
              maximum_change_from_untransformed=float(np.max(np.abs(observed - baseline))))
    inverse = cc_with_stable_scale(search, -template)
    check('signed_polarity', np.max(np.abs(inverse + baseline)) < 2e-13 and inverse[31] < -.999999)
    # A global comparison mean alone is not the local-window normalization.
    globally_centered = search - search.mean()
    a = template - template.mean()
    wrong = np.array([np.dot(a, globally_centered[k:k + len(a)]) /
                      (np.linalg.norm(a) * np.linalg.norm(globally_centered[k:k + len(a)]))
                      for k in range(len(search) - len(a) + 1)])
    check('global_only_counterexample', np.max(np.abs(wrong - reference)) > .001,
          maximum_global_only_error=float(np.max(np.abs(wrong - reference))))
    constant = cc_with_stable_scale(np.ones(306), template)
    check('constant_data_is_degenerate', np.all(constant == 0) and
          np.isnan(direct_definition(np.ones(306), template)).all())
    check('constant_template_is_degenerate', np.all(cc_with_stable_scale(search, np.ones(256)) == 0))
    # Peak index counts valid-window starts. Actual sample-start offsets are
    # included; a centered index alone is wrong when pick grids differ.
    catalog = 1.25
    for rate in (50., 100., 200.):
        for lag_samples in (-12, 0, 17):
            half_width = 25
            peak = half_width + lag_samples
            for offset_i, offset_j in ((0., 0.), (.001, -.002)):
                start_i = -.5 + offset_i
                start_j = -.5 - half_width / rate + offset_j
                dt, delay = differential_time(catalog, start_i, start_j, peak, rate)
                expected_delay = lag_samples / rate + offset_j - offset_i
                check('lag_sign_{}_{}_{}_{}'.format(rate, lag_samples, offset_i, offset_j),
                      abs(delay - expected_delay) < 2e-15 and
                      abs(dt - (catalog - expected_delay)) < 2e-15,
                      delay_j_minus_i_s=delay, dt_i_minus_j_s=dt)
    # Same invented feature at two known travel times, with deliberately
    # biased picks. Correlation must remove the differential pick error.
    true_i, true_j, pick_i, pick_j = 4.0, 5.0, 4.10, 4.94
    delta = (true_j - pick_j) - (true_i - pick_i)
    dt, unused = differential_time(pick_i - pick_j, -.5, -.75, 25 + round(delta * 100), 100)
    check('independent_known_travel_time_difference', abs(dt - (true_i - true_j)) < 2e-15)
    # Boundary and ambiguous peaks are diagnostic facts, not accepted delays.
    boundary = rng.normal(size=306); boundary[:256] = template
    check('boundary_peak_is_visible', int(np.argmax(cc_with_stable_scale(boundary, template))) == 0)
    periodic = np.tile(np.array([1., -1., 2., -2.]), 77)
    tied = cc_with_stable_scale(periodic, periodic[:256])
    check('repeated_peak_ambiguity_is_visible', np.count_nonzero(np.abs(tied - tied.max()) < 1e-12) > 1)
    for invalid in (np.array([1., np.nan]), np.array([[1., 2.]])):
        rejected = False
        try:
            cc_with_stable_scale(invalid, template)
        except ValueError:
            rejected = True
        check('invalid_sample_input_' + str(len(checks)), rejected)
    np.savez(out / 'invented_arrays.npz', template=template, search=search,
             normalized_correlation=baseline, direct_reference=reference)
    shutil.copyfile(str(Path(__file__).resolve()), str(out / Path(__file__).name))
    source = Path(inspect.getfile(correlate_template))
    result = dict(status='passed' if all(c['passed'] for c in checks) else 'failed',
                  scope='Invented normalization and lag-sign controls; no real measurements or acceptance thresholds',
                  checks=checks, versions=dict(python=sys.version.split()[0], numpy=np.__version__,
                                             scipy=scipy.__version__, obspy=obspy.__version__),
                  obspy_cross_correlation_source_sha256=sha(source),
                  source_sha256=sha(Path(__file__).resolve()),
                  output_sha256={p.name: sha(p) for p in out.iterdir() if p.is_file()},
                  limitations=['These controls do not specify waveform filtering, tapering, interpolation, quality acceptance or timing uncertainty.',
                               'A package zero for constant data is an undefined normalized coefficient, not a usable timing observation.',
                               'Signed correlation retains polarity; absolute correlation must not silently select a reversed-polarity peak.'])
    (out / 'summary.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps(dict(status=result['status'], checks=len(checks), failed=[c for c in checks if not c['passed']]), indent=2))
    if result['status'] != 'passed':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
