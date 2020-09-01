import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from glob import glob
from logging import Logger
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import git
from git import Blob, Commit, Repo, TagObject, Tree
from plumbum.cmd import awk, cloc, grep, radon, tail, tr
from pydriller import RepositoryMining
from pydriller.domain.commit import Modification

from pyexec.util.logging import get_logger


@dataclass
class RepoInfo:
    has_requirementstxt: bool
    has_setuppy: bool
    has_makefile: bool
    loc: int
    average_complexity: int


@dataclass
class RepositoryCommit:
    author: str
    author_date: datetime
    committer: str
    committer_date: datetime
    msg: str
    parents: List[str]
    diffs: List[Dict[str, str]]
    issues: List[str] = field(default_factory=list)


class GitRequest:
    class GitRepoNotFoundException(Exception):
        pass

    __close_regex = re.compile(
        r"(close([sd])?|fix(es|ed)?|resolve([sd])?)\s+#(\d+)", re.IGNORECASE
    )
    __bugfix_regex = re.compile(
        r"(error|fix|issue|mistake|incorrect|fault|detect|flaw)", re.IGNORECASE
    )

    def __init__(
        self, repo_user: str, repo_name: str, logfile: Optional[Path] = None
    ) -> None:
        self.__repo_user = repo_user
        self.__repo_name = repo_name
        self.__logger = get_logger("Pyexec::GitRequest", logfile)

        self.__commits: Dict[str, Dict[str, Any]] = dict()
        self.__num_lines = -1
        self.__num_files = -1
        self.__num_commits = -1
        self.__head_commit = None
        self.__test_frameworks: Optional[Set[str]] = None
        self.__test_run_results = None
        self.__type_annotations: Set[str] = set()
        self.__has_setuppy = False
        self.__has_requiremetnstxt = False
        self.__hasmakefile = False

    def grab(self, tmp_dir: Path, testing: bool = False) -> RepoInfo:
        path = tmp_dir.joinpath(self.__repo_name)
        if testing:
            url = "https://github.com/{}/{}".format(self.__repo_user, self.__repo_name)
        else:
            url = "git@github.com:{}/{}".format(self.__repo_user, self.__repo_name)

        try:
            repo = Repo.clone_from(url, path)
        except git.exc.GitCommandError:
            self.__logger.info("GitHub repository {} is not accessible".format(url))
            raise GitRequest.GitRepoNotFoundException("{} is inaccessible".format(url))

        repo_mining = RepositoryMining(str(path))
        self.__num_commits, commits = self.__find_flaw_referencing_commits(repo_mining)
        # issue_ids = self.__extract_issue_ids(commits)
        # commits = self.__add_issue_ids_to_commits(issue_ids, commits)

        cloc_stats = self.__get_cloc_stats(path)
        if cloc_stats is not None and len(cloc_stats) == 2:
            self.__num_files, self.__num_lines = cloc_stats
        # self.__head_commit = repo.head.commit
        # self.__test_frameworks = self.__detect_test_frameworks(path)
        #        self._test_run_results = self._extract_test_run_results(path)
        # self.__type_annotations = self.__detect_type_annotations(path)
        self.__has_setuppy = path.joinpath("setup.yp").exists()
        self.__has_requirementstxt = path.joinpath("requirements.txt").exists()
        self.__has_makefile = path.joinpath("Makefile").exists()

        return RepoInfo(
            has_requirementstxt=self.__has_requirementstxt,
            has_setuppy=self.__has_setuppy,
            has_makefile=self.__has_makefile,
            loc=self.__num_lines,
            average_complexity=self.__average_complexity(path),
        )

    def __average_complexity(self, project_dir: Path) -> int:
        cmd = (
            radon["cc", "-a", project_dir]
            | tail["-n", 1]
            | awk["{print $4}"]
            | tr["-d", r"'()'"]
        )
        _, out, _ = cmd.run(retcode=None)
        try:
            return round(float(out))
        except ValueError:
            self.__logger.error("Error computing average cyclomatic complexity")
            return -1

    @property
    def num_lines(self) -> int:
        return self.__num_lines

    @property
    def num_files(self) -> int:
        return self.__num_files

    @property
    def num_commits(self) -> int:
        return self.__num_commits

    @property
    def head_commit(self) -> Union[Blob, TagObject, Tree, Commit]:
        return self.__head_commit

    @property
    def test_frameworks(self) -> Optional[Set[str]]:
        return self.__test_frameworks

    @property
    def type_annotations(self) -> Set[str]:
        return self.__type_annotations

    @property
    def has_setuppy(self) -> bool:
        return self.__has_setuppy

    @property
    def has_requirementstxt(self) -> bool:
        return self.__has_requirementstxt

    @property
    def has_makefile(self) -> bool:
        return self.__has_makefile

    """
    @property
    def test_run_results(self) -> Optional[RunResult]:
        return self._test_run_results
    """

    def __find_flaw_referencing_commits(
        self, repo_mining: RepositoryMining
    ) -> Tuple[int, Dict[str, RepositoryCommit]]:
        def pretty_diffs(modifications: List[Modification]) -> List[Dict[str, str]]:
            return [
                {
                    "old_path": m.old_path,
                    "new_path": m.new_path,
                    "type": m.change_type.name
                    if m.change_type is not None
                    else "UNKNOWN",
                    "diff": m.diff,
                }
                for m in modifications
            ]

        self.__logger.debug("Search for flaws in commit message")
        commit_counter: int = 0
        commits: Dict[str, RepositoryCommit] = dict()

        for commit in repo_mining.traverse_commits():
            commit_counter += 1
            if self.__close_regex.match(commit.msg) or self.__bugfix_regex.match(
                commit.msg
            ):
                author = "{} <{}>".format(commit.author.name, commit.author.email)
                committer = "{} <{}>".format(
                    commit.committer.name, commit.committer.email
                )
                diff = pretty_diffs(commit.modifications)
                commits[commit.hash] = RepositoryCommit(
                    author=author,
                    author_date=commit.author_date,
                    committer=committer,
                    committer_date=commit.committer_date,
                    msg=commit.msg,
                    parents=commit.parents,
                    diffs=diff,
                )

        return commit_counter, commits

    def __extract_issue_ids(
        self, commits: Dict[str, RepositoryCommit]
    ) -> Dict[str, Set[str]]:
        self.__logger.debug("Extract issue IDs")

        issue_ids: Dict[str, Set[str]] = {}
        for commit, values in commits.items():
            issue_ids[commit] = set()
            for match in self.__close_regex.finditer(values.msg):
                groups = match.groups()
                issue_id = groups[-1]
                if issue_id is not None:
                    issue_ids[commit].add(str(issue_id))
            if len(issue_ids[commit]) == 0:
                issue_ids.pop(commit, None)
        return issue_ids

    @staticmethod
    def __add_issue_ids_to_commits(
        issue_ids: Dict[str, Set[str]], commits: Dict[str, RepositoryCommit]
    ) -> Dict[str, RepositoryCommit]:
        for commit, ids in issue_ids.items():
            commits[commit].issues = list(ids)
        return commits

    @staticmethod
    def __get_cloc_stats(path: Path) -> Optional[Tuple[int, int]]:
        chain = cloc["--include-lang=Python", "--quiet", path] | grep["Python"]
        _, result, _ = chain.run(retcode=None)
        if result is not None:
            results = result.split()
            # results looks like:
            # ['Python', <#files>, <#black lines>, <#comment lines>, <#LOC>]
            # We are interested in #files and #LOC
            if len(results) >= 5:
                return int(results[1]), int(results[4])
        return None

    @staticmethod
    def __detect_type_annotations(path: Path) -> Set[str]:
        type_annotations = set()

        # Check whether there exist *.pyi files
        result = glob(os.path.join(path, "**/*.pyi"), recursive=True)
        if len(result) > 0:
            type_annotations.add("pyi")

        _, result, _ = grep["-R", "from typing import", path].run(retcode=None)
        if len(result) > 0:
            type_annotations.add("typing")

        _, result, _ = grep["-R", "import typing", path].run(retcode=None)
        if len(result) > 0:
            type_annotations.add("typing")

        return type_annotations

    # flake8: noqa: C901
    def __detect_test_frameworks(self, path: Path) -> Optional[Set[str]]:
        self.__logger.debug("Searching for test framework")
        frameworks = set()

        # Check for stdlib unittest framework
        _, result_1, _ = grep["-R", "import unittest", path].run(retcode=None)
        _, result_2, _ = grep["-R", "from unittest import", path].run(retcode=None)
        if len(result_1) > 0 or len(result_2) > 0:
            frameworks.add("unittest")

        # Check for testify framework (https://github.com/Yelp/Testify
        _, result_1, _ = grep["-R", "import testify", path].run(retcode=None)
        _, result_2, _ = grep["-R", "from testify import", path].run(retcode=None)
        if len(result_1) > 0 or len(result_2) > 0:
            frameworks.add("testify")

        # Check for doctest framework
        _, result_1, _ = grep["-R", "import doctest", path].run(retcode=None)
        _, result_2, _ = grep["-R", "from doctest import", path].run(retcode=None)
        if len(result_1) > 0 or len(result_2) > 0:
            frameworks.add("doctest")

        # Check for testtools (https://github.com/testing-cabal/testtools)
        _, result_1, _ = grep["-R", "import testtools", path].run(retcode=None)
        _, result_2, _ = grep["-R", "from testtools import", path].run(retcode=None)
        if len(result_1) > 0 or len(result_2) > 0:
            frameworks.add("testtools")

        # pytest, import pytest, from pytest import
        _, result_1, _ = grep["-R", "import pytest", path].run(retcode=None)
        _, result_2, _ = grep["-R", "from pytest import", path].run(retcode=None)
        _, result_3, _ = grep["-R", "pytest", path].run(retcode=None)
        if len(result_1) > 0 or len(result_2) or len(result_3):
            frameworks.add("pytest")

        # nose
        _, result_1, _ = grep["-R", "nose", path].run(retcode=None)
        if len(result_1) > 0:
            frameworks.add("nose")

        # trial, import twisted, from twisted import, from twisted.* import
        _, result_1, _ = grep["-R", "trial", path].run(retcode=None)
        _, result_2, _ = grep["-R", "import twisted", path].run(retcode=None)
        _, result_3, _ = grep["-R", "from twisted import", path].run(retcode=None)
        _, result_4, _ = grep["-R", "from twisted.* import", path].run(retcode=None)
        if len(result_1) > 0 or len(result_2) > 0 or len(result_3) or len(result_4):
            frameworks.add("trial")

        # import zope, from zope import, from zope.* import
        _, result_1, _ = grep["-R", "import zope", path].run(retcode=None)
        _, result_2, _ = grep["-R", "from zope import", path].run(retcode=None)
        _, result_3, _ = grep["-R", "from zope.* import", path].run(retcode=None)
        if len(result_1) > 0 or len(result_2) > 0 or len(result_3):
            frameworks.add("zope")

        # import logilab, from logilab import (testlib)
        _, result_1, _ = grep["-R", "import logilab", path].run(retcode=None)
        _, result_2, _ = grep["-R", "from logilab import", path].run(retcode=None)
        if len(result_1) > 0 or len(result_2) > 0:
            frameworks.add("testlib")

        ########################################################################

        _, result_1, _ = grep["-R", "import ludibrio", path].run(retcode=None)
        _, result_2, _ = grep["-R", "from ludibrio import", path].run(retcode=None)
        if len(result_1) > 0 or len(result_2) > 0:
            frameworks.add("ludibrio")

        _, result_1, _ = grep["-R", "import mock", path].run(retcode=None)
        _, result_2, _ = grep["-R", "from mock import", path].run(retcode=None)
        if len(result_1) > 0 or len(result_2) > 0:
            frameworks.add("mock")

        _, result_1, _ = grep["-R", "import pymock", path].run(retcode=None)
        _, result_2, _ = grep["-R", "from pymock import", path].run(retcode=None)
        if len(result_1) > 0 or len(result_2) > 0:
            frameworks.add("pymock")

        _, result_1, _ = grep["-R", "import pmock", path].run(retcode=None)
        _, result_2, _ = grep["-R", "from pmock import", path].run(retcode=None)
        if len(result_1) > 0 or len(result_2) > 0:
            frameworks.add("pmock")

        _, result_1, _ = grep["-R", "import minimock", path].run(retcode=None)
        _, result_2, _ = grep["-R", "from minimock import", path].run(retcode=None)
        if len(result_1) > 0 or len(result_2) > 0:
            frameworks.add("minimock")

        _, result_1, _ = grep["-R", "import mocker", path].run(retcode=None)
        _, result_2, _ = grep["-R", "from mocker import", path].run(retcode=None)
        if len(result_1) > 0 or len(result_2) > 0:
            frameworks.add("mocker")

        _, result_1, _ = grep["-R", "import reahl.stubble", path].run(retcode=None)
        _, result_2, _ = grep["-R", "from reahl.stubble import", path].run(retcode=None)
        if len(result_1) > 0 or len(result_2) > 0:
            frameworks.add("stubble")

        _, result_1, _ = grep["-R", "import pymox", path].run(retcode=None)
        _, result_2, _ = grep["-R", "from pymox import", path].run(retcode=None)
        if len(result_1) > 0 or len(result_2) > 0:
            frameworks.add("mox")

        _, result_1, _ = grep["-R", "import mocktest", path].run(retcode=None)
        _, result_2, _ = grep["-R", "from mocktest import", path].run(retcode=None)
        if len(result_1) > 0 or len(result_2) > 0:
            frameworks.add("mocktest")

        _, result_1, _ = grep["-R", "import fudge", path].run(retcode=None)
        _, result_2, _ = grep["-R", "from fudge import", path].run(retcode=None)
        if len(result_1) > 0 or len(result_2) > 0:
            frameworks.add("fudge")

        _, result_1, _ = grep["-R", "import capturemock", path].run(retcode=None)
        _, result_2, _ = grep["-R", "from capturemock import", path].run(retcode=None)
        if len(result_1) > 0 or len(result_2) > 0:
            frameworks.add("capturemock")

        _, result_1, _ = grep["-R", "import flexmock", path].run(retcode=None)
        _, result_2, _ = grep["-R", "from flexmock import", path].run(retcode=None)
        if len(result_1) > 0 or len(result_2) > 0:
            frameworks.add("flexmock")

        _, result_1, _ = grep["-R", "import doublex", path].run(retcode=None)
        _, result_2, _ = grep["-R", "from doublex import", path].run(retcode=None)
        if len(result_1) > 0 or len(result_2) > 0:
            frameworks.add("doublex")

        _, result_1, _ = grep["-R", "import aspectlib", path].run(retcode=None)
        _, result_2, _ = grep["-R", "from aspectlib import", path].run(retcode=None)
        if len(result_1) > 0 or len(result_2) > 0:
            frameworks.add("aspectlib")

        return frameworks if len(frameworks) > 0 else None

    """
    def _extract_test_run_results(self, path: Union[bytes, str]) -> Optional[RunResult]:
        try:
            runner = Runner(
                self._repo_name, path, RunnerType.AUTO_DETECT, time_limit=1800
            )
        except IllegalStateException:
            self._logger.warning("Could not find test runner for %s", self._repo_name)
            return None

        self._logger.debug("Run tests with %s", runner)
        out, _ = runner.run()
        self._logger.debug("Extract run result")
        run_result = runner.extract_run_result(out)

        if (
            run_result.failed < 0
            and run_result.passed < 0
            and run_result.skipped < 0
            and run_result.statements < 0
            and run_result.missing < 0
        ):
            return None

        return run_result
    """
