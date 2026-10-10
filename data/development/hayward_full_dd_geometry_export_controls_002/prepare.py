#!/usr/bin/env python3
"""Freeze source and invented inputs only; never compile or evaluate a ray."""
import csv
import difflib
import hashlib
import json
from pathlib import Path
import shutil
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CANDIDATE = ROOT / 'data/development/hayward_full_dd_geometry_export_candidate_001'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def table(path, rows):
    with path.open('x', newline='') as f:
        out = csv.DictWriter(f, fieldnames=list(rows[0])); out.writeheader(); out.writerows(rows)


def main():
    if not __debug__:
        raise RuntimeError('Preparation requires ordinary assertion-enabled Python')
    if (HERE / 'prepared.json').exists() or (HERE / 'source').exists():
        raise RuntimeError('Preserve existing prepared controls')
    candidate = json.loads((CANDIDATE / 'prepared.json').read_text())
    review = json.loads((CANDIDATE / 'root_source_review.json').read_text())
    assert review['status'] == 'passed_source_review'
    assert review['prepared_sha256'] == sha(CANDIDATE / 'prepared.json')
    original = {str((CANDIDATE / name).relative_to(ROOT)): sha(CANDIDATE / name)
                for name in ('prepared.json', 'root_source_review.json', 'CONTROL_PLAN.md')}
    previous = ROOT / 'data/development/hayward_full_dd_geometry_export_controls_001/prepared.json'
    original[str(previous.relative_to(ROOT))] = sha(previous)
    for variant in ('before', 'after'):
        for path in sorted((CANDIDATE / variant).rglob('*')):
            if not path.is_file():
                continue
            assert sha(path) == candidate['output_sha256'][str(path.relative_to(CANDIDATE))]
            original[str(path.relative_to(ROOT))] = sha(path)
        shutil.copytree(str(CANDIDATE / variant), str(HERE / 'source' / variant))
    shutil.copytree(str(HERE / 'source/after'), str(HERE / 'source/after_io'))
    path = HERE / 'source/after_io/src/main.cpp'; old = path.read_text()
    needle = '  std::ofstream f(p);'
    replacement = ('  std::ofstream f(!fixture_output_suffix.empty() && p.size() >= fixture_output_suffix.size() &&\n'
                   '      p.compare(p.size() - fixture_output_suffix.size(), fixture_output_suffix.size(), fixture_output_suffix) == 0\n'
                   '      ? "/dev/full" : p);')
    assert old.count(needle) == 1
    new = old.replace(needle, replacement)
    path.write_text(new)
    (HERE / 'io_seam.patch').write_text(''.join(difflib.unified_diff(
        old.splitlines(True), new.splitlines(True), fromfile='source/after/src/main.cpp',
        tofile='source/after_io/src/main.cpp')))
    inputs = HERE / 'inputs'; inputs.mkdir()
    events = []
    for i, coords in enumerate(((1/3, .5, .75, .012345678901234), (.8, 1.1, 1.4, -.03))):
        row = {'id': str(i)}
        row.update({a: format(value, '.12g') for a, value in zip('xyzt', coords)})
        row.update(event_resource_id='fixture:event:' + str(i), origin_resource_id='fixture:origin:' + str(i),
                   coordinate_basis='invented saved 12-digit source', note='comma, quote " and\nnewline' if i == 0 else '')
        events.append(row)
    table(inputs / 'dd_events.csv', events)
    stations = []
    for i in range(2):
        row = {'id': str(i), 'x': '1.5', 'y': '1.5', 'z': '0', 't': '0',
               'network_code': 'XX', 'station_code': 'FIX', 'location_code': '', 'channel_code': 'HHZ',
               'channel_seed_id': 'XX.FIX..HHZ', 'channel_fdsn_source_id': 'FDSN:XX_FIX__H_H_Z',
               'metadata_epoch_start': '1984-01-01' if i == 0 else '1990-01-01',
               'metadata_epoch_end': '1990-01-01' if i == 0 else '',
               'channel_resource_id': '', 'note': 'invented, separate native epoch'}
        stations.append(row)
    table(inputs / 'stations.csv', stations)
    grid = [{'x': str(x), 'y': str(y), 'z': str(z), 'v': '6'}
            for z in (0, 2) for y in (0, 2) for x in (0, 2)]
    table(inputs / 'dd_grid.csv', grid)
    observations = []
    for i, j, k, second, kind, value, prior in ((0,-1,0,-1,0,.3,1), (1,-1,1,-1,0,.25,1),
                                               (0,1,0,1,1,.05,1), (1,-1,0,-1,0,.25,0)):
        row = {'i':str(i), 'j':str(j), 'station':str(k), 'type':str(kind), 'value':str(value),
               'station_j':str(second), 'a_priori_weight':str(prior)}
        for side, event, station in (('i',i,k), ('j',j,second)):
            for name in ('event', 'origin', 'pick', 'arrival'):
                row[name+'_'+side+'_resource_id'] = '' if event < 0 else 'fixture:'+name+':'+str(event)+(':'+str(station) if name in ('pick','arrival') else '')
        for key in ('network_code','station_code','location_code','channel_code','channel_seed_id',
                    'channel_fdsn_source_id','metadata_epoch_start','metadata_epoch_end'):
            row[key] = stations[k][key]
        for edge in ('start','end'):
            row['metadata_epoch_j_'+edge] = '' if j < 0 else stations[second]['metadata_epoch_'+edge]
        row['note'] = 'original quoted, "observation"\nmetadata'
        observations.append(row)
    table(inputs / 'observations.csv', observations)
    (inputs / 'run.cfg').write_text('smoothing 0.2\ndamping 0.1\npair_distance 10\ncatalog_only_dd 1\n'
                                   'ray_spacing 0.25\nray_iterations 1000\nray_initializer 1\nfmm_spacing 0.5\n')
    cases = {
      'array_cases': ['valid','unattempted','missing_required','local','initializer_failed','outside',
                      'source_endpoint','receiver_endpoint','empty','nan_path','nan_time','nan_source',
                      'short_dv','short_length','wrong_array','io_geometry','io_paths'],
      'malformed_cases': ['missing_pair','duplicate_pair','wrong_event_id','wrong_origin_id','wrong_channel',
                          'wrong_epoch','bad_source_coordinate','bad_source_t','drop_node','duplicate_node',
                          'node_order','wrong_count','bad_source_endpoint','bad_receiver_endpoint','outside_node',
                          'false_domain','false_evaluated','false_finite','false_local','initializer_failed',
                          'initializer_missing','bad_node_native','legacy_coordinate','legacy_flag','observed_value',
                          'observation_metadata','second_epoch','matrix_partial','missing_matrix_source',
                          'duplicate_header','bad_initializer_config','info_count','missing_original_file',
                          'coordinated_absolute_event','coordinated_absolute_origin','coordinated_dd_event_j',
                          'coordinated_dd_origin_j','coordinated_absent_event_j','coordinated_absent_origin_j',
                          'coordinated_absolute_seed','coordinated_absolute_fdsn','coordinated_absolute_location',
                          'coordinated_absolute_epoch_start','coordinated_absolute_epoch_end'],
      'preservation_cases': ['cli_geometry_regular','cli_geometry_dangling','cli_paths_regular','cli_paths_dangling',
                             'array_geometry_regular','array_geometry_dangling','array_paths_regular','array_paths_dangling'],
      'actual_ray_calls': 'Two identical tiny full exports, before and after; each traces only three used invented native pairs.',
      'not_run': ['inverse','field rays','covariance algebra','native data queries']}
    (HERE / 'cases.json').write_text(json.dumps(cases, indent=2) + '\n')
    outputs = {str(p.relative_to(HERE)): sha(p) for p in sorted(HERE.rglob('*')) if p.is_file()}
    runtimes = candidate['runtime_sha256'].copy(); runtimes[str(Path(sys.executable).resolve())] = sha(Path(sys.executable).resolve())
    for name, digest in runtimes.items():
        assert sha(name) == digest
    prepared = {'status':'prepared_not_executed', 'original_sha256':original, 'output_sha256':outputs,
                'runtime_sha256':runtimes, 'compiler':candidate['compiler'], 'flags':candidate['flags'].split(),
                'python':str(Path(sys.executable).resolve()), 'candidate_prepared_sha256':sha(CANDIDATE/'prepared.json'),
                'scope':'Declared invented geometry export/readback and I/O controls only; covariance algebra unchanged.'}
    with (HERE / 'prepared.json').open('x') as f:json.dump(prepared,f,indent=2,sort_keys=True);f.write('\n')
    print(sha(HERE / 'prepared.json'))


if __name__ == '__main__':
    main()
