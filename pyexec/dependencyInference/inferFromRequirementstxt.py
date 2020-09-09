import re
from pathlib import Path
from typing import Dict, Optional, Pattern

from pyexec.dependencyInference.inferExtraDependencies import InferExtraDependencies


class InferFromRequirementstxt(InferExtraDependencies):
    _deps_regex: Pattern = re.compile(
        r"""^(?P<name>[\d\w._-]+)(?: ?[<=>]+ ?(?P<version>[\d\w._-]+)(?:, ?<=? ?[\d._-]+)?)?$"""
    )

    def __init__(self, file_path: Path, logfile: Optional[Path] = None) -> None:
        super().__init__(file_path, logfile)
        if file_path.name != "requirements.txt":
            self._logger.error("File {} is not a requirementstxt".format(file_path))
            raise ValueError("Wrong file name: {}".format(file_path.name))

    def infer_dependencies(self) -> Dict[str, Optional[str]]:
        lines = self._file_content.splitlines()
        result: Dict[str, Optional[str]] = dict()
        for line in lines:
            line = line.strip()
            line = line.split("#", 1)[0]
            if line == "":
                continue
            match = self._deps_regex.match(line)
            if match is None:
                self._logger.warning("Did not match line: {}".format(line))
                return dict()
            else:
                name = match.group("name")
                version = match.group("version")
                if name not in result or result[name] is None:
                    result[name] = version
        return result
