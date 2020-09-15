from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Optional

from pyexec.util.logging import get_logger


class InferExtraDependencies(ABC):
    def __init__(self, file_path: Path, logfile: Optional[Path] = None):
        self._logger = get_logger("Pyexec::ExtraDependencies", logfile)
        if not file_path.exists() or not file_path.is_file():
            self._logger.warning("Path {} does not refer to a file".format(file_path))
            raise ValueError("Not a file {}".format(file_path))
        else:
            with open(file_path, "r") as f:
                self._file_content = f.read()

    @abstractmethod
    def infer_dependencies(self) -> Dict[str, Optional[str]]:
        raise NotImplementedError("Implement infer_dependencies()")

    def _add_dependencies(
        self, deps: Dict[str, Optional[str]], name: str, version: Optional[str]
    ) -> None:
        if name not in deps or deps[name] is None:
            deps[name] = version
