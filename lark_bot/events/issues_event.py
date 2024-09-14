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

"""Github webhook event: issues"""

from typing import List, Dict

from lark_bot.events.base_github_event import BaseGithubEvent, InvolveReason
from datetime import datetime


class IssuesEvent(BaseGithubEvent):
    """Issues: https://docs.github.com/en/webhooks/webhook-events-and-payloads#issues"""

    @classmethod
    def get_assignees(cls, issue_or_pr_json: object):
        """Get assignees for issue/PR."""
        assignees = [user["login"] for user in issue_or_pr_json["assignees"]]
        assignee = issue_or_pr_json["assignee"]
        if assignee is not None and assignee["login"] not in assignees:
            assignees.append(assignee["login"])
        return assignees

    def __init__(self, event_name: str, webhook_json: object) -> None:
        super().__init__(event_name=event_name, webhook_json=webhook_json)
        self._involved_users = None

    def involved_users(self) -> Dict[str, List[str]]:
        if self._involved_users is not None:
            return self._involved_users

        action = self._webhook_json["action"]
        users = {}
        if action in ["opened", "reopened", "edited"]:
            assignees = self.get_assignees(self._webhook_json["issue"])
            self._add_to_involved_users(users, assignees, InvolveReason.ASSIGNEE)

            ated_in_issue = self._find_users_ated(self._webhook_json["issue"]["body"])
            self._add_to_involved_users(
                users, ated_in_issue, InvolveReason.ATED_IN_ISSUE
            )
        elif action in ["assigned", "unassigned"]:
            assignee = self._webhook_json["assignee"]["login"]
            if assignee != self._webhook_json["sender"]["login"]:
                self._add_to_involved_users(users, [assignee], InvolveReason.ASSIGNEE)

        # no need to notify the person who triggered this event
        sender = self._webhook_json["sender"]["login"]
        if sender in users:
            users.pop(sender)

        self._involved_users = users
        return users

    def notification_title(self) -> str:
        action = self._webhook_json["action"]
        if action == "opened":
            return "New Issue"
        return f"Issue {action.capitalize()}"

    def link_title(self) -> str:
        return self._webhook_json["issue"]["title"]

    def link_url(self) -> str:
        return self._webhook_json["issue"]["html_url"]

    def notification_message(self) -> str:
        action = self._webhook_json["action"]
        sender = self._webhook_json["sender"]["login"]
        if action in ["opened", "reopened", "edited", "assigned", "unassigned"]:
            return f"{sender} {action} issue."

        print(f"[WARNING] Unhandled issues action {self._webhook_json['action']}")
        return None

    def should_skip_notification(self, combine_related_updates_interval: int) -> bool:
        action = self._webhook_json["action"]

        # events to skip notification
        if action in ["milestoned", "labeled", "closed", "pinned"]:
            return True

        if action == "edited" and len(self.involved_users()) == 0:
            print(
                "[IssuesEvent] skip notification of issue edited when no user is to be notified"
            )
            return True

        # events that are related to issue opened should be skipped to avoid duplicate notification
        create_time = datetime.strptime(
            self._webhook_json["issue"]["created_at"], "%Y-%m-%dT%H:%M:%SZ"
        )
        update_time = datetime.strptime(
            self._webhook_json["issue"]["updated_at"], "%Y-%m-%dT%H:%M:%SZ"
        )
        if action in ["assigned"]:
            # this action is correlated issue "opened", skip it
            if (
                update_time.timestamp() - create_time.timestamp()
                <= combine_related_updates_interval
            ):
                return True

        return False
