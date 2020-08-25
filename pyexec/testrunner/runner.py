from abc import ABC, abstractmethod
from pathlib import Path, PurePath
from typing import Optional, Tuple

from plumbum.cmd import docker, timeout

from pyexec.testrunner.runresult import CoverageResult, TestResult
from pyexec.util.dependencies import Dependencies
from pyexec.util.logging import get_logger


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

        project_path = PurePath.joinpath(tmp_path, project_name)
        if not project_path.exists() or not project_path.is_dir():
            raise NotADirectoryError(
                "There is not directory {} in directory {}".format(
                    project_name, tmp_path
                )
            )

        self._tmp_path = tmp_path
        self._project_name = project_name
        self._project_path = project_path
        self._dependencies = dependencies
        self._logger = get_logger("Pyexec:AbstractRunner", logfile)

    @abstractmethod
    def run(self) -> Tuple[Optional[TestResult], Optional[CoverageResult]]:
        raise NotImplementedError("Implement run()")

    @abstractmethod
    def is_used_in_project(self) -> bool:
        raise NotImplementedError("Implement is_used_in_project()")

    def _run_container(self, tout: Optional[int] = None) -> Optional[Tuple[str, str]]:
        self._dependencies.add_copy_command(
            "COPY {} /tmp/{}/".format(self._project_name, self._project_name)
        )
        self._dependencies.set_workdir_command(
            "WORKDIR /tmp/{}".format(self._project_name)
        )
        self._logger.debug("Writing Dockerfile")
        with open(self._tmp_path.joinpath("Dockerfile"), "w") as f:
            f.write(self._dependencies.to_dockerfile())
        self._logger.debug("Building docker image")
        docker["build", "-t", "pyexec/container", str(self._tmp_path)]()

        if timeout is not None:
            run_command = timeout[tout, "docker", "run", "--rm", "pyexec/container"]
        else:
            run_command = docker["run", "--rm", "pyexec/container"]
        self._logger.debug("Running container")
        ret, out, err = run_command.run(retcode=None)
        self._logger.debug("Container done, removing image")
        docker[
            "rmi", docker["images", "pyexec/container", "-f", "dangling=true", "-q"]
        ]()

        if (
            timeout is not None and ret == 124
        ):  # Timeout was triggered, see 'man timeout'
            self._logger.warning(
                "Timeout during test case execution for project {}".format(
                    self._project_name
                )
            )
            return None
        else:
            return out, err