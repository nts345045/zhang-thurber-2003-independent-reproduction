#!/usr/bin/env python3
"""Verify the isolated retention change against the proven saved-seed baseline."""
import csv
import difflib
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def load(path):
    return json.loads(path.read_text())


def check():
    prepared = load(OUT / 'prepared.json')
    assert sha(OUT / 'prepared.json') == '79562a3f2485633c84342571a77fd94f39d32e4a6d7e64247808a82ef628e60f'
    assert prepared['status'] == 'prepared_positive_curvature_diagnostic'
    assert prepared['launcher_sha256'] == 'a15355fed9b1bee795e06bc7f53e8a04783d10f7e9bfaf982ca7d43c67173982'
    assert sha(ROOT / 'diagnostics/run_positive_curvature.py') == prepared['launcher_sha256']
    assert sha(OUT / 'launcher.py') == prepared['launcher_sha256']
    for name, digest in prepared['input_sha256'].items():
        assert sha(ROOT / name) == digest, name
    for name, digest in prepared['prepared_file_sha256'].items():
        assert sha(OUT / name) == digest, name
    for name, digest in prepared['source_sha256'].items():
        assert sha(OUT / 'source' / name) == digest, name
    assert sha(Path(prepared['compiler'])) == prepared['compiler_sha256']
    assert (prepared['path_spacing_km'], prepared['field_spacing_km'], prepared['maximum_updates'], prepared['threads']) == (.03125, .125, 1000, 1)
    assert (prepared['time_limit_s'], prepared['source_vector_limit_s_per_km']) == (2.5e-5, 3e-6)
    assert prepared['baseline_retention_predicate'] == 'sy > 1e-14'
    assert prepared['diagnostic_retention_predicate'] == 'sy > 0'
    assert prepared['safe_general_retention_rule_claimed'] is False
    old = ROOT / prepared['seed_loaded_B_directory']
    review = load(old / 'review.json')
    assert sha(old / 'review.json') == prepared['seed_loaded_B_review_sha256'] == 'c49e9ab30fca87597df9ac7a8f5f70536383e8c3be6d4b694e58d73ebdeb5155'
    assert review['status'] == 'passed' and review['summary_sha256'] == sha(old / 'summary.json')
    baseline = load(old / 'summary.json')
    assert baseline['original_five_tables_byte_identical']
    assert baseline['results'] == prepared['baseline_results']
    changed = []
    for name in prepared['source_sha256']:
        before, after = old / 'source' / name, OUT / 'source' / name
        if sha(before) == sha(after):
            continue
        changed.append(name)
        if name in ('src/core.hpp', 'diagnostics/observed_optimizer.hpp'):
            a, b = before.read_text(), after.read_text()
            marker = '      if (sy > 1e-14) {'
            assert a.count(marker) == 1 and b == a.replace(marker, '      if (sy > 0) {', 1)
        else:
            assert name == 'diagnostics/extracted_retention.hpp'
            assert before.read_text() == 'bool extracted_retention(double sy) { return sy > 1e-14; }\n'
            assert after.read_text() == 'bool extracted_retention(double sy) { return sy > 0; }\n'
    assert set(changed) == {'src/core.hpp', 'diagnostics/observed_optimizer.hpp', 'diagnostics/extracted_retention.hpp'}
    for name in ('initial_grid.csv', 'curvature_initialization.csv', 'curvature_seed_metadata.csv'):
        assert sha(OUT / 'inputs' / name) == sha(old / 'inputs' / name)
    for name, digest in prepared['expected_old_table_sha256'].items():
        assert sha(old / name) == digest
    with (OUT / 'identified_ray.csv').open(newline='') as stream:
        context = list(csv.DictReader(stream))
    assert context == [prepared['native_context']] and context[0] == baseline['native_context']
    assert len(context[0]) == 199
    for name in ('curvature_initialization.csv', 'curvature_seed_metadata.csv'):
        metadata = load(OUT / 'inputs' / (name + '.identifiers.json'))
        assert metadata['native_context'] == context[0]
        assert metadata['file_sha256'] == sha(OUT / 'inputs' / name)
        assert metadata['context_sha256'] == sha(OUT / 'identified_ray.csv')
    return dict(status='passed', prepared_sha256=sha(OUT / 'prepared.json'),
                launcher_sha256=prepared['launcher_sha256'], checker_sha256=sha(Path(__file__)),
                input_pins_verified=len(prepared['input_sha256']),
                prepared_pins_verified=len(prepared['prepared_file_sha256']),
                source_pins_verified=len(prepared['source_sha256']),
                full_native_context_fields=199, changed_source_files=changed,
                mathematical_change='Two original/observed retention literals only; the third changed header is the unused control predicate.',
                unchanged_seed_loader_and_settings=True, unchanged_accuracy_limits=True,
                safe_general_retention_rule_claimed=False,
                scope='Concrete frozen-source, baseline-parity and metadata review only; no compilation or native execution.')


if __name__ == '__main__':
    print(json.dumps(check(), indent=2, allow_nan=False))
