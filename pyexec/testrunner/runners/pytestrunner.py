import re
from pathlib import Path
from typing import Optional, Pattern, Tuple

from plumbum.cmd import grep, sh
from setuptools import find_packages

from pyexec.testrunner.runner import AbstractRunner, RunnerNotUsedException
from pyexec.testrunner.runresult import CoverageResult, TestResult
from pyexec.util.dependencies import Dependencies


class PytestRunner(AbstractRunner):

    _pytest_regex: Pattern = re.compile(
        r"=+"
        r"(?:"
        r"(?: (?P<failed>\d+) failed)?"
        r"(?:,? (?P<passed>\d+) passed)?"
        r"(?:,? (?P<skipped>\d+) skipped)?"
        r"(?:,? (?P<xfailed>\d+) xfailed)?"
        r"(?:,? (?P<xpassed>\d+) xpassed)?"
        r"(?:,? (?P<warnings>\d+) warnings?)?"
        r"(?:,? (?P<errors>\d+) errors?)?"
        r"|"
        r" no tests? ran"
        r")"
        r" in (?P<time>[\d.]+)s(?:econds?)? =+\s*"
    )
    _coverage_regex: Pattern = re.compile(
        r'\s*"totals": \{\s*'
        r'\s*"covered_lines": (?P<covered>\d+),\s*'
        r'\s*"num_statements": (?P<stmts>\d+),\s*'
        r'\s*"percent_covered": (?P<percent>[\d.]+),\s*'
        r'\s*"missing_lines": (?P<missing>\d+),\s*'
        r'\s*"excluded_lines": (?P<excluded>\d+)\s*'
    )

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
        self._dependencies.add_pip_dependency("pytest")
        self._dependencies.add_pip_dependency("coverage")
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

    def get_test_count(self) -> Optional[int]:
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
                return None
        else:
            return None

    def _extract_run_results(self, log: str) -> Tuple[TestResult, CoverageResult]:
        self._logger.debug("Parsing run results")
        test_result = None
        coverage_result = None

        matches = self._pytest_regex.search(log)
        if matches:
            self._logger.debug("Matched test results")
            failed = int(matches.group("failed")) if matches.group("failed") else 0
            passed = int(matches.group("passed")) if matches.group("passed") else 0
            skipped = int(matches.group("skipped")) if matches.group("skipped") else 0
            xfailed = int(matches.group("xfailed")) if matches.group("xfailed") else 0
            xpassed = int(matches.group("xpassed")) if matches.group("xpassed") else 0
            warnings = (
                int(matches.group("warnings")) if matches.group("warnings") else 0
            )
            error = int(matches.group("errors")) if matches.group("errors") else 0
            time = float(matches.group("time"))

            test_result = TestResult(
                failed, passed, skipped, xfailed, xpassed, warnings, error, time,
            )

        matches = self._coverage_regex.search(log)
        if matches:
            self._logger.debug("Matched coverage")
            covered_lines = int(matches.group("covered"))
            num_statements = int(matches.group("stmts"))
            percent_covered = float(matches.group("percent"))
            missing_lines = int(matches.group("missing"))
            excluded_lines = int(matches.group("excluded"))

            coverage_result = CoverageResult(
                covered_lines,
                num_statements,
                percent_covered,
                missing_lines,
                excluded_lines,
            )

        if test_result is None or coverage_result is None:
            self._logger.debug(
                "Unexpected output format of pytest and pytest-cov:\n{}".format(log)
            )
            raise ValueError("Unexpected output format of pytest and pytest-cov")
        else:
            return test_result, coverage_result
