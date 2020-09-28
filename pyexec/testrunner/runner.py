from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Tuple

from pyexec.dockerTools.dockerTools import DockerTools
from pyexec.testrunner.runresult import CoverageResult, TestResult
from pyexec.util.dependencies import Dependencies
from pyexec.util.logging import get_logger


class RunnerNotUsedException(Exception):
    pass


class AbstractRunner(ABC):
    def __init__(
        self,
        tmp_path: Path,
        project_name: str,
        dependencies: Dependencies,
        logfile: Optional[Path] = None,
    ) -> None:
        if not tmp_path.exists() or not tmp_path.is_dir():
            raise NotADirectoryError(
                "The path {} does not refer to a directory".format(tmp_path)
            )

        project_path = tmp_path.joinpath(project_name)
        if not project_path.exists() or not project_path.is_dir():
            raise NotADirectoryError(
                "There is not directory {} in directory {}".format(
                    project_name, tmp_path
                )
            )

        self._project_path = project_path
        self._dependencies = dependencies
        self._project_name = project_name
        self._logfile = logfile
        self._logger = get_logger("Pyexec:AbstractRunner", logfile)

    @abstractmethod
    def run(self) -> Tuple[TestResult, CoverageResult]:
        raise NotImplementedError("Implement run()")

    @abstractmethod
    def is_used_in_project(self) -> bool:
        raise NotImplementedError("Implement is_used_in_project()")

    @abstractmethod
    def get_test_count(self) -> Optional[int]:
        raise NotImplementedError("Implement get_test_count()")

    def _run(self, tout: Optional[int] = None) -> Tuple[str, str]:
        self.__add_dependencies()
        docker = DockerTools(
            self._dependencies,
            self._project_path.parent,
            self._project_name,
            self._logfile,
        )
        docker.remove_image()
        docker.write_dockerfile()
        docker.build_image()

        try:
            return docker.run_container(tout)
        finally:
            docker.remove_image()

    def __add_dependencies(self) -> None:
        self._dependencies.set_copy_command(
            "COPY {} /tmp/{}/".format(self._project_path.name, self._project_path.name)
        )
        self._dependencies.set_workdir_command(
            "WORKDIR /tmp/{}".format(self._project_path.name)
        )
