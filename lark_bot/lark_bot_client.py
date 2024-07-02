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

"""Client to push message to lark bot."""

from lark_bot.events import BaseGithubEvent
import requests
from typing import List

GET_TIMEOUT = 5
POST_TIMEOUT = 5


class LarkBotClient:
    """Cleint to push message to the Lark bot"""

    def __init__(
        self,
        lark_bot_url: str,
        get_time_out: int = GET_TIMEOUT,
        post_time_out: int = POST_TIMEOUT,
    ) -> None:
        self._lark_bot_url = lark_bot_url
        self._get_time_out = get_time_out
        self._post_time_out = post_time_out

    def post_to_lark(self, event: BaseGithubEvent, user_ids: List[str]):
        print(
            f"[LarkBotClient] Post event {event.event_name} {event.notification_title()} to lark"
        )
        data = {
            "msg_type": "interactive",
            "card": {
                "type": "template",
                "data": {
                    # Card builder: https://open.larksuite.com/tool/cardbuilder?templateId=ctp_AAHvgR0HTy2t
                    "template_id": "ctp_AAHvgR0HTy2t",
                    "template_variable": {
                        # the "GitHub:" prefix is needed to meet the keyword requirement
                        "notification_title": f"GitHub: {event.notification_title()}",
                        "mentions": " ".join(
                            [f"<at id={user_id}></at>" for user_id in user_ids]
                        ),
                        "link_title": event.link_title(),
                        "link_url": event.link_url(),
                        "message": event.notification_message(),
                    },
                },
            },
        }
        response = requests.post(self._lark_bot_url, json=data, timeout=POST_TIMEOUT)
        # print(json.dumps(data, indent=2))
        if response.status_code != 200:
            print(
                f"Push {event.event_name} to lark notification: {response.status_code}"
            )
            print(response.text)
        return response.status_code
