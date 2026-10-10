#!/usr/bin/env python3
"""Read-only checks for the frozen, unchanged-B saved-seed replay."""
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
    assert sha(OUT / 'prepared.json') == 'abdc3673d888fa209236196b7d303dc748c7659f8251988d955b8cbaa98418bd'
    assert prepared['status'] == 'prepared_seed_loaded_B_only'
    assert prepared['launcher_sha256'] == 'a8d633e7acce1b906d66e47a7665eb60d1f82bd9d9b1f5beb616fdd796e2dcdc'
    assert sha(ROOT / 'diagnostics/run_seed_loaded_b.py') == prepared['launcher_sha256']
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
    assert prepared['original_retention_predicate'] == 'sy > 1e-14'
    assert prepared['positive_variant_allowed'] is False
    old = ROOT / 'data/development/loma_outer_accumulation_native_001'
    for name in ('src/core.hpp', 'diagnostics/observed_optimizer.hpp'):
        assert sha(OUT / 'source' / name) == sha(old / 'source' / name)
    before = (old / 'source/diagnostics/check_ray_stopping.cpp').read_text().splitlines(True)
    after = (OUT / 'source/diagnostics/check_ray_stopping.cpp').read_text().splitlines(True)
    diff = ''.join(difflib.unified_diff(before, after, fromfile='frozen_B/check_ray_stopping.cpp', tofile='seed_loaded_B/check_ray_stopping.cpp'))
    assert diff == (OUT / 'seed_loader_driver.diff').read_text()
    for name, digest in prepared['expected_old_table_sha256'].items():
        assert sha(old / name) == digest
    controls = ROOT / 'data/development/seeded_retention_controls_001'
    review = load(controls / 'review.json')
    assert sha(controls / 'review.json') == 'c443b3ec43a1278413e089fa63f54d60c18d19c571e6dffade3c2c43e8d3deb5'
    assert review['status'] == 'passed' and review['summary_sha256'] == sha(controls / 'summary.json')
    with (OUT / 'identified_ray.csv').open(newline='') as stream:
        context = list(csv.DictReader(stream))
    assert context == [prepared['native_context']] and len(context[0]) == 199
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
                full_native_context_fields=199, unchanged_B_core_and_observer=True,
                exact_driver_diff_verified=True, positive_variant_allowed=False,
                scope='Concrete frozen-source and metadata review only; no compilation or native execution.')


if __name__ == '__main__':
    print(json.dumps(check(), indent=2, allow_nan=False))
