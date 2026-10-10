"""Independent exact crossing roster and closed-file readback; no evaluator."""
from fractions import Fraction as Q
import csv
import gzip
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
FACE = ROOT / 'data/development/hayward_cmj_face_action_001'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def main():
    assert __debug__ and not (HERE / 'review.json').exists()
    prepared = read(HERE / 'prepared.json')
    summary = read(HERE / 'summary.json')
    receipt = read(HERE / 'execution_receipt.json')
    assert receipt['status'] == 'passed' and receipt['return_code'] == 0 and receipt['child_reaped']
    assert receipt['summary_sha256'] == sha(HERE / 'summary.json')
    assert receipt['prepared_sha256'] == summary['prepared_sha256'] == sha(HERE / 'prepared.json')
    for base, records in ((ROOT, prepared['input_sha256']), (HERE, prepared['output_sha256']), (HERE, receipt['output_sha256'])):
        for name, digest in records.items():
            assert sha(base / name) == digest, name
    axes = [[Q(x) for x in axis] for axis in read(FACE / 'model_provenance.json')['axes_exact_rational']]
    with (FACE / 'inputs/original_paths.csv').open(newline='') as stream:
        rows = list(csv.DictReader(stream))
    identities = read(HERE / 'native_contexts.json')
    assert identities == summary['native_contexts']
    counts = []
    for identity, brief in zip(identities, summary['cases']):
        event = identity['event']
        path = [tuple(Q(float(row[k])) for k in 'xyz') for row in rows if int(row['event']) == event]
        with gzip.open(str(HERE / brief['result_file']), 'rt') as stream:
            result = json.load(stream)
        for key in ('event', 'station', 'native_context', 'catalog_uses'):
            assert result[key] == brief[key] == identity[key]
        records = result['edge_records']
        assert len(records) == len(path) - 1 == brief['edges']
        crossings = 0
        for edge, record in enumerate(records):
            a, b = path[edge:edge + 2]
            assert record['edge'] == edge and tuple(map(Q, record['a_exact'])) == a and tuple(map(Q, record['b_exact'])) == b
            expected = {(k, j): (plane - a[k]) / (b[k] - a[k])
                        for k, axis in enumerate(axes) if a[k] != b[k]
                        for j, plane in enumerate(axis) if min(a[k], b[k]) < plane < max(a[k], b[k])}
            observed = {(p['axis'], p['plane_index']): p for p in record['crossed_or_inserted_planes']}
            assert len(observed) == len(record['crossed_or_inserted_planes']) and set(observed) == set(expected)
            assert not record['core_skips_whole_segment'] and not record['duplicate_binary_cut_count']
            for key, parameter in expected.items():
                p = observed[key]
                binary = float.fromhex(p['binary_parameter_hex'])
                assert Q(p['exact_parameter']) == parameter and Q(p['parameter_rounding_error']) == Q(binary) - parameter
                assert p['core_inserted'] and p['exact_open_segment_crossing'] and not p['spurious_extra_cut'] and not p['omission_reasons']
                assert 1e-10 < binary < 1 - 1e-10
            crossings += len(expected)
        assert crossings == brief['exact_crossings'] == brief['core_plane_insertions'] == 30
        assert not result['omitted_exact_crossings'] and not result['spurious_extra_cuts']
        counts.append(dict(event=event, station=identity['station'], edges=len(records), exact_crossings=crossings))
    assert len(counts) == 2 and [c['event'] for c in counts] == [981, 987]
    review = dict(status='passed', reviewer='root', checker_sha256=sha(Path(__file__)),
                  summary_sha256=sha(HERE / 'summary.json'), execution_receipt_sha256=sha(HERE / 'execution_receipt.json'),
                  native_contexts=identities, cases=counts,
                  scope='Independent original-coordinate exact plane roster and saved rounding-error joins; terminal pins checked. No evaluator, integration, compiled parity or gradient accuracy claim.')
    with (HERE / 'review.json').open('x') as stream:
        json.dump(review, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps(dict(status='passed', review_sha256=sha(HERE / 'review.json'), cases=counts)))


if __name__ == '__main__':
    main()
