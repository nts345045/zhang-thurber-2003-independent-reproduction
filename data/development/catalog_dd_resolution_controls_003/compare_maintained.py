#!/usr/bin/env python3
"""Compare saved invented dense fixtures with the frozen maintained Schur solve."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
FIXED = ROOT / 'data/development/full_dd_resolution_finite_checks_001/source/resolution_full_hayward.py'
OLD = ROOT / 'data/development/full_dd_resolution_checks/source/resolution_full_hayward.py'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, str(path))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def main():
    summary = json.loads((HERE / 'summary.json').read_text())
    if not summary['passed']:
        raise ValueError('Frozen dense controls did not pass')
    inputs = [HERE / 'summary.json', Path(__file__).resolve(), FIXED, OLD]
    for name, expected in summary['files'].items():
        path = HERE / name
        if sha(path) != expected:
            raise ValueError('Frozen dense input changed: ' + name)
        inputs.append(path)
    pins = {str(p.relative_to(ROOT)): sha(p) for p in inputs}
    maintained, old = module(FIXED, 'maintained'), module(OLD, 'old')
    saved = np.load(str(HERE / 'invented_matrices.npz'), allow_pickle=False)
    checks, cases = [], {}
    ns, damping, tolerance = 5, .2, 1e-12
    for label in ('coupled', 'masked'):
        G = saved[label + '_G']
        w, C, sigma = [saved['coupled_' + x] for x in ('weights', 'C', 'sigma')]
        L = np.zeros((saved['coupled_L'].shape[0], G.shape[1]))
        L[:, ns:] = saved['coupled_L']
        A = w[:, None] * G
        # These fixtures have one stored entry per position. With duplicate
        # entries, the real loader must use exported pre-coalescing norms.
        norms = np.sum(A * A, axis=0) + np.sum(L * L, axis=0)
        d = damping * np.sqrt(np.where(norms > 1e-20, norms, 1.))
        U = w[:, None] * C * sigma[None, :]
        J = G[:, ns:] if label == 'coupled' else saved['unmasked_prediction_model']
        current = maintained.joint_resolution(A, L, ns, d, U, w[:, None] * J)
        previous = old.joint_resolution(A, L, ns, d, U, w[:, None] * J)
        expected = ([saved['coupled_resolution'], saved['coupled_covariance'],
                     saved['coupled_resolution']] if label == 'coupled' else
                    [saved['masked_assembly_resolution'], saved['masked_estimator_covariance'],
                     saved['masked_estimator_physical_resolution']])
        for k, kind in enumerate(('assembly_resolution', 'shared_pick_covariance', 'physical_response')):
            error = float(np.max(np.abs(current[k] - expected[k])))
            checks.append(dict(case=label, quantity=kind, maximum_absolute_difference=error,
                tolerance=tolerance, passed=bool(np.all(np.isfinite(current[k])) and error <= tolerance),
                old_and_fixed_maintained_arrays_exactly_equal=bool(np.array_equal(current[k], previous[k]))))
        cases[label] = dict(rows=G.shape[0], source_columns=ns, model_columns=G.shape[1]-ns,
            independent_picks=C.shape[1], damping_scalar=damping,
            damping_coefficients=d.tolist(), diagnostics=current[3],
            physical_minus_assembly_max=float(np.max(np.abs(current[2]-current[0]))))
    saved.close()
    if any(sha(ROOT / path) != digest for path, digest in pins.items()):
        raise ValueError('Input changed during comparison')
    report = dict(status='passed' if all(c['passed'] and c['old_and_fixed_maintained_arrays_exactly_equal'] for c in checks) else 'failed',
        scope='Saved invented coupled/masked fixtures only; no field data, tracing or inverse solve.',
        input_sha256=pins, checks=checks, cases=cases,
        maximum_absolute_difference=max(c['maximum_absolute_difference'] for c in checks),
        conventions=dict(A='W G_used', U='W C diag(sigma_pick)',
            L='Full-width model-only smoothing; source block zero',
            damping='lambda sqrt(exported ordered norm or existing 1e-20 fallback)',
            physical='Weighted unmasked prediction-model Jacobian supplied separately'),
        limitations=['Conditional frozen weights/masks/scales and unconstrained sources.',
            'Dense output hashes and all original controls_003 files remain unchanged.',
            'No extra 0.05 factor and no independent differential-pick errors.',
            'Exact array equality only compares the two maintained revisions on these fixtures.'])
    with (HERE / 'maintained_comparison.json').open('x') as stream:
        stream.write(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps(dict(status=report['status'], checks=len(checks), maximum_absolute_difference=report['maximum_absolute_difference'])))
    if report['status'] != 'passed':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
