# Two accepted Hayward states in the report

The [report](../../../report/report.pdf) retains the first accepted-state figure and adds the published [second-minus-first comparison](../hayward_second_accepted_update_figure_001/figure/accepted_update_2_minus_1.pdf). The discussion is on page 44; Figures 19 and 20 are on pages 49 and 50. The compiled PDF has 124 pages and SHA-256 `bf40d081df39fa1911db0cd77d9983ec32cff8eba7eefe2f079afac1f679d854`.

The second update accepted iteration 1, trial 4 at fraction 1/16. Its fixed-weight objective decreased from 1410.9617357448938 to 1250.1138773364614, or 11.3999%. The figure compares the same 1,092 events and 462 grid nodes in the two saved states; its velocity panel uses the 77 nodes at 8 km depth. Published companion records preserve event, origin and both observation endpoints' pick identities, channel SEED/FDSN identifiers, metadata epochs and valid blank locations.

The text distinguishes changes between saved states from recovery errors. History RMS and ray-quality fields describe the pre-update state; the next iteration recomputes weights. Neither accepted state establishes final convergence or post-update ray accuracy. The manuscript audit remains **1 independently reproduced panel and 61 partial panels**.

Exactly two TeX passes succeeded. Checks covered the published figure/data/identity bindings, rounded values, 139 TeX paths, 30 figure references and preservation of the panel audit, other report sources and existing figures. The final log has no undefined references or overfull boxes; the existing `location_errors.pdf` page-group warning remains. Pages 44 and 49–51 were visually inspected: prose, both state comparisons and adjacent CC-map context are legible without clipping or overlap.

[scientific_manifest.json](scientific_manifest.json) binds the report, changed source and published scientific evidence. No solver, integration, interpolation, plotting or live inversion read was performed. This report check does not establish a clean end-to-end scientific rebuild.
