# Action-error reporting correction

The preserved README states that the largest action error is 2.323e-16 s.
The largest error in the saved controls is instead
**2.22953727659074219926526276885941995e-16 s**, for
`two_leg_transition_above`. The earlier number was a conservative but
inaccurate description of the maximum. No computed value, acceptance
allowance, result, or scientific interpretation changes.

This value was checked by subtracting each saved `independent_snell.time`
from the exact Decimal conversion of its binary64 `computed.time_s`, using
100-digit arithmetic, and taking the maximum absolute difference over all
33 saved cases. No connector or ray calculation was rerun.

The numerical summary remains SHA-256
`67c848b3c880a5492b17432afab6efd1be3f2571ee8202536382418799fb1497`.
The independent review remains SHA-256
`25d06bb30e02ff4af85829d4bf1e0406373b8ab7eabf3bab34f1672f4df842d7`.
That review pins the original README; both files are preserved unchanged.
