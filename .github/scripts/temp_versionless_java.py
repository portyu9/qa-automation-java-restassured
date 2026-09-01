from pathlib import Path
import re

ROOT = Path('.')
FILES = [Path('README.md'), *sorted(Path('docs').rglob('*.md'))]

REPLACEMENTS = {
    # Combined capability/toolchain claims.
    'Testcontainers 1.21.4 + PostgreSQL 16.15': 'Testcontainers + PostgreSQL',
    'Java 17, 21, 25 + Maven 3.9.16 Wrapper': 'supported Java runtimes + Maven Wrapper',
    # Runtime-role wording.
    '**Java 25 current LTS**': '**the current qualified Java runtime**',
    '**Java 17 minimum runtime**': '**the minimum supported Java runtime**',
    '**Java 21 compatibility runtime**': '**an additional qualified Java runtime**',
    '**Java 17** also runs a full extended lifecycle': '**The minimum supported Java runtime** also runs a full extended lifecycle',
    '**Java 17, 21, or 25**': '**a supported Java runtime**',
    '**17, 21, or 25**': '**a supported Java runtime**',
    'Java 25 current-LTS full verify': 'current qualified Java full verify',
    'Java 17 minimum-runtime full verify': 'minimum supported Java full verify',
    'Java 21 fast compatibility': 'additional Java compatibility',
    'Java 17/21 fast compatibility and Java 25 current-LTS full verification': 'minimum/additional Java compatibility and current-runtime full verification',
    'Java 17/21 fast-only failure': 'minimum/additional-runtime fast-only failure',
    'Java 25 full-only failure': 'current-runtime full-only failure',
    'Java 17 extended full-only failure': 'minimum-runtime extended full-only failure',
    'Java 17 extended-full-only failure': 'minimum-runtime extended-full-only failure',
    'Java 25 full': 'current-runtime full',
    'Java 17 extended full': 'minimum-runtime extended full',
    'Java 17 and Java 21 compatibility pass': 'minimum and additional Java compatibility pass',
    'Java 25 full lifecycle passes': 'current qualified Java full lifecycle passes',
    'Java 17 extended full lifecycle passes when applicable': 'minimum supported Java extended full lifecycle passes when applicable',
    'Java 17 and Java 21 run fast compatibility in primary CI, and Java 17 also runs full `verify` in extended CI.': 'The minimum and additional qualified runtimes run fast compatibility in primary CI, and the minimum runtime also runs full `verify` in extended CI.',
    'Java 25 runs full `verify` in primary CI.': 'The current qualified runtime runs full `verify` in primary CI.',
    '- **Java 21** — intermediate/previous LTS compatibility;': '- **Additional qualified Java runtime** — compatibility signal;',
    '- **Java 25** — current-LTS primary runtime.': '- **Current qualified Java runtime** — primary runtime.',
    '- Java 25 current LTS: complete primary `verify` lifecycle;': '- current qualified Java runtime: complete primary `verify` lifecycle;',
    '- Java 21: fast compatibility;': '- additional qualified Java runtime: fast compatibility;',
    '- Java 17 minimum runtime: fast compatibility in primary CI and full `verify` in extended CI.': '- minimum supported Java runtime: fast compatibility in primary CI and full `verify` in extended CI.',
    'Java 17 minimum, Java 21 compatibility, Java 25 current LTS; Enforcer rejects Java 26+ until explicitly qualified.': 'The minimum supported runtime, an additional compatibility runtime, and the current qualified Java runtime are exercised; future unqualified Java releases are rejected until deliberately supported.',
    'Java 26+': 'future unqualified Java releases',
    'Java 26': 'a future unqualified Java release',
    'Java 17 bytecode/API compatibility': 'minimum-Java bytecode/API compatibility',
    'Java 17 and Java 25 persistence execution': 'minimum/current Java persistence execution',
    'Java 17 and Java 25': 'the minimum and current qualified Java runtimes',
    'Java 17 and additional Java compatibility pass': 'minimum and additional Java compatibility pass',
    # Maven provenance/support wording.
    '**Maven 3.9.16**': '**the repository-pinned Maven distribution**',
    'Maven 3.9.16': 'the repository-pinned Maven distribution',
    'Wrapper 3.3.4 downloads Maven 3.9.16 only after validating the pinned distribution SHA-256.': 'The checked-in Maven Wrapper downloads the repository-pinned Maven distribution only after validating its SHA-256.',
    'Wrapper 3.3.4 points to Maven 3.9.16 and a pinned distribution SHA-256.': 'The checked-in Maven Wrapper points to a repository-pinned Maven distribution and validates its SHA-256.',
    'Wrapper 3.3.4, Maven 3.9.16, and the checked distribution checksum': 'the checked-in Maven Wrapper, repository-pinned Maven distribution, and distribution checksum',
    'Wrapper 3.3.4;': 'the checked-in Maven Wrapper;',
    '- Maven 3.9.16;': '- repository-pinned Maven distribution;',
    'Maven 3.9.x only; Enforcer rejects Maven 4 until deliberately qualified.': 'The repository-pinned Maven line is enforced; future unqualified Maven majors are rejected until deliberately supported.',
    'Maven 4': 'a future Maven major',
    'Maven Enforcer accepts `[3.9,4)`.': 'Maven Enforcer accepts only the repository-qualified Maven line.',
    'Maven Enforcer accepts Java `[17,26)` only.': 'Maven Enforcer accepts only repository-qualified Java runtimes.',
    'Maven Enforcer bounds Java to `[17,26)` and Maven to `[3.9,4)`.': 'Maven Enforcer bounds Java and Maven to repository-qualified runtime lines.',
    'The project compiles with `maven.compiler.release=17`, so the test framework preserves Java bytecode/API compatibility while qualifying newer LTS runtimes independently.': 'The project compiles against its configured minimum Java release, so bytecode/API compatibility is preserved while newer qualified runtimes are exercised independently.',
    '`maven.compiler.release=17`': '`maven.compiler.release` minimum-runtime policy',
    # Framework/dependency versions.
    'REST Assured 6.0.1': 'REST Assured',
    'JUnit 6.1.3': 'JUnit',
    'WireMock 3.13.2': 'WireMock',
    'Testcontainers 1.21.4': 'Testcontainers',
    'PostgreSQL 16.15': 'PostgreSQL',
    'PostgreSQL 16': 'PostgreSQL',
    'PostgreSQL driver 42.7.13': 'PostgreSQL driver',
    'Jackson BOM 2.18.8': 'Jackson BOM',
    'Jackson BOM 2.22.2': 'Jackson BOM',
    'Jackson 2.11.0': 'an older transitive Jackson release',
    'Jackson 2.18.8': 'the governed Jackson family',
    'Jackson 2.22.2': 'the governed Jackson family',
    'CycloneDX 2.9.3': 'CycloneDX',
    'postgres:16.15-alpine': 'postgres:<pinned-tag>',
    'Testcontainers 2.0.5 migration': 'prior Testcontainers major-version migration',
    '2.0.5 migration': 'prior major-version migration',
    'Testcontainers 2.x': 'a future Testcontainers major',
    'Testcontainers 2': 'a future Testcontainers major',
    'The repository deliberately remains on Testcontainers until a future Testcontainers major migration proves the runtime, not just compilation.': 'The repository deliberately remains on its currently qualified Testcontainers major line until a future major migration proves runtime behavior, not just compilation.',
    'Testcontainers remains on until a future Testcontainers major migration proves the runtime, not just compilation.': 'Testcontainers remains on the repository-qualified major line until a future major migration proves runtime behavior, not just compilation.',
    # Specific diagnostic/evidence sentences.
    'PostgreSQL lifecycle and JDBC contracts pass on Java 17 and Java 25;': 'PostgreSQL lifecycle and JDBC contracts pass on both the minimum and current qualified Java runtimes;',
    '`ci / ci-gate` aggregates Java 17 / 21 fast compatibility and Java 25 current-LTS full verification;': '`ci / ci-gate` aggregates minimum/additional Java compatibility and current-runtime full verification;',
    '`extended / extended-gate` aggregates the Java 17 minimum-runtime full lifecycle;': '`extended / extended-gate` aggregates the minimum-supported-runtime full lifecycle;',
    '| Java 25 full-only failure | Current-LTS/runtime or persistence interaction |': '| Current-runtime full-only failure | Current-runtime or persistence interaction |',
    '| Java 17 extended full-only failure | Minimum-runtime persistence integration |': '| Minimum-runtime extended full-only failure | Minimum-runtime persistence integration |',
    '| Current-LTS lifecycle | Java 25 | Full Maven `verify` | Surefire + Failsafe |': '| Current-runtime lifecycle | Current qualified Java runtime | Full Maven `verify` | Surefire + Failsafe |',
    '| Minimum-runtime lifecycle | Java 17 | Full Maven `verify` in extended CI | Surefire + Failsafe |': '| Minimum-runtime lifecycle | Minimum supported Java runtime | Full Maven `verify` in extended CI | Surefire + Failsafe |',
    '| Intermediate compatibility | Java 21 | Fast deterministic tests | Surefire |': '| Additional compatibility | Additional qualified Java runtime | Fast deterministic tests | Surefire |',
    '| Java 17/21 fast | Runtime compatibility / API assumption |': '| Minimum/additional-runtime fast | Runtime compatibility / API assumption |',
}

