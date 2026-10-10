#!/usr/bin/env python3
"""Compare the two frozen full-geometry reference batches without rerunning rays."""
import csv
import gzip
import hashlib
import itertools
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
PRIOR = HERE.parent / 'loma_layered_full_001'


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1048576), b''):
            h.update(chunk)
    return h.hexdigest()


def checked_summary(folder):
    summary = json.loads((folder / 'summary.json').read_text())
    ledger = json.loads((folder / 'execution.json').read_text())
    if ledger['status'] != 'completed' or ledger['summary_sha256'] != sha(folder / 'summary.json'):
        raise ValueError('Missing terminal batch summary')
    for name, digest in summary['output_sha256'].items():
        if sha(folder / name) != digest:
            raise ValueError('Changed batch artifact: ' + name)
    return summary


def main():
    old_summary, new_summary = map(checked_summary, (PRIOR, HERE))
    for name, digest in old_summary['input_source_sha256'].items():
        if name != 'diagnostics/first_arrival_layered_reference.py':
            if new_summary['input_source_sha256'][name] != digest:
                raise ValueError('Unexpected input/source change: ' + name)
    matches = both_valid = 0
    max_time = max_gradient = 0.
    branch_changes, validity_changes, old_invalid = [], [], []
    with gzip.open(str(PRIOR / 'references.csv.gz'), 'rt', newline='') as a:
        with gzip.open(str(HERE / 'references.csv.gz'), 'rt', newline='') as b:
            old_rows, new_rows = csv.DictReader(a), csv.DictReader(b)
            if old_rows.fieldnames != new_rows.fieldnames:
                raise ValueError('Reference schema changed')
            native = [k for k in old_rows.fieldnames if k.startswith(('source_', 'receiver_'))
                      and k not in ('source_dx_s_per_km', 'source_dy_s_per_km', 'source_dz_s_per_km')]
            for index, pair in enumerate(itertools.zip_longest(old_rows, new_rows)):
                old, new = pair
                if old is None or new is None:
                    raise ValueError('Different pair support')
                if any(old[k] != new[k] for k in native + ['pair_index', 'event', 'station']):
                    raise ValueError('Native geometry/metadata changed at pair ' + str(index))
                if int(new['pair_index']) != index:
                    raise ValueError('Pair order changed')
                matches += 1
                if old['reference_valid'] != new['reference_valid']:
                    validity_changes.append(dict(pair_index=index, old_valid=int(old['reference_valid']),
                                                 new_valid=int(new['reference_valid'])))
                if old['reference_valid'] == '1' and new['reference_valid'] == '1':
                    both_valid += 1
                    dt = abs(float(new['time_s']) - float(old['time_s']))
                    dg = math.sqrt(sum((float(new['source_d'+axis+'_s_per_km']) -
                                        float(old['source_d'+axis+'_s_per_km']))**2 for axis in 'xyz'))
                    if not math.isfinite(dt) or not math.isfinite(dg):
                        raise ValueError('Nonfinite comparison')
                    max_time, max_gradient = max(max_time, dt), max(max_gradient, dg)
                    if old['branch'] != new['branch']:
                        branch_changes.append(dict(pair_index=index, old=old['branch'], new=new['branch']))
                if old['reference_valid'] != '1':
                    keys = ['pair_index', 'event', 'station', 'source_event_resource_id',
                            'source_origin_resource_id', 'receiver_channel_seed_id',
                            'receiver_channel_fdsn_source_id', 'receiver_metadata_epoch_start',
                            'receiver_metadata_epoch_end']
                    record = {key: new[key] for key in keys}
                    record.update(old_reference_valid=int(old['reference_valid']),
                                  new_reference_valid=int(new['reference_valid']),
                                  new_time_s=float(new['time_s']) if new['time_s'] else None)
                    old_invalid.append(record)
    if matches != old_summary['expected_pairs'] or matches != new_summary['expected_pairs']:
        raise ValueError('Incomplete Cartesian support')
    max_closure = 0.
    with gzip.open(str(HERE / 'certificates.jsonl.gz'), 'rt') as stream:
        for line in stream:
            record = json.loads(line)
            for candidate in record['reference']['candidates']:
                residual = float(candidate['distance_residual_km'])
                if not math.isfinite(residual):
                    raise ValueError('Nonfinite closure residual')
                max_closure = max(max_closure, abs(residual))
    result = dict(scope='Frozen full-batch readback comparison; no reference arithmetic or production runs',
                  native_geometry_and_metadata_exact_matches=matches,
                  old_and_new_valid_count=both_valid,
                  maximum_reference_time_change_s=max_time,
                  maximum_source_vector_change_s_per_km=max_gradient,
                  branch_kind_changes_among_previously_valid=branch_changes,
                  validity_changes=validity_changes,
                  previously_invalid_pairs=old_invalid,
                  maximum_candidate_distance_residual_km=max_closure,
                  old_summary_sha256=sha(PRIOR / 'summary.json'),
                  new_summary_sha256=sha(HERE / 'summary.json'),
                  source_sha256=sha(Path(__file__)),
                  limitations=['Difference magnitudes are reported without a new acceptance threshold.',
                               'Time ranking remains ordinary floating point, not interval certified.',
                               'Native metadata is preserved for catalog-defined simulation geometry; no observations were generated.'])
    (HERE / 'prior_comparison.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({key: value for key, value in result.items() if key != 'previously_invalid_pairs'}, indent=2))


if __name__ == '__main__':
    main()
