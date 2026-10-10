#!/usr/bin/env python3
"""Read back the frozen delivery; no action evaluation, trace, plot or compile."""
import csv
import hashlib
import json
import re
import subprocess
import tarfile
from collections import Counter
from fractions import Fraction as Q
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
USED = {}


def need(value, message):
    if not value:
        raise ValueError(message)


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def pin(name, expected=None):
    value = digest(ROOT / name)
    need(expected is None or value == expected, 'Hash mismatch: ' + name)
    USED[name] = value
    return value


def read(name):
    pin(name)
    return json.loads((ROOT / name).read_text())


def table(name):
    pin(name)
    with (ROOT / name).open(newline='') as f:
        return list(csv.DictReader(f))


def bounds(value):
    a, b = Q(value['lower_rational']), Q(value['upper_rational'])
    need(a <= b, 'Reversed saved interval')
    return a, b


def package(name):
    base = 'data/development/' + name + '/'
    s, r = read(base + 'summary.json'), read(base + 'review.json')
    need(r['status'].startswith('passed'), 'Unreviewed package: ' + name)
    need(not r.get('material_issue_found', False), 'Material issue: ' + name)
    need(r.get('summary_sha256', r.get('controls_summary_sha256')) ==
         USED[base + 'summary.json'], 'Stale package review: ' + name)
    return s


