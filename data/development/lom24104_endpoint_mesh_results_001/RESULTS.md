# Six endpoint-mesh outcomes

All six independently initialized, 16-history-pair runs retain the original 1000-update limit. The saved readback passed; all six fixed-polygon time and source-vector comparisons pass the inherited 25 microsecond and 3e-6 s/km limits. Three runs reached an approximate full witness and subsequently passed the independent final interval assessment. Three ended at the update budget and their complete saved ordinary-vector projections remain above 1e-7 s/km. The first table reports saved quadrature quantities; the interval bounds are reported separately below.

| Prefix subdivisions / source offset | Updates / attempts | Saved projected norm (s/km) | Source error (s/km) | Time error (microseconds) | First edge (m) | Stop |
|---|---:|---:|---:|---:|---:|---|
| 8 bottom | 1000 / 1086 | 1.748885e-06 | 2.11307389e-06 | 0.242388988 | 4.1669503 | capped, unresolved |
| 16 bottom | 981 / 1043 | 9.17627602e-08 | 1.05654728e-06 | 0.241635593 | 2.08349552 | approximate full candidate |
| 8 inward 10m | 967 / 1017 | 9.83788606e-08 | 5.54996092e-10 | 0.27693921 | 4.30363342 | approximate full candidate |
| 16 inward 10m | 1000 / 1027 | 2.92416825e-05 | 1.86770483e-09 | 0.304757047 | 2.13588018 | capped, unresolved |
| 8 inward 2p5m | 1000 / 1063 | 1.04857453e-05 | 2.28812026e-09 | 0.256846465 | 4.15054907 | capped, unresolved |
| 16 inward 2p5m | 906 / 964 | 9.88798173e-08 | 1.36823749e-11 | 0.282589635 | 2.05652895 | approximate full candidate |

No final ordinary components are unavailable. The descriptive norm uses every internal component with exact physical-box projection; it does not discard algorithmic contact normals. The three capped norms are 1.748884995e-6, 2.924168245e-5 and 1.048574534e-5 s/km. Their top ten nodes carry 99.6163%, 99.9935% and 99.9719% of squared projected residual, respectively; this is localization, not a causal diagnosis.

At the bottom source, halving the returned first-edge length from 4.16695 m to 2.08350 m halves the source error from 2.11307e-6 to 1.05655e-6 s/km. This is consistent with the already derived finite horizontal first-edge normal partial. Every inserted knot moved, and the returned spacing differs from the initialization; these are free-knot reoptimizations, not fixed spatial grids.

The inward-source partial errors are much smaller, but that alone does not establish an optimized-source derivative. Saved finite-offset value increments retain discrepancies from the direct reference increments:

| Subdivisions / inward offset | Reference increment (microseconds) | Returned increment error (microseconds) | Relative discrepancy |
|---|---:|---:|---:|
| 8 / 10 m | 11.94725254 | 0.03455022256 | 0.28919% |
| 8 / 2.5 m | 1.493374278 | 0.01445747705 | 0.968108% |
| 16 / 10 m | 11.94725254 | 0.06312145375 | 0.528334% |
| 16 / 2.5 m | 1.493374278 | 0.04095404232 | 2.74238% |

The final-only interval check completed all 9,949 final edges for bottom/16, inward 10 m/8 and inward 2.5 m/16, using unchanged series degree 8 (nine retained powers), one subdivision and 128 bits. Its independent saved readback passed 632,924 checks. Every internal component is available, and each feasible full physical-box vector has an exact upper squared norm below the unchanged strict scale. Rounded displays are:

| Subdivisions / source offset | Full witness norm upper display (s/km) | Fixed-source error norm upper display (s/km) | Time error upper (microseconds) |
|---|---:|---:|---:|
| 16 bottom | 9.1762760224e-8 | 1.0565472759e-6 | 0.2416355912 |
| 8 inward 10 m | 9.8378860631e-8 | 5.5499609143e-10 | 0.2769392087 |
| 16 inward 2.5 m | 9.8879817316e-8 | 1.3682369917e-11 | 0.2825896335 |

All three interval fixed-source and time comparisons pass the inherited limits. Exact rational bounds, not the rounded displays, determine those classifications. Final action interval widths are 4.51e-26, 9.10e-26 and 1.06e-25 seconds respectively. There were no starting-action evaluations or aligned normal moments: starting action and paired net change remain explicitly null. Thus this is a final first-order witness assessment, without a net-descent or local-minimum certificate. The other three dispositions stay unresolved. No additional mesh, update-budget or history-capacity sweep is implied.

Full generated simulation overrides and original Event NC20091537 / Origin 2658134, event 463 / receiver 28, NC.HQR..EHZ (empty location; 1989-07-11T19:55:00 to 1990-03-24T19:55:00) are preserved in the JSON evidence. This is a fixed-polygon comparison; no first-arrival or optimized-source certification is claimed.

Scientific evidence: the saved six-case review has SHA b609597076cb8b561ecdd12a312c692e4687c4943d708bc35afb1a05da6d0557. The descriptive final-table arithmetic has SHA 3e3b33e05b036f393957e004aa3ea2b34c931f32325deb942e86beff28bf0566. The final interval readback has SHA 68539e4f79bf43e1dcb2f2ddb19839ee9a031ccf28b709386d1a79f9934354d7. Their scientific content and complete identifiers are preserved in `saved_results.json`, `final_projected_components.json` and `intervals/`; local execution records are excluded.
