"""Conditional final-audit assembly, with no I/O, integration or coefficient fit.

The later reviewed wrapper supplies pinned records from the unchanged interval
primitives.  No final case roster or numerical call is authorized by this file.
"""
from fractions import Fraction as Q
import math


def require(ok, message):
    if not ok:
        raise ValueError(message)


def bounds(value):
    lo, hi = map(Q, value)
    require(lo <= hi, 'Reversed interval')
    return lo, hi


def add(a, b):
    return a[0] + b[0], a[1] + b[1]


def binary64(token):
    """Coordinates and theta are emitted as double hex, not wide scalars."""
    value = float.fromhex(token)
    require(math.isfinite(value), 'Nonfinite binary64 value')
    # Python's parser could round an overprecise token: validate its exact value.
    mantissa, exponent = token.lower().split('p')
    sign = -1 if mantissa.startswith('-') else 1
    mantissa = mantissa.lstrip('+-')
    require(mantissa.startswith('0x'), 'Hexadecimal token required')
    whole, dot, fraction = mantissa[2:].partition('.')
    numerator = int(whole + fraction, 16)
    exact = sign * Q(numerator, 16 ** len(fraction))
    power = int(exponent)
    exact *= Q(2 ** power) if power >= 0 else Q(1, 2 ** (-power))
    require(Q(value) == exact, 'Token is not an exact binary64 value')
    return exact


def select(summary):
    """Select only a completed approximate full-witness candidate for review."""
    require(summary['status'] == 'completed_bounded_saved_polygon_reoptimization', 'Nonterminal solve summary')
    require(summary['candidate_convergence_status'] is None and not summary['original_flags_modified'],
            'Original flags and nullable candidate status must be preserved')
    reason = None
    if summary['final']['multiple_faces']:
        reason = 'multiple_aligned_faces_unsupported'
    elif not summary['approximate_full_candidate']:
        reason = 'approximate_full_target_not_reached'
    elif summary['stop_reason'] != 'approximate_full_witness_requires_final_interval_audit':
        reason = 'unexpected_approximate_terminal_state'
    elif not summary['support']['eligible']:
        reason = 'support_not_eligible'
    elif not all(p['convex'] for p in summary['support']['ordered_final_patches']):
        reason = 'nonconvex_normal_jump_unsupported'
    return dict(selected=reason is None, reason=reason, case_id=summary['case_id'],
                candidate_convergence_status=None, scope='Selection for an audit is not a certificate.')


