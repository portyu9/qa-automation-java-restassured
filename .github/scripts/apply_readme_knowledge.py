from pathlib import Path
import re

path = Path('README.md')
text = path.read_text(encoding='utf-8')
marker = '## Dependency maintenance\n'
section = '''## Confidence boundaries

The framework combines real HTTP and real relational-database execution with deterministic local control, but each signal is still scoped to the boundary actually exercised.

| Signal | Confidence gained | Deliberate limit |
| --- | --- | --- |
| REST Assured API contracts | HTTP status, headers, payload semantics, schema checks, and client-facing error behavior execute through the governed API boundary | Passing API contracts do not prove browser behavior, upstream integrations, or production ingress/network policy |
| JSON Schema validation | Provider responses retain the committed structural contract | Structural validity does not prove business correctness, authorization correctness, or semantic compatibility outside the asserted fields |
| WireMock-controlled dependencies | Timeout, error, and dependency-response conditions are reproducible and attributable | A controlled stub proves the owned condition, not the current behavior of a live third-party service |
| Testcontainers PostgreSQL integration | Repository/transaction behavior executes against a real PostgreSQL engine with isolated lifecycle ownership | It does not prove managed-service topology, replication, failover, production sizing, network policy, or migration safety in a deployed estate |
| Unit/integration lifecycle separation | Fast contracts and infrastructure-bearing tests retain distinct Maven lifecycle ownership and failure attribution | A green unit phase is not evidence that container/integration prerequisites are healthy, and the reverse is also true |
| Dependency lock / resolved graph / SBOM evidence | The build records the dependency graph actually selected for the governed execution | A generated SBOM is inventory evidence, not a vulnerability verdict or proof that every runtime path loads every component |
| Runtime compatibility lanes | The same governed suite executes across explicitly supported Java runtimes | Compatibility is scoped to exercised code paths; it does not guarantee behavior under unqualified future runtimes or JVM/environment tuning |
| CodeQL / dependency vulnerability analysis / Trivy / dependency review | Independent controls inspect source, dependency, repository/configuration, secret, and change-diff risk planes | Scanner success remains bounded by rule coverage, advisory data, repository visibility, and the evidence retained |

Use **real infrastructure when infrastructure semantics are the requirement**, not merely to make a test appear more integrated. Deterministic doubles remain appropriate for owned dependency conditions; real PostgreSQL is appropriate where SQL/transaction/driver behavior itself must be proven.

'''
if '## Confidence boundaries\n' not in text:
    if marker not in text:
        raise SystemExit('Dependency maintenance marker missing')
    text = text.replace(marker, section + marker)
path.write_text(text, encoding='utf-8')

patterns = [
    re.compile(r'\bJava\s+\d', re.I),
    re.compile(r'\bMaven\s+\d', re.I),
    re.compile(r'\bJUnit\s+v?\d', re.I),
    re.compile(r'\bREST\s+Assured\s+v?\d', re.I),
    re.compile(r'\bJackson(?:\s+BOM)?\s+v?\d', re.I),
    re.compile(r'\bTestcontainers\s+v?\d', re.I),
    re.compile(r'\bPostgreSQL\s+v?\d', re.I),
    re.compile(r'\bWireMock\s+v?\d', re.I),
    re.compile(r'\bHamcrest\s+v?\d', re.I),
    re.compile(r'\bsource\s*=?\s*\d{2}\b', re.I),
    re.compile(r'\btarget\s*=?\s*\d{2}\b', re.I),
]
candidates = []
for md in [Path('README.md'), *Path('docs').rglob('*.md')]:
    for number, line in enumerate(md.read_text(encoding='utf-8').splitlines(), 1):
        if any(pattern.search(line) for pattern in patterns):
            candidates.append(f'{md}:{number}: {line}')
if candidates:
    raise SystemExit('Residual Java/tool version candidates:\n' + '\n'.join(candidates))
