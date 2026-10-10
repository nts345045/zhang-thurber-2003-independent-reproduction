# Clean committed-input plot replay

Both documented plot commands ran once from this fresh tree exported from main
commit `6a8f79167db4c932a9fa37e6097e7ab3e05b36df`. The export contains only the two
published plot packages, the Loma plotting helper, their declared tracked
scientific dependencies, and the old Figure 2 PDF/PNG: 65 regular files,
53,640,324 bytes. No scientific-input symlink is present. The original Loma
simulation directory is absent; the six committed package input copies suffice.

The existing project-local Python 3.11 / Matplotlib 3.11.2 runtime was reused.
All Matplotlib, XDG and temporary caches were directed inside this fresh tree.
No software installation, data request, waveform measurement, inversion or
report build was performed.

Both plotting commands actually completed and were reaped with exit 0:
Loma session 76302 / terminal `2a89bc`; CC session 45395 / terminal `e9cb36`.
The saved-only comparison also returned exit 0 (`b46ee6`). Exact commands,
environment, exported-file hashes and closed output hashes are in `logs/`.

- Loma: all nine saved scientific outputs, including PDF/PNG and six native
  input copies, are byte-identical. Counts and exact identity/coordinate joins
  remain 724 sources, 52 receiver epochs and 48 horizontal grid nodes.
- CC: 98 pairs, 103 participating events, 1,092 catalog events, four channels,
  22 epochs and 38 cross-epoch pairs remain unchanged; all 3,385 plotting checks
  pass. PNG, plotted coordinates, complete identifiers, captions and sidecars
  are byte-identical.
- CC PDF SHA-256 is
  `bf504924187a40b6537a491d63d3119c54fe65421479a2f7e114f0226139ce6c`.
  The archived PDF is
  `0ee7e204cbab96d693607a8785ad66e9a831198ea3a5451b6074884b187355c7`.
  Exact byte comparison after replacing the single CreationDate field shows
  that the timestamp is the only difference. No scientific output was changed.

All 65 exported committed files are still byte-identical. This establishes
clean committed-data replay of these two plots with the existing runtime;
it is not a fresh software installation or a clean end-to-end project build.
