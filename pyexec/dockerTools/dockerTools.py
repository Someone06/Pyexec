from pathlib import Path
from typing import Optional, Tuple

from plumbum.cmd import docker, timeout, xargs

from pyexec.util.dependencies import Dependencies
from pyexec.util.exceptions import TimeoutException
from pyexec.util.logging import get_logger


class BuildFailedException(Exception):
    pass


class DockerTools:
    def __init__(
        self,
        dependencies: Dependencies,
        context: Path,
        project_name: str,
        logfile: Optional[Path] = None,
    ) -> None:
        self.__logger = get_logger("Pyexec::DockerTools", logfile)
        self.__dependencies = dependencies
        self.__project_name = project_name.lower()
        self.__tag = "pyexec:" + self.__project_name
        self.__image_id = ""
        self.__context = context
        if not self.__context.exists() or not self.__context.is_dir():
            raise ValueError("Context is not a directory")

    def write_dockerfile(self) -> None:
        self.__logger.debug("Writing Dockerfile")
        with open(self.__context.joinpath("Dockerfile"), "w") as f:
            f.write(self.__dependencies.to_dockerfile())

    def build_image(self) -> None:
        self.__logger.debug("Building docker image")
        _ = docker["build", "-q", "-t", self.__tag, self.__context].run(retcode=None)
        self.__logger.debug("Build")
        _, self.__image_id, _ = docker["images", "-q", self.__tag].run(retcode=None)
        if self.__image_id != "":
            self.__logger.debug("Successfully build image")
        else:
            self.__logger.debug("Error building image")
            raise BuildFailedException("docker build command failed")

    def run_container(self, tout: Optional[int]) -> Tuple[str, str]:
        if self.__image_id == "":
            self.__logger.error("No image to run container from!")
            return "", ""

        self.__logger.debug("Running container")
        if tout is not None:
            run_command = timeout[
                tout,
                "docker",
                "run",
                "--name",
                self.__project_name,
                "--rm",
                self.__tag,
            ]
        else:
            run_command = docker[
                "run", "--rm", "--name", self.__project_name, self.__tag
            ]

        ret, out, err = run_command.run(retcode=None)
        remove_container = (
            docker["ps", "-a", "-q", "--filter", "ancestor=" + self.__image_id]
            | xargs["-r", "docker", "rm", "-v"]
        )
        _ = remove_container.run(retcode=None)
        if (
            timeout is not None and ret == 124
        ):  # Timeout was triggered, see 'man timeout'
            self.__logger.warning("Timeout during test case execution")
            raise TimeoutException("Timeout during test case execution")
        else:
            self.__logger.debug("Successfully run container")
            return out, err

    def remove_image(self) -> None:
        self.__logger.debug("Remove docker image")
        _ = docker["rmi", "-f", self.__tag].run(retcode=None)
        _ = docker["rmi", "-f", self.__image_id].run(retcode=None)
