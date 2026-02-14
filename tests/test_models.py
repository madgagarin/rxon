from typing import List, NamedTuple

from rxon.models import GPUInfo, InstalledModel, Resources, TaskPayload, WorkerCapabilities, WorkerRegistration
from rxon.utils import to_dict


def test_to_dict_simple():
    class Simple(NamedTuple):
        a: int
        b: str

    obj = Simple(1, "test")
    assert to_dict(obj) == {"a": 1, "b": "test"}


def test_to_dict_nested():
    class Child(NamedTuple):
        val: int

    class Parent(NamedTuple):
        name: str
        child: Child
        children: List[Child]

    obj = Parent("dad", Child(1), [Child(2), Child(3)])
    expected = {"name": "dad", "child": {"val": 1}, "children": [{"val": 2}, {"val": 3}]}
    assert to_dict(obj) == expected


def test_worker_registration_serialization():
    # Construct a complex registration object
    reg = WorkerRegistration(
        worker_id="worker-01",
        worker_type="gpu",
        supported_skills=["gen_image", "upscale"],
        resources=Resources(max_concurrent_tasks=2, cpu_cores=8, gpu_info=GPUInfo("RTX 4090", 24)),
        installed_software={"python": "3.11", "cuda": "12.1"},
        installed_models=[InstalledModel("sdxl", "1.0")],
        capabilities=WorkerCapabilities(
            hostname="node-1", ip_address="192.168.1.5", cost_per_skill={"gen_image": 0.01}
        ),
    )

    data = to_dict(reg)
    assert data["worker_id"] == "worker-01"
    assert data["resources"]["gpu_info"]["model"] == "RTX 4090"
    assert data["capabilities"]["cost_per_skill"]["gen_image"] == 0.01


def test_model_field_verification():
    """Ensure TaskPayload has expected fields matching protocol."""
    fields = TaskPayload._fields
    assert "job_id" in fields
    assert "task_id" in fields
    assert "params" in fields
    assert "tracing_context" in fields
