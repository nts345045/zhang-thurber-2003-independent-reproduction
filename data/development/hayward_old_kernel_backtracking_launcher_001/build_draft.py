"""Prepare a separately named launcher; no native execution or maintained solver edits."""
import difflib
import hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
D=ROOT/'data/development'
base=D/'hayward_trial_completion_candidate_002/after/run_hayward_guarded_inversion.py'
s=base.read_text()
s=s.replace('Freeze one guarded Hayward DD attempt after independently reviewed preflight.', 'Freeze one old-kernel Hayward DD attempt with reviewed local-ray trial backtracking.')
s=s.replace('from run_loma_analytic_simulation import', 'sys.dont_write_bytecode = True\n\nfrom run_loma_analytic_simulation import',1)
s=s.replace('from diagnostics.review_trial_completion import', 'from diagnostics.review_old_kernel_trial_completion import')
s=s.replace('rows, terminate_group', 'rows, terminate_group, live_group_members')
pos=s.index('\n\ndef check_inverse(')
extra=(D/'hayward_old_kernel_backtracking_launcher_001/source_adoption.txt').read_text()
s=s[:pos]+extra+s[pos:]
start=s.index("    require(sha(ROOT/'src/main.cpp')")
end=s.index('    evidence = ',start)
s=s[:start]+"""    selected, adoption, adoption_pins = source_adoption(parity, manifest)
    for name,digest in adoption['bridge']['identical_native_numerical_input_sha256'].items():
        require(copied[name]==digest, 'Native input differs from the reviewed old-kernel bridge: '+name)
    require(configuration(data/'run.cfg')==adoption['bridge']['identical_effective_config'],
            'Inverse configuration differs from the reviewed old-kernel bridge')
"""+s[end:]
s=s.replace("    return manifest, copied, evidence, parity, dict(observations=", "    evidence.update(adoption_pins)\n    return manifest, copied, evidence, parity, selected, adoption, dict(observations=")
s=s.replace('manifest,copied,evidence,parity,expected=reviewed_inputs', 'manifest,copied,evidence,parity,selected,adoption,expected=reviewed_inputs')
s=s.replace("for protected in (reference,parity_path.parent):", "for protected in (reference,parity_path.parent,ROOT/'data/development'):")
start=s.index("        names=['CMakeLists.txt'")
end=s.index('        def normalize(info):',start)
s=s[:start]+'''        scripts=('run_hayward_old_kernel_backtracking.py','run_loma_initial_preflight.py',
                 'run_loma_analytic_simulation.py','diagnostics/review_loma_analytic_simulation.py',
                 'diagnostics/review_old_kernel_trial_completion.py')
        sources=dict(selected)
        sources.update({name:ROOT/name for name in scripts})
        names=sorted(sources)
        source_hashes={name:sha(sources[name]) for name in names}
        for name in names:
            target=source/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(str(sources[name]),str(target))
        verify_hashes(source,source_hashes)
        require({name:source_hashes[name] for name in selected} == adoption['candidate_source_sha256'],
                'Selected old-kernel source changed during frozen copy')
        require(source_hashes['diagnostics/review_old_kernel_trial_completion.py'] == COMPLETION_HELPER,
                'Copied completion helper changed')
''' + s[end:]
s=s.replace("compiler=next(line.split('=',1)[1] for line in (build/'compiled/CMakeCache.txt').read_text().splitlines() if line.startswith('CMAKE_CXX_COMPILER:FILEPATH='))", "compiler=compiler_from_cache((build/'compiled/CMakeCache.txt').read_text())")
s=s.replace("        frozen=dict(mode='dd',", "        require(libraries == adoption['runtime_library_sha256'], 'Runtime libraries differ from old-kernel controls')\n        frozen=dict(mode='dd',source_adoption=adoption,")
s=s.replace("'Per-evaluation guard preserves existing flags; it is not global first-arrival certification.',", "'Pure local stopping failures only may reject an unevaluated trial; current/final/mixed failures remain fatal.',\n                                 'Old initial forward evidence is reused through004-to-guard-to-main-only-backtracking controls; no direct main or binary equality claim.',")
s=s.replace("        ledger['completed_commands'].append(record); active=None; atomic_json(ledger_path,ledger)\n        if code:raise subprocess.CalledProcessError(code,command)", """        record['remaining_live_group_members']=live_group_members(active.pid)
        ledger['completed_commands'].append(record); atomic_json(ledger_path,ledger)
        require(not record['remaining_live_group_members'], 'Supervisor exited while process-group writers remain')
        if code:raise subprocess.CalledProcessError(code,command)
        active=None""")
s=s.replace("        if active is not None:ledger['exception_child']=terminate_group(active)", """        if active is not None:
            signal.signal(signal.SIGTERM,signal.SIG_IGN);signal.signal(signal.SIGINT,signal.SIG_IGN)
            ledger['exception_child']=terminate_group(active)""")
s=s.replace("    # This is a completion-only candidate. Initial numerical/source eligibility\n    # above stays unchanged until a separate exact old-kernel bridge is reviewed.\n", "    # Completion keeps the independently reviewed candidate002 helper and all final initializer gates.\n")
(ROOT/'run_hayward_old_kernel_backtracking.py').write_text(s)
helper=D/'hayward_trial_completion_candidate_002/after/diagnostics/review_trial_completion.py'
(ROOT/'diagnostics/review_old_kernel_trial_completion.py').write_bytes(helper.read_bytes())
(D/'hayward_old_kernel_backtracking_launcher_001/launcher.patch').write_text(''.join(difflib.unified_diff(base.read_text().splitlines(True),s.splitlines(True),fromfile='completion_candidate002/run_hayward_guarded_inversion.py',tofile='run_hayward_old_kernel_backtracking.py')))
