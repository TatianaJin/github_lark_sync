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

"""Github webhook event: pull_request"""

from typing import List, Dict

from lark_bot.events.base_github_event import BaseGithubEvent, InvolveReason
from datetime import datetime


class PullRequestEvent(BaseGithubEvent):
    """Pull Request: https://docs.github.com/en/webhooks/webhook-events-and-payloads#pull_request"""

    def __init__(self, event_name: str, webhook_json: object) -> None:
        super().__init__(event_name=event_name, webhook_json=webhook_json)
        self._involved_users = None

    @classmethod
    def _get_reviewers(cls, pull_request_json: object):
        """Get reviewers from pr reviewers and pr body @users"""
        reviewers = [user["login"] for user in pull_request_json["requested_reviewers"]]
        body = pull_request_json["body"]
        if body is not None:
            reviewers.extend(cls._find_users_ated(body))
        return reviewers

    def involved_users(self) -> Dict[str, List[str]]:
        if self._involved_users is not None:
            return self._involved_users

        users = {}
        action = self._webhook_json["action"]
        pull_request_json = self._webhook_json["pull_request"]

        if action in ["opened", "reopened", "edited", "synchronize"]:
            reviewers = self._get_reviewers(pull_request_json)
            self._add_to_involved_users(users, reviewers, InvolveReason.REVIEWER)
        elif action == "review_requested":
            reviewer = self._webhook_json["requested_reviewer"]["login"]
            self._add_to_involved_users(users, [reviewer], InvolveReason.REVIEWER)

        self._involved_users = users
        return users

    def notification_title(self) -> str:
        action = self._webhook_json["action"]
        if action == "opened":
            return "New PR"
        if action == "review_requested":
            return "Review Requested"
        return f"PR {action.capitalize()}"

    def link_title(self) -> str:
        return self._webhook_json["pull_request"]["title"]

    def link_url(self) -> str:
        return self._webhook_json["pull_request"]["html_url"]

    def notification_message(self) -> str:
        action = self._webhook_json["action"]
        sender = self._webhook_json["sender"]["login"]
        pull_request_json = self._webhook_json["pull_request"]
        body = pull_request_json["body"]
        if action in ["opened", "edited"]:
            return f"{sender} {action} PR.\n\n**Content**\n{body}"
        elif action in ["synchronize", "reopened"]:
            return f"{sender} {action} PR."
        elif action == "review_requested":
            return f"{sender} requested review."

        print(f"[WARNING] Unhandled pull_request action {self._webhook_json['action']}")
        return None

    def should_skip_notification(self, combine_related_updates_interval: int) -> bool:
        if len(self.involved_users()) == 0:
            return True

        action = self._webhook_json["action"]
        # events to skip notification
        if action in ["assigned", "labeled"]:
            return True

        # events that are related to pull_request "opened" should be skipped to avoid duplicate notification
        create_time = datetime.strptime(
            self._webhook_json["pull_request"]["created_at"], "%Y-%m-%dT%H:%M:%SZ"
        )
        update_time = datetime.strptime(
            self._webhook_json["pull_request"]["updated_at"], "%Y-%m-%dT%H:%M:%SZ"
        )
        if action in ["review_requested"]:
            if (
                update_time.timestamp() - create_time.timestamp()
                <= combine_related_updates_interval
            ):
                return True

        return False
