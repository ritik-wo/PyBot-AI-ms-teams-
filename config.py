#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import os

""" Bot Configuration """


class DefaultConfig:
    def __init__(self):
        self.PORT = 3978
        self.APP_ID = os.environ.get("MicrosoftAppId", "<<MICROSOFT-APP-ID>>")
        self.APP_PASSWORD = os.environ.get("MicrosoftAppPassword", "<<MICROSOFT-APP-PASSWORD>>")
        self.CHANNEL_AUTH_TENANT = os.environ.get("CHANNEL_AUTH_TENANT", "<<CHANNEL-AUTH-TENANT>>")