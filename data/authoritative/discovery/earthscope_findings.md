# EarthScope and NCEDC service discovery

These are service-capability checks. They do not identify the earthquake or station subsets used by Zhang and Thurber (2003), and they are not inversion inputs.

## Successful queries

`earthscope_probe_provenance.json` records retrieval times, exact query URLs, response sizes, and SHA-256 hashes. Both queries returned HTTP 200.

- `earthscope_nc_1989_station.txt`: 364 unique NC stations whose metadata overlap 17–19 October 1989, queried directly from EarthScope. This network-wide result is deliberately broader than the paper geometry.
- `earthscope_nc_1989_fedcatalog.txt`: an EarthScope federated-catalog probe for NC metadata in 36.5–38 degrees N, 123–121 degrees W during the same dates. It identifies 122 station request rows and routes them to the NCEDC station service. The bounding box is a discovery window, not a paper selection criterion.

## Attached station identifiers

Run `python3 data/authoritative/discovery/normalize_earthscope_identifiers.py` from the repository root to regenerate the attachments using only the two saved responses and their provenance. No network request is made and the raw responses remain unchanged.

- `earthscope_nc_1989_stations_identified.csv` preserves all 364 station metadata rows with SEED `NET.STA` names, station resource IDs, coordinates and units, epoch bounds, the exact query URL, the raw-file hash, and the original line number.
- `earthscope_nc_1989_station.txt.identifiers.json` attaches the same per-row identity and epoch information to the raw station response.
- `earthscope_nc_1989_fedcatalog.txt.identifiers.json` attaches station identifiers and source-line references to all 122 request rows, retaining the NCEDC routing information.

Station resource IDs such as `FDSN:NC_AAR` are derived from the provider's network/station codes according to the [FDSN identifier specification](https://docs.fdsn.org/projects/source-identifiers/en/v1.0/definition.html). The raw responses do not supply resource-ID fields; the attachments explicitly record this distinction. A station resource ID identifies the station, not one epoch. Epoch start/end and per-station epoch indices/counts preserve multiple epochs without collapsing them; this snapshot has one epoch for each of 364 stations. An empty epoch end denotes an open interval.

The federated response contains wildcard location and channel selectors. These rows describe requests rather than concrete channels, so their concrete NSLC and channel resource IDs are null. No channel identity is inferred from a wildcard.

Validation checks the saved response hashes and sizes, station code syntax, coordinate bounds, epoch ordering, unique station/epoch keys, and unique request keys. It confirms 364 metadata rows representing 364 stations and 122 request rows representing 122 stations.

## Available authoritative interfaces

EarthScope now documents `https://service.earthscope.org`; requests through `service.iris.edu` redirect. Its [station service](https://service.earthscope.org/fdsnws/station/1/) provides time-dependent station/channel metadata and instrument responses. Its [federated catalog](https://service.earthscope.org/irisws/fedcatalog/1/) discovers channels at contributing FDSN centers and returns the service endpoints.

The [NCEDC service directory](https://service.ncedc.org/) identifies:

- Station metadata: `https://service.ncedc.org/fdsnws/station/1/`
- Event catalog and picks: `https://service.ncedc.org/fdsnws/event/1/`, with `includearrivals=true` for supporting arrivals and picks in QuakeML.
- Waveform time windows: `https://service.ncedc.org/fdsnws/dataselect/1/`
- Waveform availability: `https://service.ncedc.org/fdsnws/availability/1/`
- Preassembled event waveform gathers: `https://service.ncedc.org/ncedcws/eventdata/1/`, selected by event ID and catalog, optionally restricted to channels and times.

The [NCEDC waveform archive announcement](https://ncedc.org/blog/2004/11/11/ncsn-data-available-in-seed.html) documents NCSN event waveforms from March 1984 onward. It warns that some detected events have catalog/pick entries without waveforms, and some shared-network channels originally had incomplete response metadata. No waveform availability for a particular manuscript event is established by this announcement alone.

## Historical compatibility checks required

The [NCEDC 2008 catalog migration](https://ncedc.org/blog/2008/07/18/changes-to-the-ncsn-ncedc.html) remapped historical station/channel names and corrected some channel associations. Modern archived inputs are authoritative, but should not be assumed byte-for-byte identical to the input files used in 2003.

The [2015 depth-datum change](https://ncedc.org/blog/2015/10/07/the-ncss-now-reports-earthquake.html) changed reported catalog depths for events since 1966 from the surface of the location velocity model to the geoid. The underlying model depth and geoid depth are distinct fields. A historical reproduction must state which depth is used and reconcile it with station elevations and the inversion coordinate datum.

The [NCEDC double-difference catalog description](https://ncedc.org/blog/2014/06/02/double-difference-locations-now-available.html) describes relocated hypocenters from later regional processing. It does not establish availability of the 17,955 precise differential times used by Zhang and Thurber (2003). Those later relocated outputs must not be substituted for the manuscript's observations. The inspected station, event, and waveform APIs do not document a manuscript-specific pairwise differential-time endpoint; this is not proof that the original measurement dataset is unavailable elsewhere.

The exact event IDs, station codes, selection dates, and pair list must be established before converting these service capabilities into manuscript inputs. If that identification becomes difficult, the repository's observational-data rule requires clarification from the user before proceeding.
