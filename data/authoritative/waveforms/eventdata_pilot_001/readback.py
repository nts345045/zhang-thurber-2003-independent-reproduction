#!/usr/bin/env python3
"""Read the fixed two-record request evidence only; never issue a request."""
import csv
import hashlib
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
load = lambda p: json.loads(p.read_text())


def require(ok, message):
    if not ok:
        raise ValueError(message)


def main():
    plan = load(HERE / 'plan.json')
    summary = load(HERE / 'acquisition_summary.json')
    for name, digest in plan['input_sha256'].items():
        require(sha(ROOT / name) == digest, 'Changed original input: ' + name)
    require(summary['plan_sha256'] == sha(HERE / 'plan.json'), 'Plan changed')
    for stage in ('prepare', 'docs', 'fetch'):
        ledger = load(HERE / (stage + '_execution.json'))
        require(ledger['status'] == 'completed' and ledger['return_code'] == 0 and
                ledger['source_sha256'] == sha(HERE / 'acquire.py'), 'Stage/source changed')
    for name, expected in [('native_picks.csv', plan['native_picks']),
                           ('native_pair.csv', [plan['native_pair']]),
                           ('native_events.csv', plan['native_events']),
                           ('native_epoch.csv', [plan['native_epoch']])]:
        with (HERE / name).open() as stream:
            require(list(csv.DictReader(stream)) == expected, 'Native table changed: ' + name)
    doc = load(HERE / 'current_documentation_review.json')
    require(doc['status'] == 'supported_syntax_verified' and
            doc['source_sha256'] == sha(HERE / 'current_eventdata.html') and
            summary['documentation_review_sha256'] == sha(HERE / 'current_documentation_review.json'), 'Document changed')
    require(summary['status'] == 'completed_two_declared_requests' and len(summary['results']) == 2,
            'Request roster changed')
    for name in ['current_eventdata.html', 'event_12434.response', 'event_12437.response']:
        raw = HERE / name
        meta = load(HERE / (name + '.provenance.json'))
        identities = load(HERE / (name + '.identifiers.json'))
        request_ids = load(HERE / (name + '.request.txt.identifiers.json'))
        request = HERE / (name + '.request.txt')
        require(meta['sha256'] == identities['source_sha256'] == sha(raw), 'Raw bytes changed')
        require(meta['request_sha256'] == request_ids['request_sha256'] == sha(request), 'Request changed')
        require(meta['byte_count'] == raw.stat().st_size and meta['source_sha256'] == sha(HERE / 'acquire.py'), 'Raw/source metadata changed')
        require(identities['request_context'] == request_ids['request_context'], 'Request/native context changed')
        context = identities['request_context']
        require(context['plan_sha256'] == sha(HERE / 'plan.json') and
                context['native_picks'] == plan['native_picks'] and context['native_pair'] == plan['native_pair'] and
                context['native_events'] == plan['native_events'] and context['native_epoch'] == plan['native_epoch'], 'Actual plan/native binding changed')
        if name == 'current_eventdata.html':
            require(meta['http_status'] == 200 and meta['method'] == 'GET' and not request.read_bytes(), 'Documentation request changed')
            continue
        pick, event = context['requested_pick'], context['requested_event']
        expected = ('eventid=' + event['provider_event_eventid'] + '\ncatalog=NCSS\nNC CMC -- EHZ ' +
                    pick['request_start_utc'].rstrip('Z') + ' ' + pick['request_end_utc'].rstrip('Z') + '\n').encode()
        require(request.read_bytes() == expected and pick['location_code'] == '' and pick['channel_seed_id'] == 'NC.CMC..EHZ', 'Native selection altered')
        require(meta['request_url'] == meta['final_url'] == 'https://service.ncedc.org/ncedcws/eventdata/1/query' and
                meta['method'] == 'POST' and meta['http_status'] == 204 and raw.read_bytes() == b'', 'Unexpected response or route')
        outcome = [r for r in summary['results'] if r['raw_file'] == name]
        require(len(outcome) == 1 and outcome[0]['outcome'] == 'provider_returned_no_data' and
                all(outcome[0][k] == v for k, v in meta.items()), 'Terminal outcome changed')
    for key in ('measurements_added', 'calibration_corrections', 'catalog_edits'):
        require(summary[key] == 0, 'Unsupported scientific outcome')
    require(summary['availability_asserted'] is False, 'Invented availability claim')
    inventory = {str(p.relative_to(HERE)): sha(p) for p in sorted(HERE.iterdir()) if p.is_file()}
    output = dict(status='passed', scope='Saved native/request/hash/outcome readback only; no queries or sample/CC computation',
        original_input_pins_verified=len(plan['input_sha256']), raw_responses=3, event_requests=2,
        event_http_statuses=[204, 204], event_waveform_bytes=0, measurements_added=0,
        all_native_values_retained=True, actual_plan_documentation_and_request_binding_verified=True,
        source_sha256=sha(Path(__file__)), file_sha256=inventory,
        limitation='Exact event/channel/time no-data outcomes do not establish historical waveform absence')
    with (HERE / 'readback.json').open('x') as stream:
        json.dump(output, stream, indent=2); stream.write('\n')
    print(json.dumps({k: v for k, v in output.items() if k != 'file_sha256'}, indent=2))


if __name__ == '__main__':
    main()
