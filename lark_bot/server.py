#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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

""" Obsolete. Server for handling github hooks and sending notification to lark bot. """

import json
import os
import re
import time
from argparse import ArgumentParser
from functools import partial
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import List, Tuple

import requests

bots = ["coderabbitai[bot]"]

GET_TIMEOUT = 5
POST_TIMEOUT = 5
EVENT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "event_log"
)


def _get_args():
    parser = ArgumentParser(description="Github To Lark Dev Bot Server")
    parser.add_argument("lark_bot_url", help="Lark bot Url")
    parser.add_argument("lark_user_id_list", help="File path to the lark user id list")
    parser.add_argument(
        "-m",
        "--mock_event",
        nargs=2,
        help="Event name and file path to the mock event json",
    )
    return parser.parse_args()


class NotifyLarkRequestHandler(BaseHTTPRequestHandler):
    """Handle github webhook requests and notify in a lark group"""

    def __init__(self, server_args, *args, **kwargs):
        self._server_args = server_args
        self._read_users_from_file()
        if len(args) > 0:
            super().__init__(*args, **kwargs)

    def _read_users_from_file(self):
        self._user_map = {}
        with open(
            self._server_args.lark_user_id_list, "r", encoding="utf-8"
        ) as user_file:
            for line in user_file:
                line = line.strip()
                github_login, lark_uid = line.rsplit(" ", 1)
                self._user_map.update({github_login: lark_uid})

    def do_GET(self):  # pylint: disable=invalid-name, BaseHTTPRequestHandler interface
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

    def do_POST(self):  # pylint: disable=invalid-name, BaseHTTPRequestHandler interface
        length = int(self.headers["Content-Length"])
        event = self.headers["X-GitHub-Event"]
        webhook_json_str = self.rfile.read(length).decode("utf-8")
        webhook_json = json.loads(webhook_json_str)
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        # FIXME
        # try:
        #     self.handle_event(event, webhook_json)
        # except Exception as e:  # pylint: disable=broad-exception-caught
        if True:
            print(self.headers)
            dir_name = f"{event}_{webhook_json['action']}"
            os.makedirs(os.path.join(EVENT_DIR, dir_name), exist_ok=True)
            with open(
                os.path.join(EVENT_DIR, dir_name, str(time.time())),
                "w",
                encoding="utf-8",
            ) as event_output:
                event_output.write(f"{time.time()}")
                # event_output.write(e)
                event_output.write("\n")
                event_output.write(json.dumps(webhook_json, indent=2))

    @classmethod
    def github_api(cls, url, token_file="pat.github"):
        with open(token_file, "r", encoding="utf-8") as token_f:
            token = token_f.readlines()
            assert len(token) == 1, f"Expect one-line token, got {len(token)}"
            token = token[0].strip()
        response = requests.get(
            url, headers={"Authorization": f"Bearer {token}"}, timeout=GET_TIMEOUT
        )
        return response.status_code, response.text

    def handle_event(self, event, webhook_json):
        # send event to lark bot
        github_users = None
        if event == "issues":
            github_users, notification_json = self._handle_issues(webhook_json)
        elif event == "issue_comment" and webhook_json["sender"]["login"] not in bots:
            github_users, notification_json = self._handle_issue_comment(webhook_json)
        elif event == "pull_request":
            github_users, notification_json = self._handle_pull_request(webhook_json)
        elif (
            event == "pull_request_review"
            and webhook_json["sender"]["login"] not in bots
        ):
            github_users, notification_json = self._handle_pr_review(webhook_json)
        elif event == "check_run":
            return  # github_users, notification_json = self._handle_check_run(webhook_json)
        elif event == "workflow_run":
            github_users, notification_json = self._handle_workflow_run(webhook_json)
        else:
            print(f"Unhandled {event}".ljust(60, "!"))
            return

        if notification_json is None:
            assert github_users is None
            return

        at_users = None
        if github_users is not None and len(github_users) > 0:
            at_users = self._github_users_to_lark_uid(github_users)
        self._post_to_lark(
            self._server_args.lark_bot_url, event, notification_json, at_users
        )

    def _github_users_to_lark_uid(
        self, user_login_names: List[str]
    ) -> List[Tuple[str, str]]:
        user_login_names = list(set(user_login_names))
        reread_users = False
        uids = []
        for name in user_login_names:
            print(f"name {name}")
            if name not in self._user_map and not reread_users:
                self._read_users_from_file()
                reread_users = True
            uids.append(
                (name, self._user_map[name] if name in self._user_map else None)
            )
        return uids

    @classmethod
    def _get_assignees(cls, issue_or_pr_json):
        assignees = [user["login"] for user in issue_or_pr_json["assignees"]]
        assignee = issue_or_pr_json["assignee"]
        if assignee is not None and assignee["login"] not in assignees:
            assignees.append(assignee["login"])
        return assignees

    @classmethod
    def _find_users_ated(cls, text: str):
        if text is None:
            return []
        users = re.findall("@([a-zA-Z0-9_]+)", text)
        print(f"users {users} @ed in {text}")
        return users

    @classmethod
    def _get_reviewers(cls, pull_request_json):
        """Get reviewers from pr reviewers and pr body @users"""
        reviewers = [user["login"] for user in pull_request_json["requested_reviewers"]]
        body = pull_request_json["body"]
        if body is not None:
            reviewers.extend(cls._find_users_ated(body))
        return reviewers

    @classmethod
    def _handle_pull_request(cls, webhook_json):
        pull_request_json = webhook_json["pull_request"]
        pr_url = pull_request_json["html_url"]
        title = pull_request_json["title"]
        body = pull_request_json["body"]
        sender = webhook_json["sender"]["login"]
        reviewers = cls._get_reviewers(pull_request_json)
        label_strs = [f'[{label["name"]}]' for label in pull_request_json["labels"]]
        if len(label_strs) > 0:
            label_str = f"{''.join(label_strs)} "
        else:
            label_str = ""

        if webhook_json["action"] in ["opened", "reopened"]:
            lark_notification = [  # each element is a paragraph
                [
                    {"tag": "text", "text": label_str},
                    {"tag": "a", "text": title, "href": pr_url},
                    {"tag": "text", "text": f" {webhook_json['action']} by {sender}"},
                ]
            ]
            if body is not None:
                if len(body) > 100:
                    body = body[:100] + "..."
                lark_notification.append([{"tag": "text", "text": f"\n{body}"}])

            return reviewers, lark_notification

        if webhook_json["action"] in ["editted", "synchronize"] and len(reviewers) > 0:
            lark_notification = [  # each element is a paragraph
                [
                    {"tag": "text", "text": label_str},
                    {"tag": "a", "text": title, "href": pr_url},
                    {"tag": "text", "text": f" {webhook_json['action']} by {sender}"},
                ]
            ]
            if body is not None:
                if len(body) > 100:
                    body = body[:100] + "..."
                lark_notification.append([{"tag": "text", "text": f"\n{body}"}])
            return reviewers, lark_notification

        print(f"Unhandled pull_request action {webhook_json['action']}")
        return None, None

    @classmethod
    def _handle_pr_review(cls, webhook_json):
        if webhook_json["action"] == "submitted":
            pull_request_json = webhook_json["pull_request"]
            title = pull_request_json["title"]
            review_json = webhook_json["review"]
            review_url = pull_request_json["html_url"]
            reviewer = review_json["user"]["login"]
            review_state = review_json["state"]
            body = review_json["body"]
            if body is None or len(body) == 0:
                body_str = ""
            else:
                body_str = f"\n{body}"

            pr_owner = pull_request_json["user"]["login"]
            at_github_users = [pr_owner]
            at_github_users.extend(cls._find_users_ated(body))
            lark_notification = [  # each element is a paragraph
                [
                    {"tag": "text", "text": f"{reviewer} reviewed "},
                    {
                        "tag": "a",
                        "text": f"{title}",
                        "href": review_url,
                    },
                    {
                        "tag": "text",
                        "text": f": {review_state}",
                    },
                ],
                [{"tag": "text", "text": body_str}],
            ]
            return at_github_users, lark_notification
        return None, None

    @classmethod
    def _handle_issue_comment(cls, webhook_json):
        at_github_users = cls._get_assignees(webhook_json["issue"])
        body = webhook_json["comment"]["body"]
        if body is None:
            return None, None
        # find @user in body
        at_github_users.extend(cls._find_users_ated(body))

        title = webhook_json["issue"]["title"]
        comment_url = webhook_json["comment"]["html_url"]
        if len(at_github_users) == 0:
            # @issue creator if no assignee
            at_github_users = [webhook_json["issue"]["user"]["login"]]
        if webhook_json["action"] in ["created", "edited"]:
            lark_notification = [  # each element is a paragraph
                [
                    {
                        "tag": "a",
                        "text": f"Comment in [{title}]",
                        "href": comment_url,
                    },
                    {
                        "tag": "text",
                        "text": (
                            f" edited:\n{body}"
                            if webhook_json["action"] == "edited"
                            else f":\n{body}"
                        ),
                    },
                ]
            ]
            return at_github_users, lark_notification

        print(f"Unhandled issue_comment action {webhook_json['action']}")
        return None, None

    @classmethod
    def _handle_issues(cls, webhook_json):
        label_names = cls._get_labels_from_url(webhook_json["issue"]["labels_url"])
        label_strs = [f"[{name}]" for name in label_names]
        if len(label_strs) > 0:
            label_str = f"{''.join(label_strs)} "
        else:
            label_str = ""
        created_by = webhook_json["issue"]["user"]["login"]
        assignees = cls._get_assignees(webhook_json["issue"])

        issue_url = webhook_json["issue"]["html_url"]
        title = webhook_json["issue"]["title"]
        body = webhook_json["issue"]["body"]
        lark_notification = None
        if webhook_json["action"] in ["opened", "reopened"]:
            lark_notification = [  # each element is a paragraph
                [
                    {"tag": "text", "text": label_str},
                    {"tag": "a", "text": title, "href": issue_url},
                    {"tag": "text", "text": f" opened by {created_by}"},
                ]
            ]
            if body is not None:
                lark_notification.append([{"tag": "text", "text": f"\n{body}"}])
            return assignees, lark_notification

        if webhook_json["action"] == "assigned":
            lark_notification = [
                [
                    {"tag": "text", "text": "Assigned to "},
                    {"tag": "text", "text": label_str},
                    {"tag": "a", "text": title, "href": issue_url},
                ]
            ]
            return assignees, lark_notification

        print(f"Unhandled issues action {webhook_json['action']}")
        return None, lark_notification

    @classmethod
    def _handle_check_run(cls, webhook_json):
        check_run_json = webhook_json["check_run"]
        return cls._handle_run(webhook_json, check_run_json)

    @classmethod
    def _handle_workflow_run(cls, webhook_json):
        check_run_json = webhook_json["workflow_run"]
        return cls._handle_run(webhook_json, check_run_json)

    @classmethod
    def _handle_run(cls, webhook_json, run_json):
        if webhook_json["action"] == "completed":
            prs: List[dict] = run_json["pull_requests"]
            prs = [str(pr["number"]) for pr in prs]
            if len(prs) == 0 or run_json["conclusion"] == "skipped":
                return None, None

            run_name = run_json["name"]
            run_url = run_json["html_url"]
            sender = webhook_json["sender"]["login"]
            lark_notification = [  # each element is a paragraph
                [
                    {
                        "tag": "text",
                        "text": f"Check run completed - {run_json['conclusion']}: ",
                    },
                    {"tag": "a", "text": run_name, "href": run_url},
                    {"tag": "text", "text": f"\nPR: {','.join(prs)}"},
                ]
            ]
            return [sender], lark_notification

        return None, None

    @classmethod
    def _get_labels_from_url(cls, url: str):
        if url.endswith("{/name}"):
            url = url[0 : -len("{/name}")]
        response = requests.get(url, timeout=GET_TIMEOUT)
        if response.status_code != 200:
            return []
        labels_json = json.loads(response.text)
        label_names = [label["name"] for label in labels_json]
        return label_names

    @classmethod
    def _get_user_ids(cls, email, token):
        lark_api = "https://open.larksuite.com/open-apis/contact/v3/users/batch_get_id?user_id_type=open_id"
        data = {"emails": [email]}
        response = requests.post(
            lark_api,
            json=data,
            headers={"Authorization": f"Bearer {token}"},
            timeout=POST_TIMEOUT,
        )
        print(response.content)

    @classmethod
    def _post_to_lark(
        cls,
        lark_bot_url,
        event_name,
        notification,
        at_users: List[Tuple[str, str]] = None,
    ) -> int:
        if notification is None:
            print(f"Warning: Empty notification for {event_name}")
            return 1

        message_contents = []
        if at_users is not None:
            message_contents = [
                [
                    (
                        {"tag": "text", "text": f"@{user_id[0]}"}
                        if user_id[1] is None
                        else {"tag": "at", "user_id": user_id[1]}
                    )
                    for user_id in at_users
                ]
            ]
        message_contents.extend(notification)

        # post to lark
        data = {
            "msg_type": "post",
            "content": {
                "post": {
                    "zh_cn": {
                        "title": f"GitHub Dev Notification: {event_name}",
                        "content": message_contents,
                    }
                }
            },
        }
        response = requests.post(lark_bot_url, json=data, timeout=POST_TIMEOUT)
        print(f"Push {event_name} to lark notification: {response.status_code}")
        if response.status_code != 200:
            print("".ljust(80, ">"))
            print(json.dumps(data, indent=2))
            print("".ljust(80, "<"))
            return response.status_code
        return 0


if __name__ == "__main__":
    server_address = ("", 9002)
    main_args = _get_args()
    if main_args.mock_event is not None:
        handler = NotifyLarkRequestHandler(main_args)
        with open(main_args.mock_event[1], "r", encoding="utf-8") as f:
            handler.handle_event(main_args.mock_event[0], json.load(f))
        exit(0)

    handler = partial(NotifyLarkRequestHandler, main_args)

    print("Serve at port 9002")
    httpd = HTTPServer(server_address, handler)
    httpd.serve_forever()
