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

"""Github webhook event: issue_comment"""


from typing import List

from lark_bot.events.base_github_event import BaseGithubEvent, InvolveReason
from lark_bot.events.issues_event import IssuesEvent


class IssueCommentEvent(BaseGithubEvent):
    """Issue comment: https://docs.github.com/en/webhooks/webhook-events-and-payloads#issue_comment"""

    def __init__(self, event_name: str, webhook_json: object) -> None:
        super().__init__(event_name=event_name, webhook_json=webhook_json)
        self._involved_users = None

    def _is_action_to_notify(self, action: str):
        return action in ["created", "edited"]

    def involved_users(self) -> List[object]:
        if self._involved_users is not None:
            return self._involved_users

        action = self._webhook_json["action"]
        if not self._is_action_to_notify(action):
            return []

        users = {}
        assignees = IssuesEvent.get_assignees(self._webhook_json["issue"])
        self._add_to_involved_users(users, assignees, InvolveReason.ASSIGNEE)

        ated_in_issue = self._find_users_ated(self._webhook_json["issue"]["body"])
        self._add_to_involved_users(users, ated_in_issue, InvolveReason.ATED_IN_ISSUE)

        ated_in_comment = self._find_users_ated(self._webhook_json["comment"]["body"])
        self._add_to_involved_users(
            users, ated_in_comment, InvolveReason.ATED_IN_COMMENT
        )

        self._involved_users = users
        return users

    def notification_title(self) -> str:
        action = self._webhook_json["action"]
        if action == "created":
            return "New Comment"
        return f"Issue Comment {action.capitalize()}"

    def link_url(self) -> str:
        return self._webhook_json["comment"]["html_url"]

    def link_title(self) -> str:
        issue_title = self._webhook_json["issue"]["title"]
        return f"Comment on {issue_title}"

    def notification_message(self) -> str:
        action = self._webhook_json["action"]
        sender = self._webhook_json["comment"]["user"]["login"]
        if self._is_action_to_notify(action):
            return f"{sender} {action} a comment."

        return None

    def should_skip_notification(self, combine_related_updates_interval: int) -> bool:
        return not self._is_action_to_notify(self._webhook_json["action"])
