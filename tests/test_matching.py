# Copyright (c) 2025-2026 Dmitrii Gagarin aka madgagarin
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from rxon.models import HardwareDevice, InstalledArtifact, Resources


def test_hardware_device_matches_simple() -> None:
    dev = HardwareDevice(type="gpu", model="NVIDIA RTX 4090", id="0")

    assert dev.matches(HardwareDevice(type="gpu"))
    assert dev.matches(HardwareDevice(type="gpu", model="RTX 4090"))
    assert dev.matches(HardwareDevice(type="gpu", model="rtx 4090"))
    assert dev.matches(HardwareDevice(type="gpu", id="0"))

    assert not dev.matches(HardwareDevice(type="cpu"))
    assert not dev.matches(HardwareDevice(type="gpu", model="RTX 3080"))
    assert not dev.matches(HardwareDevice(type="gpu", id="1"))


def test_hardware_device_matches_properties() -> None:
    dev = HardwareDevice(type="gpu", properties={"memory_gb": 24, "cuda_version": "12.1", "compute_cap": 8.9})

    assert dev.matches(HardwareDevice(type="gpu", properties={"memory_gb": 16}))
    assert dev.matches(HardwareDevice(type="gpu", properties={"memory_gb": 24}))
    assert dev.matches(HardwareDevice(type="gpu", properties={"cuda_version": "12.1"}))
    assert dev.matches(HardwareDevice(type="gpu", properties={"compute_cap": 8.0}))

    assert not dev.matches(HardwareDevice(type="gpu", properties={"memory_gb": 32}))
    assert not dev.matches(HardwareDevice(type="gpu", properties={"cuda_version": "11.8"}))
    assert not dev.matches(HardwareDevice(type="gpu", properties={"unknown_prop": 1}))


def test_resources_matches_compute() -> None:
    res = Resources(properties={"cpu_cores": 16, "ram_gb": 64.5})

    assert res.matches(Resources(properties={"cpu_cores": 8}))
    assert res.matches(Resources(properties={"ram_gb": 32.0}))
    assert res.matches(Resources(properties={"cpu_cores": 16, "ram_gb": 64.5}))

    assert not res.matches(Resources(properties={"cpu_cores": 32}))
    assert not res.matches(Resources(properties={"ram_gb": 128}))


def test_resources_matches_multi_device() -> None:
    res = Resources(
        devices=[
            HardwareDevice(type="gpu", model="RTX 4090", properties={"vram": 24}),
            HardwareDevice(type="gpu", model="RTX 3080", properties={"vram": 10}),
            HardwareDevice(type="sensor", model="LiDAR"),
        ]
    )

    req = Resources(
        devices=[
            HardwareDevice(type="gpu", properties={"vram": 20}),
            HardwareDevice(type="gpu", properties={"vram": 8}),
        ]
    )
    assert res.matches(req)

    req2 = Resources(devices=[HardwareDevice(type="gpu", model="RTX 4090"), HardwareDevice(type="sensor")])
    assert res.matches(req2)

    req3 = Resources(devices=[HardwareDevice(type="gpu"), HardwareDevice(type="gpu"), HardwareDevice(type="gpu")])
    assert not res.matches(req3)

    req4 = Resources(devices=[HardwareDevice(type="gpu", properties={"vram": 30})])
    assert not res.matches(req4)


def test_resources_matches_properties() -> None:
    res = Resources(properties={"location": "us-east", "tier": 1})

    assert res.matches(Resources(properties={"location": "us-east"}))
    assert res.matches(Resources(properties={"tier": 1}))

    assert not res.matches(Resources(properties={"tier": 2}))
    assert not res.matches(Resources(properties={"location": "eu-west"}))


def test_hardware_device_incompatible_types() -> None:
    dev = HardwareDevice(type="gpu", properties={"vram": "16GB"})
    req = HardwareDevice(type="gpu", properties={"vram": 8})
    assert not dev.matches(req)


def test_matching_with_none_collections() -> None:
    res = Resources(devices=None)
    req = Resources(devices=None)
    assert res.matches(req)

    req2 = Resources(devices=[])
    assert res.matches(req2)


def test_matching_extreme_types() -> None:
    dev = HardwareDevice(type="gpu", properties={"vram": [16, 32]})
    req = HardwareDevice(type="gpu", properties={"vram": 8})
    assert not dev.matches(req)

    dev2 = HardwareDevice(type="gpu", properties={"vram": {"amount": 16}})
    assert not dev2.matches(req)


