#!/usr/bin/env python3
"""Validate the report and closed input-geometry figures; no numerical calls."""
import collections
import csv
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
PINS = {}


def pin(path, expected=None):
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert expected is None or digest == expected, str(path)
    PINS[str(path.relative_to(ROOT)) if ROOT in path.parents else str(path)] = digest
    return digest


def read(path, expected=None):
    pin(path, expected)
    return json.loads(path.read_text())


def esc(value):
    # Same pure text escaping as analyze.py; no analysis module is imported.
    return str(value).replace('_', r'\_').replace('&', r'\&').replace('%', r'\%').replace('#', r'\#')


def main():
    assert __debug__ and not (OUT/'validation.json').exists()
    compilation = read(OUT/'compile.json')
    assert compilation['status'] == 'completed'
    assert [x['return_code'] for x in compilation['commands']] == [0, 0]
    pin(ROOT/'report/report.pdf', compilation['report_sha256'])
    pin(ROOT/'README.md', compilation['readme_sha256'])
    pin(ROOT/'FAILURE_SUMMARY.md', compilation['failure_summary_sha256'])
    assert len(compilation['tex_source_sha256']) == 16
    for name, digest in compilation['tex_source_sha256'].items():
        pin(ROOT/name, digest)
    for name, digest in compilation['output_sha256'].items():
        pin(OUT/name, digest)
    execution = read(OUT/'compile_execution_receipt.json')
    assert execution['status'] == 'completed_and_reaped'
    assert execution['return_code'] == 0 and execution['child_reaped']
    assert execution['compile_sha256'] == pin(OUT/'compile.json')
    assert execution['report_sha256'] == compilation['report_sha256']
    pin(OUT/'compile.py', execution['compile_source_sha256'])
    prior = read(ROOT/'data/development/hayward_accepted_update_report_001/compile.json')
    prior_validation = read(ROOT/'data/development/hayward_accepted_update_report_001/validation.json')
    assert prior_validation['status'] == 'passed'
    assert compilation['previous_report_sha256'] == prior['report_sha256']
    preservation = read(OUT/'preservation.json')
    assert preservation['prior_compile_sha256'] == pin(ROOT/'data/development/hayward_accepted_update_report_001/compile.json')
    assert preservation['prior_validation_sha256'] == pin(ROOT/'data/development/hayward_accepted_update_report_001/validation.json')
    for name, digest in preservation['published_figures_sha256'].items():
        pin(ROOT/name, digest)
    baseline = read(ROOT.parents[1]/'data/hayward/run_manifest.json', preservation['main_baseline_manifest_sha256'])
    assert baseline['sha256'] == preservation['main_baseline_sha256'] and len(baseline['sha256']) == 13
    for name, digest in baseline['sha256'].items():
        pin(ROOT.parents[1]/name, digest)
    for name, digest in preservation['runtime_sha256'].items():
        pin(Path(name), digest)
    warnings = {}
    for number in (1, 2):
        lines = (OUT/('pass%d_report.log' % number)).read_text().splitlines()
        assert not any(re.search(r'^!|Overfull', line) for line in lines)
        warnings[str(number)] = [line for line in lines if re.search('warning:', line, re.I)]
        known = 'pdfTeX warning: pdflatex (file ../figures/location_errors.pdf): PDF inclusion: '
        assert warnings[str(number)].count(known) == 1
        assert any('multiple pdfs with page group included in a single page' in line for line in lines)
        if number == 2:
            assert warnings[str(number)] == [known]
            assert not any('undefined' in line.lower() for line in lines)

    loma = ROOT/'data/development/loma_geometry_figure_001'
    manifest = read(loma/'manifest.json', '0a6d04b0f8858ab813faf2e199e733662c38149fb054cf6853c3769823aa11f1')
    review = read(loma/'validation.json')
    assert manifest['status'] == review['status'] == 'passed'
    assert review['manifest_sha256'] == pin(loma/'manifest.json')
    assert review['rebuild_from_package_inputs'] and not review['simulation_archive_required']
    assert review['rebuild_output_hashes_exact'] == manifest['output_sha256']
    for name, digest in manifest['input_sha256'].items():
        pin(ROOT/name, digest)
    for name, digest in manifest['output_sha256'].items():
        pin(loma/name, digest)
    assert manifest['counts'] == dict(events=724, receiver_epochs=52, stations=52,
        horizontal_grid_nodes=48, saved_grid_nodes=288, blank_location_codes=40,
        absent_provider_channel_source_ids=52)
    assert review['identities'] == dict(unique_events=724, unique_origins=724,
        unique_receiver_epochs=52, full_fdsn_codes_checked=52,
        preserved_blank_locations=40, provider_channel_ids_absent_and_preserved=52)
    for name, digest in manifest['original_native_source_sha256'].items():
        pin(loma/'inputs'/Path(name).name, digest)
    for name, digest in manifest['old_figure02_sha256'].items():
        pin(ROOT/name, digest)

    cc = ROOT/'data/development/native_cc_spatial_support_001'
    summary = read(cc/'render_002/summary.json', 'ae46b96cc708e78c60d9aab4dfe54ca284afb130e807bcdb3ca9e788b9d57aea')
    plot_execution = read(cc/'execution_receipt.json', '0e6a1aea9ae085ac9dcaded8826b32681ff93820b5d882707775fa23e1c068b5')
    assert plot_execution['status'] == 'passed' and plot_execution['return_code'] == 0 and plot_execution['child_reaped']
    assert plot_execution['summary_sha256'] == pin(cc/'render_002/summary.json')
    assert summary['counts'] == plot_execution['counts'] == dict(accepted_events=103,
        accepted_pairs=98, catalog_events=1092, cc_only_components=32,
        cross_epoch_pairs=38, receiving_channels=4, used_receiver_epochs=22)
    assert summary['accepted_channel_counts'] == {'NC.CBR.10.EHZ': 19, 'NC.JPR.02.EHZ': 75, 'NC.JSB.10.EHZ': 3, 'NC.JSF.10.EHZ': 1}
    for name, digest in summary['input_source_sha256'].items():
        pin(ROOT/name, digest)
    for name, digest in summary['output_sha256'].items():
        pin(cc/'render_002'/name, digest)
    for name, digest in plot_execution['output_sha256'].items():
        pin(cc/name, digest)
    visual = read(cc/'visual_review.json', plot_execution['visual_review_sha256'])
    assert visual['status'] == 'passed'
    dependencies = read(cc/'checkout_dependencies.json')
    assert dependencies['consumed_summary_sha256'] == pin(cc/'render_002/summary.json')
    assert dependencies['missing_native_inputs'] == [] and dependencies['tracked_external_input_count'] == 12
    for name, item in dependencies['tracked_external_inputs'].items():
        pin(ROOT/name, item['sha256'])
    for ext in ('pdf', 'png'):
        side = read(cc/('render_002/cc_spatial_support.'+ext+'.identifiers.json'))
        assert side['input_source_sha256'] == summary['input_source_sha256']
        pin(cc/'render_002'/side['full_identifiers'], side['full_identifiers_sha256'])
        pin(cc/'render_002'/side['plotted_table'], side['plotted_table_sha256'])

    paths = {'markdown_links': [], 'tex_paths': [], 'figures': []}
    for name in ('README.md', 'FAILURE_SUMMARY.md'):
        for link in re.findall(r'\[[^\]]*\]\(([^)]+)\)', (ROOT/name).read_text()):
            if re.match(r'(?:https?://|mailto:|#)', link):
                continue
            path = link.split('#')[0]
            assert (ROOT/path).exists(), path
            paths['markdown_links'].append({'document': name, 'path': path})
    for name in compilation['tex_source_sha256']:
        source = ROOT/name
        for literal in re.findall(r'\\path\{([^}]+)\}', source.read_text()):
            if literal.startswith('quakeml:'):
                continue
            resolved = ROOT/literal
            if not resolved.exists():
                assert '/' not in literal.rstrip('/'), literal
                resolved = ROOT/'data/development'/literal
            assert resolved.exists(), literal
            paths['tex_paths'].append({'document': name, 'path': str(resolved.relative_to(ROOT))})
        for literal in re.findall(r'\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}', source.read_text()):
            resolved = next((p.resolve() for p in (source.parent/literal, ROOT/'figures'/literal) if p.exists()), None)
            assert resolved is not None, literal
            paths['figures'].append({'document': name, 'path': str(resolved.relative_to(ROOT)), 'sha256': pin(resolved)})
    assert len(paths['figures']) == 29
    panels = list(csv.DictReader((ROOT/'data/panel_audit.csv').open()))
    pin(ROOT/'data/panel_audit.csv')
    assert panels == read(ROOT/'data/panel_audit.json')
    pin(OUT/'prior_panel_audit.csv', preservation['prior_panel_audit_sha256'])
    old_panels = list(csv.DictReader((OUT/'prior_panel_audit.csv').open()))
    assert [new['panel'] for new, old in zip(panels, old_panels) if new != old] == ['2']
    counts = dict(collections.Counter(x['status'] for x in panels))
    assert len(panels) == len(old_panels) == 62
    assert counts == {'independently reproduced': 1, 'partially reproduced': 61}
    panel2 = next(row for row in panels if row['panel'] == '2')
    assert panel2['data_command'] == panel2['plot_command'] == 'python3 diagnostics/plot_loma_geometry.py --output tmp/FRESH_loma_geometry'
    assert 'Figure 3 retains the historical random-layout calculations.' in panel2['limitation']
    table = (ROOT/'report/panel_table.tex').read_text()
    details = (ROOT/'report/panel_details.tex').read_text()
    audit_md = (ROOT/'FIGURE_AUDIT.md').read_text()
    for row in panels:
        assert '{} & {} & {}. {}'.format(esc(row['panel']), esc(row['quantity']), esc(row['status']), esc(row['limitation'])) in table
        assert esc(row['limitation']) in details
        assert row['limitation'] in audit_md
    for field in ('data_command', 'plot_command'):
        assert panel2[field] in details
    for name in ('audit.py', 'analyze.py', 'FIGURE_AUDIT.md'):
        pin(ROOT/name)
    prose = ' '.join((ROOT/'report/report.tex').read_text().split())
    cc_prose = ' '.join((ROOT/'report/recovery_checkpoint.tex').read_text().split())
    for phrase in ('724 catalog-derived', 'show 52 identified receiver epochs', 'Crosses show 48 horizontal grid nodes',
                   'historical recovery panels use the earlier random layout', 'input geometry, not an inverse result'):
        assert phrase in prose, phrase
    for phrase in ('98 accepted normalized waveform differences', 'all 1,092 catalog events',
                   '103 events in accepted pairs', 'four receiving channels', 'all 22 used receiver epochs',
                   '38 cross-epoch pairs', 'combined catalog-plus-CC input remains uninverted'):
        assert phrase in cc_prose, phrase
    pdf_text = ' '.join((OUT/'report.txt').read_text().split())
    assert 'Partial reconstruction of manuscript Figure 2' in pdf_text
    assert 'Observed spatial support of the 98 accepted' in pdf_text
    pages = int(re.search(r'^Pages:\s+(\d+)', (OUT/'pdfinfo.txt').read_text(), re.M).group(1))
    with (OUT/'path_inventory.json').open('x') as stream:
        json.dump(paths, stream, indent=2); stream.write('\n')
    result = dict(status='passed', checked_utc=datetime.utcnow().isoformat()+'Z',
        checker_sha256=pin(Path(__file__).resolve()), compile_sha256=pin(OUT/'compile.json'),
        report_sha256=compilation['report_sha256'], pages=pages, panel_counts=counts,
        path_counts={key: len(value) for key, value in paths.items()}, warnings=warnings,
        loma_counts=manifest['counts'], cc_counts=summary['counts'],
        unchanged_published_figure_files=len(preservation['published_figures_sha256']),
        unchanged_main_baseline_pins=len(baseline['sha256']), changed_audit_panels=['2'],
        path_inventory_sha256=pin(OUT/'path_inventory.json'), input_sha256=PINS,
        solver_calls=0, integration_calls=0, plotting_calls=0,
        limits='Input geometry and observational support only; historical random-layout recovery unchanged; no panel promotion.')
    with (OUT/'validation.json').open('x') as stream:
        json.dump(result, stream, indent=2); stream.write('\n')
    print(json.dumps({key: result[key] for key in ('status', 'report_sha256', 'pages', 'panel_counts', 'path_counts')}))


if __name__ == '__main__':
    main()
