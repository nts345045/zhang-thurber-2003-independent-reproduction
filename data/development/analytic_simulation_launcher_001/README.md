# Frozen analytic simulation launcher: first smoke test

Twelve checks passed using invented two-source/two-receiver constant-speed
geometry. The real CMake build and simulator wrote four identified absolute
arrivals and four differences. Input changes, missing review pins, incorrect
support, escaping paths, and reuse of completed outputs were rejected.
The two intentionally mutable input files were preserved byte for byte before
simulation. An independent streaming review also verified the synthetic
values, quantization, every identity, and blank polygon-ray status fields.

This checkpoint did not exercise interruption. Source review subsequently
identified a possible process-exit race in the exception handler. The source
and successful outputs here remain unchanged; the corrected launcher and
actual signal test are recorded in `../analytic_simulation_launcher_002/`.
No real Loma geometry was simulated by this fixture.
