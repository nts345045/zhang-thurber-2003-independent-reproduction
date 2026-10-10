# Compile failure retained

The first integration adoption did not compile (CMake build exit 2; controller exit 1). The maintained main lacked the two checked I/O helpers used by the reviewed old-kernel exporter. Its existing status writer also used an unchecked close. No ray or inversion was evaluated. The copied source, logs, and terminal receipt remain unchanged.

The separate [second adoption](../hayward_full_dd_geometry_adoption_002/adoption.json) adds exactly the reviewed helper bodies and checked status close before compiling again.
