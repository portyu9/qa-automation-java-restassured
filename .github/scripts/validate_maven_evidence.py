"""Fail closed unless Maven test reports prove the intended suite executed."""
from __future__ import annotations

import argparse
from pathlib import Path
import xml.etree.ElementTree as ET


def parse_reports(directory: Path) -> tuple[int, int, int, int, int]:
    files = sorted(directory.glob("TEST-*.xml"))
    if not files:
        raise SystemExit(f"missing Maven XML evidence: {directory}/TEST-*.xml")

    totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    for report in files:
        root = ET.parse(report).getroot()
        if root.tag != "testsuite":
            raise SystemExit(f"unexpected Maven report root in {report}: {root.tag}")
        for key in totals:
            try:
                value = int(root.attrib.get(key, "0"))
            except ValueError as exc:
                raise SystemExit(f"non-integer {key} in {report}") from exc
            if value < 0:
                raise SystemExit(f"negative {key} in {report}")
            totals[key] += value

    executed = totals["tests"] - totals["skipped"]
    return len(files), totals["tests"], totals["failures"], totals["errors"], totals["skipped"], executed


def validate(label: str, directory: Path, minimum_executed: int) -> None:
    files, tests, failures, errors, skipped, executed = parse_reports(directory)
    if executed < minimum_executed:
        raise SystemExit(
            f"{label} executed-test floor not met: executed={executed}, required={minimum_executed}"
        )
    if failures or errors:
        raise SystemExit(
            f"{label} evidence is not clean: failures={failures}, errors={errors}"
        )
    if skipped:
        raise SystemExit(f"{label} required evidence contains skipped tests: skipped={skipped}")
    print(
        f"validated {label} evidence: reports={files}, tests={tests}, executed={executed}, failures=0, errors=0, skipped=0"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--surefire-min", type=int, default=14)
    parser.add_argument("--failsafe-min", type=int, default=0)
    args = parser.parse_args()

    if args.surefire_min < 1 or args.failsafe_min < 0:
        raise SystemExit("evidence floors must be non-negative and Surefire must be at least one")

    validate("Surefire", Path("target/surefire-reports"), args.surefire_min)
    if args.failsafe_min:
        validate("Failsafe", Path("target/failsafe-reports"), args.failsafe_min)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