def test_matching_missing_properties_in_worker() -> None:
    dev = HardwareDevice(type="gpu", properties={"vram": 16})
    req = HardwareDevice(type="gpu", properties={"vram": 8, "cuda_cores": 1000})
    assert not dev.matches(req)


def test_matching_none_vs_empty_collections() -> None:
    assert Resources(devices=None).matches(Resources(devices=[]))
    assert Resources(devices=[]).matches(Resources(devices=None))
    assert Resources(devices=[]).matches(Resources(devices=[]))

    assert Resources(properties=None).matches(Resources(properties={}))
    assert Resources(properties={}).matches(Resources(properties=None))

    assert not Resources(devices=[]).matches(Resources(devices=[HardwareDevice(type="gpu")]))
    assert not Resources(properties={}).matches(Resources(properties={"a": 1}))


def test_artifact_matches() -> None:
    art = InstalledArtifact(name="cuda", version="12.1", properties={"driver": 525})

    assert art.matches(InstalledArtifact(name="cuda"))
    assert art.matches(InstalledArtifact(name="cuda", version="12.1"))
    assert art.matches(InstalledArtifact(name="cuda", properties={"driver": 500}))

    assert not art.matches(InstalledArtifact(name="cuda", version="11.8"))
    assert not art.matches(InstalledArtifact(name="cudnn"))
    assert not art.matches(InstalledArtifact(name="cuda", properties={"driver": 530}))


def test_hardware_device_partial_model_match() -> None:
    dev = HardwareDevice(type="gpu", model="NVIDIA GeForce RTX 4090 Ti")

    assert dev.matches(HardwareDevice(type="gpu", model="RTX 4090"))
    assert dev.matches(HardwareDevice(type="gpu", model="geforce"))
    assert dev.matches(HardwareDevice(type="gpu", model="nvidia"))

    assert not dev.matches(HardwareDevice(type="gpu", model="RTX 3080"))


def test_resources_complex_multi_device_matching() -> None:
    res = Resources(
        devices=[
            HardwareDevice(type="gpu", id="G1", properties={"vram": 24}),
            HardwareDevice(type="gpu", id="G2", properties={"vram": 12}),
            HardwareDevice(type="gpu", id="G3", properties={"vram": 8}),
        ]
    )

    req_ok = Resources(
        devices=[
            HardwareDevice(type="gpu", properties={"vram": 20}),
            HardwareDevice(type="gpu", properties={"vram": 10}),
        ]
    )
    assert res.matches(req_ok)

    req_fail = Resources(
        devices=[
            HardwareDevice(type="gpu", properties={"vram": 20}),
            HardwareDevice(type="gpu", properties={"vram": 20}),
        ]
    )
    assert not res.matches(req_fail)


def test_matching_advanced_lists() -> None:
    res = Resources(properties={"os": "linux", "tier": 1})
    assert res.matches(Resources(properties={"os": ["linux", "darwin"]}))

    res2 = Resources(properties={"tags": ["fast", "gpu", "local"]})
    assert res2.matches(Resources(properties={"tags": "gpu"}))
    assert res2.matches(Resources(properties={"tags": ["gpu", "remote"]}))

    assert not res.matches(Resources(properties={"os": ["windows", "darwin"]}))
    assert not res2.matches(Resources(properties={"tags": ["remote", "slow"]}))
    assert not res2.matches(Resources(properties={"tags": "remote"}))

    assert not res2.matches(Resources(properties={"tags": []}))

    res_empty = Resources(properties={"tags": []})
    assert not res_empty.matches(Resources(properties={"tags": "gpu"}))
    assert not res_empty.matches(Resources(properties={"tags": ["gpu"]}))

    assert not res2.matches(Resources(properties={"tags": 123}))
    assert Resources(properties={"val": 10}).matches(Resources(properties={"val": [10, 20]}))


def test_hardware_device_list_matching_logic() -> None:
    gpu = HardwareDevice(type="gpu", properties={"modes": ["compute", "graphics", "video"]})

    assert gpu.matches(HardwareDevice(type="gpu", properties={"modes": "compute"}))
    assert gpu.matches(HardwareDevice(type="gpu", properties={"modes": ["video", "graphics"]}))

    assert not gpu.matches(HardwareDevice(type="gpu", properties={"modes": "gaming"}))
    assert not gpu.matches(HardwareDevice(type="gpu", properties={"modes": ["gaming", "mining"]}))
