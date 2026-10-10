#!/usr/bin/env python3
"""Invented overlay, exact-restore and corruption-rejection controls."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

import package_loma_variant as variant

ROOT = Path(__file__).resolve().parents[1]
A = variant.archive


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def comparison(left, right, base):
    a, b = variant.snapshot(left), variant.snapshot(right)
    return dict(status='passed', all_physical_simulation_outputs_byte_identical=all(a[n] == b[n] for n in variant.PHYSICAL),
        all_original_hashes_and_inventories_reverified_at_end=(a == variant.snapshot(left) and b == variant.snapshot(right)),
        members={n: dict(lom=a.get(n), lon=b.get(n)) for n in sorted(set(a) | set(b))},
        base_package_manifest_sha256=A.info(base / 'manifest.json')['sha256'],
        scope='Invented two-event/two-receiver fixture comparison only')


def main():
    if not __debug__:
        raise RuntimeError('Run checks without Python -O')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True); parser.add_argument('--work', required=True)
    args = parser.parse_args()
    out, work = [(ROOT / n).resolve() for n in (args.output, args.work)]
    for p in (out, work):
        p.relative_to(ROOT); p.mkdir(parents=True)
    original = ROOT / 'data/development/analytic_simulation_launcher_002/invented_simulation'
    reviewed = ROOT / 'data/development/loma_simulation_packaging_001/fixture_review.json'
    before = variant.snapshot(original)
    left, right = work / 'base_run', work / 'variant_run'
    shutil.copytree(str(original), str(left)); shutil.copytree(str(original), str(right))
    (left / 'base_only_note.txt').write_text('Invented informational base-only file.\n')
    (right / 'variant_only_note.txt').write_text('Invented informational variant-only file.\n')
    # Initial velocity does not enter this analytic-truth observation fixture.
    lines = (right / 'initial_grid.csv').read_text().splitlines()
    fields = lines[1].split(','); fields[-1] = str(float(fields[-1]) + .01)
    lines[1] = ','.join(fields); (right / 'initial_grid.csv').write_text('\n'.join(lines) + '\n')
    with (right / 'run.cfg').open('a') as stream:
        stream.write('# Invented overlay fixture: changed starting grid, same truth observations.\n')
    prepared = json.loads((right / 'analytic_truth_manifest.json').read_text())
    for name in ('initial_grid.csv', 'run.cfg'):
        prepared['prepared_sha256'][name] = A.info(right / name)['sha256']
    prepared['fixture_note'] = 'Derived invented variant to test byte-preserving storage; no new simulation or real data'
    write(right / 'analytic_truth_manifest.json', prepared)
    manifest = json.loads((right / 'simulation_run_manifest.json').read_text())
    manifest['prepared_manifest_sha256'] = A.info(right / 'analytic_truth_manifest.json')['sha256']
    write(right / 'simulation_run_manifest.json', manifest)
    ledger = json.loads((right / 'simulation_execution.json').read_text())
    ledger['analytic_truth_manifest_sha256'] = manifest['prepared_manifest_sha256']
    ledger['output_sha256']['simulation_run_manifest.json'] = A.info(right / 'simulation_run_manifest.json')['sha256']
    write(right / 'simulation_execution.json', ledger)
    command = ['python3', str(ROOT / 'diagnostics/review_loma_analytic_simulation.py'), '--data', str(right),
               '--output', str(right / 'independent_simulation_review.json'), '--reviewer', 'invented_overlay_fixture']
    process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (out / 'fixture_audit_stdout.json').write_bytes(process.stdout)
    (out / 'fixture_audit_stderr.log').write_bytes(process.stderr)
    if process.returncode:
        raise RuntimeError('Invented full output audit failed; preserve the captured error')
    base = out / 'base_package'
    A.package(left, reviewed, base, 4096)
    compared = out / 'comparison.json'; write(compared, comparison(left, right, base))
    review = right / 'independent_simulation_review.json'
    package = out / 'variant_package'
    result = variant.create(right, review, compared, base, package)
    checks = [dict(name='invented completed variant uses exact base members and small replacements', passed=True, **result)]
    restored = work / 'restored'
    result = variant.restore(package, base, restored)
    assert variant.snapshot(restored) == variant.snapshot(right)
    assert not (restored / 'base_only_note.txt').exists() and (restored / 'variant_only_note.txt').exists()
    checks.append(dict(name='fresh restore exactly matches full variant inventory including additions and removals', passed=True, **result))

    def reject(name, call):
        try:
            call()
        except (ValueError, FileExistsError, FileNotFoundError, OSError, KeyError) as error:
            checks.append(dict(name=name, passed=True, error_type=type(error).__name__, error=str(error)))
        else:
            raise AssertionError('Unexpected acceptance: ' + name)

    reject('existing overlay directory', lambda: variant.create(right, review, compared, base, package))
    reject('existing restore directory', lambda: variant.restore(package, base, restored))
    reject('restore nested inside base', lambda: variant.restore(package, base, base / 'nested'))
    reject('restore nested inside overlay', lambda: variant.restore(package, base, package / 'nested'))
    bm = json.loads((base / 'manifest.json').read_text())
    for label in ('changed', 'missing', 'extra'):
        altered = work / ('base_' + label); shutil.copytree(str(base), str(altered))
        part = altered / bm['parts'][0]['file']
        if label == 'changed':
            payload = bytearray(part.read_bytes()); payload[0] ^= 1; part.write_bytes(payload)
        elif label == 'missing': part.unlink()
        else: (altered / 'unexpected.txt').write_text('extra')
        reject(label + ' base file', lambda path=altered: variant.verify(package, path))
    vm = json.loads((package / 'manifest.json').read_text())
    replacement = next(iter(vm['stored_files']))
    for label in ('changed', 'missing', 'extra'):
        altered = work / ('overlay_' + label); shutil.copytree(str(package), str(altered))
        path = altered / 'files' / replacement
        if label == 'changed': path.write_bytes(path.read_bytes() + b'changed')
        elif label == 'missing': path.unlink()
        else: (altered / 'unexpected.txt').write_text('extra')
        reject(label + ' overlay file', lambda path=altered: variant.verify(path, base))
    altered = work / 'edited_manifest'; shutil.copytree(str(package), str(altered))
    value = json.loads((altered / 'manifest.json').read_text()); value['scope'] = 'changed'
    write(altered / 'manifest.json', value)
    reject('edited overlay manifest with stale execution hash', lambda: variant.verify(altered, base))
    unsafe = work / 'unsafe_member'; shutil.copytree(str(package), str(unsafe))
    value = json.loads((unsafe / 'manifest.json').read_text()); value['members']['../escape'] = value['members'].pop(replacement)
    write(unsafe / 'manifest.json', value)
    write(unsafe / 'execution.json', dict(status='completed', manifest_sha256=A.info(unsafe / 'manifest.json')['sha256']))
    reject('unsafe member even with matching manifest hash', lambda: variant.restore(unsafe, base, work / 'unsafe_output'))
    assert not (work / 'unsafe_output').exists()
    stale = json.loads(compared.read_text()); stale['members']['initial_grid.csv']['lon']['sha256'] = '0' * 64
    write(work / 'stale_comparison.json', stale)
    reject('stale compared source bytes', lambda: variant.create(right, review, work / 'stale_comparison.json', base, work / 'stale_output'))
    failed = dict(stale, status='failed'); write(work / 'failed_comparison.json', failed)
    reject('failed comparison', lambda: variant.create(right, review, work / 'failed_comparison.json', base, work / 'failed_output'))
    reject('review outside retained run inventory', lambda: variant.create(right, reviewed, compared, base, work / 'external_review'))
    process = subprocess.run(['python3', str(ROOT / 'diagnostics/package_loma_variant.py'), 'restore',
        '--package', str(package), '--base', str(base), '--output', '../outside_overlay_test'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert process.returncode != 0
    checks.append(dict(name='CLI refuses target outside project', passed=True))
    assert variant.snapshot(original) == before
    assert variant.snapshot(right) == variant.snapshot(restored)
    for path in (Path(__file__), Path(variant.__file__), Path(A.__file__), ROOT / 'diagnostics/review_loma_analytic_simulation.py'):
        shutil.copyfile(str(path), str(out / path.name))
    summary = dict(status='passed', scope='Invented two-event/two-receiver storage controls; no real package created', checks=checks,
        original_fixture_unchanged=True, variant_raw_files_unchanged=True,
        output_sha256={str(p.relative_to(out)): A.info(p)['sha256'] for p in out.rglob('*') if p.is_file()})
    A.json_write(out / 'summary.json', summary)
    print(json.dumps(dict(status='passed', checks=len(checks)), indent=2))


if __name__ == '__main__':
    main()
