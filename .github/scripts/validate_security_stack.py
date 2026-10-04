"""Fail closed when REST Assured scanner coverage drifts."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SECURITY_WORKFLOW = ROOT / ".github" / "workflows" / "security.yml"
CODEQL_BY_SUFFIX = {
    ".java": "java-kotlin",
    ".py": "python",
    ".pyi": "python",
}
KNOWN_CODE_SUFFIXES = set(CODEQL_BY_SUFFIX) | {
    ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".go", ".c", ".cc", ".cpp",
    ".cxx", ".h", ".hh", ".hpp", ".cs", ".kt", ".kts", ".rb", ".rs", ".swift",
    ".php", ".scala", ".lua", ".ps1", ".sh", ".bash", ".zsh", ".ksh",
}
SHELL_SHEBANG = re.compile(r"^#!.*\b(?:ba|da|k|z)?sh\b")


def tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, check=True, capture_output=True
    )
    return [ROOT / item.decode("utf-8") for item in result.stdout.split(b"\x00") if item]


def main() -> int:
    errors: list[str] = []
    files = tracked_files()
    workflow_text = SECURITY_WORKFLOW.read_text(encoding="utf-8")
    discovered_codeql: set[str] = set()
    shell_entrypoints: list[Path] = []

    for path in files:
        suffix = path.suffix.lower()
        relative = path.relative_to(ROOT)
        if suffix in CODEQL_BY_SUFFIX:
            discovered_codeql.add(CODEQL_BY_SUFFIX[suffix])
        elif suffix in KNOWN_CODE_SUFFIXES:
            errors.append(
                f"tracked first-party source {relative} has no declared scanner mapping"
            )

        if path.is_file():
            try:
                first_line = path.open("r", encoding="utf-8").readline().rstrip("\n")
            except UnicodeDecodeError:
                first_line = ""
            if SHELL_SHEBANG.search(first_line):
                shell_entrypoints.append(relative)

    expected_codeql = {"java-kotlin", "python"}
    if discovered_codeql != expected_codeql:
        errors.append(
            "first-party CodeQL language inventory mismatch: "
            f"found {sorted(discovered_codeql)}, expected {sorted(expected_codeql)}"
        )

    unexpected_shell = [str(item) for item in shell_entrypoints if str(item) != "mvnw"]
    if unexpected_shell:
        errors.append(
            "tracked shell entrypoints require an explicit scanner/provenance policy: "
            + ", ".join(unexpected_shell)
        )
    if Path("mvnw") not in shell_entrypoints:
        errors.append("checksum-pinned Maven wrapper entrypoint mvnw was not detected")

    workflows = sorted((ROOT / ".github" / "workflows").glob("*.y*ml"))
    if not workflows:
        errors.append("no GitHub Actions workflows found for CodeQL Actions analysis")

    required_contracts = {
        "Java CodeQL analysis": "languages: java-kotlin",
        "Python and Actions CodeQL analysis": "languages: python,actions",
        "security-extended queries": "queries: security-extended",
        "Java manual build": "build-mode: manual",
        "zero-alert enforcement": "python3 .github/scripts/validate_codeql_sarif.py",
        "SARIF retention": "Upload CodeQL SARIF evidence",
        "SARIF self-check": "python3 .github/scripts/validate_codeql_sarif_selfcheck.py",
        "stack inventory self-check": "python3 .github/scripts/validate_security_stack.py",
        "Maven wrapper verification": "Verify checksum-pinned Maven wrapper",
        "Maven SBOM vulnerability gate": "Maven dependency vulnerabilities",
        "PostgreSQL image gate": "PostgreSQL Testcontainers image",
        "repository Trivy gate": "Trivy repository policy",
    }
    for name, needle in required_contracts.items():
        if needle not in workflow_text:
            errors.append(f"security workflow is missing {name}")

    if workflow_text.count("python3 .github/scripts/validate_codeql_sarif.py") < 2:
        errors.append("both Java and automation CodeQL analyses must enforce zero SARIF alerts")
    if workflow_text.count("Upload CodeQL SARIF evidence") < 2:
        errors.append("both CodeQL analyses must retain SARIF evidence")

    sarif_gate = (ROOT / ".github" / "scripts" / "validate_codeql_sarif.py").read_text(
        encoding="utf-8"
    )
    if "CodeQL zero-alert gate rejected" not in sarif_gate:
        errors.append("CodeQL SARIF gate must reject every code-scanning result")

    if errors:
        print("Security stack coverage contract failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(
        "Security stack coverage contract: Java, Python, GitHub Actions, Maven dependencies, "
        "PostgreSQL image, repository policy, and checksum-pinned Maven wrapper are governed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
