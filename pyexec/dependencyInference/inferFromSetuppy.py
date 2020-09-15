import re
from pathlib import Path
from typing import Dict, Optional, Pattern

from pyexec.dependencyInference.inferExtraDependencies import InferExtraDependencies


class InferFromSetuppy(InferExtraDependencies):
    _setup_call_regex: Pattern = re.compile(r"""^setup[([]""")
    _dependency_regex: Pattern = re.compile(
        r"""(?:['"](P<name>[\d\w]+[\d\w._-]*)(?: ?[<=>]+ ?((P<version>[\d\w._-]+)(?:\.\*)?)(?:,? ?[<>]=? ?[\d\w._-]+)?)?['"], ?)*"""
    )

    def __init__(self, file_path: Path, logfile: Optional[Path] = None) -> None:
        super().__init__(file_path, logfile)
        if file_path.name != "setup.py":
            self._logger.error("File {} is not a requirementstxt".format(file_path))
            raise ValueError("Wrong file name: {}".format(file_path.name))

    def infer_dependencies(self) -> Dict[str, Optional[str]]:
        arguments = self._filter_setup_call()
        if arguments is None:
            return dict()
        parts = arguments.partition("install_requires=")
        if parts[1] == "":
            return dict()
        deps_list = self._match_parentheses(parts[2])
        if deps_list is None:
            return dict()
        deps_list = deps_list.replace("\n", " ")
        matches = self._setup_call_regex.findall(deps_list)
        result: Dict[str, Optional[str]] = dict()
        for match in matches:
            m = self._setup_call_regex.match(match)
            if m is None:
                self._logger.warning("Did not match dependency: {}".format(match))
                return dict()

            name = m.group("name")
            version = m.group("version")
            if name not in result or result[name] is None:
                result[name] = version
        return result

    def _filter_setup_call(self) -> Optional[str]:
        parts = self._file_content.partition("setup(")
        if parts[1] == "":
            self._logger.warning("Did not find setup call in setup.py")
            return None
        rest = parts[2]
        return self._match_parentheses("(" + rest)

    def _match_parentheses(self, to_match: str) -> Optional[str]:
        if len(to_match) == 0:
            return None
        matching = {"{": "}", "(": ")", "[": "]"}
        parentheses = to_match[0]
        if parentheses not in matching:
            return None
        other = matching[parentheses]
        count = 0
        index = -1
        for i, c in enumerate(to_match):
            if c == parentheses:
                count = count + 1
            elif c == other:
                count = count - 1
                if count == 0:
                    index = i
                    break

        if index == -1:
            return None
        else:
            return to_match[1 : (index - 1)]
