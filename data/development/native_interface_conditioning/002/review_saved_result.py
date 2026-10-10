import csv
import hashlib
import json
from fractions import Fraction as Q
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'data/development/native_interface_conditioning'
OUT = BASE/'002'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def need(ok, message):
    if not ok: raise AssertionError(message)

def rows(path):
    with path.open(newline='') as f: return list(csv.DictReader(f))

s = json.loads((OUT/'summary.json').read_text())
for name, digest in s['artifact_sha256'].items():
    need(sha(OUT/name) == digest, 'artifact '+name)
for name, digest in s['input_source_sha256'].items():
    need(sha(ROOT/name) == sha(OUT/'source'/name) == digest, 'source '+name)
old = rows(BASE/'001/native_edge_curvature.csv')
new = rows(OUT/'native_edge_curvature.csv')
need(len(old) == len(new) == s['edge_count'] == 2704, 'edge inventory')
ids = ['event','station','source_event_resource_id','source_origin_resource_id',
       'receiver_channel_seed_id','receiver_channel_fdsn_source_id',
       'receiver_metadata_epoch_start','receiver_metadata_epoch_end']
same = 0; newly_eligible = 0
fields = list(s['contributions'])
totals = {k:[Q(0),Q(0)] for k in fields}
groups = {}
for n,(a,b) in enumerate(zip(old,new)):
    need(int(b['edge']) == n and int(b['node_a']) == n and int(b['node_b']) == n+1, 'edge order')
    need(b['status'] == 'computed', 'ineligible edge')
    need(all(b[k] == a[k] == s['native_case'][k] for k in ids), 'native joins')
    need(b['original_local_flag'] == a['original_local_flag'] == '0', 'original flag')
    if a['status'] == 'computed':
        need(all(b[k] == v for k,v in a.items()), 'old eligible value changed')
        same += 1
    else:
        need(Q(b['exact_dx']) != 0, 'extension used aligned edge')
        newly_eligible += 1
    for end in ('a','b'):
        side = b[end+'_normal_endpoint_side']
        dx = Q(b['d'+end+'_x_rational'])
        need(side not in ('right','left') or (side == 'right') == (dx > 0), 'directional side')
        need(side != 'fixed_normal_no_side_needed' or dx == 0, 'fixed normal moved')
    groups[b['edge_kind']] = groups.get(b['edge_kind'],0)+1
    for k in fields:
        for side,pos in [('lower',0),('upper',1)]: totals[k][pos] += Q(b[k+'_'+side+'_rational'])
for k,value in totals.items():
    need(tuple(value) == tuple(Q(s['contributions'][k][side+'_rational']) for side in ('lower','upper')), 'sum '+k)
need(same == 2696 and newly_eligible == 8, 'eligibility change')
need(groups == {k:v['edges'] for k,v in s['groups'].items()}, 'group counts')
need(s['full_curvature_available'] and s['contributions_complete'] and not s['inconclusive_edges'], 'full result flags')
need(len(s['checks']) == 56 and all(r['passed'] for r in s['checks']), 'checks')
secants = json.loads((OUT/'saved_secant_comparison.json').read_text())
need(len(secants) == 20, 'secant inventory')
events = s['first_positive_geometric_events']
for r in secants:
    need(all(r[k] == s['native_case'][k] for k in ids), 'secant native join')
    h = Q(r['step_rational'])
    within = all(h < Q(e['h']) for k,e in events.items() if k in ('endpoint_x_piece','nonzero_dx_becomes_zero'))
    need(r['within_unchanged_endpoint_pieces_and_nonzero_dx'] == within, 'piece event flag')
    need(r['within_finite_domain_interval'] == (h <= Q(events['domain_face']['h'])), 'domain interval flag')
    want = (2*Q(r['secant_coefficient_lower_rational'])-totals['total'][1],
            2*Q(r['secant_coefficient_upper_rational'])-totals['total'][0])
    need(want == tuple(Q(r['two_secant_minus_curvature'][k+'_rational']) for k in ('lower','upper')), 'secant difference')
for name,digest in s['artifact_sha256'].items(): need(sha(OUT/name) == digest,'post artifact')
review = dict(status='passed', reviewer='scientific_audit',
    scope='Read-only source/formula review and independent saved-table/hash/native/interval-sum checks; no new path, solve or numerical reference calculation',
    summary_sha256=sha(OUT/'summary.json'), maintained_source_sha256=sha(ROOT/'diagnostics/check_native_interface_curvature.py'),
    review_checker_sha256=sha(Path(__file__)), verified_artifact_hashes=len(s['artifact_sha256']),
    verified_original_and_frozen_source_hashes=len(s['input_source_sha256']),
    native_edges=2704, unchanged_previously_eligible_edges=same, newly_eligible_transverse_edges=newly_eligible,
    passing_checks=56, native_ids_and_original_false_flag_preserved=True,
    exact_rational_contribution_sums_match=True, saved_secant_rows=20,
    total_one_sided_curvature=s['contributions']['total'],
    findings=['For nonzero signed delta-x, the primitive quotient derivatives and direction-selected endpoint slowness slopes give the h-to-zero-positive second derivative.',
              'Aligned moving cusps remain ineligible; no arbitrary side, smoothing, snapping or convergence relabeling was introduced.',
              'All previously eligible edge values are byte-identical; eight formerly ineligible transverse edges are now covered.',
              'Finite x-piece, domain and zero-length events are recorded separately; the saved secants are not all in the same local piece.'],
    limitations=['One scalar one-sided curvature is not a full two-sided Hessian, spectrum or convergence-rate explanation.',
                 'Decimal finite-difference controls are consistency checks; they do not independently prove all interval bounds.',
                 'The preconditioner comparison is for this saved direction and continuous exact-coordinate metric, not a bitwise production metric replay.',
                 'No original local flag, source derivative, production implementation or inverse acceptance changed.'])
with (OUT/'review.json').open('x') as stream: json.dump(review,stream,indent=2);stream.write('\n')
print(json.dumps({k:review[k] for k in ('status','native_edges','passing_checks','verified_artifact_hashes')}))
