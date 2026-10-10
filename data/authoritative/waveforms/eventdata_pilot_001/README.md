# Two identified NCEDC event-gather requests

The official NCEDC eventdata endpoint returned HTTP 204 and an empty body
for each of the two declared requests. No waveform samples were returned,
so no decoding, correlation, coherence calculation, or new differential
measurement was possible. These responses describe the exact event/channel/
time requests below; they do not establish historical waveform absence,
authorize channel aliases, or exclude catalog observations.

The pilot retains original catalog-difference row **21796**, numerical events
11 and 13, and receiver epoch 130. Both picks use `NC.CMC..EHZ`, with a valid
empty location and the derived FDSN source identifier `FDSN:NC_CMC__E_H_Z`.
The provider channel epoch is 1984-01-01T00:00:00 through
1984-06-05T20:50:00, with 100 Hz sampling and dip -90 degrees.

| Original pick row | Provider event resource ID | Provider pick resource ID | Requested UTC window |
| --- | --- | --- | --- |
| 133 | `quakeml:NC.anss.org/Event/NC/12434` | `quakeml:NC.anss.org/Arrival/NC/11001454` | 1984-03-27 03:48:40.030 through 03:48:45.030 |
| 159 | `quakeml:NC.anss.org/Event/NC/12437` | `quakeml:NC.anss.org/Arrival/NC/11002359` | 1984-03-27 04:10:42.850 through 04:10:47.850 |

`native_picks.csv`, `native_pair.csv`, `native_events.csv`, and
`native_epoch.csv` preserve the complete original values, including origin,
arrival, channel, epoch, resource identifiers, and source hashes. `plan.json`
pins the prior reviewed inventory and original authoritative sources. Native
indices are numerical references only, not substitutes for resource IDs.

## Documented request and observed outcome

The prior discovery began with USGS and EarthScope. The saved EarthScope
route for this exact channel points to NCEDC. The current official
[eventdata documentation](https://service.ncedc.org/ncedcws/eventdata/1/)
was retrieved on 2026-10-10 and saved unchanged as `current_eventdata.html`.
It documents NCSS catalog plus event identifiers, per-channel restricted
times, miniSEED output, and `--` for an empty POST location. The provider's
numeric event IDs are explicit QuakeML attributes and match the original
NCSS catalog acquisition; they were not guessed from an alternate event.

`acquire.py prepare` independently checked both raw QuakeML pick times and
SEED identities, the provider event IDs, and the unique raw StationXML
channel epoch/rate/dip. The two POST bodies then used only `eventid`,
`catalog=NCSS`, and the exact six-field channel/time selection. No wildcard,
alternate location, broader time window, response calibration, or CMW1
request was introduced.

`event_12434.response` and `event_12437.response` are the unchanged empty
HTTP 204 response bodies. Their `.provenance.json` and `.identifiers.json`
sidecars retain the exact endpoint, request/response hashes, UTC timestamps,
HTTP status, and full native request context. Request bodies have their own
identifier sidecars. Missing provider waveform resource IDs remain null.
The original response-kind label says inspection was pending; the terminal
`acquisition_summary.json` records both final `provider_returned_no_data`
outcomes. The original no-reported-span inventory records remain unchanged.

The pilot stops here. No undocumented route, provider contact, new event,
alias, repeated request, or alternative archive search was attempted. The
98 prior accepted measurements and all 44,718 catalog pairs are untouched.
Instrument calibration remains unnecessary for the authorized normalized-CC
workflow; it was not used as a gate in this pilot.

## Reproducibility and limitations

The three executed stages were `prepare`, `docs`, and `fetch`, using
`tmp/waveform_env/bin/python` with project-local cache/temp environment
variables. Their terminal ledgers and `execution_environment.json` preserve
source hashes, commands and versions. Do not rerun acquisition over this
completed directory. `readback.py` verifies the saved request/native/hash
joins without network access and writes a fresh `readback.json`.

The source is a bounded two-record helper. Its fetch stage rechecks original
inputs but does not independently bind a changed `plan.json` to the earlier
documentation request. The saved readback explicitly verifies that actual
binding for this execution. Any later generalized helper should enforce it
before retrieval. No decoder adaptation was needed because neither response
contained samples.
