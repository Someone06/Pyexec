import os
import re
from logging import Logger
from pathlib import Path, PurePath
from typing import Optional

from plumbum import grep

from pyexec.testrunner.runner import AbstractRunner
from pyexec.testrunner.runresult import RunResult
from pyexec.util.dependencys import Dependencies


class PyTestRunner(AbstractRunner):
    def __init__(
        self, project_path: Path, dependencies: Dependencies, logger: Optional[Logger]
    ) -> None:
        super().__init__(project_path, dependencies, logger)

    def run(self) -> Optional[RunResult]:
        return None

    def used_in_project(self) -> bool:
        setup_path = PurePath.joinpath(self.project_path, "setup.py")
        if Path.exists(setup_path) and Path.is_file(setup_path):
            for file in ["pytest", "py.test"]:
                _, r, _ = grep["test_suite={}".format(file), setup_path].run(
                    retcode=None
                )
                if len(r) > 0:
                    return True

        pyini_path = PurePath.joinpath(self.project_path, "pytest.ini")
        if os.path.exists(pyini_path) and os.path.isfile(pyini_path):
            return True

        for stmt in ["import pytest", "from pytest import", "pytest"]:
            _, r, _ = grep["-R", stmt, self.project_path].run(retcode=None)
            if len(r) > 0:
                return True
        return False

    def __extract_run_result(self, log: str) -> RunResult:
        statements = -1
        missing = -1
        coverage = -1.0
        failed = -1
        passed = -1
        skipped = -1
        warnings = -1
        error = -1
        time = -1.0

        matches = re.search(
            r"[=]+ (([0-9]+) failed, )?"
            r"([0-9]+) passed"
            r"(, ([0-9]+) skipped)?"
            r"(, ([0-9]+) warnings)?"
            r"(, ([0-9]+) error)?"
            r" in ([0-9.]+) seconds",
            log,
        )
        if matches:
            failed = int(matches.group(2)) if matches.group(2) else 0
            passed = int(matches.group(3)) if matches.group(3) else 0
            skipped = int(matches.group(5)) if matches.group(5) else 0
            warnings = int(matches.group(7)) if matches.group(7) else 0
            error = int(matches.group(9)) if matches.group(9) else 0
            time = float(matches.group(10)) if matches.group(10) else 0.0

        matches = re.search(
            r"TOTAL\s+"
            r"([0-9]+)\s+"
            r"([0-9]+)\s+"
            r"(([0-9]+)\s+([0-9]+)\s+)?"
            r"([0-9]+%)",
            log,
        )
        if matches:
            statements = int(matches.group(1)) if matches.group(1) else 0
            missing = int(matches.group(2)) if matches.group(2) else 0
            coverage = float(matches.group(6)[:-1]) if matches.group(6) else 0.0
        else:
            matches = re.search(
                r".py\s+"
                r"([0-9]+)\s+"
                r"([0-9]+)\s+"
                r"(([0-9]+)\s+([0-9]+)\s+)?"
                r"([0-9]+%)",
                log,
            )
            if matches:
                statements = int(matches.group(1)) if matches.group(1) else 0
                missing = int(matches.group(2)) if matches.group(2) else 0
                coverage = float(matches.group(6)[:-1]) if matches.group(6) else 0.0

        result = RunResult(
            statements=statements,
            missing=missing,
            coverage=coverage,
            failed=failed,
            passed=passed,
            skipped=skipped,
            warnings=warnings,
            error=error,
            time=time,
        )
        return result
