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

"""Start the server that processes github webhook events and send lark notifications."""

import sys

from lark_bot.github_webhook_request_handler import NotifyLarkRequestHandler
from lark_bot.github_event_handler import GithubEventHandler

from argparse import ArgumentParser
from functools import partial
from http.server import HTTPServer


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
    parser.add_argument("-l", "--log_event", default=False, action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    server_address = ("", 9002)
    main_args = get_args()
    event_handler = GithubEventHandler(
        main_args.user_config_file, main_args.lark_bot_url
    )
    handler = partial(
        NotifyLarkRequestHandler, event_handler, always_log_event=main_args.log_event
    )

    sys.stderr.write("Serve at port 9002\n")
    httpd = HTTPServer(server_address, handler)
    httpd.serve_forever()
