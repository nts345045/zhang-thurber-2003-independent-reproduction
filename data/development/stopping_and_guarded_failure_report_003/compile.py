#!/usr/bin/env python3
"""Record two ordinary pdflatex passes; no numerical calculations."""
import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def now():
    return datetime.utcnow().isoformat() + 'Z'


def main():
    receipt = OUT/'compile.json'
    if receipt.exists():
        raise RuntimeError('Preserve the existing compilation receipt')
    tex = sorted((ROOT/'report').glob('*.tex'))
    assert len(tex) == 16
    pins = {str(p.relative_to(ROOT)): sha(p) for p in tex}
    state = {'status': 'compiling', 'started_utc': now(),
             'previous_report_sha256': sha(ROOT/'report/report.pdf'),
             'tex_source_sha256': pins, 'readme_sha256': sha(ROOT/'README.md'),
             'compile_source_sha256': sha(Path(__file__)), 'commands': []}
    receipt.write_text(json.dumps(state, indent=2) + '\n')
    try:
        for number in (1, 2):
            command = ['pdflatex', '-interaction=nonstopmode', '-halt-on-error', 'report.tex']
            with (OUT/('pass%d_stdout.txt' % number)).open('wb') as stream:
                result = subprocess.run(command, cwd=str(ROOT/'report'),
                                        stdout=stream, stderr=subprocess.STDOUT)
            state['commands'].append({'command': command, 'working_directory': 'report',
                                      'return_code': result.returncode})
            (OUT/('pass%d_report.log' % number)).write_bytes((ROOT/'report/report.log').read_bytes())
            receipt.write_text(json.dumps(state, indent=2) + '\n')
            if result.returncode:
                raise RuntimeError('pdflatex pass %d failed' % number)
        (OUT/'report.log').write_bytes((ROOT/'report/report.log').read_bytes())
        subprocess.check_call(['pdftotext', str(ROOT/'report/report.pdf'), str(OUT/'report.txt')])
        with (OUT/'pdfinfo.txt').open('wb') as stream:
            subprocess.check_call(['pdfinfo', str(ROOT/'report/report.pdf')], stdout=stream)
        assert all(sha(ROOT/name) == value for name, value in pins.items())
        assert sha(ROOT/'README.md') == state['readme_sha256']
        state.update(status='completed', finished_utc=now(),
                     report_sha256=sha(ROOT/'report/report.pdf'),
                     report_bytes=(ROOT/'report/report.pdf').stat().st_size,
                     output_sha256={name: sha(OUT/name) for name in (
                         'pass1_stdout.txt', 'pass1_report.log',
                         'pass2_stdout.txt', 'pass2_report.log',
                         'report.log', 'report.txt', 'pdfinfo.txt')})
    except Exception as exc:
        state.update(status='failed', finished_utc=now(), error=repr(exc))
        raise
    finally:
        receipt.write_text(json.dumps(state, indent=2) + '\n')
    print(json.dumps({'status': state['status'], 'report_sha256': state['report_sha256'],
                      'report_bytes': state['report_bytes'], 'compile_sha256': sha(receipt)}))


if __name__ == '__main__':
    main()
