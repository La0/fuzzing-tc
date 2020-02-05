# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import os

from tcadmin.appconfig import AppConfig

from decision.workflow import Workflow

appconfig = AppConfig()

# Add options to get our own configuration
appconfig.options.add(
    "--fuzzing-configuration",
    help="Local configuration file replacing Taskcluster secrets for fuzzing",
)
appconfig.options.add(
    "--fuzzing-taskcluster-secret",
    help="Taskcluster Secret path for fuzzing",
    default=os.environ.get("TASKCLUSTER_SECRET"),
)

# We always want to run against community Taskcluster instance
os.environ["TASKCLUSTER_ROOT_URL"] = "https://community-tc.services.mozilla.com"

# Setup our workflow as resource generetor
appconfig.generators.register(Workflow.tc_admin_boot)