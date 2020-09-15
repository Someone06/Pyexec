from pathlib import Path
from typing import Dict, Optional, Tuple

from pyexec.dependencyInference.inferExtraDependencies import InferExtraDependencies
from pyexec.dependencyInference.inferFromPipfile import InferFromPipfile
from pyexec.dependencyInference.inferFromRequirementstxt import InferFromRequirementstxt
from pyexec.dependencyInference.inferFromSetuppy import InferFromSetuppy
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

    def get_extra_dependencies(self) -> Tuple[Dict[str, Optional[str]], str]:
        result: Dict[str, Optional[str]] = dict()
        pipfile = self._project_path.joinpath("Pipfile")
        if pipfile.exists() and pipfile.is_file():
            inferer: InferExtraDependencies = InferFromPipfile(pipfile, self._logfile)
            result = inferer.infer_dependencies()
            if len(result.items()) > 0:
                return result, "Pipfile"

        setuppy = self._project_path.joinpath("setup.py")
        if setuppy.exists() and setuppy.is_file():
            inferer = InferFromSetuppy(setuppy, self._logfile)
            self._merge_dict(result, inferer.infer_dependencies())
            if len(result.items()) > 0:
                return result, "setup.py"

        requirementstxt = self._project_path.joinpath("requirements.txt")
        if requirementstxt.exists() and requirementstxt.is_file():
            inferer = InferFromRequirementstxt(requirementstxt, self._logfile)
            self._merge_dict(result, inferer.infer_dependencies())
            if len(result.items()) > 0:
                return result, "requirements.txt"
        return dict(), "None"

    @staticmethod
    def _merge_dict(
        base: Dict[str, Optional[str]], addition: Dict[str, Optional[str]]
    ) -> None:
        for name, version in addition.items():
            if name not in base or base[name] is None:
                base[name] = version
