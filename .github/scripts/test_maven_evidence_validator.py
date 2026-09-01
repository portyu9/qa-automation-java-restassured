"""Regression checks for the repository-owned Maven evidence validator."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from xml.sax.saxutils import escape

from validate_maven_evidence import (
    GOVERNED_FAILSAFE_CLASSES,
    GOVERNED_SUREFIRE_CLASSES,
    validate,
)


def write_report(
    directory: Path,
    suite_name: str,
    tests: int,
    *,
    failures: int = 0,
    errors: int = 0,
    skipped: int = 0,
) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"TEST-{suite_name}.xml"
    path.write_text(
        (
            f'<testsuite name="{escape(suite_name)}" tests="{tests}" '
            f'failures="{failures}" errors="{errors}" skipped="{skipped}">\n'
            "</testsuite>\n"
        ),
        encoding="utf-8",
    )


def populate_clean(root: Path) -> tuple[Path, Path]:
    surefire = root / "surefire"
    failsafe = root / "failsafe"
    write_report(surefire, "com.example.api.LocalHttpContractTest", 2)
    write_report(surefire, "com.example.api.PostApiTest", 2)
    write_report(surefire, "com.example.api.RestAssuredCapabilitiesTest", 4)
    write_report(surefire, "com.example.framework.FrameworkContractTest", 6)
    write_report(failsafe, "com.example.db.PostgresIntegrationTest", 1)
    return surefire, failsafe


def require_failure(action, expected: str) -> None:
    try:
        action()
    except SystemExit as error:
        if expected not in str(error):
            raise AssertionError(f"expected {expected!r} in {error!r}") from error
    else:
        raise AssertionError(f"expected validator failure containing {expected!r}")


def main() -> int:
    with TemporaryDirectory(prefix="maven-evidence-policy-") as temp_dir:
        surefire, failsafe = populate_clean(Path(temp_dir))
        validate("Surefire", surefire, 14, GOVERNED_SUREFIRE_CLASSES)
        validate("Failsafe", failsafe, 1, GOVERNED_FAILSAFE_CLASSES)

    with TemporaryDirectory(prefix="maven-evidence-policy-") as temp_dir:
        surefire, _ = populate_clean(Path(temp_dir))
        (surefire / "TEST-com.example.api.PostApiTest.xml").unlink()
        write_report(surefire, "com.example.framework.AdditionalContractTest", 2)
        require_failure(
            lambda: validate("Surefire", surefire, 14, GOVERNED_SUREFIRE_CLASSES),
            "PostApiTest=0/2",
        )

    with TemporaryDirectory(prefix="maven-evidence-policy-") as temp_dir:
        _, failsafe = populate_clean(Path(temp_dir))
        (failsafe / "TEST-com.example.db.PostgresIntegrationTest.xml").unlink()
        write_report(failsafe, "com.example.db.UnrelatedIntegrationTest", 1)
        require_failure(
            lambda: validate("Failsafe", failsafe, 1, GOVERNED_FAILSAFE_CLASSES),
            "PostgresIntegrationTest=0/1",
        )

    with TemporaryDirectory(prefix="maven-evidence-policy-") as temp_dir:
        surefire, _ = populate_clean(Path(temp_dir))
        write_report(
            surefire,
            "com.example.api.RestAssuredCapabilitiesTest",
            4,
            skipped=1,
        )
        require_failure(
            lambda: validate("Surefire", surefire, 14, GOVERNED_SUREFIRE_CLASSES),
            "skipped tests",
        )

    print("Maven evidence validator self-test: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
