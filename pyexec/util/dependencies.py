from __future__ import annotations

import re
from re import Pattern
from typing import Dict, List, Optional

from pyexec.util.list import all_equal


class Dependencies:
    class InvalidFormatException(Exception):
        pass

    __from_regex: Pattern = re.compile(r"""^FROM python:(?P<version>[\d.]+)$""")
    __apt_install_regex: Pattern = re.compile(
        r"""^RUN \["apt-get", ?"install", ?(?:"-y", ?)?"(?P<name>[\w\d._-]+) ?(?:= ?(?P<version>[\d\w._+:~-]+))?"\]$"""
    )
    __pip_install_regex: Pattern = re.compile(
        r"""^RUN \["pip", ?"install", ?"(?P<name>[\w\d._-]+) ?(?:== ?(?P<version>[\d\w._+:~-]+))?"\]$"""
    )
    __apt_update_regex: Pattern = re.compile(r"""^RUN \["apt-get", ?"update" ?\]$""")

    def __init__(self, from_clause: str) -> None:
        match = self.__from_regex.match(from_clause)
        if match:
            self.__python_version: str = match.group("version")
            self.__apt_installs: Dict[str, Optional[str]] = dict()
            self.__pip_installs: Dict[str, Optional[str]] = dict()
            self.__copy_command: Optional[str] = None
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
            if line.startswith("FROM"):
                continue
            elif instance.__parse_run_command(line):
                continue
            elif line.startswith("COPY"):
                if not drop_non_run_command:
                    instance.__copy_command = line
            elif line.startswith("CMD"):
                if not drop_non_run_command:
                    instance.__cmd_command = line
            elif line.startswith("WORKDIR"):
                if not drop_non_run_command:
                    instance.__workdir_command = line
            else:
                raise Dependencies.InvalidFormatException(
                    "Found invalid line in dockerfile: '{}'".format(line)
                )
        return instance

    def __parse_run_command(self, cmd: str) -> bool:
        match = self.__pip_install_regex.match(cmd)
        if match is not None:
            d = match.groupdict()
            self.add_pip_dependency(d["name"], d["version"])
            return True
        match = self.__apt_install_regex.match(cmd)
        if match is not None:
            d = match.groupdict()
            self.add_apt_dependency(d["name"], d["version"])
            return True
        return self.__apt_update_regex.match(cmd) is not None

    def to_dockerfile(self) -> str:
        df = "FROM python:{}\n".format(self.__python_version)
        df = df + r"""RUN ["apt-get", "update"]""" + "\n"
        df = (
            df
            + r"""RUN ["python", "-m", "pip", "install", "--upgrade", "pip"]"""
            + "\n"
        )

        self.__apt_installs.pop("python-pip", None)  # Do not attempt to install pip
        for name, version in self.__apt_installs.items():
            if version is not None:
                df = (
                    df
                    + r"""RUN ["apt-get","install","-y","{}={}"]""".format(
                        name, version
                    )
                    + "\n"
                )
            else:
                df = df + r"""RUN ["apt-get","install","-y","{}"]""".format(name) + "\n"

        for name, version in self.__pip_installs.items():
            if version is not None:
                df = (
                    df
                    + r"""RUN ["pip","install","{}=={}"]""".format(name, version)
                    + "\n"
                )
            else:
                df = df + r"""RUN ["pip","install","{}"]""".format(name) + "\n"

        if self.__copy_command is not None:
            df = df + self.__copy_command + "\n"

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

        froms = list(map(lambda d: d.__python_version, dependencies))
        if not all_equal(froms):
            raise Dependencies.InvalidFormatException(
                "Dependencies require different Python versions"
            )

        copy = list(map(lambda d: d.__copy_command, dependencies))
        if len(copy) > 1 and not all_equal(copy):
            raise Dependencies.InvalidFormatException(
                "Dockerfiles contain different COPY commands"
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

        instance = Dependencies("FROM python:{}".format(froms[0]))
        for dep in dependencies:
            cls.__merge_dict(instance.__apt_installs, dep.__apt_installs)
            cls.__merge_dict(instance.__pip_installs, dep.__pip_installs)

        instance.__copy_command = copy[0] if len(copy) > 0 else None
        instance.__workdir_command = work[0] if len(work) > 0 else None
        instance.__cmd_command = cmds[0] if len(cmds) > 0 else None
        return instance

    def add_run_command(self, cmd: str) -> None:
        if not self.__parse_run_command(cmd):
            raise Dependencies.InvalidFormatException("Argument is no valid RUN clause")

    def set_copy_command(self, cmd: str, *, replace: bool = True) -> None:
        if not cmd.startswith("COPY"):
            raise Dependencies.InvalidFormatException(
                "Argument is no valid COPY clause"
            )
        elif self.__copy_command is None or replace:
            self.__copy_command = cmd

    def set_workdir_command(self, cmd: str, *, replace: bool = True) -> None:
        if not cmd.startswith("WORKDIR"):
            raise Dependencies.InvalidFormatException(
                "Argument is no valid WORKDIR clause"
            )
        elif self.__workdir_command is None or replace:
            self.__workdir_command = cmd

    def set_cmd_command(self, cmd: str, *, replace: bool = True) -> None:
        if not cmd.startswith("CMD"):
            raise Dependencies.InvalidFormatException("Argument is no valid CMD clause")
        elif self.__cmd_command is None or replace:
            self.__cmd_command = cmd

    def add_pip_dependency(self, name: str, version: Optional[str] = None) -> None:
        if name not in self.__pip_installs or self.__pip_installs[name] is None:
            self.__pip_installs[name] = version

    def add_apt_dependency(self, name: str, version: Optional[str] = None) -> None:
        if name not in self.__apt_installs or self.__apt_installs[name] is None:
            self.__apt_installs[name] = version

    def pip_dependency_count(self) -> int:
        return len(self.__pip_installs)

    def apt_dependency_count(self) -> int:
        return len(self.__apt_installs)

    def __repr__(self) -> str:
        return self.to_dockerfile()

    @staticmethod
    def __merge_dict(
        base: Dict[str, Optional[str]], addition: Dict[str, Optional[str]]
    ) -> None:
        for name, version in addition.items():
            if name not in base or base[name] is None:
                base[name] = version
