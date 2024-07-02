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

"""Github webhook event: pull_request_review"""

from typing import List, Dict

from lark_bot.events.base_github_event import BaseGithubEvent, InvolveReason


class PullRequestReviewEvent(BaseGithubEvent):
    """Pull Request Review: https://docs.github.com/en/webhooks/webhook-events-and-payloads#pull_request_review"""

    def __init__(self, event_name: str, webhook_json: object) -> None:
        super().__init__(event_name=event_name, webhook_json=webhook_json)
        self._involved_users = None

    def involved_users(self) -> Dict[str, List[str]]:
        if self._involved_users is not None:
            return self._involved_users

        users = {}
        action = self._webhook_json["action"]
        pull_request_json = self._webhook_json["pull_request"]

        if action == "submitted":
            created_by = pull_request_json["user"]["login"]
            self._add_to_involved_users(users, [created_by], InvolveReason.CREATOR)

        self._involved_users = users
        return users

    def notification_title(self) -> str:
        review_state = self._webhook_json["review"]["state"]
        return f"PR {review_state.capitalize()} by Review"

    def link_title(self) -> str:
        return self._webhook_json["pull_request"]["title"]

    def link_url(self) -> str:
        return self._webhook_json["review"]["html_url"]

    def notification_message(self) -> str:
        sender = self._webhook_json["sender"]["login"]
        review_state = self._webhook_json["review"]["state"]
        return f"{sender} {review_state}."

    def should_skip_notification(self, combine_related_updates_interval: int) -> bool:
        action = self._webhook_json["action"]

        # events to skip notification
        if action != "submitted":
            return True

        return False
