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

"""Github Event Handler"""

from lark_bot import events
from lark_bot.user_manager import UserManager, BOTS
from lark_bot.lark_bot_client import LarkBotClient


COMBINE_RELATED_UPDATES_TIME = 2  # seconds


class GithubEventHandler:
    """Handles github webhook events. See GithubEventHandler.handle_event."""

    def __init__(self, user_config_path: str, lark_bot_url: str) -> None:
        self._user_manager = UserManager(user_config_path)
        self._lark_bot_client = LarkBotClient(lark_bot_url)
        self._debug = True

    def _post_to_lark(self, event: events.BaseGithubEvent):
        user_ids = []
        for github_user, reasons in event.involved_users().items():
            if github_user not in BOTS:
                try:
                    lark_user = self._user_manager.notify_user(
                        github_login_name=github_user, reasons=reasons, event=event
                    )
                except RuntimeError as e:
                    if self._debug:
                        print("UserManager.notify_user", e)
                    lark_user = None
                if lark_user is not None:
                    user_ids.append(lark_user)

        if len(user_ids) == 0 and event.get_sender() in BOTS:
            if self._debug:
                print(
                    "Skip post_to_lark as the sender is a bot and no users are to be notified"
                )
            return

        self._lark_bot_client.post_to_lark(event, user_ids)

    def handle_event(
        self, event_name: str, webhook_json: object
    ) -> events.BaseGithubEvent:
        event = None
        if event_name == "issues":
            event = events.IssuesEvent(event_name, webhook_json)
        elif event_name == "issue_comment":
            event = events.IssueCommentEvent(event_name, webhook_json)
        elif event_name == "pull_request":
            event = events.PullRequestEvent(event_name, webhook_json)
        elif event_name == "pull_request_review":
            event = events.PullRequestReviewEvent(event_name, webhook_json)
        elif event_name == "pull_request_review_comment":
            event = events.PullRequestReviewCommentEvent(event_name, webhook_json)
        elif event_name == "workflow_run":
            event = events.WorkflowRunEvent(event_name, webhook_json)
        elif event_name in ["check_run", "pull_request_review_thread"]:
            if self._debug:
                print(f"Discard event {event_name}")
            return None  # now we discard this event
        else:
            raise NotImplementedError(f"Unhandled event {event_name}")

        if event.should_skip_notification(COMBINE_RELATED_UPDATES_TIME):
            if self._debug:
                print(
                    f"[GithubEventHandler::handle_event] skip notification of {event.event_name}: {event.get_action()}"
                )
            return event
        if event.notification_message() is None:
            if self._debug:
                raise RuntimeError(
                    f"Event {event_name} message is None. {webhook_json}"
                )
            return event

        self._post_to_lark(event=event)
        return event
