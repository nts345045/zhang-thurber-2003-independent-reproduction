#!/usr/bin/env python3
"""Prepare isolated identified catalog-plus-CC inputs; never invoke a solver."""
import argparse
from collections import Counter
import csv
import datetime
import gzip
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parent
PREFIX = 'original_catalog_'
CHANNEL = ('network_code', 'station_code', 'location_code', 'channel_code',
           'channel_seed_id', 'channel_fdsn_source_id')
POSITION = ('x', 'y', 'z', 'latitude_deg', 'longitude_deg', 'sensor_z_geoid_km')
EXTRA = ('cc_uncertainty_status', 'solver_weight_basis', 'solver_objective_quality_power',
         'provider_pick_identity_role')
PINS = ('derived_measurement_summary_sha256', 'derived_measurement_review_sha256',
        'legacy_export_summary_sha256', 'legacy_export_review_sha256')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            digest.update(block)
    return digest.hexdigest()


def table(path):
    with (gzip.open if path.suffix == '.gz' else open)(str(path), 'rt', newline='') as stream:
        reader = csv.DictReader(stream); fields = reader.fieldnames
        require(fields and len(fields) == len(set(fields)), 'Missing/duplicate CSV columns')
        rows = list(reader)
        require(all(None not in row and all(v is not None for v in row.values()) for row in rows), 'Malformed CSV row')
    return fields, rows


def integer(value):
    result = int(value)
    require(str(result) == value, 'Noncanonical numerical identity')
    return result


def number(value):
    result = float(value)
    require(math.isfinite(result), 'Nonfinite numerical value')
    return result


def native_row(row, events, stations):
    i, j, k, kj, kind = [integer(row[x]) for x in ('i', 'j', 'station', 'station_j', 'type')]
    require(kind in (0, 1) and 0 <= i < len(events) and 0 <= k < len(stations), 'Invalid catalog row indices/type')
    require((kind == 0 and j == kj == -1) or (kind == 1 and 0 <= j < len(events) and i != j and 0 <= kj < len(stations)),
            'Invalid catalog differential/absolute association')
    require(number(row['a_priori_weight']) >= 0, 'Negative catalog row multiplier')
    number(row['value'])
    for side, index, receiver in (('i', i, k), ('j', j, kj)):
        for name in ('event', 'origin', 'pick', 'arrival'):
            value = row[name+'_'+side+'_resource_id']
            if index < 0:
                require(not value, 'Absolute row has a second native identity')
            else:
                require(bool(value), 'Missing native '+name+' identity')
                if name in ('event', 'origin'):
                    require(value == events[index][name+'_resource_id'], 'Catalog event/origin identity mismatch')
        if index < 0:
            continue
        station = stations[receiver]
        require(all(row[name] == station[name] for name in CHANNEL), 'Catalog receiver NSLC mismatch')
        for edge in ('start', 'end'):
            require(row['metadata_epoch_'+('j_' if side == 'j' else '')+edge] == station['metadata_epoch_'+edge], 'Catalog receiver epoch mismatch')
        require(row['channel_'+('j_' if side == 'j' else '')+'source_sha256'] == station['source_sha256'], 'Catalog receiver source hash mismatch')
    if j >= 0:
        require(tuple(number(stations[k][n]) for n in POSITION) == tuple(number(stations[kj][n]) for n in POSITION),
                'Paired receiver positions differ')


