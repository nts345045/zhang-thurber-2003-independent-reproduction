#!/usr/bin/env python3
"""Check the compiled report against the closed accepted-update evidence."""
import collections
import csv
import hashlib
import json
import re
import tarfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
DELIVERY = ROOT/'data/development/hayward_accepted_update_delivery_001'
PINS = {}


def pin(path, expected=None):
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert expected is None or digest == expected, str(path)
    PINS[str(path.relative_to(ROOT))] = digest
    return digest


def read(path, expected=None):
    pin(path, expected)
    return json.loads(path.read_text())


def main():
    assert __debug__
    assert not (OUT/'validation.json').exists()
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
    prior = read(ROOT/'data/development/cmj_contact_evaluator_report_001/compile.json')
    assert compilation['previous_report_sha256'] == prior['report_sha256']
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

    verification = read(DELIVERY/'verification.json',
        '025e527f86444681cf07c974ba384152e4baadada2a7971e0e7d82b41d950ea8')
    assert verification['status'] == 'passed'
    assert [x['stage'] for x in verification['commands']] == ['package', 'restore', 'replot']
    assert all(x['return_code'] == 0 and x['child_reaped'] for x in verification['commands'])
    for name, digest in verification['delivery_artifact_sha256'].items():
        pin(ROOT/name, digest)
    assert verification['replot_statistics_exactly_equal']
    assert verification['replot_byte_equality']['accepted_update_1.png']
    assert verification['pdf_only_difference']['all_other_bytes_equal']
    packaging = read(DELIVERY/'packaging.json', verification['packaging_sha256'])
    members = read(DELIVERY/'members.json', packaging['members_sha256'])['members']
    assert len(members) == packaging['member_count'] == 54
    archive = DELIVERY/'evidence.tar.gz'
    pin(archive, packaging['archive_sha256'])
    assert packaging['archive_sha256'] == packaging['deterministic_reconstruction_sha256']
    with tarfile.open(str(archive), 'r:gz') as stream:
        def saved(name):
            content = stream.extractfile(name).read()
            assert hashlib.sha256(content).hexdigest() == members[name]['sha256']
            return json.loads(content.decode())
        statistics = saved('tmp/hayward_accepted_update_001_figures/statistics.json')
        trial = saved('tmp/hayward_trial3_observation_001/receipt.json')
    accepted = trial['accepted_trial']
    assert accepted['status'] == 'accepted' and accepted['step_fraction'] == '0.125'
    assert trial['objective_basis'] == ('sum of squared fixed row-multiplied observation residuals '
        'plus final log-slowness smoothing; solve damping is not added to this objective')
    assert [format(float(accepted[x]), '.5f') for x in ('objective_before', 'objective_after')] == ['1812.15659', '1409.16490']
    assert [format(statistics['grid_delta_v_layer'][x]['display'], '.5f') for x in ('minimum', 'maximum')] == ['-0.25806', '0.07275']
    assert [format(x, '.5f') for x in statistics['horizontal_displacement_display_km']] == ['0.00181', '0.33425']
    assert format(statistics['spatial_displacement_display_km'][1], '.5f') == '0.55600'
    assert statistics['event_count'] == 1092 and statistics['plotted_nodes'] == 77
    assert statistics['plotted_depth_km_exact'] == '8' and len(statistics['detail_event_ids']) == 125
    for extension in ('pdf', 'png'):
        figure = ROOT/('figures/hayward_accepted_update_001.'+extension)
        identifiers = read(Path(str(figure)+'.identifiers.json'))
        pin(figure, identifiers['figure_sha256'])
        assert identifiers['archive_sha256'] == packaging['archive_sha256']
        assert identifiers['members_manifest_sha256'] == packaging['members_sha256']
        for field in ('full_figure_identifiers', 'full_native_mapping', 'plot_summary'):
            assert members[identifiers[field+'_member']]['sha256'] == identifiers[field+'_sha256']

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
    assert len(paths['figures']) == 28
    panels = list(csv.DictReader((ROOT/'data/panel_audit.csv').open()))
    pin(ROOT/'data/panel_audit.csv')
    panel_json = read(ROOT/'data/panel_audit.json')
    counts = dict(collections.Counter(x['status'] for x in panels))
    assert counts == {'independently reproduced': 1, 'partially reproduced': 61}
    assert [(x['panel'], x['status']) for x in panels] == [(x['panel'], x['status']) for x in panel_json]
    for name in ('report/panel_table.tex', 'report/panel_details.tex'):
        pin(ROOT/name, prior['tex_source_sha256'][name])
    prose = ' '.join((ROOT/'report/recovery_checkpoint.tex').read_text().split())
    for phrase in ('data residuals and log-slowness smoothing', 'history RMS describes the preupdate',
                   'run remains incomplete', 'lacks the complete Jacobian export',
                   'do not change the manuscript panel', 'source-derivative accuracy remain unestablished'):
        assert phrase in prose, phrase
    with (OUT/'path_inventory.json').open('x') as stream:
        json.dump(paths, stream, indent=2); stream.write('\n')
    result = dict(status='passed', checked_utc=datetime.utcnow().isoformat()+'Z',
        checker_sha256=pin(Path(__file__)), compile_sha256=pin(OUT/'compile.json'),
        report_sha256=compilation['report_sha256'], panel_counts=counts,
        path_counts={key: len(value) for key, value in paths.items()}, warnings=warnings,
        archive_members=len(members), accepted_trial=accepted,
        path_inventory_sha256=pin(OUT/'path_inventory.json'), input_sha256=PINS,
        solver_calls=0, integration_calls=0,
        limits='Intermediate accepted state only; no post-update RMS, final convergence, first-arrival, source-accuracy, full-DD resolution or panel promotion.')
    with (OUT/'validation.json').open('x') as stream:
        json.dump(result, stream, indent=2); stream.write('\n')
    print(json.dumps({key: result[key] for key in ('status', 'report_sha256', 'panel_counts', 'path_counts', 'archive_members')}))


if __name__ == '__main__':
    main()
