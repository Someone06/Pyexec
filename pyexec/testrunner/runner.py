from abc import ABC, abstractmethod
from logging import Logger
from pathlib import Path
from typing import Optional

from pyexec.testrunner.runresult import RunResult
from pyexec.util.dependencies import Dependencies


class AbstractRunner(ABC):
    def __init__(
        self,
        project_path: Path,
        dependencies: Dependencies,
        logger: Optional[Logger] = None,
    ) -> None:
        assert project_path.exists() and project_path.is_dir()

        self.project_path = project_path
        self.dependencies = dependencies
        self.logger = logger

    @abstractmethod
    def run(self) -> Optional[RunResult]:
        raise NotImplementedError("Implement run()")

    @abstractmethod
    def is_used_in_project(self) -> bool:
        raise NotImplementedError("Implement is_used_in_project()")
