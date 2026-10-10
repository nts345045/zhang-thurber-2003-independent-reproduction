# Written specifications and Loma Prieta size estimate

Reviewed 2026-10-09. This review reads manuscript prose and captions, counts existing authoritative geometry, and estimates storage. It does not use author software, input decks, simulation outputs, or digitized figures. No new observational data, waveforms, synthetic arrivals, or inversions were requested or generated. The independent geometry remains 724 earthquakes and 52 receivers.

## Target manuscript

[Zhang and Thurber (2003), DOI 10.1785/0120020190](https://www.researchgate.net/publication/215754286_Double-Difference_Tomography_The_Method_and_Its_Application_to_the_Hayward_Fault_California), author-posted manuscript text:

| Locator | Written specification |
|---|---|
| p. 1877, Synthetic Test, first paragraph | Uses the Kissling et al. synthetic experiment and actual Loma Prieta source/USGS station geometry. No source or station count is stated here. |
| p. 1877, Synthetic Test, noise paragraph | Gaussian picking noise: mean zero, standard deviation 0.04 s; one constant bias per station drawn uniformly from −0.3 to +0.3 s. |
| Same paragraph | Pseudo-correlation differences at common stations, “for pairs of events within 20 km”; synthetic times “rounded off to two decimal places”; claimed differential rounding error up to 0.005 s. |
| pp. 1877–1878, relocation and tomography paragraphs | Dietz–Ellsworth (1990) 1-D starting model; same start for absolute and DD tomography. Horizontal/vertical smoothing weight 5. No numerical source perturbation or origin-time initialization is stated. |
| p. 1879, Figure 2 caption | X: −35, −15, 0, 2, 4, 6, 20, 35 km; Y: −60, −40, −20, 0, 20, 40 km; Z: 0, 3, 7, 11, 16 km. No cohort counts. |

The synthetic section specifies no neighbor cap or complete source–receiver incidence roster. Its noise/rounding wording does not unambiguously define the order of operations.

## Earlier synthetic experiment and initialization

[Kissling et al. (1994), DOI 10.1029/93JB03138](https://doi.org/10.1029/93JB03138), p. 19638, section on the minimum 1-D model as a reference for 3-D tomography, explicitly reports 199 earthquakes and 12,000 source–receiver paths. Synthetic travel times were calculated with a finite-difference eikonal solver. Numerical rounding, typically ±0.01 s, was the experiment's only travel-time noise. Trial hypocenters were obtained by relocating those synthetic times using a simplified 1-D model; their errors ranged from hundreds of metres to a few kilometres. The later 3-D tests also used 16 synthetic quarry blasts with fixed coordinates and unknown origin times.

The prose was read in a [reprint of the primary paper](https://www.scribd.com/document/784538798/Kissling-et-al-GRL-1994); the 199/12,000 passage was also independently returned from an indexed [institutional manuscript copy](https://citeseerx.ist.psu.edu/document?doi=a1c2f0f1c9bfd916a15e1efd7c8f21ceaf28d2bb&repid=rep1&type=pdf). Direct institutional/PDF access failed. Its Figure 3 caption, p. 19639, distinguishes constant-layer models for relocation from gradient models for tomography; numeric values are graphical and were not digitized.

These are precursor counts, not a verified 2003 roster. The inspected text does not establish the synthetic station count or whether the later experiment retained the blasts. Our 724-source/52-receiver cohort and complete source–receiver incidence differ from this precursor.

## Dietz–Ellsworth profile limit

[Dietz and Ellsworth (1990)](https://pubs.usgs.gov/publication/70242141), p. 1417, Data and Analysis, describes separate northeast and southwest profiles, each with nine layers over a halfspace. The indexed primary text refers to Figure 1 for the profiles. The target does not identify a side or provide a tabulated profile. An exact numerical starting profile was therefore not established under the prohibition on figure digitization.

The already documented [USGS gradient adaptations](../../../reference/specification_notes.md) remain usable explicit alternatives; this review does not upgrade them to verified target inputs. Likewise, the repository's homogeneous 5.5 km/s start, 0.6 km coordinate perturbations, and 0.05 s origin-time perturbations are independent assumptions. A start obtained by relocating synthetic noisy arrivals with a declared 1-D profile would follow the precursor's initialization procedure more closely, but would still not reconstruct its unavailable trial hypocenters.

For the current generator, subtracting separately rounded times gives an error difference bounded by 0.01 s, not 0.005 s. Rounding a time difference once would give the latter bound, but the paper does not clearly prescribe that operation. No rounding implementation was changed here.

## Hayward waveform method, before acquisition

[Waldhauser and Ellsworth (2002), DOI 10.1029/2000JB000084](https://agupubs.onlinelibrary.wiley.com/doi/full/10.1029/2000JB000084), section 2.1, paragraph 14 (p. ESE 3-3): catalog pairs use hypocentral separation below 10 km, at least eight common observations, up to ten neighbors, and NCSN pick qualities 0–2.

Section 2.2, paragraph 16 (pp. ESE 3-3–3-4): digital NCSN vertical-component waveforms archived since 1984; stations within 200 km of the pair centroid; tapered 2.56 s windows containing P or S wave trains, 256 samples at 100 Hz. At least half the squared-coherency values in 2–10 Hz must exceed 0.9. Delay comes from cross-spectral phase slope following Poupinet et al. (1984), not simply a time-domain correlation maximum. About 1 ms precision is possible for sufficiently similar signals.

Section 2.3, paragraph 18 (pp. ESE 3-4–3-5): squared coherency supplies correlation weights; catalog weights are 1, 0.75, 0.25 for quality classes 0, 1, 2. The paragraph does not fully specify taper family, window placement, spectral smoothing, phase unwrapping or response preprocessing. Its concluding sentence distinguishes waveform-derived hypocentroid timing from first-arrival timing. These gaps need declared measurement choices before implementation; no waveforms were queried.

The target's Hayward application, p. 1880, uses 17,955 P-wave correlation differences. That count is not a claim that all available common-station pairs correlate. The existing independent run contains no such measurements.

## Count and computational consequences

[pair_cost.json](pair_cost.json) records source hashes and arithmetic for the existing generator's strict 3-D distance test. The saved coordinates give:

| Quantity | Count |
|---|---:|
| Sources / receiver placements | 724 / 52 |
| Unique rays / absolute rows | 37,648 |
| Unordered event pairs below 20 km | 152,834 |
| Catalog differential rows | 7,947,368 |
| Precise synthetic differential rows | 7,947,368 |
| Total rows | 15,932,384 |

All receiver placements are used for each source and selected pair, matching `synthetic_observations` in the hashed `src/main.cpp`. This incidence is a simulation assumption, not evidence that every historical station recorded every earthquake. Degrees range from 47 to 586, median 428.5. An independent `scipy.spatial.distance.pdist` calculation reproduced 152,834 pairs. The closest distance to the threshold is 0.0000811 km away; there are no equality cases.

With the current identifier-preserving CSV schema, fixed fields occupy exactly 6,650,014,057 bytes before numerical value strings. Mean value widths of 8–16 characters imply 6.78–6.90 GB; 12 gives 6.84 GB (6.37 GiB). This excludes arrivals, residuals, and other outputs.

The current C++ loader first stores every field as a string, then retains 18 metadata key/value pairs in every observation. The measured standard-library layout grows each metadata vector to capacity 32. The observation payload alone is at least 43.92 GB; coexistence with the raw CSV table requires at least 61.83 GB (57.59 GiB). These are payload lower bounds, excluding allocator overhead, spare outer-vector capacity and solver work. Sparse matrix entries alone would add 8.16, 16.31 or 32.63 GB at hypothetical average row widths of 32, 64 or 128. Actual ray sparsity and active-row counts have not been measured for this geometry.

Lossless gzip of the existing Hayward CSV reduces its size to 8.17%; the older numeric synthetic CSV reaches 33.90%. Applying those ratios to 6.84 GB gives roughly 0.56 or 2.32 GB, respectively, solely as archive-size analogues. No compression ratio for ungenerated Loma observations is measured. Compression leaves the scientific selection unchanged and does not reduce the current loader's materialized-memory requirement.

The next preparation can retain every declared pair while addressing repeated metadata and materialized rows computationally. The geometry, numerical starting profile, source initialization and precise-time rounding assumptions must stay explicit. This review does not authorize or implement a smaller cohort, neighbor cap, new waveform measurements, or an inversion.

## Reproduce this estimate

From the repository root:

```sh
g++ -std=c++17 -O0 data/development/loma_specification/memory_layout.cpp -o data/development/loma_specification/memory_layout
PYTHONDONTWRITEBYTECODE=1 python3 data/development/loma_specification/count_cost.py
```

The probe only reports object sizes/capacity. The Python helper uses the two existing geometry tables and hashes the relevant generator/loader source. Its compression checks read existing project CSVs into a streaming compressor and retain only byte counts. No CSV rows are produced. Recompile the probe and review the schema assumptions if the generator or C++ library changes.

`sources.json` records literature access and locators. Retrieval metadata and
hashes are included in the repository; literature PDFs, derived full text,
and HTTP response bodies remain local reference files and are not included
in this checkpoint. Their source URLs are recorded. Saved HTTP 403 bodies are
explicitly errors, not manuscript copies. The Waldhauser–Ellsworth PDF is a
written-method reference, not an observational input; its derived text is
linked to the raw PDF hash. No coordinates or measurements were extracted
from its tables/figures into a data set.
