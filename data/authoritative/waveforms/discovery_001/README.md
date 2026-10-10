# Hayward waveform availability discovery

The two identified records in one existing catalog-difference pair have
provider-reported waveform availability. This establishes a possible small
waveform measurement pilot. It does not establish coverage or correlation
quality for the full cohort. No waveform samples were downloaded and no
differential times were measured or substituted for catalog observations.

Discovery began with [USGS ComCat](https://earthquake.usgs.gov/data/comcat/)
and the [EarthScope federated catalog](https://service.earthscope.org/irisws/fedcatalog/1/).
The existing 42,236 selected picks contain no provider waveform resource URI.
EarthScope routed both exact channel/time requests to NCEDC. Its routing rows
are channel requests, not confirmed data spans. The separate
[NCEDC availability service](https://service.ncedc.org/fdsnws/availability/1/)
returned the spans below; all ten documentation and query responses returned
HTTP 200.

## Identified probes

The first record is the chronological median of the 14,262 retained absolute
picks, ordered by pick time and channel name. The second is its partner in
the first existing catalog-difference row containing that pick. These are
discovery probes within the unchanged selection, not a new scientific subset.
Original observation indices are zero-based.

Both use `NC.JPR.02.EHZ`, derived source ID `FDSN:NC_JPR_02_E_H_Z`.

| Probe | Event resource ID | Pick resource ID | Pick UTC | Native metadata epoch |
| --- | --- | --- | --- | --- |
| Absolute row 7136 | `quakeml:NC.anss.org/Event/NC/238035` | `quakeml:NC.anss.org/Arrival/NC/36225834` | 1991-11-22 16:07:23.230 | 1990-07-31 21:10 through 1992-03-26 21:00 |
| Absolute row 11142 | `quakeml:NC.anss.org/Event/NC/30083101` | `quakeml:NC.anss.org/Arrival/NC/45479094` | 1995-09-08 04:15:38.560 | 1995-08-03 18:15 through 1997-01-29 22:30 |

Existing differential row 15108 retains both event, origin, pick, association
and epoch identities in `partner_probe_identity.json`. `identified_probes.csv`
keeps all original absolute-observation fields inline. The native identities,
times and source hashes match the authoritative pick archive and unique channel
epochs; the referenced raw QuakeML and StationXML hashes were also checked.

Requests cover one second before through four seconds after each pick. This is
an availability window, not a selected correlation-window definition. Both
replies report quality `D` and 100 Hz:

- 1991: 16:07:01.5800 through 16:08:28.8600 UTC on November 22.
- 1995: 01:21:27.0800 through 16:01:26.8200, and 04:15:09.0900 through
  04:16:24.3300 UTC on September 8. The overlapping provider spans are retained
  verbatim. Sample-level overlap, continuity, timing and clipping remain untested.

The native channel epochs differ. Their response equivalence is not assumed.
Cached StationXML gives both a 100 Hz sample rate, an L-4C vertical sensor and
scalar sensitivity 9.96598e7 counts/(m/s) at 10 Hz. It contains no response
stages or poles/zeros for these epochs. Equal scalar sensitivities do not
establish equal phase responses. Full instrument-response metadata and
waveform samples would be needed before defining and checking preprocessing
across these epochs. The documented
[dataselect](https://service.ncedc.org/fdsnws/dataselect/1/) and
[eventdata](https://service.ncedc.org/ncedcws/eventdata/1/) interfaces offer
time-window and event-gather retrieval respectively; neither was queried here.

## Scope and remaining measurement choices

The [NCEDC archive announcement](https://ncedc.org/blog/2004/11/11/ncsn-data-available-in-seed.html)
describes NCSN event waveforms from March 1984, with catalog-only events possible.
Our selection retains 89 picks from eight earlier events. Their waveforms have
not been queried or excluded. Two positive probes do not establish an available
fraction for the 14,262 pick windows or 44,718 catalog differences.

The [written-method review](../../../development/loma_specification/README.md)
records the precursor's 2.56 s, 100 Hz windows, squared-coherency criterion in
2–10 Hz and cross-spectral phase-slope delay. Taper, exact window placement,
spectral smoothing, phase unwrapping and response preprocessing still require
explicit measurement choices. Catalog subtraction cannot stand in for these
waveform measurements. No new access or identity difficulty arose in this probe.

## Saved replies and offline verification

Every raw response has a `.provenance.json` file with exact URL, UTC retrieval,
HTTP status, byte count and SHA-256, plus an `.identifiers.json` attachment.
The attachments distinguish provider public IDs from derived FDSN source IDs,
retain native epoch context, and identify routing rows or availability spans.
The availability API supplies no waveform resource ID; none is invented.
Raw replies are unchanged. `summary.json` records scope and checks.

From the repository root, these commands reuse pinned replies without network
access and verify the exact NSLC and requested-window coverage:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 data/authoritative/waveforms/discovery_001/discover.py docs
PYTHONDONTWRITEBYTECODE=1 python3 data/authoritative/waveforms/discovery_001/discover.py availability
PYTHONDONTWRITEBYTECODE=1 python3 data/authoritative/waveforms/discovery_001/discover.py partner-availability
```

Initial calls added `--fetch`, running `routing` before `availability` and
`partner-routing` before `partner-availability`. Existing responses remain
immutable and are reused even with that flag. The helper stops on access,
identity or missing-span difficulties; it does not switch channels or cohorts.
