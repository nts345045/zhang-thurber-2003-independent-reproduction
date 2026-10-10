#!/usr/bin/env python3
"""Exercise analytic-truth preparation gates with an invented constant-speed model."""
import argparse
import copy
import csv
import itertools
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import prepare_loma_analytic_truth as prepare


def write(path, rows):
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader(); writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    out = prepare.inside(ROOT, ROOT / args.output)
    out.mkdir(parents=True)
    reference = out / 'invented_reference'
    (reference / 'inputs').mkdir(parents=True)
    (reference / 'source').mkdir()
    sources = [ROOT / 'diagnostics' / name for name in ('run_loma_layered_full.py',
               'first_arrival_layered_reference.py', 'first_arrival_1d_reference.py')]
    for path in sources:
        shutil.copyfile(str(path), str(reference / 'source' / path.name))
    events = [dict(id=str(i), x=str(x), y='0', z='0', t='0',
                   event_resource_id='fixture:event:' + str(i), origin_resource_id='fixture:origin:' + str(i),
                   record_basis='Invented numerical control, not a real earthquake')
              for i, x in enumerate((-.5, .5))]
    stations = [dict(id=str(i), x=str(x), y='1', z='0', t='0', network_code='ZZ',
                    station_code='FIX' + str(i), location_code='', channel_code='EHZ',
                    channel_seed_id='ZZ.FIX' + str(i) + '..EHZ',
                    channel_fdsn_source_id='FDSN:ZZ_FIX' + str(i) + '__E_H_Z',
                    metadata_epoch_start='2000-01-01T00:00:00', metadata_epoch_end='',
                    record_basis='Invented numerical control, not a real station')
                for i, x in enumerate((-1., 1.))]
    grid = [dict(x=x, y=y, z=z, v=6.) for x, y, z in itertools.product((-2., 2.), (-2., 2.), (-1., 1.))]
    for name, rows in [('truth_events.csv', events), ('stations.csv', stations), ('truth_grid.csv', grid)]:
        write(reference / 'inputs' / name, rows)
    levels, box = prepare.batch.geometry(events, stations, grid, (2, 2))
    function = prepare.batch.load_reference(reference / 'source/first_arrival_layered_reference.py')
    result = prepare.batch.stream_references(reference, events, stations, levels, box, function, lambda unused: None)
    assert result['counts']['reference_valid'] == 4 and result['counts']['branch_flat_direct'] == 4
    summary = dict(status='complete', source_count=2, receiver_count=2, expected_pairs=4, verified_pairs=4,
                   profile_x_velocity_km_km_s=levels, original_box_km=box, **result)

    def seal(header=None, independent_change=None):
        value = copy.deepcopy(summary if header is None else header)
        value['output_sha256'] = {str(p.relative_to(reference)): prepare.batch.sha(p)
            for p in reference.rglob('*') if p.is_file() and p.name not in
            ('summary.json', 'execution.json', 'review.json', 'independent_review.json')}
        (reference / 'summary.json').write_text(json.dumps(value, indent=2) + '\n')
        ledger = dict(status='completed', result_status='complete', summary_sha256=prepare.batch.sha(reference / 'summary.json'))
        (reference / 'execution.json').write_text(json.dumps(ledger, indent=2) + '\n')
        links = dict(summary_sha256=ledger['summary_sha256'], execution_sha256=prepare.batch.sha(reference / 'execution.json'))
        review = dict(links, counts=dict(pairs=4, reference_valid=4))
        independent = dict(links, verified_pairs=4, invalid_reference_count=0,
            native_metadata_fields_all_match=True, ordered_indices_complete=True,
            source_derivative_permutation_matches=True, material_issue_found=False)
        if independent_change:
            independent.update(independent_change)
        for name, record in [('review.json', review), ('independent_review.json', independent)]:
            (reference / name).write_text(json.dumps(record, indent=2) + '\n')

    seal()
    baseline = {p: p.read_bytes() for p in reference.rglob('*') if p.is_file()}
    checks = []

    def check(label, mutate, reject=True):
        for path, content in baseline.items():
            path.write_bytes(content)
        mutate()
        try:
            accepted, hashes = prepare.reviewed_reference(reference, (2, 2))
        except ValueError as error:
            if not reject:
                raise
            checks.append(dict(name=label, passed=True, rejected=True, message=str(error)))
        else:
            if reject:
                raise AssertionError('Preparation accepted ' + label)
            assert accepted['verified_pairs'] == 4 and len(hashes) >= 12
            checks.append(dict(name=label, passed=True, rejected=False))

    check('complete_identified_homogeneous_reference', lambda: None, reject=False)
    check('unresolved_terminal_status', lambda: seal(dict(summary, status='completed_with_unresolved_references')))
    check('reported_invalid_pair', lambda: seal(dict(summary, unresolved_pair_indices=[0])))
    check('reported_near_tie', lambda: seal(dict(summary, near_tie_pair_indices=[0])))
    check('independent_metadata_failure', lambda: seal(independent_change={'native_metadata_fields_all_match': False}))
    check('independent_material_issue', lambda: seal(independent_change={'material_issue_found': True}))
    check('independent_review_wrong_snapshot', lambda: seal(independent_change={'summary_sha256': 'wrong'}))
    check('changed_frozen_candidate_bytes', lambda: (reference / 'references.csv.gz').write_bytes(b'changed'))

    def moved_source():
        changed = copy.deepcopy(events); changed[0]['x'] = '-0.4'
        write(reference / 'inputs/truth_events.csv', changed)
        seal()

    check('rehash_cannot_hide_native_coordinate_mismatch', moved_source)
    for path, content in baseline.items():
        path.write_bytes(content)
    failed = ROOT / 'data/development/loma_layered_full_001'
    try:
        prepare.reviewed_reference(failed)
    except ValueError as error:
        assert 'not complete and valid' in str(error)
        checks.append(dict(name='real_failed_full001_is_not_promoted', passed=True, rejected=True, message=str(error)))
    else:
        raise AssertionError('Failed full reference was accepted')
    snapshot = out / 'source'; snapshot.mkdir()
    for path in [Path(__file__).resolve(), ROOT / 'prepare_loma_analytic_truth.py'] + sources:
        shutil.copyfile(str(path), str(snapshot / path.name))
    result = dict(status='passed', checks=checks,
        scope='Invented constant-speed preparation contract and rejection of the preserved failed full001; no real truth export or simulation',
        real_failed_summary_sha256=prepare.batch.sha(failed / 'summary.json'),
        output_sha256={str(p.relative_to(out)): prepare.batch.sha(p) for p in out.rglob('*') if p.is_file()})
    (out / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
    print('Passed {} analytic-truth preparation checks'.format(len(checks)))


if __name__ == '__main__':
    main()
