import subprocess
from os import path
from typing import List, Optional

from pyexec.util.list import flatten, remove_duplicates
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

    def __init__(self, projectPath: str) -> None:
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

    def inferDockerfile(self, timeout: Optional[int] = None) -> str:
        files: List[str] = InferDockerfile.__find_python_files(self.__projectPath)
        dockerfiles: List[str] = []

        for f in files:
            dockerfiles.append(
                InferDockerfile.__execute_v2(self.__projectPath, f, timeout)
            )
        return InferDockerfile.__mergeDockerfiles(dockerfiles)

    @staticmethod
    def __find_python_files(projectPath: str) -> List[str]:
        command: str = "find " + projectPath + " -type f -name '*.py' -not -name 'test*' -not -name '__init__.py'"
        out, _ = run_command(command)
        return out.splitlines()

    @staticmethod
    def __execute_v2(
        projectPath: str, filePath: str, timeout: Optional[int] = None
    ) -> str:
        command: str = 'v2 run --projectdir "' + projectPath + '" --environment "PYTHONPATH=$(find' + projectPath + " -not -path '*/\\.*' -not path '*__pycache__*' -type d -printf \":%p\" | sed \"s|" + projectPath + '|/mnt/projectdir/|g")" ' + filePath

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

    @staticmethod
    def __mergeDockerfiles(dockerfiles: List[str]) -> str:
        lines: List[List[str]] = [f.splitlines() for f in dockerfiles]
        for f in lines:
            f.pop()
            f.pop(1)
        return "\n".join(remove_duplicates(flatten(lines)))
