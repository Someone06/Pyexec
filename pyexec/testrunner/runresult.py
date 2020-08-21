from dataclasses import dataclass
from typing import Optional


@dataclass
class RunResult:
    statements: Optional[int] = None
    missing: Optional[int] = None
    coverage: Optional[float] = None
    failed: Optional[int] = None
    passed: Optional[int] = None
    skipped: Optional[int] = None
    warnings: Optional[int] = None
    error: Optional[int] = None
    time: Optional[float] = None
