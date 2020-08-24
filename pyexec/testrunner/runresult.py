from dataclasses import dataclass


@dataclass
class CoverageResult:
    statements: int
    missing: int
    coverage: float


@dataclass
class TestResult:
    failed: int
    passed: int
    skipped: int
    warnings: int
    error: int
    time: float
