from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import pandas as pd

from pyexec.mining.packageInfo import PackageInfo
from pyexec.util.logging import get_logger


@dataclass
class PyexecStats:
    name: str
    project_on_pypi: bool
    github_link_found: bool
    github_repo_exists: bool
    github_repo_created_at: datetime
    github_repo_last_updated: datetime
    github_repo_active_days: int
    github_repo_age: int
    has_requirementstxt: bool
    has_makefile: bool
    has_pipfile: bool
    loc: int
    num_files: int
    average_complexity: float
    min_python_version: int
    dockerfile_found: bool
    dockerfile_source: str
    pip_dependency_count: int
    apt_dependency_count: int
    dockerimage_build_success: bool
    testcase_count: int
    testsuit_executed: bool
    testsuit_result_parsed: bool
    failed: int
    passed: int
    skipped: int
    xfailed: int
    xpassed: int
    warnings: int
    errors: int
    time: float
    covered_lines: int
    num_statements: int
    percentage_covered: float
    missing_lines: int
    excluded_lines: int


class CSV:
    def __init__(self, logfile: Optional[Path] = None) -> None:
        self.__logger = get_logger("Pyexec::CSV", logfile)

    def to_stats(self, infos: List[PackageInfo]) -> List[PyexecStats]:
        result: List[PyexecStats] = list()
        for info in infos:
            name = info.name
            project_on_pypi = info.project_on_pypi
            github_link_found = info.github_repo is not None
            github_repo_exists = info.github_repo_exists
            github_repo_created_at = (
                datetime.min
                if info.github_info is None
                else info.github_info.created_at
            )
            github_repo_last_updated = (
                datetime.min
                if info.github_info is None
                else info.github_info.last_updated
            )
            github_repo_active_days = (
                -1
                if info.github_info is None
                else (github_repo_last_updated - github_repo_created_at).days
            )
            github_repo_age = (
                -1
                if info.github_info is None
                else (datetime.today() - github_repo_created_at).days
            )
            has_requirementstxt = (
                False if info.repo_info is None else info.repo_info.has_requirementstxt
            )
            has_makefile = (
                False if info.repo_info is None else info.repo_info.has_makefile
            )
            has_pipfile = (
                False if info.repo_info is None else info.repo_info.has_pipfile
            )
            loc = (
                -1
                if info.repo_info is None or info.repo_info.loc is None
                else info.repo_info.loc
            )
            num_files = (
                -1
                if info.repo_info is None or info.repo_info.num_files is None
                else info.repo_info.num_files
            )
            average_complexity = (
                -1
                if info.repo_info is None or info.repo_info.average_complexity is None
                else info.repo_info.average_complexity
            )
            min_python_version = (
                -1
                if info.repo_info is None or info.repo_info.min_python_version is None
                else info.repo_info.min_python_version
            )
            dockerfile_found = info.dockerfile is not None
            dockerfile_source = (
                "None" if info.dockerfile_source is None else info.dockerfile_source
            )
            pip_dependency_count = (
                -1
                if info.dockerfile is None
                else info.dockerfile.pip_dependency_count()
            )
            apt_dependency_count = (
                -1
                if info.dockerfile is None
                else info.dockerfile.apt_dependency_count()
            )
            dockerimage_build_success = info.dockerimage_build
            testcase_count = -1 if info.testcase_count is None else info.testcase_count
            testsuit_executed = info.testsuit_executed
            testsuit_result_parsed = info.testsuit_result_parsed
            failed = -1 if info.test_result is None else info.test_result[0].failed
            passed = -1 if info.test_result is None else info.test_result[0].passed
            skipped = -1 if info.test_result is None else info.test_result[0].skipped
            xfailed = -1 if info.test_result is None else info.test_result[0].xfailed
            xpassed = -1 if info.test_result is None else info.test_result[0].xpassed
            warnings = -1 if info.test_result is None else info.test_result[0].warnings
            errors = -1 if info.test_result is None else info.test_result[0].error
            time = -1 if info.test_result is None else info.test_result[0].time
            covered_lines = (
                -1 if info.test_result is None else info.test_result[1].covered_lines
            )
            num_statements = (
                -1 if info.test_result is None else info.test_result[1].num_statements
            )
            percentage_covered = (
                -1
                if info.test_result is None
                else info.test_result[1].percentage_covered
            )
            missing_lines = (
                -1 if info.test_result is None else info.test_result[1].missing_lines
            )
            excluded_lines = (
                -1 if info.test_result is None else info.test_result[1].excluded_lines
            )
            stat = PyexecStats(
                name,
                project_on_pypi,
                github_link_found,
                github_repo_exists,
                github_repo_created_at,
                github_repo_last_updated,
                github_repo_active_days,
                github_repo_age,
                has_requirementstxt,
                has_makefile,
                has_pipfile,
                loc,
                num_files,
                average_complexity,
                min_python_version,
                dockerfile_found,
                dockerfile_source,
                pip_dependency_count,
                apt_dependency_count,
                dockerimage_build_success,
                testcase_count,
                testsuit_executed,
                testsuit_result_parsed,
                failed,
                passed,
                skipped,
                xfailed,
                xpassed,
                warnings,
                errors,
                time,
                covered_lines,
                num_statements,
                percentage_covered,
                missing_lines,
                excluded_lines,
            )
            result.append(stat)
        return result

    def write(self, stats: List[PyexecStats], csv_file: Path) -> None:
        toCSV = [asdict(s) for s in stats]
        frame = pd.DataFrame(toCSV)
        frame.to_csv(csv_file)
