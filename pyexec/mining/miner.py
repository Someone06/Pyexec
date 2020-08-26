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

from pyexec.dependencyInference.inferDependencys import InferDockerfile
from pyexec.mining.gitrequest import GitRequest
from pyexec.mining.pypirequest import PyPIRequest
from pyexec.testrunner.runner import AbstractRunner
from pyexec.testrunner.runners.pytestrunner import PytestRunner
from pyexec.testrunner.runresult import CoverageResult, TestResult
from pyexec.util.dependencies import Dependencies
from pyexec.util.logging import get_logger


@dataclass
class PackageInfo:
    name: str
    repo_user: Optional[str] = None
    repo_name: Optional[str] = None
    dockerfile: Optional[Dependencies] = None
    test_result: Optional[TestResult] = None
    test_coverage: Optional[CoverageResult] = None
    has_requirementstxt: bool = False
    has_setuppy: bool = False
    has_makefile: bool = False


class Miner:
    def __init__(self, packages: List[str], logfile: Optional[Path] = None):
        self.__packages = packages
        self.__logfile = logfile
        self.__logger = get_logger("Pyexec::Miner", logfile)
        self.__github_regex = re.compile(
            r"(http[s]?://)?(www.)?github.com/([^/]*)/(.*)", re.IGNORECASE
        )

    def mine(self) -> List[PackageInfo]:
        self.__logger.info("Starting to mine")
        result: List[PackageInfo] = list()

        for p in self.__packages:
            self.__logger.info("Mining package {}".format(p))
            info = PackageInfo(name=p)
            result.append(info)
            pypirequest = PyPIRequest(p, self.__logfile)
            pypi_info = pypirequest.get_result_from_url()
            if pypi_info is None:
                self.__logger.warning(
                    "No PyPI information found for package {}".format(p)
                )
                continue

            ghpath = self.__extract_repository_path(pypi_info)
            if ghpath is None:
                self.__logger.info("No Github link found for package {}".format(p))
                continue
            user, name = ghpath
            info.repo_user = user
            info.repo_name = name
            gitrequest = GitRequest(user, name, self.__logfile)

            try:
                with TemporaryDirectory() as directory:
                    tmp = Path(directory)
                    try:
                        gitrequest.grab(tmp)
                    except GitRequest.GitRepoNotFoundException:
                        self.__logger.info(
                            "Cound not clone package {} from GitHub".format(p)
                        )
                        continue
                    tmp_content = list(tmp.iterdir())
                    if len(tmp_content) != 1:
                        self.__logger.error(
                            "Check out of repository for packages {} did not work".format(
                                p
                            )
                        )
                        continue
                    projectdir = tmp_content[0]
                    info.has_requirementstxt = projectdir.joinpath(
                        "requirements.txt"
                    ).exists()
                    info.has_makefile = projectdir.joinpath("Makefile").exists()
                    info.has_setuppy = projectdir.joinpath("setup.py").exists()

                    inferdockerfile = InferDockerfile(projectdir, self.__logfile)
                    try:
                        info.dockerfile = inferdockerfile.infer_dockerfile()
                    except InferDockerfile.NoEnvironmentFoundException:
                        self.__logger.info(
                            "No environment found for package {}".format(p)
                        )
                        continue
                    except InferDockerfile.TimeoutException:
                        self.__logger.info("v2 timed out on package {}".format(p))
                        continue

                    if info.dockerfile is not None:
                        runner: AbstractRunner = PytestRunner(
                            tmp, projectdir.name, info.dockerfile, self.__logfile
                        )
                        if runner.is_used_in_project():
                            testresult, coverage = runner.run()

                            info.test_result = testresult
                            info.test_coverage = coverage
            except PermissionError as e:
                self.__logger.warning("Caught Error: {}".format(e))
                continue
                """ Found Repos on GitHub which have a __pycache__ subdirectory with root permission.
                Trying to delete such a directory causes a PermissonError.
                The temporary directories are placed in /tmp so they will be eventually cleaned up when
                shutting down the computer.
                Note: Creating a temporary directory in the (user owned) home folder does not solve
                this problem.
            """
            except KeyboardInterrupt:
                print(
                    "Caught keyboard interrupt. Stopped mining. Returning already mined results"
                )
                return result
            except Exception as e:
                self.__logger.warning("Caught unknown excption: {}".format(e))
                continue
        return result

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
        self.__parser = self._create_parser()
        if len(argv) == 0:
            self.__parser.format_help()
            sys.exit(0)

        self.__config = self.__parser(argv[1:])
        if self.__config.package_list is not None:
            self.__package_list = self.__packages_from_file(
                Path(self.__config.package_list)
            )
        elif self.__config.num:
            n = self.__config.num
            if n <= 0:
                print("Package count must be >= 1")
                raise ValueError("Package count must be >= 1")
            else:
                self.__package_list = self.__random_pypi_packages(n)
        else:
            self.__parser.format_help()
            sys.exit(0)

    @staticmethod
    def __random_pypi_packages(n: int) -> List[str]:
        return (
            wget["-q", "-O-", "pypi.org/simple"]
            | grep["/simple/"]
            | sed['s|    <a href="/simple/||g']
            | sed["s|/.*||g"]
            | shuf["-n", n]().splitlines()
        )

    @staticmethod
    def __packages_from_file(path: Path) -> List[str]:
        if not path.exists() or path.is_file():
            raise NotADirectoryError("Package file path is not a directory")
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
        miner = Miner(self.__package_list, output_dir.joinpath("log.txt"))
        result = miner.mine()

        githubs = 0
        rqs = 0
        setups = 0
        makes = 0
        for i in result:
            if i.repo_user is not None:
                githubs = githubs + 1
            if i.has_requirementstxt:
                rqs = rqs + 1
            if i.has_setuppy:
                setups = setups + 1
            if i.has_makefile:
                makes = makes + 1

        with open(output_dir.joinpath("output.txt"), "w") as f:
            f.write("\n".join(str(e) for e in result))
            f.write(
                "\n\n\nStats:\n\tTotal packages: {}\n\tGitHub Repos: {}\n\tsetup.py: {}\n\trequirements.txt: {}\n\tMakefile: {}\n\n".format(
                    len(result), githubs, setups, rqs, makes
                )
            )

    @staticmethod
    def _create_parser() -> ArgParser:
        parser = ArgParser(
            fromfile_prefix_chars="@",
            description="""
            """,
        )

        miner_source = parser.add_mutually_exclusive_group()
        miner_source.add_argument(
            "-p",
            "--package-list",
            dest="package_list",
            help="Path to a file containing the package list to mine data from. "
            "Each line of this list has to contain one package name on PyPI.",
        )
        miner_source.add_argument(
            "-r", "--random", dest="num", help="Try mining n random packages from PyPI"
        )


def main(argv: List[str]) -> None:
    miner = PyexecMiner(argv)
    miner.mine()
