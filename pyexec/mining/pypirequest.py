from logging import Logger
from typing import Dict, Optional, cast

import requests


class PyPIRequest:
    """Models the request for a package to the PyPI API."""

    def __init__(self, packageName: str, logger: Optional[Logger]) -> None:
        self.__url = "https://pypi.python.org/pypi/{}/json".format(packageName)
        self.__fields = [
            "author",
            "classifiers",
            "description",
            "home_page",
            "download_url",
            "keywords",
            "license",
            "name",
            "platform",
            "summary",
            "version",
        ]

        self.__packageName = packageName
        self.__logger = logger

    def get_result_from_url(self) -> Optional[Dict[str, str]]:
        """
        Retrieves the result from the PyPI API.

        :return: An optional dictionary containing the relevant fields from PyPI.
        """
        data = self.__get_json()
        if data is not None:
            return self.__parse_fields_from_json(data)
        else:
            return None

    def __get_json(self) -> Optional[Dict[str, str]]:
        try:
            response = requests.get(url=self.__url, stream=True)
        except requests.exceptions.ConnectionError:
            self.__log_error(
                "Connection error when querying PyPI for package {}".format(
                    self.__packageName
                )
            )
            return None

        try:
            return response.json()
        except ValueError:  # Is probably a JSONDecodeError, however the doc for response.json() only promises a ValueError
            self.__log_error(
                "PyPI request for package {} did not return valid json".format(
                    self.__packageName
                )
            )
            return None

    def __parse_fields_from_json(
        self, data: Dict[str, str]
    ) -> Optional[Dict[str, str]]:
        result: Dict[str, str] = dict()
        info: Dict[str, str] = cast(Dict[str, str], data["info"])

        if not isinstance(info, dict):
            self.__log_error(
                "Json for PyPI request for package {} has unexpected format".format(
                    self.__packageName
                )
            )
            return None

        for key, value in info.items():
            if key in self.__fields:
                result[key] = str(value)
        return result

    def __log_error(self, msg: str) -> None:
        if self.__logger is not None:
            self.__logger.error(msg)
