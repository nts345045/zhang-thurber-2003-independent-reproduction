# Published-cohort membership of four NC borehole stations

Investigated 2026-10-09. **No written evidence examined confirms either
inclusion or exclusion of these four stations in the Zhang--Thurber (2003)
52-station cohort or the Waldhauser--Ellsworth (2002) analysis.** None should
be labeled as excluded by the study on the present evidence.

| Station SEED name | Derived FDSN station identifier | Published site name | BSL 2001--2002 table date* | Zhang--Thurber membership | Waldhauser--Ellsworth membership |
| --- | --- | --- | --- | --- | --- |
| NC.CMW1 | FDSN:NC_CMW1 | Mill Creek | 1995/06 | Unknown | Unknown |
| NC.CCH1 | FDSN:NC_CCH1 | Chabot | 1995/05 | Unknown | Unknown |
| NC.CGP1 | FDSN:NC_CGP1 | Garin Park | 1995/03 | Unknown | Unknown |
| NC.CSU1 | FDSN:NC_CSU1 | Sunol | 1995/10 | Unknown | Unknown |

These standardized station identifiers are derived from the published SEED
network/station codes; they are not provider-assigned public IDs. The written
station table supplies neither channel identities nor exact metadata epochs.
Its month-level dates are retained as reported and are not converted into
invented channel epochs. The BSL PDF's `.identifiers.json` sidecar attaches
these identities to the four reviewed table entries. [FDSN identifier mapping](https://docs.fdsn.org/projects/source-identifiers/en/v1.0/definition.html).

*The table describes these dates as installation **or upgrade**, not
necessarily first operation. All four are explicitly listed with network NC
in BSL's Table 5.1, printed p. 36. These dates overlap the 1984--1998 study
period; they establish historical station availability, not inclusion in a
particular inversion. [BSL 2001--2002 Annual Report, chapter 5](https://ncedc.org/pub/annual_report/ar01_02.pI-II.pdf).

## Direct study evidence

Zhang and Thurber, pp. 1880--1881, describe 1,489 earthquakes, 52 stations,
20,257 absolute P picks, and catalog and waveform differences for 1984--1998.
They identify the dataset with Waldhauser and Ellsworth (2002). Their stated
pair selection links an event to at most ten neighbors with at least eight
pairwise observations. The accessible written manuscript supplies no station
roster, names none of these four codes, and states no borehole exclusion.
The network label and station count cannot identify individual membership.
[Author-posted Zhang--Thurber manuscript](https://www.researchgate.net/publication/215754286_Double-Difference_Tomography_The_Method_and_Its_Application_to_the_Hayward_Fault_California),
[publication DOI](https://doi.org/10.1785/0120020190).

Waldhauser and Ellsworth, sections 2.1--2.3, paragraphs 14--18, use NCSN
catalog pick qualities 0--2, neighboring pairs less than 10 km apart, and
at least eight pairwise observations. Paragraph 15 reports 260 stations
for the 1984--1998 catalog-difference example. The waveform analysis uses
archived vertical-component recordings and stations up to 200 km from a
pair's centroid, with a coherence criterion. These are observation-selection
rules, not a named station inclusion or exclusion list. None of the four
codes occurs in the extracted full paper, and no borehole exclusion is
stated. The 260-station example does not identify Zhang--Thurber's 52-station
selection. [Waldhauser--Ellsworth (2002), pp. ESE 3-3--3-4](https://www.ldeo.columbia.edu/~felixw/papers/Waldhauser_Ellsworth_JGR2002.pdf).

The BSL report, p. 35, states that the southern Hayward network's five
stations send digital streams to Menlo Park, where Earthworm processes
them with NCSN data. Thus a description of data as NCSN does **not** imply
that southern Hayward borehole stations were excluded. This is a selection-rule
inference, not proof that any of their observations entered either study.
[BSL report, chapter 5](https://ncedc.org/pub/annual_report/ar01_02.pI-II.pdf).

## Consequence and limits

Preserve all four stations' observations, native resource IDs, channel
identities, and epoch records. Record their original-study membership as
unknown. The present evidence provides no study-based reason to remove them
or to call them confirmed additions outside the published cohort. A later
comparison may distinguish independently acquired observations, but must not
claim that the original study excluded these stations without new evidence.
This membership investigation does not resolve sensor elevation or epoch
ambiguities and does not authorize substituting unverified coordinates.

Only written manuscripts, tables, and operational descriptions were used.
No station identity was inferred from map positions, and no author code,
input deck, or numerical output was examined. Source files prefixed
`membership_` retain the two successfully retrieved PDFs, extracted text,
request URLs, access times, and hashes. A separate consulted-source JSON
records the author-posted target text. An attempted USGS grant-report URL
returned HTTP 404; its saved error body is explicitly identified and is not
used as direct evidence here.
