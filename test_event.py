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

"""Test event processing"""

from lark_bot.github_event_handler import GithubEventHandler

from argparse import ArgumentParser
import json


def get_args():
    parser = ArgumentParser(description="Github To Lark Dev Bot Server")
    parser.add_argument("lark_bot_url", help="Lark bot Url")
    parser.add_argument("event_name")
    parser.add_argument("event_json_file")
    parser.add_argument(
        "-u",
        "--user_config_file",
        default="user_list",
        help="File path to the lark user id list",
    )
    return parser.parse_args()


if __name__ == "__main__":
    main_args = get_args()
    event_handler = GithubEventHandler(
        main_args.user_config_file, main_args.lark_bot_url
    )

    with open(main_args.event_json_file, "r", encoding="utf-8") as f:
        try:
            j = json.load(f)
        except json.JSONDecodeError as e:
            print(main_args.event_json_file, e)
            exit(1)

        test_event = event_handler.handle_event(main_args.event_name, j)
