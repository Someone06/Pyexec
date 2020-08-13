from os import path
from typing import List, Optional

from pydefects.util.list import flatten, remove_duplicates
from pydefects.util.shell import run_command


class InferDockerfile:

    class NoEnviromentFoundExcpetion(Exception):
        pass

    __projectPath: str

    def __init__(self, projectPath: str) -> None:
        if not path.exists(projectPath):
            raise FileNotFoundError(
                "There is no file or directory named " + projectPath
            )
        elif not path.isdir(projectPath):
            raise NotADirectoryError(
                "The project path" + projectPath + " is not a directory"
            )
        else:
            self.__projectPath = projectPath

    def inferDockerfile(self, timeout: Optional[int] = None) -> str:
        files: List[str] = InferDockerfile.__find_python_files(self.__projectPath)
        dockerfiles: List[str] = []
        for f in dockerfiles:
            dockerfiles.append(InferDockerfile.__execute_v2(self.__projectPath, f, timeout))
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
        command: str = 'v2 run --projectdir "' + projectPath + '" --environment "PYTHONPATH=$(find' + projectPath + ' -not -path \'*/\.*\' -type d -printf ":%p" | sed "s|' + projectPath + '/mnt/projectdir/|g")" ' + filePath
        out, _ = run_command(command, timeout)
        out = out.strip()
        if out == "":
            raise InferDockerfile.NoEnviromentFoundExcpetion(
                "V2 is unable to infer a working environment for a package "
                + projectPath
            )
        else:
            return out

    @staticmethod
    def __mergeDockerfiles(dockerfiles: List[str]) -> str:
        lines: List[List[str]] = [f.splitlines() for f in dockerfiles]
        for f in lines:
            f.pop()
        return "\n".join(remove_duplicates(flatten(lines)))
