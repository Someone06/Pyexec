import subprocess
from logging import Logger
from os import path
from typing import List, Optional

from pyexec.util.list import flatten, remove_duplicates
from pyexec.util.shell import run_command


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
            self.__projectPath = projectPath
            self.__logger = logger

    def inferDockerfile(self, timeout: Optional[int] = None) -> str:
        self.__log_info("Start inferring dependencies")
        files: List[str] = self.__find_python_files()
        self.__log_debug("Files found: ")
        self.__log_debug(" ".join(files))
        dockerfiles: List[str] = []

        for f in files:
            self.__log_debug("Inferring file: " + f)
            dockerfiles.append(self.__execute_v2(f, timeout))
            self.__log_debug("Inferring for file " + f + "successful")
        return self.__mergeDockerfiles(dockerfiles)

    def __find_python_files(self) -> List[str]:
        command: str = "find " + self.__projectPath + " -type f -name '*.py' -not -path '*tests*' -not -name '__init__.py' -not -name 'setup.py' -not -path '*doc*' -not -path '*examples*'"
        out, _ = run_command(command)
        return out.splitlines()

    def __execute_v2(self, filePath: str, timeout: Optional[int] = None) -> str:
        command: str = 'v2 run --projectdir "' + self.__projectPath + '" --environment "PYTHONPATH=$(find ' + self.__projectPath + " -not -path '*/\\.*' -not path '*__pycache__*' -type d -printf \":%p\" | sed \"s|" + self.__projectPath + '|/mnt/projectdir|g")" ' + filePath
        self.__log_debug("Calling v2: {}".format(command))

        try:
            out, _ = run_command(command, timeout)
        except subprocess.TimeoutExpired:
            raise InferDockerfile.TimeoutException(
                "A timeout happend during execution of v2"
            )

        out = out.strip()
        if out == "":
            self.__log_debug("No dockerfile for module {}".format(filePath))
            raise InferDockerfile.NoEnvironmentFoundException(
                "V2 is unable to infer a working environment for package " + filePath
            )
        else:
            return out

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
