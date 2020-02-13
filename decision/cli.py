# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import argparse
import os

from decision.workflow import Workflow


def main():
    parser = argparse.ArgumentParser("Fuzzing decision task")
    parser.add_argument(
        "pool_name", type=str, help="The target fuzzing pool to create tasks for"
    )
    parser.add_argument(
        "--taskcluster-secret",
        type=str,
        help="Taskcluster Secret path for configuration",
        default=os.environ.get("TASKCLUSTER_SECRET"),
    )
    parser.add_argument(
        "--configuration",
        type=str,
        help="Local configuration file replacing Taskcluster secrets for fuzzing",
    )
    parser.add_argument(
        "--task-id",
        type=str,
        help="Taskcluster decision task creating new fuzzing tasks",
        default=os.environ.get("TASK_ID"),
    )
    parser.add_argument(
        "--task-group-id",
        type=str,
        help="Taskcluster decision task group where the new tasks will be added",
        default=os.environ.get("TASK_GROUP_ID"),
    )
    args = parser.parse_args()

    # We need both task & task group information
    if not args.task_id:
        raise Exception("Missing decision task id")
    if not args.task_group_id:
        raise Exception("Missing decision task group id")

    # Configure workflow using the secret or local configuration
    workflow = Workflow()
    config = workflow.configure(
        local_path=args.configuration, secret=args.taskcluster_secret
    )

    # Retrieve remote repositories
    workflow.clone(config)

    # Build all task definitions for that pool
    workflow.build_tasks(args.pool_name, args.task_id, args.task_group_id)
