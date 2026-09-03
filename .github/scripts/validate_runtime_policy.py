"""Validate that Maven runtime enforcement matches the deliberately qualified Java lines."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POM = ROOT / "pom.xml"
CI = ROOT / ".github" / "workflows" / "ci.yml"
EXTENDED = ROOT / ".github" / "workflows" / "extended.yml"

QUALIFIED_MAJORS = (17, 21, 25)
EXPECTED_RANGE = "[17,18),[21,22),[25,26)"


def fail(message: str) -> None:
    raise SystemExit(f"runtime policy contract failed: {message}")


def read_java_range() -> str:
    root = ET.parse(POM).getroot()
    namespace = {"m": "http://maven.apache.org/POM/4.0.0"}
    node = root.find(".//m:requireJavaVersion/m:version", namespace)
    if node is None or not (node.text or "").strip():
        fail("pom.xml does not define requireJavaVersion/version")
    return (node.text or "").strip()


def main() -> int:
    java_range = read_java_range()
    if java_range != EXPECTED_RANGE:
        fail(
            f"requireJavaVersion must be {EXPECTED_RANGE!r} for qualified majors "
            f"{QUALIFIED_MAJORS}, got {java_range!r}"
        )

    ci = CI.read_text(encoding="utf-8")
    extended = EXTENDED.read_text(encoding="utf-8")

    if not re.search(r"matrix:\s*\n(?:.*\n)*?\s+java:\s*\[17,\s*21\]", ci):
        fail("ci.yml must qualify Java 17 and 21 in the fast compatibility matrix")
    if not re.search(r"java-version:\s*25\b", ci):
        fail("ci.yml must run the current full verification on Java 25")
    if not re.search(r"java-version:\s*17\b", extended):
        fail("extended.yml must run the minimum-runtime full lifecycle on Java 17")

    print(
        "runtime policy contract passed: Maven Enforcer allows only Java 17/21/25 and CI qualifies all three lines"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
