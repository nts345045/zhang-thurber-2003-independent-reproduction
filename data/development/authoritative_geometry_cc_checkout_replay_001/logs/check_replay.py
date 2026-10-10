"""Compare two closed, committed-input plot replays without plotting again."""
import gzip
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):
    return json.loads(path.read_text())

def main():
    assert not (ROOT/'logs/comparison.json').exists()
    exported = read(ROOT/'logs/export.json')
    for name, item in exported['files'].items():
        path = ROOT/name
        assert not path.is_symlink() and sha(path) == item['sha256'], name
    loma = ROOT/'data/development/loma_geometry_figure_001'
    loma_new = ROOT/'tmp/loma_geometry_figure_rebuild_001'
    old, new = read(loma/'manifest.json'), read(loma_new/'manifest.json')
    assert old['status'] == new['status'] == 'passed'
    for key in ('figure_status', 'counts', 'checks', 'grid_axes_km', 'plot_axes_limits_km',
                'plot_distance_aspect', 'old_figure02_sha256', 'original_native_source_sha256'):
        assert new[key] == old[key], key
    for name, digest in new['input_sha256'].items():
        assert sha(ROOT/name) == digest, name
    assert new['output_sha256'] == old['output_sha256']
    for name, digest in old['output_sha256'].items():
        assert sha(loma_new/name) == sha(loma/name) == digest, name
    cc = ROOT/'data/development/native_cc_spatial_support_001/render_002'
    cc_new = ROOT/'tmp/cc_spatial_replot_001'
    prior, replay = read(cc/'summary.json'), read(cc_new/'summary.json')
    assert replay['status'] == prior['status'] == 'completed_saved_input_plot'
    for key in ('source_sha256', 'input_source_sha256', 'checks', 'counts', 'accepted_channel_counts',
                'channel_saved_positions_km', 'axes', 'versions', 'caption', 'limits',
                'new_measurements', 'solver_calls', 'waveform_requests', 'graph_recomputations'):
        assert replay[key] == prior[key], key
    for name, digest in replay['input_source_sha256'].items():
        assert sha(ROOT/name) == digest, name
    equality = {}
    for name, digest in replay['output_sha256'].items():
        assert sha(cc_new/name) == digest, name
        equality[name] = digest == prior['output_sha256'][name]
        if name != 'cc_spatial_support.pdf':
            assert equality[name], name
    old_ids = gzip.decompress((cc/'plot_identifiers.json.gz').read_bytes())
    new_ids = gzip.decompress((cc_new/'plot_identifiers.json.gz').read_bytes())
    assert old_ids == new_ids
    ids = json.loads(new_ids.decode())
    assert len(ids['catalog_events']) == 1092 and len(ids['receiver_epochs']) == 22
    assert len(ids['accepted_pairs']) == 98
    old_pdf = (cc/'cc_spatial_support.pdf').read_bytes()
    new_pdf = (cc_new/'cc_spatial_support.pdf').read_bytes()
    date = rb'/(?:CreationDate|ModDate)\s*\(D:[^)]*\)'
    old_dates, new_dates = re.findall(date, old_pdf), re.findall(date, new_pdf)
    assert old_dates and len(old_dates) == len(new_dates)
    assert re.sub(date, b'/DATE', old_pdf) == re.sub(date, b'/DATE', new_pdf)
    result = dict(status='passed', checked_utc=datetime.utcnow().isoformat()+'Z',
        checker_sha256=sha(Path(__file__).resolve()), commit=exported['commit'],
        export_sha256=sha(ROOT/'logs/export.json'), unchanged_exported_files=len(exported['files']),
        loma_manifest_sha256=sha(loma_new/'manifest.json'), loma_counts=new['counts'],
        loma_nine_outputs_byte_exact=new['output_sha256'], cc_summary_sha256=sha(cc_new/'summary.json'),
        cc_counts=replay['counts'], cc_checks=replay['checks'], cc_output_byte_equality=equality,
        cc_complete_identifiers_byte_exact=True, cc_plotted_coordinates_byte_exact=True,
        cc_pdf=dict(archived_sha256=sha(cc/'cc_spatial_support.pdf'), replay_sha256=sha(cc_new/'cc_spatial_support.pdf'),
                    archived_dates=[x.decode() for x in old_dates], replay_dates=[x.decode() for x in new_dates],
                    only_date_fields_differ=True),
        output_sha256={str(p.relative_to(ROOT)):sha(p) for folder in (loma_new,cc_new)
                       for p in sorted(folder.rglob('*')) if p.is_file()},
        limits='Clean committed-input plot replay using an existing external runtime; not a clean software installation, solver validation or end-to-end project rebuild.',
        numerical_solver_calls=0, waveform_requests=0, plotting_calls_in_checker=0)
    with (ROOT/'logs/comparison.json').open('x') as f:
        json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:result[k] for k in ('status','unchanged_exported_files','loma_counts','cc_counts','cc_output_byte_equality','cc_pdf')}))

if __name__ == '__main__':
    main()
