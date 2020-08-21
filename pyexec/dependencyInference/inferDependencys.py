from logging import Logger
from os import path
from timeit import default_timer as time
from typing import List, Optional

from plumbum import local
from plumbum.cmd import find, sed, timeout

from pyexec.util.list import flatten, remove_duplicates


class InferDockerfile:
    class NoEnvironmentFoundException(Exception):
        pass

    class DirectoryNotFoundException(Exception):
        pass

    class NotADirectoryException(Exception):
        pass

    class TimeoutException(Exception):
        pass

    def __init__(self, projectPath: str, logger: Optional[Logger] = None) -> None:
        if not path.exists(projectPath):
            raise InferDockerfile.DirectoryNotFoundException(
                "There is no file or directory named " + projectPath
            )
        elif not path.isdir(projectPath):
            raise InferDockerfile.NotADirectoryException(
                "The project path" + projectPath + " is not a directory"
            )
        else:
            self.__projectPath = projectPath.rstrip("/")
            self.__v2 = local["v2"]
            self.__pythonPath = (
                find[
                    self.__projectPath,
                    "-type",
                    "d",
                    "-not",
                    "-path",
                    "*__pycache__*",
                    "-not",
                    "-path",
                    "*tests*",
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
                | sed["s|{}|/mnt/projectdir|g".format(self.__projectPath)]
            )()
            self.__logger = logger

    def inferDockerfile(self, timeout: Optional[int] = None) -> str:
        self.__log_info(
            "Start inferring dependencies for package {}".format(self.__projectPath)
        )
        files: List[str] = self.__find_python_files()
        self.__log_debug("Files found:\n{}".format("\t\n".join(files)))
        dockerfiles: List[str] = []
        startTime = time()

        for f in files:
            self.__log_debug("Inferring file: " + f)
            if timeout is not None:
                runtime = time() - startTime
                if runtime < timeout:
                    df = self.__execute_v2(f, int(timeout - runtime))
                else:
                    df = None
            else:
                df = self.__execute_v2(f, None)

            if timeout is not None:
                runtime = int(time() - startTime)
                if (
                    runtime + 2 >= timeout
                ):  # The + 2 is needed because of measurement inaccuracies
                    raise InferDockerfile.TimeoutException("V2 timeout")
            if df is None:
                raise InferDockerfile.NoEnvironmentFoundException(
                    "V2 was unable to infer a working environment"
                )
            else:
                dockerfiles.append(df)
                self.__log_debug("Inferring for file " + f + " successful")
        return self.__mergeDockerfiles(dockerfiles)

    def __find_python_files(self) -> List[str]:
        command = find[
            self.__projectPath,
            "-type",
            "f",
            "-name",
            "*.py",
            "-not",
            "-path",
            "*__pycache__*",
            "-not",
            "-path",
            "*tests*",
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
        return command().splitlines()

    def __execute_v2(self, filePath: str, tout: Optional[int] = None) -> Optional[str]:
        print(self.__pythonPath)
        if tout is not None:
            command = timeout[
                tout,
                "v2",
                "run",
                "--projectdir",
                self.__projectPath,
                "--environment",
                "PYTHONPATH={}".format(self.__pythonPath),
                filePath,
            ]
        else:
            command = self.__v2[
                "run",
                "--projectdir",
                self.__projectPath,
                "--environment",
                "PYTHONPATH={}".format(self.__pythonPath),
                filePath,
            ]

        try:
            _, out, _ = command.run(retcode=None)
        except OSError:
            self.__log_warning("Caught OSError")
            return None  # Reason this can be thrown: Too long argument list
        lines = out.splitlines()
        if len(lines) >= 2 and lines[0] == "FROM python:3.8":
            return lines
        else:
            return None

    def __mergeDockerfiles(self, dockerfiles: List[str]) -> str:
        lines: List[List[str]] = [f.splitlines() for f in dockerfiles]
        for f in lines:
            f.pop()
            f.pop(1)
        file = "\n".join(remove_duplicates(flatten(lines)))
        self.__log_debug("The found dockerfile is: " + file)
        return file

    def __log_info(self, msg: str) -> None:
        if self.__logger is not None:
            self.__logger.info(msg)

    def __log_debug(self, msg: str) -> None:
        if self.__logger is not None:
            self.__logger.debug(msg)

    def __log_warning(self, msg: str) -> None:
        if self.__logger is not None:
            self.__logger.warning(msg)
