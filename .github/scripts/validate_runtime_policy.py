"""Validate that Maven/runtime enforcement matches every deliberately qualified Java surface."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POM = ROOT / "pom.xml"
CI = ROOT / ".github" / "workflows" / "ci.yml"
EXTENDED = ROOT / ".github" / "workflows" / "extended.yml"
SECURITY = ROOT / ".github" / "workflows" / "security.yml"

QUALIFIED_MAJORS = (17, 21, 25)
EXPECTED_RANGE = "[17,18),[21,22),[25,26)"
MINIMUM_MAJOR = min(QUALIFIED_MAJORS)
CURRENT_MAJOR = max(QUALIFIED_MAJORS)


def fail(message: str) -> None:
    raise SystemExit(f"runtime policy contract failed: {message}")


def read_pom_policy() -> tuple[str, int]:
    root = ET.parse(POM).getroot()
    namespace = {"m": "http://maven.apache.org/POM/4.0.0"}
    java_range = root.find(".//m:requireJavaVersion/m:version", namespace)
    compiler_release = root.find("m:properties/m:maven.compiler.release", namespace)
    if java_range is None or not (java_range.text or "").strip():
        fail("pom.xml does not define requireJavaVersion/version")
    if compiler_release is None or not (compiler_release.text or "").strip():
        fail("pom.xml does not define maven.compiler.release")
    release_text = (compiler_release.text or "").strip()
    if not release_text.isdigit():
        fail(f"maven.compiler.release must be a numeric Java major, got {release_text!r}")
    return (java_range.text or "").strip(), int(release_text)


def java_versions(workflow: str) -> list[int]:
    return [int(value) for value in re.findall(r"java-version:\s*[\"']?(\d+)[\"']?\s*$", workflow, re.MULTILINE)]


def main() -> int:
    java_range, compiler_release = read_pom_policy()
    if java_range != EXPECTED_RANGE:
        fail(
            f"requireJavaVersion must be {EXPECTED_RANGE!r} for qualified majors "
            f"{QUALIFIED_MAJORS}, got {java_range!r}"
        )
    if compiler_release != MINIMUM_MAJOR:
        fail(
            f"maven.compiler.release must preserve the minimum qualified Java API level "
            f"{MINIMUM_MAJOR}, got {compiler_release}"
        )

    ci = CI.read_text(encoding="utf-8")
    extended = EXTENDED.read_text(encoding="utf-8")
    security = SECURITY.read_text(encoding="utf-8")

    matrix_match = re.search(r"matrix:\s*\n(?:.*\n)*?\s+java:\s*\[([^\]]+)\]", ci)
    if not matrix_match:
        fail("ci.yml must define the fast Java compatibility matrix")
    fast_majors = tuple(sorted(int(value.strip()) for value in matrix_match.group(1).split(",")))
    expected_fast = tuple(major for major in QUALIFIED_MAJORS if major != CURRENT_MAJOR)
    if fast_majors != expected_fast:
        fail(f"ci.yml fast matrix must qualify {expected_fast}, got {fast_majors}")

    ci_exact = java_versions(ci)
    if CURRENT_MAJOR not in ci_exact:
        fail(f"ci.yml must run the current full verification on Java {CURRENT_MAJOR}")
    unsupported_ci = sorted(set(ci_exact) - set(QUALIFIED_MAJORS))
    if unsupported_ci:
        fail(f"ci.yml uses Java majors outside the qualified policy: {unsupported_ci}")

    extended_majors = sorted(set(java_versions(extended)))
    if extended_majors != [MINIMUM_MAJOR]:
        fail(
            f"extended.yml must run the minimum-runtime full lifecycle only on Java {MINIMUM_MAJOR}, "
            f"got {extended_majors}"
        )

    security_majors = sorted(set(java_versions(security)))
    if security_majors != [CURRENT_MAJOR]:
        fail(
            f"security.yml Java compilation/dependency-analysis jobs must use the current qualified "
            f"Java {CURRENT_MAJOR}, got {security_majors}"
        )

    print(
        "runtime policy contract passed: compiler API level Java "
        f"{compiler_release}; Maven Enforcer permits only {QUALIFIED_MAJORS}; CI qualifies all lines; "
        f"Extended replays Java {MINIMUM_MAJOR}; Security compiles/analyzes on Java {CURRENT_MAJOR}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
