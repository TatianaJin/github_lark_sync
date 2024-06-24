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

from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse as urlparse


class NotifyLarkRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        print(self.path)
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

    def do_POST(self):
        print(self.path)
        length = int(self.headers["Content-Length"])
        post_data = urlparse.parse_qs(self.rfile.read(length).decode("utf-8"))
        for key, value in post_data.items():
            print("------------------ Key --------------------")
            print(key)
            print("------------------ value --------------------")
            print(value)


if __name__ == "__main__":
    server_address = ("", 9002)
    httpd = HTTPServer(server_address, NotifyLarkRequestHandler)
    httpd.serve_forever()
