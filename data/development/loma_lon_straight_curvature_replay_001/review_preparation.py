#!/usr/bin/env python3
"""Independent saved-input/source readback; no compile, ray call or network."""
import csv
import gzip
import hashlib
import json
from pathlib import Path
import sys
import tarfile

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def rows(path):
    opener = gzip.open if str(path).endswith('.gz') else open
    with opener(str(path), 'rt') as stream:
        return list(csv.DictReader(stream))


def main():
    prepared_path = HERE / sys.argv[1]
    p = json.loads(prepared_path.read_text())
    counts = {}
    for key, base in [('original_sha256', ROOT), ('runtime_sha256', Path('/')),
                      ('output_sha256', HERE), ('source_sha256', HERE)]:
        for name, expected in p[key].items():
            assert sha(base / name) == expected, (key, name)
        counts[key] = len(p[key])
    manifest = json.loads((HERE / 'inputs/preflight_run_manifest.json').read_text())
    with tarfile.open(str(HERE / 'inputs/preflight_source.tar.gz'), 'r:gz') as archive:
        members = archive.getmembers()
        assert set(m.name for m in members) == set(manifest['source_sha256'])
        for member in members:
            content = archive.extractfile(member).read()
            assert hashlib.sha256(content).hexdigest() == manifest['source_sha256'][member.name]
            assert (HERE / 'source/old' / member.name).read_bytes() == content
            if member.name != 'src/core.hpp':
                assert (HERE / 'source/D' / member.name).read_bytes() == content
    candidate = ROOT / 'data/development/usable_curvature_integration_prepared_001/after'
    for name in ('src/core.hpp', 'src/usable_ray_curvature.hpp'):
        assert (HERE / 'source/D' / name).read_bytes() == (candidate / name).read_bytes()
    base = ROOT / 'data/development/loma_lon_initial_accuracy_001'
    source = rows(base / 'comparison.csv.gz')
    status = rows(base / 'inputs/preflight/dd_preflight_ray_status.csv.gz')
    references = rows(base / 'inputs/reference/references.csv.gz')
    selected = rows(HERE / 'inputs/selected_comparison.csv')
    selected_status = rows(HERE / 'inputs/selected_status.csv')
    selected_refs = rows(HERE / 'inputs/selected_reference.csv')
    contexts = json.loads((HERE / 'inputs/native_context.json').read_text())
    events, stations = rows(HERE / 'inputs/initial_events.csv'), rows(HERE / 'inputs/stations.csv')
    assert len(source) == len(status) == len(references) == 37648
    assert len(events) == 724 and len(stations) == 52
    assert len(selected) == len(selected_status) == len(selected_refs) == len(contexts) == 2
    for n, pair in enumerate((8670, 8674)):
        i, k = divmod(pair, 52)
        assert selected[n] == source[pair]
        assert selected_status[n] == status[pair]
        assert selected_refs[n] == references[pair]
        assert contexts[n]['pair_index'] == pair
        assert contexts[n]['source_native'] == events[i]
        assert contexts[n]['receiver_native'] == stations[k]
        assert contexts[n]['saved_comparison_row'] == source[pair]
        assert status[pair]['ray_selected_fmm_seed'] == '0'
        assert status[pair]['ray_direct_seed_time'] == status[pair]['ray_time']
        assert all(references[pair][key] == '1' for key in
                   ('reference_complete', 'reference_valid', 'candidate_count'))
        assert references[pair]['near_tie_count'] == '1'  # The winning candidate is included.
        assert (i, k) == (166, (38, 42)[n])
    review_path = ROOT / 'data/development/loma_lon_initial_accuracy_review_001/review.json'
    review = json.loads(review_path.read_text())
    assert review['status'] == 'passed_saved_readback'
    assert review['summary_sha256'] == sha(base / 'summary.json')
    for name in ('build', 'results', 'execution.json', 'summary.json'):
        assert not (HERE / name).exists(), 'Execution already started: ' + name
    result = {'status': 'passed', 'prepared_sha256': sha(prepared_path),
              'checker_sha256': sha(Path(__file__)), 'checked_hash_counts': counts,
              'archived_source_members': len(members), 'native_pairs': [8670, 8674],
              'native_context_sha256': sha(HERE / 'inputs/native_context.json'),
              'terminal_accuracy_review_sha256': sha(review_path),
              'scope': 'Independent saved source/input/hash/native joins; no compiler, ray, reference or network execution.'}
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
