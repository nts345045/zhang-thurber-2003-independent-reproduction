#!/usr/bin/env python3
"""Check the documented bulk interface using the same two previously retrieved pilot windows."""
import hashlib
import json
from pathlib import Path
import acquire


def main():
    picks, unused = acquire.context()
    native = []
    for name in ('probe_identity.json', 'partner_probe_identity.json'):
        old = json.loads((acquire.HERE.parent / 'pilot_001' / name).read_text())
        rows = [p for p in picks if p['original_observation_index'] == str(old['original_observation_index'])]
        if len(rows) != 1 or any(rows[0][k] != v for k, v in old['original_observation'].items()):
            raise ValueError('Established pilot identity changed')
        native.append(rows[0])
    lines = [' '.join([p['network_code'], p['station_code'], p['location_code'] or '--', p['channel_code'],
        p['request_start_utc'].rstrip('Z'), p['request_end_utc'].rstrip('Z')]) for p in native]
    body = 'format=json\n' + '\n'.join(lines) + '\n'
    batch = dict(stage='pilot_post_control', batch=0, request_body=body,
        metadata=dict(endpoint='https://service.ncedc.org/fdsnws/availability/1/query',
            request_sha256=hashlib.sha256(body.encode()).hexdigest(),
            rows=[dict(request_line=n + 2, channel_seed_id=p['channel_seed_id'],
                channel_fdsn_source_id=p['channel_fdsn_source_id'], metadata_epoch_start=p['metadata_epoch_start'],
                metadata_epoch_end=p['metadata_epoch_end'], native_pick_rows=[p['original_observation_index']],
                provider_pick_resource_ids=[p['pick_i_resource_id']], source_metadata_sha256=p['channel_source_sha256'])
                for n, p in enumerate(native)]))
    raw, meta = acquire.retrieve(batch, picks, True)
    parsed = acquire.availability(raw, batch, picks) if meta['http_status'] == 200 else None
    result = dict(scope='Supported bulk-protocol control on exactly the two previously retrieved windows; no replacement measurement pair',
        status='passed' if parsed is not None and not parsed['missing_pick_rows'] else 'stopped_for_access_clarification',
        http_status=meta['http_status'], raw_file=str(raw.relative_to(acquire.HERE)), raw_sha256=acquire.sha(raw),
        parsed=parsed, source_sha256=acquire.sha(Path(__file__)), acquisition_source_sha256=acquire.sha(Path(acquire.__file__)))
    acquire.save(acquire.HERE / 'pilot_bulk_availability_001.json', result)
    print(json.dumps(result, indent=2))
    if result['status'] != 'passed':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
