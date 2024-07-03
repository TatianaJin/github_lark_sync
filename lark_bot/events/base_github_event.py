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

"""Interface for github events"""


import re
from typing import List, Dict


class InvolveReason:
    CREATOR = "creator"  # creator of issue/PR
    ATED_IN_ISSUE = "@issue"  # @ed in issue/PR body
    ATED_IN_COMMENT = "@comment"  # @ed in issue/PR comment
    ASSIGNEE = "assignee"  # assigned to issue/PR
    REVIEWER = "reviewer"  # reviewed or requested to review PR
    SENDER = "sender"  # github user that triggered the event
    WORKFLOW_RUN_COMPLETE = "workflow_run_complete"


class BaseGithubEvent:
    """Github event interface for notification construction."""

    def __init__(self, event_name: str, webhook_json: object) -> None:
        if event_name is None:
            raise ValueError("event_name cannot be None")
        if webhook_json is None:
            raise ValueError("webhook_json cannot be None")

        self.event_name = event_name
        self._webhook_json = webhook_json

    def involved_users(self) -> List[object]:
        """
        Interface to get users that are involved in this event.
        Return a list of github users with reason of involvement.

        Return value example:
        {
            "TatianaJin": [ InvolveReason.CREATOR, InvolveReason.SENDER ]
        }
        """
        pass

    def notification_title(self) -> str:
        """Interface to get notification title."""
        pass

    def link_url(self) -> str:
        """Interface to get the event html url."""
        pass

    def link_title(self) -> str:
        """Interface to get the title for the url."""
        pass

    def notification_message(self) -> str:
        """Interface to get the notification message."""
        pass

    def should_skip_notification(self, combine_related_updates_interval: int) -> bool:
        """
        Returns True if should skip notification for this event.
        To avoid sending multiple notifications related to the same user action.
        """
        pass

    def get_sender(self) -> str:
        return self._webhook_json["sender"]["login"]

    def get_action(self) -> str:
        return self._webhook_json["action"]

    @classmethod
    def _find_users_ated(cls, text: str):
        if text is None:
            return []
        users = re.findall("@([a-zA-Z0-9_]+)", text)
        # print(f"users {users} @ed in {text}")
        return users

    @classmethod
    def _add_to_involved_users(
        cls, users: Dict, to_add: List[str], reason: InvolveReason
    ):
        for user in to_add:
            if user in users:
                users[user].append(reason)
            else:
                users.update({user: [reason]})
