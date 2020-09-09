from pathlib import Path
from typing import Dict, Optional

from pyexec.dependencyInference.inferExtraDependencies import InferExtraDependencies
from pyexec.dependencyInference.inferFromPipfile import InferFromPipfile
from pyexec.dependencyInference.inferFromRequirementstxt import InferFromRequirementstxt
from pyexec.util.logging import get_logger


class ExtraDependencies:
    def __init__(self, project_path: Path, logfile: Optional[Path] = None) -> None:
        self._logfile = logfile
        self._logger = get_logger("Pyexec:ExtraDepnendencies", logfile)
        if not project_path.exists() or not project_path.is_dir():
            self._logger.warning(
                "Path {} does not refer to an existing directory".format(project_path)
            )
            raise ValueError(
                "Path {} does not refer to an existing directory".format(project_path)
            )
        else:
            self._project_path = project_path

    def get_extra_dependencies(self) -> Dict[str, Optional[str]]:
        result: Dict[str, Optional[str]] = dict()
        pipfile = self._project_path.joinpath("Pipfile")
        if pipfile.exists() and pipfile.is_file():
            inferer: InferExtraDependencies = InferFromPipfile(pipfile, self._logfile)
            result = inferer.infer_dependencies()
            if len(result.items()) > 0:
                return result
        requirementstxt = self._project_path.joinpath("requirements.txt")
        if requirementstxt.exists() and requirementstxt.is_file():
            inferer = InferFromRequirementstxt(requirementstxt, self._logfile)
            self._merge_dict(result, inferer.infer_dependencies())
        return result

    @staticmethod
    def _merge_dict(
        base: Dict[str, Optional[str]], addition: Dict[str, Optional[str]]
    ) -> None:
        for name, version in addition.items():
            if name not in base or base[name] is None:
                base[name] = version
