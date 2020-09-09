import re
from pathlib import Path
from typing import Dict, List, Optional, Pattern

from pyexec.dependencyInference.inferExtraDependencies import InferExtraDependencies


class InferFromPipfile(InferExtraDependencies):
    _section_regex: Pattern = re.compile(r"""^\[+(?P<section>[\w\d._-]+)\]+$""")
    _version_regex: Pattern = re.compile(
        r"""^(?P<name>[\w\d._-]+) ?(?:= ?['"]?(?:[<=>]+ ?(?P<version>[/d/w._-]+)| ?\* ?) ?["']?)?$"""
    )

    def __init__(self, file_path: Path, logfile: Optional[Path]) -> None:
        super().__init__(file_path, logfile)
        if file_path.name != "Pipfile":
            self._logger.error("File {} is not a Pipfile".format(file_path))
            raise ValueError("Wrong file name: {}".format(file_path.name))

    def infer_dependencies(self) -> Dict[str, Optional[str]]:
        sections = self._find_sections()
        if sections["packages"] is None:
            return dict()
        deps: List[str] = sections["packages"]
        result: Dict[str, Optional[str]] = dict()
        for line in deps:
            match = self._version_regex.match(line)
            if match is None:
                self._logger.warning("Did not match dependency string: {}".format(line))
                return dict()
            else:
                name = match.group("name")
                version = match.group("version")
                if name not in result or result[name] is None:
                    result[name] = version
        return result

    def _find_sections(self) -> Dict[str, List[str]]:
        sections: Dict[str, List[str]] = dict()
        lines = self._file_content.splitlines()
        section: Optional[str] = None
        for line in lines:
            line = line.strip()
            if line == "":
                continue
            matches = self._section_regex.match(line)
            if matches is not None:
                section = matches.group("section")
            elif section is not None:
                if section not in sections:
                    sections[section] = []
                sections[section].append(line)
            else:
                self._logger.warning("Found line outside of section: {}".format(line))
        return sections
