# Invented single-trial controls

The preserved `../cmj_tangent_step_source_001` attempt compiled successfully
but stopped after 15 of 16 recorded checks. Its tenth helper emitted decimal
`-0` beside negative-zero hexadecimal output. JSON parsed the decimal token
as integer zero, and the strict representation check rejected it. All ten
helpers were reaped; no rounded trial or action edge was evaluated.

The separately frozen 002 correction writes zero doubles as `-0.0` or `0.0`
and saves each experiment before asserting its outcome. The numerical helper,
metric equations, action bounds, integration budget and controller are
unchanged. All **50 checks passed**, all **13 helper calls were reaped**, and
exactly **two invented action edges** were evaluated.

The exact principal-block fixture gives direction `(-1, 2, 0, -1)`, metric
energy 22 and slope -22. The homogeneous bent-path fixture takes its single
rounded trial to the straight path, whose action is exactly 1/4 second, and
passes the conservative Armijo test. The stationary case makes no trial;
the negative nominal direction that rounds to zero displacement is rejected
before action evaluation. Independent radical and rational readback passed
in [review.json](review.json).

These are invented controls, not native action, convergence, source-derivative
or first-arrival results. The terminal [summary](summary.json),
[execution record](execution.json) and independent review preserve that scope.
