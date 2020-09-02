import pickle
from functools import reduce
from pathlib import Path
from typing import Callable, List, Optional

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

    def testsuit_executed(self) -> int:
        return self.__accumulate(lambda p: p.testsuit_executed)

    def testsuit_parsed(self) -> int:
        return self.__accumulate(lambda p: p.testsuit_result_parsed)


def main(argv: List[str]) -> None:
    if len(argv) != 2:
        print("Argument: A path to a pickled data file")
    else:
        path = Path(argv[1])
        stats = Stats(path)
        print(stats.projects_attempted)
