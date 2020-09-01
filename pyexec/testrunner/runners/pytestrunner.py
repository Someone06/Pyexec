import re
from pathlib import Path
from typing import Optional, Tuple

from plumbum.cmd import grep, sh
from setuptools import find_packages

from pyexec.testrunner.runner import AbstractRunner, RunnerNotUsedException
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

    def run(self, timeout: Optional[int] = None) -> Tuple[TestResult, CoverageResult]:
        if not self.is_used_in_project():
            raise RunnerNotUsedException(
                "Pytest is not used in project {}".format(self._project_path.name)
            )
        self._add_dependencies()
        out, err = self._run(timeout)
        return self._extract_run_results(out)

    def _add_dependencies(self) -> None:
        self._logger.debug("Adding dependencies")
        self._dependencies.add_run_command(r'RUN ["pip", "install", "pytest"]')
        self._dependencies.add_run_command(r'RUN ["pip", "install", "coverage"]')
        self._dependencies.set_cmd_command(
            r"""CMD ["sh", "-c", "coverage run --source={} -m pytest -rA --tb=no -report=term-missing ; coverage json --pretty-print -o- | sed '/totals/,$!d' | head -n -1"]""".format(
                ",".join(find_packages(where=self._project_path))
            )
        )

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

    def get_test_count(self) -> int:
        if self.is_used_in_project():
            cmd = sh[
                "-c",
                r"""find """
                + str(self._project_path)
                + r""" -type f -name 'test*.py' -exec grep -e 'def test_' '{}' \; | wc -l""",
            ]
            _, count, _ = cmd.run(retcode=None)
            try:
                return int(count)
            except ValueError:
                self._logger.warning("Unbale to parse pytest test count")
                return -1
        else:
            return -1

    def _extract_run_results(self, log: str) -> Tuple[TestResult, CoverageResult]:
        self._logger.debug("Parsing run results")
        test_result = None
        coverage_result = None

        #  Example:
        #  === 6 failed, 5 passed, 2 skipped, 1 xfailed, 1 xpassed, 2 warnings in 2.49s ===
        matches = re.search(
            r"=+ ((\d+) failed, )?"
            r"(\d+) passed"
            r"(, (\d+) skipped)?"
            r"(, (\d+) xfailed)?"
            r"(, (\d+) xpassed)?"
            r"(, (\d+) warnings?)?"
            r"(, (\d+) errors?)?"
            r" in ([\d.]+)s =+\s*",
            log,
        )
        if matches:
            self._logger.debug("Matched test results")
            failed = int(matches.group(2)) if matches.group(2) else 0
            passed = int(matches.group(3)) if matches.group(3) else 0
            skipped = int(matches.group(5)) if matches.group(5) else 0
            xfailed = int(matches.group(7)) if matches.group(7) else 0
            xpassed = int(matches.group(9)) if matches.group(9) else 0
            warnings = int(matches.group(11)) if matches.group(11) else 0
            error = int(matches.group(13)) if matches.group(13) else 0
            time = float(matches.group(14)) if matches.group(14) else 0.0

            test_result = TestResult(
                failed=failed,
                passed=passed,
                skipped=skipped,
                xfailed=xfailed,
                xpassed=xpassed,
                warnings=warnings,
                error=error,
                time=time,
            )

        # Example (without the #'s):
        #    "totals": {
        #        "covered_lines": 0,
        #        "num_statements": 234,
        #        "percent_covered": 0.0,
        #        "missing_lines": 234,
        #        "excluded_lines": 0
        #    }
        matches = re.search(
            r'\s*"totals": \{\s*'
            r'\s*"covered_lines": (\d+),\s*'
            r'\s*"num_statements": (\d+),\s*'
            r'\s*"percent_covered": (\d+)\.(\d+),\s*'
            r'\s*"missing_lines": (\d+),\s*'
            r'\s*"excluded_lines": (\d+)\s*',
            log,
        )
        if matches:
            self._logger.debug("Matched coverage")
            covered_lines = int(matches.group(1))
            num_statements = int(matches.group(2))
            percent_covered = float(matches.group(3) + "." + matches.group(4))
            missing_lines = int(matches.group(5))
            excluded_lines = int(matches.group(6))

            coverage_result = CoverageResult(
                covered_lines,
                num_statements,
                percent_covered,
                missing_lines,
                excluded_lines,
            )

        if test_result is None or coverage_result is None:
            self._logger.debug("Unexpected output format of pytest and pytest-cov")
            raise ValueError("Unexpected output format of pytest and pytest-cov")
        else:
            return test_result, coverage_result
