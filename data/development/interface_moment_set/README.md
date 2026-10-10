# Exact moment set and the retained native residual

For a constant nonnegative interface jump c, every feasible continuous supporting slope is represented exactly by two endpoint moments A,B. Their moment set is

    (A+B)² <= 2cA,    (A+B)² <= 2cB,     c>0.

For c=0 only A=B=0 is feasible. The proof supplies a bounded-density realization for every feasible pair and shows that this set's support function is exactly c*I_plus. No quadrature or dual optimizer is used. See [proof.md](proof.md).

All 156 exact controls in `001` passed: five zero/reversed-jump checks, 75 support-equivalence cases, 30 constructive realizations, 30 groups of supporting inequalities, 12 rejected boundary violations, three saved native projection bounds, and the complete 20-row tangent trial inventory. The arithmetic controls use invented rational inputs; native quantities are reconstructed only from already saved interval tables.

Changing guide-normal support cannot change the smooth/tangent projection P*G. The resulting lower bound on every feasible Euclidean support norm nearly equals the saved alpha=0 norm upper bound:

| Saved polygon | Fixed-projection norm lower bound, s/km | Saved norm upper bound, s/km | Maximum possible relative reduction from changing normal support |
| --- | ---: | ---: | ---: |
| Original reference-seed polygon | 6.82583946604e-6 | 6.82584832193e-6 | 1.297406e-6 |
| Full-direction one-step polygon | 1.84175435118e-5 | 1.84175508076e-5 | 3.961307e-7 |
| Tangent one-step polygon | 1.84174627264e-5 | 1.84174635279e-5 | 4.352281e-8 |

The displayed numbers are rounded; the identified CSV and JSON contain exact rational bounds. All three polygons preserve event `quakeml:NC.anss.org/Event/NC/20091683`, origin `quakeml:NC.anss.org/Origin/NC/2660124`, and receiver `NC.BSL..EHZ` (`FDSN:NC_BSL__E_H_Z`), epoch `1989-08-25T19:45:00` through `1990-09-10T19:20:00`. Full native context and original flag zero remain attached to the evidence.

A separate [sign corollary](nonnegative_corollary.md) is stronger for the first two polygons. Every guide-incident alpha=0 normal component is nonnegative, and every feasible moment change adds nonnegative normal components. Therefore alpha=0 already minimizes the Euclidean support norm there. The tangent-step polygon fails this sufficient sign condition; its projection lower bound still applies. `001/sign_check.py` and `normal_sign_certificate.json` preserve this distinction.

The saved tangent trials also enclose K(h)=[T(P+h*d)-T(P)-h*F(d)]/h² without new action evaluations. At halvings 17, 18 and 19, K is approximately 2.29409699, 2.29410177 and 2.29410416 s/km². These positive directional secants help explain why a finite trial can increase action despite a negative infinitesimal slope. They do not determine the full Hessian spectrum or establish mesh stiffness as the cause of slow optimization.

The results establish that changing guide-normal support cannot remove the dominant residual of these particular retained polygons. They do not establish stationarity, choose source/model derivatives, or prescribe an optimizer. These are Euclidean support norms. The production code also uses a Euclidean norm after its box projection (`src/core.hpp:38,264–270`), with a 1e-7 strict test or the combined action-change <1e-11 and gradient <1e-5 test. Its sampled one-sided ordinary gradient differs from the continuous supporting vector at an aligned interface, so these bounds do not replace either test or change any flag.

Reproduce the exact components and saved-table projection analysis from the integration repository root, using a fresh output directory:

```bash
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 \
python3 diagnostics/check_interface_moment_set.py \
  --output data/development/interface_moment_set/reproduction
```

The recorded command used output `data/development/interface_moment_set/001`. Its summary freezes and hashes source, proof, the reviewed square-root enclosure helper and all native inputs. `001/sign_check.py` is a separate saved-table check of the sufficient sign criterion. No production code, observational selection, action, ray trace or inversion is rerun by this package.
