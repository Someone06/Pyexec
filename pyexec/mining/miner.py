import re
from dataclasses import dataclass
from logging import Logger
from os import path
from tempfile import TemporaryDirectory
from typing import Dict, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup

from pyexec.depenencyInferrance.inferDependencys import InferDockerfile
from pyexec.mining.gitrequest import GitRequest
from pyexec.mining.Miner import PackageInfo
from pyexec.mining.pypirequest import PyPIRequest


class Miner:
    @dataclass
    class PackageInfo:
        name: str
        repo_user: Optional[str]
        repo_name: Optional[str]
        dockerfile: Optional[str]

    def __init__(self, packages: List[str], logger: Optional[Logger]):
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

            (user, name) = self.__extract_repository_path(pypi_info)  # type: ignore
            if (user, name) is None:
                self.__log_info("No Github link found for package {}".format(p))
                continue
            info.repo_user = user
            info.repo_name = name
            gitrequest = GitRequest(user, name, self.__logger)

            with TemporaryDirectory() as tmp:
                gitrequest.grab(tmp)
                inferdockerfile = InferDockerfile(path.join(tmp, p))

                try:
                    info.dockerfile = inferdockerfile.inferDockerfile()
                except InferDockerfile.NoEnvironmenFoundExpection:
                    self.__log_info("No environment found for package {}".format(p))
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
