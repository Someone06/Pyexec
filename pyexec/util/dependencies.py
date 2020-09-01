from __future__ import annotations

import re
from re import Pattern
from typing import List, Optional

from pyexec.util.list import all_equal, flatten, remove_duplicates


class Dependencies:
    class InvalidFormatException(Exception):
        pass

    __from_regex: Pattern = re.compile(r"FROM python:3")
    __run_regex: Pattern = re.compile(r"RUN ")
    __copy_regex: Pattern = re.compile(r"COPY ")
    __cmd_regex: Pattern = re.compile(r"CMD ")
    __workdir_regex: Pattern = re.compile(r"WORKDIR ")

    def __init__(self, from_clause: str) -> None:
        if Dependencies.__full_match(from_clause, Dependencies.__from_regex):
            self.__from: str = from_clause
            self.__run_commands: List[str] = []
            self.__copy_commands: List[str] = []
            self.__workdir_command: Optional[str] = None
            self.__cmd_command: Optional[str] = None
        else:
            raise Dependencies.InvalidFormatException("Invalid FROM clause")

    @classmethod
    def from_dockerfile(
        cls, dockerfile: str, drop_non_run_command: bool = True
    ) -> Dependencies:
        df = dockerfile.splitlines()

        if len(df) == 0:
            raise Dependencies.InvalidFormatException("dockerfile is empty")

        instance = Dependencies(df[0])
        for line in df:
            line = line.strip()
            if line == "":
                continue
            if Dependencies.__full_match(line, cls.__from_regex):
                continue
            if Dependencies.__full_match(line, cls.__run_regex):
                instance.__run_commands.append(line)
            elif Dependencies.__full_match(line, cls.__copy_regex):
                if not drop_non_run_command:
                    instance.__copy_commands.append(line)
            elif Dependencies.__full_match(line, cls.__cmd_regex):
                if not drop_non_run_command:
                    instance.__cmd_command = line
            elif Dependencies.__full_match(line, cls.__workdir_regex):
                if not drop_non_run_command:
                    instance.__workdir_command = line
            else:
                raise Dependencies.InvalidFormatException(
                    "Found invalid line in dockerfile: '{}'".format(line)
                )
        return instance

    def to_dockerfile(self) -> str:
        self.__run_commands = remove_duplicates(self.__run_commands)
        self.__copy__commands = remove_duplicates(self.__copy_commands)

        df = self.__from + "\n"
        for run in self.__run_commands:
            df = df + run + "\n"
        for copy in self.__copy_commands:
            df = df + copy + "\n"
        if self.__workdir_command is not None:
            df = df + self.__workdir_command + "\n"
        if self.__cmd_command is not None:
            df = df + self.__cmd_command + "\n"
        return df

    @classmethod
    def merge_dependencies(cls, dependencies: List[Dependencies]) -> Dependencies:
        if len(dependencies) == 0:
            raise Dependencies.InvalidFormatException(
                "Argument list must contain at least one element"
            )

        froms = list(map(lambda d: d.__from, dependencies))
        if not all_equal(froms):
            raise Dependencies.InvalidFormatException(
                "Dependencies require different Python versions"
            )

        work = list(map(lambda d: d.__workdir_command, dependencies))
        if len(work) > 1 and not all_equal(work):
            raise Dependencies.InvalidFormatException(
                "Dockerfiles contain different WORKDIR commands"
            )
        cmds = list(map(lambda d: d.__cmd_command, dependencies))
        if len(cmds) > 1 and not all_equal(cmds):
            raise Dependencies.InvalidFormatException(
                "Dockerfiles contain different CMD commands"
            )

        instance = Dependencies(froms[0])
        instance.__run_commands = flatten(
            list(map(lambda d: d.__run_commands, dependencies))
        )
        instance.__copy_commands = flatten(
            list(map(lambda d: d.__copy_commands, dependencies))
        )
        instance.__workdir_command = work[0] if len(work) > 0 else None
        instance.__cmd_command = cmds[0] if len(cmds) > 0 else None
        return instance

    def add_run_command(self, clause: str) -> None:
        if not Dependencies.__full_match(clause, self.__run_regex):
            raise Dependencies.InvalidFormatException("Argument is no valid RUN clause")
        else:
            self.__run_commands.append(clause)

    def push_run_command(self, clause: str) -> None:
        if not Dependencies.__full_match(clause, self.__run_regex):
            raise Dependencies.InvalidFormatException("Argument is no valid RUN clause")
        else:
            self.__run_commands.insert(0, clause)

    def clear_run_pythonpip(self) -> None:
        self.__run_commands = [
            line for line in self.__run_commands if "python-pip" not in line
        ]

    def add_copy_command(self, clause: str) -> None:
        if not Dependencies.__full_match(clause, self.__copy_regex):
            raise Dependencies.InvalidFormatException(
                "Argument is no valid COPY clause"
            )
        else:
            self.__copy_commands.append(clause)

    def set_workdir_command(self, clause: str, *, replace: bool = True) -> None:
        if not Dependencies.__full_match(clause, self.__workdir_regex):
            raise Dependencies.InvalidFormatException(
                "Argument is no valid WORKDIR clause"
            )
        elif self.__workdir_command is None or replace:
            self.__workdir_command = clause

    def set_cmd_command(self, clause: str, *, replace: bool = True) -> None:
        if not Dependencies.__full_match(clause, self.__cmd_regex):
            raise Dependencies.InvalidFormatException("Argument is no valid CMD clause")
        elif self.__cmd_command is None or replace:
            self.__cmd_command = clause

    def __repr__(self) -> str:
        return self.to_dockerfile()

    @staticmethod
    def __full_match(candidate: str, pattern: Pattern) -> bool:
        return pattern.match(candidate) is not None
