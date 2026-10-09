# AGENTS.md

This repository should use an absolutely minimal research style.

- Keep analyses and code simple, direct, and readable.
- Add code, dependencies, and directory structure only when they are needed to achieve project goals.
- Prefer small functions and plain data over custom classes or frameworks.
- This is not production code. It is an initial investigation intended to clarify the physics. Don't worry about backwards compatibility.
- Complex code inhibits learning. Keep it simple.
- Start from first principles. Do not invent physics.
- Do not impose heuristic or contrived constraints, conditions, or equations of any kind unless they are clearly requested and made explicit.
- State assumptions, units, boundary conditions, and the observational prediction of each model.
- Separate observations, calculations, inferences, and speculative mechanisms.
- Follow `brad-lipovsky-academic-style-guide.md` for academic prose.
- Save notebooks with figures and outputs intact, then commit and push them to GitHub.

## Observational data for reproduction

- If a reproduction uses real station and/or earthquake data, retrieve those data and their associated metadata from authoritative sources, such as USGS, EarthScope, or the Southern California Seismic Network.
- Start with USGS and EarthScope web services to locate the required data and metadata.
- All saved real station and earthquake data and metadata must carry their resource IDs. Preserve provider event, origin, pick, and other resource IDs; attach station/channel SEED naming codes (network and station; full network.station.location.channel for channels) and FDSN source identifiers, with metadata epochs. Preserve valid empty location codes.
- Keep these identifiers in derived files and any mapping to numerical solver indices. Differential observations must retain both event/pick identities and the common channel identity. Preserve raw provider responses unchanged and attach identifier sidecars when the source format cannot hold the required fields. Distinguish standardized identifiers derived from SEED codes from provider-supplied resource IDs; do not invent missing identities.
- If locating, accessing, or identifying the required data or metadata becomes difficult, stop and ask the user for clarification before proceeding.
- Investigate metadata before excluding a station. If written study evidence establishes that a station was excluded, omit its observations from the reproduction selection, retain the identified records and metadata, and support a separate later run with the additional data. Record the evidence and differences between selections. Unknown study membership is not evidence of exclusion.
