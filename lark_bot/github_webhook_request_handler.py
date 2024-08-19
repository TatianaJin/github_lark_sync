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
import sys
import requests
import ipaddress
from datetime import datetime

from http.server import BaseHTTPRequestHandler
from lark_bot.github_event_handler import GithubEventHandler


EVENT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "event_log"
)


class GitHubHookIpManager:
    """Get github hook info and verify IP address is github hook"""

    REFRESH_HOOK_SUBNET_INTERVAL = 1  # day

    def __init__(self, refresh_interval_days: int = REFRESH_HOOK_SUBNET_INTERVAL):
        self._last_github_hook_ip_fetch = None
        self._refresh_interval = refresh_interval_days

    @classmethod
    def get_github_webhook_subnets(cls):
        github_api_url = "https://api.github.com/meta"
        rsp = requests.get(github_api_url, timeout=3)
        try:
            hooks = json.loads(rsp.text)["hooks"]
        except KeyError as e:
            sys.stderr.write(json.dumps(json.loads(rsp.text), indent=2))
            sys.stderr.write(f"{e}\n")
            hooks = [
                "192.30.252.0/22",
                "185.199.108.0/22",
                "140.82.112.0/20",
                "143.55.64.0/20",
                "2a0a:a440::/29",
                "2606:50c0::/32",
            ]
        return hooks

    def _refresh_from_github(self):
        now = datetime.now()
        if (
            self._last_github_hook_ip_fetch is None
            or (now - self._last_github_hook_ip_fetch).days > self._refresh_interval
        ):
            if self._last_github_hook_ip_fetch is not None:
                print(
                    "Refresh after",
                    (now - self._last_github_hook_ip_fetch).days,
                    "days",
                )
            self._github_hook_subnets = self.get_github_webhook_subnets()
            self._last_github_hook_ip_fetch = now
            sys.stderr.write(f"Refreshed hook subnets:\n{self._github_hook_subnets}\n")

    def check_from_github(self, client_ip_str: str):
        self._refresh_from_github()
        for subnet in self._github_hook_subnets:
            subnet_ip, subnet_length = subnet.split("/", 1)
            client_subnet = ipaddress.ip_network(
                f"{client_ip_str}/{subnet_length}", strict=False
            ).network_address
            if str(client_subnet) == subnet_ip:
                return True
        return False


class NotifyLarkRequestHandler(BaseHTTPRequestHandler):
    """Handle github webhook requests"""

    def __init__(
        self,
        github_event_handler: GithubEventHandler,
        github_ip_manager: GitHubHookIpManager,
        *args,
        event_log_dir: str = EVENT_DIR,
        always_log_event: bool = False,
        **kwargs,
    ):
        self._github_event_handler = github_event_handler
        self._event_log_dir = event_log_dir
        self._always_log_event = always_log_event
        self._ip_manager = github_ip_manager
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
        if self.path == "/health":  # allow health check
            self.send_response(200)
        else:
            self.send_response(403)
        self.send_header("Content-type", "text/html")
        self.end_headers()

    def do_POST(self):  # pylint: disable=invalid-name, BaseHTTPRequestHandler interface
        if self._ip_manager.check_from_github(self.address_string()) is False:
            sys.stderr.write(
                f"Got POST from outside github: {self.address_string()}. Return 403.\n"
            )
            self.send_response(403)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            return

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
