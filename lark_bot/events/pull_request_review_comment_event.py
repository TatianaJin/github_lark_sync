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

"""Github webhook event: pull_request_review_comment"""

from typing import List, Dict

from lark_bot.events.base_github_event import BaseGithubEvent, InvolveReason


class PullRequestReviewCommentEvent(BaseGithubEvent):
    """PR Review Comment: https://docs.github.com/en/webhooks/webhook-events-and-payloads#pull_request_review_comment"""

    def __init__(self, event_name: str, webhook_json: object) -> None:
        super().__init__(event_name=event_name, webhook_json=webhook_json)
        self._involved_users = None

    def involved_users(self) -> Dict[str, List[str]]:
        if self._involved_users is not None:
            return self._involved_users

        users = {}
        created_by = self._webhook_json["pull_request"]["user"]["login"]
        self._add_to_involved_users(users, [created_by], InvolveReason.CREATOR)

        ated_in_comment = self._find_users_ated(self._webhook_json["comment"]["body"])
        self._add_to_involved_users(
            users, ated_in_comment, InvolveReason.ATED_IN_COMMENT
        )

        self._involved_users = users
        return users

    def notification_title(self) -> str:
        action = self._webhook_json["action"]
        return f"PR Comment {action.capitalize()}"

    def link_title(self) -> str:
        title = self._webhook_json["pull_request"]["title"]
        return f"Comment on {title}"

    def link_url(self) -> str:
        return self._webhook_json["comment"]["html_url"]

    def notification_message(self) -> str:
        sender = self._webhook_json["sender"]["login"]
        action = self._webhook_json["action"]
        body = self._webhook_json["comment"]["body"]
        if action == "deleted":
            return f"{sender} {action} comment."
        return f"{sender} {action} comment.\n\n{body}"

    def should_skip_notification(self, combine_related_updates_interval: int) -> bool:
        action = self._webhook_json["action"]
        # This event is associated with a review, skip duplicate notification
        if (
            self._webhook_json["comment"]["pull_request_review_id"] is not None
            and action == "created"
            and len(self.involved_users()) == 1
        ):
            return True

        return False
