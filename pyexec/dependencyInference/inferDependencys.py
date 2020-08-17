import subprocess
from logging import Logger
from os import path
from typing import List, Optional

from pyexec.util.list import flatten, remove_duplicates
from pyexec.util.logging import get_logger
from pyexec.util.shell import run_command


class InferDockerfile:
    class NoEnviromentFoundExcpetion(Exception):
        pass

    class DirectoryNotFoundExcpetion(Exception):
        pass

    class NotADirectoryException(Exception):
        pass

    class TimeoutException(Exception):
        pass

    __projectPath: str
    __logger: Logger

    def __init__(self, projectPath: str, logfile: Optional[str] = None) -> None:
        if not path.exists(projectPath):
            raise InferDockerfile.DirectoryNotFoundExcpetion(
                "There is no file or directory named " + projectPath
            )
        elif not path.isdir(projectPath):
            raise InferDockerfile.NotADirectoryException(
                "The project path" + projectPath + " is not a directory"
            )
        else:
            self.__projectPath = projectPath
            self.__logger = get_logger(__name__, logfile)

    def inferDockerfile(self, timeout: Optional[int] = None) -> str:
        self.__logger.info("Start inferring dependencies")
        files: List[str] = self.__find_python_files()
        self.__logger.debug("Files found: ")
        self.__logger.debug(*files)
        dockerfiles: List[str] = []

        for f in files:
            self.__logger.debug("Inferring file: " + f)
            dockerfiles.append(self.__execute_v2(f, timeout))
            self.__logger.debug("Inferring for file " + f + "successful")
        return self.__mergeDockerfiles(dockerfiles)

    def __find_python_files(self) -> List[str]:
        command: str = "find " + self.__projectPath + " -type f -name '*.py' -not -name 'test*' -not -name '__init__.py'"
        out, _ = run_command(command)
        return out.splitlines()

    def __execute_v2(self, filePath: str, timeout: Optional[int] = None) -> str:
        command: str = 'v2 run --projectdir "' + self.__projectPath + '" --environment "PYTHONPATH=$(find' + self.__projectPath + " -not -path '*/\\.*' -not path '*__pycache__*' -type d -printf \":%p\" | sed \"s|" + self.__projectPath + '|/mnt/projectdir/|g")" ' + filePath

        try:
            out, _ = run_command(command, timeout)
        except subprocess.TimeoutExpired:
            raise InferDockerfile.TimeoutException(
                "A timeout happend during execution of v2"
            )

        out = out.strip()
        if out == "":
            raise InferDockerfile.NoEnviromentFoundExcpetion(
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
        self.__logger.debug("The found dockerfile is: " + file)
        return file
