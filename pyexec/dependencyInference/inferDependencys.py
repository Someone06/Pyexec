from pathlib import Path
from timeit import default_timer as time
from typing import List, Optional

from plumbum.cmd import find, sed, timeout, v2

from pyexec.util.dependencies import Dependencies
from pyexec.util.logging import get_logger


class InferDockerfile:
    class NoEnvironmentFoundException(Exception):
        pass

    class DirectoryNotFoundException(Exception):
        pass

    class NotADirectoryException(Exception):
        pass

    class TimeoutException(Exception):
        pass

    def __init__(self, project_path: Path, logfile: Optional[Path] = None) -> None:
        if not Path.exists(project_path):
            raise InferDockerfile.DirectoryNotFoundException(
                "There is no file or directory named {}".format(project_path)
            )
        elif not Path.is_dir(project_path):
            raise InferDockerfile.NotADirectoryException(
                "The project path {} is not a directory".format(project_path)
            )
        else:
            self.__project_path = project_path
            self.__python_path = (
                find[
                    self.__project_path,
                    "-type",
                    "d",
                    "-not",
                    "-path",
                    "*__pycache__*",
                    "-not",
                    "-path",
                    "*doc*",
                    "-not",
                    "-path",
                    "*.git*",
                    "-not",
                    "-path",
                    "*examples*",
                    "-printf",
                    ":%p",
                ]
                | sed["s|{}|/mnt/projectdir|g".format(self.__project_path)]
            )()
            self.__logger = get_logger("Pyexec::InferDockerfile", logfile)

    def infer_dockerfile(self, timeout: Optional[int] = None) -> Dependencies:
        self.__logger.info(
            "Start inferring dependencies for package {}".format(
                self.__project_path.name
            )
        )
        files: List[Path] = self.__find_python_files()
        if len(files) == 0:
            self.__logger.warning(
                "No files found for project {}".format(self.__project_path.name)
            )
            raise InferDockerfile.NoEnvironmentFoundException(
                "No file found for project {}".format(self.__project_path.name)
            )
        else:
            self.__logger.debug("Found {} Python files".format(len(files)))

        dependencies: List[Dependencies] = []
        startTime = time()
        for f in files:
            self.__logger.debug("Inferring file: {}".format(f))
            if timeout is not None:
                runtime = time() - startTime
                if runtime < timeout:
                    df = self.__execute_v2(f, int(timeout - runtime))
                else:
                    self.__logger.debug("Timed out on file {}".format(f))
                    self.__logger.info(
                        "Timed out on project {}".format(self.__project_path.name)
                    )
                    raise InferDockerfile.TimeoutException(
                        "Timed out on file {}".format(f)
                    )
            else:
                df = self.__execute_v2(f)

            if df is None:
                self.__logger.debug("No environment found for file {}".format(f))
                self.__logger.info(
                    "No environment found for package {}".format(
                        self.__project_path.name
                    )
                )
                raise InferDockerfile.NoEnvironmentFoundException(
                    "V2 was unable to infer a working environment"
                )
            else:
                dependencies.append(df)
                self.__logger.debug("Inferring for file {} successful".format(f))

        self.__logger.info(
            "Dependency inference successful for package {}".format(
                self.__project_path.name
            )
        )
        try:
            return Dependencies.merge_dependencies(dependencies)
        except Exception as e:
            self.__logger.debug(e)
            raise e

    def __find_python_files(self) -> List[Path]:
        command = find[
            self.__project_path,
            "-type",
            "f",
            "-name",
            "*.py",
            "-not",
            "-path",
            "*__pycache__*",
            "-not",
            "-path",
            "*doc*",
            "-not",
            "-path",
            "*examples*",
            "-not",
            "-path",
            "*.git*",
            "-not",
            "-name",
            "setup.py",
            "-not",
            "-name",
            "__init__.py",
        ]
        return [Path(line) for line in command().splitlines()]

    def __execute_v2(
        self, file_path: Path, tout: Optional[int] = None
    ) -> Optional[Dependencies]:
        if tout is not None:
            command = timeout[
                tout,
                "v2",
                "run",
                "--projectdir",
                self.__project_path,
                "--environment",
                "PYTHONPATH={}".format(self.__python_path),
                "--exclude",
                self.__project_path.name.lower(),
                file_path,
            ]
        else:
            command = v2[
                "run",
                "--projectdir",
                self.__project_path,
                "--environment",
                "PYTHONPATH={}".format(self.__python_path),
                "--exclude",
                self.__project_path.name.lower(),
                file_path,
            ]

        try:
            ret, out, _ = command.run(retcode=None)
        except OSError:
            self.__logger.warning("Caught OSError")
            return None  # Reason this can be thrown: Too long argument list

        if tout is not None and ret == 124:  # Timeout triggered, see 'man timeout'
            self.__logger.debug("Timed out on file {}".format(file_path))
            self.__logger.info(
                "Timed out on project {}".format(self.__project_path.name)
            )
            raise InferDockerfile.TimeoutException(
                "V2 timed out on file {}".format(file_path.name)
            )

        lines = out.splitlines()
        if len(lines) >= 1 and lines[0].startswith("FROM python:"):
            try:
                return Dependencies.from_dockerfile(out)
            except Dependencies.InvalidFormatException:
                self.__logger.error(
                    "V2 produced ill-formatted dockerfile:\n{}".format(out)
                )
                raise InferDockerfile.NoEnvironmentFoundException(
                    "V2 did produce an ill-formatted dockerfile"
                )
        else:
            return None
