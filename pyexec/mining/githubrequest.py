import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from github.MainClass import Github
from github.Rate import Rate
from github.RateLimit import RateLimit
from github.Repository import Repository

from pyexec.util.logging import get_logger


@dataclass
class GitHubInfo:
    python_version: str
    created_at: datetime
    last_updated: datetime


class GitHubRequest:
    """
    A wrapper around the GitHub API that gives us all information we need.

    See the GitHub API documentation and the documentation of the PyGithub package for
    details on the values.
    """

    def __init__(
        self,
        access_token: str,
        repo_user: str,
        repo_name: str,
        logfile: Optional[Path] = None,
    ) -> None:
        self.__logger = get_logger("Pyexec:GitHubRequest", logfile)
        self.__github = Github(login_or_token=access_token, user_agent="pyexec")
        self.wait_if_necessary()
        self.__repo: Repository = self.__github.get_repo(
            "{}/{}".format(repo_user, repo_name)
        )

    def get_github_info(self) -> GitHubInfo:
        return GitHubInfo(
            python_version=self.get_language(),
            created_at=self.get_created_at(),
            last_updated=self.get_updated_at(),
        )

    def wait_if_necessary(self) -> None:
        """Wait for the GitHub API to accept new requests, if necessary."""

        def wait(seconds: int) -> None:
            self.__logger.info("Wait for %d seconds for GitHub API", seconds)
            time.sleep(seconds)
            self.__logger.info("Done waiting")

        rate_limit: RateLimit = self.__github.get_rate_limit()
        rate: Rate = rate_limit.core

        if rate.remaining <= 10:
            reset_time: datetime = rate.reset
            wait_time = reset_time - datetime.utcnow()
            wait(int(wait_time.total_seconds()) + 10)

    def get_issues(self) -> Dict[int, Dict[str, Any]]:
        """
        Retrieves all issues from a repository.

        This can be a long running process!

        :return: A mapping from issue number to issue properties.
        """
        issues: Dict[int, Dict[str, Any]] = dict()
        for issue in self.__repo.get_issues(state="all"):
            self.wait_if_necessary()
            number = issue.number
            comments = []
            for comment in issue.get_comments():
                self.wait_if_necessary()
                comments.append(comment)
            issues[number] = {"issue": issue, "comments": comments}
        return issues

    def get_issue(self, number: int) -> Dict[str, Any]:
        """
        Retrieves one issue from a repository.

        This can be a long running process!

        :param number: The issue number on GitHub.
        :return: A mapping on the issue properties.
        """
        self.wait_if_necessary()
        issue = self.__repo.get_issue(number)
        comments = []
        for comment in issue.get_comments():
            self.wait_if_necessary()
            comments.append(comment)
        return {"issue": issue, "comments": comments}

    def get_forks_count(self) -> int:
        """
        Returns the number of forks.

        :return: The number of forks.
        """
        self.wait_if_necessary()
        return int(self.__repo.forks_count)

    def get_stargazers_count(self) -> int:
        """
        Returns the number of stargazers.
        :return: The number of stargazers.
        """
        self.wait_if_necessary()
        return int(self.__repo.stargazers_count)

    def get_subscribers_count(self) -> int:
        """
        Returns the number of subscribers.

        :return: The number of subscribers.
        """
        self.wait_if_necessary()
        return int(self.__repo.subscribers_count)

    def get_watchers_count(self) -> int:
        """
        Returns the number of repository watchers.

        :return: The number of watchers.
        """
        self.wait_if_necessary()
        return int(self.__repo.watchers_count)

    def get_language(self) -> str:
        """
        Returns the main language of the repository.

        :return: The main language of the repository.
        """
        self.wait_if_necessary()
        return self.__repo.language

    def get_created_at(self) -> datetime:
        """
        Returns the time stamp the repository was created at.

        :return: The time stamp the repository was created at.
        """
        self.wait_if_necessary()
        return self.__repo.created_at

        """
    def get_last_modified(self) -> datetime:
        Returns the time stamp the repository was last modified at.

        :return: The time stamp the repository was last modified at.
        self.wait_if_necessary()
        if self.__
        return datetime.strptime(self.__repo.last_modified, "%a, %d %b %Y %H:%M:%S %Z")
        """

    def get_open_issues_count(self) -> int:
        """
        Returns the current number of open issues.

        :return: The current number of open issues.
        """
        self.wait_if_necessary()
        return int(self.__repo.open_issues_count)

    def get_updated_at(self) -> datetime:
        """
        Returns the time stamp the repository was last updated at.

        :return: Returns the time stamp the repository was last updated at.
        """
        self.wait_if_necessary()
        return self.__repo.updated_at
