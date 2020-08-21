import re
from dataclasses import dataclass
from logging import Logger
from os import listdir, path
from tempfile import TemporaryDirectory
from typing import Dict, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup

from pyexec.dependencyInference.inferDependencys import InferDockerfile
from pyexec.mining.gitrequest import GitRequest
from pyexec.mining.pypirequest import PyPIRequest
from pyexec.util.dependencies import Dependencies
from pyexec.util.logging import get_logger


@dataclass
class PackageInfo:
    name: str
    repo_user: Optional[str] = None
    repo_name: Optional[str] = None
    dockerfile: Optional[Dependencies] = None
    has_requirementstxt: bool = False
    has_setuppy: bool = False
    has_makefile: bool = False


class Miner:
    def __init__(self, packages: List[str], logger: Optional[Logger] = None):
        self.__packages = packages
        self.__logger = logger
        self.__github_regex = re.compile(
            r"(http[s]?://)?(www.)?github.com/([^/]*)/(.*)", re.IGNORECASE
        )

    def infer_environments(self) -> List[PackageInfo]:
        result: List[PackageInfo] = list()

        for p in self.__packages:
            info = PackageInfo(name=p)
            result.append(info)
            pypirequest = PyPIRequest(p, self.__logger)
            pypi_info = pypirequest.get_result_from_url()
            if pypi_info is None:
                self.__log_warning("No PyPI information found for package {}".format(p))
                continue

            ghpath = self.__extract_repository_path(pypi_info)
            if ghpath is None:
                self.__log_info("No Github link found for package {}".format(p))
                continue
            user, name = ghpath
            info.repo_user = user
            info.repo_name = name
            gitrequest = GitRequest(user, name, self.__logger)

            try:
                with TemporaryDirectory() as tmp:
                    try:
                        gitrequest.grab(tmp)
                    except GitRequest.GitRepoNotFoundException:
                        continue
                    projectdir = path.join(tmp, listdir(tmp)[0])
                    assert path.exists(projectdir)
                    info.has_requirementstxt = path.exists(
                        path.join(projectdir, "requirements.txt")
                    )
                    info.has_makefile = path.exists(path.join(projectdir, "Makefile"))
                    info.has_setuppy = path.exists(path.join(projectdir, "setup.py"))

                    inferdockerfile = InferDockerfile(projectdir, self.__logger)

                    try:
                        info.dockerfile = inferdockerfile.inferDockerfile()
                    except InferDockerfile.NoEnvironmentFoundException:
                        self.__log_info("No environment found for package {}".format(p))
                        continue
                    except InferDockerfile.TimeoutException:
                        self.__log_info("v2 timed out on package {}".format(p))
                        continue
            except PermissionError:
                continue
                """ Found Repos on GitHub which have a __pycache__ subdirectory with root permission.
                Trying to delete such a directory causes a PermissonError.
                The temporary directory is places in /tmp so it will be eventually clean up when
                shutting down the computer.
                Note: Creating a temporary directory in the (user owned) home folder does not solve
                this problem.
            """
        return result

    def __log_debug(self, msg: str) -> None:
        if self.__logger is not None:
            self.__logger.debug(msg)

    def __log_info(self, msg: str) -> None:
        if self.__logger is not None:
            self.__logger.info(msg)

    def __log_warning(self, msg: str) -> None:
        if self.__logger is not None:
            self.__logger.warning(msg)

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
    def __init__(
        self, packageListFile: str, outputfile: str, logfile: Optional[str] = None
    ) -> None:
        if not path.exists(packageListFile) or not path.isfile(packageListFile):
            raise FileNotFoundError(
                "The file {} does not exist".format(packageListFile)
            )
        if not path.exists(outputfile):
            raise FileNotFoundError("The path {} does not exist".format(outputfile))
        if logfile is not None and not path.exists(logfile):
            raise FileNotFoundError("The path {} does not exist".format(logfile))

        self.__outputfile = outputfile
        with open(packageListFile) as f:
            self.__packageList: List[str] = [line.rstrip() for line in f.readlines()]
        self.__logger = (
            get_logger("PyexecMiner", logfile) if logfile is not None else None
        )

    def mine(self) -> None:
        miner = Miner(self.__packageList, self.__logger)
        result: List[PackageInfo] = miner.infer_environments()
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

        print(
            "Stats:\n\tTotal packages: {}\n\tGitHub Repos: {}\n\tsetup.py: {}\n\trequirements.txt: {}\n\tMakefile: {}\n\n".format(
                len(result), githubs, setups, rqs, makes
            )
        )

        with open(self.__outputfile, "w") as f:
            f.write(", ".join(str(e) for e in result))


def main(argv: List[str]) -> None:
    print(argv)
    if not len(argv) == 3 and not len(argv) == 4:
        print(
            "Need two or three arguments: The package file, output file and optionally logfile"
        )
    elif len(argv) == 3:
        miner = PyexecMiner(argv[1], argv[2])
        miner.mine()
    else:
        miner = PyexecMiner(argv[1], argv[2], argv[3])
        miner.mine()
