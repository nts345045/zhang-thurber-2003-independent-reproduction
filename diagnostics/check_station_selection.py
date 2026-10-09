#!/usr/bin/env python3
"""Check station selection with invented identities, without observational edits."""
import csv
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from prepare_hayward import excluded_by_study, study_station_policy


def check():
    fixture = dict(network_code="XX", station_code="TEST", station_seed_id="XX.TEST",
                   station_fdsn_source_id="FDSN:XX_TEST", study_membership="unknown",
                   study_evidence_url="", study_evidence_locator="", evidence_summary="Invented fixture")
    checks = []
    (ROOT / "tmp").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=str(ROOT / "tmp")) as directory:
        path = Path(directory) / "policy.csv"

        def save(rows):
            with path.open("w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=list(fixture))
                writer.writeheader()
                writer.writerows(rows)

        save([fixture])
        policy = study_station_policy(path)
        assert not excluded_by_study(fixture, policy, "reproduction")
        assert not excluded_by_study(fixture, {}, "reproduction")
        checks.append("unknown or unlisted membership does not cause exclusion")
        confirmed = dict(fixture, study_membership="excluded", study_evidence_url="https://example.invalid/fixture",
                         study_evidence_locator="Invented written fixture, paragraph 1")
        save([confirmed])
        policy = study_station_policy(path)
        assert excluded_by_study(fixture, policy, "reproduction")
        assert not excluded_by_study(fixture, policy, "additional")
        checks.append("documented exclusion applies only to reproduction")
        save([dict(confirmed, study_membership="included")])
        assert not excluded_by_study(fixture, study_station_policy(path), "reproduction")
        checks.append("documented inclusion remains eligible")
        for name, rows in [
            ("uncited claimed exclusion rejected", [dict(fixture, study_membership="excluded")]),
            ("mismatched station identity rejected", [dict(fixture, station_fdsn_source_id="FDSN:XX_BAD")]),
            ("duplicate policy rejected", [fixture, fixture]),
            ("unsupported membership rejected", [dict(fixture, study_membership="probably_excluded")]),
        ]:
            save(rows)
            try:
                study_station_policy(path)
            except ValueError:
                checks.append(name)
            else:
                raise AssertionError(name)
    result = dict(fixture_kind="invented station and evidence; no authoritative observations modified",
                  checks=checks, passed=len(checks))
    (ROOT / "data/development/station_selection_checks.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    check()
