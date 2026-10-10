#!/usr/bin/env python3
"""Attach native identifiers to a completed static formula document; no arithmetic."""
import argparse
import csv
import hashlib
import json
from pathlib import Path


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--verify-existing', action='store_true')
    args = parser.parse_args()
    out = Path(args.output).resolve()
    summary = json.loads((out/'summary.json').read_text())
    if summary['status'] != 'completed_static_component_original_flags_preserved':
        raise ValueError('Static calculation is not complete')
    for name in ['exact_baseline_formulas.json', 'native_context.csv']:
        if sha(out/name) != summary['output_sha256'][name]:
            raise ValueError('Changed numerical/context artifact: '+name)
    with (out/'native_context.csv').open(newline='') as f:
        rows = list(csv.DictReader(f))
    context = summary['native_context']
    if len(context) != 199 or rows != [context] or context['observation_index'] != '24104':
        raise ValueError('Missing full native context')
    result = dict(file='exact_baseline_formulas.json',file_sha256=sha(out/'exact_baseline_formulas.json'),
                  join_key=None,join_value='24104',
                  join_basis='The entire JSON document describes one fixed run/pair, not a row-indexed table. point_coordinates_q entries are source node0, first interior node1, second interior node2 in that order.',
                  run_id='fmm_0.031250_1000',observation_index='24104',native_context=context,
                  context_csv='native_context.csv',context_sha256=sha(out/'native_context.csv'),
                  basis='Authoritative simulation geometry provenance; no simulated pick identity or new forward result.')
    path=out/'exact_baseline_formulas.json.identifiers.json'
    if args.verify_existing:
        if json.loads(path.read_text()) != result:
            raise ValueError('Existing attachment differs from native mapping')
    else:
        with path.open('x') as f:
            json.dump(result,f,indent=2)
            f.write('\n')
    print(json.dumps(dict(status='verified_existing' if args.verify_existing else 'attached',
                          summary_sha256=sha(out/'summary.json'),attachment_sha256=sha(path))))


if __name__=='__main__':
    main()
