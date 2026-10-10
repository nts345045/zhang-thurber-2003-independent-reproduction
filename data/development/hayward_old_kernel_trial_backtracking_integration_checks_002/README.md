# Bounded integration checks: compiler-cache correction

Attempt001 configured and compiled successfully, then stopped before numerical tests because its runner expected the CMake compiler cache entry to have type `FILEPATH`. The executed CMake version wrote `STRING` for the explicitly supplied compiler. Its source, logs, executable and terminal failure ledger remain unchanged.

This fresh package changes only that parser: it requires exactly one `CMAKE_CXX_COMPILER` key and still verifies the compiler bytes and original optimized flags. Five saved parser controls cover both types, a missing key, duplicate keys and a malformed entry. All copied C++ candidate and fixture files are byte-identical to attempt001. The old-kernel actual-loop suite has separately passed and is bound by its terminal review.

After independent source review, `run.py` performs the previously scoped core validation, unchanged external-input test and adapted existing guard test. It preserves every outcome and reaps child process groups. No authoritative ray cohort or real inversion is run. Preparation performs only source/hash and parser checks; it does not compile or execute numerical code.
