"""Require every external GitHub Action to use a full immutable commit SHA."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"
USES_RE = re.compile(r"^\s*-?\s*uses:\s*([^\s#]+)")
IMMUTABLE_RE = re.compile(r"^[^@\s]+@[0-9a-fA-F]{40}$")

failures: list[str] = []
for workflow in sorted((*WORKFLOWS.glob("*.yml"), *WORKFLOWS.glob("*.yaml"))):
    for line_number, line in enumerate(workflow.read_text(encoding="utf-8").splitlines(), 1):
        match = USES_RE.match(line)
        if not match:
            continue
        reference = match.group(1)
        if reference.startswith("./"):
            continue
        if not IMMUTABLE_RE.fullmatch(reference):
            failures.append(f"{workflow.name}:{line_number}: mutable action reference {reference}")

if failures:
    print("Workflow action pin contract failed:")
    for failure in failures:
        print(f"- {failure}")
    raise SystemExit(1)

print("Workflow action pin contract: ok")