def assemble(catalog_fields, catalog_rows, events, stations, export_rows,
             event_map, receiver_epochs, legacy_text):
    """Return header and complete rows, with unchanged catalog values first."""
    require(catalog_fields[:5] == ['i', 'j', 'station', 'type', 'value'], 'Solver CSV prefix differs')
    require(catalog_rows and events and stations and export_rows, 'Empty input roster')
    require(len(catalog_fields) == len(set(catalog_fields)), 'Duplicate catalog fields')
    for rows, label in ((events, 'event'), (stations, 'receiver')):
        require([r['id'] for r in rows] == [str(i) for i in range(len(rows))], 'Noncontiguous '+label+' indices')
    require(len({e['event_resource_id'] for e in events}) == len(events), 'Duplicate event resource ID')
    for row in catalog_rows:
        require(set(row) == set(catalog_fields), 'Catalog row schema differs')
        native_row(row, events, stations)
    export_fields = list(export_rows[0])
    require(all(set(r) == set(export_fields) for r in export_rows), 'Export sidecar schema differs')
    extra_fields = export_fields + list(EXTRA)
    require(not (set(extra_fields) & set(catalog_fields)) and len(extra_fields) == len(set(extra_fields)), 'Derived metadata collides with catalog columns')
    combined_fields = catalog_fields + extra_fields
    combined = [dict(row, **{name: '' for name in extra_fields}) for row in catalog_rows]
    epoch_map = {r['id']: r for r in receiver_epochs}
    require(len(epoch_map) == len(receiver_epochs), 'Duplicate exported receiver epoch')
    maps = {r['original_event_index']: r for r in event_map}
    require(len(maps) == len(event_map), 'Duplicate exported event mapping')
    seen, measurements, used_events, used_epochs, used_lines, used_headers = set(), set(), set(), set(), set(), set()
    lines = legacy_text.splitlines()
    for exported in export_rows:
        q = integer(exported[PREFIX+'original_observation_index'])
        require(0 <= q < len(catalog_rows) and q not in seen, 'Missing/duplicate original catalog row')
        seen.add(q); original = catalog_rows[q]
        require(original['type'] == '1', 'CC source row must be a catalog differential')
        require(all(exported[PREFIX+name] == original[name] for name in catalog_fields), 'Full original catalog row differs')
        require(exported['measurement_id'] and exported['measurement_id'] not in measurements, 'Missing/duplicate derived measurement ID')
        measurements.add(exported['measurement_id'])
        for side in ('i', 'j'):
            index = original[side]; used_events.add(index); event = events[integer(index)]
            require(index in maps, 'Missing exported event mapping')
            mapping = maps[index]
            require(mapping['dt_cc_event_id'] == str(integer(index)+1) == exported['dt_cc_event_'+side] and
                    all(mapping[key] == event[key] for key in ('event_resource_id', 'origin_resource_id')), 'Export event/origin map differs')
        accepted = exported['measurement_status'] == 'accepted_discrete_measurement'
        require((exported['dt_cc_export_status'] == 'exported') == accepted, 'Measurement/export acceptance differs')
        if not accepted:
            require(exported['dt_cc_export_status'] == 'not_accepted' and not exported['dt_cc_i_minus_j_s'] and
                    not exported['cc_relative_weight_squared'] and not exported['dt_cc_line_number'], 'Rejected row has an accepted export')
            continue
        require(exported['cc_attempted'] == '1' and exported['diagnostics_jsonl_row'] != '', 'Accepted row lacks diagnostics')
        require(not exported['cc_formal_timing_uncertainty_s'], 'CC timing uncertainty is not established')
        cc = number(exported['maximum_cc']); prior = number(exported['cc_relative_weight_squared'])
        require(0 < cc <= 1+64*sys.float_info.epsilon and prior == cc**2 == number(exported['maximum_cc_squared']), 'Expected literal positive CC squared prior')
        value = number(exported['dt_cc_i_minus_j_s'])
        require(value == number(original['value'])-number(exported['cc_delay_j_minus_i_s']), 'CC differential-time sign/value differs')
        require(exported['dt_cc_phase'] == 'P' and number(exported['dt_cc_origin_correction_s']) == 0 and
                exported['dt_cc_station'] == original['station_code'], 'Legacy phase/station/origin convention differs')
        for name in ('station', 'station_j'):
            index = original[name]; require(index in epoch_map, 'Missing exported receiver epoch')
            epoch = epoch_map[index]; native = stations[integer(index)]
            require(all(epoch[key] == val for key, val in native.items()), 'Exported full native receiver epoch differs')
            require(epoch['dt_cc_station'] == native['station_code'], 'Exported station label differs')
            used_epochs.add(index)
        line = integer(exported['dt_cc_line_number']); header = integer(exported['dt_cc_header_line_number'])
        require(1 <= header < line <= len(lines) and line not in used_lines, 'Invalid/duplicate legacy line mapping')
        require(lines[header-1].split() == ['#', exported['dt_cc_event_i'], exported['dt_cc_event_j'], '0.0'], 'Legacy pair header differs')
        words = lines[line-1].split()
        require(len(words) == 4 and words[0] == exported['dt_cc_station'] and words[3] == 'P' and
                number(words[1]) == value and number(words[2]) == prior, 'Legacy value/weight readback differs')
        require(all(not item.startswith('#') for item in lines[header:line]), 'Legacy line points to an intervening pair header')
        used_lines.add(line); used_headers.add(header)
        row = dict(original); row.update(exported)
        row.update(type='2', value=exported['dt_cc_i_minus_j_s'], a_priori_weight=exported['cc_relative_weight_squared'],
            uncertainty_s='', observation_basis='normalized waveform P difference', cc_uncertainty_status='unestimated',
            solver_weight_basis='literal_legacy_CC_squared_row_multiplier', solver_objective_quality_power='4',
            provider_pick_identity_role='reference catalog picks; derived waveform measurement is locally identified')
        combined.append(row)
    require(seen == {q for q,r in enumerate(catalog_rows) if r['type'] == '1'}, 'Full catalog differential roster is not preserved')
    require(set(maps) == used_events and set(epoch_map) == used_epochs, 'Exported native mapping inventory differs')
    require(used_lines | used_headers == set(range(1,len(lines)+1)), 'Legacy file has unidentified lines')
    return combined_fields, combined


