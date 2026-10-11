# Completed procedure, unresolved numerical limitations

The unmodified historical synthetic rebuild at commit `976d2590c60fae542e25c37c8b2352ff3765c6a1` completed in **9,597 seconds**, with exit zero from all eight inversions. All **48 component checks** passed their recorded tolerances. Five synthetic generators, the initial and two final sampled ray checks, audit, analysis, plotting and two successful TeX passes completed. The rebuilt PDF has **125 pages**, 2,819,523 bytes and SHA-256 `54a3b6165335f5aaad84797ea08e2d9b90a99a692e5ea124f94b028abf117271`. Panel statuses remain **one independently reproduced and 61 partially reproduced**.

The earlier 801-second/32-check baseline was produced at `848620388c4528c0d643470b2ad04c5554b42f24`. This replay includes commit `5d9933f`'s change from two- to eight-point quadrature per grid piece and weighted-Laplacian ray-metric preconditioning. It does not include the later integration-branch ray candidates. These are new historical-procedure results; published baseline figures retain their original provenance.

Sampled ray limitations persist:

| Saved state | Production/refined convergence flags, of 32 | Maximum time-refinement difference (µs) | Maximum production/refined source-FD discrepancy (s/km) |
|---|---:|---:|---:|
| Truth model | 16 / 26 | 559.237 | 3.02344e-4 / 3.11202e-4 |
| Standard final | 2 / 26 | 669.648 | 1.62537e-4 / 1.52547e-4 |
| DD final | 11 / 29 | 350.542 | 4.22883e-4 / 4.15531e-4 |

Each derivative diagnostic covers only **eight rays and 24 components**. The historical component tolerance is **0.003 s/km**, distinct from the later project's 3e-6 s/km source-accuracy criterion. Passing these historical checks does not resolve the failed ray flags, validate the full cohort or establish continuous first-arrival accuracy. The time differences compare the two recorded discretizations; finite differences are not an independent analytic reference.

The larger synthetic location RMS is **1.11233 km initially**, **3.06080 km after standard inversion** and **1.38831 km after DD inversion**. Thus DD improves on standard here but does not recover the initial location accuracy. Both sets of 18 LSQR solves satisfy their recorded convergence tests, which does not establish accurate nonlinear ray tracing. Separate small controls remain useful: the known-model location RMS falls from 0.394115 to 0.0687185 km; the 16-source joint control passes its recorded gates, with median location error 0.182076→0.0210263 km and illuminated median velocity error 0.3→0.00795103 km/s. These limited results do not establish manuscript recovery with the unmatched historical geometry and starting assumptions. Full precision is retained in [metrics.json](results/data/metrics.json).

Plotting regenerated nine PDF/PNG pairs. The report consumes eight of those PDFs and **13 byte-identical committed figures**, including authoritative Figure 2 and the field, accepted-update and CC-support figures. The regenerated historical `figure02` depicts invented geometry and is not that authoritative Figure 2. Analysis refreshed field summaries from saved inputs but did not rerun field inversions, waveform acquisition or full-DD resolution. All eight final grids/events/histories and sampled diagnostic rows are retained; every other generated scientific artifact has an explicit path/hash disposition in the [manifest](scientific_manifest.json). History RMS/ray fields describe the pre-update linearization; final model/event tables are separate outputs.
