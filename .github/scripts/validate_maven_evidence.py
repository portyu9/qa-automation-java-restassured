"""Fail closed unless Maven reports prove the governed test topology executed."""
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import xml.etree.ElementTree as ET

GOVERNED_SUREFIRE_CLASSES = {
    "com.example.api.LocalHttpContractTest": 2,
    "com.example.api.PostApiTest": 2,
    "com.example.api.RestAssuredCapabilitiesTest": 4,
}
GOVERNED_FAILSAFE_CLASSES = {
    "com.example.db.PostgresIntegrationTest": 1,
}


def parse_reports(directory: Path) -> tuple[int, int, int, int, int, int, Counter[str]]:
    files = sorted(directory.glob("TEST-*.xml"))
    if not files:
        raise SystemExit(f"missing Maven XML evidence: {directory}/TEST-*.xml")

    totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    executed_by_class: Counter[str] = Counter()
    for report in files:
        root = ET.parse(report).getroot()
        if root.tag != "testsuite":
            raise SystemExit(f"unexpected Maven report root in {report}: {root.tag}")
        suite_name = root.attrib.get("name", "").strip()
        if not suite_name:
            raise SystemExit(f"Maven report lacks testsuite name: {report}")

        values: dict[str, int] = {}
        for key in totals:
            try:
                value = int(root.attrib.get(key, "0"))
            except ValueError as exc:
                raise SystemExit(f"non-integer {key} in {report}") from exc
            if value < 0:
                raise SystemExit(f"negative {key} in {report}")
            totals[key] += value
            values[key] = value

        suite_executed = values["tests"] - values["skipped"]
        if suite_executed < 0:
            raise SystemExit(f"skipped tests exceed total tests in {report}")
        executed_by_class[suite_name] += suite_executed

    executed = totals["tests"] - totals["skipped"]
    return (
        len(files),
        totals["tests"],
        totals["failures"],
        totals["errors"],
        totals["skipped"],
        executed,
        executed_by_class,
    )


def require_governed_classes(
    label: str,
    executed_by_class: Counter[str],
    governed: dict[str, int],
) -> None:
    missing = {
        class_name: (executed_by_class.get(class_name, 0), minimum)
        for class_name, minimum in governed.items()
        if executed_by_class.get(class_name, 0) < minimum
    }
    if missing:
        detail = ", ".join(
            f"{class_name}={actual}/{minimum}"
            for class_name, (actual, minimum) in sorted(missing.items())
        )
        raise SystemExit(f"{label} governed test-class floor not met: {detail}")


def validate(
    label: str,
    directory: Path,
    minimum_executed: int,
    governed: dict[str, int] | None = None,
) -> None:
    files, tests, failures, errors, skipped, executed, executed_by_class = parse_reports(directory)
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

    governed = governed or {}
    require_governed_classes(label, executed_by_class, governed)
    governed_summary = ", ".join(
        f"{class_name.rsplit('.', 1)[-1]}={executed_by_class[class_name]}"
        for class_name in sorted(governed)
    )
    suffix = f", governed=[{governed_summary}]" if governed_summary else ""
    print(
        f"validated {label} evidence: reports={files}, tests={tests}, executed={executed}, "
        f"failures=0, errors=0, skipped=0{suffix}"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--surefire-min", type=int, default=14)
    parser.add_argument("--failsafe-min", type=int, default=0)
    args = parser.parse_args()

    if args.surefire_min < 1 or args.failsafe_min < 0:
        raise SystemExit("evidence floors must be non-negative and Surefire must be at least one")

    validate(
        "Surefire",
        Path("target/surefire-reports"),
        args.surefire_min,
        GOVERNED_SUREFIRE_CLASSES,
    )
    if args.failsafe_min:
        validate(
            "Failsafe",
            Path("target/failsafe-reports"),
            args.failsafe_min,
            GOVERNED_FAILSAFE_CLASSES,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
