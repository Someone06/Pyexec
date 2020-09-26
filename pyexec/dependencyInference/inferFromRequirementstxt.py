import re
from pathlib import Path
from typing import Dict, Optional, Pattern

from pyexec.dependencyInference.inferExtraDependencies import InferExtraDependencies


class InferFromRequirementstxt(InferExtraDependencies):
    _deps_regex: Pattern = re.compile(
        r"""^["']?(?P<name>[\d\w]+[\d\w._-]+)(?:\[(?:[\d\w._-]+,? ?)+\])?["']?(?:(?: ?~?[<=>]+ ?["']?(?P<version>[\d\w._-]+(?:\.\*)?)(?:,? ?[<>!]=? ?[\d\w._-]+)?)| ?= ?["']?\*["']?)?$"""
    )
    _python_version_regex = re.compile(
        r"""^["']?python_version["']? ?[<=>]+ ?["']?[\d.]+(?:\.\*)?["']?$"""
    )

    def __init__(self, file_path: Path, logfile: Optional[Path] = None) -> None:
        super().__init__(file_path, logfile)
        if file_path.name != "requirements.txt":
            self._logger.error("File {} is not a requirementstxt".format(file_path))
            raise ValueError("Wrong file name: {}".format(file_path.name))

    def infer_dependencies(self) -> Dict[str, Optional[str]]:
        lines = self._file_content.splitlines()
        formatted = list()
        result: Dict[str, Optional[str]] = dict()
        for line in lines:
            line = line.split("#", 1)[0]  # Ignore Comments
            formatted.extend(line.split(";"))
        formatted = [line.strip() for line in formatted]

        for line in formatted:
            if line == "":
                continue
            match = self._deps_regex.match(line)
            if match is None:
                match = self._python_version_regex.match(line)
                if match is None:
                    self._logger.warning("Did not match line: {}".format(line))
                    return dict()
            else:
                name = match.group("name")
                version = match.group("version")
                self._add_dependencies(result, name, version)
        return result
