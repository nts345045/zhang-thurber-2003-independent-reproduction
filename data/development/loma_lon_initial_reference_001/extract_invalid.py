#!/usr/bin/env python3
"""Extract unchanged failed references with complete native metadata; no arithmetic rerun."""
import csv
import gzip
import hashlib
import itertools
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

summary = json.loads((HERE / 'summary.json').read_text())
ledger = json.loads((HERE / 'execution.json').read_text())
assert ledger['status'] == 'completed' and ledger['summary_sha256'] == sha(HERE / 'summary.json')
names = ('references.csv.gz', 'certificates.jsonl.gz')
for name in names:
    assert sha(HERE / name) == summary['output_sha256'][name]
failed = []
with gzip.open(str(HERE / names[0]), 'rt', newline='') as cf, gzip.open(str(HERE / names[1]), 'rt') as jf:
    for row, line in itertools.zip_longest(csv.DictReader(cf), jf):
        assert row is not None and line is not None
        record = json.loads(line)
        assert int(row['pair_index']) == record['pair_index']
        if row['reference_valid'] != '1':
            assert row['time_s'] == ''
            assert all(row['source_d' + axis + '_s_per_km'] == '' for axis in 'xyz')
            failed.append(dict(saved_row=row, unchanged_certificate=record))
assert [int(x['saved_row']['pair_index']) for x in failed] == summary['invalid_reference_pair_indices']
result = dict(status='failed_references_preserved', numerical_rerun=False,
    scope='Exact extraction from frozen full batch; invalid selected times and derivatives remain blank',
    summary_sha256=sha(HERE / 'summary.json'), execution_sha256=sha(HERE / 'execution.json'),
    source_sha256=sha(Path(__file__)), input_sha256={n:sha(HERE / n) for n in names}, cases=failed)
(HERE / 'invalid_cases.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
print('Preserved {} invalid reference(s)'.format(len(failed)))