def normalize(summary, initial_rows, final_rows, axes, model_sha256, identity,
              evidence_sha256, settings):
    """Bind exact paths, final patch order and emitted feasible coefficients.

    Native identifiers, source/epoch/catalog joins, terminal receipts, and model
    node bytes are verified by the caller; their complete identity/pins survive.
    The returned edge counts are planning inputs, not an executable budget.
    """
    require(settings == dict(terms=8, subdivisions=1, bits=128), 'Unreviewed interval settings')
    require(isinstance(model_sha256, str) and len(model_sha256) == 64, 'Raw model digest required')
    axes = [tuple(map(Q, axis)) for axis in axes]
    require(len(axes) == 3 and all(len(a) >= 2 and all(x < y for x, y in zip(a, a[1:])) for a in axes),
            'Strictly increasing physical axes')
    decision = select(summary)
    paths = []
    for rows in (initial_rows, final_rows):
        require([int(row['node']) for row in rows] == list(range(len(rows))), 'Complete ordered path rows')
        path = [tuple(binary64(row[k + '_hex']) for k in 'xyz') for row in rows]
        require(len(path) >= 3 and all(a != b for a, b in zip(path, path[1:])), 'Positive fixed-edge topology')
        require(all(axes[k][0] <= p[k] <= axes[k][-1] for p in path for k in range(3)), 'True physical box')
        paths.append(path)
    start, final = paths
    require(len(start) == len(final) and start[0] == final[0] and start[-1] == final[-1], 'Fixed topology/endpoints')
    require(summary['initial']['nodes'] == summary['final']['nodes'] == len(final), 'Summary/path dimensions')
    aligned = {}
    unsupported = []
    for edge, (a, b) in enumerate(zip(final, final[1:])):
        faces = [(k, j) for k in range(3) for j in range(1, len(axes[k]) - 1)
                 if a[k] == b[k] == axes[k][j]]
        if faces:
            aligned[edge] = faces
        if len(faces) > 1:
            unsupported.append(edge)
    if unsupported:
        decision.update(selected=False, reason='multiple_aligned_faces_unsupported')
    record = dict(decision=decision, identity=identity, evidence_sha256=evidence_sha256,
                  case_id=summary['case_id'], model_sha256=model_sha256, settings=dict(settings),
                  axes=axes, start=start, final=final, aligned_edges=aligned,
                  unsupported_edges=unsupported, source_summary=summary,
                  original_status_scope='The complete inherited identity/status is retained without rewriting it.',
                  candidate_convergence_status=None)
    if not decision['selected']:
        return record
    patches = summary['support']['ordered_final_patches']
    theta_hex = summary['support']['theta_hex']
    require([p['index'] for p in patches] == list(range(len(patches))) and len(patches) == len(theta_hex),
            'One emitted coefficient for each ordered final patch')
    theta = [binary64(v) for v in theta_hex]
    require(all(0 <= v <= 1 for v in theta), 'Feasible exact binary64 mixture coefficients')
    normalized = []
    coverage = {edge: [] for edge in aligned}
    for patch in patches:
        edge, axis, plane = patch['edge'], patch['axis'], patch['plane']
        require(edge in aligned and aligned[edge] == [(axis, plane)], 'Patch must join its exact single face')
        left, right = Q(patch['left_exact']), Q(patch['right_exact'])
        require(0 <= left < right <= 1, 'Positive patch interval')
        minus, plus = list(patch['minus_cell']), list(patch['plus_cell'])
        require(len(minus) == len(plus) == 3 and minus[axis] == plane - 1 and plus[axis] == plane
                and all(minus[k] == plus[k] for k in range(3) if k != axis), 'Adjacent incident cells')
        require(all(0 <= cell[k] < len(axes[k]) - 1 for cell in (minus, plus) for k in range(3)), 'Valid cell indices')
        coverage[edge].append((left, right))
        normalized.append(dict(index=patch['index'], edge=edge, normal_axis=axis,
          normal_coordinate=axes[axis][plane], u=(left, right), minus_cell=minus, plus_cell=plus))
    require([p['edge'] for p in normalized] == sorted(p['edge'] for p in normalized), 'Ordered edge/patch traversal')
    for pieces in coverage.values():
        require(pieces and pieces[0][0] == 0 and pieces[-1][1] == 1
                and all(a[1] == b[0] for a, b in zip(pieces, pieces[1:])), 'Complete final patch partition')
    changed = [e for e in range(len(final) - 1) if start[e:e + 2] != final[e:e + 2]]
    record.update(ordered_patches=normalized, theta_hex=theta_hex, theta_exact=theta,
                  changed_edges=changed, combined_final_edge_count=len(final) - 1,
                  normal_patch_count=len(normalized), maximum_missing_start_action_count=len(changed))
    return record


