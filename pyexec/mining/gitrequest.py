import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from git import Repo
from git.exc import GitCommandError
from plumbum.cmd import awk, cloc, find, grep, radon, tail, tr, wc

from pyexec.util.logging import get_logger


@dataclass
class RepoInfo:
    has_requirementstxt: bool
    has_setuppy: bool
    has_makefile: bool
    has_pipfile: bool
    loc: Optional[int]
    num_impl_files: Optional[int]
    num_test_files: Optional[int]
    average_complexity: Optional[float]
    min_python_version: Optional[int]


class GitRequest:
    class GitRepoNotFoundException(Exception):
        pass

    __close_regex = re.compile(
        r"(close([sd])?|fix(es|ed)?|resolve([sd])?)\s+#(\d+)", re.IGNORECASE
    )
    __bugfix_regex = re.compile(
        r"(error|fix|issue|mistake|incorrect|fault|detect|flaw)", re.IGNORECASE
    )

    __python_version_regex_1 = re.compile(r"[Pp]ython ?:: ?3\.\d+")
    __python_version_regex_2 = re.compile(
        r"""python_requires ?= ?["'].?.?3\.(\d+)["']"""
    )
    __python_version_regex_3 = re.compile(r"""python_version ?..? ?["']?3\.(\d+)""")

    def __init__(
        self, repo_user: str, repo_name: str, logfile: Optional[Path] = None
    ) -> None:
        self.__repo_user = repo_user
        self.__repo_name = repo_name
        self.__logger = get_logger("Pyexec::GitRequest", logfile)

        self.__num_lines = -1
        self.__num_impl_files: Optional[int] = None
        self.__num_test_files: Optional[int] = None
        self.__has_setuppy = False
        self.__has_requiremetnstxt = False
        self.__hasmakefile = False

    def grab(self, tmp_dir: Path) -> RepoInfo:
        path = tmp_dir.joinpath(self.__repo_name)
        url = "git@github.com:{}/{}".format(self.__repo_user, self.__repo_name)

        try:
            _ = Repo.clone_from(url, path)
        except GitCommandError:
            self.__logger.info("GitHub repository {} is not accessible".format(url))
            raise GitRequest.GitRepoNotFoundException("{} is inaccessible".format(url))

        cloc_stats = self.__get_cloc_stats(path)
        if cloc_stats is not None:
            self.__num_lines = cloc_stats

        self.__num_impl_files = self.__impl_files(path)
        self.__num_test_files = self.__test_files(path)
        self.__has_setuppy = path.joinpath("setup.py").exists()
        self.__has_requirementstxt = path.joinpath("requirements.txt").exists()
        self.__has_makefile = path.joinpath("Makefile").exists()
        self.__has_pipfile = path.joinpath("Pipfile").exists()

        return RepoInfo(
            has_requirementstxt=self.__has_requirementstxt,
            has_setuppy=self.__has_setuppy,
            has_makefile=self.__has_makefile,
            has_pipfile=self.__has_pipfile,
            loc=self.__num_lines,
            num_impl_files=self.__num_impl_files,
            num_test_files=self.__num_test_files,
            average_complexity=self.__average_complexity(path),
            min_python_version=self.__min_python_version(path),
        )

    def __min_python_version(self, project_dir: Path) -> Optional[int]:
        setuppy = project_dir.joinpath("setup.py")
        if setuppy.exists() and setuppy.is_file():
            with open(setuppy, "r") as f:
                content = f.read()
            match = self.__python_version_regex_2.search(content)
            if match is not None:
                return int(match.group(1))
            found = self.__python_version_regex_1.findall(content)
            versions = [int(m[m.index(".") + 1 :]) for m in found]
            if len(versions) != 0:
                return min(versions)
        setupcfg = project_dir.joinpath("setup.cfg")
        if setupcfg.exists() and setupcfg.is_file():
            with open(setupcfg, "r") as f:
                content = f.read()
            match = self.__python_version_regex_3.search(content)
            if match is not None:
                return int(match.group(1))
        return None

    def __get_cloc_stats(self, path: Path) -> Optional[int]:
        chain = cloc["--include-lang=Python", "--quiet", path] | grep["Python"]
        _, result, _ = chain.run(retcode=None)
        if result is not None:
            results = result.split()
            # results looks like:
            # ['Python', <#files>, <#black lines>, <#comment lines>, <#LOC>]
            # We are interested in #LOC
            if len(results) >= 5:
                return int(results[4])
        self.__logger.error("Unable to obtaion cloc stats")
        return None

    def __average_complexity(self, project_dir: Path) -> Optional[float]:
        cmd = (
            radon["cc", "-a", project_dir]
            | tail["-n", 1]
            | awk["{print $4}"]
            | tr["-d", r"'()'"]
        )
        _, out, _ = cmd.run(retcode=None)
        try:
            return float(out)
        except ValueError:
            self.__logger.error("Error computing average cyclomatic complexity")
            return None

    def __impl_files(self, project_dir: Path) -> Optional[int]:
        command = (
            find[
                project_dir,
                "-type",
                "f",
                "-name",
                "*.py",
                "-not",
                "-path",
                "*/__pycache__*",
                "-not",
                "-path",
                "*/doc*",
                "-not",
                "-path",
                "*/example*",
                "-not",
                "-path",
                "*/.git*",
                "-not",
                "-path",
                "*/test*",
                "-not",
                "-name",
                "setup.py",
                "-not",
                "-name",
                "__init__.py",
                "-not",
                "-name",
                "test_*.py",
                "-not",
                "-name",
                "*_test.py",
            ]
            | wc["-l"]
        )
        _, out, _ = command.run(retcode=None)
        try:
            return int(out)
        except ValueError:
            return 0

    def __test_files(self, project_dir: Path) -> Optional[int]:
        command = (
            find[
                project_dir,
                "-type",
                "f",
                "-not",
                "-path",
                "*/__pycache__*",
                "-not",
                "-path",
                "*/doc*",
                "-not",
                "-path",
                "*/example*",
                "-not",
                "-path",
                "*/.git*",
                "-not",
                "-name",
                "setup.py",
                "-not",
                "-name",
                "__init__.py",
                "-path",
                "*/test*",
                "(",
                "-name",
                "test_*.py",
                "-o",
                "-name",
                "*_test.py",
                ")",
            ]
            | wc["-l"]
        )
        _, out, _ = command.run(retcode=None)
        try:
            return int(out)
        except ValueError:
            return 0
