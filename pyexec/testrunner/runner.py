from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Tuple

from plumbum.cmd import docker, timeout

from pyexec.testrunner.runresult import CoverageResult, TestResult
from pyexec.util.dependencies import Dependencies
from pyexec.util.exceptions import TimeoutException
from pyexec.util.logging import get_logger


class BuildFailedException(Exception):
    pass


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
        self._tag = "pyexec/{}".format(self._project_path.name.lower())
        self._logger = get_logger("Pyexec:AbstractRunner", logfile)

    @abstractmethod
    def run(self) -> Tuple[TestResult, CoverageResult]:
        raise NotImplementedError("Implement run()")

    @abstractmethod
    def is_used_in_project(self) -> bool:
        raise NotImplementedError("Implement is_used_in_project()")

    @abstractmethod
    def get_test_count(self) -> int:
        raise NotImplementedError("Implement get_test_count()")

    def _run(self, tout: Optional[int] = None) -> Tuple[str, str]:
        self.__remove_image()
        self.__add_dependencies()
        self.__write_dockerfile()
        self.__build_image()
        try:
            return self.__run_container(tout)
        finally:
            self.__remove_image()

    def __add_dependencies(self) -> None:
        self._dependencies.set_copy_command(
            "COPY {} /tmp/{}/".format(self._project_path.name, self._project_path.name)
        )
        self._dependencies.set_workdir_command(
            "WORKDIR /tmp/{}".format(self._project_path.name)
        )

    def __write_dockerfile(self) -> None:
        self._logger.debug("Writing Dockerfile")
        with open(self._project_path.parent.joinpath("Dockerfile"), "w") as f:
            f.write(self._dependencies.to_dockerfile())

    def __build_image(self) -> None:
        self._logger.debug("Building docker image")
        _, out, err = docker["build", "-t", self._tag, self._project_path.parent].run(
            retcode=None
        )
        self._logger.debug("Build")
        success = out.splitlines()[-1].startswith("Success")
        if success:
            self._logger.debug("Successfully build image")
        else:
            self._logger.debug("Error building image")
            raise BuildFailedException("docker build command failed")

    def __run_container(self, tout: Optional[int]) -> Tuple[str, str]:
        self._logger.debug("Running container")
        if tout is not None:
            run_command = timeout[tout, "docker", "run", "--rm", self._tag]
        else:
            run_command = docker["run", "--rm", self._tag]

        ret, out, err = run_command.run(retcode=None)
        if (
            timeout is not None and ret == 124
        ):  # Timeout was triggered, see 'man timeout'
            self._logger.warning(
                "Timeout during test case execution for project {}".format(
                    self._project_path.name
                )
            )
            raise TimeoutException("Timeout during test case execution")
        else:
            self._logger.debug("Successfully run container")
            return out, err

    def __remove_image(self) -> None:
        self._logger.debug("Remove docker image")
        _, out, _ = docker["images", "-q", self._tag].run(retcode=None)
        out = out.strip()
        if not out.startswith("Error"):
            docker["rmi", out].run(retcode=None)
