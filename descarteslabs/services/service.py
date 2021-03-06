# Copyright 2017 Descartes Labs.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import random

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import descarteslabs
from ..exceptions import ServerError, BadRequestError, NotFoundError, RateLimitError, GatewayTimeoutError


class WrappedSession(requests.Session):
    def __init__(self, base_url, timeout=None):
        self.base_url = base_url
        self.timeout = timeout
        super(WrappedSession, self).__init__()

    def request(self, method, url, **kwargs):
        if self.timeout and 'timeout' not in kwargs:
            kwargs['timeout'] = self.timeout

        resp = super(WrappedSession, self).request(method, self.base_url + url, **kwargs)

        if resp.status_code == 200:
            return resp
        elif resp.status_code == 400:
            raise BadRequestError(resp.text)
        elif resp.status_code == 404:
            raise NotFoundError("404 %s %s" % (method, url))
        elif resp.status_code == 429:
            raise RateLimitError(resp.text)
        elif resp.status_code == 504:
            raise GatewayTimeoutError(
                "Your request timed out on the server. "
                "Consider reducing the complexity of your request.")
        else:
            raise ServerError(resp.text)


class Service:
    TIMEOUT = (9.5, 30)

    def __init__(self, url, token):
        self.auth = descarteslabs.descartes_auth
        self.base_url = url
        if token:
            self.auth._token = token

        self.current_session = None
        self.session_token = None

    @property
    def token(self):
        return self.auth.token

    @token.setter
    def token(self, token):
        self.auth._token = token

    @property
    def session(self):
        if self.session_token != self.token:
            self.current_session = None

        if not self.current_session:
            self.current_session = self.build_session()
            self.session_token = self.token

        return self.current_session

    def build_session(self):
        s = WrappedSession(self.base_url, timeout=self.TIMEOUT)

        retries = Retry(total=5,
                        read=2,
                        backoff_factor=random.uniform(1, 3),
                        method_whitelist=frozenset([
                            'HEAD', 'TRACE', 'GET', 'POST',
                            'PUT', 'OPTIONS', 'DELETE'
                        ]),
                        status_forcelist=[429, 500, 502, 503])

        s.mount('https://', HTTPAdapter(max_retries=retries))

        s.headers.update({
            "Authorization": self.token,
            "Content-Type": "application/json",
            "User-Agent": "dl-python/{}".format(descarteslabs.__version__)
        })

        here = os.path.dirname(__file__)

        try:
            file = os.path.join(here, 'gd_bundle-g2-g1.crt')
            with open(file):
                s.verify = file
        except:
            s.verify = False

        return s
