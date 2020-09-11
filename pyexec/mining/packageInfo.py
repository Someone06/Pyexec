from dataclasses import dataclass
from typing import Optional, Tuple

from pyexec.mining.githubrequest import GitHubInfo
from pyexec.mining.gitrequest import RepoInfo
from pyexec.testrunner.runresult import CoverageResult, TestResult
from pyexec.util.dependencies import Dependencies


@dataclass
class PackageInfo:
    name: str
    project_on_pypi: bool = False
    github_repo: Optional[Tuple[str, str]] = None
    github_repo_exists: bool = False
    dockerfile: Optional[Dependencies] = None
    dockerfile_source: Optional[str] = None
    dockerimage_build: bool = False
    testcase_count: Optional[int] = None
    test_result: Optional[Tuple[TestResult, CoverageResult]] = None
    github_info: Optional[GitHubInfo] = None
    repo_info: Optional[RepoInfo] = None

    @property
    def has_testsuit(self) -> bool:
        return self.testcase_count is not None

    @property
    def testsuit_executed(self) -> bool:
        return self.has_testsuit and self.dockerimage_build

    @property
    def testsuit_result_parsed(self) -> bool:
        return self.test_result is not None

    @property
    def github_link_found(self) -> bool:
        return self.github_repo is not None