def main():
    receipt_name = 'data/development/loma_failed_search_delivery.json'
    receipt = read(receipt_name)
    need(len(receipt['sha256']) == 270, 'Delivery inventory changed')
    for name, expected in receipt['sha256'].items():
        pin(name, expected)
    need(not any('loma_outer_accumulation' in x for x in receipt['sha256']),
         'Incomplete accumulator experiment included')
    commit_range = '402cfb9..5a7132b'
    commits = subprocess.check_output(['git', 'log', '--format=%H', commit_range],
                                     cwd=str(ROOT)).decode().splitlines()
    changed = subprocess.check_output(['git', 'diff', '--name-only', '402cfb9',
                                      '5a7132b'], cwd=str(ROOT)).decode().splitlines()
    need(len(commits) == 5 and len(changed) == 258, 'Completed commit inventory')
    need(set(changed) <= set(receipt['sha256']), 'Unpinned completed evidence')
    proc = subprocess.Popen(['git', 'archive', '--format=tar', '5a7132b', '--'] + changed,
                            cwd=str(ROOT), stdout=subprocess.PIPE)
    committed = set()
    with tarfile.open(fileobj=proc.stdout, mode='r|') as archive:
        for member in archive:
            if not member.isfile():
                continue
            h = hashlib.sha256()
            stream = archive.extractfile(member)
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                h.update(block)
            need(h.hexdigest() == receipt['sha256'][member.name],
                 'Committed evidence differs: ' + member.name)
            committed.add(member.name)
    need(proc.wait() == 0 and committed == set(changed), 'Committed member readback')

    node = package('loma_node_action_001')
    replay = package('loma_failed_search_3426_001')
    exact = package('loma_failed_trial_exact_001')
    accum = package('loma_trial_accumulation_001')
    mesh = package('loma_boundary_endpoint_mesh_controls_001')
    figure = read('figures/diagnostics/loma_failed_trials.json')
    context = replay['native_context']
    for s in (node, exact, accum, figure):
        need(s['native_context'] == context, 'Native context changed')
    identity_fields = ('source_event_resource_id', 'source_origin_resource_id',
                       'receiver_channel_seed_id', 'receiver_channel_fdsn_source_id',
                       'receiver_metadata_epoch_start', 'receiver_metadata_epoch_end')
    identities = {k: context[k] for k in identity_fields}
    need(all(identities.values()) and context['receiver_location_code'] == '',
         'Missing identities or changed empty location')
    identified = table('data/development/loma_failed_search_3426_001/identified_ray.csv')
    need(len(identified) == 1 and identified[0] == context, 'Identified native row')
    sidecars = 0
    for name in receipt['sha256']:
        if name.endswith('.csv.identifiers.json') and any('/' + d + '/' in name for d in
                ('loma_failed_search_3426_001', 'loma_trial_accumulation_001')):
            s = read(name)
            need(s['native_context'] == context, 'Sidecar native context: ' + name)
            pin(str(Path(name).parent / s['file']), s['file_sha256'])
            sidecars += 1

    need(node['focus_node'] == 484, 'Focus node changed')
    node_z = bounds(node['exact_node_gradient_xyz'][2])
    node_error = bounds(node['exact_minus_saved_gradient_xyz'][2])
    need(abs(float(node_z[0]) - 1.03120815e-5) <= 5e-14, 'Reported node derivative')
    need(max(abs(x) for x in node_error) <= Q('4.59e-21'), 'Node gradient error')
    need(float(node['original_focus_node_fd']['numerical_gradient']) < 0,
         'Original crossing finite difference sign')
    need(any(not x['crosses_depth_break'] and x['action_change_sign'] == 'strict_decrease'
             for x in node['probes']), 'No within-piece decrease')
    for name, expected in replay['expected_old_table_sha256'].items():
        pin('data/development/loma_failed_search_3426_001/' + name, expected)
        pin('data/development/loma_initial_failure_3426_001/' + name, expected)
    need(replay['all_five_prior_numerical_tables_byte_identical'] and
         replay['recorded_failed_trials'] == 24, 'Replay parity')
    need(exact['original_local_flag'] == accum['original_local_flag'] == '0',
         'Original failed flag changed')
    need(exact['maximum_component_gradient_discrepancy_s_per_km'] <= 1.17e-16,
         'Reported full gradient discrepancy')

    need(len(exact['trials']) == 24, 'Trial support changed')
    binary, lower, widths = [], [], []
    for i, t in enumerate(exact['trials']):
        d = t['original_decision']
        need(int(d['trial_index']) == i and float(d['step']) == 2.0 ** (-i),
             'Actual evaluated step differs from trial index')
        need(d['binary64_accepted'] == '0' and d['valid'] == '1' and
             d['merged_nodes'] == '0', 'Trial status changed')
        a, b = bounds(t['exact_action_change_s'])
        need(b < 0, 'Uncertified decrease')
        for key in ('exact_saved_slope_armijo', 'exact_gradient_armijo'):
            need(t[key] == 'certified_pass' and bounds(t[key + '_gap_s'])[1] <= 0,
                 'Armijo classification')
        binary.append(float(d['trial_action_s']) - float(d['cached_base_action_s']))
        lower.append(float(a))
        widths.append(float(b - a))
    need(all(x > 0 for x in binary), 'Original increase signs')
    need(abs(lower[0] + 6.76195e-15) < 5e-21 and
         abs(lower[-1] + 3.36321e-22) < 5e-28 and
         abs(binary[0] - 1.24345e-14) < 5e-20, 'Rounded reported action changes')
    dec = read('data/development/loma_failed_trial_exact_review_001/decimal_checks.json')
    need({(r['trial_index'], r['decimal_precision']) for r in dec['checks']} ==
         {(0, 80), (0, 100), (23, 80), (23, 100)}, 'Decimal comparison support')
    for r in dec['checks']:
        a, b = bounds(exact['trials'][r['trial_index']]['exact_action_change_s'])
        need(a <= Q(r['action_change_s']) <= b, 'Decimal value outside enclosure')
    need(figure['trial_index'] == list(range(24)) and
         figure['original_binary64_action_change_s'] == binary and
         figure['exact_action_change_lower_display_s'] == lower, 'Plotted values')
    pin('data/development/loma_failed_trial_exact_001/summary.json', figure['source_summary_sha256'])
    pin('data/development/loma_failed_trial_exact_001/review.json', figure['source_review_sha256'])
    pin('plot_loma_failed_trials.py', figure['plot_source_sha256'])
    for name, expected in figure['figure_sha256'].items():
        pin('figures/diagnostics/' + name, expected)
    need("linthresh=1e-22" in (ROOT / 'plot_loma_failed_trials.py').read_text(),
         'Figure linear interval differs from caption')

    methods = ('exact_sum_of_original_segment_changes_s', 'paired_extended_segment_change_s')
    pass_counts = {}
    for method in methods:
        flags = []
        for c, t in zip(accum['comparisons'], exact['trials']):
            value = Q(c['methods'][method]['value_decimal'])
            target = bounds(t['exact_saved_slope_armijo_target_s'])[0]
            flags.append(value <= target)
            need(flags[-1] == c['methods'][method]['approximate_armijo_pass'],
                 'Approximate accumulation decision')
        pass_counts[method] = sum(flags)
    need(list(pass_counts.values()) == [17, 21], 'Reported accumulation counts')
    need(accum['comparisons'][0]['methods'][methods[0]]['approximate_armijo_pass'],
         'First-step outer summation result')
    need(all(Q(c['methods'][methods[1]]['value_decimal']) >= 0
             for c in accum['comparisons'][-3:]), 'Last three accumulation signs')
    totals = table('data/development/loma_trial_accumulation_001/totals.csv')
    need({r['extended_mantissa_bits'] for r in totals} == {'64'}, 'Significand width')

    optimized = []
    need(mesh['passing_checks'] == mesh['total_checks'] == 836 and
         not mesh['native_execution_performed'], 'Mesh controls scope')
    for c in mesh['controls']:
        need(all(x['passed'] for x in c['checks']), 'Failed algebra/parity control')
        rows = table('data/development/loma_boundary_endpoint_mesh_controls_001/' +
                     c['name'] + '/comparisons.csv')
        optimized.extend(r for r in rows if r['family'] == 'optimized')
    false_flags = sum(r['converged'] == '0' for r in optimized)
    source_failures = sum(r['scientific_source_pass'] == 'False' for r in optimized)
    need((len(optimized), false_flags, source_failures) == (80, 2, 32),
         'Negative endpoint totals')
    small = [r for r in optimized if r['run_id'] == 'positive_guide' and
             float(r['epsilon_requested_km']) == 2.0 ** -22]
    need(len(small) == 5 and all(r['iterations'] == '0' and
         3.2e-9 < float(r['projected_gradient']) < 3.4e-9 and
         r['scientific_source_pass'] == 'False' for r in small), 'Small-step example')

    local_links = []
    for name in receipt['sha256']:
        if not name.endswith('.md'):
            continue
        for target in re.findall(r'\]\(([^)]+)\)', (ROOT / name).read_text()):
            if re.match(r'^(https?://|mailto:|#)', target):
                continue
            target = target.split('#')[0]
            need((ROOT / name).parent.joinpath(target).exists(), 'Missing link: ' + target)
            local_links.append([name, target])
    report = (ROOT / 'report/recovery_checkpoint.tex').read_text()
    tex_paths = re.findall(r'\\path\{([^}]+)\}', report)
    for name in tex_paths:
        need((ROOT / name).exists(), 'Missing report path: ' + name)
    for name in re.findall(r'\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}', report):
        need((ROOT / 'report' / name).exists(), 'Missing report figure: ' + name)
    for text in ('does not establish convergence of a corrected optimizer',
                 'The proposed native extension is not executed.',
                 'two false local flags and 32 source-vector accuracy failures'):
        need(text in re.sub(r'\s+', ' ', report), 'Missing scientific limitation: ' + text)

    compile_base = 'data/development/loma_failed_search_report_001/'
    ledger = read(compile_base + 'execution.json')
    need(ledger['status'] == 'completed' and ledger['passes'] ==
         receipt['validation']['pdflatex_passes'], 'Compile ledger mismatch')
    for p in ledger['passes']:
        need(p['return_code'] == 0, 'LaTeX failure')
        for stream in ('stdout', 'stderr'):
            name = compile_base + 'pass%d_%s.log' % (p['number'], stream)
            pin(name, p[stream + '_sha256'])
            text = (ROOT / name).read_text()
            need(not re.search(r'(^!|undefined|Overfull|LaTeX Error|Fatal error)',
                               text, re.I | re.M), 'Actionable compile diagnostic')
    for name, expected in ledger['source_sha256'].items():
        pin(name, expected)
    pdf_hash = pin('report/report.pdf', ledger['pdf_sha256'])
    info = subprocess.check_output(['pdfinfo', 'report/report.pdf'], cwd=str(ROOT)).decode()
    need(re.search(r'Pages:\s+103\b', info) and
         (ROOT / 'report/report.pdf').stat().st_size == ledger['pdf_bytes'] ==
         receipt['validation']['pdf_bytes'],
         'PDF extent changed')
    text = subprocess.check_output(['pdftotext', '-f', '29', '-l', '31',
                                   'report/report.pdf', '-'], cwd=str(ROOT)).decode()
    need(len(text) > 3000 and all(x in text for x in ('836', '24', '3426')),
         'New PDF pages are unreadable or missing claims')
    panels = dict(Counter(r['status'] for r in table('data/panel_audit.csv')))
    need(panels == receipt['validation']['panel_statuses'] ==
         {'independently reproduced': 1, 'partially reproduced': 27, 'not reproduced': 34},
         'Manuscript panel status changed')
    for name, expected in list(USED.items()):
        need(digest(ROOT / name) == expected, 'Input changed during review: ' + name)
    result = dict(status='passed', material_issue_found=False,
        delivery_manifest_sha256=USED[receipt_name], delivery_members_verified=270,
        completed_commits=commits, completed_commit_members_pinned=len(changed),
        checker_sha256=digest(Path(__file__).resolve()), pdf_sha256=pdf_hash,
        pdf_pages=103, pdf_bytes=ledger['pdf_bytes'], compile_passes=2,
        compile_diagnostics_clear=True, pdf_text_pages_checked=[29, 30, 31],
        visual_review_attribution='Root separately inspected final pages 29–31; this checker validates PDF text and hashes.',
        native_identifiers=identities, native_context_fields_matched=len(context),
        checked_identifier_sidecars=sidecars, exact_passing_trials=24,
        first_exact_action_change_s=lower[0], first_binary64_action_change_s=binary[0],
        last_exact_action_change_s=lower[-1], max_interval_width_s=max(widths),
        accumulation_pass_counts=pass_counts,
        endpoint_checks=836, optimized_endpoint_records=80,
        endpoint_false_flags=false_flags, endpoint_source_failures=source_failures,
        local_markdown_links_checked=local_links, report_paths_checked=tex_paths,
        panel_statuses=panels, input_sha256=USED,
        scope='Delivery hash/link/native and saved arithmetic readback. No action evaluation, numerical rerun, tracing, plotting, compile, optimization, inverse run or network request.',
        findings=['Reported exact decreases and original binary64 rejections are both preserved.',
                  'Accumulation results describe these saved polygons; no corrected optimizer is accepted.',
                  'Endpoint algebra/parity success is explicitly separated from retained local and source-accuracy failures.',
                  'Incomplete outer-accumulator A/B evidence is excluded.'],
        limitations=['Independent numerical reviews are consumed by exact hashes, not repeated.',
                     'Local filesystem link targets are checked; external URLs and Markdown fragment anchors are not queried.',
                     'No manuscript panel promotion, production correction or inverse-result acceptance follows from this delivery.'])
    with (HERE / 'review.json').open('x') as f:
        json.dump(result, f, indent=2, sort_keys=True)
        f.write('\n')
    print(json.dumps({'status': result['status'], 'members': 270,
                      'review_sha256': digest(HERE / 'review.json')}))


if __name__ == '__main__':
    main()
