from __future__ import annotations

import re
from typing import List

from pyexec.util.list import all_equal, flatten, remove_duplicates


class Dependencies:
    class InvalidFormatException(Exception):
        pass

    __from: str
    __run_commands: List[str]
    __from_regex = re.compile("FROM python:3.\\d")
    __run_regex = re.compile(r'RUN \[("\w+",){2,}"\w+"==\d+.\d+(.\d+)?\]')

    @classmethod
    def from_dockerfile(cls, dockerfile: str) -> Dependencies:
        df = dockerfile.splitlines()

        if len(df) == 0:
            raise Dependencies.InvalidFormatException("dockerfile is empty")
        match = cls.__from_regex.match(df[0])
        if match is None or not match.group() == df[0]:
            raise Dependencies.InvalidFormatException("Invalid FROM clause")

        instance = cls()
        instance.__from = df[0]
        for line in df:
            match = cls.__run_regex.match(line)
            if match is not None and match.group == line:
                instance.__run_commands.append(line)

        return instance

    def to_dockerfile(self) -> str:
        remove_duplicates(self.__run_commands)
        df = self.__from
        for run in self.__run_commands:
            df = df + run
        return df

    @classmethod
    def merge_dependencies(cls, dependencies: List[Dependencies]) -> Dependencies:
        if len(dependencies) == 0:
            raise Dependencies.InvalidFormatException(
                "Argument list must contain at least one element"
            )

        if not all_equal(list(map(lambda d: d.__from, dependencies))):
            raise Dependencies.InvalidFormatException(
                "Dependencies require different Python versions"
            )

        instance = cls()
        instance.__from = dependencies[0].__from
        instance.__run_commands = flatten(
            list(map(lambda d: d.__run_commands, dependencies))
        )
        return instance
