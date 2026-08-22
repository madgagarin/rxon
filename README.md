# RXON (Reverse Axon) Protocol

**EN** | [ES](https://github.com/madgagarin/rxon/blob/main/docs/es/README.md) | [RU](https://github.com/madgagarin/rxon/blob/main/docs/ru/README.md)

[![License: MPL 2.0](https://img.shields.io/badge/License-MPL%202.0-brightgreen.svg)](https://opensource.org/licenses/MPL-2.0)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![PyPI version](https://img.shields.io/pypi/v/rxon.svg)](https://pypi.org/project/rxon/)

**RXON** (Reverse Axon) is a lightweight, extensible reverse-connection protocol designed for **[HLN (Holarchical Logic Network)](https://github.com/madgagarin/hln)** architectures.

It serves as the "nervous system" for distributed multi-agent systems, providing a strictly typed, Zero Trust foundation for inter-service communication.

## 🚀 Concept

In traditional networks, commands usually flow "top-down" (Push model). In **RXON**, the connection initiative always comes from the subordinate node (Shell) to the superior node (Orchestrator). This "Reverse Axon" architecture allows workers to operate behind NAT or Firewalls without complex network configuration, while maintaining a secure, bi-directional control channel.

## ✨ Key Features

- **Reverse Connection (PULL)**: Nodes connect to the orchestrator to pull tasks, ensuring compatibility with complex network environments (NAT/Firewalls).
- **Zero Trust Security**: Payload signing via HMAC-SHA256 (symmetric) and Ed25519 (asymmetric digital signatures) with constant-time verification. Support for signed bubbling chains, mTLS certificate identity extraction, and `sig` (`orchestrator_signature`) task verification.
- **Policy & Cost Headers**: Built-in support for job policy constraints (`policy`), holarchy depth tracking (`depth`), transition step counters (`step`), parent hash linkage (`parent_hash`), and task execution cost reporting (`costs`).
- **Deep Model Restoration**: Robust `from_dict` utility powered by `msgspec.convert` that recursively restores complex Python types (msgspec.Structs, Enums, UUIDs, datetimes) from raw dictionaries, supporting nested structures and `Union` types.
- **Secure Serialization**: `to_dict` utility that recursively strips `None` values to reduce payload size and normalizes `float` values (e.g., `1.0` -> `1`) to ensure stable cryptographic hashes.
- **Automated Contract Validation**: Built-in JSON Schema engine that automatically infers schemas from Python types and validates `TaskPayload` parameters against `SkillInfo` contracts.
- **Advanced Resource Matching**: Mathematical logic for resource allocation:
  - **Numbers**: Uses **GE (Greater or Equal)** logic (Requirement <= Available).
  - **Lists**: Uses **Inclusion** (val in list) or **Intersection** (any common element).
  - **Strings**: Case-insensitive partial matching for hardware models.
- **Unified Telemetry**: Heartbeats include granular metrics for any custom devices (Sensors, GPUs, Actuators) and generic system properties via the extensible `HardwareDevice` model.
- **Resilient Transport**: HTTP/WebSocket implementation with Secure Token Service (STS) supporting **Refresh Tokens**, exponential backoff for reconnections, and built-in **Rate Limit (HTTP 429)** handling with `Retry-After`.

## 🌐 Ecosystem

RXON is the foundational protocol powering the distributed multi-agent automation stack:

- **[HLN (Holarchical Logic Network)](https://github.com/madgagarin/hln)**: The architectural pattern, manifesto, and design specification for self-similar holarchies.
- **[Avtomatika](https://github.com/avtomatika-ai/avtomatika)**: High-performance state-machine based orchestrator for long-running AI workflows and distributed execution.
- **[Avtomatika Worker SDK](https://github.com/avtomatika-ai/avtomatika-worker)**: The official Python SDK for building autonomous workers (Holons) that connect to orchestrators via RXON.

## 🏗 Architecture & Logic

### Internal Validation & Normalization

The library ensures data integrity at several layers:

1.  **Serialization Stability**: RXON uses a **JSON Round-trip** mechanism with `orjson` to normalize all numeric types (`10.0` -> `10`), coerce dictionary keys to strings, and sort keys. This ensures that the same object always produces the exact same HMAC hash regardless of minor formatting differences.
2.  **Full Type Support**: Native support for `datetime`, `UUID`, `Enum`, and **Pydantic** models ensures seamless integration with modern Python ecosystems while maintaining cryptographic consistency.
3.  **Recursion Protection**: All recursive operations are limited to a depth of 100 to prevent stack overflow or DoS attacks via malicious payloads.
4.  **Schema Enforcement**: Before task execution, the library validates input parameters against the skill's JSON Schema, checking for required fields, type correctness, and allowed enum values.

### Smart Matching Logic

RXON formalizes the rules for matching tasks to holons:

1.  **Hardware Matching**: Compares `HardwareDevice` properties. If a task requires `vram_gb: 16`, it will match any device with `vram_gb >= 16`.
2.  **Resource Properties**: Generic resources (like RAM or CPU cores) are matched via the `properties` dictionary using the same GE logic.
3.  **Capability Intersection**: If a task accepts multiple environments (e.g., `["linux", "darwin"]`), a worker with `linux` will be correctly matched.

### Policy, Holarchy & Cost Tracking

RXON standardizes execution governance and metric tracking across distributed holons:

- **Policy Constraints (`policy`)**: Dict carrying execution constraints (e.g. allowed skills, token limits, budget caps).
- **Holarchy & Step Counters (`depth`, `step`, `parent_hash`)**: Track call nesting depth (`depth`), state transition index (`step`), and parent event cryptographic link (`parent_hash`).
- **Signature (`sig`)**: Cryptographic signature of the task payload from the orchestrator.
- **Execution Cost Reporting (`costs`)**: `TaskResult.costs` field reporting consumed tokens, computational duration, or financial metrics (e.g. `{"tokens": 1500, "usd": 0.02}`).

## 🧪 Quick Start

### Worker Side (PULL)

```python
from rxon import create_transport
from rxon.models import Resources, HardwareDevice

# 1. Create transport (supports http, https, ws, wss)
transport = create_transport("ws://api.hln.local", "worker-01", "secret-token")

# 2. Define worker resources
my_res = Resources(
    properties={"ram_gb": 64, "cpu_cores": 16},
    devices=[HardwareDevice(type="gpu", model="RTX 4090", properties={"vram_gb": 24})],
)

# 3. Smart Matching Logic (Requirement: GPU with at least 16GB VRAM)
req = Resources(devices=[HardwareDevice(type="gpu", properties={"vram_gb": 16})])
if my_res.matches(req):
    print("This holon is ready for the task!")
```

### Orchestrator Side (Server)

```python
from aiohttp import web
from rxon import HttpListener

app = web.Application()
listener = HttpListener(app)

# MANDATORY: Register RXON routes before app startup
listener.setup_routes()


async def my_handler(action, payload, context):
    if action == "poll":
        return {"job_id": "j-1", "task_id": "t-1", "type": "echo"}
    return {"status": "ok"}


# Start listening
await listener.start(handler=my_handler)
```

## 📜 License

The project is distributed under the Mozilla Public License 2.0 (MPL 2.0).

---

_Mantra: "The RXON is the medium for the Ghost."_