def run(catalog_dir, export_summary, export_review, output):
    catalog_dir, export_summary, export_review, output = [p.resolve() for p in (catalog_dir, export_summary, export_review, output)]
    for path in (catalog_dir, export_summary, export_review, output):
        path.relative_to(ROOT)
    require(not output.exists() and output != ROOT and output not in catalog_dir.parents and catalog_dir not in output.parents,
            'Use a fresh output disjoint from original catalog inputs')
    exported_dir = export_summary.parent
    require(output != exported_dir and output not in exported_dir.parents and exported_dir not in output.parents, 'Output overlaps export evidence')
    exported = json.loads(export_summary.read_text()); review = json.loads(export_review.read_text())
    execution_path = exported_dir/'execution.json'; execution = json.loads(execution_path.read_text())
    require(exported['status'] == 'completed_identified_dt_cc_export' and exported['solver_observations_added'] == 0 and
            exported['original_catalog_values_changed'] is False, 'Export is not a completed isolated stage')
    require(review['status'] == 'passed' and review['export_summary_sha256'] == sha(export_summary) and
            review['export_execution_sha256'] == sha(execution_path), 'Require independent hash-bound export review')
    require(execution['status'] == 'completed' and execution['return_code'] == 0 and execution['summary_sha256'] == sha(export_summary) and
            execution['network_requests'] == 0, 'Require terminal offline export execution')
    pins = dict(exported['input_source_sha256'])
    for name in ('observations.csv','initial_events.csv','stations.csv'):
        path = catalog_dir/name
        require(pins.get(str(path.relative_to(ROOT))) == sha(path), 'Original catalog input is not bound to export: '+name)
    for name, digest in exported['output_sha256'].items():
        path = (exported_dir/name).resolve(); path.relative_to(exported_dir)
        require(sha(path) == digest, 'Export artifact changed: '+name); pins[str(path.relative_to(ROOT))] = digest
    copied = ['initial_events.csv','initial_grid.csv','stations.csv','authoritative_ids_required']
    for path in [catalog_dir/name for name in copied]+[export_summary,export_review,execution_path,Path(__file__).resolve()]:
        pins[str(path.relative_to(ROOT))] = sha(path)
    for name, digest in pins.items():
        path = (ROOT/name).resolve(); path.relative_to(ROOT)
        require(sha(path) == digest, 'Pinned input/source changed: '+name)
    fields, catalog = table(catalog_dir/'observations.csv')
    _, events = table(catalog_dir/'initial_events.csv'); _, stations = table(catalog_dir/'stations.csv')
    _, sidecar = table(exported_dir/'dt.cc.identifiers.csv.gz'); _, event_map = table(exported_dir/'event_id_map.csv')
    _, epochs = table(exported_dir/'receiver_epochs.csv.gz')
    require(len(sidecar) == exported['retained_original_catalog_pairs'] and
            sum(r['dt_cc_export_status'] == 'exported' for r in sidecar) == exported['exported_observations'], 'Export row counts differ')
    combined_fields, combined = assemble(fields,catalog,events,stations,sidecar,event_map,epochs,(exported_dir/'dt.cc').read_text())
    provenance = dict(zip(PINS, (review['measurements_summary_sha256'],review['measurements_review_sha256'],sha(export_summary),sha(export_review))))
    require(not (set(PINS) & set(combined_fields)), 'Provenance column collision')
    combined_fields += list(PINS)
    for q,row in enumerate(combined):
        row.update(provenance if q >= len(catalog) else {key:'' for key in PINS})
    output.mkdir(parents=True); (output/'source').mkdir(); (output/'catalog_provenance').mkdir()
    for name in copied:
        shutil.copyfile(str(catalog_dir/name),str(output/name))
    shutil.copyfile(str(catalog_dir/'observations.csv'),str(output/'catalog_provenance/observations.csv'))
    shutil.copyfile(str(Path(__file__).resolve()),str(output/'source'/Path(__file__).name))
    with (output/'observations.csv').open('x',newline='') as stream:
        writer = csv.DictWriter(stream,fieldnames=combined_fields,lineterminator='\n');writer.writeheader();writer.writerows(combined)
    read_fields,read_rows = table(output/'observations.csv')
    require(read_fields == combined_fields and read_rows == combined, 'Prepared row readback differs')
    require([{key:row[key] for key in fields} for row in read_rows[:len(catalog)]] == catalog, 'Catalog values changed')
    for name,digest in pins.items():
        require(sha(ROOT/name) == digest, 'Input/source changed during preparation: '+name)
    result = dict(status='prepared_identified_catalog_plus_cc_inputs',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        input_source_sha256=pins,original_catalog_rows=len(catalog),appended_cc_rows=len(combined)-len(catalog),prepared_rows=len(combined),
        type_counts=dict(Counter(r['type'] for r in combined)),original_catalog_fields_and_order_unchanged=True,
        legacy_weight_adoption='Literal saved CC squared is a_priori_weight; it multiplies residual and Jacobian rows.',
        squared_objective_quality='CC to the fourth power before squared stage, robust and distance factors; no square-root reinterpretation.',
        uncertainty='Derived CC uncertainty_s remains blank/unestimated. Original pick uncertainties remain reference-pick provenance, not CC sigmas.',
        required_future_configuration='Explicitly set catalog_only_dd=0 and all nine stage weights in a separate reviewed run configuration.',
        covariance='Existing catalog shared-pick covariance rejects type2 and must not silently treat CC as independent or noiseless.',
        solver_invocations=0,original_inputs_changed=False,run_configuration_created=False,
        limitations=['Prepared inputs only: no inverse or forward validation is implied.',
                     'Empirical CC squared row weighting does not establish inverse-variance calibration or exact manuscript weighting.',
                     'Retain all native sidecars and rejected measurement records; no new pair/channel selection is applied.'],
        output_sha256={str(p.relative_to(output)):sha(p) for p in output.rglob('*') if p.is_file()})
    (output/'preparation_manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ('catalog-dir','export-summary','export-review','output'):
        parser.add_argument('--'+flag,required=True,type=Path)
    args=parser.parse_args(); result=run(args.catalog_dir,args.export_summary,args.export_review,args.output)
    print(json.dumps({key:result[key] for key in ('status','original_catalog_rows','appended_cc_rows','prepared_rows')}))
