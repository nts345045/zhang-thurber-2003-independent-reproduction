"""Discrete normalized delay and post-alignment coherence; no solver import.

The fixed prospective method is documented in
data/development/normalized_correlation_specification/README.md.
Input sample times are integer nanoseconds relative to their own catalog pick.
The caller must verify authoritative trace identities, rates and continuity.
"""
import math

import numpy as np

RATE = 100
STEP_NS = 10_000_000
N = 256
PRE_NS = 500_000_000
SHIFT_NS = 250_000_000
TIE_TOLERANCE = 64 * np.finfo(np.float64).eps


def nearest_sample(target_ns, start_ns):
    """Nearest native sample index, with earlier sample at an exact tie."""
    index, remainder = divmod(target_ns - start_ns, STEP_NS)
    return index + int(2 * remainder > STEP_NS)


def centered_scale(samples):
    values = samples.astype(np.float64)
    values -= values.mean()
    scale = np.max(np.abs(values))
    return values / scale if scale else values


def local_coefficients(search, template):
    """Direct Pearson coefficients without subtracting large rolling moments."""
    template = centered_scale(template)
    windows = np.lib.stride_tricks.sliding_window_view(search, len(template)).astype(np.float64)
    windows -= windows.mean(axis=1, keepdims=True)
    scales = np.max(abs(windows), axis=1)
    defined = scales > 0
    windows[defined] /= scales[defined, None]
    coefficients = np.full(len(windows), np.nan)
    denominator = np.linalg.norm(windows[defined], axis=1) * np.linalg.norm(template)
    coefficients[defined] = (windows[defined] @ template) / denominator
    return coefficients, defined


def spectral_screen(first, second):
    """Same-length aligned arrays; no delay fitted from their spectrum."""
    taper = np.hanning(N)
    x, y = [np.fft.rfft(centered_scale(v) * taper) for v in (first, second)]
    kernel = np.ones(5) / 5
    cross = np.convolve(np.conj(x) * y, kernel, mode='same')
    power_i = np.convolve(abs(x) ** 2, kernel, mode='same')
    power_j = np.convolve(abs(y) ** 2, kernel, mode='same')
    frequency = np.fft.rfftfreq(N, 1 / RATE)
    band = (frequency >= 2) & (frequency <= 10)
    denominator = power_i[band] * power_j[band]
    squared = np.full(int(band.sum()), np.nan)
    valid = np.isfinite(denominator) & (denominator > 0)
    squared[valid] = abs(cross[band][valid]) ** 2 / denominator[valid]
    resolved = bool(np.isfinite(squared).all() and np.all(squared >= 0)
                    and np.all(squared <= 1 + TIE_TOLERANCE))
    passed = int(np.count_nonzero(squared > .9))
    return dict(frequency_hz=frequency[band], squared_coherence=squared,
                coherence_resolved=resolved, passing_bins=passed,
                evaluation_bins=len(squared),
                coherence_pass=resolved and 2 * passed >= len(squared))


def measure(first, first_start_ns, second, second_start_ns,
            catalog_i_minus_j_s, first_rate=RATE, second_rate=RATE):
    """Return full diagnostic arrays and explicit acceptance/rejection status.

    Rates other than native 100 Hz are retained as unsupported. No output
    uncertainty or residual multiplier is inferred from a coefficient.
    """
    result = dict(status='unprocessed', dt_cc_i_minus_j_s=None,
                  formal_timing_uncertainty_s=None, sample_spacing_s=1 / RATE)
    if first_rate != RATE or second_rate != RATE:
        result['status'] = 'unsupported_sample_rate'
        return result
    if not isinstance(first_start_ns, (int, np.integer)) or not isinstance(second_start_ns, (int, np.integer)):
        raise ValueError('Sample starts must be integer nanoseconds relative to picks')
    if not math.isfinite(catalog_i_minus_j_s):
        raise ValueError('Catalog difference must be finite')
    arrays = []
    for v in (first, second):
        if np.ma.isMaskedArray(v) and np.any(np.ma.getmaskarray(v)):
            result['status'] = 'masked_samples'
            return result
        v = np.asarray(v)
        if v.ndim != 1 or not np.issubdtype(v.dtype, np.number) or np.iscomplexobj(v):
            raise ValueError('Require one-dimensional real samples')
        if not np.isfinite(v).all():
            result['status'] = 'nonfinite_samples'
            return result
        arrays.append(v)
    first, second = arrays
    index_i = nearest_sample(-PRE_NS, first_start_ns)
    template_start_ns = first_start_ns + index_i * STEP_NS
    lower = template_start_ns - SHIFT_NS - second_start_ns
    upper = template_start_ns + SHIFT_NS - second_start_ns
    index_j_min = -(-lower // STEP_NS)
    index_j_max = upper // STEP_NS
    result.update(template_sample_index=int(index_i),
                  search_first_sample_index=int(index_j_min),
                  search_last_window_index=int(index_j_max),
                  template_start_from_pick_ns=int(template_start_ns))
    if index_i < 0 or index_i + N > len(first) or index_j_min < 0 or index_j_max + N > len(second):
        result['status'] = 'incomplete_declared_support'
        return result
    template = first[index_i:index_i + N]
    search = second[index_j_min:index_j_max + N]
    if not np.any(centered_scale(template)):
        result['status'] = 'constant_template'
        return result
    coefficients, defined = local_coefficients(search, template)
    search_start_ns = second_start_ns + index_j_min * STEP_NS
    lags_ns = search_start_ns + np.arange(len(coefficients), dtype=np.int64) * STEP_NS - template_start_ns
    result.update(coefficients=coefficients, lag_ns=lags_ns,
                  search_start_from_pick_ns=int(search_start_ns),
                  catalog_dt_i_minus_j_s=float(catalog_i_minus_j_s))
    finite = np.isfinite(coefficients)
    if np.any(defined & ~finite) or np.any(abs(coefficients[finite]) > 1 + TIE_TOLERANCE):
        result['status'] = 'invalid_numerical_coefficient'
        return result
    if not finite.any():
        result['status'] = 'constant_search_windows'
        return result
    peak = float(np.max(coefficients[finite]))
    maxima = np.flatnonzero(finite & (abs(coefficients - peak) <= TIE_TOLERANCE))
    result.update(maximum_cc=peak, maximum_cc_squared=peak ** 2,
                  tied_peak_indices=maxima.tolist())
    if peak <= 0:
        result['status'] = 'nonpositive_peak'
        return result
    if len(maxima) != 1:
        result['status'] = 'ambiguous_peak'
        return result
    peak_index = int(maxima[0])
    result['peak_index'] = peak_index
    if peak_index in (0, len(coefficients) - 1):
        result['status'] = 'boundary_peak'
        return result
    selected = search[peak_index:peak_index + N]
    result.update(spectral_screen(template, selected))
    delay = int(lags_ns[peak_index]) / 1e9
    result.update(delay_j_minus_i_s=delay,
                  candidate_dt_cc_i_minus_j_s=float(catalog_i_minus_j_s) - delay)
    if not result['coherence_resolved']:
        result['status'] = 'unresolved_coherence'
    elif not result['coherence_pass']:
        result['status'] = 'failed_coherence'
    else:
        result['status'] = 'accepted_discrete_measurement'
        result['dt_cc_i_minus_j_s'] = result['candidate_dt_cc_i_minus_j_s']
    return result
