# Two-record authoritative waveform pilot

Both previously selected picks were retrieved successfully from NCEDC. Each
unchanged miniSEED reply contains 500 contiguous `int32` samples at 100 Hz,
quality `D`, encoded with STEIM2. ObsPy 1.5.1 decoded the samples without gaps,
overlaps, interpolation or resampling. No waveform differential time, filtering,
response correction or inversion input was produced.

The [availability discovery](../discovery_001/README.md) preserves the official
USGS/EarthScope starting points and exact NCEDC routing. These same two records
form existing catalog-difference observation 15108. Their event, origin, pick,
association, channel, epoch and original source hashes remain in the copied
`probe_identity.json` and `partner_probe_identity.json`, and in every raw reply's
identifier attachment. They are not an altered event or station selection.

Both use `NC.JPR.02.EHZ` (`FDSN:NC_JPR_02_E_H_Z`):

| Record | Event resource ID | Pick resource ID | Native epoch | First and last sample UTC |
| --- | --- | --- | --- | --- |
| `waveform.mseed` | `quakeml:NC.anss.org/Event/NC/238035` | `quakeml:NC.anss.org/Arrival/NC/36225834` | 1990-07-31 21:10 through 1992-03-26 21:00 | 1991-11-22 16:07:22.230 through 16:07:27.220 |
| `partner_waveform.mseed` | `quakeml:NC.anss.org/Event/NC/30083101` | `quakeml:NC.anss.org/Arrival/NC/45479094` | 1995-08-03 18:15 through 1997-01-29 22:30 | 1995-09-08 04:15:37.560 through 04:15:42.550 |

Requests span the half-open five-second interval from one second before to
four seconds after each pick. At 100 Hz this contains 500 samples, ending
0.01 s before the exclusive endpoint. The initial local check incorrectly
required a sample at that endpoint, effectively asking for 501 samples.
`initial_coverage_check.py` and `initial_coverage_failure.json` preserve that
failed check and the identified decoded result. Correcting the interval
arithmetic changed no request, raw byte, sample or identifier. The first
waveform was reused from the pinned cache before retrieving the partner.

## Instrument responses and identities

Two bounded `level=response` requests to the
[NCEDC station service](https://service.ncedc.org/fdsnws/station/1/) returned
the exact original channel epochs, each with three response stages. The full
Response elements have identical canonical content, including poles, zeros and
gains. This is a comparison of retrieved provider descriptions, not an
assumption based on channel names or independent calibration verification.
Their latitude, longitude, elevation, depth, azimuth, dip, sample rate and
clock-drift fields match the original cached StationXML exactly.

The provider supplies no channel/response public resource IDs in these XML
records and no separate waveform public ID in the miniSEED data. Those fields
remain absent. Derived FDSN channel IDs are labeled explicitly and accompany
native epoch bounds; provider event/origin/pick/association IDs are preserved
verbatim. Request URLs identify retrieved representations, not invented
provider resource IDs.

Raw files are `response.xml`, `partner_response.xml`, `waveform.mseed` and
`partner_waveform.mseed`. Each has immutable-response provenance containing
exact URL, UTC retrieval, status, byte count and SHA-256, plus an identifier
sidecar linking the full native request and parsed response or trace records.
`responses_summary.json` and `waveforms_summary.json` retain the checks and
hashes, including decoded sample hashes. Sample minima/maxima are recorded;
they do not establish that the instrument never clipped or had timing errors.

## Decoder environment and replay

The default Python 3.6 environment lacked ObsPy. The
[official package metadata](https://pypi.org/project/obspy/1.5.1/) supports
Python 3.8 and newer, so a project-local Python 3.11 environment was created at
`tmp/waveform_env`. `requirements.txt` records all installed versions;
`dependencies.json` retains official wheel URLs/hashes and cache locations.
The installer report is preserved in deterministic gzip form. The environment,
pip cache, temporary files and plotting/cache directories stay under `tmp/`.

`acquire.py` reuses the committed immutable-response writer from discovery and
verifies its saved hashes. With no `--fetch` it replays the pinned responses
without network access. From the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 data/authoritative/waveforms/pilot_001/acquire.py responses
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 \
  MPLCONFIGDIR="$PWD/tmp/waveform_mpl" XDG_CACHE_HOME="$PWD/tmp/waveform_cache" \
  TMPDIR="$PWD/tmp/waveform_tmp" tmp/waveform_env/bin/python \
  data/authoritative/waveforms/pilot_001/acquire.py waveforms
```

Initial retrieval added `--fetch`, obtaining both response epochs before any
waveform samples. This pilot establishes access and sample identity for only
these two records. Full-cohort availability, sample quality, waveform similarity
and a documented cross-spectral delay estimator remain separate tasks.
