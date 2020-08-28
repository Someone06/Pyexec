from dataclasses import dataclass


@dataclass
class CoverageResult:
    covered_lines: int
    num_statements: int
    percentage_covered: float
    missing_lines: int
    excluded_lines: int


@dataclass
class TestResult:
    failed: int
    passed: int
    skipped: int
    xfailed: int
    xpassed: int
    warnings: int
    error: int
    time: float
