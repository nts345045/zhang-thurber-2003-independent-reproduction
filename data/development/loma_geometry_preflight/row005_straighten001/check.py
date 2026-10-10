#!/usr/bin/env python3
"""Review this frozen candidate experiment without running another ray search."""
import csv
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path):
    with path.open() as stream:
        return list(csv.DictReader(stream))


def main():
    manifest = json.loads((ROOT / 'summary.json').read_text())
    reference_path = ROOT.parent / 'row005_guide_reference/result.json'
    reference = json.loads(reference_path.read_text())
    identity = rows(ROOT / 'identified_ray.csv')
    checks = []

    def check(name, condition):
        checks.append(dict(name=name, passed=bool(condition)))

    check('one identified diagnostic row', len(identity) == 1)
    check('all frozen command exits are zero', all(c['exit_code'] == 0 for c in manifest['commands']))
    for name, expected in manifest['output_sha256'].items():
        check('hash:' + name, digest(ROOT / name) == expected)
    results = []
    for path in sorted(ROOT.glob('spacing*/result.csv')):
        data = rows(path)
        initial, straight, final = data
        check(path.parent.name + ': three declared stages', [r['stage'] for r in data] ==
              ['original', 'straightened', 'branch_optimized'])
        history = rows(path.parent / 'history.csv')
        check(path.parent.name + ': budget exhausted', len(history) == 4001 and history[-1]['iteration'] == '4000')
        check(path.parent.name + ': strict restricted stop not met', float(final['restricted_gradient_s_per_km']) >= 1e-7)
        check(path.parent.name + ': action decreases', float(initial['time_s']) >= float(straight['time_s']) >= float(final['time_s']))
        check(path.parent.name + ': history is monotone', all(float(b['time_s']) <= float(a['time_s']) + 1e-12
              for a, b in zip(history, history[1:])))
        check(path.parent.name + ': exact action agrees', all(abs(float(r['time_s']) - float(r['exact_action_s'])) < 3e-13 for r in data))
        check(path.parent.name + ': final history agrees', history[-1]['time_s'] == final['time_s'] and
              history[-1]['restricted_gradient_s_per_km'] == final['restricted_gradient_s_per_km'])
        paths = rows(path.parent / 'paths.csv')
        stages = {stage: [[float(r[k]) for k in ['x_km', 'y_km', 'z_km']]
                           for r in paths if r['stage'] == stage]
                  for stage in ['original', 'straightened', 'branch_optimized']}
        check(path.parent.name + ': all path identities join', all(r['diagnostic_row'] == '5' and r['run_id'] == final['run_id'] for r in paths))
        for stage, points in stages.items():
            check(path.parent.name + ': fixed endpoints:' + stage,
                  points[0] == stages['original'][0] and points[-1] == stages['original'][-1])
            check(path.parent.name + ': finite in-domain points:' + stage,
                  all(math.isfinite(v) and reference['original_domain_km'][key][0] <= v <= reference['original_domain_km'][key][1]
                      for p in points for key, v in zip('xyz', p)))
            if stage != 'original':
                check(path.parent.name + ': exact guide contacts:' + stage,
                      points[int(final['guide_start_node'])][0] == 0 and points[int(final['guide_end_node'])][0] == 0)
        results.append(dict(run_id=final['run_id'], diagnostic_row=5,
                            event_resource_id=reference['event_resource_id'],
                            origin_resource_id=reference['origin_resource_id'],
                            channel_seed_id=reference['channel_seed_id'],
                            channel_fdsn_source_id=reference['channel_fdsn_source_id'],
                            metadata_epoch_start=reference['metadata_epoch_start'],
                            metadata_epoch_end=reference['metadata_epoch_end'],
                            straightening_reduction_s=float(initial['time_s']) - float(straight['time_s']),
                            total_reduction_s=float(initial['time_s']) - float(final['time_s']),
                            branch_minus_exact_guide_s=float(final['time_s']) - reference['candidate_time_s'],
                            restricted_gradient_s_per_km=float(final['restricted_gradient_s_per_km']),
                            maximum_source_derivative_error_s_per_km=max(abs(float(final['source_d' + key]) - exact)
                                for key, exact in zip('xyz', reference['source_derivative_s_per_km']))))
    check('four completed saved-path candidates', len(results) == 4)
    result = dict(status='passed' if all(c['passed'] for c in checks) else 'failed', checks=checks, results=results,
                  scientific_conclusion='Straightening is action-decreasing, but none of the four restricted searches meets the strict 1e-7 s/km gradient stop within 4000 updates. No production correction or unrestricted stationarity is claimed.',
                  reference_sha256=digest(reference_path), review_source_sha256=digest(Path(__file__)))
    (ROOT / 'review.json').write_text(json.dumps(result, indent=2) + '\n')
    print('{}: {} checks'.format(result['status'], len(checks)))
    if result['status'] != 'passed':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
