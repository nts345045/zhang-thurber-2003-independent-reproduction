#!/usr/bin/env python3
"""Preserve the identified graph of accepted measurements without new filtering."""
import argparse
from collections import Counter, defaultdict
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
PREFIX = 'original_catalog_'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_table(path, rows, fields):
    with path.open('xb') as raw:
        stream = gzip.GzipFile(filename='', fileobj=raw, mode='wb', mtime=0) if path.suffix == '.gz' else raw
        with io.TextIOWrapper(stream, encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
            writer.writeheader(); writer.writerows(rows)


def run(measurements, output):
    measurements, output = measurements.resolve(), output.resolve()
    measurements.relative_to(ROOT); output.relative_to(ROOT)
    if output.exists():
        raise ValueError('Use a fresh output directory')
    summary_path = measurements / 'summary.json'
    review_path = measurements / 'independent_measurement_review.json'
    table_path = measurements / 'identified_measurements.csv.gz'
    summary = json.loads(summary_path.read_text())
    review = json.loads(review_path.read_text())
    if review['status'] != 'passed' or review['measurements_summary_sha256'] != sha(summary_path):
        raise ValueError('Require the hash-bound independent measurement review')
    if sha(table_path) != summary['output_sha256'][table_path.name]:
        raise ValueError('Measurement table hash differs')
    pins = {str(p.relative_to(ROOT)): sha(p) for p in (summary_path, review_path, table_path, Path(__file__).resolve())}
    with gzip.open(str(table_path), 'rt', newline='') as f:
        reader = csv.DictReader(f); fields = reader.fieldnames; rows = list(reader)
    if len(rows) != summary['retained_original_catalog_pairs'] or dict(Counter(r['measurement_status'] for r in rows)) != summary['status_counts']:
        raise ValueError('Full measurement roster differs')
    accepted = [r for r in rows if r['measurement_status'] == 'accepted_discrete_measurement']
    identities, indices, adjacency, pairs = {}, {}, defaultdict(set), Counter()
    measurement_ids, original_rows = set(), set()
    for row in accepted:
        if row['measurement_id'] in measurement_ids or row[PREFIX+'original_observation_index'] in original_rows:
            raise ValueError('Duplicate measurement/original row ID')
        measurement_ids.add(row['measurement_id']); original_rows.add(row[PREFIX+'original_observation_index'])
        endpoints = []
        for side in ('i', 'j'):
            event = row[PREFIX+'event_'+side+'_resource_id']
            origin = row[PREFIX+'origin_'+side+'_resource_id']
            index = int(row[PREFIX+side])
            if not event or not origin or identities.get(event, (index, origin)) != (index, origin) or indices.get(index, event) != event:
                raise ValueError('Ambiguous event/origin/index identity')
            identities[event] = (index, origin); indices[index] = event; endpoints.append(event)
        a, b = endpoints
        if a == b:
            raise ValueError('Self event pair')
        adjacency[a].add(b); adjacency[b].add(a)
        pairs[tuple(sorted(endpoints))] += 1
    components, seen = [], set()
    for event in sorted(adjacency, key=lambda e: identities[e][0]):
        if event in seen:
            continue
        todo, members = [event], []; seen.add(event)
        while todo:
            node = todo.pop(); members.append(node)
            for neighbor in sorted(adjacency[node], key=lambda e: identities[e][0], reverse=True):
                if neighbor not in seen:
                    seen.add(neighbor); todo.append(neighbor)
        components.append(sorted(members, key=lambda e: identities[e][0]))
    membership = []
    for number, members in enumerate(components):
        for event in members:
            index, origin = identities[event]
            membership.append(dict(original_event_index=index, event_resource_id=event,
                origin_resource_id=origin, local_component_id='cc-component-{:03d}'.format(number),
                component_event_count=len(members), unique_pair_degree=len(adjacency[event])))
    membership.sort(key=lambda r: r['original_event_index'])
    assert len(membership) == len(identities) == len(seen)
    assert sum(len(v) for v in adjacency.values()) == 2*len(pairs)
    output.mkdir(parents=True); (output/'source').mkdir()
    shutil.copyfile(str(Path(__file__).resolve()), str(output/'source'/Path(__file__).name))
    write_table(output/'accepted_measurements.csv.gz', accepted, fields)
    write_table(output/'event_membership.csv', membership,
        ['original_event_index','event_resource_id','origin_resource_id','local_component_id','component_event_count','unique_pair_degree'])
    with gzip.open(str(output/'accepted_measurements.csv.gz'), 'rt', newline='') as f:
        assert list(csv.DictReader(f)) == accepted
    for name, digest in pins.items():
        if sha(ROOT/name) != digest:
            raise ValueError('Input changed during audit: '+name)
    result = dict(status='completed_identified_connectivity_audit', input_source_sha256=pins,
        retained_original_catalog_pairs=len(rows), accepted_measurements=len(accepted),
        unique_event_pairs=len(pairs), accepted_event_count=len(identities),
        accepted_measurements_per_pair_distribution=dict(Counter(pairs.values())),
        component_count=len(components), component_event_counts_descending=sorted([len(c) for c in components],reverse=True),
        maximum_unique_pair_degree=max([len(v) for v in adjacency.values()] or [0]),
        accepted_channel_counts=dict(Counter((r[PREFIX+'channel_seed_id']+' | '+r[PREFIX+'channel_fdsn_source_id']) for r in accepted)),
        all_accepted_rows_preserved_exactly=True, new_filters_or_thresholds=False,
        measurements_or_solver_inputs_changed=False,
        limitations=['CC-only undirected event graph, not the combined catalog-plus-CC graph or a Jacobian rank test.',
                     'One receiver per accepted pair does not establish independent three-dimensional relative-location constraints.',
                     'Local component labels are derived identifiers, not provider resource IDs.'],
        output_sha256={str(p.relative_to(output)):sha(p) for p in output.rglob('*') if p.is_file()})
    (output/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('accepted_measurements','unique_event_pairs','accepted_event_count','component_count')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--measurements',type=Path,default=Path('data/development/native_waveform_cc_001'))
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();run(args.measurements,args.output)
