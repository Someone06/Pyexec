import re
from pathlib import Path
from typing import Optional, Tuple

from plumbum.cmd import grep

from pyexec.testrunner.runner import AbstractRunner
from pyexec.testrunner.runresult import CoverageResult, TestResult
from pyexec.util.dependencies import Dependencies


class PytestRunner(AbstractRunner):
    def __init__(
        self,
        tmp_path: Path,
        project_name: str,
        dependencies: Dependencies,
        logfile: Optional[Path] = None,
    ) -> None:
        super().__init__(tmp_path, project_name, dependencies, logfile)

    def run(
        self, timeout: Optional[int] = None
    ) -> Tuple[Optional[TestResult], Optional[CoverageResult]]:
        if not self.is_used_in_project():
            return None, None

        self._logger.debug("Setting up Dockerfile")
        self._dependencies.add_run_command(r'RUN ["pip", "install", "pytest"]')
        self._dependencies.add_run_command(r'RUN ["pip", "install", "pytest-cov"]')
        self._dependencies.set_cmd_command(
            r'CMD ["python", "-m", "pytest", "--cov={}", "-report=term-missing"]'.format(
                self._project_path.name
            )
        )
        result = self._run_container(timeout)
        if result is None:
            return None, None
        else:
            out, _ = result
            self._logger.debug("Extracting run results")
            return PytestRunner.__extract_run_results(out)

    def is_used_in_project(self) -> bool:
        setup_path = self._project_path.joinpath("setup.py")
        if setup_path.exists() and setup_path.is_file():
            for file in ["pytest", "py.test"]:
                _, r, _ = grep["test_suite={}".format(file), setup_path].run(
                    retcode=None
                )
                if len(r) > 0:
                    return True

        pyini_path = self._project_path.joinpath("pytest.ini")
        if pyini_path.exists() and pyini_path.is_file():
            return True

        for stmt in ["import pytest", "from pytest import"]:
            _, r, _ = grep["-R", stmt, self._project_path].run(retcode=None)
            if len(r) > 0:
                return True
        return False

    @staticmethod
    def __extract_run_results(
        log: str,
    ) -> Tuple[Optional[TestResult], Optional[CoverageResult]]:
        test_result = None
        coverage_result = None

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
            test_result = TestResult(
                failed=failed,
                passed=passed,
                skipped=skipped,
                warnings=warnings,
                error=error,
                time=time,
            )

        matches = re.search(
            r"TOTAL\s+"
            r"([0-9]+)\s+"
            r"([0-9]+)\s+"
            r"(([0-9]+)\s(+([0-9]+)\s+)?"
            r"([0-9]+%)",
            log,
        )
        if matches:
            statements = int(matches.group(1)) if matches.group(1) else 0
            missing = int(matches.group(2)) if matches.group(2) else 0
            coverage = float(matches.group(6)[:-1]) if matches.group(6) else 0.0
            coverage_result = CoverageResult(
                statements=statements, missing=missing, coverage=coverage
            )

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
                coverage_result = CoverageResult(
                    statements=statements, missing=missing, coverage=coverage
                )

        return test_result, coverage_result
