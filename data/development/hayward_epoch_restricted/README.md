# Strict metadata-epoch sensitivity subset

This preserves the first prepared authoritative subset before correcting an
unnecessary same-epoch pairing restriction. No inversion was performed.
All input identities remain in the gzip-compressed CSV files; compression is
lossless. The manifest records the exact preparation hash and counts. The
snapshot helper is provenance, not a standalone relocated build command.

The 1 km/400-update initial-ray check converged for 20/32 sampled paths;
refinement to 0.5 km/1,000 updates converged for 32/32. The maximum travel-time
difference was 0.000406012 s. Its diagnostics retain observation/source/receiver
identity mappings and refer to this frozen observations.csv.

Strict matching produced 1,092 events, 14,262 absolute observations, 33,280 catalog
differences, 3,293 pairs, 132 graph components and 111 unlinked events. All 62 NSLCs
had identical reported positions across their used 372 epochs. The primary
selection therefore permits same-position links across native epochs while
preserving each side's epoch and a calibration-change flag.
