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

"""Github webhook event: workflow_run"""


from typing import List
from lark_bot.events.base_github_event import BaseGithubEvent, InvolveReason


class WorkflowRunEvent(BaseGithubEvent):
    """Workflow Run: https://docs.github.com/en/webhooks/webhook-events-and-payloads#workflow_run"""

    def __init__(self, event_name: str, webhook_json: object) -> None:
        super().__init__(event_name=event_name, webhook_json=webhook_json)
        self._involved_users = None

    def involved_users(self) -> List[object]:
        if self._involved_users is not None:
            return self._involved_users

        users = {}

        sender = self._webhook_json["sender"]["login"]
        self._add_to_involved_users(
            users, [sender], InvolveReason.WORKFLOW_RUN_COMPLETE
        )

        self._involved_users = users
        return users

    def notification_title(self) -> str:
        return "Workflow Run Complete"

    def link_url(self) -> str:
        return self._webhook_json["workflow_run"]["html_url"]

    def link_title(self) -> str:
        name = self._webhook_json["workflow_run"]["name"]
        display = self._webhook_json["workflow_run"]["display_title"]
        return f"{name} for {display}"

    def notification_message(self) -> str:
        name = self._webhook_json["workflow_run"]["name"]
        conclusion = self._webhook_json["workflow_run"]["conclusion"]

        return f'Workflow "{name}" ended with status: **{conclusion}**'

    def should_skip_notification(self, combine_related_updates_interval: int) -> bool:
        # events to skip notification
        if self._webhook_json["action"] != "completed":
            return True

        return False
