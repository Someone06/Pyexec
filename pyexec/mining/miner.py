import pickle
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Dict, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup
from configargparse import ArgParser
from plumbum.cmd import grep, sed, shuf, wget

from pyexec.dependencyInference.extraDependencies import ExtraDependencies
from pyexec.dependencyInference.inferDependencys import InferDockerfile
from pyexec.mining.githubrequest import (
    GitHubInfo,
    GitHubRequest,
    GitHubRequestException,
)
from pyexec.mining.gitrequest import GitRequest, RepoInfo
from pyexec.mining.pypirequest import PyPIRequest
from pyexec.testrunner.runner import AbstractRunner, BuildFailedException
from pyexec.testrunner.runners.pytestrunner import PytestRunner
from pyexec.testrunner.runresult import CoverageResult, TestResult
from pyexec.util.dependencies import Dependencies
from pyexec.util.logging import get_logger


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


class Miner:
    def __init__(
        self,
        packages: List[str],
        github_token: Optional[str],
        logfile: Optional[Path] = None,
    ):
        self.__packages = packages
        self.__github_token = github_token
        self.__logfile = logfile
        self.__logger = get_logger("Pyexec::Miner", logfile)
        self.__github_regex = re.compile(
            r"(http[s]?://)?(www.)?github.com/([^/]*)/(.*)", re.IGNORECASE
        )

    def mine(self) -> List[PackageInfo]:
        self.__logger.info("Starting to mine")
        result: List[PackageInfo] = list()

        try:
            with TemporaryDirectory(prefix="pyexec-cache-") as d:
                tmpdir = Path(d)

                for count, p in enumerate(self.__packages):
                    try:
                        self.__logger.info(
                            "Mining package {} (Number {} of  {})".format(
                                p, count + 1, len(self.__packages)
                            )
                        )
                        info = PackageInfo(name=p)
                        result.append(info)
                        pypirequest = PyPIRequest(p, self.__logfile)
                        pypi_info = pypirequest.get_result_from_url()
                        if pypi_info is None:
                            self.__logger.warning(
                                "No PyPI information found for package {}".format(p)
                            )
                            continue

                        info.project_on_pypi = True
                        info.github_repo = self.__extract_repository_path(pypi_info)
                        if info.github_repo is None:
                            self.__logger.info(
                                "No Github link found for package {}".format(p)
                            )
                            continue

                        if self.__github_token is not None:
                            self.__logger.debug("Getting information from GitHub")
                            try:
                                github_request = GitHubRequest(
                                    self.__github_token,
                                    info.github_repo[0],
                                    info.github_repo[1],
                                    self.__logfile,
                                )
                                info.github_info = github_request.get_github_info()
                            except GitHubRequestException:
                                pass
                            except Exception as e:
                                self.__logger.error(
                                    "Unknown exxeption from GitHubRequest: {}".format(e)
                                )

                        try:
                            gitrequest = GitRequest(
                                info.github_repo[0], info.github_repo[1], self.__logfile
                            )
                        except Exception as e:
                            self.__logger.error(
                                "Unknown exception from GitRequest: {}".format(e)
                            )

                        self.__checkout(tmpdir, gitrequest, info)
                    except KeyboardInterrupt:
                        self.__logger.info(
                            "Caught keyboard interrupt. Stopped mining. Returning already mined results"
                        )
                        break
                    except Exception as e:
                        self.__logger.error("Caught unknown exception: {}".format(e))
                        continue
        except PermissionError:
            self.__logger.error(
                "Could not delete temporary directory {}. Requires root permission. Please do this cleanup manually!".format(
                    tmpdir
                )
            )
        return result

    def __checkout(self, basedir: Path, request: GitRequest, info: PackageInfo):
        try:
            with TemporaryDirectory(dir=basedir) as d:
                tmpdir = Path(d)
                try:
                    info.github_repo_exists = True
                    info.repo_info = request.grab(tmpdir)
                except GitRequest.GitRepoNotFoundException:
                    info.github_repo_exists = False
                    self.__logger.info(
                        "Cound not clone package {} from GitHub".format(info.name)
                    )
                    return
                tmp_content = list(tmpdir.iterdir())
                if len(tmp_content) != 1:
                    self.__logger.error(
                        "Check out of repository for packages {} did not work".format(
                            info.name
                        )
                    )
                    return
                projectdir = tmp_content[0]
                count_runner = PytestRunner(
                    tmpdir,
                    projectdir.name,
                    Dependencies("FROM python:3.8"),
                    self.__logfile,
                )
                if count_runner.is_used_in_project():
                    self.__logger.debug("Pytest is used!")
                    info.testcase_count = count_runner.get_test_count()

                info.dockerfile = self._run_v2(projectdir)
                if not info.dockerfile:
                    info.dockerfile = self._get_extra_dependencies(projectdir)
                    if info.dockerfile is None:
                        return
                    else:
                        info.dockerfile_source = "Extras"
                else:
                    info.dockerfile_source = "V2"

                self.__logger.debug("Found dependencies")
                runner: AbstractRunner = PytestRunner(
                    tmpdir, projectdir.name, info.dockerfile, self.__logfile
                )
                if runner.is_used_in_project():
                    info.testcase_count = runner.get_test_count()
                    try:
                        info.dockerimage_build = True
                        info.test_result = runner.run()
                    except BuildFailedException:
                        info.dockerimage_build = False
                    except ValueError:
                        self.__logger.error("Cound not parse test execution results")

        except PermissionError:
            pass
            """
            Found repositories on GitHub which have a __pycache__ sub-directory with root permission.
            Trying to delete such a directory causes a PermissonError.
            The temporary directories are placed in $TMPDIR, which defaults to /tmp so they will
            be eventually cleaned up when shutting down the computer.
            Note: Creating a temporary directory in the (user owned) home folder does not solve
            this problem.
            """

    def _run_v2(self, projectdir: Path) -> Optional[Dependencies]:
        inferdockerfile = InferDockerfile(projectdir, self.__logfile)
        try:
            return inferdockerfile.infer_dockerfile()
        except InferDockerfile.NoEnvironmentFoundException:
            self.__logger.info(
                "No environment found for package {}".format(projectdir.name)
            )
        except InferDockerfile.TimeoutException:
            self.__logger.info("v2 timed out on package {}".format(projectdir.name))
        return None

    def _get_extra_dependencies(self, projectdir: Path) -> Optional[Dependencies]:
        extra = ExtraDependencies(projectdir, self.__logfile)
        deps = extra.get_extra_dependencies()
        if deps:
            df = Dependencies("FROM python:3.8")
            for name, version in deps.items():
                df.add_pip_dependency(name, version)
            self.__logger.debug("Found extra dependencies")
            return df
        else:
            self.__logger.debug("Found no extra dependencies")
            return None

    def __extract_repository_path(
        self, repo_info: Dict[str, str]
    ) -> Optional[Tuple[str, str]]:
        def slash_stripper(string: str) -> str:
            return string.rstrip("/")

        fields: List[str] = ["home_page", "download_url"]
        for field in fields:
            matches = self.__github_regex.match(slash_stripper(repo_info[field]))
            if matches is not None:
                user, name = matches.group(3), matches.group(4)
                return user.split("/", 1)[0], name.split("/", 1)[0]

        for field in fields:
            if "readthedocs" in repo_info[field]:
                content = BeautifulSoup(
                    requests.get(url=repo_info[field], stream=True).content,
                    "html.parser",
                )
                matches = None
                for link in content.findAll("a"):
                    if "github.com" in link.get("href"):
                        matches = self.__github_regex.match(
                            slash_stripper(link.get("href"))
                        )
                    if matches is not None:
                        user, name = matches.group(3), matches.group(4)
                        return user.split("/", 1)[0], name.split("/", 1)[0]
        return None


