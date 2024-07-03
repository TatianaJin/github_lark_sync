#!/usr/bin/env python3
#
# Copyright 2023 Kasma
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied
# See the License for the specific language governing permissions and
# limitations under the License.

""" User Manager """


from lark_bot.events import BaseGithubEvent, InvolveReason
from typing import List
import json


BOTS = ["coderabbitai[bot]", "coderabbitai"]

DEFAULT_CONFIG = {
    "bot_pr_review": False,  # PR reviewed by bots
    "pr_review": True,  # PR reviewed by others
    InvolveReason.WORKFLOW_RUN_COMPLETE: True,  # workflow run completed for PR
    InvolveReason.ASSIGNEE: True,  # assigned to issue
    InvolveReason.ATED_IN_ISSUE: True,  # @ed in issue body
    InvolveReason.ATED_IN_COMMENT: True,  # @ed in issue comment
    InvolveReason.REVIEWER: True,  # requested to review PR
}


class User:
    """User representing github user and lark user."""

    def __init__(self, github_login_name: str, user_id: str, config_path: str = None):
        self.github_login_name = github_login_name
        self.user_id = user_id
        self._config_path = config_path
        self.config = DEFAULT_CONFIG
        try:
            if config_path is not None:
                with open(self._config_path, "r", encoding="utf-8") as config_f:
                    config_json = json.load(config_f)
                    for k, v in config_json.items():
                        if k in DEFAULT_CONFIG:
                            self.config.update({k: v})
        except FileNotFoundError as e:
            print(f"WARNING: {e}. Using default config")
            self.config = DEFAULT_CONFIG
        except json.JSONDecodeError as e:
            print(f"WARNING reading {config_path}: {e}. Using default config")
            self.config = DEFAULT_CONFIG

    def notify(self, reasons: List[InvolveReason], event: BaseGithubEvent):
        to_notify = False
        if event.get_sender() in BOTS and self.config["bot_pr_review"] is not True:
            return None

        for reason in reasons:
            if reason in self.config and self.config[reason]:
                to_notify = True
                break
        if not to_notify and InvolveReason.CREATOR in reasons:
            if event.event_name == "pull_request_review":
                if event.get_sender() in BOTS:
                    if self.config["bot_pr_review"]:
                        to_notify = True
                elif self.config["pr_review"]:
                    to_notify = True

        if to_notify:
            return self.user_id
        return None


class UserManager:
    """Manage user configs and notify users."""

    def __init__(self, user_config_path: str) -> None:
        self._user_config_path = user_config_path
        self._read_users_from_file()

    def _read_users_from_file(self):
        self._user_map = {}
        with open(self._user_config_path, "r", encoding="utf-8") as user_file:
            for line in user_file:
                line = line.strip()
                splits = line.split(" ", 3)
                self._user_map.update({splits[0]: User(*splits)})

    def notify_user(
        self,
        github_login_name: str,
        reasons: List[InvolveReason],
        event: BaseGithubEvent,
    ) -> str:
        if github_login_name in self._user_map:
            return self._user_map[github_login_name].notify(reasons, event)
        raise RuntimeError(
            f"GitHub user {github_login_name} is not in the config path {self._user_config_path}"
        )
