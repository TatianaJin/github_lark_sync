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

""" BaseHTTPRequestHandler implementation for handling github webhook events. """

import json
import os
from datetime import datetime

from http.server import BaseHTTPRequestHandler
from lark_bot.github_event_handler import GithubEventHandler


EVENT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "event_log"
)


class NotifyLarkRequestHandler(BaseHTTPRequestHandler):
    """Handle github webhook requests"""

    def __init__(
        self,
        github_event_handler: GithubEventHandler,
        *args,
        event_log_dir: str = EVENT_DIR,
        always_log_event: bool = False,
        **kwargs,
    ):
        self._github_event_handler = github_event_handler
        self._event_log_dir = event_log_dir
        self._always_log_event = always_log_event
        if len(args) > 0:
            super().__init__(*args, **kwargs)

    def _log_event(self, event_name: str, webhook_json: object, timestamp: datetime):
        dir_name = f"{event_name}-{webhook_json['action']}"
        os.makedirs(os.path.join(self._event_log_dir, dir_name), exist_ok=True)
        with open(
            os.path.join(
                self._event_log_dir,
                dir_name,
                timestamp.strftime("%Y%m%d-%H%M%S.%f") + ".json",
            ),
            "w",
            encoding="utf-8",
        ) as event_output:
            event_output.write(json.dumps(webhook_json, indent=2))

    def do_GET(self):  # pylint: disable=invalid-name, BaseHTTPRequestHandler interface
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

    def do_POST(self):  # pylint: disable=invalid-name, BaseHTTPRequestHandler interface
        now = datetime.now()
        length = int(self.headers["Content-Length"])
        event = self.headers["X-GitHub-Event"]
        webhook_json_str = self.rfile.read(length).decode("utf-8")
        webhook_json = json.loads(webhook_json_str)
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        try:
            self._github_event_handler.handle_event(event, webhook_json)
            if self._always_log_event:
                self._log_event(event, webhook_json, now)
        except Exception:  # pylint: disable=broad-exception-caught
            self._log_event(event, webhook_json, now)
