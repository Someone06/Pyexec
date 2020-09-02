import pickle
from datetime import datetime, timedelta
from functools import reduce
from pathlib import Path
from typing import Callable, List, Optional

from pyexec.mining.githubrequest import GitHubInfo
from pyexec.mining.gitrequest import RepoInfo
from pyexec.mining.miner import PackageInfo
from pyexec.util.logging import get_logger


class Stats:
    def __init__(self, pickled_data: Path, logfile: Optional[Path] = None) -> None:
        self.__logger = get_logger("Pyexec:Stats", logfile)
        if pickled_data.exists() and pickled_data.is_file():
            with open(pickled_data, "rb") as data:
                self.__mined_data: List[PackageInfo] = pickle.load(data)
            if not isinstance(self.__mined_data, list) or not reduce(
                lambda a, b: a and b,
                map(lambda e: isinstance(e, PackageInfo), self.__mined_data),
            ):
                self.__logger.error("Unpickled data has wrong type")
                raise ValueError("Unpickled data has wrong type!")
        else:
            self.__logger.error("No such file: {}".format(pickled_data))
            raise ValueError("Path {} does not refer to a file".format(pickled_data))

    def __accumulate(self, lmbda: Callable[[PackageInfo], bool]) -> int:
        return len([p for p in self.__mined_data if lmbda(p)])

    def projects_attempted(self) -> int:
        return len(self.__mined_data)

    def project_on_pypi(self) -> int:
        return self.__accumulate(lambda p: p.project_on_pypi)

    def github_link_found(self) -> int:
        return self.__accumulate(lambda p: p.github_link_found)

    def github_repos_found(self) -> int:
        return self.__accumulate(lambda p: p.github_repo_exists)

    def dockerfiles_inferred(self) -> int:
        return self.__accumulate(lambda p: p.dockerfile is not None)

    def dockerimages_built(self) -> int:
        return self.__accumulate(lambda p: p.dockerimage_build)

    def testsuit_found(self) -> int:
        return self.__accumulate(lambda p: p.has_testsuit)

    def testsuit_executed(self) -> int:
        return self.__accumulate(lambda p: p.testsuit_executed)

    def testsuit_parsed(self) -> int:
        return self.__accumulate(lambda p: p.testsuit_result_parsed)

    def __repo_info(self) -> List[RepoInfo]:
        return [p.repo_info for p in self.__mined_data if p.repo_info is not None]

    def locs(self) -> List[int]:
        return list(map(lambda r: r.loc, self.__repo_info()))

    def comlexities(self) -> List[float]:
        return list(map(lambda r: r.average_complexity, self.__repo_info()))

    def min_python_versions(self) -> List[int]:
        return [
            r.min_python_version
            for r in self.__repo_info()
            if r.min_python_version is not None
        ]

    def __github_info(self) -> List[GitHubInfo]:
        return [p.github_info for p in self.__mined_data if p.github_info is not None]

    def active_times(self) -> List[timedelta]:
        return list(map(lambda g: g.last_updated - g.created_at, self.__github_info()))

    def exits_since(self) -> List[timedelta]:
        return list(
            map(lambda g: datetime.today() - g.created_at, self.__github_info())
        )


def main(argv: List[str]) -> None:
    if len(argv) != 2:
        print("Argument: A path to a pickled data file")
    else:
        path = Path(argv[1])
        stats = Stats(path)
        print("Stats:")
        print("Attepted: {}".format(stats.projects_attempted()))
        print("Projects found on PyPI: {}".format(stats.project_on_pypi()))
        print("GitHub links found: {}".format(stats.github_link_found()))
        print("GitHub repos found {}".format(stats.github_repos_found()))
        print("Dockerfiles inffered: {}".format(stats.dockerfiles_inferred()))
        print("Testsuits found: {}".format(stats.testsuit_found()))
        print("Dockerimages built: {}".format(stats.dockerimages_built()))
        print("Testsuits executed: {}".format(stats.testsuit_executed()))
        print("Testresults parsed: {}".format(stats.testsuit_parsed()))
