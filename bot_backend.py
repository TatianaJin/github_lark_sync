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

"""Start a flask server that processes github webhook events and send lark notifications."""

import sys
import os
import json
from datetime import datetime

from flask import Flask, request, jsonify

from lark_bot.github_webhook_request_handler import (
    GitHubHookIpManager,
)
from lark_bot.github_event_handler import GithubEventHandler

from argparse import ArgumentParser


def get_args():
    parser = ArgumentParser(description="Github To Lark Dev Bot Server")
    parser.add_argument("lark_bot_url", help="Lark bot Url")
    parser.add_argument(
        "-u",
        "--user_config_file",
        default="user_list",
        help="File path to the lark user id list",
    )
    parser.add_argument("-p", "--port", type=int, default=9002, help="Server port")
    parser.add_argument(
        "-l",
        "--log_event",
        default=False,
        action="store_true",
        help="Log event to file, regardless of whether the event is processed successfully. "
        "If False, only log the event on error.",
    )
    parser.add_argument(
        "-e",
        "--event_log_dir",
        default=os.path.join(
            os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "event_log"
        ),
        help="Directory to log events",
    )
    return parser.parse_args()


def log_event(
    event_log_dir: str, event_name: str, event_json: object, timestamp: datetime
):
    dir_name = f"{event_name}-{event_json['action']}"
    os.makedirs(os.path.join(event_log_dir, dir_name), exist_ok=True)
    with open(
        os.path.join(
            event_log_dir,
            dir_name,
            timestamp.strftime("%Y%m%d-%H%M%S.%f") + ".json",
        ),
        "w",
        encoding="utf-8",
    ) as event_output:
        event_output.write(json.dumps(event_json, indent=2))


app = Flask(__name__)


@app.route("/", methods=["POST"])
def handle_webhook():
    # Initialize handlers
    event_handler = app.config["EVENT_HANDLER"]
    ip_manager = app.config["IP_MANAGER"]

    # Verify IP if necessary
    if not ip_manager.check_from_github(request.remote_addr):
        sys.stderr.write(
            f"Got POST from outside github: {request.remote_addr}. Return 403.\n"
        )
        return jsonify({"error": "Unauthorized IP"}), 403

    # Process the event
    now = datetime.now()
    webhook_json = request.json
    event_name = request.headers.get("X-GitHub-Event")
    print(event_name)
    try:
        event_handler.handle_event(event_name, webhook_json)
        if app.config["LOG_EVENT"]:
            log_event(app.config["EVENT_LOG_DIR"], event_name, webhook_json, now)
    except Exception as e:  # pylint: disable=broad-except
        sys.stderr.write(f"Error handling event: {e}\n")
        log_event(app.config["EVENT_LOG_DIR"], event_name, webhook_json, now)
        return jsonify({"status": "error"}), 200

    return jsonify({"status": "success"}), 200


if __name__ == "__main__":
    main_args = get_args()
    app.config["EVENT_HANDLER"] = GithubEventHandler(
        main_args.user_config_file, main_args.lark_bot_url
    )
    app.config["IP_MANAGER"] = GitHubHookIpManager()
    app.config["LOG_EVENT"] = main_args.log_event
    app.config["EVENT_LOG_DIR"] = main_args.event_log_dir

    app.run(host="0.0.0.0", port=main_args.port, debug=False)
