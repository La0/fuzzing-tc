# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

from datetime import datetime
from datetime import timedelta

from taskcluster.utils import fromNow
from taskcluster.utils import slugId
from taskcluster.utils import stringDate
from tcadmin.resources import Hook
from tcadmin.resources import Role
from tcadmin.resources import WorkerPool

from ..common.pool import PoolConfiguration as CommonPoolConfiguration
from . import DECISION_TASK_SECRET
from . import HOOK_PREFIX
from . import OWNER_EMAIL
from . import PROVIDER_IDS
from . import PROVISIONER_ID
from . import SCHEDULER_ID
from . import WORKER_POOL_PREFIX

DESCRIPTION = """*DO NOT EDIT* - This resource is configured automatically.

Fuzzing workers generated by decision task"""


class PoolConfiguration(CommonPoolConfiguration):
    """Fuzzing Pool Configuration

    Attributes:
        cloud (str): cloud provider, like aws or gcp
        command (list): list of strings, command to execute in the image/container
        container (str): name of the container
        cores_per_task (int): number of cores to be allocated per task
        cpu (int): cpu architecture (eg. x64/arm64)
        cycle_time (int): maximum run time of this pool in seconds
        disk_size (int): disk size in GB
        imageset (str): imageset name in community-tc-config/config/imagesets.yml
        macros (dict): dictionary of environment variables passed to the target
        metal (bool): whether or not the target requires to be run on bare metal
        minimum_memory_per_core (float): minimum RAM to be made available per core in GB
        name (str): descriptive name of the configuration
        parents (list): list of parents to inherit from
        platform (str): operating system of the target (linux, windows)
        scopes (list): list of taskcluster scopes required by the target
        tasks (int): number of tasks to run (each with `cores_per_task`)
    """

    def build_resources(self, providers, machine_types, env=None):
        """Build the full tc-admin resources to compare and build the pool"""

        # Select a cloud provider according to configuration
        assert self.cloud in providers, f"Cloud Provider {self.cloud} not available"
        provider = providers[self.cloud]

        # Build the pool configuration for selected machines
        machines = self.get_machine_list(machine_types)
        config = {
            "minCapacity": 0,
            "maxCapacity": self.tasks,
            "launchConfigs": provider.build_launch_configs(
                self.imageset, machines, self.disk_size
            ),
        }

        # Mandatory scopes to execute the hook
        # or create new tasks
        decision_task_scopes = (
            f"queue:scheduler-id:{SCHEDULER_ID}",
            f"queue:create-task:highest:{PROVISIONER_ID}/{self.id}",
            f"secrets:get:{DECISION_TASK_SECRET}",
        )

        # Build the decision task payload that will trigger the new fuzzing tasks
        decision_task = {
            "created": {"$fromNow": "0 seconds"},
            "deadline": {"$fromNow": "1 hour"},
            "expires": {"$fromNow": "1 month"},
            "extra": {},
            "metadata": {
                "description": DESCRIPTION,
                "name": f"Fuzzing decision {self.id}",
                "owner": OWNER_EMAIL,
                "source": "https://github.com/MozillaSecurity/fuzzing-tc",
            },
            "payload": {
                "artifacts": {},
                "cache": {},
                "capabilities": {},
                "env": {"TASKCLUSTER_SECRET": DECISION_TASK_SECRET},
                "features": {"taskclusterProxy": True},
                "image": {
                    "type": "indexed-image",
                    "path": "public/fuzzing-tc-decision.tar",
                    "namespace": "project.fuzzing.config.master",
                },
                "command": ["fuzzing-decision", self.filename],
                "maxRunTime": 3600,
            },
            "priority": "high",
            "provisionerId": PROVISIONER_ID,
            "workerType": self.id,
            "retries": 1,
            "routes": [],
            "schedulerId": SCHEDULER_ID,
            "scopes": decision_task_scopes,
            "tags": {},
        }
        if env is not None:
            assert set(decision_task["payload"]["env"].keys()).isdisjoint(
                set(env.keys())
            )
            decision_task["payload"]["env"].update(env)

        pool = WorkerPool(
            workerPoolId=f"{WORKER_POOL_PREFIX}/{self.id}",
            providerId=PROVIDER_IDS[self.cloud],
            description=DESCRIPTION,
            owner=OWNER_EMAIL,
            emailOnError=True,
            config=config,
        )

        hook = Hook(
            hookGroupId=HOOK_PREFIX,
            hookId=self.id,
            name=self.id,
            description="Generated Fuzzing hook",
            owner=OWNER_EMAIL,
            emailOnError=True,
            schedule=(),  # TODO
            task=decision_task,
            bindings=(),
            triggerSchema={},
        )

        role = Role(
            roleId=f"hook-id:{HOOK_PREFIX}/{self.id}",
            description=DESCRIPTION,
            scopes=tuple(self.scopes) + decision_task_scopes,
        )

        return [pool, hook, role]

    def build_tasks(self, parent_task_id, env=None):
        """Create fuzzing tasks and attach them to a decision task"""
        now = datetime.utcnow()
        for i in range(1, self.tasks + 1):
            task_id = slugId()
            task = {
                "taskGroupId": parent_task_id,
                "dependencies": [parent_task_id],
                "created": stringDate(now),
                "deadline": stringDate(now + timedelta(seconds=self.cycle_time)),
                "expires": stringDate(fromNow("1 month", now)),
                "extra": {},
                "metadata": {
                    "description": DESCRIPTION,
                    "name": f"Fuzzing task {self.id} - {i}/{self.tasks}",
                    "owner": OWNER_EMAIL,
                    "source": "https://github.com/MozillaSecurity/fuzzing-tc",
                },
                "payload": {
                    "artifacts": {
                        "project/fuzzing/private/logs": {
                            "expires": stringDate(fromNow("1 month", now)),
                            "path": "/logs/",
                            "type": "directory",
                        }
                    },
                    "cache": {},
                    "capabilities": {},
                    "env": {"TASKCLUSTER_FUZZING_POOL": self.filename},
                    "features": {"taskclusterProxy": True},
                    "image": self.container,
                    "maxRunTime": self.cycle_time,
                },
                "priority": "high",
                "provisionerId": PROVISIONER_ID,
                "workerType": self.id,
                "retries": 1,
                "routes": [],
                "schedulerId": SCHEDULER_ID,
                "scopes": self.scopes,
                "tags": {},
            }
            if env is not None:
                assert set(task["payload"]["env"]).isdisjoint(set(env))
                task["payload"]["env"].update(env)

            yield task_id, task
