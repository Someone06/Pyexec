from __future__ import annotations

import re
from re import Pattern
from typing import List, Optional

from pyexec.util.list import all_equal, flatten, remove_duplicates


class Dependencies:
    class InvalidFormatException(Exception):
        pass

    __from: str
    __run_commands: List[str] = []
    __copy_commands: List[str] = []
    __cmd_command: Optional[str] = None

    __from_regex: Pattern = re.compile(r"FROM python:3.\d")
    __run_regex: Pattern = re.compile(r'RUN \[("\w+",){2,}"\w+"(==\d+.\d+(.\d+)?)?\]')
    __copy_regex: Pattern = re.compile(r'COPY \["/?(\w+/)*\w+?",  "/?(\w+/)*\w+?"\]')
    __cmd_regex: Pattern = re.compile(r'CMD \["[\w+./]*"(, "[\w+./]*")*\]')

    @classmethod
    def from_dockerfile(cls, dockerfile: str) -> Dependencies:
        df = dockerfile.splitlines()

        if len(df) == 0:
            raise Dependencies.InvalidFormatException("dockerfile is empty")

        if not Dependencies.__full_match(df[0], cls.__from_regex):
            raise Dependencies.InvalidFormatException("Invalid FROM clause")

        instance = cls()
        instance.__from = df[0]
        for line in df:
            if Dependencies.__full_match(line, cls.__run_regex):
                instance.__run_commands.append(line)
            elif Dependencies.__full_match(line, cls.__copy_regex):
                instance.__copy_commands.append(line)
            elif Dependencies.__full_match(line, cls.__cmd_regex):
                instance.__cmd_command = line
        return instance

    def to_dockerfile(self) -> str:
        remove_duplicates(self.__run_commands)
        remove_duplicates(self.__copy_commands)

        df = self.__from
        for run in self.__run_commands:
            df = df + run
        for copy in self.__copy_commands:
            df = df + copy
        if self.__cmd_command is not None:
            df = df + self.__cmd_command
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

        cmds = list(map(lambda d: d.__cmd_command, dependencies))
        if len(cmds) > 1:
            raise Dependencies.InvalidFormatException(
                "More then one Dependency includes a CMD command"
            )

        instance = cls()
        instance.__from = dependencies[0].__from
        instance.__run_commands = flatten(
            list(map(lambda d: d.__run_commands, dependencies))
        )
        instance.__copy_commands = flatten(
            list(map(lambda d: d.__copy_commands, dependencies))
        )
        instance.__cmd_command = cmds[0] if len(cmds) > 0 else None
        return instance

    def add_copy_command(self, clause: str) -> None:
        if not Dependencies.__full_match(clause, self.__copy_regex):
            raise Dependencies.InvalidFormatException(
                "Argument is no valid COPY clause"
            )
        else:
            self.__copy_commands.append(clause)

    def set_cmd_command(self, clause: str, *, replace: bool = True) -> None:
        if not Dependencies.__full_match(clause, self.__cmd_regex):
            raise Dependencies.InvalidFormatException("Argument is no valid CMD clause")
        elif self.__cmd_command is None or replace:
            self.__command = clause

    def add_run_command(self, clause: str) -> None:
        if not Dependencies.__full_match(clause, self.__run_regex):
            raise Dependencies.InvalidFormatException("Argument is no valid RUN clause")
        else:
            self.__run_commands.append(clause)

    @staticmethod
    def __full_match(candidate: str, pattern: Pattern) -> bool:
        match = pattern.match(candidate)
        return match is not None and match.group() == candidate
