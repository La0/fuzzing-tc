# -*- coding: utf-8 -*-

import pytest

from decision.pool import PoolConfiguration


@pytest.mark.parametrize(
    "size, divisor, result",
    [
        ("2g", "1g", 2),
        ("2g", "1m", 2048),
        ("2g", 1, 2048 * 1024 * 1024),
        ("128t", "1g", 128 * 1024),
    ],
)
def test_parse_size(size, divisor, result):
    if isinstance(divisor, str):
        divisor = PoolConfiguration.parse_size(divisor)

    assert PoolConfiguration.parse_size(size, divisor) == result


@pytest.mark.parametrize(
    "provider, cpu, cores, ram, metal, result",
    [
        ("gcp", "x64", 1, 1, False, ["base", "2-cpus", "more-ram", "metal"]),
        ("gcp", "x64", 2, 1, False, ["2-cpus", "more-ram"]),
        ("gcp", "x64", 2, 5, False, ["more-ram"]),
        ("gcp", "x64", 1, 1, True, ["metal"]),
        ("aws", "arm64", 1, 1, False, ["a1", "a2", "a3"]),
        ("aws", "arm64", 2, 1, False, ["a2", "a3"]),
        ("aws", "arm64", 12, 32, False, ["a3"]),
        ("aws", "arm64", 1, 1, True, []),
        # x64 is not present in aws
        ("aws", "x64", 1, 1, False, KeyError),
        # invalid provider raises too
        ("dummy", "x64", 1, 1, False, KeyError),
    ],
)
def test_machine_filters(mock_machines, provider, cpu, ram, cores, metal, result):

    if isinstance(result, list):
        assert list(mock_machines.filter(provider, cpu, cores, ram, metal)) == result
    else:
        with pytest.raises(result):
            list(mock_machines.filter(provider, cpu, cores, ram, metal))


def test_aws_resources(mock_clouds, mock_machines):

    conf = PoolConfiguration(
        "test",
        {
            "cloud": "aws",
            "scopes": [],
            "disk_size": "120g",
            "cycle_time": "1h",
            "cores_per_task": 10,
            "metal": False,
            "name": "Amazing fuzzing pool",
            "tasks": 3,
            "command": "run-fuzzing.sh",
            "container": "MozillaSecurity/fuzzer:latest",
            "minimum_memory_per_core": "1g",
            "imageset": "generic-worker-A",
            "parents": [],
            "cpu": "arm64",
            "platform": "linux",
            "macros": {},
        },
    )
    resources = conf.build_resources(mock_clouds, mock_machines)
    assert len(resources) == 3
    pool, hook, role = resources

    assert pool.to_json() == {
        "kind": "WorkerPool",
        "config": {
            "launchConfigs": [
                {
                    "capacityPerInstance": 2,
                    "launchConfig": {
                        "ImageId": "ami-1234",
                        "InstanceMarketOptions": {"MarketType": "spot"},
                        "InstanceType": "a3",
                        "Placement": {"AvailabilityZone": "us-west-1a"},
                        "SecurityGroupIds": ["sg-A"],
                        "SubnetId": "subnet-XXX",
                    },
                    "region": "us-west-1",
                    "workerConfig": {
                        "genericWorker": {
                            "config": {
                                "anyKey": "anyValue",
                                "deploymentId": "a17c0937986b2812",
                                "os": "linux",
                                "wstAudience": "communitytc",
                                "wstServerURL": "https://community-websocktunnel.services.mozilla.com",
                            }
                        }
                    },
                }
            ],
            "maxCapacity": 3,
            "minCapacity": 0,
        },
        "emailOnError": True,
        "owner": "fuzzing+taskcluster@mozilla.com",
        "providerId": "community-tc-workers-aws",
        "workerPoolId": "proj-fuzzing/linux-test",
        "description": "*DO NOT EDIT* - This resource is configured automatically.\n"
        "\n"
        "Fuzzing workers generated by decision task",
    }

    assert hook.to_json() == {
        "kind": "Hook",
        "bindings": [],
        "emailOnError": True,
        "hookGroupId": "project-fuzzing",
        "hookId": "linux-test",
        "name": "Amazing fuzzing pool",
        "owner": "fuzzing+taskcluster@mozilla.com",
        "schedule": [],
        "task": {
            "created": {"$fromNow": "0 seconds"},
            "deadline": {"$fromNow": "3600 seconds"},
            "expires": {"$fromNow": "1 month"},
            "extra": {},
            "metadata": {
                "description": "*DO NOT EDIT* - This resource is "
                "configured automatically.\n"
                "\n"
                "Fuzzing workers generated by decision "
                "task",
                "name": "Fuzzing task linux-test",
                "owner": "fuzzing+taskcluster@mozilla.com",
                "source": "https://github.com/MozillaSecurity/fuzzing-tc",
            },
            "payload": {
                "artifacts": {},
                "cache": {},
                "capabilities": {},
                "env": {},
                "features": {"taskclusterProxy": True},
                "image": "MozillaSecurity/fuzzer:latest",
                "maxRunTime": 3600,
            },
            "priority": "high",
            "provisionerId": "proj-fuzzing",
            "retries": 1,
            "routes": [],
            "schedulerId": "-",
            "scopes": [],
            "tags": {},
            "workerType": "linux-test",
        },
        "triggerSchema": {},
        "description": "*DO NOT EDIT* - This resource is configured automatically.\n"
        "\n"
        "Generated Fuzzing hook",
    }

    assert role.to_json() == {
        "kind": "Role",
        "roleId": "hook-id:project-fuzzing/linux-test",
        "scopes": [
            "queue:create-task:highest:proj-fuzzing/linux-test",
            "queue:scheduler-id:-",
        ],
        "description": "*DO NOT EDIT* - This resource is configured automatically.\n"
        "\n"
        "Fuzzing workers generated by decision task",
    }
