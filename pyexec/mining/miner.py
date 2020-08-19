import re
from dataclasses import dataclass
from logging import Logger
from os import path
from tempfile import TemporaryDirectory
from typing import Dict, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup

from pyexec.dependencyInference.inferDependencys import InferDockerfile
from pyexec.mining.gitrequest import GitRequest
from pyexec.mining.pypirequest import PyPIRequest
from pyexec.util.logging import get_logger


@dataclass
class PackageInfo:
    name: str
    repo_user: Optional[str] = None
    repo_name: Optional[str] = None
    dockerfile: Optional[str] = None


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

            with TemporaryDirectory() as tmp:
                gitrequest.grab(tmp)
                inferdockerfile = InferDockerfile(
                    path.join(tmp, p.capitalize()), self.__logger
                )

                try:
                    info.dockerfile = inferdockerfile.inferDockerfile()
                except InferDockerfile.NoEnvironmentFoundException:
                    self.__log_info("No environment found for package {}".format(p))
                    continue
                except InferDockerfile.TimeoutException:
                    self.__log_info("v2 timed out on package {}".format(p))
                    continue

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

    @staticmethod
    def __has_github_repository(repo_info: Dict[str, str]) -> bool:
        return (
            "github.com" in repo_info["download_url"]
            or "github.com" in repo_info["home_page"]
        )

    @staticmethod
    def __has_github_link_on_readthedocs(repo_info: Dict[str, str]) -> bool:
        if (
            "readthedocs" not in repo_info["download_url"]
            and "readthedocs" not in repo_info["home_page"]
        ):
            return False

        if "readthedocs" in repo_info["download_url"]:
            site = repo_info["download_url"]
        else:
            site = repo_info["home_page"]

        content = BeautifulSoup(
            requests.get(url=site, stream=True).content, "html.parser"
        )
        for link in content.findAll("a"):
            if "github.com" in link.get("href"):
                return True
        return False

    def __extract_repository_path(
        self, repo_info: Dict[str, str]
    ) -> Optional[Tuple[str, str]]:
        def slash_stripper(string: str) -> str:
            return string[:-1] if string[-1] == "/" else string

        if self.__has_github_repository(repo_info):
            if "github.com" in repo_info["download_url"]:
                matches = self.__github_regex.match(
                    slash_stripper(repo_info["download_url"])
                )
            else:
                matches = self.__github_regex.match(
                    slash_stripper(repo_info["home_page"])
                )
            assert matches is not None
            user, name = matches.group(3), matches.group(4)
            # Remove trailing things after slashes and only keep first part
            return user.split("/", 1)[0], name.split("/", 1)[0]

        elif self.__has_github_link_on_readthedocs(repo_info):
            if "readthedocs" in repo_info["download_url"]:
                site = repo_info["download_url"]
            else:
                site = repo_info["home_page"]

            content = BeautifulSoup(
                requests.get(url=site, stream=True).content, "html.parser"
            )
            matches = None
            for link in content.findAll("a"):
                if "github.com" in link.get("href"):
                    matches = self.__github_regex.match(
                        slash_stripper(link.get("href"))
                    )
                    break
            assert matches is not None
            user, name = matches.group(3), matches.group(4)

            # Remove trailing things after slashes and only keep first part
            return user.split("/", 1)[0], name.split("/", 1)[0]

        else:
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
