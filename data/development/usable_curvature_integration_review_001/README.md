# Independent saved integration review

The review passes for the declared bounded controls. No compilation, ray trace,
control rerun, production edit or adoption was performed by this reviewer.

`check.py` verifies the terminal controller/driver chain, 982 prepared ancestry
pins, 44 launch inputs, 20 frozen source files, 217 terminal outputs, compiler,
libraries, binaries and 22 archived source members. All files are rehashed after
readback. The candidate core maps to the previously reviewed D implementation
with only its include path changed; the helper changes only a comment. Nine
other original source/CMake members are unchanged. The two copied analytic
runners add only the new helper to their snapshot inventories. Their drivers,
source generator, grids, tolerances and entry comparisons are unchanged.

All 11 commands returned 0. The saved results contain 48 core checks, the
current/trial/final guard and external-input components, 44 layered rows with
37 declared gates and 58 entry comparisons, and six oblique rows with 72 checks
and six entry comparisons. Entry equality is exact numeric equality, not a
representation-bit claim for signed zero.

The layered accuracy gates apply to the finest 0.0625 km field/path grid.
Its 11 rows have maximum time error 1.79781e-6 s and source-vector error
4.42750e-7 s/km. The saved 14.68 km coarse 0.125/0.125 case has source error
3.24035e-6 s/km and remains explicitly retained above the 3e-6 criterion.
All 44 selected local flags, endpoints and domain checks pass. The oblique
maximum selected time/source errors are 4.30759e-6 s and 4.57375e-7 s/km.

These results do not establish historical full-cohort equivalence, strict
1e-7 convergence for every ray, general first arrivals, or resolution of the
remaining endpoint/interface issues. They do not authorize an inversion.
The prepared validation plan makes the same distinctions.

Executed saved-only command (requires no existing review.json):

```sh
PYTHONDONTWRITEBYTECODE=1 python3 data/development/usable_curvature_integration_review_001/check.py
```
