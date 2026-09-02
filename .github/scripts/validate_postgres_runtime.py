"""Validate the repository-owned PostgreSQL Testcontainers runtime provenance."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src" / "test" / "java" / "com" / "example" / "db" / "PostgresIntegrationTest.java"
DOCKERFILE = ROOT / "docker" / "postgres-test.Dockerfile"
SECURITY = ROOT / ".github" / "workflows" / "security.yml"

IMAGE_NAME = "qa-restassured-postgres:16.15-hardened"
DOCKERFILE_PATH = "docker/postgres-test.Dockerfile"
GO_BUILDER = (
    "golang:1.26.6-alpine3.24@sha256:"
    "3889b425f035be855a72fb4755265311293b6d414521f0a519d819df32222d83"
)
POSTGRES_BASE = (
    "postgres:16.15-alpine@sha256:"
    "cf78e76683b9ca8c5733cbbdce6c9262b45b6767934dd0a95e671f9a0fc20685"
)
GOSU_TAG = "1.19"
GOSU_COMMIT = "6456aaa0f3c854d199d0f037f068eb97515b7513"
OPENSSL_VERSION = "3.5.8-r0"


def _require(text: str, token: str, surface: str, errors: list[str]) -> None:
    if token not in text:
        errors.append(f"{surface} is missing required PostgreSQL runtime contract: {token}")


def validate(errors: list[str]) -> None:
    for path in (SOURCE, DOCKERFILE, SECURITY):
        if not path.is_file():
            errors.append(f"required PostgreSQL runtime surface is missing: {path.relative_to(ROOT)}")
            return

    source = SOURCE.read_text(encoding="utf-8")
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")
    security = SECURITY.read_text(encoding="utf-8")

    source_tokens = (
        f'private static final String POSTGRES_IMAGE = "{IMAGE_NAME}";',
        f'Path.of("{DOCKERFILE_PATH}")',
        "new ImageFromDockerfile(POSTGRES_IMAGE, false)",
        ".withDockerfile(POSTGRES_DOCKERFILE)",
        "DockerImageName.parse(POSTGRES_IMAGE_BUILD.get())",
        '.asCompatibleSubstituteFor("postgres")',
        "new PostgreSQLContainer<>(POSTGRES_DOCKER_IMAGE)",
    )
    for token in source_tokens:
        _require(source, token, SOURCE.relative_to(ROOT).as_posix(), errors)

    from_lines = [line.strip() for line in dockerfile.splitlines() if line.strip().startswith("FROM ")]
    expected_from = [f"FROM {GO_BUILDER} AS gosu-builder", f"FROM {POSTGRES_BASE}"]
    if from_lines != expected_from:
        errors.append(
            "docker/postgres-test.Dockerfile must use exactly the governed Go builder and PostgreSQL base digests"
        )

    docker_tokens = (
        f"ARG GOSU_COMMIT={GOSU_COMMIT}",
        f"ARG GOSU_TAG={GOSU_TAG}",
        'git -C /src fetch --depth 1 https://github.com/tianon/gosu.git "refs/tags/${GOSU_TAG}"',
        'test "$(git -C /src rev-parse HEAD)" = "$GOSU_COMMIT"',
        "ENV CGO_ENABLED=0",
        "go mod download",
        "go build -trimpath -ldflags='-d -w' -buildvcs=true -o /out/gosu github.com/tianon/gosu",
        "grep -F 'go1.26.6' /out/gosu-build-info.txt",
        "COPY --from=gosu-builder /out/gosu /usr/local/bin/gosu",
        f"'libcrypto3={OPENSSL_VERSION}'",
        f"'libssl3={OPENSSL_VERSION}'",
        r"grep -q '^libcrypto3-3\.5\.8-r0 '",
        r"grep -q '^libssl3-3\.5\.8-r0 '",
        "gosu nobody true",
    )
    for token in docker_tokens:
        _require(dockerfile, token, DOCKERFILE.relative_to(ROOT).as_posix(), errors)

    if re.search(r"\bapk\s+upgrade\b", dockerfile):
        errors.append("PostgreSQL test image must not use a floating apk upgrade operation")
    if re.search(r"^FROM\s+[^\n@]+$", dockerfile, re.MULTILINE):
        errors.append("every PostgreSQL test image FROM reference must be digest-pinned")
    if re.search(r"(?mi)^\s*USER\s+root\s*$", dockerfile):
        errors.append("PostgreSQL test image must not add an explicit root USER declaration")
    if "apk info -v" in dockerfile:
        errors.append("PostgreSQL package version checks must use installed-package list output, not apk info metadata")

    security_tokens = (
        "  postgres-image:",
        "python3 .github/scripts/validate_postgres_runtime.py",
        f"POSTGRES_TEST_IMAGE: {IMAGE_NAME}",
        f"POSTGRES_TEST_DOCKERFILE: {DOCKERFILE_PATH}",
        'docker build --pull=false -f "$POSTGRES_TEST_DOCKERFILE" -t "$POSTGRES_TEST_IMAGE" .',
        "scan-type: image",
        "image-ref: ${{ env.POSTGRES_TEST_IMAGE }}",
        "postgres-image-security-evidence-${{ github.run_id }}",
        "needs: [codeql, maven-dependencies, postgres-image, trivy-repository, dependency-review]",
        '[[ "$POSTGRES_IMAGE" == "success" ]]',
    )
    for token in security_tokens:
        _require(security, token, SECURITY.relative_to(ROOT).as_posix(), errors)


def main() -> int:
    errors: list[str] = []
    validate(errors)
    if errors:
        print("PostgreSQL runtime provenance validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(
        "PostgreSQL runtime provenance: Testcontainers build wiring, immutable bases, "
        "gosu source/toolchain, exact OpenSSL patches, and Security image scan are consistent"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
