# Full retained-cohort waveform plan, paused before retrieval

The existing 14,262 absolute picks and 44,718 catalog-derived differences remain
unchanged. This offline audit preserves their full native identities and plans
bounded requests for all 62 NSLCs and 372 used receiver epochs. No network
request, waveform measurement, station exclusion, or pair substitution is made
by this package. New observational retrieval is paused for user clarification
about the established historical CMW1 response gap.

The [CMW1 investigation](../../stations/investigation/cmw1_report.md) recovered
historical operation records, which establish channel identity and geometry.
They do not establish instrument calibration. The pinned EarthScope and NCEDC
StationXML replies begin in 2000, whereas 117 retained picks and 199 catalog
pairs use CMW1 in 1995–1998. No later response is backdated. The audit also
retains 89 picks and 542 catalog differences involving dates before the
archive's documented March 1984 start. The archive announcement is a coverage
lead, not proof of absence at every earlier requested time.

There are 398 picks whose channel code does not end in Z. The audit therefore
reads Dip and Azimuth from their exact cached StationXML channel epochs when
available, instead of inferring orientation from the channel name. Historical
operation records have no orientation fields. `summary.json` distinguishes
provider-declared vertical, provider-declared nonvertical, and missing
orientation. These fields identify a processing-scope question relative to the
written vertical-component method; they do not remove any catalog observation.

## Existing authoritative evidence and bulk capabilities

The earlier discovery began with [USGS ComCat](https://earthquake.usgs.gov/data/comcat/)
and [EarthScope's federated catalog](https://service.earthscope.org/irisws/fedcatalog/1/),
which routed the two exact pilot windows to NCEDC. The actual cohort's event,
origin, association, and pick identities came from the NCEDC FDSN event API;
USGS/ComCat supported the initial discovery. No waveform resource URI was
supplied for these archived picks. The
[preserved service documentation](../discovery_001/README.md) describes
plain-text POST lists of `NET STA LOC CHA START END` for the federated catalog,
[NCEDC availability](https://service.ncedc.org/fdsnws/availability/1/), and
[NCEDC miniSEED dataselect](https://service.ncedc.org/fdsnws/dataselect/1/).
Empty location is serialized as `--` in a request and retained as empty in
native tables. Availability `/query` returns spans; `/extent` alone cannot
establish continuity. Quality, sample rate, overlaps, and gaps must remain
separate; this plan requests no merging across them.

The federated-catalog documentation also identifies the FDSN station POST
selection format. The proposed NCEDC station endpoint uses `level=response`
and XML. Its response-level POST capability still needs an initial bounded
provider check when retrieval resumes; no successful bulk query is claimed.
Routing must be established for every requested native channel/time interval,
not inherited solely from the two pilot windows. The existing two full JPR
response epochs cover the metadata epochs of 70 retained picks (45 and 25),
but only two five-second waveform windows have actually been retrieved.
Responses cannot be assumed equivalent across epochs from a common NSLC.

## Bounded sequence after clarification

1. Send EarthScope station and dataselect routing requests in batches of at
   most 25 exact used-epoch intervals. Validate returned concrete codes,
   intervals, and authoritative provider endpoints. Preserve all routing rows,
   including missing or conflicting routes.
2. Request full response metadata for those same 372 used epochs, in 15
   batches of at most 25 intervals. The interval spans only the retained pick
   windows within an epoch. Preserve all returned channel/response epochs,
   and require unique coverage of each actual waveform window. Compare native
   geometry and dates, retain all response stages, and distinguish any provider
   response IDs from derived channel identifiers. Missing historical response
   information remains missing.
3. Query availability for every pick's P−1 to P+4 second window, in 143
   batches of at most 100 windows. Keep returned spans unmerged. Classify every
   original pick and both members of all 44,718 pairs; a missing row or gap is
   not silently dropped or replaced. No automatic retries, alternate aliases,
   or new cohort are authorized by this plan if access/identity becomes difficult.
4. After metadata/availability review, retrieve the same bounded windows using
   the established route and save the original miniSEED bytes. Planned batching
   is 143 requests of at most 100 windows, not a selection cap. Decode with the
   pinned standard ObsPy environment from [pilot_001](../pilot_001/README.md).
   Verify NSLC, response epoch, sampling rate/grid, overlaps/gaps, and half-open
   sample support. Do not interpolate missing samples or equate responses
   across epochs. Archive-quality choice and multiple overlapping records
   require an explicit documented rule before broad processing.
5. Any later signal processing keeps the existing pair graph and the
   [declared method assumptions](../../../development/waveform_correlation_specification/README.md).
   Every measured or rejected pair retains both native event/origin/pick/
   association IDs and response epochs, raw hashes, and local derived IDs.
   Preserve the failed pilot and the unchanged coherence criterion. Broad
   measurements are not exact replication of undocumented paper processing.

Batch sizes are client choices to bound memory and request size, not published
provider limits. Requests run sequentially initially; an HTTP/access/identity
failure stops retrieval for clarification rather than changing the selection.
At 100 samples/s and int32, the planned 71,310 seconds represent 28.524 MB of
sample payload before miniSEED overhead, assuming all records have that rate.
The actual channel rates, record packing, raw response size, and availability
remain to be validated. Response XML and native metadata add storage.

## Files and checks

`identified_picks.csv.gz` contains every original absolute row plus request
window and audit flags. `identified_catalog_differences.csv.gz` contains every
original catalog-difference row with affected-pair flags and both orientation
statuses. `identified_used_epochs.csv.gz` carries all used station metadata
rows, provider orientation/rate fields where supplied, and pick-count/time
bounds. None is solver replacement input.

`planned_batches.json.gz` contains exact prospective POST bodies and per-line
native identities, references to the full pick table/hash, and request hashes.
All are explicitly unsubmitted. `summary.json` pins the original cohort,
raw authoritative metadata and service-document hashes, planned batches, and
all output hashes. Raw cached provider files and their identifier/provenance
sidecars remain unchanged in their original authoritative directories.

`prepare.py` performs this offline build with explicit native event/station/
pick/pair joins and source-hash validation; it has no networking dependency.
Run a copied helper in a fresh sibling package directory to rebuild. Existing
outputs are exclusive-created, so a populated directory is not overwritten.
