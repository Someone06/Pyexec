import csv
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from pyexec.mining.packageInfo import PackageInfo
from pyexec.util.logging import get_logger


@dataclass
class PyexecStats:
    name: str
    project_on_pypi: bool
    github_link_found: bool
    github_repo_exists: bool
    github_repo_created_at: Optional[datetime]
    github_repo_last_updated: Optional[datetime]
    has_requirementstxt: bool
    has_makefile: bool
    has_pipfile: bool
    loc: Optional[int]
    average_complexity: Optional[float]
    min_python_version: Optional[int]
    dockerfile_found: bool
    dockerfile_source_is_v2: bool
    dockerimage_build_success: bool
    testcase_count: Optional[int]
    failed: Optional[int]
    passed: Optional[int]
    skipped: Optional[int]
    xfailed: Optional[int]
    xpassed: Optional[int]
    warnings: Optional[int]
    errors: Optional[int]
    time: Optional[float]
    covered_lines: Optional[int]
    num_statements: Optional[int]
    percentage_covered: Optional[float]
    missing_lines: Optional[int]
    excluded_lines: Optional[int]


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
                None if info.github_info is None else info.github_info.created_at
            )
            github_repo_last_updated = (
                None if info.github_info is None else info.github_info.last_updated
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
            loc = None if info.repo_info is None else info.repo_info.loc
            average_complexity = (
                None if info.repo_info is None else info.repo_info.average_complexity
            )
            min_python_version = (
                None if info.repo_info is None else info.repo_info.min_python_version
            )
            dockerfile_found = info.dockerfile is not None
            dockerfile_source_is_v2 = info.dockerfile_source == "V2"
            dockerimage_build_success = info.dockerimage_build
            testcase_count = info.testcase_count
            failed = None if info.test_result is None else info.test_result[0].failed
            passed = None if info.test_result is None else info.test_result[0].passed
            skipped = None if info.test_result is None else info.test_result[0].skipped
            xfailed = None if info.test_result is None else info.test_result[0].xfailed
            xpassed = None if info.test_result is None else info.test_result[0].xpassed
            warnings = (
                None if info.test_result is None else info.test_result[0].warnings
            )
            errors = None if info.test_result is None else info.test_result[0].error
            time = None if info.test_result is None else info.test_result[0].time
            covered_lines = (
                None if info.test_result is None else info.test_result[1].covered_lines
            )
            num_statements = (
                None if info.test_result is None else info.test_result[1].num_statements
            )
            percentage_covered = (
                None
                if info.test_result is None
                else info.test_result[1].percentage_covered
            )
            missing_lines = (
                None if info.test_result is None else info.test_result[1].missing_lines
            )
            excluded_lines = (
                None if info.test_result is None else info.test_result[1].excluded_lines
            )
            stat = PyexecStats(
                name,
                project_on_pypi,
                github_link_found,
                github_repo_exists,
                github_repo_created_at,
                github_repo_last_updated,
                has_requirementstxt,
                has_makefile,
                has_pipfile,
                loc,
                average_complexity,
                min_python_version,
                dockerfile_found,
                dockerfile_source_is_v2,
                dockerimage_build_success,
                testcase_count,
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
        keys = toCSV[0].keys()
        with open(csv_file, "w", newline="") as output_file:
            dict_writer = csv.DictWriter(output_file, keys)
            dict_writer.writeheader()
            dict_writer.writerows(toCSV)

    def read(self, csv_file: Path) -> List[PyexecStats]:
        if not csv_file.exists() or not csv_file.is_file():
            raise ValueError("Passed CSV file does not exist")
        with open(csv_file, "r") as data:
            dicts = list(csv.DictReader(data))
        return [PyexecStats(**s) for s in dicts]  # type: ignore