def assemble(normalized, final_edge_records, patch_moment_records, helper, projected_norm):
    """Assemble already computed bounds with the unchanged helper's pure sums.

    final_edge_records: complete edge/a_exact/b_exact/action/components/blocked_axes.
    patch_moment_records: one unchanged aligned_patch_moments result per aligned
    edge, tagged edge/model_sha256/settings and exact a_exact/b_exact.
    Starting action and net change are explicitly not assessed in this final-only audit.
    No primitive integration, support fit, or output-status mutation occurs here.
    """
    out = dict(identity=normalized['identity'], evidence_sha256=normalized['evidence_sha256'],
               decision=normalized['decision'], candidate_convergence_status=None)
    if not normalized['decision']['selected']:
        return dict(out, status='unresolved_not_selected')
    path, start = normalized['final'], normalized['start']
    require([r['edge'] for r in final_edge_records] == list(range(len(path) - 1)), 'Complete final edge roster')
    for r in final_edge_records:
        e = r['edge']
        require(tuple(map(Q, r['a_exact'])) == path[e] and tuple(map(Q, r['b_exact'])) == path[e + 1], 'Exact final ordered edge')
        require(r['model_sha256'] == normalized['model_sha256'] and r['settings'] == normalized['settings'], 'Final record model/settings')
        require(r['blocked_axes'] == [k for k, j in normalized['aligned_edges'].get(e, [])], 'Actual final availability')
        require(len(r['components']) == 2 and all(side is not None and len(side) == 3 for side in r['components']),
                'Retain both fixed-polygon endpoint sides for the separate endpoint audit')
        for side in r['components']:
            for k, value in enumerate(side):
                require((value is None) == (k in r['blocked_axes']), 'Endpoint ordinary/blocked classification')
                if value is not None:
                    bounds(value)
        bounds(r['action'])
    require(not normalized['aligned_edges'] and not normalized['ordered_patches']
            and not normalized['theta_exact'] and not patch_moment_records, 'Frozen three-case no-aligned-face scope')
    after_total = (Q(0), Q(0))
    actions = []
    for r in final_edge_records:
        after = bounds(r['action']); after_total = add(after_total, after)
        actions.append(dict(edge=r['edge'], final_action=after))
    base = helper.ordinary_base(path, final_edge_records)
    available = [list(v) if v is not None else None for v in base['components']]
    for node, axis in base['blocked_slots']:
        available[node][axis] = None
    available_norm, available_projected, blocked = projected_norm(path, available, normalized['axes'])
    require(blocked == base['blocked_slots'], 'Full available component mask')
    out.update(status='assembled_action_and_ordinary_bounds', ordinary_base=base,
      available_components=available, available_norm=available_norm, available_projected=available_projected,
      action=dict(starting_action=None, final_action=after_total, paired_net_change=None,
        classification='not_evaluated_final_only', unchanged_geometry=not normalized['changed_edges'],
        edges=actions, scope='Final action bounds only; starting action, net decrease and intermediate decisions are not assessed.'),
      fixed_polygon_endpoint_partials=dict(source=final_edge_records[0]['components'][0],
        receiver=final_edge_records[-1]['components'][1], units='s/km',
        scope='Ordinary endpoint-family intervals only; null internal-face normals remain unavailable. Physical-box boundary directions are one-sided. These are separate from full free-vertex support and optimized-ray/source accuracy.'))
    require([r['edge'] for r in patch_moment_records] == sorted(normalized['aligned_edges']), 'Complete ordered moment edge roster')
    for r in patch_moment_records:
        e = r['edge']
        require(r['model_sha256'] == normalized['model_sha256'] and r['settings'] == normalized['settings'],
                'Moment record model/settings')
        require(tuple(map(Q, r['a_exact'])) == path[e] and tuple(map(Q, r['b_exact'])) == path[e + 1],
                'Exact final ordered moment edge')
    failures = [dict(edge=r['edge'], status=r['status']) for r in patch_moment_records
                if r['status'] != 'bounded_convex_patch_moments']
    if failures:
        return dict(out, status='unresolved_nonconvex_or_unsupported_moments', support_ineligibility=failures)
    patches = [dict(p, edge=r['edge']) for r in patch_moment_records for p in r['patches']]
    require(len(patches) == len(normalized['ordered_patches']), 'Same C++/interval patch count')
    for p, declared in zip(patches, normalized['ordered_patches']):
        require(all(p[k] == declared[k] for k in ('edge', 'normal_axis', 'minus_cell', 'plus_cell'))
                and tuple(map(Q, p['u'])) == declared['u'] and Q(p['normal_coordinate']) == declared['normal_coordinate'],
                'Same ordered final patch for the same emitted theta')
    support = helper.assemble_support(path, base, patches, normalized['theta_exact'], normalized['axes'], projected_norm)
    norm = support['norm']
    strict = Q(float('1e-7'))
    within = Q(norm['upper_squared']) < strict * strict
    return dict(out, status='assembled_feasible_full_witness', full_support=support,
      strict_scale=dict(binary64_hex=float('1e-7').hex(), exact=strict, squared=strict * strict, units='s^2/km^2'),
      full_witness_below_strict_scale=within,
      interpretation='A resolved small full feasible vector is a first-order witness for this fixed polygon. A large restricted witness is inconclusive; neither result establishes source accuracy, a local minimum, or first arrival. Original flags remain unchanged.')