BADGE_RULES = [
    (r'/badge/Java-[^)]*?-ED8B00', '/badge/Java-runtime-ED8B00'),
    (r'/badge/Maven-[^)]*?-C71A36', '/badge/Maven-build-C71A36'),
    (r'/badge/REST%20Assured-[^)]*?-6E7781', '/badge/REST%20Assured-API%20testing-6E7781'),
    (r'/badge/JUnit-[^)]*?-25A162', '/badge/JUnit-testing-25A162'),
    (r'/badge/Testcontainers-[^)]*?-00B8A9', '/badge/Testcontainers-integration-00B8A9'),
    (r'/badge/PostgreSQL-[^)]*?-4169E1', '/badge/PostgreSQL-persistence-4169E1'),
]

for path in FILES:
    text = path.read_text(encoding='utf-8')
    for old, new in REPLACEMENTS.items():
        text = text.replace(old, new)
    for pattern, replacement in BADGE_RULES:
        text = re.sub(pattern, replacement, text)
    path.write_text(text, encoding='utf-8')

validator = Path('.github/scripts/validate_readme.py')
validator_text = validator.read_text(encoding='utf-8')
old = '''    lower = text.lower()\n    for claim in ("java 25", "java 17", "maven 3.9.16"):\n        if claim not in lower:\n            fail(f"README must document qualified toolchain claim: {claim}", errors)\n'''
new = '''    lower = text.lower()\n    for claim in ("minimum supported java", "current qualified java", "maven wrapper"):\n        if claim not in lower:\n            fail(f"README must document versionless toolchain claim: {claim}", errors)\n'''
if old not in validator_text:
    raise SystemExit('expected Java README validator toolchain block not found')
validator.write_text(validator_text.replace(old, new), encoding='utf-8')

# Fail closed on technology/runtime version claims in human-facing documentation.
tech = r'(?:Java|Maven|REST Assured|JUnit|WireMock|Testcontainers|PostgreSQL|Jackson(?: BOM)?|CycloneDX)'
patterns = [
    re.compile(rf'(?i)\\b{tech}\\s+(?:\\*\\*|`)?v?\\d+(?:\\.\\d+)*(?:\\.x)?'),
    re.compile(r'(?i)\\b(?:Java|Maven)\\b[^.\\n|]{0,24}\\[\\d'),
    re.compile(r'(?i)postgres:\\d'),
    re.compile(r'(?i)/badge/(?:Java|Maven|REST%20Assured|JUnit|Testcontainers|PostgreSQL)-v?\\d'),
    re.compile(r'(?i)\\bWrapper\\s+\\d+(?:\\.\\d+)+'),
]
leftovers = []
for path in FILES:
    for line_number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
        if any(pattern.search(line) for pattern in patterns):
            leftovers.append(f'{path}:{line_number}: {line}')
if leftovers:
    print('Remaining versioned technology claims:')
    print('\n'.join(leftovers))
    raise SystemExit(1)