class PyexecMiner:
    def __init__(self, argv: List[str]) -> None:
        self.__parser = self.__create_parser()
        if len(argv) == 0:
            self.__parser.format_help()
            sys.exit(0)

        self.__config = self.__parser.parse_args(argv[1:])
        self.__github_token: Optional[str] = self.__config.github_token

        if self.__config.package_list is not None:
            self.__package_list = self.__packages_from_file(
                Path(self.__config.package_list)
            )
        elif self.__config.n:
            n = self.__str_to_int(self.__config.n)
            if n is None or n <= 0:
                print("--random requires a positive integer")
                sys.exit(0)
            else:
                self.__package_list = self.__random_pypi_packages(n)
        else:
            self.__parser.format_help()
            sys.exit(0)

    @staticmethod
    def __random_pypi_packages(n: int) -> List[str]:
        cmd = (
            wget["-q", "-O-", "pypi.org/simple"]
            | grep["/simple/"]
            | sed['s|    <a href="/simple/||g']
            | sed["s|/.*||g"]
            | shuf["-n", n]
        )
        return cmd().splitlines()

    @staticmethod
    def __packages_from_file(path: Path) -> List[str]:
        if not path.exists() or not path.is_file():
            raise NotADirectoryError("Package path does not refer to a file")
        with open(path, "r") as f:
            packages = f.readlines()
        packages = [line.strip() for line in packages]
        return packages

    @staticmethod
    def __create_output_dir() -> Path:
        output_dir = (
            Path.home()
            .joinpath("pyexec-output")
            .joinpath(time.strftime("%Y%m%d-%H%M%S"))
        )
        output_dir.mkdir(parents=True)
        return output_dir

    def mine(self) -> None:
        output_dir = self.__create_output_dir()
        miner = Miner(
            self.__package_list, self.__github_token, output_dir.joinpath("log.txt")
        )
        result = miner.mine()

        with open(output_dir.joinpath("pickled_data"), "wb") as p:
            pickle.dump(result, p)

        with open(output_dir.joinpath("output.txt"), "w") as f:
            f.write("\n".join(str(e) for e in result))

        for r in result:
            if r.dockerfile is not None:
                with open(
                    output_dir.joinpath("Dockerfile_{}".format(r.name)), "w"
                ) as f:
                    f.write(r.dockerfile.to_dockerfile())

    @staticmethod
    def __create_parser() -> ArgParser:
        parser = ArgParser()
        miner_source = parser.add_mutually_exclusive_group()
        miner_source.add_argument(
            "-p",
            "--package-list",
            dest="package_list",
            help="Path to a file containing the package list to mine data from. "
            "Each line of this list has to contain one package name on PyPI.",
        )
        miner_source.add_argument(
            "-r", "--random", dest="n", help="Try mining n random packages from PyPI"
        )
        parser.add_argument(
            "-t",
            "--github-token",
            dest="github_token",
            help="A GitHub token for mining data from GitHub",
        )
        return parser

    @staticmethod
    def __str_to_int(n: str) -> Optional[int]:
        try:
            return int(n)
        except ValueError:
            return None


def main(argv: List[str]) -> None:
    miner = PyexecMiner(argv)
    miner.mine()
