# Shared-kernel field comparison

This frozen run uses the integrated core and shared FMM implementation, while
retaining the diagnostic generated `bend_seed` entry. All 186 native input
records, model values and identity columns are unchanged. The independently
reviewed numerical results and scope corrections are in `review.json`.

The frozen summary's claim that no source changed is too broad: `src/main.cpp`
and `src/core.hpp` differ from the historical source, as its source-hash list
records. The original running workflow and its input files were not changed.
This variant did not directly exercise `trace_first_arrival` for all 186 rays.
The later `../fmm_hayward_integrated_production_entry/` variant does so, with
exact parity checks attached to the identified result rows.

All selected saved times and convergence flags equal the prior order-2 closed
seed audit. The separate exact-endpoint correction removes its 22 endpoint
roundoff errors. One local convergence failure remains; exit 1 preserves that
failure. Neither this test nor parity with its implementation certifies a global
first arrival or reproduces an inversion.
